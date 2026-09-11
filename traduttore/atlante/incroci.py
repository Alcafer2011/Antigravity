# -*- coding: utf-8 -*-
"""INCROCI: cosa chiede la skin di ogni apparecchio e cosa da' il nostro add-on.

La domanda di fondo: sulla TV di QUEL apparecchio, con QUELLA skin, le voci
della Videoteca hanno tutto quello che la skin cerca? E il codice che gira
li' e' lo stesso del sorgente?
"""

import hashlib
import io
import os
import re

# Etichetta letta dalla skin -> metodo dell'InfoTag che la riempie.
ETICHETTE_INFOTAG = {
    "Title": "setTitle", "Plot": "setPlot", "PlotOutline": "setPlotOutline", "Year": "setYear",
    "Rating": "setRating", "Genre": "setGenres", "Duration": "setDuration", "Premiered": "setPremiered",
    "TVShowTitle": "setTvShowTitle", "Season": "setSeason", "Episode": "setEpisode",
    "Tagline": "setTagline", "Trailer": "setTrailer", "Studio": "setStudios", "Mpaa": "setMpaa",
    "Votes": "setVotes", "Director": "setDirectors", "Writer": "setWriters", "Country": "setCountries",
    "OriginalTitle": "setOriginalTitle", "DBType": "setMediaType", "UserRating": "setUserRating",
    "Top250": "setTop250", "IMDBNumber": "setIMDBNumber", "Aired": "setFirstAired",
    "PercentPlayed": "setResumePoint", "IsResumable": "setResumePoint",
}
# Etichette che Kodi riempie da solo o che dipendono dalla libreria, non dall'add-on.
AUTOMATICHE = {"Label", "Label2", "Icon", "Thumb", "FolderPath", "FileNameAndPath", "Path", "IsFolder",
               "IsPlaying", "IsSelected", "IsParentFolder", "CurrentItem", "Filename", "FileExtension",
               "Size", "Date", "DateAdded", "StartTime", "EndTime", "ChannelName", "ChannelNumberLabel",
               "HasEpg", "IsRecording", "Overlay", "IsCollection", "DBID", "Property", "Art", "PictureDateTime"}

# Etichette che hanno senso solo per la libreria video di Kodi: Top250 e' la
# classifica IMDb che mette lo scraper, Season la stagione di un episodio in
# libreria. Le nostre tappe sono anelli di una catena che attraversa piu' serie:
# una "stagione" non esiste, e inventarla confonderebbe (11/09/2026).
SOLO_LIBRERIA = {"Top250", "Season"}


def _md5_sorgente(cartella):
    fuori = {}
    for radice, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith((".py", ".xml", ".json", ".po")) and ".bak" not in f and "prima" not in f:
                p = os.path.join(radice, f)
                with open(p, "rb") as h:
                    fuori[os.path.relpath(p, cartella).replace("\\", "/")] = hashlib.md5(h.read()).hexdigest()
    return fuori


def _font_nostri(cartella_addon):
    fuori = {}
    base = os.path.join(cartella_addon, "resources", "skins")
    for radice, _d, files in os.walk(base):
        for f in files:
            if f.endswith(".xml"):
                with io.open(os.path.join(radice, f), encoding="utf-8", errors="replace") as h:
                    fuori[f] = sorted(set(re.findall(r"<font>([^<$]+)</font>", h.read())))
    return fuori


def analizza(addon, skin_per_app, kodi_per_app, cartella_addon):
    fuori = {}
    sorgente = _md5_sorgente(cartella_addon)
    art_date = set(addon["art_date"])
    prop_date = set(addon["proprieta_date"])
    setter = set(addon["infotag"])
    font_nostri = _font_nostri(cartella_addon)
    for app, sk in skin_per_app.items():
        k = kodi_per_app.get(app) or {}
        if not sk or sk.get("errore"):
            fuori[app] = {"errore": (sk or {}).get("errore", "skin non analizzata")}
            continue
        art_lette = set(sk["art"])
        # le chiavi di arte composte (tvshow.poster, season.poster) le riempie Kodi dalla libreria
        art_nostre_utili = sorted(a for a in art_lette if "." not in a and "$" not in a and "(" not in a)
        etichette = set(sk["etichette_voce"]) - AUTOMATICHE - SOLO_LIBRERIA
        mancano_etichette = []
        for e in sorted(etichette):
            s = ETICHETTE_INFOTAG.get(e)
            if s and s not in setter:
                mancano_etichette.append({"etichetta": e, "serve": s, "volte": sk["etichette_voce"][e]["volte"],
                                          "dove": sk["etichette_voce"][e]["dove"][:3]})
        prop_lette = {p for p in sk["proprieta_voce"] if "$" not in p}
        font_skin = set(sk.get("font_definiti") or [])
        font_mancanti = {f: [x for x in fonts if x not in font_skin] for f, fonts in font_nostri.items()}
        font_mancanti = {f: v for f, v in font_mancanti.items() if v}
        md5_app = k.get("saghe_md5") or {}
        diversi = sorted(f for f in sorgente if f in md5_app and md5_app[f] != sorgente[f])
        mancanti = sorted(f for f in sorgente if f not in md5_app) if md5_app else []
        in_piu = sorted(f for f in md5_app if f not in sorgente)
        fuori[app] = {
            "skin": "%s %s" % (sk.get("nome"), sk.get("versione")),
            "art_lette_dalla_skin": {a: sk["art"][a]["volte"] for a in art_nostre_utili},
            "art_che_non_diamo": sorted(a for a in art_nostre_utili if a not in art_date),
            "art_che_diamo_e_la_skin_non_legge": sorted(a for a in art_date if a not in art_lette),
            "etichette_che_non_riempiamo": mancano_etichette,
            "proprieta_lette_non_date": sorted(p for p in prop_lette if p not in prop_date)[:60],
            "proprieta_date_non_lette": sorted(p for p in prop_date if p not in prop_lette),
            "font_nostre_finestre_mancanti": font_mancanti,
            "saghe_diversi_dal_sorgente": diversi,
            "saghe_mancanti_sull_apparecchio": mancanti,
            "saghe_in_piu_sull_apparecchio": in_piu,
            "include_mancanti": sk.get("include_mancanti", []),
            "variabili_mancanti": sk.get("variabili_mancanti", []),
        }
    return fuori
