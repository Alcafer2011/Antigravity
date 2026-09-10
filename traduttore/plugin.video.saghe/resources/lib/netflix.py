# -*- coding: utf-8 -*-
"""COSA C'E' SU NETFLIX ORA (Italia), per genere.

Chiesto dall'utente il 10/09/2026: "righe separate che mi dicono anime su
Netflix, serie TV su Netflix, per genere. Ne scelgo una e viene aggiunta in
automatico nella sezione giusta, col percorso creato e visibile."

DA DOVE VIENE IL DATO
    TMDb sa, regione per regione, su quale servizio in abbonamento sta ogni
    titolo (`watch/providers`). Il provider Netflix in TMDb e' l'id 8, la
    regione Italia e' IT. Con `/discover` si chiede "le serie che ORA sono
    su Netflix IT, di questo genere, ordinate per popolarita'".

NIENTE CHIAVE NUOVA
    Si usa la stessa chiave TMDb gia' nel progetto (copertine.py, consigli.py).

COME SI COLLEGA AL RESTO
    Una serie scelta qui diventa una serie "aggiunta da te" identica a quelle
    dei Consigliati: `consigli.aggiungi(tmdb_id, tipo=...)`. Da li' in poi la
    ricerca e la riproduzione sono quelle di sempre - prima i siti gratuiti,
    e se ce l'ha solo Netflix, il ripiego apre l'app Netflix col titolo gia'
    scritto. Il tipo decide la sezione: "anime" -> Cartoni, "serietv" ->
    Serie TV.
"""

import io
import json
import time
import urllib.parse
import urllib.request

CHIAVE_TMDB = "a1ab8b8669da03637a4b98fa39c39228"
NETFLIX_ID = 8
REGIONE = "IT"
BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w500"
SFONDO = "https://image.tmdb.org/t/p/w1280"

DURATA_CACHE = 24 * 60 * 60          # un giorno: i cataloghi cambiano piano

# I generi TV di TMDb, coi nomi che usa l'utente. "Anime" non e' un genere
# TMDb: e' Animazione (16) piu' la keyword 210024 ("anime"), cosi' non
# entrano i cartoni occidentali.
GENERI_TV = [
    ("Azione e avventura", "10759"),
    ("Commedia",           "35"),
    ("Dramma",             "18"),
    ("Crime e polizieschi", "80"),
    ("Mistero e thriller", "9648"),
    ("Fantascienza e fantasy", "10765"),
    ("Guerra e politica",  "10768"),
    ("Documentario",       "99"),
    ("Per ragazzi",        "10762"),
    ("Reality",            "10764"),
]

GENERI_ANIME = [
    ("Shonen / azione",    "10759"),
    ("Commedia",           "35"),
    ("Dramma e sentimentale", "18"),
    ("Fantascienza e fantasy", "10765"),
    ("Mistero e soprannaturale", "9648"),
    ("Per bambini",        "10762"),
]


def _file():
    import xbmcvfs
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    import os
    return os.path.join(c, "netflix_cache.json")


def _chiedi(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return {}


def _cache_leggi():
    try:
        with io.open(_file(), encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _cache_scrivi(d):
    try:
        with io.open(_file(), "w", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False))
    except Exception:
        pass


def _discover_tv(genere_id, solo_anime=False, pagine=2):
    """Le serie su Netflix IT di un genere, dalla piu' popolare."""
    fuori = []
    for pagina in range(1, pagine + 1):
        par = {
            "api_key": CHIAVE_TMDB, "language": "it-IT",
            "watch_region": REGIONE, "with_watch_providers": str(NETFLIX_ID),
            "with_genres": genere_id, "sort_by": "popularity.desc",
            "include_adult": "false", "page": str(pagina),
        }
        if solo_anime:
            par["with_genres"] = "16," + genere_id if genere_id != "16" else "16"
            par["with_keywords"] = "210024"
            par["with_original_language"] = "ja"
        d = _chiedi("%s/discover/tv?%s" % (BASE, urllib.parse.urlencode(par)))
        for r in d.get("results", []):
            if not r.get("id"):
                continue
            fuori.append({
                "id": r["id"],
                "titolo": r.get("name") or r.get("original_name") or "",
                "anno": (r.get("first_air_date") or "")[:4],
                "voto": round(r.get("vote_average") or 0, 1),
                "trama": (r.get("overview") or "").strip(),
                "poster": (IMG + r["poster_path"]) if r.get("poster_path") else "",
                "sfondo": (SFONDO + r["backdrop_path"]) if r.get("backdrop_path") else "",
            })
        if pagina >= d.get("total_pages", 1):
            break
    return fuori


def titoli(sezione, genere_id):
    """Titoli su Netflix IT. `sezione` = 'anime' | 'serietv'. Con cache di
    un giorno per non martellare TMDb a ogni apertura di riga."""
    chiave = "%s/%s" % (sezione, genere_id)
    cache = _cache_leggi()
    voce = cache.get(chiave)
    if voce and (time.time() - voce.get("quando", 0)) < DURATA_CACHE:
        return voce.get("titoli") or []
    dati = _discover_tv(genere_id, solo_anime=(sezione == "anime"))
    cache[chiave] = {"quando": time.time(), "titoli": dati}
    _cache_scrivi(cache)
    return dati
