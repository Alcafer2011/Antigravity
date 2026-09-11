# -*- coding: utf-8 -*-
"""
IL PUNTO DI INGRESSO FUORI DALLE CARTELLE.

PERCHE' ESISTE, ed e' la lezione piu' cara di tutta questa storia
    Quando Kodi chiede a un add-on il contenuto di una cartella, tiene
    aperta la SUA finestra di attesa. Se da li' dentro si apre un'altra
    finestra - una barra di avanzamento nostra, o peggio un altro add-on
    che apre la propria - Kodi si trova due finestre di attesa sovrapposte
    e **si spegne di proposito**:

        critical: Logic error due to two concurrent busydialogs,
                  this is a known issue. The application will exit.

    E' successo davvero il 06/09/2026, due volte in due minuti: l'utente
    apriva un episodio dal nostro add-on e LibreELEC ripartiva. Non era un
    guasto del nostro codice: era il POSTO da cui lo eseguivamo.

    Un programma lanciato con `RunScript` gira per conto suo, senza nessuna
    finestra di attesa davanti. Da qui si puo' aprire quello che si vuole.

REGOLA, da non dimenticare mai piu'
    Dentro una cartella (`main.py`) si costruiscono SOLO elenchi.
    Tutto cio' che apre finestre, chiama altri add-on o riproduce video
    passa DA QUI.

COME SI CHIAMA
    RunScript(plugin.video.saghe, vetrina)
    RunScript(plugin.video.saghe, regola_s4me)
    RunScript(plugin.video.saghe, aggiungi_titolo, <tmdb>, <anime|serietv>)
    RunScript(plugin.video.saghe, togli_titolo, <tmdb>)

NOTA STORICA, perche' il file resti comprensibile
    Qui dentro c'era anche l'apertura degli episodi, con tutto il motore
    delle fonti. Non c'e' piu': dal 06/09/2026 gli episodi li trova s4me,
    che ha 55 fonti e le aggiorna da solo. Quel codice e' stato tolto, non
    lasciato a marcire: sta nella storia del deposito se dovesse servire.
"""

import sys

import xbmc
import xbmcgui


def _vetrina():
    from resources.lib import vetrina
    scelto = vetrina.apri("plugin://plugin.video.saghe/")
    if scelto:
        xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % scelto)


# Le leve di s4me che valgono la pena, con il valore giusto per questa casa.
#
# Sono impostazioni SUE: si scrivono con la sua stessa interfaccia, perche'
# modificargli il settings.xml a mano mentre Kodi gira non servirebbe a
# niente - lo riscrive lui uscendo.
LEVE_S4ME = [
    ("autoplay", "true",
     "Scelta automatica della fonte",
     "Senza, a ogni singolo episodio compare 'scegli un'opzione' e devi "
     "premere. Con, sceglie da solo e parte."),
    ("default_action", "1",
     "Qualita' video: Bassa",
     "Era su 'Chiedi'. Con 4 Mbps la qualita' alta non regge: scegliendo "
     "bassa in automatico il video parte e non si ferma. E' la stessa "
     "logica del tetto gia' messo su Netflix e Prime."),
    ("videolibrary_kodi", "true",
     "Videoteca di s4me dentro la libreria di Kodi",
     "Le saghe che aggiungi alla videoteca finiscono nella libreria Serie "
     "TV di Kodi: ripresa vera, prossimo episodio nativo, locandine "
     "ovunque. Da sola non fa niente finche' non aggiungi una saga."),
    ("next_ep", "1",
     "Prossimo episodio: automatico",
     "Funziona per le saghe messe nella videoteca."),
    # TRAKT: NON si accende, ed e' una scelta motivata.
    #
    # Provato il 06/09/2026: la chiave con cui QUESTA versione di s4me si
    # presenta a Trakt non e' piu' registrata da loro. La risposta e'
    #     401 {"error":"invalid_client","error_description":"client not found"}
    # Non e' un problema di configurazione: e' l'applicazione di s4me su
    # Trakt che non esiste piu'. Lasciare l'interruttore acceso darebbe
    # l'impressione che sincronizzi, e non sincronizza niente.
    ("trakt_sync", "false",
     "Sincronia con Trakt: spenta apposta",
     "La chiave di s4me non e' piu' valida su Trakt (risponde 'client not "
     "found'). Acceso non farebbe niente, quindi resta spento: il segno di "
     "dove sei arrivato lo teniamo noi, come prima."),
]


