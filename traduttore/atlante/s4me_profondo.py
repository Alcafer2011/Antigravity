# -*- coding: utf-8 -*-
"""s4me VISTO DA DENTRO: canali, siti, server, aggiornamenti - e cosa succede
davvero quando lo si usa sugli apparecchi.

PERCHE' (l'utente, 11/09/2026)
    "fai che questo script esamina profondamente s4me per capire come lavora,
    dove prende i suoi collegamenti, dato che c'e' questo errore server voe, e
    aggiungere se le trovi delle alternative che vengono aggiornate come s4me".
    Il guasto di voe l'ha trovato un'occhiata a mano al registro: i due video
    erano cancellati (404) ma s4me li dava per vivi. Qui la stessa occhiata la
    fa lo script, su tutti i server e tutti gli apparecchi, ogni volta.

COSA GUARDA
  1. DENTRO la copia di ogni apparecchio (copie/<app>/addons/plugin.video.s4me):
     versione e commit, i canali (channels/*.json: acceso, lingue, categorie),
     i domini dei siti (channels.json: "direct" e "findhost"), i server
     (servers/*.json: acceso, quanti schemi di indirizzo riconosce), le
     impostazioni che contano e la lista nera dei server.
  2. IL REGISTRO, riga per riga e filo per filo:
     - ogni tentativo su un server ("Server: voe, Url: ...") e come e' finito:
       video partito, file cancellato, errore del risolutore, riquadro d'errore;
     - le cartelle di s4me che non si sono aperte, per canale e azione (anche i
       nostri indirizzi, decodificati con s4me_link);
     - i canali che vanno in errore, con la riga del loro codice;
     - gli indirizzi in chiaro ("NOT able to load the JSON");
     - le decisioni del nostro canale (server scartati, ricerche lente).
  3. IN RETE (vivo=True):
     - i link dei server presi dal registro: rispondono o sono cancellati?
     - i domini dei canali che usiamo: rispondono?
     - s4me su GitHub (stream4me/addon, ramo stable) e ResolveURL (Gujal00):
       l'ultimo aggiornamento, quali server copre ResolveURL - l'alternativa
       che si aggiorna da sola.
"""

import ast
import collections
import concurrent.futures
import glob
import hashlib
import importlib.util
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
SORGENTE = os.path.join(os.path.dirname(QUI), "plugin.video.saghe")
S4ME = "plugin.video.s4me"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
CACHE = os.path.join(QUI, "uscita", "cache")
IMPOSTAZIONI_CHE_CONTANO = ("autoplay", "default_action", "thread_number", "checklinks", "resolver_dns",
                            "result_mode", "favorites_servers", "quality_priority", "player_mode", "tmdb_active")
ESITI_BRUTTI = ("file cancellato", "errore del risolutore", "riquadro d'errore a schermo", "nessun video")
RIGA = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+ T:(\d+)\s+(\w+)\s+<[^>]+>:\s?(.*)$")
_LINK = None


def _s4me_link():
    global _LINK
    if _LINK is None:
        spec = importlib.util.spec_from_file_location(
            "s4me_link_atlante", os.path.join(SORGENTE, "resources", "lib", "s4me_link.py"))
        _LINK = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_LINK)
    return _LINK


