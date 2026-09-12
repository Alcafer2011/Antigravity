# -*- coding: utf-8 -*-
"""IL VESTITO NOVIX SULLA SKIN: splash, apertura animata col suo suono, logo in ogni schermata.

PERCHE' (l'utente, 11/09/2026)
    "vorrei un logo in stile Netflix animato in apertura, e persistente in
    tutte le sezioni dell'add-on proprio come Netflix". Poi: "non far apparire
    il logo della skin Arctic, lascia solo il nostro, cosi' il suo tempo e'
    piu' lungo". E: "metti anche un suono di sottofondo al logo, come fa Netflix".

COSA SI CUCE, e dove (Arctic Zephyr, uguale nella 2.0.5 del Raspberry e nella
3.0.3 del box)
    1. 1080i/Startup.xml - la finestra che Kodi apre per prima. Di fabbrica
       passa SUBITO alla finestra 1150 (Custom_Startup.xml): quattro secondi
       con la scritta "Arctic Zephyr", poi la home. Quella finestra non prepara
       niente (a parte il "video d'avvio" della skin, che qui non si usa), quindi
       la si SALTA: 5 secondi di animazione NOVIX (120 fotogrammi da 40 ms,
       fai-logo.py) col suo suono (PlaySFX: il comando dei suoni dell'interfaccia,
       non apre il lettore musicale), poi dritti alla home.
    2. 1080i/Includes_Defs.xml - gli include Kodi_Logo e Kodi_Logo_Home: il
       logo di Kodi in alto a sinistra di 47 schermate. Al suo posto la N a
       nastro, coi suoi colori, e la sfumatura di Kodi spenta.
    3. special://home/media/splash.jpg (e .png) - l'immagine che Kodi mostra
       all'accensione, prima ancora della skin: la N accesa.

IL SUONO SI SENTE SOLO SE "Suoni dell'interfaccia" non e' su "mai"
    (audiooutput.guisoundmode diverso da 0). Sul box, l'11/09/2026, era 0.

LE REGOLE
    - Un SEGNO nel file dice che e' gia' cucito: non si cuce mai due volte.
      Le aperture vecchie (1: 3 secondi e poi la finestra della skin; 2: senza
      suono) si aggiornano da sole alla 3.
    - Si cuce SOLO se si trova esattamente il pezzo atteso. Se un aggiornamento
      della skin lo ha cambiato, non si tocca niente e lo si dice.
    - Un aggiornamento della skin riscrive i suoi file e il vestito sparisce:
      il guardiano lo ricuce al primo giro (si vede dal riavvio dopo).
    - Queste funzioni non importano Kodi: le usa anche servi.py dal PC.
"""

import filecmp
import io
import os
import re
import shutil

SEGNO = "videoteca-vestito-1"               # il logo nelle schermate (Includes_Defs.xml)
SEGNO_APERTURA = "videoteca-apertura-4"     # l'apertura (Startup.xml); il suono lo fa il servizio
APERTURE_VECCHIE = ("videoteca-apertura-2", "videoteca-apertura-3")
LOGO = "special://home/addons/plugin.video.saghe/resources/media/logo/"
DURATA = "00:05"
ATTESA_HOME = '<onload condition="!Skin.HasSetting(disable.startup.window)">ReplaceWindow(1150)</onload>'
ATTESA_ALTRA = '<onload condition="Skin.HasSetting(disable.startup.window)">ReplaceWindow($INFO[System.StartupWindow])</onload>'
VAI_ALLA_HOME = "AlarmClock(videoteca_apertura,ReplaceWindow($INFO[System.StartupWindow]),%s,true)" % DURATA
PRIMA_ONLOAD_NOSTRA = '<onload condition="!Skin.HasSetting(disable.startup.window)">%s</onload>' % VAI_ALLA_HOME
SUONO = '<onload condition="!Player.HasMedia">PlaySFX(%ssuono.wav)</onload>' % LOGO
CONTROLLI = (
    '\n        <!-- %s: l\'apertura animata NOVIX col suo suono (fai-logo.py), poi dritti alla home -->\n'
    '        <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height>'
    '<texture>%snero.png</texture></control>\n'
    '        <control type="multiimage"><left>0</left><top>0</top><width>1920</width><height>1080</height>'
    '<imagepath>%sintro/</imagepath><timeperimage>40</timeperimage><fadetime>0</fadetime>'
    '<loop>no</loop><randomize>false</randomize><aspectratio>keep</aspectratio></control>\n    ' % (SEGNO_APERTURA, LOGO, LOGO))


