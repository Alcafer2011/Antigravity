# -*- coding: utf-8 -*-
"""LE LOCANDINE CHE MANCANO, CERCATE SU TUTTI I SERVIZI CHE LE DANNO.

PERCHE' (chiesto dall'utente l'11/09/2026)
    "devi creare uno script python per la ricerca delle locandine che mancano
    a livello di tutti i servizi che le espongono per metterle, non credo che
    solo tmdb le fornisca". Giusto: TMDb ha locandine, sfondi e loghi, ma la
    striscia (banner), il personaggio ritagliato (clearart) e il disco li ha
    solo fanart.tv; le strisce delle serie le ha anche TVmaze; per anime poco
    noti AniList, Kitsu e MyAnimeList (Jikan) ne sanno piu' di TMDb; i loghi
    di programmi e film a volte stanno solo su Wikidata.

COME LAVORA
    1. SCORRE la Videoteca sul Kodi del PC come la vede la TV (menu, reparti,
       righe della home) e raccoglie ogni voce con le sue immagini.
    2. CONTROLLA ogni immagine: manca? e' un segnaposto? l'indirizzo e' morto?
    3. RICONOSCE il titolo: dall'id TMDb nell'indirizzo, dal catalogo delle
       saghe, o per nome e anno, con un confronto dei titoli (sotto 0,86 di
       somiglianza non si prende: una locandina sbagliata e' peggio di nessuna).
    4. CERCA, in quest'ordine: TMDb, fanart.tv (solo con la chiave personale
       in ~/.fanart-tv-key), TVmaze, AniList, Kitsu, iTunes, Wikidata, Jikan.
    5. VERIFICA ogni immagine prima di tenerla: misure e trasparenza (un logo
       senza trasparenza sopra una tessera e' un rettangolo), forma giusta.
    6. SCRIVE plugin.video.saghe/resources/arte_extra.json - l'add-on lo usa
       solo dove un'immagine manca - e il rapporto HTML locandine/REPORT.html.

USO
    python locandine.py                    tutto (la prima volta qualche minuto; poi c'e' la cache)
    python locandine.py --profondita 2     meno livelli, piu' veloce
    python locandine.py --solo-controllo   guarda soltanto: niente ricerche, niente file
    python locandine.py --non-aprire
"""

import argparse
import base64
import collections
import concurrent.futures
import difflib
import hashlib
import html
import importlib.util
import io
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(QUI, "plugin.video.saghe")
CARTELLA = os.path.join(QUI, "locandine")
CACHE = os.path.join(CARTELLA, "cache")
KODI = os.path.expandvars(r"%APPDATA%\Kodi")
BASE = "plugin://plugin.video.saghe/"
FILE_API_PC = os.path.join(os.path.expanduser("~"), ".kodi-pc-api")
FILE_FANART = os.path.join(os.path.expanduser("~"), ".fanart-tv-key")
UA = "Mozilla/5.0 (Videoteca locandine.py)"
q = urllib.parse.quote


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ARTE = _modulo("arte_extra_pc", os.path.join(ADDON, "resources", "lib", "arte_extra.py"))
with io.open(os.path.join(ADDON, "resources", "lib", "tmdb.py"), encoding="utf-8") as _f:
    CHIAVE_TMDB = re.search(r'CHIAVE\s*=\s*"([^"]+)"', _f.read()).group(1)
CHIAVE_FANART = io.open(FILE_FANART, encoding="utf-8").read().strip() if os.path.exists(FILE_FANART) else ""

PRINCIPALI = ("poster", "fanart", "clearlogo", "keyart")
BELLE = ("landscape", "banner", "clearart", "discart")
TUTTE = PRINCIPALI + BELLE
# Azioni che fanno qualcosa (finestre, rete, scritture) o elencano episodi: non si aprono.
NON_APRIRE = {"cerca", "misura", "stato_linea", "impostazioni", "aggiornamenti", "segnala", "regola_s4me",
              "regola_s4me_muto", "vetrina", "netflix_aggiungi", "consiglio_aggiungi", "consiglio_togli",
              "lista_metti", "lista_togli", "pollice", "vai", "visto", "nonvisto", "azzera", "salta", "capitoli",
              "spiega", "riproduci", "apri_film", "diretta", "tv", "tv_gruppo", "tv_apri", "russo_guarda",
              "anomalie", "sfoglia", "tagli", "altro", "linea", "abbonamenti", "percorso", "russo",
              # Dall'11/09/2026 un genere dei documentari e la ricerca FANNO una ricerca vera sui
              # siti (ricerca_siti.py): 130 generi = dieci minuti di rete, e i risultati hanno
              # gia' le immagini di s4me. Non sono locandine nostre da completare.
              "scaffale_cerca", "cerca_di_nuovo", "assistenza", "netflix_aggiungi", "cinema_fonti"}
REGOLE = {
    "poster": lambda w, h, r, a: w >= 300 and 0.6 <= r <= 0.76,
    "keyart": lambda w, h, r, a: w >= 300 and 0.6 <= r <= 0.76,
    "fanart": lambda w, h, r, a: w >= 960 and 1.6 <= r <= 1.9,
    "landscape": lambda w, h, r, a: w >= 500 and 1.6 <= r <= 1.9,
    "clearlogo": lambda w, h, r, a: w >= 300 and r >= 1.3 and a,
    "banner": lambda w, h, r, a: w >= 500 and r >= 3.5,
    "clearart": lambda w, h, r, a: w >= 400 and a,
    "discart": lambda w, h, r, a: w >= 400 and 0.9 <= r <= 1.1 and a,
}
FIDATE_TRASPARENTI = ("TMDb", "fanart.tv")      # loghi e clearart di questi sono PNG trasparenti per regola