# Leve che, nel metterle, fanno comparire una finestra.
#
# `videolibrary_kodi` acceso fa partire la procedura guidata che chiede i
# provider delle informazioni: comodissima da fermi, insopportabile se
# compare sopra un film gia' cominciato. In modo silenzioso si salta.
LEVE_CHE_APRONO_FINESTRE = ("videolibrary_kodi",)


def _regola_s4me(muto=False):
    """Mette in s4me i valori giusti per questa casa, e racconta cosa ha fatto.

    Con `muto` non apre NIENTE: ne' il riepilogo finale, ne' le leve che si
    tirano dietro una finestra. Serve per regolare un apparecchio mentre lo
    si sta usando, senza interrompere quello che c'e' sullo schermo.
    """
    import xbmcaddon
    try:
        s4 = xbmcaddon.Addon("plugin.video.s4me")
    except Exception:
        if not muto:
            xbmcgui.Dialog().ok("Le Saghe", "s4me non e' installato.")
        return

    righe = []
    for chiave, valore, nome, perche in LEVE_S4ME:
        if muto and chiave in LEVE_CHE_APRONO_FINESTRE:
            xbmc.log("[Le Saghe] muto: salto %s (aprirebbe una finestra)"
                     % chiave, xbmc.LOGINFO)
            continue
        prima = s4.getSetting(chiave)
        if prima == valore:
            righe.append("[COLOR grey]gia' a posto[/COLOR]  %s" % nome)
            continue
        try:
            s4.setSetting(chiave, valore)
            righe.append("[B]cambiato[/B]  %s\n   %s" % (nome, perche))
        except Exception as e:
            righe.append("[COLOR red]non riuscito[/COLOR]  %s (%s)" % (nome, e))

    if muto:
        for r in righe:
            xbmc.log("[Le Saghe] %s" % r.replace("\n", " "), xbmc.LOGINFO)
        return

    xbmcgui.Dialog().textviewer(
        "s4me regolato per questa casa",
        "\n\n".join(righe) +
        "\n\n\n[B]Cosa fare adesso[/B]\n"
        "Per avere il passaggio automatico all'episodio dopo, apri una saga "
        "dentro s4me (canale 'Le Saghe'), premi Menu sul titolo e scegli "
        "[B]Aggiungi alla videoteca[/B].\n\n"
        "Falla UNA saga per volta, quella che stai guardando: ogni saga "
        "crea un file per episodio, e con tutte insieme sarebbero migliaia "
        "di file da scansionare su un Raspberry.\n\n"
        "[B]Su Trakt: non si puo' fare, e non e' colpa tua[/B]\n"
        "La chiave con cui questa versione di s4me si presenta a Trakt non "
        "e' piu' registrata da loro: risponde 'client not found'. Acceso "
        "non sincronizzerebbe niente, quindi resta spento apposta.\n"
        "Il segno di dove sei arrivato continua a tenerlo il nostro "
        "quaderno, come prima: non si perde nulla.")


def _una_riga(testo):
    """Un avviso e' una riga sola: via grassetti, colori e a capo."""
    import re
    return re.sub(r"\[/?(B|I|COLOR)[^\]]*\]", "", testo or "").replace(
        "\n", " ").strip()


def _via_dalla_pagina_vuota():
    """La tessera della home e' una cartella: chiusa senza contenuto, Kodi
    resta sulla radice della finestra Video ("File", "Add-on"...). Visto sul
    banco il 10/09/2026. Se succede entro pochi istanti si torna alla home.
    Dal menu Netflix interno il percorso non e' vuoto e non si tocca nulla.
    """
    monitor = xbmc.Monitor()
    for _ in range(15):
        if (xbmcgui.getCurrentWindowId() == 10025
                and not xbmc.getInfoLabel("Container.FolderPath")):
            xbmc.executebuiltin("ActivateWindow(home)")
            return
        if monitor.waitForAbort(0.2):
            return


def _aggiorna_se_home():
    # SOLO sulla home, dove Container.Refresh ricarica la riga di tessere.
    # Sulla pagina che ha lanciato l'azione rileggerebbe la stessa cartella
    # e rifarebbe l'aggiunta: e' il ciclo trovato sul banco il 10/09/2026.
    if xbmcgui.getCurrentWindowId() == 10000:
        xbmc.executebuiltin("Container.Refresh")