def _senza_suono(testo):
    """Toglie la riga del suono dalla schermata di avvio.

    Era `<onload ...>PlaySFX(...suono.wav)</onload>`, e Kodi la rifiutava
    ("no such action"): PlaySFX e' un'azione del telecomando, non un comando
    eseguibile da una schermata. Adesso il suono lo fa il servizio del
    guardiano con xbmc.playSFX(). Si toglie anche la riga a capo che la
    seguiva, per non lasciare buchi nel file."""
    import re as _re
    if "PlaySFX" not in (testo or ""):
        return testo
    return _re.sub(r"[ \t]*<onload[^>]*>\s*PlaySFX\([^)]*\)\s*</onload>\s*\n?", "", testo)


def _con_suono(testo):
    """Mette il suono subito prima dell'attesa della home. None se non trova il posto."""
    if SUONO in testo:
        return testo
    if PRIMA_ONLOAD_NOSTRA not in testo:
        return None
    return testo.replace(PRIMA_ONLOAD_NOSTRA, SUONO + "\n    " + PRIMA_ONLOAD_NOSTRA, 1)


def cuci_startup(testo):
    """(testo nuovo, esito) - esito: 'cucito', 'gia cucito' o 'non riconosciuto'."""
    if SEGNO_APERTURA in testo:
        # ANCHE SE E' GIA' CUCITO, la riga del suono va tolta (12/09/2026).
        # Chi ha ricevuto la versione di prima ha il segno nuovo MA la riga
        # vecchia dentro: uscendo subito con "gia cucito" non la togliamo mai,
        # ed e' quello che e' successo sul Raspberry - installazione riuscita,
        # riga ancora li'. Qui si ripulisce e si dichiara il lavoro fatto.
        pulito = _senza_suono(testo)
        if pulito != testo:
            return pulito, "cucito"
        return testo, "gia cucito"
    vecchia = next((s for s in APERTURE_VECCHIE if s in testo), None)
    if vecchia:
        nuovo = _con_suono(testo.replace(vecchia, SEGNO_APERTURA))
        return (nuovo, "cucito") if nuovo else (testo, "non riconosciuto")
    if SEGNO in testo:
        # la prima apertura: 3 secondi e poi la finestra col logo di Arctic Zephyr
        nuovo = testo.replace("AlarmClock(videoteca_apertura,ReplaceWindow(1150),00:03,true)", VAI_ALLA_HOME)
        nuovo = nuovo.replace("AlarmClock(videoteca_apertura,ReplaceWindow($INFO[System.StartupWindow]),00:03,true)", VAI_ALLA_HOME)
        nuovo = nuovo.replace("<!-- %s: l'apertura animata della Videoteca (fai-logo.py) -->" % SEGNO,
                              "<!-- %s: l'apertura animata NOVIX col suo suono (fai-logo.py), poi dritti alla home -->" % SEGNO_APERTURA)
        nuovo = _con_suono(nuovo) if SEGNO_APERTURA in nuovo and "ReplaceWindow(1150)" not in nuovo else None
        return (nuovo, "cucito") if nuovo else (testo, "non riconosciuto")
    if ATTESA_HOME not in testo or ("<controls/>" not in testo and "<controls>" not in testo):
        return testo, "non riconosciuto"
    nuovo = testo.replace(ATTESA_HOME, PRIMA_ONLOAD_NOSTRA, 1)
    nuovo = nuovo.replace(ATTESA_ALTRA, '<onload condition="Skin.HasSetting(disable.startup.window)">%s</onload>' % VAI_ALLA_HOME, 1)
    if "<controls/>" in nuovo:
        nuovo = nuovo.replace("<controls/>", "<controls>%s</controls>" % CONTROLLI, 1)
    else:
        nuovo = nuovo.replace("<controls>", "<controls>%s" % CONTROLLI, 1)
    # LA RIGA PlaySFX VA TOLTA, NON SOLO "NON AGGIUNTA" (12/09/2026).
    #   <onload ...>PlaySFX(special://home/.../suono.wav)</onload>
    # non ha mai suonato, e il registro del Raspberry diceva perche':
    #   "Keymapping error: no such action 'playsfx(...)' defined".
    # PlaySFX in Kodi e' un'AZIONE del telecomando, non un comando che una
    # schermata puo' eseguire: dentro <onload> viene rifiutata. Il suono lo fa
    # ora il servizio del guardiano con xbmc.playSFX(), che e' l'API giusta.
    # ATTENZIONE: ricucendo sopra una versione vecchia il testo di partenza LA
    # CONTIENE GIA', quindi smettere di aggiungerla non basta - sul Raspberry
    # infatti era rimasta, col segno nuovo. Qui si toglie davvero.
    nuovo = _senza_suono(nuovo) if nuovo else nuovo
    return (nuovo, "cucito") if nuovo else (testo, "non riconosciuto")