# ------------------------------------------------------------------ rete, con cache e buone maniere

_BLOCCHI = collections.defaultdict(lambda: threading.Semaphore(4))
_BLOCCHI["api.tvmaze.com"] = threading.Semaphore(2)
_BLOCCHI["api.jikan.moe"] = threading.Semaphore(1)
_BLOCCHI["graphql.anilist.co"] = threading.Semaphore(2)
_SCRITTURA = threading.Lock()


def chiedi(url, dati=None, intestazioni=None, giorni=7):
    """JSON da un servizio. Le risposte restano in cache: rilanciare costa poco."""
    firma = url + (json.dumps(dati, sort_keys=True) if dati is not None else "")
    p = os.path.join(CACHE, "risposte", hashlib.md5(firma.encode("utf-8")).hexdigest() + ".json")
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < giorni * 86400:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    host = urllib.parse.urlsplit(url).netloc
    risposta = None
    with _BLOCCHI[host]:
        for tentativo in range(3):
            try:
                corpo = json.dumps(dati).encode("utf-8") if dati is not None else None
                h = {"User-Agent": UA, "Accept": "application/json"}
                if corpo:
                    h["Content-Type"] = "application/json"
                h.update(intestazioni or {})
                with urllib.request.urlopen(urllib.request.Request(url, corpo, h), timeout=25) as f:
                    risposta = json.loads(f.read().decode("utf-8", "replace"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2 + 3 * tentativo)
                    continue
                risposta = {"_errore": e.code}
                break
            except Exception:
                time.sleep(1 + tentativo)
        if host == "api.jikan.moe":
            time.sleep(0.4)
    if risposta is not None:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(risposta, f)
    return risposta


def _cache_json(nome):
    p = os.path.join(CACHE, nome)
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _salva_json(nome, dati):
    os.makedirs(CACHE, exist_ok=True)
    with _SCRITTURA:
        with io.open(os.path.join(CACHE, nome), "w", encoding="utf-8") as f:
            json.dump(dati, f)


# ------------------------------------------------------------------ Kodi del PC

def rpc(metodo, parametri=None, tempo=180):
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": parametri or {}}).encode()
    h = {"Content-Type": "application/json"}
    if os.path.exists(FILE_API_PC):
        segreto = io.open(FILE_API_PC, encoding="utf-8").read().strip()
        h["Authorization"] = "Basic " + base64.b64encode(("kodi:" + segreto).encode()).decode()
    with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8080/jsonrpc", corpo, h), timeout=tempo) as f:
        d = json.load(f)
    if "error" in d:
        raise RuntimeError(d["error"].get("message", d["error"]))
    return d.get("result") or {}


def pulisci(etichetta):
    t = re.sub(r"\[/?(?:B|I|COLOR[^\]]*|UPPERCASE|LOWERCASE|LIGHT)\]", "", etichetta or "")
    return t.split("\n")[0].strip()


def _parametri(indirizzo):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(indirizzo).query))


def _vero(url):
    """Kodi restituisce le immagini come image://<indirizzo codificato>/."""
    if url.startswith("image://"):
        url = urllib.parse.unquote(url[len("image://"):])
        if url.endswith("/"):
            url = url[:-1]
    return url


def _partenze():
    fuori = [("Menu principale", BASE)]
    for che in ("continua", "saghe", "film", "serietv", "cinema", "consigli", "lista", "novita",
                "netflix:serietv", "netflix:film", "netflix:anime"):
        fuori.append(("Riga %s" % che, BASE + "?" + urllib.parse.urlencode({"azione": "widget", "che": che})))
    return fuori


def _genere(v):
    """'tv' o 'movie' per un titolo; None per le voci di servizio (menu, strumenti)."""
    f = v["file"]
    if f.startswith("plugin://plugin.video.s4me") and "cinema_fonti" in f:
        return "movie"
    if not f.startswith(BASE):
        scaffali = ("riga documentari", "riga cucina", "riga youtube", "documentari", "cucina", "i tuoi canali youtube")
        return "tv" if any(d.lower().startswith(scaffali) for d in v["dove"]) else None
    p = _parametri(f)
    azione = p.get("azione", "")
    if azione == "apri_film":
        return "movie"
    if azione == "netflix_aggiungi":
        return "movie" if p.get("tipo") == "film" else "tv"
    if azione in ("percorso", "film", "gruppo", "consiglio_aggiungi", "consiglio_togli", "scaffale_cerca"):
        return "tv"
    return None


