# -*- coding: utf-8 -*-
"""
Sincronizzazione del "dove sono arrivato" fra i due apparecchi.

Il quaderno comune sta sul Raspberry (sempre acceso). Questo modulo lo
interroga e gli manda gli aggiornamenti. Se il Raspberry non risponde non
succede niente di male: si continua col registro locale e si risincronizza
la volta dopo. Nessuna funzione qui dentro deve poter rompere la
riproduzione: per questo ogni cosa e' avvolta in un try.
"""
import json
import time

try:
    from urllib.request import Request, urlopen
except ImportError:                      # non dovrebbe servire su Kodi 20
    from urllib2 import Request, urlopen  # noqa

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ATTESA = 4                # secondi: oltre, si rinuncia e si va avanti locale
_ultimo_tentativo = [0.0]  # per non martellare il quaderno a ogni schermata


def _indirizzo():
    """Dove sta il quaderno. Vuoto = sincronizzazione spenta."""
    try:
        v = (ADDON.getSetting("hub_indirizzo") or "").strip()
    except Exception:
        v = ""
    if not v:
        return ""
    if not v.startswith("http"):
        v = "http://" + v  # atlante: http voluto - il quaderno comune sta in casa, sulla rete locale
    return v.rstrip("/") + "/progressi"


def attiva():
    return bool(_indirizzo())


def _chiama(dati=None, timeout=ATTESA):
    url = _indirizzo()
    if not url:
        return None
    try:
        if dati is None:
            req = Request(url)
        else:
            req = Request(url, data=json.dumps(dati).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        xbmc.log("[Le Saghe] quaderno comune non raggiungibile: %s" % e, xbmc.LOGDEBUG)
        return None


def unisci_da_remoto(locale, ogni_secondi=20):
    """Restituisce il registro locale arricchito con quello comune.

    `ogni_secondi` evita di interrogare il Raspberry a ogni singola riga di
    elenco: sfogliare 659 tappe farebbe centinaia di chiamate inutili.
    """
    if not attiva():
        return locale
    adesso = time.time()
    if adesso - _ultimo_tentativo[0] < ogni_secondi:
        return locale
    _ultimo_tentativo[0] = adesso
    remoto = _chiama()
    if not remoto:
        return locale
    return _fondi(locale, remoto)


def manda(locale):
    """Manda al quaderno quello che sappiamo noi. Non blocca se non risponde."""
    if not attiva():
        return locale
    _ultimo_tentativo[0] = time.time()
    unito = _chiama(locale)
    return unito or locale


def _fondi(a, b):
    """Stessa regola del quaderno: posizione piu' recente, visti sommati."""
    fuori = dict(a or {})
    fuori.setdefault("percorsi", {})
    for pid, sb in ((b or {}).get("percorsi") or {}).items():
        sa = fuori["percorsi"].get(pid)
        if not sa:
            fuori["percorsi"][pid] = sb
            continue
        visti = set(sa.get("visti") or []) | set(sb.get("visti") or [])
        if int(sb.get("aggiornato", 0)) > int(sa.get("aggiornato", 0)):
            unito = dict(sb)
        else:
            unito = dict(sa)
        unito["visti"] = sorted(visti)
        fuori["percorsi"][pid] = unito
    return fuori
