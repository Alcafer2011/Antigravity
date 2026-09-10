# -*- coding: utf-8 -*-
"""COSTRUISCE Home.xml DELLA VIDEOTECA DA UNA TABELLA DI RIGHE.

PERCHE' UN GENERATORE E NON UN FILE SCRITTO A MANO
    La home ha, per ogni riga, QUATTRO cose in quattro punti diversi del
    file: l'immagine di sfondo, la terna di etichette della testata, la
    lista vera e propria, e gli anelli `onup`/`ondown` che la collegano a
    quelle sopra e sotto. Scritte a mano, in sei mesi si e' rotto ogni
    pezzo almeno una volta, e sempre in silenzio:

      07/09  due righe saltate dalla navigazione: nessun tasto le
             raggiungeva, per l'utente non esistevano.
      07/09  due righe annidate una dentro l'altra: XML valido, due elenchi
             disegnati nello stesso riquadro.
      10/09  la riga AL CINEMA ORA senza testata: titolo e trama bianchi.
      10/09  nessuna riga aveva `target` sul <content>: premendo OK non si
             apriva NIENTE, e non lo diceva nessun registro.

    Sono tutti errori di ripetizione, non di ragionamento. Da qui in avanti
    la ripetizione la fa la macchina: si tocca solo la tabella RIGHE qui
    sotto, e le quattro parti escono per forza coerenti.

USO
    python fai-home.py            scrive skin-videoteca/Home.xml e controlla
    python fai-home.py --controlla   controlla e basta, non scrive
"""

import io
import os
import re
import sys
import importlib.util

QUI = os.path.dirname(os.path.abspath(__file__))
SKIN = os.path.join(QUI, "skin-videoteca", "Home.xml")
SCOPERTE = os.path.join(QUI, "plugin.video.saghe", "resources", "lib",
                        "scoperte.py")

PRIMA_RIGA = 5010          # la barra in alto rimanda a questo numero

# LA GEOMETRIA, in un posto solo.
# L'utente (10/09/2026): "aumenterei la parte grossa che si vede a tutto
# schermo togliendo a monitor una riga, cioe' DUE invece di tre".
ALTEZZA_RIGA = 214              # titolo (40) + tessera 16:9 (174)
RIGHE_A_VIDEO = 2
FONDO_RIGHE = 1028              # sopra la scritta dei tasti, che sta a 1034
# L'altezza deve essere un MULTIPLO ESATTO dell'altezza di una riga: con una
# misura qualunque il grouplist si ferma a meta' riga e il titolo di quella
# in cima si vede tagliato per lungo, che sembra un errore di disegno.
ALTEZZA_RIGHE = ALTEZZA_RIGA * RIGHE_A_VIDEO
CIMA_RIGHE = FONDO_RIGHE - ALTEZZA_RIGHE
SFUMATURA = 240                 # quanto e' lunga la transizione verso il buio


