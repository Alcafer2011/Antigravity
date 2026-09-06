# -*- coding: utf-8 -*-
"""
CHE SI CAPISCANO LE PAROLE.

Il problema, spiegato bene: in una traccia 5.1 le voci stanno quasi tutte nel
canale CENTRALE, mentre musica ed effetti stanno nei canali laterali. Quando
quella traccia viene schiacciata su due canali - ed e' quello che fa il tuo
Raspberry, perche' l'uscita e' stereo - il centro viene sommato agli altri e
la voce finisce sepolta. Alzi il volume e ti spacchi i timpani sugli effetti,
senza capire meglio le parole.

COSA SI PUO' FARE DAVVERO (verificato sul campo il 05/09/2026)
  * Kodi 20 ha TOLTO l'impostazione "potenzia il canale centrale".
  * Su LibreELEC non ci sono plugin ALSA ne' LADSPA: un compressore audio di
    sistema non si puo' installare senza ricompilare il firmware.
  * QUELLO CHE RESTA, ed e' la leva piu' efficace: SCEGLIERE LA TRACCIA GIUSTA.
    Quando un film ha sia il 5.1 sia una traccia stereo, la stereo NON e' un
    ripiego: e' un missaggio fatto apposta per due casse, con le voci gia'
    bilanciate. Su un'uscita stereo si capisce molto di piu' di un 5.1
    schiacciato al volo.

Quindi questo modulo non "filtra" l'audio (sarebbe una promessa che non
possiamo mantenere): sceglie, fra quelle che ci sono, la traccia in cui le
parole si sentono meglio. E lo fa da solo, a ogni riproduzione.
"""
import json

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()

# Tracce da non scegliere mai: non sono il film, sono commenti o descrizioni.
_DA_EVITARE = ("commentary", "commento", "descriptive", "audiodescri",
               "narrazione", "director")

_ITALIANO = ("it", "ita", "italian", "italiano")


def _rpc(metodo, params=None):
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}})))
    except Exception:
        return {}


def _uscita_stereo():
    """L'apparecchio sta suonando in stereo? Solo allora il problema esiste."""
    r = _rpc("Settings.GetSettingValue", {"setting": "audiooutput.channels"})
    v = (r.get("result") or {}).get("value")
    # nell'elenco di Kodi 1 = 2.0 (stereo). Tutto il resto e' multicanale.
    return v in (0, 1, None)


def _e_italiana(t):
    lingua = (t.get("language") or "").lower()
    nome = (t.get("name") or "").lower()
    return lingua in _ITALIANO or any(x in nome for x in ("italian", "ita"))


def _punteggio(t, preferisci_stereo):
    """Quanto e' adatta questa traccia a farsi CAPIRE.

    L'ordine dei pesi non e' casuale: la lingua viene prima di tutto (una
    traccia inglese cristallina non serve a niente), poi il numero di canali.
    """
    nome = ((t.get("name") or "") + " " + (t.get("language") or "")).lower()
    if any(x in nome for x in _DA_EVITARE):
        return -1000
    p = 0
    if _e_italiana(t):
        p += 1000                     # la lingua e' la prima cosa
    canali = int(t.get("channels") or 0)
    if preferisci_stereo:
        # 2 canali = missaggio nato per due casse: le voci sono gia' a posto
        if canali == 2:
            p += 100
        elif canali > 2:
            p += 20                   # meglio di niente, ma va schiacciato
    else:
        if canali > 2:
            p += 100                  # impianto multicanale: tanto vale usarlo
        else:
            p += 20
    return p


def scegli_traccia_migliore():
    """Sceglie la traccia audio in cui le parole si capiscono di piu'.

    Restituisce (cambiata, spiegazione). Non fa nulla se c'e' una traccia sola
    o se quella giusta e' gia' attiva: cambiare per niente farebbe saltare
    l'audio per un istante, e si sente.
    """
    r = _rpc("Player.GetActivePlayers")
    giocatori = r.get("result") or []
    if not giocatori:
        return False, "niente in riproduzione"
    pid = giocatori[0]["playerid"]

    r = _rpc("Player.GetProperties", {"playerid": pid,
                                      "properties": ["audiostreams", "currentaudiostream"]})
    res = r.get("result") or {}
    tracce = res.get("audiostreams") or []
    attuale = res.get("currentaudiostream") or {}
    if len(tracce) < 2:
        return False, "c'e' una sola traccia: non c'e' niente da scegliere"

    stereo = _uscita_stereo()
    migliore = max(tracce, key=lambda t: _punteggio(t, stereo))
    if migliore.get("index") == attuale.get("index"):
        return False, "la traccia migliore era gia' quella attiva"

    _rpc("Player.SetAudioStream", {"playerid": pid, "stream": migliore["index"]})
    return True, "%s, %d canali" % (migliore.get("language") or migliore.get("name") or "?",
                                    int(migliore.get("channels") or 0))


def descrizione_tracce():
    """A cosa somigliano le tracce di quello che sta suonando. Per diagnosi."""
    r = _rpc("Player.GetActivePlayers")
    giocatori = r.get("result") or []
    if not giocatori:
        return []
    r = _rpc("Player.GetProperties", {"playerid": giocatori[0]["playerid"],
                                      "properties": ["audiostreams", "currentaudiostream"]})
    res = r.get("result") or {}
    attuale = (res.get("currentaudiostream") or {}).get("index")
    fuori = []
    for t in res.get("audiostreams") or []:
        fuori.append("%s%s  %s  %d canali  (%s)" % (
            "> " if t.get("index") == attuale else "  ",
            t.get("index"), t.get("language") or "?",
            int(t.get("channels") or 0), t.get("codec") or "?"))
    return fuori
