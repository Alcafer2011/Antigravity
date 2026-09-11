# -*- coding: utf-8 -*-
"""IL MENU DELLA VIDEOTECA SULLA SKIN ARCTIC ZEPHYR MOD.

Arctic Zephyr costruisce il suo menu con `script.skinshortcuts`. Qui si
scrivono i tre file che skinshortcuts legge, cosi' il menu e' lo stesso su
tutti gli apparecchi invece di essere rifatto a mano col telecomando.

LE REGOLE DI SKINSHORTCUTS, lette nel suo codice (10/09/2026)
    - I file dell'utente stanno in `userdata/addon_data/script.skinshortcuts/`
      e NON hanno il prefisso della skin nel nome: i menu sono condivisi di
      default. Un `skin.arctic.zephyr.mod-mainmenu.DATA.xml` viene ignorato.
    - Le righe sono PROPRIETA' della voce del menu principale, nel file
      `skin.arctic.zephyr.mod.properties` (JSON, voci di 4 campi).
      `widgetName` e' il titolo della riga.
    - MASSIMO 6 RIGHE PER VOCE: `widgetPath`, poi `.2` ... `.6`.
    - Le righe 2-6 senza `widgetEnable.N = yes` restano nascoste.
    - Se l'azione di una voce contiene `plugin://` SENZA `?`, skinshortcuts le
      cambia identificativo con il nome dell'add-on e le righe scritte per
      quella voce non si attaccano. La Home ha avuto questo guasto.

USO
    python fai-menu-arctic.py [cartella]      (predefinita: ./menu-arctic)
    Poi, a Kodi SPENTO, i tre file in addon_data/script.skinshortcuts/, e si
    tolgono `1080i/script-skinshortcuts-includes.xml` e
    `skin.arctic.zephyr.mod.hash` perche' la skin ricostruisca.
"""

import importlib.util
import io
import json
import os
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

QUI = os.path.dirname(os.path.abspath(__file__))
SCOPERTE = os.path.join(QUI, "plugin.video.saghe", "resources", "lib",
                        "scoperte.py")
P = "plugin://plugin.video.saghe/?azione="
W = P + "widget&che="
MAX_RIGHE = 6


def apri(azione_query):
    """L'azione al clic. SEMPRE con un "?" nell'indirizzo (vedi sopra)."""
    return 'ActivateWindow(Videos,"%s%s",return)' % (P, azione_query)


# (etichetta, labelID, azione al clic, [(titolo riga, che), ...])
# labelID = etichetta minuscola senza spazi, come la calcola skinshortcuts.
# Niente apostrofi ne' accenti nelle etichette: cosi' la trasformazione non
# riserva sorprese.
VOCI = [
    ("Home", "home", apri(""), [
        ("Continua a guardare", "continua"),
        ("La mia lista", "lista"),
        ("Consigliati per te", "consigli"),
        ("Su Netflix ora - Serie TV", "netflix:serietv"),
        ("Su Netflix ora - Film", "netflix:film"),
        ("Su Netflix ora - Anime", "netflix:anime"),
    ]),
    # CERCA (11/09/2026): dal menu della skin, senza entrare nella Videoteca.
    # Scrivi, e la ricerca va da sola sul catalogo e su tutti i siti.
    ("Cerca", "cerca", "RunScript(plugin.video.saghe,cerca_nuova)", []),
    ("Le tue saghe", "letuesaghe", apri("reparto&reparto=cartoni"), [
        ("Le tue saghe", "saghe"),
        ("I film delle saghe", "film"),
        ("Novita dai tuoi siti", "novita"),
    ]),
    ("Serie TV", "serietv", apri("reparto&reparto=serietv"), [
        ("Le tue serie TV", "serietv"),
        ("Su Netflix ora - Serie TV", "netflix:serietv"),
        ("Al cinema ora", "cinema"),
    ]),
    ("Documentari", "documentari", apri("scaffale&scaffale=documentari"), [
        ("Natura e animali", "documentari:1"),
        ("Spazio e scienza", "documentari:2"),
        ("Preistoria e archeologia", "documentari:3"),
        ("Storia", "documentari:4"),
        ("I programmi di Discovery e Sky", "documentari:5"),
        ("Motori, garage e restauri", "documentari:6"),
    ]),
    # Il limite di 6 righe per voce lasciava fuori 5 gruppi dei documentari:
    # nessuna voce li raggiungeva, per l'utente non esistevano. (Trovato
    # dalla sessione di prova il 10/09/2026.)
    ("Altri documentari", "altridocumentari", apri("scaffale&scaffale=documentari"), [
        ("Motori e ingegneria", "documentari:7"),
        ("Disastri e misteri", "documentari:8"),
        ("Cronaca e crimine", "documentari:9"),
        ("Societa, arte e viaggi", "documentari:10"),
        ("Documentari a catalogo", "documentari:0"),
    ]),
    ("Cucina", "cucina", apri("scaffale&scaffale=cucina"), [
        ("I programmi", "cucina:1"),
        ("Gli chef", "cucina:2"),
        ("Imparare a cucinare", "cucina:3"),
        ("Cucine del mondo", "cucina:4"),
        ("Particolari", "cucina:5"),
        ("Cucina a catalogo", "cucina:0"),
    ]),
    ("YouTube", "youtube", apri("scaffale&scaffale=youtube"), [
        ("I canali che segui", "youtube:0"),
    ]),
    # Le due "In diretta" di documentari e cucina stanno qui, insieme ai
    # canali: e' il posto dove uno le va a cercare.
    ("TV in diretta", "tvindiretta", apri("tv"), [
        ("TV in diretta", "tv"),
        ("Documentari in diretta", "documentari:11"),
        ("Cucina in diretta", "cucina:6"),
    ]),
    ("Impostazioni", "settings", "ActivateWindow(Settings)", []),
    ("Uscita", "power", "ActivateWindow(shutdownmenu)", []),
]

