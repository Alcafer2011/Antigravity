# -*- coding: utf-8 -*-
"""L'IMMAGINE A TUTTO SCHERMO, SENZA DEFORMARLA.

PERCHE' (l'utente, 11/09/2026)
    "su tutti gli apparecchi schermo intero automatico secondo lo schermo
    della TV: il video non deve uscire dallo schermo ne' restare piccolo, ma
    senza deformarlo; se riempire deformerebbe, allargalo al massimo
    mantenendo le proporzioni."

COSA FA KODI, E DOVE SBAGLIA
    La modalita' "Normale" fa esattamente questo: allarga il video finche'
    tocca due bordi, senza tagliare e senza stirare. E' gia' la predefinita
    sui tre apparecchi (guisettings: viewmode 0, zoom 1, pixel 1 - servi.py la
    rimette a ogni installazione). Il guaio e' che Kodi RICORDA lo zoom di ogni
    singolo video: basta aver premuto una volta il tasto delle proporzioni, o
    averlo toccato per sbaglio, e quel video riparte ogni volta zoomato (esce
    dallo schermo) o rimpicciolito. Qui, a ogni video che parte, si torna a
    "Normale". Uno zoom scelto DURANTE il video non si tocca: si interviene
    solo all'avvio.

COSA NON SI PUO' FARE
    Riempire una TV 16:9 con un video 4:3 o 2,39:1 senza bande nere vuol dire
    tagliare o deformare: l'utente non vuole ne' l'uno ne' l'altro, quindi le
    bande restano. E se i bordi escono dalla TV anche in "Normale", e' la TV
    che ingrandisce (overscan): si toglie dal suo menu, formato immagine
    "Adatta allo schermo" o "Punto per punto".
"""
import json

import xbmc

NORMALE = "normal"


def _rpc(metodo, params=None):
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}})))
    except (ValueError, TypeError):
        return {}


def _numero(valore, difetto):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return difetto


def gia_normale(stato):
    """Il modo letto da Player.GetViewMode e' gia' "Normale" senza ritocchi?"""
    return (stato.get("viewmode") == NORMALE
            and abs(_numero(stato.get("zoom"), 1.0) - 1.0) < 0.01
            and abs(_numero(stato.get("pixelratio"), 1.0) - 1.0) < 0.01
            and abs(_numero(stato.get("verticalshift"), 0.0)) < 0.01
            and not stato.get("nonlinearstretch"))


def adatta_allo_schermo():
    """Rimette "Normale" se il video e' partito zoomato o stirato.

    Restituisce cosa ha fatto, in parole, oppure "" se non c'era niente da fare."""
    if not xbmc.getCondVisibility("Player.HasVideo"):
        return ""
    stato = _rpc("Player.GetViewMode").get("result") or {}
    if stato and gia_normale(stato):
        return ""
    risposta = _rpc("Player.SetViewMode", {"viewmode": NORMALE})
    if "error" in risposta:
        return "non riuscito: %s" % risposta["error"]
    return "era %s (zoom %s) -> normale" % (stato.get("viewmode", "?"), stato.get("zoom", "?"))
