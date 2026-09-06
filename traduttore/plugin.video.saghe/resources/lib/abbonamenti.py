# -*- coding: utf-8 -*-
"""
Il pannello "I miei abbonamenti".

Non un elenco di interruttori, ma la risposta a una domanda sola:
**cosa mi sblocca ogni abbonamento, in episodi veri.**
"""

from . import catalogo, fonti

# Prezzi in Italia, verificati il 04/09/2026.
PREZZI = {
    "netflix": "da 5,99 €/mese",
    "prime": "4,99 €/mese - 49,90 €/anno",
    "disney": "da 5,99 €/mese",
    "crunchyroll": "da 5,99 €/mese",
    "infinity": "gratis",
    "youtube": "gratis",
    "pluto": "gratis",
}


def _episodi_per_fonte():
    """Quanti episodi porta ogni fonte, contati sulle saghe vere."""
    conto = {}
    for pid in catalogo.ORDINE_PERCORSI:
        # La via veloce e' un doppione di Dragon Ball: non la conto due volte.
        if pid == "dragonball_veloce":
            continue
        for t in catalogo.catena(pid):
            for f in catalogo.SERIE[t["serie"]]["fonti"]:
                conto[f] = conto.get(f, 0) + 1
    return conto


def riepilogo():
    """Elenco ordinato di dizionari, pronto da mostrare.

    Ogni voce: id, nome, posseduta, gratis, episodi, prezzo, esclusivi
    ("esclusivi" = episodi che SOLO quella fonte ti darebbe, oggi).
    """
    conto = _episodi_per_fonte()
    posseduti = {f for f in catalogo.FONTI if fonti.possiede(f)}

    # Episodi che oggi non puoi vedere con nulla di cio' che hai.
    scoperti = {}
    for pid in catalogo.ORDINE_PERCORSI:
        if pid == "dragonball_veloce":
            continue
        for t in catalogo.catena(pid):
            elenco = catalogo.SERIE[t["serie"]]["fonti"]
            if any(f in posseduti for f in elenco):
                continue
            for f in elenco:
                scoperti[f] = scoperti.get(f, 0) + 1

    voci = []
    for fid, f in catalogo.FONTI.items():
        if not conto.get(fid):
            continue
        voci.append({
            "id": fid,
            "nome": f["etichetta"].replace(" (gratis)", ""),
            "posseduta": fid in posseduti,
            "gratis": f["gratis"],
            "episodi": conto.get(fid, 0),
            "esclusivi": scoperti.get(fid, 0),
            "prezzo": PREZZI.get(fid, ""),
        })

    # Prima cio' che hai, poi cio' che ti servirebbe di piu'.
    voci.sort(key=lambda v: (not v["posseduta"], -v["esclusivi"], -v["episodi"]))
    return voci


def copertura():
    """(coperti, totale, percentuale) con gli abbonamenti attuali."""
    tot = cop = 0
    posseduti = {f for f in catalogo.FONTI if fonti.possiede(f)}
    for pid in catalogo.ORDINE_PERCORSI:
        if pid == "dragonball_veloce":
            continue
        for t in catalogo.catena(pid):
            tot += 1
            if any(f in posseduti
                   for f in catalogo.SERIE[t["serie"]]["fonti"]):
                cop += 1
    return cop, tot, int(round(100.0 * cop / tot)) if tot else 0