# In cima al menu Uscita, prima delle voci della skin.
USCITA_IN_CIMA = [
    ("s4me (il motore sotto)", 'ActivateWindow(Videos,"plugin://plugin.video.s4me/",return)'),
    ("Impostazioni Videoteca", "RunPlugin(plugin://plugin.video.saghe/?azione=impostazioni)"),
    ("Cerca aggiornamenti", "RunScript(plugin.video.saghe,aggiornamenti)"),
    ("Qualcosa non va? Segnalalo", "RunScript(plugin.video.saghe,segnala,00)"),
]


def _scoperte():
    spec = importlib.util.spec_from_file_location("scoperte", SCOPERTE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def controlla():
    """Un menu che non passa non si scrive."""
    guai = []
    visti = set()
    for et, lid, azione, righe in VOCI:
        if lid in visti:
            guai.append("labelID doppio: %s" % lid)
        visti.add(lid)
        if len(righe) > MAX_RIGHE:
            guai.append("%s ha %d righe: skinshortcuts ne mostra al massimo %d"
                        % (et, len(righe), MAX_RIGHE))
        if "plugin://" in azione and "?" not in azione:
            guai.append("%s: azione plugin:// senza '?' - skinshortcuts le "
                        "cambierebbe identificativo" % et)
    # OGNI gruppo di documentari, cucina e YouTube deve essere raggiungibile
    # da almeno una voce. E' il guasto delle 7 righe orfane del 10/09.
    presenti = {che for _, _, _, righe in VOCI for _, che in righe}
    sc = _scoperte()
    for sezione in ("documentari", "cucina", "youtube"):
        for i, (intestazione, voci) in enumerate(sc.scaffale(sezione)):
            if voci and "%s:%d" % (sezione, i) not in presenti:
                guai.append("gruppo irraggiungibile: %s:%d (%s)"
                            % (sezione, i, intestazione))
    return guai


def scrivi(cartella):
    os.makedirs(cartella, exist_ok=True)

    righe = ["<?xml version='1.0' encoding='UTF-8'?>", "<shortcuts>"]
    for et, lid, azione, _ in VOCI:
        righe += ["    <shortcut>",
                  "        <label>%s</label>" % escape(et),
                  "        <label2>Videoteca</label2>",
                  "        <defaultID>%s</defaultID>" % lid,
                  "        <icon>DefaultFolder.png</icon>",
                  "        <action>%s</action>" % escape(azione),
                  "    </shortcut>"]
    righe.append("</shortcuts>")
    io.open(os.path.join(cartella, "mainmenu.DATA.xml"), "w",
            encoding="utf-8", newline="\n").write("\n".join(righe) + "\n")

    props = []
    for _, lid, _, rr in VOCI:
        for n, (titolo, che) in enumerate(rr, 1):
            s = "" if n == 1 else ".%d" % n
            props += [["mainmenu", lid, "widget" + s, "Addon"],
                      ["mainmenu", lid, "widgetName" + s, titolo],
                      ["mainmenu", lid, "widgetType" + s, "videos"],
                      ["mainmenu", lid, "widgetTarget" + s, "videos"],
                      ["mainmenu", lid, "widgetPath" + s, W + che]]
            if n > 1:
                props.append(["mainmenu", lid, "widgetEnable" + s, "yes"])
    io.open(os.path.join(cartella, "skin.arctic.zephyr.mod.properties"), "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(props, indent=4, ensure_ascii=False))

    skin_pm = os.path.expandvars(
        r"%APPDATA%\Kodi\addons\skin.arctic.zephyr.mod\shortcuts\powermenu.DATA.xml")
    corpo = io.open(skin_pm, encoding="utf-8").read()
    aggiunta = "".join(
        "    <shortcut>\n        <label2>Power Menu Shortcut</label2>\n"
        "        <label>%s</label>\n        <action>%s</action>\n"
        "        <icon />\n        <thumb />\n    </shortcut>\n"
        % (escape(a), escape(b)) for a, b in USCITA_IN_CIMA)
    corpo = corpo.replace("<shortcuts>\n", "<shortcuts>\n" + aggiunta, 1)
    io.open(os.path.join(cartella, "powermenu.DATA.xml"), "w",
            encoding="utf-8", newline="\n").write(corpo)

    for f in ("mainmenu.DATA.xml", "powermenu.DATA.xml"):
        ET.parse(os.path.join(cartella, f))
    json.load(io.open(os.path.join(cartella, "skin.arctic.zephyr.mod.properties"),
                      encoding="utf-8"))
    return len(props)


def main():
    cartella = sys.argv[1] if len(sys.argv) > 1 else os.path.join(QUI, "menu-arctic")
    guai = controlla()
    for et, lid, _, rr in VOCI:
        print("   %-18s (%-16s) righe: %d" % (et, lid, len(rr)))
    if guai:
        print("\nCONTROLLI FALLITI - non scrivo niente:")
        for g in guai:
            print("   - " + g)
        return 1
    n = scrivi(cartella)
    print("\ncontrolli passati; %d proprieta' scritte in %s" % (n, cartella))
    return 0


if __name__ == "__main__":
    sys.exit(main())
