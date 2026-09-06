# -*- coding: utf-8 -*-
"""
IL CUSTODE: rimette il nostro canale dentro s4me, e lo tiene li'.

IL PROBLEMA
    Il nostro canale (`lesaghe.py`) deve stare dentro la cartella di s4me
    per essere eseguito da s4me. Ma s4me si aggiorna spesso - quasi sempre
    solo per inseguire i domini dei provider che cambiano - e un
    aggiornamento puo' portarsi via i file che non gli appartengono.

LA SOLUZIONE, gia' collaudata altrove in questa casa
    Non si spera che sopravviva: si RIMETTE. A ogni avvio di Kodi il
    custode controlla e, se manca o e' vecchio, ricopia. E' lo stesso
    schema del ritocco che riapplichiamo a Vavoo dopo ogni suo
    aggiornamento, e li' funziona da mesi.

COSA NON FA, ed e' importante
    Non tocca NESSUN file di s4me. Aggiunge due file suoi
    (`channels/lesaghe.py` e `channels/lesaghe.json`) e basta. Se un giorno
    si vuole tornare indietro basta cancellarli: s4me non si accorge di
    niente, perche' non e' stato modificato.
"""

import os
import shutil

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
S4ME = "plugin.video.s4me"
# I due canali che mettiamo dentro s4me:
#   lesaghe      - il catalogo cronologico
#   abbonamenti  - risponde a OGNI ricerca di s4me offrendo Netflix, Prime
#                  e Mediaset, cosi' quando i siti non hanno una cosa ma tu
#                  ce l'hai in abbonamento, la ricerca te lo dice lo stesso
FILE = ("lesaghe.py", "lesaghe.json",
        "abbonamenti.py", "abbonamenti.json")


def _nostra_cartella():
    return os.path.join(
        xbmcvfs.translatePath(ADDON.getAddonInfo("path")),
        "resources", "canale")


def _cartella_s4me():
    p = xbmcvfs.translatePath("special://home/addons/%s/channels" % S4ME)
    return p if os.path.isdir(p) else ""


def stato():
    """(installato, aggiornato, dove). Serve anche alla schermata di stato."""
    dove = _cartella_s4me()
    if not dove:
        return False, False, ""
    nostra = _nostra_cartella()
    installato = all(os.path.exists(os.path.join(dove, f)) for f in FILE)
    if not installato:
        return False, False, dove
    aggiornato = True
    for f in FILE:
        a = os.path.join(nostra, f)
        b = os.path.join(dove, f)
        try:
            if os.path.getsize(a) != os.path.getsize(b) or \
                    os.path.getmtime(a) > os.path.getmtime(b):
                aggiornato = False
        except OSError:
            aggiornato = False
    return True, aggiornato, dove


def assicura(forza=False):
    """Mette il canale al suo posto se manca o e' vecchio.

    Restituisce (fatto, spiegazione). Non solleva mai: se s4me non c'e' o
    la copia non riesce, il nostro add-on deve funzionare lo stesso.
    """
    dove = _cartella_s4me()
    if not dove:
        return False, "s4me non e' installato: non c'e' dove mettere il canale"

    installato, aggiornato, _ = stato()
    if installato and aggiornato and not forza:
        return False, "gia' a posto"

    nostra = _nostra_cartella()
    copiati = []
    for f in FILE:
        a = os.path.join(nostra, f)
        if not os.path.exists(a):
            return False, "manca il file di partenza: %s" % f
        try:
            shutil.copy2(a, os.path.join(dove, f))
            copiati.append(f)
        except OSError as e:
            return False, "non sono riuscito a copiare %s: %s" % (f, e)

    # Il pacchetto Python di s4me tiene una cache: se resta quella vecchia,
    # s4me continua a eseguire il canale di prima senza dirlo a nessuno.
    for c in ("__pycache__",):
        p = os.path.join(dove, c)
        if os.path.isdir(p):
            for n in os.listdir(p):
                if n.startswith(("lesaghe.", "abbonamenti.")):
                    try:
                        os.remove(os.path.join(p, n))
                    except OSError:
                        pass

    xbmc.log("[Le Saghe] canale installato dentro s4me: %s"
             % ", ".join(copiati), xbmc.LOGINFO)
    return True, "canale messo dentro s4me (%s)" % ", ".join(copiati)


def togli():
    """Toglie il canale da s4me. s4me resta esattamente com'era."""
    dove = _cartella_s4me()
    if not dove:
        return False, "s4me non e' installato"
    tolti = []
    for f in FILE:
        p = os.path.join(dove, f)
        if os.path.exists(p):
            try:
                os.remove(p)
                tolti.append(f)
            except OSError:
                pass
    return bool(tolti), ("tolto: %s" % ", ".join(tolti)) if tolti else "non c'era"


def racconta():
    """Lo stato, in parole, per la schermata delle impostazioni."""
    installato, aggiornato, dove = stato()
    if not dove:
        return ("s4me non e' installato su questo apparecchio.\n\n"
                "Il canale 'Le Saghe' dentro s4me serve a far riprodurre gli "
                "episodi dal suo motore, che e' molto piu' forte del nostro: "
                "55 fonti, aggiornate di continuo.")
    if not installato:
        return ("Il canale non e' ancora dentro s4me.\n\n"
                "Verra' messo al prossimo avvio di Kodi, oppure subito da "
                "qui.")
    if not aggiornato:
        return ("Il canale dentro s4me e' una versione vecchia.\n\n"
                "Verra' aggiornato al prossimo avvio di Kodi.")
    return ("Il canale e' dentro s4me e aggiornato.\n\n"
            "Lo trovi fra i canali di s4me come [B]Le Saghe - in ordine "
            "cronologico[/B]. Da li' gli episodi si aprono col motore di "
            "s4me: 55 fonti, nessuna pubblicita', e il segno di dove sei "
            "arrivato tenuto da lui.\n\n"
            "Se un aggiornamento di s4me se lo porta via, torna da solo al "
            "riavvio successivo.")
