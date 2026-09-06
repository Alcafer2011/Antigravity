# -*- coding: utf-8 -*-
"""Sorveglia la temperatura e avvisa sullo schermo quando sale troppo.

Gira in sottofondo finche' Kodi e' acceso. Non fa nulla di pesante: legge
quattro file di sistema ogni tot minuti.
"""
import os
import sys
import time

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stato     # noqa: E402
import registro  # noqa: E402
import azioni    # noqa: E402

ADDON = xbmcaddon.Addon()
NOME = "Pannello 8K"
DATI = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
SEGNO_MANUTENZIONE = os.path.join(DATI, "ultima-manutenzione.txt")

# Doppia sicura: il file dice "fatta" anche dopo un riavvio di Kodi, ma se per
# qualunque motivo non si riesce a scriverlo la manutenzione si ripeterebbe a
# ogni giro per tutta l'ora. Questa variabile la ferma dentro la sessione.
_fatta_in_memoria = ""


def _num(chiave, default):
    try:
        return int(ADDON.getSetting(chiave))
    except Exception:
        return default


def _si(chiave, default=True):
    v = ADDON.getSetting(chiave)
    if v == "":
        return default
    return v.lower() == "true"



def _gia_fatta_oggi():
    if _fatta_in_memoria == time.strftime("%Y-%m-%d"):
        return True
    try:
        with open(SEGNO_MANUTENZIONE) as f:
            return f.read().strip() == time.strftime("%Y-%m-%d")
    except Exception:
        return False


def _segna_fatta():
    global _fatta_in_memoria
    _fatta_in_memoria = time.strftime("%Y-%m-%d")
    try:
        if not os.path.isdir(DATI):
            os.makedirs(DATI)
        with open(SEGNO_MANUTENZIONE, "w") as f:
            f.write(time.strftime("%Y-%m-%d"))
    except Exception as e:
        xbmc.log("[%s] non riesco a segnare la manutenzione: %s" % (NOME, e), xbmc.LOGWARNING)


def manutenzione_se_e_ora():
    """Una volta al giorno, all'ora scelta, rimette a posto le cose che si
    sporcano da sole. Non parte mai mentre si sta guardando qualcosa."""
    if not _si("manutenzione_attiva", False):
        return
    if int(time.strftime("%H")) != _num("ora_manutenzione", 5):
        return
    if _gia_fatta_oggi():
        return
    if xbmc.Player().isPlaying():
        return  # si riprova al giro dopo: l'ora dura 60 minuti

    _segna_fatta()
    fatto = []
    try:
        if _si("man_ricarica_iptv", True):
            if azioni.ricarica_iptv(silenzioso=True):
                fatto.append("canali e guida ricaricati")
        if _si("man_svuota_cache", True):
            azioni.svuota_cache_addon(silenzioso=True)
            fatto.append("cache degli add-on svuotate")
        if _si("man_traduzioni", False):
            if azioni.riapplica_traduzioni(silenzioso=True):
                fatto.append("traduzioni riapplicate")
    except Exception as e:
        xbmc.log("[%s] manutenzione interrotta: %s" % (NOME, e), xbmc.LOGERROR)

    xbmc.log("[%s] manutenzione notturna: %s" % (NOME, ", ".join(fatto) or "niente da fare"),
             xbmc.LOGINFO)
    if fatto and _si("man_avvisa", False):
        xbmcgui.Dialog().notification(NOME, "Manutenzione fatta: " + ", ".join(fatto),
                                      xbmcgui.NOTIFICATION_INFO, 6000)


def main():
    monitor = xbmc.Monitor()
    ultimo_avviso = 0.0
    xbmc.log("[%s] sorveglianza temperatura avviata" % NOME, xbmc.LOGINFO)

    while not monitor.abortRequested():
        attesa = max(60, _num("intervallo", 5) * 60)
        if monitor.waitForAbort(attesa):
            break

        try:
            manutenzione_se_e_ora()
        except Exception as e:
            xbmc.log("[%s] errore negli automatismi: %s" % (NOME, e), xbmc.LOGERROR)

        if not _si("allarme_attivo", True):
            continue

        try:
            nome, gradi = stato.piu_calda()
            if not nome:
                continue
            registro.annota(gradi, nome)
            soglia = _num("soglia", 80)
            if gradi < soglia:
                continue

            ripeti = max(5, _num("ripeti_ogni", 30)) * 60
            adesso = time.time()
            if adesso - ultimo_avviso < ripeti:
                continue
            ultimo_avviso = adesso

            xbmcgui.Dialog().notification(
                "Attenzione: apparecchio caldo",
                "%s a %.0f °C — libera le feritoie" % (nome, gradi),
                xbmcgui.NOTIFICATION_WARNING, 10000)
            xbmc.log("[%s] TEMPERATURA ALTA: %s %.1f C (soglia %d)" % (NOME, nome, gradi, soglia), xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log("[%s] errore nella sorveglianza: %s" % (NOME, e), xbmc.LOGERROR)

    xbmc.log("[%s] sorveglianza terminata" % NOME, xbmc.LOGINFO)


if __name__ == "__main__":
    main()
