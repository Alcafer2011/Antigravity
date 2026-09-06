# -*- coding: utf-8 -*-
"""Pannello 8K — come sta l'apparecchio, visto dal divano."""
import os
import sys

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stato      # noqa: E402
import registro   # noqa: E402
import azioni     # noqa: E402

ADDON = xbmcaddon.Addon()
NOME = "Pannello 8K"
DATI = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))


def _riga(etichetta, valore):
    return "%-24s %s" % (etichetta + ":", valore)


def _ultimo_crash():
    """La sentinella sul box ci lascia un riepilogo qui: data|uptime|totale."""
    f = os.path.join(DATI, "ultimo-crash.txt")
    try:
        with open(f) as h:
            p = h.read().strip().split("|")
        if len(p) >= 3:
            return "%s  (Kodi girava da %s) — %s in tutto" % (p[0], p[1], p[2])
        return p[0]
    except Exception:
        return "nessuno registrato"


def testo_stato():
    r = []
    r.append("[B]TEMPERATURE[/B]")
    temp = stato.temperature()
    if temp:
        for nome, gradi in temp:
            r.append(_riga("  " + nome, "%.1f °C" % gradi))
        r.append(_riga("  Situazione", stato.giudizio(temp[0][1])))
    else:
        r.append("  (sensori non leggibili)")

    massima, quando, media, campioni = registro.riassunto()
    if massima:
        r.append("")
        r.append(_riga("  Massima registrata", "%.1f °C  il %s" % (massima, quando)))
        if media:
            r.append(_riga("  Media 24 ore", "%.1f °C" % media))
    r.append("")
    r.append("[B]ANDAMENTO ULTIME 12 ORE[/B]")
    r.append(registro.grafico())

    r.append("")
    r.append("[B]SISTEMA[/B]")
    usata, tot, pct = stato.memoria()
    if tot:
        r.append(_riga("  Memoria", "%d MB su %d  (%d%%)" % (usata, tot, pct)))
    r.append(_riga("  Carico", stato.carico()))
    r.append(_riga("  Acceso da", stato.acceso_da()))
    lib, tots, pcts = stato.spazio(stato.cartella_dati())
    if tots:
        r.append(_riga("  Spazio", "%.1f GB liberi su %.1f  (%d%% usato)" % (lib, tots, pcts)))

    r.append("")
    r.append("[B]GUIDA TV[/B]")
    try:
        canali, con_guida = azioni.guida_tv()
        if canali:
            quota = con_guida * 100 // canali
            r.append(_riga("  Canali", "%d" % canali))
            r.append(_riga("  Con programmi", "%d  (%d%%)" % (con_guida, quota)))
            if con_guida == 0:
                r.append("  La guida non e' ancora arrivata: prova")
                r.append("  \"Ricarica lista IPTV e guida TV\".")
        else:
            r.append("  (nessun canale: IPTV Simple e' spento?)")
    except Exception:
        r.append("  (non leggibile adesso)")

    r.append("")
    r.append("[B]KODI[/B]")
    r.append(_riga("  Versione", xbmc.getInfoLabel("System.BuildVersion").split(" ")[0]))
    r.append(_riga("  Indirizzo di rete", xbmc.getInfoLabel("Network.IPAddress") or "?"))
    r.append(_riga("  Ultimo crash", _ultimo_crash()))
    return "\n".join(r)


VOCI = [
    ("Aggiorna la schermata", None),
    ("Prova la velocità di internet", azioni.prova_velocita),
    ("Aggiorna canali e guida TV", azioni.aggiorna_canali),
    ("Ricarica lista IPTV e guida TV", azioni.ricarica_iptv),
    ("Riapplica le traduzioni italiane", azioni.riapplica_traduzioni),
    ("Svuota le cache degli add-on", azioni.svuota_cache_addon),
    ("Svuota le immagini temporanee", azioni.svuota_cache_immagini),
    ("Metti la TV in standby", azioni.spegni_schermo),
    ("Riavvia Kodi", "riavvia"),
    ("Impostazioni (allarme e automatismi)", "impostazioni"),
    ("Chiudi", "chiudi"),
]


def main():
    while True:
        xbmcgui.Dialog().textviewer(NOME, testo_stato())
        scelta = xbmcgui.Dialog().select(NOME + " — cosa faccio?", [v[0] for v in VOCI])
        if scelta == -1:
            break
        fn = VOCI[scelta][1]
        if fn is None:
            continue
        if fn == "chiudi":
            break
        if fn == "impostazioni":
            ADDON.openSettings()
        elif fn == "riavvia":
            if xbmcgui.Dialog().yesno(NOME, "Riavvio Kodi adesso?"):
                xbmc.executebuiltin("RestartApp")
                break
        else:
            fn()


if __name__ == "__main__":
    main()
