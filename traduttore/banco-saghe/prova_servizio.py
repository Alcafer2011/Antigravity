# -*- coding: utf-8 -*-
"""Prove sull'episodio successivo automatico.

E' la funzione piu' delicata di tutte: e' l'unica che fa partire un video da
sola. Se sbaglia, l'utente si ritrova un episodio addosso mentre si alza dal
divano, oppure - peggio - perde il segno perche' la catena e' avanzata quando
non doveva.
"""
import io
import json
import os
import shutil
import sys
import time

ADDON = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finto_kodi  # noqa: E402

IMPOSTAZIONI = {
    "ha_netflix": True, "ha_prime": True, "ha_disney": False,
    "ha_timvision": False, "ha_animegeneration": False, "ha_crunchyroll": False,
    "cartella_serie": "", "hub_indirizzo": "",
    "audio_scelta_automatica": False, "audio_avvisa": False,
    "prossimo_automatico": True, "prossimo_attesa": 3,
}
PROFILO = finto_kodi.installa(ADDON, IMPOSTAZIONI)
sys.path.insert(0, ADDON)
sys.argv = ["plugin://plugin.video.saghe/", "1", ""]

import service                                   # noqa: E402
from resources.lib import catalogo, progresso    # noqa: E402

ESITI = []


def prova(nome):
    def dec(f):
        try:
            f()
            ESITI.append((True, nome, ""))
        except AssertionError as e:
            ESITI.append((False, nome, str(e) or "asserzione fallita"))
        except Exception as e:
            ESITI.append((False, nome, "%s: %s" % (type(e).__name__, e)))
        return f
    return dec


def prepara(idx, secondi, durata, percorso="naruto"):
    with io.open(os.path.join(PROFILO, "progresso.json"), "w",
                 encoding="utf-8") as f:
        f.write(json.dumps({percorso: {
            "idx": idx, "secondi": secondi, "durata": durata,
            "visti": [], "aggiornato": int(time.time())}}))
    finto_kodi.azzera()
    finto_kodi.DialogProgress.annullato = False
    return {"percorso": percorso, "idx": idx, "dentro_kodi": True,
            "avviata": int(time.time()) - 100}


def partito():
    return [v for v in finto_kodi.VOCI
            if isinstance(v, tuple) and v[0] == "riproduci"]


# --------------------------------------------------------------------------

@prova("episodio finito: parte da solo il successivo")
def _():
    sess = prepara(5, 1400, 1400)
    service._chiudi_riproduzione_interna(sess)
    p = partito()
    assert p, "non e' partito niente"
    assert "idx=6" in p[0][1], "e' partita la tappa sbagliata: %s" % p[0][1]
    assert "percorso=naruto" in p[0][1]


@prova("episodio finito a meta': NON parte niente")
def _():
    sess = prepara(5, 100, 1400)
    service._chiudi_riproduzione_interna(sess)
    assert not partito(), "e' partito un episodio dopo 100 secondi su 1400"
    assert progresso.posizione("naruto") == 5, "la catena e' avanzata a sproposito"


@prova("se dico di no durante il conto alla rovescia, non parte")
def _():
    sess = prepara(5, 1400, 1400)
    finto_kodi.DialogProgress.annullato = True
    service._chiudi_riproduzione_interna(sess)
    assert not partito(), "e' partito lo stesso dopo l'annullamento"


@prova("annullare non cancella il progresso: l'episodio resta visto")
def _():
    assert 5 in progresso.visti("naruto"), "l'episodio finito non risulta visto"
    assert progresso.posizione("naruto") == 6, "la catena non e' avanzata"


@prova("con l'automatico spento avvisa e basta")
def _():
    sess = prepara(5, 1400, 1400)
    service.ADDON.__class__.getSettingBool = lambda self, k: (
        False if k == "prossimo_automatico" else bool(IMPOSTAZIONI.get(k)))
    try:
        service._chiudi_riproduzione_interna(sess)
        assert not partito(), "e' partito con l'automatico spento"
        avvisi = [v for v in finto_kodi.VOCI
                  if isinstance(v, tuple) and v[0] == "notifica"]
        assert avvisi, "non ha nemmeno avvisato"
    finally:
        del service.ADDON.__class__.getSettingBool


@prova("l'ultima tappa della saga non fa partire il vuoto")
def _():
    ultima = catalogo.lunghezza("naruto")
    sess = prepara(ultima, 1400, 1400)
    service._chiudi_riproduzione_interna(sess)
    assert not partito(), "ha provato a riprodurre oltre la fine della saga"


@prova("l'impostazione mancante non fa cadere il servizio")
def _():
    assert service._impostazione("non_esiste_proprio", True) is True
    assert service._impostazione("non_esiste_proprio", 7) == 7


@prova("l'attesa e' quella scelta nelle impostazioni")
def _():
    partenza = time.time()
    sess = prepara(5, 1400, 1400)
    service._chiudi_riproduzione_interna(sess)
    # il finto Monitor non dorme: qui si controlla solo che non si blocchi
    assert time.time() - partenza < 5, "il conto alla rovescia blocca il servizio"


# --------------------------------------------------------------------------

larghezza = max(len(n) for _, n, _ in ESITI)
ok = 0
for esito, nome, perche in ESITI:
    print("  %s  %-*s %s" % ("OK  " if esito else "FALLITA", larghezza, nome, perche))
    ok += 1 if esito else 0
print("\n  %d prove su %d superate" % (ok, len(ESITI)))
shutil.rmtree(PROFILO, ignore_errors=True)
sys.exit(0 if ok == len(ESITI) else 1)
