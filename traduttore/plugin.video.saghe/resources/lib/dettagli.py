# -*- coding: utf-8 -*-
"""LA SCHEDA COMPLETA E LE IMMAGINI IN PIU' DEI TITOLI CHE VENGONO DA TMDb.

PERCHE' (atlante, 11/09/2026)
    Arctic Zephyr sa mostrare genere, regista, durata, studio, paese, data di
    uscita, frase di lancio, divieto per eta', numero di voti, trailer - e
    immagini come la locandina senza scritte (keyart), la striscia (banner),
    il personaggio ritagliato (clearart) e il disco (discart). Le liste di
    TMDb danno solo titolo, trama, voto e due immagini: il resto sta nella
    scheda di ogni titolo, una richiesta a testa. Le tessere restavano mezze
    vuote e l'atlante lo contava.

COME
    Due tempi, come i loghi: LE RIGHE DELLA HOME NON VANNO MAI IN RETE.
    - `applica()` e `arte()` leggono soltanto la cache `dettagli_tmdb.json`.
    - `riempi()` la riempie dal SERVIZIO, in un filo a parte:
        TMDb       la scheda, la locandina senza scritte, lo sfondo col titolo
        TVmaze     la striscia delle serie (gratis, senza chiave)
        fanart.tv  clearart, disco e striscia dei film, SOLO se nelle
                   impostazioni c'e' la chiave personale (gratuita)

IL TRAILER
    Punta all'add-on YouTube, che su tutti e tre gli apparecchi e' configurato
    (servi.py, 11/09): senza configurazione il primo trailer apriva la
    procedura guidata e poteva bloccare Kodi. Il trailer automatico della
    skin resta spento: parte solo se lo chiedi.
"""

import io
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.tmdb import CHIAVE as CHIAVE_TMDB  # la chiave sta in un posto solo

IMG = "https://image.tmdb.org/t/p/%s%s"
TRAILER = "plugin://plugin.video.youtube/play/?video_id=%s"
PREFERENZA = {"it": 0, None: 1, "": 1, "en": 2}

# Una scheda si rilegge dopo un mese (voti e immagini cambiano piano); un
# titolo che TMDb non conosceva si richiede dopo due settimane.
RINNOVA = 30 * 24 * 3600
RIPROVA_VUOTI = 14 * 24 * 3600
MASSIMO_PER_GIRO = 300

_CACHE = None


def _file():
    cartella = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(cartella):
        xbmcvfs.mkdirs(cartella)
    return os.path.join(cartella, "dettagli_tmdb.json")


def _leggi():
    global _CACHE
    if _CACHE is None:
        try:
            with io.open(_file(), encoding="utf-8") as f:
                _CACHE = json.load(f) or {}
        except (OSError, ValueError):
            _CACHE = {}
    return _CACHE


def _chiave(tipo, tmdb_id):
    return "%s/%s" % ("movie" if tipo == "movie" else "tv", tmdb_id)


def _voce(tipo, tmdb_id):
    if not tmdb_id:
        return None
    v = _leggi().get(_chiave(tipo, tmdb_id))
    return v if isinstance(v, dict) and v.get("ok") else None


# --------------------------------------------------------------------------
# LETTURA (le righe): mai la rete
# --------------------------------------------------------------------------

def applica(tag, tipo, tmdb_id):
    """Riempie l'InfoTag con la scheda in cache. Vero se c'era."""
    v = _voce(tipo, tmdb_id)
    if not v:
        return False
    if v.get("generi"):
        tag.setGenres(list(v["generi"]))
    if v.get("studi"):
        tag.setStudios(list(v["studi"]))
    if v.get("registi"):
        tag.setDirectors(list(v["registi"]))
    if v.get("autori"):
        tag.setWriters(list(v["autori"]))
    if v.get("paesi"):
        tag.setCountries(list(v["paesi"]))
    if v.get("uscita"):
        tag.setPremiered(v["uscita"])
    if v.get("frase"):
        tag.setTagline(v["frase"])
    if v.get("durata"):
        tag.setDuration(int(v["durata"]))
    if v.get("divieto"):
        tag.setMpaa(v["divieto"])
    if v.get("voti"):
        tag.setVotes(int(v["voti"]))
    if v.get("imdb"):
        tag.setIMDBNumber(v["imdb"])
        tag.setUniqueIDs({"tmdb": str(tmdb_id), "imdb": v["imdb"]}, "tmdb")
    if v.get("originale"):
        tag.setOriginalTitle(v["originale"])
    if v.get("trailer"):
        tag.setTrailer(v["trailer"])
    return True