def cuci_logo(testo):
    """(testo nuovo, esito) per Includes_Defs.xml."""
    if SEGNO in testo:
        return testo, "gia cucito"
    icona = re.compile(r"<colordiffuse>\$VAR\[ColorKodiLogo\]</colordiffuse>(\s*)<texture>buttons/kodi-logo\.png</texture>")
    sfumatura = re.compile(r"(<texture>buttons/kodi-logo-gradient\.png</texture>)")
    blocchi = list(re.finditer(r'<include name="Kodi_Logo(?:_Home)?">.*?</include>', testo, re.S))
    if len(blocchi) != 2:
        return testo, "non riconosciuto"
    nuovo, inizio = [], 0
    for b in blocchi:
        pezzo = b.group(0)
        pezzo, n1 = icona.subn(r"<colordiffuse>FFFFFFFF</colordiffuse>\1<texture>%smonogramma-128.png</texture>" % LOGO, pezzo)
        pezzo, n2 = sfumatura.subn(r"\1<visible>false</visible>", pezzo)
        if n1 != 1 or n2 != 1:
            return testo, "non riconosciuto"
        nuovo.append(testo[inizio:b.start()])
        nuovo.append(pezzo)
        inizio = b.end()
    nuovo.append(testo[inizio:])
    risultato = "".join(nuovo)
    risultato = risultato.replace('<include name="Kodi_Logo">',
                                  '<!-- %s: la N di NOVIX al posto del logo di Kodi -->\n    <include name="Kodi_Logo">' % SEGNO, 1)
    return risultato, "cucito"


FILE = (("Startup.xml", cuci_startup, SEGNO_APERTURA), ("Includes_Defs.xml", cuci_logo, SEGNO))


def stato(cartella_skin):
    """{file: 'cucito' | 'da cucire' | 'manca'} senza toccare niente."""
    fuori = {}
    for nome, _funzione, segno in FILE:
        p = os.path.join(cartella_skin, "1080i", nome)
        if not os.path.exists(p):
            fuori[nome] = "manca"
            continue
        with io.open(p, encoding="utf-8", errors="replace") as f:
            fuori[nome] = "cucito" if segno in f.read() else "da cucire"
    return fuori


def applica(cartella_skin):
    """Cuce i due file della skin. {file: esito}."""
    fuori = {}
    for nome, funzione, _segno in FILE:
        p = os.path.join(cartella_skin, "1080i", nome)
        if not os.path.exists(p):
            fuori[nome] = "manca"
            continue
        with io.open(p, encoding="utf-8") as f:
            testo = f.read()
        nuovo, esito = funzione(testo)
        if esito == "cucito":
            provvisorio = p + ".tmp"
            with io.open(provvisorio, "w", encoding="utf-8", newline="") as f:
                f.write(nuovo)
            os.replace(provvisorio, p)
        fuori[nome] = esito
    return fuori


def assicura_splash(cartella_home, cartella_logo):
    """Mette lo splash NOVIX in <home>/media/ se manca o e' diverso. Una frase per il guardiano."""
    fatti = []
    media = os.path.join(cartella_home, "media")
    for nome in ("splash.jpg", "splash.png"):
        sorgente, destinazione = os.path.join(cartella_logo, nome), os.path.join(media, nome)
        if not os.path.exists(sorgente):
            return "lo splash non c'e' nell'add-on (fai-logo.py)"
        if os.path.exists(destinazione) and filecmp.cmp(sorgente, destinazione, shallow=False):
            continue
        os.makedirs(media, exist_ok=True)
        shutil.copyfile(sorgente, destinazione)
        fatti.append(nome)
    return ("splash NOVIX messo (%s)" % ", ".join(fatti)) if fatti else "splash NOVIX al suo posto"
