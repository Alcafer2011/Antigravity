# -*- coding: utf-8 -*-
"""I film che sono AL CINEMA ADESSO in Italia.

PERCHE' NON BASTAVA s4me
    L'idea di partenza era: "s4me pesca gia' le uscite al cinema, prendiamo
    quelle". Guardando dentro, non e' cosi'. Il suo aggregatore
    (`specials/news.py`) conosce tre sole categorie - film, serie, anime - e
    quello che raccoglie sono **gli ultimi film caricati dai siti**, che e'
    un'altra cosa: un film del 2019 messo online ieri finisce li', un film
    in sala da un mese che nessuno ha ancora caricato no.
    L'unico canale che si avvicina davvero e' ilgeniodellostreaming_cam, ma
    raccoglie le copie riprese in sala col telefono: qualita' pessima.

COME FUNZIONA INVECE QUI
    L'elenco di CHI e' al cinema lo da' TMDB, che sa quali film sono nelle
    sale ITALIANE oggi (`/movie/now_playing` con region=IT). E' l'unica
    fonte che risponde davvero alla domanda.
    Poi, per ognuno, la fonte da cui guardarlo la cerca s4me - ma quel pezzo
    NON sta qui: sta nel nostro canale dentro s4me (`resources/canale/
    lesaghe.py`, azione `cinema`), perche' e' li' che si possono chiamare i
    55 siti. Qui si prepara solo l'elenco e lo si scrive su file.

    Divisione netta, e voluta:
        questo file  ->  CHI e' al cinema      (TMDB, una volta al giorno)
        lesaghe.py   ->  DOVE si guarda        (s4me, quando apri la sezione)

    Cosi' l'elenco resta fresco anche quando i siti sono giu', e aprire la
    sezione non aspetta mai una chiamata a TMDB.
"""

import io
import json
import os
import time

import xbmcvfs

CHIAVE_TMDB = "a1ab8b8669da03637a4b98fa39c39228"
UA = {"User-Agent": "Mozilla/5.0"}

# Ogni quanto si richiede l'elenco a TMDB. I film di sala cambiano il
# giovedi': una volta al giorno e' piu' che sufficiente, e non pesa.
DURATA = 24 * 60 * 60

# Quanti tenerne. TMDB ne da' una ventina per pagina; due pagine coprono
# abbondantemente il cartellone italiano di una settimana.
PAGINE = 2
QUANTI = 40


def _dati():
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    return c


def file_cinema():
    """Il file che legge anche il canale dentro s4me. Percorso condiviso."""
    return os.path.join(_dati(), "cinema.json")


def _chiedi(url):
    import urllib.request
    for _ in range(2):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=20) as f:
                return json.loads(f.read().decode("utf-8"))
        except Exception:
            time.sleep(1.5)
    return {}


def leggi():
    """L'elenco gia' scaricato. Non va mai in rete."""
    try:
        with io.open(file_cinema(), encoding="utf-8") as f:
            return (json.load(f) or {}).get("film") or []
    except Exception:
        return []


def scaduto():
    try:
        with io.open(file_cinema(), encoding="utf-8") as f:
            return (time.time() - (json.load(f) or {}).get("quando", 0)) > DURATA
    except Exception:
        return True


def _immagine(percorso, misura="w500"):
    if not percorso:
        return ""
    return "https://image.tmdb.org/t/p/%s%s" % (misura, percorso)


def aggiorna():
    """Richiede a TMDB il cartellone italiano e lo scrive su file.

    Torna quanti film ha trovato. Se la rete e' giu' NON tocca il file
    esistente: meglio un elenco di ieri che una sezione vuota.
    """
    film = []
    visti = set()
    for pagina in range(1, PAGINE + 1):
        d = _chiedi("https://api.themoviedb.org/3/movie/now_playing"
                    "?api_key=%s&language=it-IT&region=IT&page=%d"
                    % (CHIAVE_TMDB, pagina))
        risultati = d.get("results") or []
        if not risultati:
            break
        for r in risultati:
            tid = r.get("id")
            titolo = (r.get("title") or "").strip()
            if not tid or not titolo or tid in visti:
                continue
            visti.add(tid)
            film.append({
                "tmdb": tid,
                "titolo": titolo,
                # Il titolo originale serve come SECONDO tentativo di ricerca:
                # molti siti italiani archiviano col titolo inglese.
                "originale": (r.get("original_title") or "").strip(),
                "anno": (r.get("release_date") or "")[:4],
                "trama": (r.get("overview") or "").strip(),
                "voto": r.get("vote_average") or 0,
                "poster": _immagine(r.get("poster_path")),
                "sfondo": _immagine(r.get("backdrop_path"), "w1280"),
            })

    if not film:
        return 0                      # rete giu': si tiene quello di prima

    # NON si riordina.
    # TMDB li da' gia' in ordine di popolarita', che per un cartellone e'
    # l'ordine giusto: in cima quello che la gente sta andando a vedere.
    # Riordinandoli per anno (primo tentativo) le riedizioni finivano in
    # fondo - ma "Terminator 2" rimesso in sala oggi e' al cinema oggi
    # quanto un film del 2026, e la sua data di uscita non dice niente.
    film = film[:QUANTI]

    try:
        with io.open(file_cinema(), "w", encoding="utf-8") as f:
            f.write(json.dumps({"quando": time.time(), "film": film},
                               ensure_ascii=False))
    except Exception:
        return 0
    return len(film)


def aggiorna_se_serve():
    """Chiamata dal servizio all'avvio. Se l'elenco e' fresco non fa niente."""
    if not scaduto():
        return 0
    return aggiorna()
