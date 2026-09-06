# -*- coding: utf-8 -*-
"""
Schede degli episodi: titolo italiano, trama e immagine.

I dati sono imbarcati nell'addon (resources/schede/*.json), scaricati una
volta da TMDb sul PC. Nessuna chiamata di rete a runtime: il menu si apre
alla stessa velocita' anche con la linea 4G a terra, e funziona offline.
"""

import json
import os

import xbmcaddon
import xbmcvfs

_CARTELLA = os.path.join(
    xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("path")),
    "resources", "schede")

_cache = {}

_VUOTA = {"serie": "", "poster": "", "sfondo": "", "episodi": {}}


def _serie(serie_id):
    if serie_id in _cache:
        return _cache[serie_id]
    percorso = os.path.join(_CARTELLA, serie_id + ".json")
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            dati = json.load(f)
    except (OSError, ValueError):
        dati = dict(_VUOTA)
    _cache[serie_id] = dati
    return dati


def poster(serie_id):
    return _serie(serie_id).get("poster", "")


def sfondo(serie_id):
    return _serie(serie_id).get("sfondo", "")


def episodio(serie_id, ep):
    """Scheda di un episodio.

    Restituisce sempre un dizionario: titolo, trama, immagine, data.
    Vuoti se la scheda manca, cosi' chi chiama non deve controllare nulla.
    """
    e = _serie(serie_id).get("episodi", {}).get(str(ep))
    if not e:
        return {"titolo": "", "trama": "", "immagine": "", "data": ""}
    return {
        "titolo": e.get("t", ""),
        "trama": e.get("p", ""),
        "immagine": e.get("i", ""),
        "data": e.get("d", ""),
    }


def ha_schede():
    """Vero se almeno una serie ha le schede a bordo."""
    try:
        return any(n.endswith(".json") for n in os.listdir(_CARTELLA))
    except OSError:
        return False


_FILM = os.path.join(
    xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("path")),
    "resources", "film")


def film(percorso_id):
    """Elenco dei film della saga, dal piu' vecchio al piu' recente."""
    try:
        with open(os.path.join(_FILM, percorso_id + ".json"), "r",
                  encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []
