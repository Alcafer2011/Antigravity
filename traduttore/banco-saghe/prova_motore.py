# -*- coding: utf-8 -*-
"""Prove sul motore delle fonti: il piano, il pre-volo, la memoria.

E' la parte da cui dipende tutto il resto: se il piano sbaglia ordine o non
ricade sulla strada successiva, l'utente vede un errore e non gli importa
niente di quanto e' bello il menu.
"""
import io
import json
import os
import shutil
import sys

ADDON = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finto_kodi  # noqa: E402

IMPOSTAZIONI = {
    "ha_netflix": True, "ha_prime": True, "ha_disney": False,
    "ha_timvision": False, "ha_animegeneration": False, "ha_crunchyroll": False,
    "cartella_serie": "", "hub_indirizzo": "",
    "scadenza_prime": "04/10/2026", "scadenza_netflix": "",
    "audio_scelta_automatica": False, "audio_avvisa": False,
    "prossimo_automatico": False, "prossimo_attesa": 3,
}
PROFILO = finto_kodi.installa(ADDON, IMPOSTAZIONI)
sys.path.insert(0, ADDON)
sys.argv = ["plugin://plugin.video.saghe/", "1", ""]

import main                                              # noqa: E402
from resources.lib import catalogo, motore, ponte_s4me   # noqa: E402

ESITI = []


def prova(nome):
    def dec(f):
        try:
            motore.dimentica()
            f()
            ESITI.append((True, nome, ""))
        except AssertionError as e:
            ESITI.append((False, nome, str(e) or "asserzione fallita"))
        except Exception as e:
            ESITI.append((False, nome, "%s: %s" % (type(e).__name__, e)))
        return f
    return dec


# --------------------------------------------------------------------------

@prova("il piano non e' mai vuoto: c'e' sempre un'ultima spiaggia")
def _():
    """Un episodio senza fonti deve comunque avere una strada da provare.
    Se il piano e' vuoto l'utente vede un muro, ed e' proprio cio' che
    l'add-on esiste per evitare."""
    ponte_s4me.installato = lambda: True
    p = motore.piano("naruto", 5)
    assert p, "piano vuoto"
    assert p[-1]["id"] == "s4me", "l'ultima strada non e' il ponte: %s" % p[-1]["id"]


@prova("il ponte s4me e' l'ultimo fra le strade in salute")
def _():
    """L'unica cosa che passa sotto al ponte e' una fonte bocciata tre
    volte di fila, ed e' voluto: vedi la prova sulla bocciatura."""
    ponte_s4me.installato = lambda: True
    for serie, ep in (("naruto", 5), ("db", 1), ("sdbh", 3), ("tr_terra_amara", 10)):
        p = motore.piano(serie, ep)
        posti = [i for i, s in enumerate(p) if s["id"] == "s4me"]
        assert posti == [len(p) - 1], \
            "%s: il ponte sta in posizione %s su %d strade" % (serie, posti, len(p))


@prova("fuori da Android le app non entrano nemmeno nel piano")
def _():
    p = motore.piano("naruto", 5, su_android=False)
    app = [s["id"] for s in p if s["tipo"] == "app"]
    assert not app, "app nel piano su un apparecchio senza app: %s" % app


@prova("su Android le app ci sono")
def _():
    p = motore.piano("naruto", 5, su_android=True)
    assert [s for s in p if s["tipo"] == "app"], \
        "nessuna app nel piano su Android, ma Naruto sta su Prime"


@prova("tre riuscite di fila e una fonte scavalca l'ordine del catalogo")
def _():
    """Serve un caso con PIU' di una fonte vera, altrimenti non c'e' niente
    da riordinare. One Piece ha Netflix e Prime, tutti e due posseduti."""
    ponte_s4me.installato = lambda: True
    prima = [s["id"] for s in motore.piano("one_piece", 5, su_android=True)]
    assert len(prima) >= 3, "servono due fonti piu' il ponte, ho: %s" % prima
    seconda = prima[1]
    for _i in range(3):
        motore.ricorda("one_piece", seconda, True, 1.0)
    dopo = [s["id"] for s in motore.piano("one_piece", 5, su_android=True)]
    assert dopo.index(seconda) < prima.index(seconda), \
        "dopo tre riuscite %s non e' salita: %s -> %s" % (seconda, prima, dopo)


@prova("una fonte bocciata tre volte finisce SOTTO l'ultima spiaggia")
def _():
    """Difetto di progetto trovato dal banco il 06/09/2026.

    Se Prime ha fallito tre volte di fila, riprovarlo per primo e'
    testardaggine: meglio andare dritti su s4me e tenere Prime come
    riserva. Con la penalita' piccola di prima, una fonte rotta restava in
    testa per sempre, perche' il ponte pesa comunque piu' di tutti.
    """
    ponte_s4me.installato = lambda: True
    prima = [s["id"] for s in motore.piano("one_piece", 5, su_android=True)]
    testa = prima[0]
    for _i in range(3):
        motore.ricorda("one_piece", testa, False)
    dopo = [s["id"] for s in motore.piano("one_piece", 5, su_android=True)]
    assert testa in dopo, "la fonte bocciata e' sparita dal piano: non deve mai"
    assert dopo.index(testa) > dopo.index("s4me"), \
        "%s ha fallito tre volte e sta ancora prima del ponte: %s" % (testa, dopo)


@prova("il pre-volo riconosce un file locale che non c'e' piu'")
def _():
    ok, perche = motore.previsione(
        {"tipo": "locale", "percorso": r"C:\questo\non\esiste\mai.mkv"})
    assert ok is False, "ha detto che un file inesistente va bene"
    assert "non c'e" in perche, perche


@prova("il pre-volo accetta un file locale che c'e'")
def _():
    ok, _p = motore.previsione({"tipo": "locale", "percorso": __file__})
    assert ok is True


@prova("cio' che non si puo' sondare NON viene scartato per prudenza")
def _():
    """Un'app o un altro add-on non si possono sondare da qui. Scartarli
    sarebbe peggio del male: si perderebbe una strada buona."""
    for tipo in ("app", "plugin", "ponte"):
        ok, perche = motore.previsione({"tipo": tipo, "percorso": ""})
        assert ok is True, "%s scartata senza motivo: %s" % (tipo, perche)


@prova("la memoria sopravvive e si puo' cancellare")
def _():
    motore.ricorda("db", "prime", True, 2.5)
    assert motore.scheda("db", "prime")["ok"] == 1
    motore.dimentica("db")
    assert motore.scheda("db", "prime") == {}, "dimentica() non ha cancellato"


@prova("una memoria rovinata non impedisce di guardare")
def _():
    """Il file della memoria e' un aiuto, non un requisito."""
    with io.open(os.path.join(PROFILO, "motore.json"), "w", encoding="utf-8") as f:
        f.write("{questo non e' json")
    p = motore.piano("naruto", 5)
    assert p, "con la memoria rovinata il piano e' vuoto"


@prova("il registro racconta cosa e' stato provato")
def _():
    motore.annota("naruto", 5, "prime", "saltata", "il collegamento non risponde")
    motore.annota("naruto", 5, "s4me", "riuscita", "")
    r = motore.registro()
    assert len(r) >= 2, "il registro non ha annotato"
    assert r[-1]["esito"] == "riuscita"
    assert r[-2]["dettaglio"], "manca il perche' della strada saltata"


@prova("il registro non cresce all'infinito")
def _():
    for i in range(60):
        motore.annota("naruto", i, "prime", "fallita", "")
    assert len(motore.registro()) <= motore.MAX_REGISTRO, \
        "il registro e' cresciuto oltre il limite"


@prova("il piano si sa spiegare a parole")
def _():
    ponte_s4me.installato = lambda: True
    testo = motore.spiega_piano("naruto", 5)
    assert testo and "1." in testo, "spiegazione vuota: %r" % testo[:60]
    assert "s4me" in testo.lower()


@prova("apri() passa alla strada dopo quando la prima non risponde")
def _():
    """La prova che conta piu' di tutte: la ricaduta automatica."""
    ponte_s4me.installato = lambda: True
    chiamate = []
    ponte_s4me.titolo_per_ricerca = lambda serie, t: "Naruto"
    ponte_s4me.apri_automatico = lambda titolo, ep: (chiamate.append("auto"), "aperto")[1]
    ponte_s4me.cerca = lambda titolo: chiamate.append("cerca")

    # una strada che il pre-volo boccia di sicuro, messa davanti a tutto
    vero_piano = motore.piano

    def piano_finto(serie_id, ep, su_android=None):
        rotta = {"id": "rotta", "etichetta": "Fonte rotta", "tipo": "locale",
                 "percorso": r"C:\non\esiste\mai.mkv", "dentro_kodi": True,
                 "posseduta": True, "base": 0, "perche": "prova"}
        return [rotta] + vero_piano(serie_id, ep, su_android=False)

    motore.piano = piano_finto
    try:
        finto_kodi.azzera()
        # Si prova avvio._apri e NON main.apri: da main l'apertura ora viene
        # solo DELEGATA, perche' farla dentro una cartella faceva crollare
        # Kodi ("two concurrent busydialogs"). Il lavoro vero sta in avvio.
        import avvio
        avvio._apri("naruto", 5)
    finally:
        motore.piano = vero_piano

    assert chiamate, "non ha mai raggiunto il ponte: la ricaduta non funziona"
    reg = motore.registro()
    saltate = [x for x in reg if x["esito"] == "saltata"]
    assert saltate, "la strada rotta non risulta saltata nel registro"


@prova("main.apri NON apre niente da se': delega, altrimenti Kodi crolla")
def _():
    """Il guasto del 06/09/2026: aprire da dentro una richiesta di cartella
    fa vedere a Kodi due finestre di attesa sovrapposte, e Kodi si spegne
    di proposito. main.apri deve solo chiudere la cartella e delegare."""
    import inspect
    sorgente = inspect.getsource(main.apri)
    assert "RunScript" in sorgente, "main.apri non delega piu': puo' far crollare Kodi"
    for vietato in ("ponte_s4me.", "Dialog()", "apri_automatico"):
        assert vietato not in sorgente,             "main.apri fa ancora %s dentro la cartella: e' il guasto di prima" % vietato


@prova("una strada saltata non viene contata come riuscita")
def _():
    motore.ricorda("naruto", "rotta", False)
    s = motore.scheda("naruto", "rotta")
    assert s["ok"] == 0 and s["ko"] == 1, s


# --------------------------------------------------------------------------

larghezza = max(len(n) for _, n, _ in ESITI)
ok = 0
for esito, nome, perche in ESITI:
    print("  %s  %-*s %s" % ("OK  " if esito else "FALLITA", larghezza, nome, perche))
    ok += 1 if esito else 0
print("\n  %d prove su %d superate" % (ok, len(ESITI)))
shutil.rmtree(PROFILO, ignore_errors=True)
sys.exit(0 if ok == len(ESITI) else 1)