def _aggiungi_titolo(tmdb_id, tipo):
    """Aggiunge una serie da Consigliati o da Netflix, senza riquadri.

    PERCHE' QUI E NON IN main.py (10/09/2026, provato col tasto OK sul
    banco): la tessera e' una cartella, e quando l'aggiunta girava dentro
    la cartella, chiudere il riquadro "Aggiunto" faceva rileggere la stessa
    cartella a Kodi, che la aggiungeva di nuovo, all'infinito. Dietro al
    riquadro si vedeva una pagina vuota "Video - 0 film".
    Come fa Netflix: niente da confermare, una barra in un angolo mentre
    scarica la scheda e un avviso con la locandina quando ha finito.
    """
    from resources.lib import consigli, schede
    _via_dalla_pagina_vuota()
    barra = xbmcgui.DialogProgressBG()
    barra.create("Le Saghe", "Aggiungo il titolo e scarico la sua scheda...")
    try:
        fatto, messaggio = consigli.aggiungi(tmdb_id, tipo=tipo)
    finally:
        barra.close()
    if not fatto:
        xbmcgui.Dialog().notification("Non aggiunto", _una_riga(messaggio),
                                      xbmcgui.NOTIFICATION_WARNING, 6000)
        return
    sid = "tmdb_%s" % tmdb_id
    titolo = (consigli.serie_mie().get(sid) or {}).get("titolo") or "Aggiunto"
    dove = "Serie TV" if tipo == "serietv" else "Cartoni animati"
    _aggiorna_se_home()
    _avviso(titolo, "Aggiunto alla Videoteca, in %s" % dove,
            schede.poster(sid))


# Quanto resta a schermo l'avviso. Netflix non chiede conferme: avvisa e
# sparisce da solo.
DURATA_AVVISO = 6


