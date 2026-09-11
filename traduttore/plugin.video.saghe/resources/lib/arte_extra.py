# -*- coding: utf-8 -*-
"""LE IMMAGINI TROVATE SUL PC PER LE VOCI CHE NE ERANO SENZA.

PERCHE' (chiesto dall'utente l'11/09/2026: "uno script per la ricerca delle
locandine che mancano a livello di tutti i servizi che le espongono, non
credo che solo TMDb le fornisca")
    `traduttore/locandine.py` gira sul PC: scorre tutte le voci della
    Videoteca come le vede Kodi e, per quelle senza immagine, con un
    segnaposto o con un indirizzo morto, cerca su TMDb, TVmaze, AniList,
    Kitsu, iTunes, Wikidata e fanart.tv. Scrive `resources/arte_extra.json`.

QUI SI APPLICA
    Al momento in cui una voce entra nell'elenco (`aggancia`), e SOLO per le
    chiavi che non ha gia': un'immagine buona non si copre mai. Nessuna rete:
    e' un file dell'add-on, arriva con gli aggiornamenti.
    Questo modulo non importa niente di Kodi: lo usa anche locandine.py sul PC,
    cosi' le chiavi del file si calcolano in UN modo solo.
"""

import io
import json
import os
import re
import unicodedata
from urllib.parse import parse_qsl, urlsplit

# Le immagini che una voce puo' ricevere. `thumb` solo se nel file e' gia'
# orizzontale: una locandina verticale su thumb la skin la STIRA (10/09/2026).
CHIAVI_ARTE = ("poster", "fanart", "landscape", "thumb", "clearlogo", "keyart",
               "banner", "clearart", "discart")
SEGNAPOSTI = ("resources/icon.png", "resources/segnaposto.png", "/Default", "Default")
# I parametri che dicono QUALE voce e': gli altri (pagina, nuova=1...) no.
STABILI = ("azione", "percorso", "tmdb", "id", "canale", "cosa", "gruppo", "reparto",
           "scaffale", "che", "sez", "g", "serie", "titolo", "titolo_film")

_DATI = None


def _file():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arte_extra.json")


def _leggi():
    global _DATI
    if _DATI is None:
        try:
            with io.open(_file(), encoding="utf-8") as f:
                _DATI = json.load(f) or {}
        except (OSError, ValueError):
            _DATI = {}
    return _DATI


def chiave_indirizzo(indirizzo):
    """La chiave di una voce dal suo indirizzo, senza i parametri che cambiano."""
    indirizzo = indirizzo or ""
    if not indirizzo.startswith("plugin://plugin.video.saghe"):
        return "url:" + indirizzo
    q = dict(parse_qsl(urlsplit(indirizzo).query))
    return "saghe:" + "&".join("%s=%s" % (k, q[k]) for k in STABILI if q.get(k))


def chiave_titolo(etichetta):
    """La chiave di una voce dal suo titolo: prima riga, senza colori ne' accenti."""
    t = re.sub(r"\[/?(?:B|I|COLOR[^\]]*|UPPERCASE|LOWERCASE|LIGHT)\]", "", etichetta or "")
    t = t.split("\n")[0].strip().lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return "titolo:" + re.sub(r"[^a-z0-9]+", " ", t).strip()


def vuota(valore):
    return not valore or any(s in valore for s in SEGNAPOSTI)


def metti_se_mancano(li, arte):
    """Mette le immagini di `arte` che la voce non ha (o ha come segnaposto)."""
    nuove = {k: v for k, v in (arte or {}).items() if k in CHIAVI_ARTE and v and vuota(li.getArt(k))}
    if nuove:
        li.setArt(nuove)
    return nuove


def completa(li, indirizzo):
    dati = _leggi()
    if not dati:
        return {}
    extra = dati.get(chiave_indirizzo(indirizzo)) or dati.get(chiave_titolo(li.getLabel()))
    return metti_se_mancano(li, extra) if extra else {}


def aggancia(xbmcplugin):
    """Ogni voce aggiunta all'elenco passa prima da `completa`. Una volta sola."""
    originale = xbmcplugin.addDirectoryItem
    if getattr(originale, "_con_arte_extra", False):
        return

    def aggiungi(*argomenti, **nominati):
        try:
            indirizzo = argomenti[1] if len(argomenti) > 1 else nominati.get("url", "")
            li = argomenti[2] if len(argomenti) > 2 else nominati.get("listitem")
            if li is not None:
                completa(li, indirizzo)
        except Exception as errore:           # un'immagine in piu' non vale una voce persa
            import xbmc
            xbmc.log("[Le Saghe] arte in piu': %s" % errore, xbmc.LOGDEBUG)
        return originale(*argomenti, **nominati)

    aggiungi._con_arte_extra = True
    xbmcplugin.addDirectoryItem = aggiungi
