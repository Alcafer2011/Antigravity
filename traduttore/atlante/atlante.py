# -*- coding: utf-8 -*-
"""ATLANTE DELLA VIDEOTECA: tutto Kodi, tutta la skin, tutto il nostro add-on,
tutto quello che vuole l'utente, in un posto solo.

PERCHE'
    Ogni sessione di lavoro ripartiva scansionando a mano migliaia di file
    sugli apparecchi, e i guasti venivano scoperti uno per volta davanti
    alla TV. L'atlante raccoglie UNA volta, analizza tutto, e lascia:
        uscita/REPORT.html     da leggere (grafici, livelli, rimedi)
        uscita/REQUISITI.html  tutte le parole dell'utente, per argomento e per sessione
        (niente .md: l'utente legge l'HTML, 11/09/2026)
        uscita/atlante.json  l'indice completo, da interrogare con `cerca`

USO
    python atlante.py tutto            raccoglie dai 3 apparecchi, analizza, apre il rapporto
    python atlante.py raccogli [pc box pi]
    python atlante.py analizza         analizza le copie gia' raccolte
    python atlante.py cerca <testo>    cerca nell'indice (problemi, skin, add-on, chat)
    python atlante.py apri             apre REPORT.html

NON COMMITTARE copie/ e uscita/atlante.json: sono i file degli apparecchi.
"""

import io
import json
import os
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)

import addon as m_addon      # noqa: E402
import chat as m_chat        # noqa: E402
import codice as m_codice    # noqa: E402
import incroci as m_incroci  # noqa: E402
import kodi as m_kodi        # noqa: E402
import raccolta              # noqa: E402
import rapporto              # noqa: E402
import regole as m_regole    # noqa: E402
import ricettario            # noqa: E402
import skin as m_skin        # noqa: E402

USCITA = os.path.join(QUI, "uscita")
SORGENTE = os.path.join(raccolta.ANTIGRAVITY, "traduttore", "plugin.video.saghe")
MENU = os.path.join(raccolta.ANTIGRAVITY, "traduttore", "menu-arctic")
APPARECCHI = ("pc", "box", "pi")


def _cartella_skin(copia, nome):
    for sotto in ("addons", "sistema"):
        p = os.path.join(copia, sotto, nome)
        if os.path.isdir(p):
            return p
    return ""


def analizza():
    t0 = time.time()
    R = {"cartella_addon": SORGENTE, "apparecchi": {}, "skin": {}, "skin_attiva": {}}
    print("  add-on ...")
    R["addon"] = m_addon.analizza(SORGENTE, MENU)
    print("  codice ...")
    R["codice"] = m_codice.analizza(SORGENTE)
    for app in APPARECCHI:
        copia = os.path.join(raccolta.COPIE, app)
        print("  %s ..." % app)
        k = m_kodi.analizza(copia)
        R["apparecchi"][app] = k
        if k.get("errore"):
            continue
        # la skin che conta e' Arctic Zephyr (quella per cui e' fatta la home); se non c'e', quella attiva
        cart = _cartella_skin(copia, "skin.arctic.zephyr.mod") or _cartella_skin(copia, k.get("skin_attiva") or "")
        R["skin"][app] = m_skin.analizza(cart) if cart else {"errore": "nessuna skin trovata nella copia"}
        attiva = k.get("skin_attiva") or ""
        if attiva and attiva != "skin.arctic.zephyr.mod":
            ca = _cartella_skin(copia, attiva)
            R["skin_attiva"][app] = {"nome": attiva, "analizzata": bool(ca)}
    print("  incroci ...")
    R["incroci"] = m_incroci.analizza(R["addon"], R["skin"], R["apparecchi"], SORGENTE)
    print("  chat e memorie ...")
    R["chat"] = m_chat.analizza()
    voci, regole, salute = m_regole.trova(R)
    ricette = ricettario.ricette(R)
    percorso = rapporto.scrivi(R, voci, regole, salute, ricette, USCITA)
    conta = {}
    for v in voci:
        conta[v["livello"]] = conta.get(v["livello"], 0) + 1
    print("\n  %d problemi: %s" % (len(voci), ", ".join("%s %d" % (l, conta.get(l, 0)) for l in m_regole.LIVELLI)))
    print("  %d messaggi dell'utente sulla Videoteca, %d memorie" %
          (sum(1 for m in R["chat"]["messaggi"] if m["videoteca"]), len(R["chat"]["memorie"])))
    print("  rapporto: %s  (%.0f s)" % (percorso, time.time() - t0))
    return percorso


def cerca(testo):
    p = os.path.join(USCITA, "atlante.json")
    if not os.path.exists(p):
        print("Prima: python atlante.py analizza")
        return
    with io.open(p, encoding="utf-8") as f:
        dati = json.load(f)
    ago = testo.lower()
    trovati = 0

    def giro(nodo, percorso):
        nonlocal trovati
        if trovati >= 200:
            return
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                if ago in str(k).lower() and not isinstance(v, (dict, list)):
                    print("%s.%s = %s" % (percorso, k, str(v)[:200]))
                    trovati += 1
                giro(v, "%s.%s" % (percorso, k))
        elif isinstance(nodo, list):
            for i, v in enumerate(nodo):
                giro(v, "%s[%d]" % (percorso, i))
        elif isinstance(nodo, str) and ago in nodo.lower():
            i = nodo.lower().find(ago)
            print("%s: ...%s..." % (percorso, nodo[max(0, i - 80):i + 120].replace("\n", " ")))
            trovati += 1

    giro(dati, "atlante")
    print("\n%d risultati%s" % (trovati, " (fermato a 200)" if trovati >= 200 else ""))


def apri():
    p = os.path.join(USCITA, "REPORT.html")
    if os.path.exists(p):
        os.startfile(p)  # noqa: S606 - solo Windows, apre il browser
    else:
        print("Prima: python atlante.py analizza")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd = argv[1] if len(argv) > 1 else "tutto"
    if cmd == "raccogli":
        raccolta.raccogli(tuple(argv[2:]) or APPARECCHI)
    elif cmd == "analizza":
        analizza()
    elif cmd == "cerca" and len(argv) > 2:
        cerca(" ".join(argv[2:]))
    elif cmd == "apri":
        apri()
    elif cmd == "tutto":
        print("RACCOLTA")
        raccolta.raccogli(APPARECCHI)
        print("ANALISI")
        analizza()
        apri()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