def _avviso(titolo, testo, immagine=""):
    """L'avviso grande con la locandina (resources/skins/.../avviso.xml).

    La notifica di Kodi la disegna la skin, e su Arctic Zephyr dal divano
    non si legge. Se la nostra finestra non si apre - skin strana, file
    mancante - si ripiega sulla notifica normale: meglio piccola che niente.
    """
    # AL PRIMO TASTO SI CHIUDE. Una finestra di Python aperta con show()
    # riceve lei i tasti: sul banco (10/09/2026) la freccia non spostava piu'
    # le tessere finche' l'avviso restava a schermo. Chiuderla al primo tasto
    # vuol dire al massimo un tasto "speso", mai sei secondi di telecomando
    # morto.
    class _Finestra(xbmcgui.WindowXMLDialog):
        chiusa = False

        def onAction(self, azione):
            self.chiusa = True
            self.close()

    try:
        import xbmcaddon
        percorso = xbmcaddon.Addon("plugin.video.saghe").getAddonInfo("path")
        finestra = _Finestra("avviso.xml", percorso, "Default", "1080i")
        finestra.setProperty("titolo", titolo or "")
        finestra.setProperty("testo", testo or "")
        finestra.setProperty("immagine", immagine or "")
        finestra.show()
        monitor = xbmc.Monitor()
        for _ in range(DURATA_AVVISO * 5):
            if finestra.chiusa or monitor.waitForAbort(0.2):
                break
        if not finestra.chiusa:
            finestra.close()
        del finestra
    except Exception as e:
        xbmc.log("[Le Saghe] avviso grande non aperto: %s" % e, xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(titolo or "Le Saghe", testo or "",
                                      immagine or xbmcgui.NOTIFICATION_INFO,
                                      DURATA_AVVISO * 1000)


def _togli_titolo(tmdb_id):
    """Toglie una serie aggiunta da te. Qui la domanda resta: si perde il
    segno di dove eri arrivato, e un tasto premuto per sbaglio non basta."""
    from resources.lib import consigli
    _via_dalla_pagina_vuota()
    if not xbmcgui.Dialog().yesno(
            "Toglierla?",
            "Vuoi toglierla dalle tue serie?\n\nIl segno di dove sei "
            "arrivato si perde. Puoi sempre riaggiungerla dai consigli."):
        return
    fatto, messaggio = consigli.togli("tmdb_%s" % tmdb_id)
    if fatto:
        _aggiorna_se_home()
    _avviso("Tolta" if fatto else "Non tolta", _una_riga(messaggio))


def _apri_film(pid, titolo_hex):
    """Un film del catalogo: la sua app se c'e', altrimenti la ricerca su s4me.

    Prima stava in main.py e usava ponte_s4me, che non esiste piu' dal commit
    77d75a7: il film senza fonte finiva in NameError. La ricerca su s4me si
    apre con lo stesso indirizzo che usa gia' la Ricerca della Videoteca.
    """
    from resources.lib import catalogo, fonti
    try:
        titolo = bytes.fromhex(titolo_hex).decode("utf-8") if titolo_hex not in ("", "00") else ""
    except ValueError:
        titolo = ""
    _via_dalla_pagina_vuota()
    percorso = catalogo.PERCORSI.get(pid)
    if not percorso:
        xbmcgui.Dialog().notification("Le Saghe", "Film non trovato nel catalogo",
                                      xbmcgui.NOTIFICATION_WARNING, 5000)
        return
    titolo = titolo or percorso.get("titolo", "")
    fonte = fonti.fonte_migliore(percorso["segmenti"][0][0], 1)
    if fonte and fonte["tipo"] == "app":
        xbmcgui.Dialog().notification("Le Saghe", "Cerca: %s" % titolo,
                                      xbmcgui.NOTIFICATION_INFO, 8000)
        fonti.avvia_app(catalogo.FONTI[fonte["id"]]["pacchetto"])
        return
    if titolo and xbmc.getCondVisibility("System.HasAddon(plugin.video.s4me)"):
        # Niente domanda "vuoi cercarlo su s4me?" (e l'indirizzo che apriva,
        # action=Search, in s4me non esiste: registro del Raspberry, 11/09/2026).
        # La ricerca parte da sola su tutti i siti e si apre la pagina.
        _cerca_e_mostra(titolo)
        return
    xbmcgui.Dialog().ok("Le Saghe",
                        "Per questo film non c'e' ancora una fonte configurata. %s" % titolo)


def _stato_linea():
    from resources.lib import taratura
    xbmcgui.Dialog().textviewer("La mia linea", taratura.racconta())


def _anomalie():
    from resources.lib import progresso
    righe = ["%s\n   chiesto:  %s\n   partito:  %s\n" % (a["quando"], a["atteso"], a["ottenuto"])
             for a in progresso.anomalie()[::-1]]
    xbmcgui.Dialog().textviewer("Episodi sbagliati", "\n".join(righe) or "Nessuna anomalia.")


def _russo_consiglio():
    from resources.lib import russo
    xbmcgui.Dialog().textviewer("Russo con i cartoni", russo.CONSIGLIO)


def _spiega(pid):
    from resources.lib import catalogo
    p = catalogo.PERCORSI.get(pid)
    if not p:
        return
    righe = [p["spiegazione"], "", "[B]Come e' composta la catena:[/B]"]
    n = 0
    for serie_id, primo, ultimo in p["segmenti"]:
        serie = catalogo.SERIE[serie_id]
        quanti = ultimo - primo + 1
        righe.append("- %s, episodi %d-%d  (tappe %d-%d)%s" % (
            serie["titolo"], primo, ultimo, n + 1, n + quanti,
            "" if serie["verificato"] else "  <- conteggio da confermare"))
        n += quanti
    righe.append("")
    righe.append("Totale: %d episodi." % n)
    xbmcgui.Dialog().textviewer(p["titolo"], "\n".join(righe))


def _azzera(pid):
    from resources.lib import catalogo, progresso
    if pid not in catalogo.PERCORSI:
        return
    if xbmcgui.Dialog().yesno(
            "Le Saghe",
            "Azzerare il progresso di [B]%s[/B]?\n"
            "Tornerai al primo episodio." % catalogo.PERCORSI[pid]["titolo"]):
        progresso.azzera(pid)
        xbmc.executebuiltin("Container.Refresh")


def _salta(pid):
    from resources.lib import catalogo, progresso
    if pid not in catalogo.PERCORSI:
        return
    totale = catalogo.lunghezza(pid)
    corrente = progresso.posizione(pid)
    scelta = xbmcgui.Dialog().numeric(0, "Tappa da cui ripartire (1-%d)" % totale, str(corrente))
    if not scelta or not str(scelta).isdigit():
        return
    n = max(1, min(int(scelta), totale))
    progresso.vai_a(pid, n)
    xbmcgui.Dialog().notification("Le Saghe", catalogo.descrizione_segmento(pid, n),
                                  xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin("Container.Refresh")


def _capitoli(pid):
    from resources.lib import catalogo, progresso
    archi = catalogo.archi_di(pid)
    if not archi:
        return
    corrente = progresso.posizione(pid)
    righe = []
    for nome, da, a in archi:
        segno = "[COLOR yellow]  <- sei qui[/COLOR]" if da <= corrente <= a else ""
        righe.append("%s   [COLOR grey](tappe %d-%d)[/COLOR]%s" % (nome, da, a, segno))
    scelta = xbmcgui.Dialog().select("Vai a un capitolo", righe)
    if scelta < 0:
        return
    nome, da, _a = archi[scelta]
    progresso.vai_a(pid, da)
    xbmcgui.Dialog().notification("Le Saghe", "Sei all'inizio di: %s" % nome,
                                  xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin("Container.Refresh")


def _cerca_nuova():
    """La tastiera della ricerca, fuori dalla cartella.

    La casella parte SEMPRE vuota (il difetto del 06/09/2026: con dentro la
    ricerca di prima, col telecomando Indietro chiude invece di cancellare e
    non se ne esce). Scritto il testo, la ricerca parte da sola su catalogo e
    siti (11/09/2026): vedi _cerca_e_mostra.
    """
    testo = xbmcgui.Dialog().input("Cerca dappertutto: catalogo e tutti i siti",
                                   defaultt="", type=xbmcgui.INPUT_ALPHANUM)
    if not testo:
        return
    _cerca_e_mostra(testo)


def _cerca_testo(esadecimale):
    """Una ricerca gia' scritta (le ricerche recenti), col testo in esadecimale."""
    try:
        testo = bytes.fromhex(esadecimale).decode("utf-8") if esadecimale not in ("", "00") else ""
    except ValueError:
        testo = ""
    if testo:
        _cerca_e_mostra(testo)


def _cerca_e_mostra(testo):
    """Cerca su tutti i siti con la barra in un angolo, poi apre i risultati.

    La ricerca sui siti dura qualche decina di secondi. Dentro la cartella
    sarebbe una pagina bianca con la rotellina; qui invece si vede la barra
    ("12 siti su 40 - 23 risultati") e la pagina si apre gia' piena, perche'
    la risposta resta in memoria (ricerca_siti.py). Se c'e' gia' in memoria,
    la pagina si apre subito."""
    import threading
    import time
    from urllib.parse import urlencode
    from resources.lib import ricerca_siti
    if ricerca_siti.s4me_presente() and not ricerca_siti.dalla_cache(testo):
        barra = xbmcgui.DialogProgressBG()
        barra.create("Cerco '%s'" % testo, "Chiedo a tutti i siti insieme...")
        filo = threading.Thread(target=ricerca_siti.cerca, args=(testo,))
        filo.daemon = True
        filo.start()
        monitor = xbmc.Monitor()
        inizio = time.time()
        try:
            while filo.is_alive():
                st = ricerca_siti.stato()
                if st.get("testo") == testo and st.get("totale"):
                    barra.update(int(100 * st.get("fatti", 0) / max(1, st["totale"])), "Cerco '%s'" % testo,
                                 "%d siti su %d  -  %d risultati" % (st.get("fatti", 0), st["totale"],
                                                                      st.get("trovati", 0)))
                else:
                    barra.update(min(95, int((time.time() - inizio) * 3)), "Cerco '%s'" % testo,
                                 "Chiedo a tutti i siti insieme...")
                if monitor.waitForAbort(0.5):
                    return
        finally:
            barra.close()
    indirizzo = "plugin://plugin.video.saghe/?%s" % urlencode({"azione": "cerca", "testo": testo})
    if xbmc.getCondVisibility("Window.IsActive(videos)"):
        xbmc.executebuiltin("Container.Update(%s)" % indirizzo)
    else:
        xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % indirizzo)


def _misura_linea():
    """La misura della linea con la sua barra. Qui, fuori dalla cartella, la
    barra non si scontra con la rotellina di Kodi."""
    from resources.lib import taratura
    _via_dalla_pagina_vuota()
    d = xbmcgui.DialogProgress()
    d.create("Le Saghe", "Misuro la linea...")
    valori = []
    for n in range(3):
        if d.iscanceled():
            d.close()
            return
        d.update(int(n * 100 / 3),
                 "Misuro la linea...  prova %d di 3\n\n"
                 "Sto scaricando qualche megabyte per vedere quanto va." % (n + 1))
        v = taratura._misura_una()
        if v > 0:
            valori.append(v)
    d.close()
    if not valori:
        xbmcgui.Dialog().ok("Le Saghe",
                            "Non sono riuscito a misurare: la linea non risponde.\n\n"
                            "Non ho cambiato niente. Riprova piu' tardi.")
        return
    fatto, testo = taratura.applica(round(max(valori), 2))
    xbmcgui.Dialog().ok("La mia linea" if fatto else "Non ho potuto regolare", testo)


# --------------------------------------------------------------------------
# CERCA AGGIORNAMENTI (chiesto dall'utente l'11/09/2026)
#
# "aggiungerei un pulsante cerca aggiornamenti cosi' senza attendere un giorno
# posso fargli cercare e se ci sono li scarica e li installa".
# 1. Si legge l'indice del NOSTRO repository (privato: il token sta
#    nell'indirizzo come utente:token@, che urllib non accetta - si toglie e
#    si manda come intestazione) e si confrontano le versioni.
# 2. UpdateAddonRepos: Kodi rilegge TUTTI i repository e, con gli
#    aggiornamenti automatici accesi (lo sono su PC, box e Raspberry),
#    installa da solo. Si aspetta, mostrando l'avanzamento.
# 3. Se dopo due minuti non l'ha fatto, lo si fa qui: pacchetto scaricato,
#    controllato (addon.xml e versione), la copia vecchia spostata FUORI da
#    addons/ (un backup li' dentro Kodi lo esegue al posto del nuovo, 10/09).
# --------------------------------------------------------------------------

NOSTRI_ADDON = {"plugin.video.saghe": "Videoteca", "service.videoteca.guardiano": "Guardiano"}


def _versione_tupla(v):
    import re
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def _installata(aid):
    import json
    r = json.loads(xbmc.executeJSONRPC(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails",
        "params": {"addonid": aid, "properties": ["version"]}})))
    return ((r.get("result") or {}).get("addon") or {}).get("version", "")


