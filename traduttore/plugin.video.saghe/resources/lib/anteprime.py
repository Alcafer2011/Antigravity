# -*- coding: utf-8 -*-
"""LE ANTEPRIME: il filmato che parte se resti fermo su una tessera.

Chiesto dall'utente il 10/09/2026: "ha anche le anteprime che si vedono
quando rimani su una locandina".

QUESTO FILE NON RIPRODUCE NIENTE. Trova soltanto l'indirizzo del filmato e
se lo ricorda. A farlo partire e' il servizio, che e' anche l'unico posto
che sa se si sta gia' guardando qualcos'altro.
La separazione non e' pignoleria: cosi' questa parte si puo' provare senza
accendere nessuno schermo.

DA DOVE VIENE IL FILMATO
    TMDb, per ogni serie e ogni film, tiene i `videos`: sono trailer su
    YouTube. Si preferisce, in ordine:
      1. un trailer ITALIANO (iso_639_1 = it)
      2. un trailer qualunque
      3. un "teaser"
    e si scarta tutto il resto (dietro le quinte, interviste, clip): non
    sono anteprime, sono altro.

PERCHE' LA CACHE E' PER SEMPRE (quasi)
    Il trailer di Dragon Ball del 1986 non cambia. Si tiene un mese, e chi
    non ce l'ha resta senza anteprima invece di richiedere ogni volta: una
    ricerca in rete mentre scorri le locandine e' esattamente cio' che
    NON deve succedere.

SE NON C'E' UN TRAILER
    Non succede niente. Nessun avviso, nessuna attesa: la maggior parte
    delle voci (documentari, ricerche a tema, canali) un trailer non ce
    l'ha, ed e' normale.
"""

import io
import json
import os
import time
import urllib.parse
import urllib.request

import xbmcvfs

from resources.lib.tmdb import CHIAVE as CHIAVE_TMDB  # la chiave sta in un posto solo
import xbmc
BASE = "https://api.themoviedb.org/3"
DURATA = 30 * 24 * 60 * 60          # un mese

# I tipi di video che sono davvero un'anteprima, in ordine di preferenza.
BUONI = ("Trailer", "Teaser")


def _file():
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    return os.path.join(c, "anteprime.json")


def _leggi():
    try:
        with io.open(_file(), encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _scrivi(d):
    try:
        with io.open(_file(), "w", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False))
    except Exception as _errore:
        xbmc.log("[Le Saghe] _scrivi: errore ignorato: %s" % _errore, xbmc.LOGDEBUG)


def _chiedi(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return {}


def _scegli(video):
    """Il video migliore fra quelli che TMDb ha, o "" se non ce n'e' uno."""
    def punteggio(v):
        if v.get("site") != "YouTube" or not v.get("key"):
            return -1
        if v.get("type") not in BUONI:
            return -1
        p = 10 if v.get("type") == "Trailer" else 5
        if v.get("iso_639_1") == "it":
            p += 20          # l'italiano viene prima, come sempre qui
        if v.get("official"):
            p += 2
        return p
    migliori = sorted(video, key=punteggio, reverse=True)
    if not migliori or punteggio(migliori[0]) < 0:
        return ""
    return migliori[0]["key"]


def chiave_youtube(tmdb_id, tipo="tv"):
    """La chiave YouTube dell'anteprima. "" se non c'e'.

    PUO' andare in rete: la chiama il servizio in un filo a parte, mai
    l'interfaccia mentre disegni una riga.
    """
    if not tmdb_id:
        return ""
    ck = "%s/%s" % (tipo, tmdb_id)
    cache = _leggi()
    voce = cache.get(ck)
    if voce and (time.time() - voce.get("quando", 0)) < DURATA:
        return voce.get("chiave", "")
    # Prima in italiano; TMDb con `include_video_language` aggiunge i video
    # italiani a quelli originali invece di sostituirli.
    par = urllib.parse.urlencode({
        "api_key": CHIAVE_TMDB, "language": "it-IT",
        "include_video_language": "it,en,null"})
    d = _chiedi("%s/%s/%s/videos?%s" % (BASE, tipo, tmdb_id, par))
    chiave = _scegli(d.get("results") or [])
    cache[ck] = {"quando": time.time(), "chiave": chiave}
    _scrivi(cache)
    return chiave


def indirizzo(chiave):
    """L'indirizzo che Kodi sa aprire. Passa dall'add-on di YouTube: e'
    l'unico che sa trasformare una chiave in un flusso video."""
    if not chiave:
        return ""
    return "plugin://plugin.video.youtube/play/?video_id=%s" % chiave


def per_voce(tmdb_id, tipo="tv"):
    """Scorciatoia: da identificativo TMDb a indirizzo pronto."""
    return indirizzo(chiave_youtube(tmdb_id, tipo))
