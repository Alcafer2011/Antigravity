# -*- coding: utf-8 -*-
"""Le locandine per Documentari, Cucina e YouTube.

IL GUASTO (utente, 07/09): "TV in diretta non appare nessuna locandina,
documentari idem, cucina idem, i tuoi canali YouTube idem".
Non era un guasto di disegno: quelle righe mettevano l'ICONA DELLA
VIDEOTECA su ogni voce. Centoventinove quadratini identici, che in una
riga di locandine e' come non averne nessuna.

CHE COSA SONO QUELLE VOCI, che non sono tutte uguali
    - le FONTI          RaiPlay, Discovery+, La7, Pluto TV, Paramount
    - i TEMI            "Fisica", "Marte", "Animali selvatici" - sono
                        ricerche, non esiste una locandina
    - i PROGRAMMI       "Cash or Trash", "Affari al buio", "Come e' fatto"
                        - questi sono programmi TV veri, e TMDB ha il
                        loro poster
    - i CANALI YOUTUBE  hanno l'immagine del canale nella loro pagina

QUINDI
    Ai programmi si da' il poster di TMDB, ai canali YouTube l'immagine
    del canale. I temi e le fonti restano com'erano: non si inventa una
    locandina a "Fisica quantistica" per riempire un buco.

LA SOGLIA, e perche' c'e'
    Cercando "Marte" su TMDB esce qualcosa: un film, una serie, qualunque
    cosa. Metterla sarebbe peggio che lasciare l'icona, perche' sembrerebbe
    giusta. Si accetta il risultato solo se il titolo trovato CONTIENE
    tutte le parole di quello cercato - la stessa misura che ha risolto
    "Terra Nova al posto di Terra amara" nel canale delle saghe.

QUANDO GIRA
    Nel servizio, in sottofondo, una volta al mese: sono ~190 voci e una
    chiamata l'una. Il risultato sta in `copertine.json` e le righe lo
    leggono senza mai toccare la rete.
"""

import io
import json
import os
import re
import time
import unicodedata

import xbmcvfs

from resources.lib.tmdb import CHIAVE as CHIAVE_TMDB  # la chiave sta in un posto solo
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

DURATA = 30 * 24 * 60 * 60          # un mese: questi elenchi cambiano piano

# Le parole che non contano quando si confrontano due titoli.
VUOTE = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a",
         "da", "in", "con", "su", "per", "tra", "fra", "e", "the", "of",
         "and", "del", "della", "dei", "degli", "delle", "al", "alla"}


def _dati():
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    return c


def _file():
    return os.path.join(_dati(), "copertine.json")


def leggi():
    """Le copertine gia' trovate: {etichetta: indirizzo}. Mai la rete."""
    try:
        with io.open(_file(), encoding="utf-8") as f:
            return (json.load(f) or {}).get("voci") or {}
    except Exception:
        return {}


def scaduto():
    try:
        with io.open(_file(), encoding="utf-8") as f:
            return (time.time() - (json.load(f) or {}).get("quando", 0)) > DURATA
    except Exception:
        return True