def _repository():
    import base64
    import io
    import re
    import xbmcvfs
    p = xbmcvfs.translatePath("special://home/addons/repository.videoteca/addon.xml")
    with io.open(p, encoding="utf-8") as f:
        testo = f.read()
    info = re.search(r"<info[^>]*>([^<]+)</info>", testo).group(1).strip()
    datadir = re.search(r"<datadir[^>]*>([^<]+)</datadir>", testo).group(1).strip()
    intestazioni = {"User-Agent": "Kodi-Videoteca"}
    m = re.match(r"(https?://)([^:@/]+):([^@/]+)@(.+)", info)
    if m:
        segreto = base64.b64encode(("%s:%s" % (m.group(2), m.group(3))).encode("utf-8")).decode("ascii")
        intestazioni["Authorization"] = "Basic " + segreto
        info = m.group(1) + m.group(4)
        datadir = re.sub(r"(https?://)[^@/]+@", r"\1", datadir)
    return info, datadir.rstrip("/"), intestazioni


def _scarica(indirizzo, intestazioni, tempo=30):
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(indirizzo, headers=intestazioni), timeout=tempo) as r:
        return r.read()


def _pubblicate():
    import re
    info, datadir, intestazioni = _repository()
    indice = _scarica(info, intestazioni).decode("utf-8", "replace")
    fuori = {}
    for m in re.finditer(r"<addon\b[^>]*>", indice):
        ident = re.search(r'\bid="([^"]+)"', m.group(0))
        versione = re.search(r'\bversion="([^"]+)"', m.group(0))
        if ident and versione:
            fuori[ident.group(1)] = versione.group(1)
    return fuori, datadir, intestazioni