def scorri(profondita, massimo):
    voci, visitate, errori = {}, set(), []
    coda = collections.deque((nome, url, 0) for nome, url in _partenze())
    for scaffale in ("documentari", "cucina", "youtube"):
        for i in range(40):
            url = BASE + "?" + urllib.parse.urlencode({"azione": "widget", "che": "%s:%d" % (scaffale, i)})
            coda.append(("Riga %s" % scaffale, url, profondita))       # righe: solo il loro contenuto
    vuote = collections.Counter()
    while coda and len(visitate) < massimo:
        nome, url, livello = coda.popleft()
        if url in visitate:
            continue
        chiave_riga = nome if nome.startswith("Riga ") and ":" in url else None
        if chiave_riga and vuote[chiave_riga] >= 2:
            continue                                  # due indici vuoti di fila: lo scaffale e' finito
        visitate.add(url)
        try:
            files = rpc("Files.GetDirectory", {"directory": url, "media": "video",
                                               "properties": ["art", "thumbnail", "title", "year"]}).get("files") or []
        except Exception as e:
            errori.append((url, str(e)))
            continue
        if chiave_riga:
            vuote[chiave_riga] = 0 if files else vuote[chiave_riga] + 1
        for f in files:
            v = voci.setdefault(f["file"], {"etichetta": f.get("label", ""), "file": f["file"], "tipo": f.get("filetype"),
                                            "anno": str(f.get("year") or "") if f.get("year") else "",
                                            "arte": {k: _vero(x) for k, x in (f.get("art") or {}).items()},
                                            "dove": []})
            if nome not in v["dove"]:
                v["dove"].append(nome)
            azione = _parametri(f["file"]).get("azione", "")
            if (f.get("filetype") == "directory" and livello < profondita and f["file"].startswith(BASE)
                    and azione not in NON_APRIRE):
                coda.append((pulisci(f.get("label", ""))[:40] or azione, f["file"], livello + 1))
    return voci, len(visitate), errori


# ------------------------------------------------------------------ controllo delle immagini

def verifica_indirizzi(indirizzi):
    cache = _cache_json("verifiche.json")
    adesso = time.time()
    da_fare = [u for u in indirizzi if not (u in cache and adesso - cache[u][1] < 3 * 86400)]

    def prova(u):
        for metodo in ("HEAD", "GET"):
            try:
                r = urllib.request.Request(u, method=metodo, headers={"User-Agent": UA, "Range": "bytes=0-1023"})
                with urllib.request.urlopen(r, timeout=20) as f:
                    return u, str(f.status)
            except urllib.error.HTTPError as e:
                if metodo == "GET":
                    return u, str(e.code)
            except Exception:
                if metodo == "GET":
                    return u, "rete"
        return u, "rete"

    with concurrent.futures.ThreadPoolExecutor(24) as ex:
        for u, esito in ex.map(prova, da_fare):
            cache[u] = [esito, adesso]
    _salva_json("verifiche.json", cache)
    return {u: cache[u][0] for u in indirizzi}


def stato_immagine(url, verifiche):
    if ARTE.vuota(url):
        return "manca"
    if url.startswith(("http://", "https://")):
        return "morta" if verifiche.get(url) in ("404", "410", "403") else "ok"
    locale = url
    for prefisso, cartella in (("special://home/", KODI + os.sep), ("special://profile/", os.path.join(KODI, "userdata") + os.sep)):
        if locale.startswith(prefisso):
            locale = cartella + locale[len(prefisso):]
    return "ok" if os.path.exists(locale.replace("/", os.sep)) or locale.startswith("special://") else "morta"


_MISURE = None


def misura(url):
    """(larghezza, altezza, trasparenza) leggendo solo l'inizio del file."""
    global _MISURE
    with _SCRITTURA:
        if _MISURE is None:
            _MISURE = _cache_json("misure.json")
        if url in _MISURE:
            return _MISURE[url]
    esito = None
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        r = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-400000"})
        with urllib.request.urlopen(r, timeout=25) as f:
            dati = f.read(400001)
        with Image.open(io.BytesIO(dati)) as im:
            alfa = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
            esito = [im.size[0], im.size[1], bool(alfa)]
    except Exception:
        esito = None
    with _SCRITTURA:
        _MISURE[url] = esito
    return esito


def adatta(chiave, c):
    w, h, alfa = c.get("w"), c.get("h"), None
    serve_alfa = chiave in ("clearlogo", "clearart", "discart")
    if c["fonte"] in FIDATE_TRASPARENTI and serve_alfa:
        alfa = True
    if not (w and h) or (serve_alfa and alfa is None):
        m = misura(c["url"])
        if not m:
            return False
        w, h = m[0], m[1]
        alfa = m[2] if alfa is None else alfa
    return bool(h) and REGOLE[chiave](w, h, w / float(h), bool(alfa))


# ------------------------------------------------------------------ riconoscere un titolo