def _json(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _testo(p):
    try:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _impostazioni(p):
    fuori = {}
    for m in re.finditer(r'<setting id="([^"]+)"[^>]*?(?:/>|>([^<]*)</setting>)', _testo(p)):
        fuori[m.group(1)] = m.group(2) or ""
    return fuori


def _secondi(a, b):
    try:
        return abs(time.mktime(time.strptime(b, "%Y-%m-%d %H:%M:%S")) - time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S")))
    except ValueError:
        return 1e9


# ---------------------------------------------------------------------------- 1. dentro la copia

def _dentro(copia):
    s4 = os.path.join(copia, "addons", S4ME)
    if not os.path.isdir(s4):
        return {"installato": False}
    versione = re.search(r'<addon\b[^>]*\bversion="([^"]+)"', _testo(os.path.join(s4, "addon.xml")))
    domini = _json(os.path.join(s4, "channels.json")) or {}
    utente = os.path.join(copia, "userdata", "addon_data", S4ME)
    canali = {}
    for p in sorted(glob.glob(os.path.join(s4, "channels", "*.json"))):
        c = _json(p) or {}
        cid = c.get("id") if isinstance(c.get("id"), str) else os.path.basename(p)[:-5]
        voce = {"nome": c.get("name", cid), "acceso": bool(c.get("active")), "lingue": c.get("language") or [],
                "categorie": c.get("categories") or [], "ha_codice": os.path.exists(p[:-5] + ".py"),
                "dominio": (domini.get("direct") or {}).get(cid) or (domini.get("findhost") or {}).get(cid) or ""}
        dati = _json(os.path.join(utente, "settings_channels", "%s_data.json" % cid)) or {}
        imp = dati.get("settings") if isinstance(dati.get("settings"), dict) else dati
        if isinstance(imp, dict) and "include_in_global_search" in imp:
            voce["nella_ricerca"] = bool(imp.get("include_in_global_search"))
        canali[cid] = voce
    server = {}
    for p in sorted(glob.glob(os.path.join(s4, "servers", "*.json"))):
        v = _json(p) or {}
        # in alcuni server "id" non e' un nome ma un blocco di impostazioni: vale il nome del file
        sid = (v.get("id") if isinstance(v.get("id"), str) else os.path.basename(p)[:-5]).lower()
        schemi = (v.get("find_videos") or {}).get("patterns") or []
        server[sid] = {"nome": v.get("name", sid), "acceso": v.get("active", True) is not False,
                       "schemi": len(schemi), "ha_codice": os.path.exists(p[:-5] + ".py"),
                       "domini": sum(x.get("pattern", "").count("|") + 1 for x in schemi if isinstance(x, dict))}
    imp = _impostazioni(os.path.join(utente, "settings.xml"))
    nera = ((_json(os.path.join(utente, "settings_servers", "servers_data.json")) or {}).get("settings") or {}).get("black_list") or []
    lesaghe = os.path.join(s4, "channels", "lesaghe.py")
    return {"installato": True, "versione": versione.group(1) if versione else "?",
            "commit": _testo(os.path.join(s4, "last_commit.txt")).strip()[:40],
            "canali": canali, "server": server, "lista_nera": nera,
            "impostazioni": {k: imp.get(k) for k in IMPOSTAZIONI_CHE_CONTANO if k in imp},
            "domini": {"diretti": len(domini.get("direct") or {}), "da_cercare": len(domini.get("findhost") or {})},
            "lesaghe_md5": hashlib.md5(open(lesaghe, "rb").read()).hexdigest() if os.path.exists(lesaghe) else "",
            "resolveurl": os.path.isdir(os.path.join(copia, "addons", "script.module.resolveurl"))}


# ---------------------------------------------------------------------------- 2. il registro

def _registro(cartella_log):
    """Il registro filo per filo. Ogni cosa contata due volte: in tutto e ADESSO
    (dopo l'ultimo "Starting Kodi" di kodi.log). Lo storico conta meno: le ricerche
    fallite del Raspberry prima della correzione non sono un guasto di oggi."""
    righe = []
    vecchio = _testo(os.path.join(cartella_log, "kodi.old.log"))
    if vecchio:
        righe.extend((r, False) for r in vecchio.splitlines())
    attuale = _testo(os.path.join(cartella_log, "kodi.log")).splitlines()
    avvio = max([i for i, r in enumerate(attuale) if "Starting Kodi" in r] or [0])
    righe.extend((r, i >= avvio) for i, r in enumerate(attuale))
    tentativi, aperti = [], {}
    cartelle_fallite, cartelle_adesso = collections.Counter(), collections.Counter()
    canali_errore = {}
    in_chiaro = in_chiaro_adesso = 0
    scartati = collections.Counter()
    ricerche, aggiornamenti = [], []
    traccia = None                       # [canali visti nel Traceback, ultima riga d'errore, quando, adesso]

    def _chiudi_traccia():
        if not traccia or not traccia[0]:
            return
        for canale, riga in traccia[0]:
            e = canali_errore.setdefault(canale, {"volte": 0, "volte_adesso": 0, "righe": set(), "errore": "", "ultima": ""})
            e["volte"] += 1
            e["volte_adesso"] += 1 if traccia[3] else 0
            e["righe"].add(riga)
            e["errore"] = traccia[1] or e["errore"]
            e["ultima"] = traccia[2]

    for r, adesso in righe:
        m = RIGA.match(r)
        if not m:
            if traccia is not None:
                c = re.search(r'channels[\\/]+(\w+)\.py", line (\d+)', r)
                if c and c.group(1) not in ("lesaghe", "abbonamenti"):
                    traccia[0].add((c.group(1), int(c.group(2))))
                if re.match(r"\s*[\w.]+(Error|Exception)\b", r):
                    traccia[1] = r.strip()[:200]
            continue
        _chiudi_traccia()
        traccia = None
        quando, filo, _livello, msg = m.groups()
        if "Traceback" in msg:
            traccia = [set(), "", quando, adesso]
        s = re.search(r"Server: ([\w.-]+), Url: (\S+)", msg)
        if s:
            t = {"server": s.group(1).lower(), "url": s.group(2), "quando": quando, "filo": filo,
                 "esito": "sconosciuto", "adesso": adesso}
            tentativi.append(t)
            aperti[filo] = t
            continue
        t = aperti.get(filo)
        if t:
            if "doesn't exist" in msg:
                t["esito"] = "file cancellato"
                aperti.pop(filo, None)
            elif "Error getting url in free mode" in msg or "Could not import server" in msg:
                t["esito"] = "errore del risolutore"
                aperti.pop(filo, None)
        if "Loading skin file: DialogConfirm.xml" in msg or "Loading skin file: DialogOK.xml" in msg:
            vicini = [x for x in tentativi if x["esito"] == "sconosciuto" and _secondi(x["quando"], quando) <= 6]
            if vicini:
                vicini[-1]["esito"] = "riquadro d'errore a schermo"
        if re.search(r"VideoPlayer::OpenFile|CVideoPlayer::OpenFile|Opening stream|Creating InputStream", msg):
            vicini = [x for x in tentativi if x["esito"] == "sconosciuto" and _secondi(x["quando"], quando) <= 60]
            if vicini:
                vicini[-1]["esito"] = "video partito"
        if "Error getting plugin://plugin.video.s4me" in msg:
            campi = _s4me_link().leggi(msg.split("Error getting ", 1)[1].strip())
            chiave = (campi.get("channel", "?"), campi.get("action", "?"))
            cartelle_fallite[chiave] += 1
            if adesso:
                cartelle_adesso[chiave] += 1
        if "**NOT** able to load the JSON" in msg:
            in_chiaro += 1
            in_chiaro_adesso += 1 if adesso else 0
        z = re.search(r"Le Saghe: server (\S+) scartato", msg)
        if z:
            scartati[z.group(1)] += 1
        if "Le Saghe: ricerca di" in msg or "Le Saghe: film " in msg:
            ricerche.append({"quando": quando, "testo": msg.split("Le Saghe: ", 1)[1][:240]})
        if "updater.check" in msg:
            aggiornamenti.append({"quando": quando, "testo": msg.split("]:", 1)[-1].strip()[:140]})
    _chiudi_traccia()

    for t in tentativi:
        if t["esito"] == "sconosciuto" and t["filo"] not in aperti:
            t["esito"] = "nessun video"
    per_server = {}
    for t in tentativi:
        s = per_server.setdefault(t["server"], {"tentativi": 0, "tentativi_adesso": 0, "esiti": collections.Counter(),
                                                "brutti_adesso": 0, "indirizzi": []})
        s["tentativi"] += 1
        s["esiti"][t["esito"]] += 1
        if t["adesso"]:
            s["tentativi_adesso"] += 1
            s["brutti_adesso"] += 1 if t["esito"] in ESITI_BRUTTI else 0
        if t["url"] not in s["indirizzi"]:
            s["indirizzi"].append(t["url"])
    for s in per_server.values():
        s["esiti"] = dict(s["esiti"])
        s["indirizzi"] = s["indirizzi"][-25:]
        s["brutti"] = sum(v for k, v in s["esiti"].items() if k in ESITI_BRUTTI)
    for e in canali_errore.values():
        e["righe"] = sorted(e["righe"])
    return {"righe": len(righe), "server": per_server, "tentativi": tentativi[-200:],
            "cartelle_fallite": [{"canale": c, "azione": a, "volte": n, "volte_adesso": cartelle_adesso.get((c, a), 0)}
                                 for (c, a), n in cartelle_fallite.most_common()],
            "canali_in_errore": canali_errore, "indirizzi_in_chiaro": in_chiaro,
            "indirizzi_in_chiaro_adesso": in_chiaro_adesso,
            "scartati_dal_nostro_canale": dict(scartati), "ricerche": ricerche[-30:],
            "aggiornamenti": aggiornamenti[-5:]}


# ---------------------------------------------------------------------------- 3. in rete

def _stato_http(indirizzo, tempo=12):
    for metodo in ("HEAD", "GET"):
        try:
            r = urllib.request.Request(indirizzo, method=metodo, headers={"User-Agent": UA, "Range": "bytes=0-1023"})
            with urllib.request.urlopen(r, timeout=tempo) as f:
                return str(f.status)
        except urllib.error.HTTPError as e:
            if metodo == "GET" or e.code not in (403, 405, 501):
                return str(e.code)
        except Exception as e:
            if metodo == "GET":
                return "rete: %s" % str(e)[:60]
    return "?"


def _in_parallelo(indirizzi):
    with concurrent.futures.ThreadPoolExecutor(16) as ex:
        return dict(zip(indirizzi, ex.map(_stato_http, indirizzi)))


def _github(indirizzo, cache, ore=12):
    voce = cache.get(indirizzo)
    if voce and time.time() - voce.get("quando", 0) < ore * 3600:
        return voce.get("dati")
    try:
        r = urllib.request.Request(indirizzo, headers={"User-Agent": "atlante-videoteca", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(r, timeout=30) as f:
            dati = json.loads(f.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"errore": str(e)[:120]}
    cache[indirizzo] = {"quando": time.time(), "dati": dati}
    return dati


def _a_monte():
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "github.json")
    cache = _json(p) or {}
    fuori = {}
    testa = _github("https://api.github.com/repos/stream4me/addon/commits?sha=stable&per_page=1", cache)
    if isinstance(testa, list) and testa:
        fuori["s4me_ultimo"] = {"commit": testa[0]["sha"], "data": testa[0]["commit"]["committer"]["date"],
                                "messaggio": testa[0]["commit"]["message"][:120]}
    srv = _github("https://api.github.com/repos/stream4me/addon/commits?sha=stable&path=servers&per_page=8", cache)
    if isinstance(srv, list):
        fuori["s4me_server_toccati"] = [{"data": c["commit"]["committer"]["date"][:10], "messaggio": c["commit"]["message"][:90]} for c in srv]
    plug = _github("https://api.github.com/repos/Gujal00/ResolveURL/contents/script.module.resolveurl/lib/resolveurl/plugins", cache, ore=48)
    if isinstance(plug, list):
        fuori["resolveurl_plugin"] = sorted(x["name"][:-3] for x in plug if x.get("name", "").endswith(".py") and not x["name"].startswith("__"))
    ru = _github("https://api.github.com/repos/Gujal00/ResolveURL/commits?per_page=10", cache)
    if isinstance(ru, list):
        fuori["resolveurl_ultimi"] = [{"data": c["commit"]["committer"]["date"][:10], "messaggio": c["commit"]["message"][:90]} for c in ru]
    try:
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass
    return fuori


def _alternativa(server, plugin):
    """Il plugin di ResolveURL che copre questo server di s4me, se c'e'."""
    s = re.sub(r"[^a-z]", "", server.lower())
    for p in plugin or []:
        q = re.sub(r"[^a-z]", "", p.lower())
        if len(s) >= 3 and (q == s or q.startswith(s) or (len(q) >= 4 and s.startswith(q))):
            return p
    return ""


# ---------------------------------------------------------------------------- insieme

def _liste_del_nostro_canale():
    """CANALI_PER_TIPO, CANALI_FILM, CANALI_ROTTI letti da lesaghe.py (senza eseguirlo)."""
    p = os.path.join(SORGENTE, "resources", "canale", "lesaghe.py")
    fuori = {"testo_md5": hashlib.md5(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""}
    try:
        albero = ast.parse(_testo(p))
    except SyntaxError:
        return fuori
    for n in albero.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if n.targets[0].id in ("CANALI_PER_TIPO", "CANALI_FILM", "CANALI_ROTTI", "CANALI"):
                try:
                    fuori[n.targets[0].id] = ast.literal_eval(n.value)
                except ValueError:
                    pass
    return fuori


def analizza(copie, apparecchi=("pc", "box", "pi"), vivo=False):
    nostro = _liste_del_nostro_canale()
    fuori = {"nostro_canale": {k: (sorted(v) if isinstance(v, set) else v) for k, v in nostro.items()}, "apparecchi": {}}
    for app in apparecchi:
        copia = os.path.join(copie, app)
        d = _dentro(copia)
        if d.get("installato"):
            d["registro"] = _registro(os.path.join(copia, "log"))
        fuori["apparecchi"][app] = d
    if vivo:
        a_monte = _a_monte()
        fuori["a_monte"] = a_monte
        link = sorted({u for d in fuori["apparecchi"].values() for s in (d.get("registro") or {}).get("server", {}).values()
                       for u in s["indirizzi"][-8:]})
        usati = set()
        for v in nostro.get("CANALI_PER_TIPO", {}).values():
            usati.update(v)
        usati.update(nostro.get("CANALI_FILM", []))
        domini = sorted({c["dominio"] for d in fuori["apparecchi"].values() for cid, c in (d.get("canali") or {}).items()
                         if cid in usati and c.get("dominio", "").startswith("http")})
        risposte = _in_parallelo(link + domini)
        fuori["link_provati"] = {u: risposte[u] for u in link}
        fuori["domini_provati"] = {u: risposte[u] for u in domini}
        for d in fuori["apparecchi"].values():
            for sid, s in ((d.get("registro") or {}).get("server") or {}).items():
                s["alternativa_resolveurl"] = _alternativa(sid, a_monte.get("resolveurl_plugin"))
                s["link_cancellati"] = sum(1 for u in s["indirizzi"] if risposte.get(u) in ("404", "410"))
                s["link_provati"] = sum(1 for u in s["indirizzi"] if u in risposte)
    return fuori


def problemi(dati):
    """Dai dati a problemi per l'elenco unico dell'atlante (regole.py)."""
    fuori = []

    def p(livello, tipo, area, titolo, dettaglio="", dove=None, rimedio=""):
        fuori.append({"livello": livello, "tipo": tipo, "area": area, "titolo": titolo,
                      "dettaglio": dettaglio, "dove": dove or [], "rimedio": rimedio})

    nostro = dati.get("nostro_canale") or {}
    usati = set()
    for v in (nostro.get("CANALI_PER_TIPO") or {}).values():
        usati.update(v)
    usati.update(nostro.get("CANALI_FILM") or [])
    rotti = set(nostro.get("CANALI_ROTTI") or [])
    a_monte = dati.get("a_monte") or {}
    for app, d in (dati.get("apparecchi") or {}).items():
        if not d.get("installato"):
            p("alto", "malfunzionamento", app, "s4me non e' installato",
              "Senza s4me la Videoteca non trova nessun video e la ricerca sui siti non parte.", [], "Installare s4me.")
            continue
        mancanti = sorted(c for c in usati if c not in d["canali"])
        spenti = sorted(c for c in usati if c in d["canali"] and not d["canali"][c]["acceso"] and c not in rotti)
        if mancanti:
            p("alto", "malfunzionamento", app, "Canali delle nostre liste che s4me non ha (%d)" % len(mancanti),
              "Mancano: %s." % ", ".join(mancanti), ["resources/canale/lesaghe.py (CANALI_PER_TIPO, CANALI_FILM)"],
              "Toglierli dalle liste: s4me li ha eliminati.")
        if spenti:
            p("basso", "manutenzione", app, "Canali delle nostre liste spenti da s4me stesso (%d)" % len(spenti),
              "Spenti: %s. Li spegne s4me quando il sito muore; il nostro canale li salta da solo (lesaghe._acceso) "
              "e li riprende quando s4me li riaccende." % ", ".join(spenti),
              ["resources/canale/lesaghe.py (CANALI_PER_TIPO, CANALI_FILM)"], "")
        if d["lesaghe_md5"] and d["lesaghe_md5"] != nostro.get("testo_md5"):
            p("alto", "incoerenza", app, "Il nostro canale dentro s4me e' una versione diversa dal sorgente",
              "channels/lesaghe.py sull'apparecchio non coincide con resources/canale/lesaghe.py: gira il codice di prima.",
              [], "Riavviare Kodi (il custode lo ricopia) o rilanciare servi.py.")
        if not d.get("resolveurl"):
            p("medio", "malfunzionamento", app, "ResolveURL non installato: nessuna seconda opinione sui server",
              "Quando un server di s4me non da' il video, il nostro canale prova ResolveURL (si aggiorna da solo dal suo "
              "repository). Qui non c'e'.", [], "python servi.py %s (lo installa col suo repository)." % app)
        imp = d.get("impostazioni") or {}
        if imp.get("autoplay") not in (None, "true"):
            p("medio", "malfunzionamento", app, "s4me senza autoplay: a ogni episodio chiede di scegliere il server",
              "autoplay=%s" % imp.get("autoplay"), [], "RunScript(plugin.video.saghe,regola_s4me,muto) o il servizio all'avvio.")
        reg = d.get("registro") or {}
        for sid, s in sorted((reg.get("server") or {}).items(), key=lambda x: -x[1]["brutti"]):
            if s["tentativi"] >= 1 and s["brutti"] and s["brutti"] >= s["tentativi"] / 2.0:
                schermo = s["esiti"].get("riquadro d'errore a schermo", 0)
                if not s.get("brutti_adesso"):
                    # solo prima dell'ultimo avvio: si racconta, non si allarma
                    p("info", "malfunzionamento", app, "Server %s: video che non partivano (storico, prima dell'ultimo avvio)" % sid,
                      "%d tentativi, %d andati male: %s." % (s["tentativi"], s["brutti"], ", ".join("%s %d" % kv for kv in s["esiti"].items())),
                      s["indirizzi"][-3:], "Dal 11/09/2026 il nostro canale prova i server prima di mostrarli (lesaghe._server_vivi).")
                    continue
                dettaglio = "%d tentativi, %d andati male: %s." % (s["tentativi"], s["brutti"],
                                                                    ", ".join("%s %d" % kv for kv in s["esiti"].items()))
                if s.get("link_provati"):
                    dettaglio += " Link provati adesso: %d, cancellati (404/410): %d." % (s["link_provati"], s["link_cancellati"])
                alt = s.get("alternativa_resolveurl")
                p("alto" if schermo else "medio", "malfunzionamento", app,
                  "Server %s: i suoi video non partono (%d su %d)" % (sid, s["brutti"], s["tentativi"]), dettaglio,
                  s["indirizzi"][-3:],
                  "Il nostro canale ora prova i server PRIMA di mostrarli (lesaghe._server_vivi) e scarta quelli morti; "
                  + ("ResolveURL ha un risolutore alternativo: %s." % alt if alt else "ResolveURL non ha un risolutore per questo server."))
        for c in reg.get("cartelle_fallite") or []:
            if c["canale"] in ("lesaghe", "abbonamenti"):
                continue
            tastiera = c["azione"] in ("search", "Search")
            if not c.get("volte_adesso"):
                p("info", "malfunzionamento", app, "Cartella di s4me che non si apriva: %s / %s (storico, %d volte)"
                  % (c["canale"], c["azione"], c["volte"]), "Prima dell'ultimo avvio di Kodi.", [],
                  "Le ricerche ora passano da ricerca_siti.py -> lesaghe.cerca_siti." if tastiera else "")
                continue
            p("alto" if tastiera else "basso", "malfunzionamento", app,
              "Cartella di s4me che non si apre: %s / %s (%d volte)" % (c["canale"], c["azione"], c["volte"]),
              "action=search da un indirizzo riapre la TASTIERA (launcher.search) invece di usare il testo gia' scritto; "
              "action=Search non esiste." if tastiera else "Il canale non ha restituito niente o e' andato in errore.",
              [], "Le ricerche passano da ricerca_siti.py -> lesaghe.cerca_siti." if tastiera else "")
        for canale, e in sorted((reg.get("canali_in_errore") or {}).items(), key=lambda x: -x[1]["volte"]):
            p("info" if not e.get("volte_adesso") else ("basso" if canale in rotti else "medio"), "instabilita", app,
              "Il canale %s di s4me va in errore (%d volte)" % (canale, e["volte"]),
              "%s (ultima volta %s)" % (e["errore"] or "errore Python", e["ultima"]),
              ["channels/%s.py:%s" % (canale, r) for r in e["righe"][:5]],
              "E' codice di s4me: si ripara col suo aggiornamento. Se e' nelle nostre liste e continua, "
              "metterlo in CANALI_ROTTI di lesaghe.py cosi' non fa perdere tempo.")
        if reg.get("indirizzi_in_chiaro"):
            p("basso" if reg.get("indirizzi_in_chiaro_adesso") else "info", "incoerenza", app,
              "Indirizzi di s4me scritti in chiaro (%d errori nel registro, %d dopo l'ultimo avvio)"
              % (reg["indirizzi_in_chiaro"], reg.get("indirizzi_in_chiaro_adesso", 0)),
              "s4me si aspetta la testa codificata (Item.tourl): in chiaro funziona ma scrive un Traceback a ogni apertura. "
              "Se il conto non scende dopo l'aggiornamento, qualche indirizzo vecchio e' rimasto (menu, preferiti, videoteca di s4me).",
              [], "resources/lib/s4me_link.py per ogni indirizzo nuovo.")
        commit, testa = d.get("commit"), (a_monte.get("s4me_ultimo") or {}).get("commit", "")
        if commit and testa and not testa.startswith(commit[:10]):
            p("medio", "manutenzione", app, "s4me non e' all'ultima versione del suo GitHub",
              "Commit locale %s, su GitHub %s (%s: %s)." % (commit[:10], testa[:10], a_monte["s4me_ultimo"]["data"][:10],
                                                          a_monte["s4me_ultimo"]["messaggio"]),
              [], "s4me si aggiorna da solo all'avvio (updater.check): controllare che la rete arrivi a api.github.com.")
    morti = [u for u, s in (dati.get("domini_provati") or {}).items() if not s.startswith(("2", "3", "403"))]
    if morti:
        p("medio", "malfunzionamento", "addon", "Siti usati dal nostro canale che non rispondono (%d)" % len(morti),
          "\n".join("%s -> %s" % (u, dati["domini_provati"][u]) for u in morti), [],
          "Di solito il sito ha cambiato dominio e s4me lo insegue col suo aggiornamento (channels.json).")
    return fuori
