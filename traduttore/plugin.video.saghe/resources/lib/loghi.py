# -*- coding: utf-8 -*-
"""IL LOGO DEL TITOLO PER LE RIGHE CHE NON VENGONO DAL CATALOGO.

PERCHE'
    Su Arctic Zephyr, sopra la tessera scelta, compare la scritta del titolo
    disegnata (il "clearlogo"), come su Netflix. All'utente e' piaciuta
    subito. Le serie del catalogo hanno gia' il loro logo in
    `resources/loghi_titolo.json` (lo prepara `traduttore/fai-loghi.py`).
    Le righe della Home che arrivano da TMDb - Su Netflix ora, Consigliati,
    Al cinema ora, le serie aggiunte da te - cambiano ogni giorno: un file
    preparato prima sul PC non puo' conoscerle.

COME
    Due tempi, per la regola di sempre: LE RIGHE NON VANNO MAI IN RETE.
    - `logo()` legge soltanto la cache `loghi_tmdb.json` nei dati
      dell'add-on. La chiamano le righe.
    - `riempi()` guarda cosa c'e' nelle cache di Netflix, Consigliati e
      Cinema e chiede a TMDb i loghi che mancano. La chiama il SERVIZIO, che
      gira per conto suo.

LA LINGUA
    La stessa regola di fai-loghi.py: italiano > senza lingua > inglese >
    qualunque. Fra loghi della stessa lingua il piu' votato, e a parita' il
    piu' largo (un logo quadrato sopra una tessera sta male).
"""

import io
import json
import os
import time

import xbmc
import xbmcvfs

from resources.lib.tmdb import CHIAVE as CHIAVE_TMDB  # la chiave sta in un posto solo
IMG = "https://image.tmdb.org/t/p/w500%s"
PREFERENZA = {"it": 0, None: 1, "": 1, "en": 2}

# Un titolo senza logo oggi puo' averlo fra qualche giorno: si richiede dopo
# una settimana, non a ogni giro.
RIPROVA_VUOTI = 7 * 24 * 3600
# Tetto per giro, per non martellare TMDb. Era 120: sul banco (10/09/2026)
# le righe ne chiedevano circa 130, e gli ultimi arrivavano solo al riavvio
# dopo. Con 0,25 s fra una richiesta e l'altra 400 titoli sono meno di due
# minuti, in un filo a parte.
MASSIMO_PER_GIRO = 400

_CACHE = None


def _file():
    cartella = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(cartella):
        xbmcvfs.mkdirs(cartella)
    return os.path.join(cartella, "loghi_tmdb.json")


def _leggi():
    global _CACHE
    if _CACHE is None:
        try:
            with io.open(_file(), encoding="utf-8") as f:
                _CACHE = json.load(f) or {}
        except Exception:
            _CACHE = {}
    return _CACHE


def _chiave(tipo, tmdb_id):
    return "%s/%s" % ("movie" if tipo == "movie" else "tv", tmdb_id)


def logo(tipo, tmdb_id):
    """Il logo del titolo, dalla sola cache. `tipo` e' 'tv' o 'movie'.
    Stringa vuota se non c'e': mai la rete, mai un'attesa."""
    if not tmdb_id:
        return ""
    v = _leggi().get(_chiave(tipo, tmdb_id))
    return v.get("url", "") if isinstance(v, dict) else ""


def _chiedi(url):
    import urllib.request
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(r, timeout=20) as f:
            return json.loads(f.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def _scegli(tipo, tmdb_id):
    """Il logo migliore da TMDb. None se la rete non ha risposto (si riprova
    al giro dopo), "" se TMDb risponde ma un logo non ce l'ha."""
    d = _chiedi("https://api.themoviedb.org/3/%s/%s/images?api_key=%s"
                "&include_image_language=it,null,en"
                % ("movie" if tipo == "movie" else "tv", tmdb_id, CHIAVE_TMDB))
    if d is None:
        return None
    loghi = [x for x in (d.get("logos") or []) if x.get("file_path")]
    if not loghi:
        return ""

    def voto(x):
        return (PREFERENZA.get(x.get("iso_639_1"), 3),
                -(x.get("vote_average") or 0),
                -(x.get("aspect_ratio") or 0))

    return IMG % sorted(loghi, key=voto)[0]["file_path"]


def _da_cercare():
    """(tipo, id) di tutto quello che le righe della Home possono mostrare."""
    voci = []
    try:
        from resources.lib import netflix
        for chiave, voce in (netflix._cache_leggi() or {}).items():
            if not chiave.startswith("home/"):
                continue
            for v in (voce or {}).get("titoli") or []:
                voci.append(("movie" if v.get("tipo") == "film" else "tv",
                             v.get("id")))
    except Exception as e:
        xbmc.log("[Le Saghe] loghi, netflix: %s" % e, xbmc.LOGWARNING)
    try:
        from resources.lib import consigli
        voci += [("tv", v.get("id")) for v in consigli.leggi()]
        voci += [("tv", v.get("tmdb")) for v in consigli.serie_mie().values()]
    except Exception as e:
        xbmc.log("[Le Saghe] loghi, consigli: %s" % e, xbmc.LOGWARNING)
    try:
        from resources.lib import cinema
        voci += [("movie", f.get("tmdb")) for f in cinema.leggi()]
    except Exception as e:
        xbmc.log("[Le Saghe] loghi, cinema: %s" % e, xbmc.LOGWARNING)
    visti, fuori = set(), []
    for tipo, tid in voci:
        if tid and (tipo, str(tid)) not in visti:
            visti.add((tipo, str(tid)))
            fuori.append((tipo, str(tid)))
    return fuori


def riempi():
    """Chiede a TMDb i loghi che mancano. La chiama il servizio. Quanti ne ha
    chiesti in questo giro."""
    cache = _leggi()
    adesso = time.time()
    monitor = xbmc.Monitor()
    chiesti = 0
    for tipo, tid in _da_cercare():
        v = cache.get(_chiave(tipo, tid))
        if isinstance(v, dict) and (v.get("url") or
                                    adesso - v.get("quando", 0) < RIPROVA_VUOTI):
            continue
        if chiesti >= MASSIMO_PER_GIRO:
            break
        url = _scegli(tipo, tid)
        chiesti += 1
        if url is not None:
            cache[_chiave(tipo, tid)] = {"url": url, "quando": adesso}
        if monitor.waitForAbort(0.25):
            break
    if chiesti:
        try:
            with io.open(_file(), "w", encoding="utf-8") as f:
                f.write(json.dumps(cache, ensure_ascii=False))
        except Exception as e:
            xbmc.log("[Le Saghe] loghi non salvati: %s" % e, xbmc.LOGWARNING)
    return chiesti