def norm(t):
    t = unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def simile(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() if a and b else 0.0


def accetta(titolo, anno, nomi, anno_trovato):
    s = max([simile(titolo, n) for n in nomi if n] or [0])
    if anno and anno_trovato and str(anno_trovato)[:4].isdigit() and abs(int(anno) - int(str(anno_trovato)[:4])) > 1:
        return s >= 0.97
    return s >= 0.86


def _catalogo():
    try:
        cat = _modulo("catalogo_pc", os.path.join(ADDON, "resources", "lib", "catalogo.py"))
        with io.open(os.path.join(ADDON, "resources", "tmdb.json"), encoding="utf-8") as f:
            serie = json.load(f)
        return {pid: (serie.get(p["segmenti"][0][0]) or {}).get("id") for pid, p in cat.PERCORSI.items() if p.get("segmenti")}
    except Exception as e:
        print("   (catalogo non letto: %s)" % e)
        return {}


def identifica(v, saghe):
    """(tipo, id TMDb, come) per una voce della Videoteca.

    `come` racconta COME e' stato riconosciuto il titolo, e se la cosa e'
    sicura. Serve al rapporto: l'utente (12/09/2026) "ci vuole qualcosa che
    controlla in automatico l'abbinamento, deve corrispondere". Un id preso
    dall'indirizzo o dal catalogo e' certo; un titolo cercato per nome no, e
    se e' andato vicino ma non uguale va guardato da un umano invece di
    finire zitto dentro arte_extra.json.
    Fra i risultati che passano la soglia si sceglie il PIU' somigliante, con
    un premio a chi ha anche l'anno giusto: prima si teneva il primo che
    passava, cioe' quello che TMDb metteva per primo (di solito il piu'
    popolare, non il piu' somigliante)."""
    p = _parametri(v["file"])
    tipo = v["genere"]
    if p.get("tmdb", "").isdigit():
        return tipo, int(p["tmdb"]), {"come": "id nell'indirizzo", "sicuro": True}
    if p.get("azione") in ("consiglio_aggiungi", "consiglio_togli") and p.get("id", "").isdigit():
        return "tv", int(p["id"]), {"come": "id nell'indirizzo", "sicuro": True}
    if p.get("percorso") in saghe and saghe[p["percorso"]] and p.get("azione") != "apri_film":
        return "tv", int(saghe[p["percorso"]]), {"come": "catalogo delle saghe", "sicuro": True}
    titolo = pulisci(v["etichetta"])
    if p.get("titolo_film"):
        titolo = p["titolo_film"]
    migliore = None
    for t in (tipo, "movie" if tipo == "tv" else "tv"):
        d = chiedi("https://api.themoviedb.org/3/search/%s?api_key=%s&language=it-IT&query=%s" % (t, CHIAVE_TMDB, q(titolo)))
        for r in (d or {}).get("results") or []:
            nomi = [r.get("title"), r.get("name"), r.get("original_title"), r.get("original_name")]
            anno_trovato = (r.get("release_date") or r.get("first_air_date") or "")[:4]
            if not accetta(titolo, v.get("anno"), nomi, anno_trovato):
                continue
            s = max([simile(titolo, n) for n in nomi if n] or [0])
            anno_uguale = bool(v.get("anno")) and anno_trovato == str(v.get("anno"))[:4]
            punti = s + (0.05 if anno_uguale else 0)
            if migliore and punti <= migliore[0]:
                continue
            migliore = (punti, t, r["id"],
                        {"come": "cercato per nome", "sicuro": s >= 0.95 or (s >= 0.9 and anno_uguale),
                         "titolo_tmdb": r.get("title") or r.get("name") or "",
                         "somiglianza": round(s, 2), "anno_tmdb": anno_trovato})
    if migliore:
        return migliore[1], migliore[2], migliore[3]
    return tipo, None, {"come": "nessun servizio lo riconosce", "sicuro": False}


# ------------------------------------------------------------------ i servizi

def cand(url, fonte, w=None, h=None):
    return {"url": url, "fonte": fonte, "w": w, "h": h}


def da_tmdb(tipo, tid):
    d = chiedi("https://api.themoviedb.org/3/%s/%s?api_key=%s&append_to_response=images,external_ids"
               "&include_image_language=it,null,en" % (tipo, tid, CHIAVE_TMDB))
    if not d or d.get("_errore"):
        return {}, {}
    im = d.get("images") or {}

    def lista(gruppo, lingue, taglia):
        xs = [x for x in im.get(gruppo) or [] if x.get("iso_639_1") in lingue and x.get("file_path")]
        xs.sort(key=lambda x: (lingue.index(x.get("iso_639_1")), -(x.get("vote_average") or 0)))
        return [cand("https://image.tmdb.org/t/p/%s%s" % (taglia, x["file_path"]), "TMDb", x.get("width"), x.get("height"))
                for x in xs[:4]]

    arte = {"poster": lista("posters", ["it", "en", None], "w780"),
            "keyart": lista("posters", [None], "w780"),
            "fanart": lista("backdrops", [None, "en", "it"], "w1280"),
            "landscape": lista("backdrops", ["it", "en"], "w1280"),
            "clearlogo": lista("logos", ["it", "en", None], "w500")}
    est = d.get("external_ids") or {}
    ids = {"imdb": est.get("imdb_id") or d.get("imdb_id"), "tvdb": est.get("tvdb_id"),
           "titolo": d.get("title") or d.get("name"), "originale": d.get("original_title") or d.get("original_name"),
           "anno": (d.get("release_date") or d.get("first_air_date") or "")[:4],
           "anime": any(g.get("id") == 16 for g in d.get("genres") or []) and
           (d.get("original_language") == "ja" or "JP" in (d.get("origin_country") or []))}
    return arte, ids


def da_fanart(tipo, tid, ids):
    if not CHIAVE_FANART:
        return {}
    if tipo == "movie":
        d = chiedi("https://webservice.fanart.tv/v3/movies/%s?api_key=%s" % (tid, CHIAVE_FANART))
        mappa = {"clearlogo": ("hdmovielogo", "movielogo"), "clearart": ("hdmovieclearart", "movieart"),
                 "discart": ("moviedisc",), "banner": ("moviebanner",), "poster": ("movieposter",),
                 "fanart": ("moviebackground",), "landscape": ("moviethumb",)}
    elif ids.get("tvdb"):
        d = chiedi("https://webservice.fanart.tv/v3/tv/%s?api_key=%s" % (ids["tvdb"], CHIAVE_FANART))
        mappa = {"clearlogo": ("hdtvlogo", "clearlogo"), "clearart": ("hdclearart", "clearart"), "banner": ("tvbanner",),
                 "poster": ("tvposter",), "fanart": ("showbackground",), "landscape": ("tvthumb",)}
    else:
        return {}
    fuori = {}
    for nostro, loro in mappa.items():
        xs = [x for nome in loro for x in ((d or {}).get(nome) or []) if isinstance(x, dict) and x.get("url")]
        xs.sort(key=lambda x: ({"it": 0, "en": 1, "00": 2, "": 2}.get(x.get("lang"), 3), -int(x.get("likes") or 0)))
        fuori[nostro] = [cand(x["url"], "fanart.tv") for x in xs[:3]]
        if nostro == "poster":
            fuori["keyart"] = [cand(x["url"], "fanart.tv") for x in xs if x.get("lang") in ("00", "")][:2]
    return fuori


def da_tvmaze(titolo, anno, ids):
    serie = None
    for campo, valore in (("imdb", ids.get("imdb")), ("thetvdb", ids.get("tvdb"))):
        if valore:
            d = chiedi("https://api.tvmaze.com/lookup/shows?%s=%s" % (campo, valore))
            if isinstance(d, dict) and d.get("id"):
                serie = d
                break
    if not serie:
        for x in chiedi("https://api.tvmaze.com/search/shows?q=%s" % q(titolo)) or []:
            s = (x or {}).get("show") or {} if isinstance(x, dict) else {}
            if accetta(titolo, anno, [s.get("name")], (s.get("premiered") or "")[:4]):
                serie = s
                break
    if not serie:
        return {}
    fuori = collections.defaultdict(list)
    immagini = chiedi("https://api.tvmaze.com/shows/%s/images" % serie["id"])
    for x in sorted(immagini if isinstance(immagini, list) else [], key=lambda x: not x.get("main")):
        nostro = {"poster": "poster", "banner": "banner", "background": "fanart"}.get(x.get("type"))
        r = (x.get("resolutions") or {}).get("original") or {}
        if nostro and r.get("url"):
            fuori[nostro].append(cand(r["url"], "TVmaze", r.get("width"), r.get("height")))
    return fuori


ANILIST = ("query($s:String){Page(perPage:6){media(search:$s,type:ANIME){title{romaji english native} synonyms "
           "startDate{year} coverImage{extraLarge} bannerImage}}}")


def da_anilist(titolo, anno):
    d = chiedi("https://graphql.anilist.co", {"query": ANILIST, "variables": {"s": titolo}})
    for m in ((((d or {}).get("data") or {}).get("Page") or {}).get("media") or []):
        t = m.get("title") or {}
        if accetta(titolo, anno, [t.get("romaji"), t.get("english"), t.get("native")] + (m.get("synonyms") or []),
                   (m.get("startDate") or {}).get("year")):
            fuori = {}
            if (m.get("coverImage") or {}).get("extraLarge"):
                fuori["poster"] = [cand(m["coverImage"]["extraLarge"], "AniList")]
            if m.get("bannerImage"):
                fuori["banner"] = [cand(m["bannerImage"], "AniList")]
            return fuori
    return {}


def da_kitsu(titolo, anno):
    d = chiedi("https://kitsu.app/api/edge/anime?filter%%5Btext%%5D=%s&page%%5Blimit%%5D=6" % q(titolo),
               intestazioni={"Accept": "application/vnd.api+json"})
    for x in (d or {}).get("data") or []:
        a = x.get("attributes") or {}
        nomi = [a.get("canonicalTitle")] + list((a.get("titles") or {}).values()) + (a.get("abbreviatedTitles") or [])
        if accetta(titolo, anno, nomi, (a.get("startDate") or "")[:4]):
            fuori = {}
            if (a.get("posterImage") or {}).get("original"):
                fuori["poster"] = [cand(a["posterImage"]["original"], "Kitsu")]
            if (a.get("coverImage") or {}).get("original"):
                fuori["banner"] = [cand(a["coverImage"]["original"], "Kitsu")]
            return fuori
    return {}


def da_itunes(titolo, anno):
    d = chiedi("https://itunes.apple.com/search?term=%s&country=it&media=movie&entity=movie&limit=8" % q(titolo))
    for r in (d or {}).get("results") or []:
        if accetta(titolo, anno, [r.get("trackName")], (r.get("releaseDate") or "")[:4]) and r.get("artworkUrl100"):
            return {"poster": [cand(r["artworkUrl100"].replace("100x100bb", "1000x1500bb"), "iTunes")]}
    return {}


def da_wikidata(titolo, anno):
    d = chiedi("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=it&uselang=it"
               "&type=item&limit=6&search=%s" % q(titolo))
    for r in (d or {}).get("search") or []:
        if not re.search(r"film|serie|anime|programma|televisiv|cartone|animat|documentar|show|manga",
                         (r.get("description") or "").lower()) or simile(titolo, r.get("label", "")) < 0.86:
            continue
        e = chiedi("https://www.wikidata.org/wiki/Special:EntityData/%s.json" % r["id"], giorni=30)
        claims = ((((e or {}).get("entities") or {}).get(r["id"])) or {}).get("claims") or {}

        def immagine(proprieta):
            for c in claims.get(proprieta) or []:
                v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
                if isinstance(v, str):
                    return "https://commons.wikimedia.org/wiki/Special:FilePath/%s?width=800" % q(v.replace(" ", "_"))
            return ""

        fuori = {}
        if immagine("P154"):
            fuori["clearlogo"] = [cand(immagine("P154"), "Wikidata")]
        if immagine("P3383"):
            fuori["poster"] = [cand(immagine("P3383"), "Wikidata")]
        return fuori
    return {}


def da_jikan(titolo, anno):
    d = chiedi("https://api.jikan.moe/v4/anime?limit=6&q=%s" % q(titolo))
    for a in (d or {}).get("data") or []:
        nomi = [a.get("title"), a.get("title_english"), a.get("title_japanese")] + [t.get("title") for t in a.get("titles") or []]
        da = (((a.get("aired") or {}).get("prop") or {}).get("from") or {}).get("year")
        url = (((a.get("images") or {}).get("jpg")) or {}).get("large_image_url")
        if url and accetta(titolo, anno, nomi, da):
            return {"poster": [cand(url, "Jikan (MyAnimeList)")]}
    return {}


# ------------------------------------------------------------------ una voce

def lavora(v, saghe):
    mancano = [k for k in TUTTE if v["stato"][k] in ("manca", "morta")]
    if not mancano:
        return {"voce": v, "scelte": {}, "mancano": [], "fonti": [], "tmdb": None,
                "come": {"come": "gia' completo", "sicuro": True}}
    tipo, tid, come = identifica(v, saghe)
    titolo = pulisci(v["etichetta"])
    anno = v.get("anno") or ""
    candidati = collections.defaultdict(list)
    fonti = []

    def unisci(nome, trovati):
        fonti.append(nome)
        for k, lista in (trovati or {}).items():
            candidati[k].extend(lista)

    ids = {}
    if tid:
        arte, ids = da_tmdb(tipo, tid)
        unisci("TMDb", arte)
        anno = anno or ids.get("anno", "")
        unisci("fanart.tv", da_fanart(tipo, tid, ids))
    anime = ids.get("anime") or any(re.search(r"(?i)cartoni|saghe|anime", d) for d in v["dove"])

    def manca_ancora(*chiavi):
        return any(k in mancano and not candidati[k] for k in chiavi)

    if tipo == "tv" and manca_ancora("poster", "fanart", "banner"):
        unisci("TVmaze", da_tvmaze(ids.get("titolo") or titolo, anno, ids))
    if anime and manca_ancora("poster", "banner"):
        for nome in dict.fromkeys(x for x in (ids.get("originale"), ids.get("titolo"), titolo) if x):
            unisci("AniList", da_anilist(nome, anno))
            if not manca_ancora("poster", "banner"):
                break
        if manca_ancora("poster", "banner"):
            unisci("Kitsu", da_kitsu(ids.get("titolo") or titolo, anno))
    if tipo == "movie" and manca_ancora("poster"):
        unisci("iTunes", da_itunes(titolo, anno))
    if manca_ancora("poster", "clearlogo"):
        unisci("Wikidata", da_wikidata(ids.get("titolo") or titolo, anno))
    if anime and manca_ancora("poster"):
        unisci("Jikan", da_jikan(ids.get("titolo") or titolo, anno))
    scelte = {}
    for k in mancano:
        for c in candidati[k][:6]:
            if c["url"] and adatta(k, c):
                scelte[k] = c
                break
    return {"voce": v, "scelte": scelte, "mancano": mancano, "fonti": list(dict.fromkeys(fonti)),
            "tmdb": tid, "come": come}


# ------------------------------------------------------------------ uscite

def scrivi(risultati):
    p = os.path.join(ADDON, "resources", "arte_extra.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            dati = json.load(f) or {}
    except (OSError, ValueError):
        dati = {}
    nuove = 0
    for r in risultati:
        if not r["scelte"]:
            continue
        voce = dati.setdefault(ARTE.chiave_indirizzo(r["voce"]["file"]), {})
        for k, c in r["scelte"].items():
            if voce.get(k) != c["url"]:
                voce[k] = c["url"]
                nuove += 1
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dati, f, ensure_ascii=False, indent=0, sort_keys=True)
    return nuove, len(dati)


STILE = """
:root{--sfondo:#f6f5f2;--carta:#fff;--testo:#1d1d1f;--tenue:#6b6b70;--riga:#e4e2dc;--ok:#2e7d32;--no:#c62828;--blu:#1e5aa8}
@media (prefers-color-scheme:dark){:root{--sfondo:#141416;--carta:#1f1f23;--testo:#ececef;--tenue:#9a9aa2;--riga:#34343a;
--ok:#6fcf73;--no:#ff6b6b;--blu:#7fb0ff}}
*{box-sizing:border-box}body{margin:0;padding:24px clamp(16px,4vw,48px);background:var(--sfondo);color:var(--testo);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}h1{font-size:28px;margin:0}h2{margin:34px 0 12px}
.tenue{color:var(--tenue)}.carte{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.carta{background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:14px}.numero{font-size:30px;font-weight:700}
.ok{color:var(--ok)}.no{color:var(--no)}.tabella{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
td,th{border-bottom:1px solid var(--riga);padding:6px 8px;text-align:left;vertical-align:middle}
.barra{background:var(--riga);border-radius:6px;height:10px;min-width:120px;position:relative;overflow:hidden}
.barra span{position:absolute;left:0;top:0;bottom:0;background:var(--ok)}.barra i{position:absolute;top:0;bottom:0;background:var(--blu)}
.galleria{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.tessera{background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:10px;font-size:13px}
.tessera img{max-width:100%;max-height:150px;border-radius:6px;display:block;margin:6px 0;background:#8883}
.pill{display:inline-block;border:1px solid var(--riga);border-radius:99px;padding:0 8px;margin:2px;font-size:12px}
"""


def rapporto(titoli, risultati, cartelle, errori, secondi, nuove, totale_file, solo_controllo):
    per_voce = {r["voce"]["file"]: r for r in risultati}

    def carta(n, testo, classe=""):
        return "<div class='carta'><div class='numero %s'>%s</div><div class='tenue'>%s</div></div>" % (classe, n, testo)

    righe_chiavi = []
    for k in TUTTE:
        prima = sum(1 for v in titoli if v["stato"][k] == "ok")
        trovate = sum(1 for r in risultati if k in r["scelte"])
        n = max(len(titoli), 1)
        righe_chiavi.append("<tr><td>%s</td><td>%d%%</td><td>+%d</td><td><div class='barra'><span style='width:%.1f%%'>"
                            "</span><i style='left:%.1f%%;width:%.1f%%'></i></div></td></tr>"
                            % (k, 100 * prima / n, trovate, 100 * prima / n, 100 * prima / n, 100 * trovate / n))
    posti = collections.defaultdict(lambda: [0, 0, 0])
    for v in titoli:
        r = per_voce.get(v["file"], {"scelte": {}})
        posto = v["dove"][0]
        posti[posto][0] += 1
        posti[posto][1] += 1 if v["stato"]["poster"] != "ok" else 0
        posti[posto][2] += 1 if r["scelte"] else 0
    fonti = collections.Counter(c["fonte"] for r in risultati for c in r["scelte"].values())
    trovate_html = []
    for r in [r for r in risultati if r["scelte"]][:400]:
        immagini = "".join("<div class='tenue'>%s <span class='pill'>%s</span></div><img loading='lazy' src='%s' alt=''>"
                           % (k, html.escape(c["fonte"]), html.escape(c["url"]))
                           for k, c in sorted(r["scelte"].items()) if k in ("poster", "clearlogo", "fanart", "keyart", "banner", "clearart", "discart"))
        trovate_html.append("<div class='tessera'><b>%s</b><div class='tenue'>%s</div>%s</div>"
                            % (html.escape(pulisci(r["voce"]["etichetta"])), html.escape(r["voce"]["dove"][0]), immagini))
    senza = []
    for v in titoli:
        r = per_voce.get(v["file"])
        if not r:
            continue
        restano = [k for k in r["mancano"] if k not in r["scelte"]]
        if not restano:
            continue
        motivo = ("nessun servizio lo riconosce con questo nome" if not r["tmdb"] and not r["scelte"]
                  else "i servizi non hanno immagini adatte")
        if set(restano) & {"clearart", "discart"} and not CHIAVE_FANART:
            motivo += "; clearart e disco li ha solo fanart.tv (serve la chiave gratuita in ~/.fanart-tv-key)"
        senza.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='tenue'>%s</td></tr>"
                     % (html.escape(pulisci(v["etichetta"])), html.escape(v["dove"][0]), ", ".join(restano), html.escape(motivo)))
    # ABBINAMENTI DA CONTROLLARE (12/09/2026). Un'immagine presa per un titolo
    # riconosciuto "per nome" e non identico e' il posto dove nascono le
    # locandine sbagliate: qui si mostrano una per una, con quello che TMDb ha
    # risposto e quanto somigliava, cosi' si vedono invece di scoprirle in TV.
    dubbi = []
    for r in risultati:
        c = r.get("come") or {}
        if not r["scelte"] or c.get("sicuro"):
            continue
        immagine = (r["scelte"].get("poster") or r["scelte"].get("keyart")
                    or r["scelte"].get("landscape") or r["scelte"].get("fanart"))
        dubbi.append("<div class='tessera'><b>%s</b><div class='tenue'>%s</div>"
                     "<div class='tenue'>abbinato a: <b>%s</b>%s - somiglianza %s - %s</div>%s</div>"
                     % (html.escape(pulisci(r["voce"]["etichetta"])), html.escape(r["voce"]["dove"][0]),
                        html.escape(str(c.get("titolo_tmdb", "?"))),
                        (" (%s)" % html.escape(str(c.get("anno_tmdb")))) if c.get("anno_tmdb") else "",
                        c.get("somiglianza", "?"), html.escape(str(c.get("come", ""))),
                        ("<img loading='lazy' src='%s' alt=''>" % html.escape(immagine["url"])) if immagine else ""))
    morte = ["<tr><td>%s</td><td>%s</td><td class='tenue'>%s</td></tr>" % (html.escape(pulisci(v["etichetta"])), k,
                                                                            html.escape(v["arte"].get(k, "")[:120]))
             for v in titoli for k in TUTTE if v["stato"][k] == "morta"]
    pagina = ("<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
              "initial-scale=1'><title>Locandine della Videoteca</title><style>%s</style></head><body>" % STILE
              + "<h1>Le locandine della Videoteca</h1><div class='tenue'>%s - %d cartelle lette in %d secondi%s</div>"
              % (time.strftime("%d/%m/%Y %H:%M"), cartelle, secondi, " - solo controllo" if solo_controllo else "")
              + "<div class='carte'>" + carta(len(titoli), "titoli controllati")
              + carta(sum(1 for v in titoli if all(v["stato"][k] == "ok" for k in PRINCIPALI)), "gia' completi", "ok")
              + carta(sum(1 for r in risultati if r["scelte"]), "titoli migliorati adesso", "ok")
              + carta(nuove, "immagini nuove scritte") + carta(len(morte), "indirizzi morti", "no" if morte else "ok")
              + carta(sum(1 for v in titoli if v["stato"]["poster"] != "ok" and "poster" not in per_voce.get(v["file"], {"scelte": {}})["scelte"]),
                      "ancora senza locandina", "no") + "</div>"
              + "<h2>Copertura per tipo di immagine</h2><p class='tenue'>verde: c'era gia'; blu: trovata adesso</p>"
              + "<div class='tabella'><table><tr><th>immagine</th><th>prima</th><th>trovate</th><th></th></tr>%s</table></div>"
              % "".join(righe_chiavi)
              + "<h2>Da quali servizi</h2><div>%s</div>" % ("".join("<span class='pill'>%s: %d</span>" % (html.escape(f), n)
                                                                    for f, n in fonti.most_common()) or "<span class='tenue'>nessuna ricerca</span>")
              + ("" if CHIAVE_FANART else "<p class='tenue'>fanart.tv non usato: senza la chiave personale gratuita "
                 "(~/.fanart-tv-key) clearart e disco non si trovano da nessun'altra parte.</p>")
              + "<h2>Dove</h2><div class='tabella'><table><tr><th>posto</th><th>titoli</th><th>senza locandina prima</th>"
                "<th>migliorati</th></tr>%s</table></div>"
              % "".join("<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td></tr>" % (html.escape(p), *n) for p, n in sorted(posti.items()))
              + ("<h2>Abbinamenti da controllare</h2><p class='tenue'>Titoli riconosciuti per nome e non "
                 "identici: guarda se l'immagine e' davvero la loro.</p><div class='galleria'>%s</div>"
                 % "".join(dubbi[:200]) if dubbi else "")
              + ("<h2>Trovate adesso</h2><div class='galleria'>%s</div>" % "".join(trovate_html) if trovate_html else "")
              + ("<h2>Ancora senza</h2><div class='tabella'><table><tr><th>titolo</th><th>dove</th><th>manca</th><th>perche'</th></tr>%s"
                 "</table></div>" % "".join(senza[:600]) if senza else "")
              + ("<h2>Indirizzi morti</h2><div class='tabella'><table>%s</table></div>" % "".join(morte[:300]) if morte else "")
              + ("<h2>Cartelle che Kodi non ha aperto</h2><pre>%s</pre>" % html.escape("\n".join("%s  %s" % e for e in errori[:60]))
                 if errori else "")
              + "<p class='tenue'>File dell'add-on: resources/arte_extra.json, %d voci. L'add-on usa queste immagini solo dove "
                "ne manca una; quelle delle righe di TMDb (Netflix, Consigliati, Cinema) le completa anche il servizio sugli "
                "apparecchi, ogni giorno.</p></body></html>" % totale_file)
    p = os.path.join(CARTELLA, "REPORT.html")
    os.makedirs(CARTELLA, exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(pagina)
    return p


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Le locandine che mancano, cercate ovunque")
    a.add_argument("--profondita", type=int, default=3)
    a.add_argument("--massimo-cartelle", type=int, default=400)
    a.add_argument("--solo-controllo", action="store_true")
    a.add_argument("--non-aprire", action="store_true")
    o = a.parse_args(argv[1:])
    inizio = time.time()
    try:
        rpc("JSONRPC.Ping", tempo=10)
    except Exception as e:
        raise SystemExit("Il Kodi del PC non risponde su 127.0.0.1:8080 (%s). E' acceso? La password e' in ~/.kodi-pc-api?" % e)
    print("1/5 scorro la Videoteca sul Kodi del PC...")
    voci, cartelle, errori = scorri(o.profondita, o.massimo_cartelle)
    for v in voci.values():
        v["genere"] = _genere(v)
    titoli = [v for v in voci.values() if v["genere"]]
    print("    %d cartelle, %d voci, %d titoli" % (cartelle, len(voci), len(titoli)))
    print("2/5 controllo le immagini...")
    indirizzi = sorted({u for v in titoli for u in v["arte"].values() if u.startswith(("http://", "https://"))})
    verifiche = verifica_indirizzi(indirizzi)
    for v in titoli:
        v["stato"] = {k: stato_immagine(v["arte"].get(k, ""), verifiche) for k in TUTTE}
    risultati = []
    nuove, totale_file = 0, 0
    if not o.solo_controllo:
        saghe = _catalogo()
        da_cercare = [v for v in titoli if any(v["stato"][k] != "ok" for k in TUTTE)]
        print("3/5 cerco su TMDb, fanart.tv, TVmaze, AniList, Kitsu, iTunes, Wikidata, Jikan (%d titoli)..." % len(da_cercare))
        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            futuri = [ex.submit(lavora, v, saghe) for v in da_cercare]
            for i, f in enumerate(concurrent.futures.as_completed(futuri), 1):
                try:
                    risultati.append(f.result())
                except Exception as e:
                    print("    (un titolo non riuscito: %s)" % e)
                if i % 25 == 0 or i == len(futuri):
                    print("    %d/%d" % (i, len(futuri)))
        _salva_json("misure.json", _MISURE or {})
        print("4/5 scrivo resources/arte_extra.json...")
        nuove, totale_file = scrivi(risultati)
    print("5/5 rapporto...")
    p = rapporto(titoli, risultati, cartelle, errori, time.time() - inizio, nuove, totale_file, o.solo_controllo)
    print("    %d immagini nuove, %s" % (nuove, p))
    if not o.non_aprire:
        sys.path.insert(0, os.path.join(QUI, "atlante"))
        import raccolta
        raccolta.apri_nel_browser(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