def _installa_a_mano(aid, versione, datadir, intestazioni):
    import io
    import os
    import shutil
    import time
    import zipfile
    import xbmcvfs
    dati = _scarica("%s/%s/%s-%s.zip" % (datadir, aid, aid, versione), intestazioni, 180)
    appoggio = xbmcvfs.translatePath("special://temp/videoteca-aggiorna/")
    shutil.rmtree(appoggio, ignore_errors=True)
    os.makedirs(appoggio)
    pacchetto = os.path.join(appoggio, "pacchetto.zip")
    with open(pacchetto, "wb") as f:
        f.write(dati)
    with zipfile.ZipFile(pacchetto) as z:
        if "%s/addon.xml" % aid not in z.namelist():
            raise ValueError("pacchetto senza %s/addon.xml" % aid)
        z.extractall(appoggio)
    nuovo = os.path.join(appoggio, aid)
    with io.open(os.path.join(nuovo, "addon.xml"), encoding="utf-8") as f:
        if 'version="%s"' % versione not in f.read():
            raise ValueError("dentro il pacchetto non c'e' la versione %s" % versione)
    vecchio = xbmcvfs.translatePath("special://home/addons/%s" % aid)
    scorta = xbmcvfs.translatePath("special://home/backup-aggiornamenti/")
    os.makedirs(scorta, exist_ok=True)
    if os.path.isdir(vecchio):
        shutil.move(vecchio, os.path.join(scorta, "%s-%s" % (aid, time.strftime("%Y%m%d-%H%M%S"))))
    shutil.move(nuovo, vecchio)
    for vecchia in sorted(d for d in os.listdir(scorta) if d.startswith(aid + "-"))[:-2]:
        shutil.rmtree(os.path.join(scorta, vecchia), ignore_errors=True)
    shutil.rmtree(appoggio, ignore_errors=True)
    xbmc.executebuiltin("UpdateLocalAddons")


