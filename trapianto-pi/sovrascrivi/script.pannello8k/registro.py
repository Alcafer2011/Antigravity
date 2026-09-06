# -*- coding: utf-8 -*-
"""Registro delle temperature: massima raggiunta e andamento recente.

Scrive dentro addon_data, l'unica cartella dove Kodi puo' scrivere.
"""
import os
import time

import xbmcaddon
import xbmcvfs

DATI = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
STORICO = os.path.join(DATI, "temperature.csv")
MAX_RIGHE = 2000  # ~7 giorni con un campione ogni 5 minuti


def _assicura():
    if not os.path.isdir(DATI):
        os.makedirs(DATI)


def annota(gradi, nome=""):
    try:
        _assicura()
        with open(STORICO, "a") as f:
            f.write("%d;%.1f;%s\n" % (int(time.time()), gradi, nome))
        _pota()
    except Exception:
        pass


def _pota():
    try:
        with open(STORICO) as f:
            righe = f.readlines()
        if len(righe) > MAX_RIGHE:
            with open(STORICO, "w") as f:
                f.writelines(righe[-MAX_RIGHE:])
    except Exception:
        pass


def _leggi():
    fuori = []
    try:
        with open(STORICO) as f:
            for r in f:
                p = r.strip().split(";")
                if len(p) >= 2:
                    fuori.append((int(p[0]), float(p[1])))
    except Exception:
        pass
    return fuori


def riassunto():
    """(massima, quando_massima, media_24h, campioni)"""
    d = _leggi()
    if not d:
        return (None, None, None, 0)
    massima = max(d, key=lambda x: x[1])
    limite = time.time() - 86400
    ultime = [v for t, v in d if t >= limite]
    media = sum(ultime) / len(ultime) if ultime else None
    return (massima[1], time.strftime("%d/%m alle %H:%M", time.localtime(massima[0])), media, len(d))


def grafico(larghezza=34, ore=12):
    """Un grafico a barre in caratteri delle ultime ore."""
    d = _leggi()
    if not d:
        return "  (nessun dato ancora — serve qualche ora)"
    limite = time.time() - ore * 3600
    d = [(t, v) for t, v in d if t >= limite]
    if len(d) < 2:
        return "  (dati insufficienti — serve qualche ora)"
    # raggruppo in 'larghezza' colonne
    inizio, fine = d[0][0], d[-1][0]
    passo = max(1, (fine - inizio) // larghezza)
    colonne = []
    for i in range(larghezza):
        a, b = inizio + i * passo, inizio + (i + 1) * passo
        v = [x[1] for x in d if a <= x[0] < b]
        colonne.append(max(v) if v else None)
    validi = [c for c in colonne if c is not None]
    if not validi:
        return "  (dati insufficienti)"
    basso, alto = min(validi), max(validi)
    span = max(1.0, alto - basso)
    livelli = "▁▂▃▄▅▆▇█"
    barra = "".join(livelli[min(7, int((c - basso) / span * 7))] if c is not None else " " for c in colonne)
    return "  %s\n  da %.0f a %.0f °C nelle ultime %d ore" % (barra, basso, alto, ore)
