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


# --------------------------------------------------------------------------
# LA RIGA NELLA HOME
#
# L'utente (10/09/2026): "della funzione di netflix che abbiamo implementato
# che mi fa vedere cosa c'e' in onda ora, non c'e' traccia". Aveva ragione:
# c'era solo una voce dentro il menu dell'add-on. Adesso e' una riga come le
# altre.
#
# REGOLA: LA RIGA NON VA MAI IN RETE.
# Una riga della home che aspetta TMDb tiene ferma tutta la schermata
# iniziale finche' non risponde - e sono 29 righe che partono insieme. Qui si
# legge SOLO la cache; a riempirla ci pensa il servizio, che gira per conto
# suo. Se la cache e' vuota la riga e' vuota per un giro, e va bene cosi'.
# --------------------------------------------------------------------------

# LE TRE SEZIONI. Sono quelle di Netflix, guardate sul loro sito il
# 10/09/2026: nel menu in alto "Serie" e "Film" sono due voci di PRIMO
# livello, e nel menu Generi dei Film "Anime" e' un genere a se'.
# L'utente, guardando la riga unica: "ho visto forse dei film o serie tv e
# cartoni animati o anime ... e sono due categorie diverse". Aveva ragione.
SEZIONI = [
    ("serietv", "SERIE TV", "tv"),
    ("film",    "FILM",     "movie"),
    ("anime",   "ANIME",    "tv"),
]

# I generi dei FILM, coi nomi e nell'ordine del menu di Netflix. Gli
# identificativi pero' sono quelli di TMDb, non di Netflix: Netflix usa i
# suoi (Horror 8711), TMDb i suoi (Horror 27), e a interrogare e' TMDb.
# Le voci che non sono un genere ("Italiani", "Premiati") si fanno con altri
# parametri: sono marcate con una chiave che comincia per "@".
GENERI_FILM = [
    ("Anime",               "@anime"),
    ("Azione",              "28"),
    ("Avventura",           "12"),
    ("Bambini e famiglie",  "10751"),
    ("Commedie",            "35"),
    ("Crime",               "80"),
    ("Documentari",         "99"),
    ("Drammi",              "18"),
    ("Fantascienza",        "878"),
    ("Fantasy",             "14"),
    ("Guerra",              "10752"),
    ("Horror",              "27"),
    ("Italiani",            "@italiani"),
    ("Musica e musical",    "10402"),
    ("Mistero",             "9648"),
    ("Premiati",            "@premiati"),
    ("Romantici",           "10749"),
    ("Storia",              "36"),
    ("Thriller",            "53"),
    ("Western",             "37"),
]


def _alfabeto_nostro(titolo):
    """Vero se il titolo e' scritto con le nostre lettere.

    Non e' snobismo: TMDb da' il titolo ORIGINALE quando la traduzione
    italiana non esiste, quindi un titolo in kanji o in devanagari e' il
    segnale che in italiano quella cosa non c'e'.
    """
    t = (titolo or "").strip()
    lettere = [c for c in t if c.isalpha()]
    if not lettere:
        return False
    return sum(1 for c in lettere if ord(c) < 0x250) >= len(lettere) * 0.6


def _voce(r, tipo):
    """Una scheda, uguale per film e serie: TMDb usa nomi di campo diversi."""
    return {
        "id": r["id"],
        "tipo": tipo,
        "titolo": (r.get("name") or r.get("title")
                   or r.get("original_name") or r.get("original_title") or ""),
        "anno": (r.get("first_air_date") or r.get("release_date") or "")[:4],
        "voto": round(r.get("vote_average") or 0, 1),
        "trama": (r.get("overview") or "").strip(),
        "poster": (IMG + r["poster_path"]) if r.get("poster_path") else "",
        "sfondo": (SFONDO + r["backdrop_path"]) if r.get("backdrop_path") else "",
    }