def _aggiornamenti():
    import time
    barra = xbmcgui.DialogProgressBG()
    barra.create("Cerca aggiornamenti", "Chiedo al repository cosa c'e' di nuovo...")
    monitor = xbmc.Monitor()
    try:
        try:
            pubblicate, datadir, intestazioni = _pubblicate()
        except Exception as e:
            xbmc.log("[Le Saghe] aggiornamenti, repository: %s" % e, xbmc.LOGWARNING)
            xbmcgui.Dialog().notification("Aggiornamenti", "Il repository non risponde: riprova fra poco",
                                          xbmcgui.NOTIFICATION_WARNING, 7000)
            return
        # Tutti i repository, non solo il nostro: s4me e gli altri si aggiornano insieme.
        xbmc.executebuiltin("UpdateAddonRepos")
        da_fare = {}
        for aid in NOSTRI_ADDON:
            adesso, nuova = _installata(aid), pubblicate.get(aid, "")
            if adesso and nuova and _versione_tupla(nuova) > _versione_tupla(adesso):
                da_fare[aid] = nuova
        if not da_fare:
            barra.update(100, "Cerca aggiornamenti", "Nessuna novita'")
            xbmcgui.Dialog().notification(
                "Tutto aggiornato", "Videoteca %s: e' l'ultima versione" % _installata("plugin.video.saghe"),
                xbmcgui.NOTIFICATION_INFO, 6000)
            return
        elenco = ", ".join("%s %s" % (NOSTRI_ADDON[a], v) for a, v in da_fare.items())
        inizio = time.time()
        restano = dict(da_fare)
        while restano and time.time() - inizio < 120:
            barra.update(10 + int(70 * (time.time() - inizio) / 120), "Aggiornamento trovato", "Kodi installa %s..." % elenco)
            if monitor.waitForAbort(2):
                return
            restano = {a: v for a, v in restano.items() if _versione_tupla(_installata(a)) < _versione_tupla(v)}
        a_mano = []
        for aid, versione in restano.items():
            barra.update(85, "Aggiornamento", "Installo %s %s..." % (NOSTRI_ADDON[aid], versione))
            _installa_a_mano(aid, versione, datadir, intestazioni)
            a_mano.append(aid)
        barra.update(100, "Aggiornamento", "Fatto")
        testo = "Installato: %s" % elenco
        if a_mano:
            # installato a mano, un servizio gira ancora col codice di prima
            testo += ". Riavvia Kodi per finire"
        xbmcgui.Dialog().notification("Aggiornamenti", testo, xbmcgui.NOTIFICATION_INFO, 9000)
    except Exception as e:
        xbmc.log("[Le Saghe] aggiornamenti: %s" % e, xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Aggiornamenti", "Non riuscito: %s" % str(e)[:80],
                                      xbmcgui.NOTIFICATION_ERROR, 8000)
    finally:
        barra.close()


# --------------------------------------------------------------------------
# QUALCOSA NON VA (11/09/2026)
#
# Dal menu della Videoteca o dal tasto MENU di una locandina. Si fotografa lo
# schermo e si scrive una riga nella SCATOLA NERA del guardiano: il resto
# (cosa si stava facendo, gli errori di quei secondi) c'e' gia' li'.
# Sul PC: python registratore.py box|pi.
# --------------------------------------------------------------------------

