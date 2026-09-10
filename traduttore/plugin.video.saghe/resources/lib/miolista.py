# -*- coding: utf-8 -*-
"""LA MIA LISTA e I POLLICI.

Chiesto dall'utente il 10/09/2026, guardando Netflix: "hai visto quando
clicchi su una locandina netflix dice aggiungi alla mia lista oppure
riproduci o valuta con il pollice".

DOVE STANNO QUESTE AZIONI
    Nel MENU CONTESTUALE di Kodi: il tasto menu del telecomando (o C sulla
    tastiera). E' il posto previsto da Kodi per le azioni su una voce, e a
    differenza di una finestra nostra funziona in ogni elenco, anche dentro
    s4me, senza che si debba disegnare niente.

A COSA SERVE IL POLLICE, che se no e' un giochino
    A pesare i Consigliati. `consigli.py` gia' guarda cosa hai guardato;
    ora guarda anche cosa hai detto che ti piace, e soprattutto SCARTA quello
    a cui hai messo il pollice giu'. Un consiglio che continua a riproporti
    una cosa che hai rifiutato e' peggio di nessun consiglio.

DUE COSE DIVERSE, TENUTE SEPARATE
    - `lista`   quello che vuoi guardare (le voci vere e proprie)
    - `pollici` il tuo giudizio su una serie (su / giu')
    Una cosa puo' stare in lista senza giudizio, e avere un giudizio senza
    stare in lista.

I DATI SONO TUOI, NON DEL CATALOGO
    Stanno in `addon_data`, come il progresso e le serie aggiunte: un
    aggiornamento dell'add-on non se li porta via.
"""

import io
import json
import os
import time

import xbmcvfs


def _dati():
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    return c


def _file():
    return os.path.join(_dati(), "mia_lista.json")


def _leggi():
    try:
        with io.open(_file(), encoding="utf-8") as f:
            d = json.load(f) or {}
    except Exception:
        d = {}
    d.setdefault("lista", {})
    d.setdefault("pollici", {})
    return d


def _scrivi(d):
    try:
        with io.open(_file(), "w", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=1))
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# LA MIA LISTA
# --------------------------------------------------------------------------

def in_lista(chiave):
    return str(chiave) in _leggi()["lista"]


def elenco():
    """Le voci in lista, la piu' recente per prima."""
    voci = list(_leggi()["lista"].values())
    voci.sort(key=lambda v: v.get("quando", 0), reverse=True)
    return voci


def aggiungi(chiave, titolo, indirizzo, arte=None, trama="", sotto=""):
    """Mette una voce in lista. `chiave` deve essere stabile nel tempo:
    per una saga il suo percorso, per un titolo di Netflix "tmdb_<id>"."""
    d = _leggi()
    d["lista"][str(chiave)] = {
        "chiave": str(chiave), "titolo": titolo, "indirizzo": indirizzo,
        "arte": arte or {}, "trama": trama, "sotto": sotto,
        "quando": time.time(),
    }
    return _scrivi(d)


def togli(chiave):
    d = _leggi()
    if str(chiave) in d["lista"]:
        del d["lista"][str(chiave)]
        return _scrivi(d)
    return False


# --------------------------------------------------------------------------
# I POLLICI
# --------------------------------------------------------------------------

def pollice(chiave):
    """"su", "giu" o "" se non l'hai giudicata."""
    return _leggi()["pollici"].get(str(chiave), "")


def metti_pollice(chiave, verso):
    """`verso` = "su" | "giu" | "" (toglie il giudizio).

    Premere di nuovo lo stesso pollice lo TOGLIE: e' come fa Netflix, e
    senza non ci sarebbe modo di cambiare idea.
    """
    d = _leggi()
    c = str(chiave)
    if not verso or d["pollici"].get(c) == verso:
        d["pollici"].pop(c, None)
        _scrivi(d)
        return ""
    d["pollici"][c] = verso
    _scrivi(d)
    return verso


def bocciate_tmdb():
    """Gli identificativi TMDb col pollice GIU'.

    Li usa `consigli.py` per non riproporli: continuare a consigliare una
    cosa che hai rifiutato e' peggio che non consigliare niente.
    """
    fuori = set()
    for c, v in _leggi()["pollici"].items():
        if v == "giu" and c.startswith("tmdb_"):
            fuori.add(c[5:])
    return fuori


def promosse_tmdb():
    fuori = set()
    for c, v in _leggi()["pollici"].items():
        if v == "su" and c.startswith("tmdb_"):
            fuori.add(c[5:])
    return fuori