def _parole(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(x for x in s if not unicodedata.combining(x)).lower()
    p = set(re.sub(r"[^a-z0-9]+", " ", s).split())
    return (p - VUOTE) or p


def _combacia(trovato, voluto):
    """True solo se il titolo trovato contiene TUTTE le parole cercate."""
    pv = _parole(voluto)
    return bool(pv) and pv <= _parole(trovato)


def _chiedi(url, testo=False):
    import urllib.request
    try:
        r = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(r, timeout=15) as f:
            grezzo = f.read().decode("utf-8", "ignore")
        return grezzo if testo else json.loads(grezzo)
    except Exception:
        return "" if testo else {}


def _poster_tmdb(titolo, doc_ok=False):
    """Il poster di un programma / film / persona.

    Prima la ricerca in italiano, poi in inglese (i programmi Discovery e
    National Geographic su TMDB stanno spesso solo col titolo originale).
    Con `doc_ok` (per i temi: "Deserti", "Vulcani") si accetta anche il
    primo risultato che sia un DOCUMENTARIO con locandina, senza pretendere
    che il titolo contenga tutte le parole: un documentario sui deserti va
    bene per la tessera "Deserti".
    """
    from urllib.parse import quote
    IMG = "https://image.tmdb.org/t/p/w500%s"
    for lingua in ("it-IT", "en-US"):
        d = _chiedi("https://api.themoviedb.org/3/search/multi"
                    "?api_key=%s&language=%s&query=%s"
                    % (CHIAVE_TMDB, lingua, quote(titolo)))
        risultati = (d.get("results") or [])[:8]
        # 1) match esatto sulle parole (come prima)
        for r in risultati:
            nome = r.get("name") or r.get("title") or ""
            if r.get("poster_path") and _combacia(nome, titolo):
                return IMG % r["poster_path"]
        # 2) una PERSONA (uno chef): meglio la SUA foto che il poster del
        #    programma dove fa il giudice (l'utente non vuole "MasterChef"
        #    sotto il nome di Iginio Massari).
        for r in risultati:
            if r.get("media_type") == "person" and _combacia(
                    r.get("name") or "", titolo):
                if r.get("profile_path"):
                    return IMG % r["profile_path"]
                for k in (r.get("known_for") or []):
                    if k.get("poster_path"):
                        return IMG % k["poster_path"]
        # 3) tema: il primo documentario con locandina
        if doc_ok:
            for r in risultati:
                if (r.get("poster_path")
                        and r.get("media_type") in ("tv", "movie")
                        and 99 in (r.get("genre_ids") or [])):
                    return IMG % r["poster_path"]
    return ""


def _immagine_youtube(indirizzo):
    """L'immagine di un canale YouTube, presa dalla sua pagina.

    Non serve nessuna chiave: la pagina del canale dichiara la propria
    immagine in `og:image`, che e' esattamente quella che si vede in cima
    al canale.
    """
    m = re.search(r"(UC[0-9A-Za-z_-]{20,})", indirizzo or "")
    if not m:
        return ""
    pagina = _chiedi("https://www.youtube.com/channel/%s" % m.group(1),
                     testo=True)
    m2 = re.search(r'<meta property="og:image" content="([^"]+)"', pagina)
    return m2.group(1) if m2 else ""


# I SERVIZI, e perche' NON si cercano su TMDB.
# "Discovery+", "Pluto TV", "Paramount" sono servizi, non programmi: TMDB ci
# attacca sopra il primo titolo che contiene quella parola e viene fuori una
# locandina a caso che sembra giusta (successo davvero, alla prima prova).
# Pero' lasciarli senza immagine li rende quadrati vuoti in mezzo alle
# locandine. La risposta giusta non e' un poster: e' il LORO LOGO, preso dal
# loro stesso sito. Non serve nessuna chiave.
LOGHI = {
    "RaiPlay": "raiplay.it",
    "Discovery+": "discoveryplus.com",
    "La7": "la7.it",
    "Pluto TV": "pluto.tv",
    "Paramount": "paramountplus.com",
    "Mediaset Infinity": "mediasetinfinity.mediaset.it",
    "YouTube": "youtube.com",
    "Netflix": "netflix.com",
    "Prime Video": "primevideo.com",
}


def _logo_servizio(etichetta):
    """Il logo di un servizio, dal suo sito. Vuoto se non lo conosciamo."""
    # Le etichette a volte hanno una parentesi: "Discovery+ (Real Time)",
    # "RaiPlay" con o senza spazi. Si prova esatta, poi senza parentesi.
    dominio = (LOGHI.get(etichetta)
               or LOGHI.get(re.sub(r"\s*\(.*?\)\s*$", "", etichetta).strip()))
    if not dominio:
        return ""
    # L'indirizzo delle icone dei siti: non e' un'API con chiave, e' il
    # servizio che usa il browser per mettere l'iconcina nelle schede.
    return ("https://www.google.com/s2/favicons?domain=%s&sz=256" % dominio)


def _poster_tvmaze(titolo):
    """Seconda fonte per i programmi, quando TMDB non ha niente.

    TVmaze conosce la TV generalista e i documentari molto meglio di TMDB,
    non vuole nessuna chiave, e risponde in fretta. Vale la stessa soglia:
    si accetta solo se il titolo trovato contiene tutte le parole cercate.
    """
    from urllib.parse import quote
    d = _chiedi("https://api.tvmaze.com/singlesearch/shows?q=%s"
                % quote(titolo))
    if not isinstance(d, dict):
        return ""
    nome = d.get("name") or ""
    img = (d.get("image") or {}).get("original") or ""
    return img if img and _combacia(nome, titolo) else ""


def calcola(scaffale_di):
    """Cerca le copertine mancanti. `scaffale_di` e' scoperte.scaffale.

    Torna quante ne ha trovate. Riparte da quelle gia' note, cosi' un
    ricalcolo non rifa' tutto il lavoro.
    """
    trovate = dict(leggi())
    nuove = 0
    for quale in ("documentari", "cucina", "youtube"):
        try:
            gruppi = scaffale_di(quale)
        except Exception:
            continue
        for _, voci in gruppi:
            for etichetta, indirizzo, _nota, tipo in voci:
                if etichetta in trovate:
                    continue
                # LE FONTI NON SI CERCANO SU TMDB.
                # "Discovery+", "Pluto TV", "Paramount" sono servizi, non
                # programmi: TMDB ci attacca sopra il primo titolo che
                # contiene quella parola, e viene fuori una locandina a
                # caso che sembra giusta. (Successo alla prima prova.)
                # Stessa cosa per i canali in diretta.
                if tipo.startswith("diretta:"):
                    continue
                if tipo == "catalogo":
                    # Non un poster: il logo del servizio.
                    img = _logo_servizio(etichetta)
                elif quale == "youtube":
                    # I canali veri hanno un UC... nell'indirizzo e la loro
                    # immagine; le RICERCHE no - per quelle si prova come
                    # per un programma, e se non si trova resta l'icona.
                    img = (_immagine_youtube(indirizzo)
                           or _poster_tmdb(etichetta)
                           or _poster_tvmaze(etichetta))
                else:
                    # Si cerca la QUERY pulita (`cerca:<q>`), non l'etichetta
                    # decorata: "American Chopper (le moto Harley)" come
                    # ricerca non becca niente, "american chopper" si'.
                    # E per i temi si toglie il "documentario/cucina/ricette"
                    # davanti, che nessun titolo contiene.
                    q = (tipo.split(":", 1)[1]
                         if tipo.startswith("cerca:") else etichetta)
                    qp = re.sub(r"^(documentari[oi]|cucina|ricett[ae])\s+",
                                "", q, flags=re.I).strip() or q
                    img = (_poster_tmdb(q)
                           or (_poster_tmdb(qp) if qp != q else "")
                           or _poster_tvmaze(q)
                           or (_poster_tvmaze(qp) if qp != q else "")
                           # ultimo tentativo: un documentario qualunque a
                           # tema (solo per Documentari/Cucina, non YouTube)
                           or (_poster_tmdb(qp, doc_ok=True)
                               if quale != "youtube" else ""))
                if img:
                    trovate[etichetta] = img
                    nuove += 1

    try:
        with io.open(_file(), "w", encoding="utf-8") as f:
            f.write(json.dumps({"quando": time.time(), "voci": trovate},
                               ensure_ascii=False))
    except Exception:
        return 0
    return nuove


def calcola_se_serve(scaffale_di):
    if not scaduto():
        return 0
    return calcola(scaffale_di)
