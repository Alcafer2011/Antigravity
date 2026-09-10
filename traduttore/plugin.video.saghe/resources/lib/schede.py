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

# Le schede delle serie che l'utente ha aggiunto dai consigli non stanno
# dentro l'add-on (un aggiornamento le cancellerebbe) ma nei suoi dati.
_CARTELLA_MIE = os.path.join(
    xbmcvfs.translatePath("special://profile/addon_data/plugin.video.saghe/"),
    "schede")

_cache = {}

_VUOTA = {"serie": "", "poster": "", "sfondo": "", "episodi": {}}


def _serie(serie_id):
    if serie_id in _cache:
        return _cache[serie_id]
    dati = None
    # Prima quelle dell'add-on, poi quelle aggiunte dall'utente: cosi' una
    # serie aggiunta da lui ha la sua scheda come tutte le altre.
    for cartella in (_CARTELLA, _CARTELLA_MIE):
        try:
            with open(os.path.join(cartella, serie_id + ".json"),
                      "r", encoding="utf-8") as f:
                dati = json.load(f)
                break
        except (OSError, ValueError):
            continue
    if dati is None:
        dati = dict(_VUOTA)
    _cache[serie_id] = dati
    return dati


def poster(serie_id):
    return _serie(serie_id).get("poster", "")


def sfondo(serie_id):
    return _serie(serie_id).get("sfondo", "")


def poster_percorso(pid):
    """Locandina di un PERCORSO (una saga), non di una serie.

    Se il percorso ne dichiara una sua (`"poster"` in catalogo.PERCORSI) usa
    quella; altrimenti ripiega sulla prima serie del percorso. Serve perche'
    due percorsi che cominciano con la stessa serie - "Dragon Ball" e
    "Dragon Ball - via veloce", "Mazinga" e "I robot di Go Nagai" - altrimenti
    mostravano la STESSA identica locandina, e due saghe uguali sono impossibili.
    """
    from . import catalogo
    p = catalogo.PERCORSI.get(pid) or {}
    if p.get("poster"):
        return p["poster"]
    seg = p.get("segmenti") or []
    return poster(seg[0][0]) if seg else ""


def sfondo_percorso(pid):
    """Sfondo di un percorso, con la stessa regola di poster_percorso."""
    from . import catalogo
    p = catalogo.PERCORSI.get(pid) or {}
    if p.get("sfondo"):
        return p["sfondo"]
    seg = p.get("segmenti") or []
    return sfondo(seg[0][0]) if seg else ""


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