def _scoperte():
    spec = importlib.util.spec_from_file_location("scoperte", SCOPERTE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tabella():
    """(titolo di riga, valore di `che`) nell'ordine in cui si vedono."""
    sc = _scoperte()
    righe = [
        ("CONTINUA A GUARDARE",     "continua"),
        ("LA MIA LISTA",            "lista"),
        ("CONSIGLIATI PER TE",      "consigli"),
        # SU NETFLIX ORA in TRE righe, non una. L'utente, vedendo la riga
        # unica: "ho visto forse dei film o serie tv e cartoni animati o
        # anime ... e sono due categorie diverse". Sul sito di Netflix
        # "Serie" e "Film" sono voci di primo livello e "Anime" e' un genere
        # a se': qui sono tre righe, e i 22 generi stanno dietro il menu.
        ("SU NETFLIX ORA - SERIE TV", "netflix:serietv"),
        ("SU NETFLIX ORA - FILM",     "netflix:film"),
        ("SU NETFLIX ORA - ANIME",    "netflix:anime"),
        ("LE TUE SAGHE",            "saghe"),
        ("NOVITA' DAI TUOI SITI",   "novita"),
        ("TV IN DIRETTA",           "tv"),
    ]
    # UNA RIGA PER GRUPPO. Il titolo del gruppo diventa il titolo della
    # riga: e' il posto dove un titolo si legge, invece della tessera scura
    # in mezzo alle locandine ("un'icona nera chiamata a catalogo").
    # Il nome della sezione va davanti perche' "A CATALOGO" e "IN DIRETTA"
    # esistono sia nei documentari sia in cucina: senza prefisso sarebbero
    # due righe con lo stesso nome.
    for sezione, etichetta in (("documentari", "DOCUMENTARI"),
                               ("cucina", "CUCINA"),
                               ("youtube", "YOUTUBE")):
        for i, (intestazione, voci) in enumerate(sc.scaffale(sezione)):
            if not voci:
                continue
            titolo = "%s - %s" % (etichetta, intestazione) if intestazione \
                else etichetta
            righe.append((titolo, "%s:%d" % (sezione, i)))
    righe += [
        ("I FILM DELLE SAGHE",      "film"),
        ("AL CINEMA ORA",           "cinema"),
        ("SERIE TV",                "serietv"),
    ]
    return [(PRIMA_RIGA + i, t, c) for i, (t, c) in enumerate(righe)]


# --------------------------------------------------------------------------
# I PEZZI FISSI, presi dal file che c'e' gia'
# --------------------------------------------------------------------------

def pezzo_fisso(testo, da, a):
    """Il blocco fra due segni, estremi compresi. Serve a non riscrivere a
    mano la barra in alto, che funziona e non c'entra con le righe."""
    i = testo.index(da)
    j = testo.index(a, i)
    return testo[i:j + len(a)]


# --------------------------------------------------------------------------
# I PEZZI GENERATI
# --------------------------------------------------------------------------

def sfondi(righe):
    fuori = ["        <!-- ============ LO SFONDO: una immagine per riga.",
             "             Generato da fai-home.py: una per ogni riga, senza",
             "             saltarne nessuna. -->"]
    for rid, _t, _c in righe:
        fuori += [
            '        <control type="image">',
            "            <left>0</left><top>0</top><width>1920</width><height>1080</height>",
            "            <aspectratio>scale</aspectratio>",
            "            <fadetime>500</fadetime>",
            "            <visible>Control.HasFocus(%d)</visible>" % rid,
            '            <texture background="true">$INFO[Container(%d).ListItem.Art(fanart)]</texture>' % rid,
            "        </control>",
        ]
    return "\n".join(fuori)


def velature():
    """Le velature fra la fanart e il testo, e il passaggio verso le righe.

    IL GUASTO CHE CURA (detto dall'utente il 10/09/2026): "non si deve
    vedere il taglio netto tra la parte superiore ed inferiore".
    Prima qui c'era un rettangolo scuro che cominciava di colpo a y=380: a
    schermo era una RIGA ORIZZONTALE che tagliava l'immagine in due, e
    sembrava un errore. E' lo stesso identico difetto gia' avuto con la
    velatura da sinistra, curato allo stesso modo: una striscia sfumata,
    stirata sull'altezza che serve, invece di un bordo.
    """
    cima = CIMA_RIGHE - SFUMATURA
    return "\n".join([
        "        <!-- Le velature. Senza, il testo bianco su una fanart",
        "             chiara non si legge: e' gia' successo con la Vetrina. -->",
        '        <control type="image">',
        "            <left>0</left><top>0</top><width>1920</width><height>1080</height>",
        '            <texture colordiffuse="B00B0B0B">bianco.png</texture>',
        "        </control>",
        "        <!-- La velatura da SINISTRA. Era un rettangolo largo 1200 e",
        "             si vedeva lo stacco netto a meta' schermo. -->",
        '        <control type="image">',
        "            <left>0</left><top>0</top><width>1400</width><height>1080</height>",
        '            <texture colordiffuse="F00B0B0B">sfumatura.png</texture>',
        "        </control>",
        "        <!-- IL PASSAGGIO VERSO LE RIGHE: sfumato, non tagliato. -->",
        '        <control type="image">',
        "            <left>0</left><top>%d</top><width>1920</width><height>%d</height>"
        % (cima, SFUMATURA),
        "            <texture>velo-righe.png</texture>",
        "        </control>",
        '        <control type="image">',
        "            <left>0</left><top>%d</top><width>1920</width><height>%d</height>"
        % (CIMA_RIGHE, 1080 - CIMA_RIGHE),
        '            <texture colordiffuse="E60B0B0B">bianco.png</texture>',
        "        </control>",
    ])


def testate(righe):
    """La terna titolone / stato / trama per OGNI riga.

    Va per forza insieme alla lista: e' la meta' che il 10/09 mancava alla
    riga AL CINEMA ORA, e a schermo restava tutto bianco."""
    fuori = ["        <!-- ============ IL TITOLONE E LA TRAMA",
             "             Una terna per riga. Generata: non se ne puo'",
             "             dimenticare una. -->"]
    for rid, _t, _c in righe:
        fuori += [
            '        <control type="label">',
            "            <left>80</left><top>150</top><width>1200</width><height>96</height>",
            "            <font>font45_title</font><textcolor>FFF3EDE3</textcolor>",
            "            <shadowcolor>FF000000</shadowcolor>",
            "            <visible>Control.HasFocus(%d)</visible>" % rid,
            "            <label>$INFO[Container(%d).ListItem.Label]</label>" % rid,
            "        </control>",
            '        <control type="label">',
            "            <left>80</left><top>252</top><width>1200</width><height>36</height>",
            "            <font>font13</font><textcolor>FFE8A24A</textcolor>",
            "            <shadowcolor>FF000000</shadowcolor>",
            "            <visible>Control.HasFocus(%d)</visible>" % rid,
            "            <label>$INFO[Container(%d).ListItem.Label2]</label>" % rid,
            "        </control>",
            '        <control type="textbox">',
            # 300+210 = 510, e le righe cominciano a 600: 90 punti d'aria.
            # Prima il riquadro era alto 150 e l'ultima riga veniva TAGLIATA
            # A META' ("...tappa 1 di 227" col 227 mozzato). Ora ci stanno
            # comodamente cinque righe di trama.
            "            <left>80</left><top>300</top><width>1040</width><height>210</height>",
            "            <font>font13</font><textcolor>FFC6BCAF</textcolor>",
            "            <shadowcolor>FF000000</shadowcolor>",
            "            <visible>Control.HasFocus(%d)</visible>" % rid,
            "            <label>$INFO[Container(%d).ListItem.Plot]</label>" % rid,
            "        </control>",
        ]
    return "\n".join(fuori)


def elenco_righe(righe):
    """Le liste, con gli anelli su/giu' calcolati - mai scritti a mano."""
    fuori = [
        "        <!-- ============ LE RIGHE, dentro un gruppo che scorre in su",
        "             Un grouplist verticale scorre DA SOLO per tenere in",
        "             vista la riga scelta, e ritaglia quello che esce: e'",
        "             quello che usa Estuary per la sua home. Il primo",
        "             tentativo (un gruppo con le animazioni) non si mosse di",
        "             un punto e le righe finivano sopra la scritta in fondo.",
        "",
        "             GLI ANELLI onup/ondown SONO CALCOLATI. Scritti a mano,",
        "             il 07/09 ne mancavano due e quelle righe non le",
        "             raggiungeva nessun tasto.",
        "",
        "             ALTEZZA = 3 RIGHE ESATTE (3 x 214 = 642). Con un'altezza",
        "             qualunque il grouplist si fermava a META' RIGA e il",
        "             titolo di quella in cima si vedeva tagliato per lungo:",
        "             sembrava un errore di disegno. Un multiplo esatto fa",
        "             scorrere sempre righe intere. -->",
        '        <control type="grouplist" id="5000">',
        "            <left>0</left><top>%d</top><width>1920</width><height>%d</height>"
        % (CIMA_RIGHE, ALTEZZA_RIGHE),
        "            <orientation>vertical</orientation>",
        "            <itemgap>0</itemgap>",
        "            <usecontrolcoords>false</usecontrolcoords>",
        '            <scrolltime tween="cubic" easing="out">500</scrolltime>',
    ]
    n = len(righe)
    for k, (rid, titolo, che) in enumerate(righe):
        # La prima riga risale alla barra in alto; l'ultima riscende alla
        # prima, cosi' il giro si chiude e nessuna riga resta isolata.
        su = "6001" if k == 0 else str(righe[k - 1][0])
        giu = str(righe[(k + 1) % n][0])
        fuori += [
            "",
            '            <control type="group">',
            "                <left>0</left><top>0</top><width>1920</width><height>%d</height>" % ALTEZZA_RIGA,
            '                <control type="list" id="%d">' % rid,
            "                    <left>80</left><top>40</top><width>1790</width><height>174</height>",
            "                    <orientation>horizontal</orientation>",
            '                    <scrolltime tween="cubic" easing="out">400</scrolltime>',
            "                    <preloaditems>2</preloaditems>",
            "                    <onup>%s</onup><ondown>%s</ondown>" % (su, giu),
            "                    <onleft>noop</onleft><onright>noop</onright>",
            "                    <!-- Le voci che non sono cartelle (aggiungi un",
            "                         titolo da Netflix o dai consigli) si",
            "                         ESEGUONO; mandarle al riproduttore darebbe",
            '                         "errore di riproduzione". Le cartelle le',
            '                         apre il target="videos" del content. -->',
            '                    <onclick condition="!ListItem.IsFolder">RunPlugin($INFO[ListItem.FileNameAndPath])</onclick>',
            '                    <itemlayout width="300" height="174">',
            "                        <include>VideotecaLocandina</include>",
            "                    </itemlayout>",
            '                    <focusedlayout width="300" height="174">',
            "                        <include>VideotecaLocandinaScelta</include>",
            "                    </focusedlayout>",
            # target="videos" = la finestra in cui aprire la voce cliccata.
            # SENZA, il tasto OK non fa NIENTE e non lascia traccia da
            # nessuna parte. E' il guasto del 10/09.
            '                    <content target="videos">plugin://plugin.video.saghe/?azione=widget&amp;che=%s</content>' % che,
            "                </control>",
            '                <control type="label">',
            "                    <left>80</left><top>0</top><width>1200</width><height>28</height>",
            "                    <font>font13</font><textcolor>FFF3EDE3</textcolor>",
            "                    <shadowcolor>FF000000</shadowcolor>",
            "                    <label>%s</label>" % titolo,
            "                </control>",
            "            </control>",
        ]
    fuori.append("        </control>")
    return "\n".join(fuori)


TESTA = '''<?xml version="1.0" encoding="UTF-8"?>
<!--
  LA HOME IN STILE NETFLIX.

  *** FILE GENERATO DA traduttore/fai-home.py - NON MODIFICARLO A MANO ***
  Si cambia la tabella RIGHE dentro fai-home.py e si rilancia lo script.
  Ogni riga porta con se', per forza, quattro cose: lo sfondo, la terna di
  etichette della testata, la lista, e gli anelli su/giu'. Scritte a mano si
  sono rotte tutte e quattro almeno una volta, sempre senza dare errore.

  DA DOVE VENGONO LE LOCANDINE
      Non dalla libreria di Kodi, che qui e' vuota: da indirizzi plugin://
      del nostro add-on (`azione=widget`). La skin non sa niente di saghe:
      chiede, e l'add-on risponde.

  UNA RIGA PER GRUPPO (10/09/2026, scelta dell'utente)
      Documentari e Cucina erano UNA striscia sola - 143 tessere i primi -
      con dentro delle tessere scure a fare da separatore. "Fast N' Loud"
      stava verso la centesima: c'era, ma non ci arrivava nessuno. Adesso
      ogni gruppo e' una riga col suo titolo scritto sopra.
-->
<window>
    <!-- IL FUOCO PARTE DA "LE TUE SAGHE", NON DA "CONTINUA A GUARDARE".
         Provato il 07/09/2026 chiedendo a Kodi `System.CurrentControlId`: a
         scatola nuova la riga "continua" e' VUOTA, ma il fuoco ci restava
         sopra lo stesso e la testata restava tutta bianca. -->
    <defaultcontrol always="true">%(fuoco)d</defaultcontrol>
    <backgroundcolor>FF0B0B0B</backgroundcolor>

    <!-- NON RIMETTERE <onload>Container(<id>).Refresh</onload>.
         Aggiunto il 10/09/2026 per ricaricare le righe tornando alla home,
         non ha MAI funzionato: `Container(id).Refresh` non e' un'azione di
         Kodi. Quella forma esiste solo per le INFORMAZIONI
         (Container(5010).NumItems), non per i comandi. Kodi la rifiutava a
         ogni avvio, una riga per riga, e a schermo non si vedeva niente:
             Keymapping error: no such action 'container(5010).refresh'
         Non serve nemmeno: widget() chiude con cacheToDisc=False. -->

    <controls>

'''

CODA = '''
        <!-- ============ LA RIGA DEI TASTI, sempre in fondo -->
        <control type="label">
            <left>80</left><top>1034</top><width>1760</width><height>28</height>
            <font>font12</font>
            <textcolor>FF8C8175</textcolor>
            <label>Frecce per spostarti  -  OK per aprire  -  SU in cima per s4me, add-on, impostazioni e spegnimento</label>
        </control>

    </controls>
</window>
'''


def costruisci():
    vecchio = io.open(SKIN, encoding="utf-8").read()
    righe = tabella()

    # La barra in alto non c'entra con le righe e funziona: si riusa.
    barra = pezzo_fisso(vecchio, "        <!-- ============ LA BARRA IN ALTO",
                        "        <!-- ============ IL TITOLONE E LA TRAMA")
    barra = barra[:barra.index("        <!-- ============ IL TITOLONE")].rstrip()

    # Il fuoco parte da "LE TUE SAGHE": la prima riga mai vuota.
    fuoco = next((r[0] for r in righe if r[2] == "saghe"), righe[0][0])

    return "\n".join([
        TESTA % {"fuoco": fuoco},
        sfondi(righe), "",
        velature(), "",
        barra, "",
        testate(righe), "",
        elenco_righe(righe),
        CODA,
    ]), righe


# --------------------------------------------------------------------------
# I CONTROLLI. Girano SEMPRE, anche solo generando: un file che non passa
# non si scrive.
# --------------------------------------------------------------------------

def controlla(testo, righe):
    import xml.etree.ElementTree as ET
    guai = []
    try:
        radice = ET.fromstring(testo)
    except ET.ParseError as e:
        return ["XML non valido: %s" % e]

    liste = [c for c in radice.iter("control")
             if c.get("type") == "list" and (c.get("id") or "").isdigit()
             and int(c.get("id")) >= PRIMA_RIGA]
    attese = [r[0] for r in righe]
    if sorted(int(c.get("id")) for c in liste) != sorted(attese):
        guai.append("le liste nel file non sono quelle della tabella")

    # 1) ogni riga ha il target: senza, il tasto OK non fa niente
    for c in liste:
        cont = c.find("content")
        if cont is None or cont.get("target") != "videos":
            guai.append("riga %s: manca target=\"videos\" sul <content>" % c.get("id"))

    # 2) ogni riga ha la sua terna di etichette nella testata
    for rid in attese:
        for campo in ("Label", "Label2", "Plot"):
            if "Container(%d).ListItem.%s]" % (rid, campo) not in testo:
                guai.append("riga %d: manca l'etichetta %s nella testata" % (rid, campo))

    # 3) ogni riga ha il suo sfondo
    for rid in attese:
        if "Container(%d).ListItem.Art(fanart)" % rid not in testo:
            guai.append("riga %d: manca l'immagine di sfondo" % rid)

    # 4) il grouplist deve avere UN gruppo per riga, e ogni gruppo UNA lista
    #    e UNA etichetta. (Il 07/09 due righe finirono annidate in una sola:
    #    XML valido, due elenchi disegnati nello stesso riquadro.)
    gl = [c for c in radice.iter("control") if c.get("id") == "5000"][0]
    figli = [c for c in gl if c.tag == "control"]
    if len(figli) != len(righe):
        guai.append("il grouplist ha %d gruppi invece di %d"
                    % (len(figli), len(righe)))
    for g in figli:
        dentro_liste = [x for x in g.iter("control") if x.get("type") == "list"]
        dentro_etich = [x for x in g.iter("control") if x.get("type") == "label"]
        if len(dentro_liste) != 1 or len(dentro_etich) != 1:
            guai.append("un gruppo contiene %d liste e %d etichette (ne vuole 1 e 1)"
                        % (len(dentro_liste), len(dentro_etich)))

    # 5) la catena su/giu' deve passare da TUTTE le righe e richiudersi
    su, giu = {}, {}
    for c in liste:
        su[c.get("id")] = (c.findtext("onup") or "").strip()
        giu[c.get("id")] = (c.findtext("ondown") or "").strip()
    giro, cur = [], str(attese[0])
    for _ in range(len(attese) + 2):
        giro.append(cur)
        cur = giu.get(cur, "")
        if cur == str(attese[0]):
            break
    if len(giro) != len(attese) or cur != str(attese[0]):
        guai.append("la catena ondown non tocca tutte le righe o non si chiude")
    prima = str(attese[0])
    for c in liste:
        i = c.get("id")
        # L'ultima riga richiude sulla prima, ma la PRIMA sale sulla barra
        # in alto (6001), non sull'ultima: e' voluto, ed e' l'unico anello
        # che non torna indietro. Sta scritto qui perche' il controllo non
        # lo segnali come guasto ogni volta.
        if giu[i] == prima:
            if su[prima] != "6001":
                guai.append("la prima riga dovrebbe salire sulla barra in alto "
                            "(6001), invece sale su %s" % su[prima])
            continue
        if giu[i] in su and su[giu[i]] != i:
            guai.append("riga %s scende su %s, ma %s non risale su %s"
                        % (i, giu[i], giu[i], i))

    # 6) niente condizioni sul proprio contenuto: una riga nascosta non
    #    carica, quindi NumItems resta 0, quindi resta nascosta per sempre.
    if "Integer.IsGreater(Container(" in testo:
        guai.append("c'e' una condizione Integer.IsGreater(Container(...): "
                    "il cane si morde la coda, la riga non comparira' mai")
    return guai


def main():
    testo, righe = costruisci()
    guai = controlla(testo, righe)
    print("righe: %d  (da %d a %d)" % (len(righe), righe[0][0], righe[-1][0]))
    for rid, titolo, che in righe:
        print("   %d  %-46s %s" % (rid, titolo, che))
    print()
    if guai:
        print("CONTROLLI FALLITI - non scrivo niente:")
        for g in guai:
            print("   - " + g)
        return 1
    print("controlli: tutti passati")
    if "--controlla" in sys.argv:
        return 0
    io.open(SKIN, "w", encoding="utf-8", newline="\n").write(testo)
    print("scritto %s (%d byte)" % (SKIN, len(testo.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