def arte(tipo, tmdb_id):
    """Le immagini in piu' in cache: solo quelle che ci sono."""
    v = _voce(tipo, tmdb_id) or {}
    return {k: v[k] for k in ("keyart", "landscape", "banner", "clearart", "discart") if v.get(k)}


# --------------------------------------------------------------------------
# RIEMPIMENTO (il servizio): qui si va in rete
# --------------------------------------------------------------------------

def _chiedi(url):
    """(codice HTTP, dati). Codice 0 = la rete non ha risposto."""
    import urllib.error
    import urllib.request
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Videoteca)"})
        with urllib.request.urlopen(r, timeout=20) as f:
            return f.status, json.loads(f.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as errore:
        return errore.code, None
    except Exception as errore:
        xbmc.log("[Le Saghe] dettagli, rete: %s" % errore, xbmc.LOGDEBUG)
        return 0, None


def _migliore(immagini, lingue=None):
    """La piu' adatta: lingua preferita, poi la piu' votata, poi la piu' larga."""
    scelte = [x for x in immagini or [] if x.get("file_path") and
              (lingue is None or x.get("iso_639_1") in lingue)]
    if not scelte:
        return None
    return sorted(scelte, key=lambda x: (PREFERENZA.get(x.get("iso_639_1"), 3),
                                         -(x.get("vote_average") or 0),
                                         -(x.get("width") or 0)))[0]


def _da_tmdb(tipo, tmdb_id):
    film = tipo == "movie"
    extra = "credits,external_ids,videos,images," + ("release_dates" if film else "content_ratings")
    codice, d = _chiedi("https://api.themoviedb.org/3/%s/%s?api_key=%s&language=it-IT"
                        "&append_to_response=%s&include_image_language=it,null,en"
                        "&include_video_language=it,en"
                        % ("movie" if film else "tv", tmdb_id, CHIAVE_TMDB, extra))
    if codice == 404:
        return {}
    if not d:
        return None
    v = {"generi": [g["name"] for g in d.get("genres") or [] if g.get("name")][:4],
         "frase": d.get("tagline") or "",
         "voti": d.get("vote_count") or 0,
         "originale": d.get("original_title" if film else "original_name") or "",
         "uscita": d.get("release_date" if film else "first_air_date") or "",
         "paesi": [p["name"] for p in d.get("production_countries") or [] if p.get("name")][:3],
         "imdb": (d.get("external_ids") or {}).get("imdb_id") or d.get("imdb_id") or "",
         "tvdb": (d.get("external_ids") or {}).get("tvdb_id") or ""}
    studi = [s["name"] for s in (d.get("networks") or []) + (d.get("production_companies") or []) if s.get("name")]
    v["studi"] = list(dict.fromkeys(studi))[:3]
    troupe = (d.get("credits") or {}).get("crew") or []
    if film:
        v["registi"] = [c["name"] for c in troupe if c.get("job") == "Director"][:3]
        v["durata"] = (d.get("runtime") or 0) * 60
        for paese in (d.get("release_dates") or {}).get("results") or []:
            if paese.get("iso_3166_1") == "IT":
                v["divieto"] = next((x["certification"] for x in paese.get("release_dates") or []
                                     if x.get("certification")), "")
    else:
        v["registi"] = [c["name"] for c in d.get("created_by") or [] if c.get("name")][:3]
        durate = d.get("episode_run_time") or []
        v["durata"] = (durate[0] if durate else 0) * 60
        for paese in (d.get("content_ratings") or {}).get("results") or []:
            if paese.get("iso_3166_1") == "IT":
                v["divieto"] = paese.get("rating") or ""
    v["autori"] = list(dict.fromkeys(c["name"] for c in troupe
                                     if c.get("department") == "Writing" and c.get("name")))[:3]
    video = [x for x in (d.get("videos") or {}).get("results") or []
             if x.get("site") == "YouTube" and x.get("type") in ("Trailer", "Teaser") and x.get("key")]
    if video:
        video.sort(key=lambda x: (x.get("iso_639_1") != "it", x.get("type") != "Trailer", not x.get("official")))
        v["trailer"] = TRAILER % video[0]["key"]
    immagini = d.get("images") or {}
    senza_scritte = _migliore(immagini.get("posters"), lingue=(None, ""))
    if senza_scritte:
        v["keyart"] = IMG % ("w780", senza_scritte["file_path"])
    col_titolo = _migliore(immagini.get("backdrops"), lingue=("it", "en"))
    if col_titolo:
        v["landscape"] = IMG % ("w1280", col_titolo["file_path"])
    return v


def _da_tvmaze(v):
    """La striscia (banner) di una serie, da TVmaze: la cerca per IMDb o TVDb."""
    for campo, valore in (("imdb", v.get("imdb")), ("thetvdb", v.get("tvdb"))):
        if not valore:
            continue
        codice, serie = _chiedi("https://api.tvmaze.com/lookup/shows?%s=%s" % (campo, valore))
        if not serie or not serie.get("id"):
            continue
        _c, immagini = _chiedi("https://api.tvmaze.com/shows/%s/images" % serie["id"])
        for x in immagini or []:
            if x.get("type") == "banner":
                url = ((x.get("resolutions") or {}).get("original") or {}).get("url")
                if url:
                    return url
        return ""
    return ""


def _da_fanart(tipo, tmdb_id, v, chiave):
    """clearart, disco e striscia da fanart.tv. Solo con la chiave personale."""
    if tipo == "movie":
        _c, d = _chiedi("https://webservice.fanart.tv/v3/movies/%s?api_key=%s" % (tmdb_id, chiave))
        tipi = {"clearart": ("hdmovieclearart", "movieart"), "discart": ("moviedisc",), "banner": ("moviebanner",)}
    elif v.get("tvdb"):
        _c, d = _chiedi("https://webservice.fanart.tv/v3/tv/%s?api_key=%s" % (v["tvdb"], chiave))
        tipi = {"clearart": ("hdclearart", "clearart"), "banner": ("tvbanner",)}
    else:
        return {}
    fuori = {}
    for nostro, loro in tipi.items():
        for nome in loro:
            scelte = sorted((d or {}).get(nome) or [],
                            key=lambda x: ({"it": 0, "en": 1, "00": 2, "": 2}.get(x.get("lang"), 3), -int(x.get("likes") or 0)))
            if scelte and scelte[0].get("url"):
                fuori[nostro] = scelte[0]["url"]
                break
    return fuori


def _da_cercare():
    """(tipo, id) di tutti i titoli con una tessera: righe di TMDb e saghe."""
    from resources.lib import loghi
    voci = list(loghi._da_cercare())
    try:
        base = xbmcvfs.translatePath("special://home/addons/plugin.video.saghe/resources/tmdb.json")
        with io.open(base, encoding="utf-8") as f:
            voci += [("tv", str(c["id"])) for c in (json.load(f) or {}).values() if c.get("id")]
    except (OSError, ValueError) as errore:
        xbmc.log("[Le Saghe] dettagli, saghe: %s" % errore, xbmc.LOGDEBUG)
    return list(dict.fromkeys(voci))


def riempi():
    """Chiede le schede che mancano. La chiama il servizio. Quante ne ha chieste."""
    try:
        return _riempi()
    except Exception as errore:
        xbmc.log("[Le Saghe] dettagli non riempiti: %s" % errore, xbmc.LOGWARNING)
        return 0


def _riempi():
    from resources.lib import salva
    cache = _leggi()
    adesso = time.time()
    monitor = xbmc.Monitor()
    chiave_fanart = (xbmcaddon.Addon("plugin.video.saghe").getSetting("fanart_chiave") or "").strip()
    chiesti = 0
    for tipo, tid in _da_cercare():
        vecchia = cache.get(_chiave(tipo, tid))
        if isinstance(vecchia, dict):
            eta = adesso - vecchia.get("quando", 0)
            if eta < (RINNOVA if vecchia.get("ok") else RIPROVA_VUOTI):
                continue
        if chiesti >= MASSIMO_PER_GIRO:
            break
        chiesti += 1
        v = _da_tmdb(tipo, tid)
        if v is None:
            if monitor.waitForAbort(1):
                break
            continue            # la rete non ha risposto: si riprova al giro dopo
        if v:
            if tipo != "movie":
                v["banner"] = _da_tvmaze(v)
            if chiave_fanart:
                for k, url in _da_fanart(tipo, tid, v, chiave_fanart).items():
                    if not (k == "banner" and v.get("banner")):     # la striscia di TVmaze resta
                        v[k] = url
        v.update({"ok": bool(v), "quando": adesso})
        cache[_chiave(tipo, tid)] = v
        if monitor.waitForAbort(0.3):
            break
    if chiesti:
        salva.json_atomico(_file(), cache, ensure_ascii=False)
    return chiesti
