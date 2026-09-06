# -*- coding: utf-8 -*-
"""Le azioni del pannello: cose che Kodi puo' davvero fare da solo."""
import json
import os
import time
import urllib.request

import xbmc
import xbmcgui
import xbmcvfs

NOME = "Pannello 8K"


def _rpc(metodo, params=None):
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}})
    try:
        return json.loads(xbmc.executeJSONRPC(corpo))
    except Exception:
        return {}


def prova_velocita():
    """Scarica un po' di dati e misura. Consuma ~8 MB del piano."""
    if not xbmcgui.Dialog().yesno(NOME,
                                  "La prova scarica circa 8 MB dal tuo piano dati.\nProcedo?"):
        return
    prog = xbmcgui.DialogProgress()
    prog.create(NOME, "Misuro la velocità...")
    try:
        url = "https://speed.cloudflare.com/__down?bytes=8000000"
        inizio = time.time()
        letti = 0
        req = urllib.request.Request(url, headers={"User-Agent": "Kodi"})
        with urllib.request.urlopen(req, timeout=60) as r:
            while True:
                if prog.iscanceled():
                    prog.close()
                    return
                pezzo = r.read(65536)
                if not pezzo:
                    break
                letti += len(pezzo)
                pct = min(99, int(letti * 100 / 8000000))
                prog.update(pct, "Scaricati %.1f MB" % (letti / 1048576.0))
        durata = max(0.1, time.time() - inizio)
        mbps = (letti * 8) / (durata * 1000000.0)
        prog.close()
        giudizio = ("ottima" if mbps > 25 else "buona" if mbps > 12 else
                    "sufficiente per un film" if mbps > 6 else "bassa: un solo video alla volta")
        xbmcgui.Dialog().ok(NOME,
                            "Velocità in scarico: [B]%.1f Mbps[/B]\n"
                            "(%.1f MB in %.1f secondi)\n\nGiudizio: %s" % (mbps, letti / 1048576.0, durata, giudizio))
    except Exception as e:
        prog.close()
        xbmcgui.Dialog().ok(NOME, "Prova non riuscita:\n%s" % e)


def svuota_cache_immagini():
    p = xbmcvfs.translatePath("special://temp/")
    n = 0
    for radice, _d, file in os.walk(p):
        for f in file:
            if f.endswith((".jpg", ".png", ".tbn")):
                try:
                    os.remove(os.path.join(radice, f))
                    n += 1
                except Exception:
                    pass
    xbmcgui.Dialog().notification(NOME, "Rimossi %d file temporanei" % n, xbmcgui.NOTIFICATION_INFO, 4000)


def svuota_cache_addon(silenzioso=False):
    """Svuota le cache degli add-on video (s4me, Filmix...): risolve i cataloghi bloccati."""
    base = xbmcvfs.translatePath("special://profile/addon_data/")
    tolti = 0
    for a in os.listdir(base) if os.path.isdir(base) else []:
        for nome in ("cache", "Cache"):
            c = os.path.join(base, a, nome)
            if os.path.isdir(c):
                for radice, _d, file in os.walk(c):
                    for f in file:
                        try:
                            os.remove(os.path.join(radice, f))
                            tolti += 1
                        except Exception:
                            pass
    if not silenzioso:
        xbmcgui.Dialog().notification(NOME, "Svuotate le cache: %d file" % tolti, xbmcgui.NOTIFICATION_INFO, 4000)
    return tolti


def aggiorna_canali():
    """Rilegge le liste IPTV e la guida."""
    _rpc("PVR.Scan")
    xbmc.executebuiltin("UpdateAddonRepos")
    xbmcgui.Dialog().notification(NOME, "Aggiornamento canali avviato", xbmcgui.NOTIFICATION_INFO, 4000)


def spegni_schermo():
    """Manda la TV in standby via CEC (se la TV lo supporta)."""
    xbmc.executebuiltin("CECStandby")
    xbmcgui.Dialog().notification(NOME, "Comando di standby inviato alla TV", xbmcgui.NOTIFICATION_INFO, 3000)


# ---------------------------------------------------------------- v1.2.0

IPTV = "pvr.iptvsimple"
TRADUTTORE = "script.traduttore.it"


def _addon_installato(addon_id):
    r = _rpc("Addons.GetAddonDetails", {"addonid": addon_id, "properties": ["enabled"]})
    return "result" in r


def ricarica_iptv(silenzioso=False):
    """Rilegge da capo le liste dei canali e la guida TV.

    PVR.Scan da solo NON rilegge il file M3U: spegnere e riaccendere l'add-on
    IPTV Simple e' l'unico modo, da dentro Kodi, per fargli ripartire la
    lettura delle liste e lo scarico dell'XMLTV.
    """
    if not _addon_installato(IPTV):
        if not silenzioso:
            xbmcgui.Dialog().ok(NOME, "L'add-on IPTV Simple non risulta installato.")
        return False
    prog = None
    if not silenzioso:
        prog = xbmcgui.DialogProgress()
        prog.create(NOME, "Ricarico canali e guida TV...")
        prog.update(20)
    _rpc("Addons.SetAddonEnabled", {"addonid": IPTV, "enabled": False})
    for _ in range(20):
        if xbmc.Monitor().waitForAbort(0.5):
            break
    if prog:
        prog.update(60, "Riaccendo IPTV Simple...")
    _rpc("Addons.SetAddonEnabled", {"addonid": IPTV, "enabled": True})
    if xbmc.Monitor().waitForAbort(3):
        pass
    _rpc("PVR.Scan")
    if prog:
        prog.update(100)
        prog.close()
    if not silenzioso:
        xbmcgui.Dialog().notification(
            NOME, "Canali e guida in ricarica: fra un minuto sono pronti",
            xbmcgui.NOTIFICATION_INFO, 6000)
    xbmc.log("[%s] ricarica IPTV richiesta" % NOME, xbmc.LOGINFO)
    return True


def riapplica_traduzioni(silenzioso=False):
    """Rimette l'italiano negli add-on che un aggiornamento ha riportato in
    inglese o tedesco. Il lavoro vero lo fa l'add-on Traduttore IT."""
    if not _addon_installato(TRADUTTORE):
        if not silenzioso:
            xbmcgui.Dialog().ok(NOME, "L'add-on Traduttore IT non risulta installato.")
        return False
    xbmc.executebuiltin("RunScript(%s,apply,all)" % TRADUTTORE)
    if not silenzioso:
        xbmcgui.Dialog().notification(NOME, "Traduzioni in riapplicazione",
                                      xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.log("[%s] riapplicazione traduzioni avviata" % NOME, xbmc.LOGINFO)
    return True


def guida_tv():
    """(canali, con_programma) — quanti canali hanno davvero la guida.

    Si chiede a Kodi il programma in onda su ogni canale: e' una sola chiamata
    e dice piu' di qualunque conteggio di righe nel file XMLTV.
    """
    canali = con = 0
    for tipo in ("tv", "radio"):
        r = _rpc("PVR.GetChannels", {"channelgroupid": "all" + tipo,
                                     "properties": ["broadcastnow"]})
        for c in (r.get("result", {}) or {}).get("channels", []) or []:
            canali += 1
            ora = c.get("broadcastnow")
            if ora and ora.get("title"):
                con += 1
    return canali, con