def _parametri(sezione, genere=""):
    """I parametri di /discover per una sezione (e un genere, se c'e')."""
    par = {
        "api_key": CHIAVE_TMDB, "language": "it-IT",
        "watch_region": REGIONE, "with_watch_providers": str(NETFLIX_ID),
        "sort_by": "popularity.desc", "include_adult": "false", "page": "1",
    }
    if sezione == "anime":
        # "Anime" non e' un genere TMDb: Animazione (16) + la parola chiave
        # "anime" (210024) + lingua originale giapponese. Senza la keyword
        # entrerebbero anche i cartoni occidentali.
        par.update({"with_genres": "16", "with_keywords": "210024",
                    "with_original_language": "ja"})
    if genere.startswith("@"):
        speciale = genere[1:]
        if speciale == "anime":
            par.update({"with_genres": "16", "with_keywords": "210024",
                        "with_original_language": "ja"})
        elif speciale == "italiani":
            par["with_original_language"] = "it"
        elif speciale == "premiati":
            # I piu' votati, ma solo con abbastanza voti: senza la soglia
            # vince un titolo con tre voti da dieci.
            par["sort_by"] = "vote_average.desc"
            par["vote_count.gte"] = "300"
    elif genere:
        g = par.get("with_genres")
        par["with_genres"] = (g + "," + genere) if g else genere
    return par


def _scarica(sezione, genere="", pagine=1):
    _, _, cosa = next(s for s in SEZIONI if s[0] == sezione)
    fuori = []
    for pagina in range(1, pagine + 1):
        par = _parametri(sezione, genere)
        par["page"] = str(pagina)
        d = _chiedi("%s/discover/%s?%s"
                    % (BASE, cosa, urllib.parse.urlencode(par)))
        for r in d.get("results", []):
            if not (r.get("id") and r.get("poster_path")):
                continue
            # NIENTE TITOLI IN UN ALTRO ALFABETO. Fra i film su Netflix IT
            # e' uscito un titolo in hindi: TMDb, quando la traduzione
            # italiana non c'e', restituisce l'ORIGINALE - ed e' proprio il
            # segno che in italiano quel titolo non esiste. Stessa regola
            # gia' usata dai Consigliati.
            if not _alfabeto_nostro(r.get("name") or r.get("title")):
                continue
            if True:
                fuori.append(_voce(r, "anime" if sezione == "anime"
                                   else ("film" if sezione == "film" else "serietv")))
        if pagina >= d.get("total_pages", 1):
            break
    return fuori


# --------------------------------------------------------------------------
# LE RIGHE NELLA HOME
#
# REGOLA: LE RIGHE NON VANNO MAI IN RETE.
# Una riga della home che aspetta TMDb tiene ferma tutta la schermata
# iniziale, e sono trenta righe che partono insieme. Qui si legge SOLO la
# cache; a riempirla ci pensa il servizio, che gira per conto suo. Se la
# cache e' vuota la riga e' vuota per un giro, e va bene cosi'.
# --------------------------------------------------------------------------

def _chiave_riga(sezione):
    return "home/%s" % sezione


def aggiorna_righe():
    """Riempie la cache delle tre righe. La chiama il SERVIZIO, non la home.

    Torna quante schede ha messo, per sezione."""
    cache = _cache_leggi()
    esito = {}
    for sezione, _nome, _cosa in SEZIONI:
        chiave = _chiave_riga(sezione)
        voce = cache.get(chiave)
        if voce and (time.time() - voce.get("quando", 0)) < DURATA_CACHE:
            esito[sezione] = len(voce.get("titoli") or [])
            continue
        dati = _scarica(sezione, pagine=1)
        if dati:
            cache[chiave] = {"quando": time.time(), "titoli": dati}
        esito[sezione] = len(dati)
    _cache_scrivi(cache)
    return esito


def riga(sezione):
    """Le schede di una riga, dalla sola cache. Mai la rete."""
    return (_cache_leggi().get(_chiave_riga(sezione)) or {}).get("titoli") or []


def per_genere(sezione, genere):
    """Un genere dentro una sezione, con cache di un giorno.

    Questa PUO' andare in rete: la si chiama aprendo una voce di menu, dove
    una rotellina di due secondi e' normale. Le righe della home no.
    """
    chiave = "%s/%s" % (sezione, genere or "tutti")
    cache = _cache_leggi()
    voce = cache.get(chiave)
    if voce and (time.time() - voce.get("quando", 0)) < DURATA_CACHE:
        return voce.get("titoli") or []
    dati = _scarica(sezione, genere, pagine=2)
    cache[chiave] = {"quando": time.time(), "titoli": dati}
    _cache_scrivi(cache)
    return dati


def generi(sezione):
    """I generi di una sezione. Per le serie e gli anime quelli TV, per i
    film la lista del menu di Netflix."""
    if sezione == "film":
        return GENERI_FILM
    if sezione == "anime":
        return GENERI_ANIME
    return GENERI_TV