def _segnala(esadecimale="00"):
    import io
    import json
    import os
    import time
    import xbmcvfs
    try:
        titolo = bytes.fromhex(esadecimale).decode("utf-8", "replace") if esadecimale not in ("", "00") else ""
    except ValueError:
        titolo = ""
    cartella = xbmcvfs.translatePath("special://profile/addon_data/service.videoteca.guardiano/scatola_nera/")
    scatti = os.path.join(cartella, "scatti")
    os.makedirs(scatti, exist_ok=True)
    xbmc.Monitor().waitForAbort(0.5)          # si chiude il menu: la foto deve vedere lo schermo sotto
    adesso = time.time()
    nome = time.strftime("%Y%m%d-%H%M%S", time.localtime(adesso)) + "-segnalata.png"
    xbmc.executebuiltin("TakeScreenshot(%s,sync)" % os.path.join(scatti, nome))
    riga = {"t": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(adesso)), "ts": round(adesso, 2),
            "tipo": "anomalia", "genere": "segnalata", "scatto": nome,
            "testo": "Segnalato da te" + (": %s" % titolo if titolo else ""),
            "cartella": xbmc.getInfoLabel("Container.FolderPath"), "voce": xbmc.getInfoLabel("ListItem.Label")}
    with io.open(os.path.join(cartella, time.strftime("%Y-%m-%d", time.localtime(adesso)) + ".jsonl"),
                 "a", encoding="utf-8") as f:
        f.write(json.dumps(riga, ensure_ascii=False) + "\n")
    xbmcgui.Dialog().notification("Segnato", "Ho fotografato lo schermo e segnato l'ora: lo guardo io",
                                  xbmcgui.NOTIFICATION_INFO, 5000)


def main():
    comando = sys.argv[1] if len(sys.argv) > 1 else "vetrina"
    # Le finestre che prima si aprivano dentro le cartelle (11/09/2026).
    senza_argomenti = {"stato_linea": _stato_linea, "anomalie": _anomalie,
                       "russo_consiglio": _russo_consiglio, "cerca_nuova": _cerca_nuova,
                       "aggiornamenti": _aggiornamenti}
    con_un_argomento = {"spiega": _spiega, "azzera": _azzera, "salta": _salta, "capitoli": _capitoli,
                        "segnala": _segnala, "cerca_testo": _cerca_testo}
    if comando in senza_argomenti or comando in con_un_argomento:
        try:
            if comando in senza_argomenti:
                senza_argomenti[comando]()
            else:
                con_un_argomento[comando](sys.argv[2] if len(sys.argv) > 2 else "")
        except Exception as e:
            xbmc.log("[Le Saghe] %s: %s" % (comando, e), xbmc.LOGERROR)
        return
    if comando == "misura_linea":
        # RunScript(plugin.video.saghe, misura_linea)
        try:
            _misura_linea()
        except Exception as e:
            xbmc.log("[Le Saghe] misura_linea: %s" % e, xbmc.LOGERROR)
        return
    if comando == "apri_film":
        # RunScript(plugin.video.saghe, apri_film, <pid>, <titolo in esadecimale>)
        try:
            _apri_film(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "00")
        except Exception as e:
            xbmc.log("[Le Saghe] apri_film: %s" % e, xbmc.LOGERROR)
        return
    try:
        if comando == "vetrina":
            _vetrina()
        elif comando == "regola_s4me":
            # RunScript(plugin.video.saghe, regola_s4me, muto)
            _regola_s4me(muto=(len(sys.argv) > 2 and sys.argv[2] == "muto"))
        elif comando == "aggiungi_titolo":
            # RunScript(plugin.video.saghe, aggiungi_titolo, <tmdb>, <anime|serietv>)
            _aggiungi_titolo(sys.argv[2],
                             sys.argv[3] if len(sys.argv) > 3 else "anime")
        elif comando == "togli_titolo":
            # RunScript(plugin.video.saghe, togli_titolo, <tmdb>)
            _togli_titolo(sys.argv[2])
        else:
            xbmc.log("[Le Saghe] comando sconosciuto: %s" % comando,
                     xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log("[Le Saghe] avvio.py: %s" % e, xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Le Saghe", "Qualcosa e' andato storto",
                                      xbmcgui.NOTIFICATION_ERROR, 5000)


if __name__ == "__main__":
    main()
