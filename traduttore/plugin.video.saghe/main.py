# -*- coding: utf-8 -*-
"""Le Saghe - punto di ingresso del plugin."""

import sys
import time
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib import (abbonamenti, catalogo, fonti, motore, progresso,
                          ricerca, russo as russo_lib, schede, taratura,
                          vetrina, ponte_s4me)

ADDON = xbmcaddon.Addon()
MANIGLIA = int(sys.argv[1])
BASE = sys.argv[0]

PAGINA = 100  # tappe per pagina quando si sfoglia


def url(**kwargs):
    return BASE + "?" + urlencode(kwargs)


def _voce(etichetta, descrizione="", cartella=True, url_voce=None,
          icona="DefaultVideo.png", riproducibile=False):
    li = xbmcgui.ListItem(label=etichetta)
    li.setArt({"icon": icona, "thumb": icona})
    tag = li.getVideoInfoTag()
    tag.setTitle(etichetta)
    if descrizione:
        tag.setPlot(descrizione)
    if riproducibile:
        li.setProperty("IsPlayable", "true")
    return li


# --------------------------------------------------------------------------
# Continua a guardare
#
# La riga che sta in cima a Netflix, e per un buon motivo: chi accende la TV
# quasi sempre vuole riprendere una cosa sola. Farla cercare fra quattordici
# saghe, ognuna con centinaia di tappe, e' una scortesia.
# Qui le voci NON sono cartelle: partono al primo colpo.
# --------------------------------------------------------------------------

def _riga_continua():
    """Mette in cima le saghe toccate di recente. Quante voci ha aggiunto."""
    righe = progresso.recenti(4)
    if not righe:
        return 0

    messe = 0
    for r in righe:
        pid = r["percorso"]
        p = catalogo.PERCORSI.get(pid)
        if not p:
            continue                      # saga tolta dal catalogo: si salta
        t = catalogo.tappa(pid, r["idx"])
        if not t:
            continue
        serie = catalogo.SERIE[t["serie"]]
        sch = schede.episodio(t["serie"], t["ep"])

        titolo_ep = sch["titolo"] or ("Episodio %d" % t["ep"])
        # Il minuto esatto lo abbiamo solo per i video passati dentro Kodi.
        if r["durata"] > 0 and r["secondi"] > 0:
            resta = max(0, r["durata"] - r["secondi"])
            coda = "ripartiamo da %s - mancano %s" % (_mmss(r["secondi"]), _mmss(resta))
        else:
            coda = "%s, episodio %d" % (serie["titolo"], t["ep"])

        li = xbmcgui.ListItem(
            label="[B]%s[/B]\n[COLOR grey]%s - %s[/COLOR]"
                  % (p["titolo"], titolo_ep, coda))
        # "riproducibile" NON si decide qui: lo decide metti_tappa, in un
        # posto solo, guardando se la fonte e' davvero un file che Kodi apre.

        tag = li.getVideoInfoTag()
        tag.setTitle("%s - %s" % (p["titolo"], titolo_ep))
        tag.setTvShowTitle(serie["titolo"])
        tag.setEpisode(t["ep"])
        tag.setMediaType("episode")
        if sch["trama"]:
            tag.setPlot(sch["trama"])
        # La barretta verde sotto la locandina: e' questa che fa sembrare
        # l'add-on un servizio vero invece che un elenco.
        if r["durata"] > 0 and r["secondi"] > 0:
            try:
                tag.setResumePoint(float(r["secondi"]), float(r["durata"]))
            except Exception:
                pass

        arte = {}
        immagine = sch["immagine"] or schede.poster(t["serie"])
        if immagine:
            arte["thumb"] = arte["icon"] = immagine
        if schede.poster(t["serie"]):
            arte["poster"] = schede.poster(t["serie"])
        if schede.sfondo(t["serie"]):
            arte["fanart"] = schede.sfondo(t["serie"])
        if arte:
            li.setArt(arte)

        metti_tappa(pid, r["idx"], t, li)
        messe += 1

    return messe


# --------------------------------------------------------------------------
# Menu principale
# --------------------------------------------------------------------------

def menu_principale():
    xbmcplugin.setPluginCategory(MANIGLIA, "Le Saghe")
    # Con un tipo di contenuto dichiarato la pelle di Kodi mostra le locandine
    # a griglia invece di un elenco di testo. Senza questa riga, tutto il
    # lavoro sulle immagini non si vede.
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    _riga_continua()

    li = _voce("Vetrina\n[COLOR grey]la schermata a righe, come Netflix[/COLOR]",
               "Locandine grandi, righe che scorrono di lato, sfondo della "
               "serie selezionata. E' una schermata disegnata da noi: la "
               "pelle di Kodi da sola non la sa fare.",
               icona="DefaultAddonSkin.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="vetrina"), li, True)

    # La ricerca sta in cima, prima delle saghe: con oltre duemilasettecento
    # tappe e' il modo piu' rapido di arrivare a qualcosa, e chi non la vuole
    # scorre una riga.
    li = _voce("Cerca...\n[COLOR grey]saghe, episodi, capitoli, film, canali[/COLOR]",
               "Una casella sola per tutto il catalogo. Non guarda accenti "
               "ne' maiuscole, e le parole possono stare in qualsiasi ordine.",
               icona="DefaultAddonsSearch.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="cerca"), li, True)

    for pid in catalogo.ORDINE_PERCORSI:
        p = catalogo.PERCORSI[pid]
        totale = catalogo.lunghezza(pid)
        idx = progresso.posizione(pid)
        fatto = progresso.percentuale(pid, totale)
        quanti_visti = len(progresso.visti(pid))

        if quanti_visti == 0:
            stato = "%d episodi - mai cominciata" % totale
        else:
            stato = "%d%% vista - %d episodi su %d" % (fatto, quanti_visti, totale)

        li = _voce("%s\n[COLOR grey]%s[/COLOR]" % (p["titolo"], stato),
                   "%s\n\nSei arrivato a: %s" % (
                       p["sottotitolo"],
                       catalogo.descrizione_segmento(pid, idx)))
        prima = p["segmenti"][0][0]
        arte = {}
        if schede.poster(prima):
            arte["poster"] = arte["thumb"] = arte["icon"] = schede.poster(prima)
        if schede.sfondo(prima):
            arte["fanart"] = schede.sfondo(prima)
        if arte:
            li.setArt(arte)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="percorso", percorso=pid), li, True)

    # I raggruppamenti: una riga sola che ne contiene tanti. Stanno dopo le
    # saghe perche' le saghe sono il cuore dell'add-on, e prima degli
    # abbonamenti perche' sono roba da guardare, non da configurare.
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        g = catalogo.GRUPPI[gid]
        quante = len(g["percorsi"])
        puntate = sum(catalogo.lunghezza(p) for p in g["percorsi"])
        li = _voce("%s\n[COLOR grey]%d serie, %d puntate - %s[/COLOR]"
                   % (g["titolo"], quante, puntate, g["sottotitolo"]),
                   g["spiegazione"], icona=g.get("icona", "DefaultTVShows.png"))
        # la locandina della prima serie fa da copertina al gruppo
        if g["percorsi"]:
            prima = catalogo.PERCORSI[g["percorsi"][0]]["segmenti"][0][0]
            arte = {}
            if schede.poster(prima):
                arte["poster"] = arte["thumb"] = arte["icon"] = schede.poster(prima)
            if schede.sfondo(prima):
                arte["fanart"] = schede.sfondo(prima)
            if arte:
                li.setArt(arte)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="gruppo", gruppo=gid), li, True)

    cop, tot, perc = abbonamenti.copertura()
    li = _voce("I miei abbonamenti\n[COLOR grey]con quello che hai vedi il "
               "%d%% di tutto[/COLOR]" % perc,
               "Cosa ti sblocca ogni abbonamento, in episodi veri.",
               icona="DefaultAddonService.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="abbonamenti"), li, True)

    avviso = ""
    if taratura.serve_rimisurare():
        avviso = "  [COLOR orange]da rimisurare[/COLOR]"
    u = taratura.ultima()
    quanto = ("%.1f Mbps" % u["mbps"]) if u.get("mbps") else "mai misurata"
    li = _voce("La mia linea\n[COLOR grey]%s%s[/COLOR]" % (quanto, avviso),
               "L'add-on misura la linea e regola da solo quanto fiato "
               "tenere di scorta prima di far partire un video.",
               icona="DefaultAddonService.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="linea"), li, True)

    li = _voce("Russo con i cartoni\n[COLOR grey]%d canali per bambini, in ordine di difficolta'[/COLOR]"
               % len(russo_lib.CANALI),
               "I cartoni per bambini piccoli sono la cosa piu' vicina a un "
               "corso di lingua che ci sia in TV: parlano lentamente, "
               "ripetono, e le immagini spiegano le parole.",
               icona="DefaultAddonLanguage.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="russo"), li, True)

    an = progresso.anomalie()
    if an:
        li = _voce("[COLOR red]Attenzione: %d episodi sbagliati[/COLOR]" % len(an),
                   "È partito un episodio diverso da quello scelto.",
                   icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="anomalie"), li, False)

    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_gruppo(gid):
    """Le serie di un raggruppamento. Ognuna e' un percorso a se'."""
    g = catalogo.GRUPPI.get(gid)
    if not g:
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        return
    xbmcplugin.setPluginCategory(MANIGLIA, g["titolo"])
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    for pid in g["percorsi"]:
        p = catalogo.PERCORSI[pid]
        totale = catalogo.lunghezza(pid)
        quanti_visti = len(progresso.visti(pid))
        prima = p["segmenti"][0][0]
        serie = catalogo.SERIE[prima]

        # il numero di puntate sta gia' nel sottotitolo: qui si dice solo
        # a che punto sei, altrimenti si legge "141 puntate - 141 puntate"
        if quanti_visti == 0:
            stato = "mai cominciata"
        else:
            stato = "%d%% vista - %d su %d" % (
                progresso.percentuale(pid, totale), quanti_visti, totale)
        # Se non e' doppiata va detto QUI, nell'elenco, non dentro:
        # la regola di casa e' italiano prima di tutto.
        if not serie.get("audio_ita"):
            stato += "  [COLOR orange]sottotitolata[/COLOR]"

        li = _voce("%s\n[COLOR grey]%s - %s[/COLOR]"
                   % (p["titolo"], p["sottotitolo"], stato),
                   p.get("spiegazione", ""))
        arte = {}
        if schede.poster(prima):
            arte["poster"] = arte["thumb"] = arte["icon"] = schede.poster(prima)
        if schede.sfondo(prima):
            arte["fanart"] = schede.sfondo(prima)
        if arte:
            li.setArt(arte)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="percorso", percorso=pid), li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def apri_vetrina():
    """Apre la schermata a righe orizzontali e va dove dice l'utente.

    Se la vetrina non si apre (disegno mancante, versione di Kodi diversa)
    non succede niente di grave: si resta nel menu normale. Vale la pena
    ricordarlo, perche' una schermata bella che impedisce di guardare la TV
    sarebbe un peggioramento, non un miglioramento.
    """
    # NON si apre qui: da dentro una cartella la finestra finirebbe dietro
    # la rotellina di caricamento e non si vedrebbe mai. Si lancia il
    # programma a parte, che gira per conto suo.
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
    xbmc.executebuiltin("RunScript(plugin.video.saghe,vetrina)")


def menu_linea():
    """La taratura sulla linea: misura, spiega, e lascia decidere."""
    xbmcplugin.setPluginCategory(MANIGLIA, "La mia linea")

    li = _voce("Misura la linea e regola tutto\n[COLOR grey]circa mezzo minuto[/COLOR]",
               "Scarica qualche megabyte per capire quanto va la linea, poi "
               "regola da solo quanto fiato di scorta tenere prima di far "
               "partire un video. Su una SIM 4G e' la differenza fra un "
               "video che continua e uno che si pianta.",
               icona="DefaultAddonService.png")
    # CARTELLA, non voce semplice: una voce non-cartella e senza IsPlayable
    # Kodi prova a RIPRODURLA, ed e' lo stesso errore gia' corretto per gli
    # episodi. Qui la "cartella" fa il lavoro e non aggiunge niente.
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="misura"), li, True)

    li = _voce("Com'e' tarata adesso",
               taratura.racconta(), icona="DefaultAddonHelper.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="stato_linea"), li, True)
    xbmcplugin.endOfDirectory(MANIGLIA)


def misura_linea():
    """Misura davvero. Mostra l'avanzamento: mezzo minuto in silenzio
    sembrerebbe un blocco."""
    d = xbmcgui.DialogProgress()
    d.create("Le Saghe", "Misuro la linea...")
    valori = []
    for n in range(3):
        if d.iscanceled():
            d.close()
            xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
            return
        d.update(int(n * 100 / 3),
                 "Misuro la linea...  prova %d di 3\n\n"
                 "Sto scaricando qualche megabyte per vedere quanto va." % (n + 1))
        v = taratura._misura_una()
        if v > 0:
            valori.append(v)
    d.close()

    if not valori:
        xbmcgui.Dialog().ok(
            "Le Saghe",
            "Non sono riuscito a misurare: la linea non risponde.\n\n"
            "Non ho cambiato niente. Riprova piu' tardi.")
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        return

    fatto, testo = taratura.applica(round(max(valori), 2))
    xbmcgui.Dialog().ok("La mia linea" if fatto else "Non ho potuto regolare", testo)
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)


def menu_ricerca(testo=""):
    """Una casella sola per tutto il catalogo."""
    if not testo:
        testo = xbmcgui.Dialog().input(
            "Cerca fra saghe, episodi, capitoli, film e canali",
            type=xbmcgui.INPUT_ALPHANUM)
    if not testo:
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        return

    risultati = ricerca.cerca(testo)
    xbmcplugin.setPluginCategory(MANIGLIA, "Cerca: %s" % testo)
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    if not risultati:
        li = _voce("Nessun risultato per '%s'" % testo,
                   "Prova con meno parole, o con una parte del titolo: la "
                   "ricerca non guarda gli accenti ne' le maiuscole.",
                   icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="cerca"), li, False)
        xbmcplugin.endOfDirectory(MANIGLIA)
        return

    etichette = {"saga": "SAGA", "serie": "SERIE", "capitolo": "CAPITOLO",
                 "episodio": "EPISODIO", "film": "FILM", "canale": "CANALE"}
    for r in risultati:
        li = _voce("[COLOR grey]%s[/COLOR]  %s\n[COLOR grey]%s[/COLOR]"
                   % (etichette.get(r["tipo"], ""), r["titolo"], r["dettaglio"]),
                   r["dettaglio"])
        if r["serie"]:
            po = schede.poster(r["serie"])
            sf = schede.sfondo(r["serie"])
            arte = {}
            if po:
                arte["poster"] = arte["thumb"] = arte["icon"] = po
            if sf:
                arte["fanart"] = sf
            if arte:
                li.setArt(arte)

        if r["tipo"] == "canale":
            xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="russo"), li, True)
        elif r["tipo"] in ("saga", "serie", "film"):
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="percorso", percorso=r["percorso"]), li, True)
        else:
            # capitolo o episodio: si va DRITTI a quella pagina dell'elenco,
            # non all'inizio della saga. E' tutto il punto della ricerca.
            da = max(1, ((int(r["idx"]) - 1) // PAGINA) * PAGINA + 1)
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="sfoglia", percorso=r["percorso"], da=da),
                li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def diagnosi(pid):
    """Racconta cosa e' stato provato e com'e' andata.

    Nessun altro add-on lo fa, e dovrebbero farlo tutti: quando un episodio
    non parte, la domanda dell'utente non e' "quale codice ha sbagliato" ma
    "cosa hai provato, e perche' non ha funzionato". Qui c'e' la risposta,
    senza aprire nessun registro tecnico.
    """
    righe = []
    idx = progresso.posizione(pid)
    t = catalogo.tappa(pid, idx)
    if t:
        serie = catalogo.SERIE[t["serie"]]
        righe.append("[B]Dove sei: %s, episodio %d[/B]\n"
                     % (serie["titolo"], t["ep"]))
        righe.append("[B]Le strade, nell'ordine in cui verrebbero provate[/B]")
        righe.append(motore.spiega_piano(t["serie"], t["ep"]))
        righe.append("")

    reg = motore.registro()
    if reg:
        righe.append("[B]Cosa e' successo davvero, dal piu' recente[/B]")
        colori = {"riuscita": "green", "saltata": "orange", "fallita": "red"}
        for r in reg[::-1][:15]:
            col = colori.get(r["esito"], "grey")
            righe.append("%s  %s ep %s  ->  [COLOR %s]%s[/COLOR]%s"
                         % (r["quando"], r["serie"], r["ep"], col, r["esito"],
                            ("  (%s)" % r["dettaglio"]) if r.get("dettaglio") else ""))
    else:
        righe.append("[B]Nessun tentativo registrato finora.[/B]\n"
                     "Prova ad aprire un episodio e torna qui: troverai "
                     "l'elenco di cosa e' stato provato e come e' andata.")

    xbmcgui.Dialog().textviewer("Perche' non e' partito", "\n".join(righe))


def pannello_abbonamenti():
    cop, tot, perc = abbonamenti.copertura()
    xbmcplugin.setPluginCategory(MANIGLIA, "I miei abbonamenti")

    li = _voce("[B]Oggi puoi vedere %d episodi su %d  (%d%%)[/B]"
               % (cop, tot, perc),
               "Conteggio su tutte le saghe, esclusa la via veloce di Dragon "
               "Ball che e' un doppione.", icona="DefaultAddonService.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="abbonamenti"), li, False)

    for v in abbonamenti.riepilogo():
        if v["posseduta"]:
            segno = "[COLOR green]HAI[/COLOR]"
            nota = "ti da %d episodi" % v["episodi"]
        elif v["esclusivi"]:
            segno = "[COLOR orange]TI MANCA[/COLOR]"
            nota = "sbloccherebbe %d episodi che oggi non puoi vedere" % v["esclusivi"]
        else:
            segno = "[COLOR grey]non serve[/COLOR]"
            nota = "i suoi %d episodi li hai gia altrove" % v["episodi"]

        li = _voce("%s  %s\n[COLOR grey]%s - %s[/COLOR]"
                   % (segno, v["nome"], nota, v["prezzo"]),
                   "%s\n\n%s\nPrezzo: %s" % (v["nome"], nota, v["prezzo"]))
        lg = fonti.logo(v["id"])
        if lg:
            li.setArt({"icon": lg, "thumb": lg})
        xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="abbonamenti"), li, False)

    li = _voce("Cambia i miei abbonamenti...",
               "Apre le impostazioni per spuntare cosa possiedi.",
               icona="DefaultAddonProgram.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="impostazioni"), li, False)
    xbmcplugin.endOfDirectory(MANIGLIA)


# --------------------------------------------------------------------------
# Menu di un percorso
# --------------------------------------------------------------------------

def menu_percorso(pid):
    p = catalogo.PERCORSI[pid]
    totale = catalogo.lunghezza(pid)
    idx = progresso.posizione(pid)
    secondi, durata = progresso.ripresa(pid)
    mai = len(progresso.visti(pid)) == 0

    xbmcplugin.setPluginCategory(MANIGLIA, p["titolo"])

    # 1. La voce che serve nel 90% dei casi.
    dove = catalogo.descrizione_segmento(pid, idx).split(" - ")[0]
    if mai:
        testo = "Comincia dal primo episodio"
    else:
        testo = "Riprendi da: %s" % dove
        if secondi > 60:
            testo += "  (al minuto %s)" % _mmss(secondi)
    li = _voce("[B]%s[/B]" % testo,
               "Parte subito l'episodio giusto, senza cercare nulla.",
               icona="DefaultInProgressShows.png")
    metti_tappa(pid, idx, catalogo.tappa(pid, idx), li)

    # 2. Tutti gli episodi.
    li = _voce("Tutti gli episodi in ordine\n[COLOR grey]%d, dal primo "
               "all'ultimo[/COLOR]" % totale,
               "L'ordine corretto per capire la storia, anche quando salta da "
               "una serie all'altra.", icona="DefaultTVShows.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="sfoglia", percorso=pid, da=1), li, True)

    # 2-bis. I capitoli. In 659 tappe non si trova piu' niente: senza questa
    # voce, per sapere dove sono gli episodi con Jiren bisogna contare a mano.
    archi = catalogo.archi_di(pid)
    if archi:
        dove = catalogo.arco_della_tappa(pid, progresso.posizione(pid))
        li = _voce("Vai a un capitolo\n[COLOR grey]%d capitoli%s[/COLOR]"
                   % (len(archi), (" - sei in: " + dove) if dove else ""),
                   "Salta direttamente all'arco che ti interessa, senza "
                   "scorrere centinaia di episodi.", icona="DefaultTags.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="capitoli", percorso=pid), li, False)

    # 3. I film.
    fl = schede.film(pid)
    if fl:
        disp = sum(1 for m in fl
                   if any(fonti.possiede(f) for f in m.get("f", [])))
        li = _voce("I film\n[COLOR grey]%d, di cui %d guardabili adesso[/COLOR]"
                   % (len(fl), disp),
                   "Lungometraggi e special. Stanno fuori dall'ordine: "
                   "raccontano storie a se'.", icona="DefaultMovies.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="film", percorso=pid), li, True)

    # 4. I tagli italiani.
    quanti = len(catalogo.tutti_i_tagli(pid))
    if quanti:
        li = _voce("Dove la TV italiana ti ha interrotto\n[COLOR grey]%d punti"
                   "[/COLOR]" % quanti,
                   "Gli episodi esatti in cui hanno tagliato o smesso di "
                   "trasmettere.", icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="tagli", percorso=pid), li, True)

    # 5. Tutto il resto, raccolto.
    li = _voce("[COLOR grey]Altro...[/COLOR]",
               "Com'e' fatto questo ordine, riparti da un punto preciso, "
               "ricomincia da capo.", icona="DefaultAddonHelper.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="altro", percorso=pid), li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_altro(pid):
    xbmcplugin.setPluginCategory(MANIGLIA, "Altro")
    voci = [
        ("Com'e' fatto questo ordine", "spiega",
         "Perche' gli episodi sono in quest'ordine e non un altro.",
         "DefaultAddonHelper.png", False),
        ("Riparti da un episodio preciso...", "salta",
         "Scegli tu il punto da cui ricominciare.",
         "DefaultAddonsSearch.png", False),
        ("Regola s4me per guardare senza attriti", "regola_s4me",
         "Accende la scelta automatica della fonte (niente piu' 'scegli "
         "un'opzione' a ogni episodio) e il passaggio automatico al "
         "successivo.", "DefaultAddonService.png", True),
        ("Perche' non e' partito?", "diagnosi",
         "Le strade provate per l'ultimo episodio, in ordine, e come e' "
         "andata ognuna.", "DefaultAddonsSearch.png", False),
        ("Dimentica cosa ha funzionato", "scorda",
         "L'add-on impara quali fonti funzionano a casa tua. Se hai cambiato "
         "linea o abbonamenti, qui riparte da zero.",
         "DefaultAddonProgram.png", False),
        ("Ricomincia da capo", "azzera",
         "Riporta la saga al primo episodio e cancella cosa hai visto.",
         "DefaultAddonNone.png", False),
    ]
    for etichetta, azione, desc, icona, cartella in voci:
        li = _voce(etichetta, desc, icona=icona)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione=azione, percorso=pid), li, cartella)
    xbmcplugin.endOfDirectory(MANIGLIA)


def _mmss(secondi):
    m, s = divmod(int(secondi), 60)
    h, m = divmod(m, 60)
    if h:
        return "%d:%02d:%02d" % (h, m, s)
    return "%d:%02d" % (m, s)


# --------------------------------------------------------------------------
# Sfoglia la catena
# --------------------------------------------------------------------------

def sfoglia(pid, da):
    tappe = catalogo.catena(pid)
    totale = len(tappe)
    da = max(1, min(int(da), totale))
    fine = min(da + PAGINA - 1, totale)
    gia_visti = progresso.visti(pid)
    corrente = progresso.posizione(pid)

    xbmcplugin.setPluginCategory(
        MANIGLIA, "%s - %d-%d di %d" % (
            catalogo.PERCORSI[pid]["titolo"], da, fine, totale))

    if da > 1:
        li = _voce("[COLOR grey]' Indietro[/COLOR]")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="sfoglia", percorso=pid,
                          da=max(1, da - PAGINA)), li, True)

    for t in tappe[da - 1:fine]:
        serie = catalogo.SERIE[t["serie"]]
        fonte = fonti.fonte_migliore(t["serie"], t["ep"])

        segno = ""
        if t["idx"] in gia_visti:
            segno = "[COLOR green]v[/COLOR] "
        elif t["idx"] == corrente:
            segno = "[COLOR yellow]>[/COLOR] "

        tagli = catalogo.tagli_di(t["serie"], t["ep"])
        if tagli:
            segno = "[COLOR red]*[/COLOR] " + segno

        coda = ""
        if fonte is None:
            # NIENTE etichetta rossa: da quando c'e' il ripiego su s4me
            # l'episodio si vede lo stesso, quindi "non disponibile" era una
            # bugia che sporcava tutta la lista. Chi non ha una fonte fra gli
            # abbonamenti semplicemente non porta nessuna sigla.
            coda = ""
        elif fonte["id"] == "locale":
            coda = "  [COLOR green]- tuo file[/COLOR]"
        else:
            sg = fonti.sigla(fonte["id"])
            if sg:
                colore = "99FF9E4D" if catalogo.FONTI[fonte["id"]]["gratis"]                     else "997FA8D8"
                coda = "  [COLOR %s]- %s[/COLOR]" % (colore, sg)

        sch = schede.episodio(t["serie"], t["ep"])
        nome = sch["titolo"] or t["etichetta"]
        etichetta = "%s%04d. %s%s" % (segno, t["idx"], nome, coda)

        descrizione = "%s\n\n%s" % (
            catalogo.descrizione_segmento(pid, t["idx"]), serie["nota"])
        if not serie["verificato"]:
            descrizione += ("\n\n[COLOR yellow]Il numero di episodi di questa "
                            "serie non e' ancora stato confermato alla "
                            "fonte.[/COLOR]")
        if fonte:
            descrizione += "\n\nPartirà da: %s" % fonte["etichetta"]
        for tg in tagli:
            descrizione += "\n\n[COLOR red]* TAGLIO ITALIANO[/COLOR]\n%s" % tg["cosa"]

        li = _voce(etichetta, descrizione)
        arte = {}
        if sch["immagine"]:
            arte["thumb"] = sch["immagine"]
        if fonte and fonte["id"] != "locale":
            lg = fonti.logo(fonte["id"])
            if lg:
                arte["clearlogo"] = lg
                arte["icon"] = lg
        po = schede.poster(t["serie"])
        if po:
            arte["poster"] = po
        sf = schede.sfondo(t["serie"])
        if sf:
            arte["fanart"] = sf
        if arte:
            li.setArt(arte)
        tag = li.getVideoInfoTag()
        tag.setMediaType("episode")
        tag.setTvShowTitle(serie["titolo"])
        tag.setEpisode(t["ep"])
        if sch["titolo"]:
            tag.setTitle(sch["titolo"])
        if sch["trama"]:
            tag.setPlot(descrizione)
        if sch["data"]:
            tag.setFirstAired(sch["data"])
        if t["idx"] in gia_visti:
            tag.setPlaycount(1)

        li.addContextMenuItems([
            ("Riparti da qui",
             "RunPlugin(%s)" % url(azione="vai", percorso=pid, idx=t["idx"])),
            ("Segna come visto",
             "RunPlugin(%s)" % url(azione="visto", percorso=pid, idx=t["idx"])),
            ("Segna come non visto",
             "RunPlugin(%s)" % url(azione="nonvisto", percorso=pid, idx=t["idx"])),
        ])

        metti_tappa(pid, t["idx"], t, li)

    if fine < totale:
        li = _voce("[COLOR grey]Avanti '[/COLOR]")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="sfoglia", percorso=pid, da=fine + 1), li, True)

    xbmcplugin.setContent(MANIGLIA, "episodes")
    xbmcplugin.endOfDirectory(MANIGLIA)


# --------------------------------------------------------------------------
# Riproduzione
# --------------------------------------------------------------------------

def dentro_kodi(t):
    """Vero se questa tappa si risolve in un video che Kodi apre da solo.

    E' la domanda che decide TUTTO il resto: un elemento dichiarato
    riproducibile deve finire in `setResolvedUrl` con un indirizzo vero.
    Se non ce l'ha, Kodi dice "errore di riproduzione" - ed e' esattamente
    cio' che e' successo il 06/09/2026 su ogni episodio: le fonti non erano
    file locali, e la fine della catena era sempre `setResolvedUrl(False)`.
    """
    fonte = fonti.fonte_migliore(t["serie"], t["ep"])
    return bool(fonte) and fonte["tipo"] == "locale"


def metti_tappa(pid, idx, t, li):
    """Mette in elenco la voce di una tappa scegliendo da sola la strada.

    Un solo posto decide se una voce e' "riproducibile" oppure "cartella", e
    tutti gli elenchi passano di qui. Quando la decisione era sparsa in
    quattro punti diversi bastava dimenticarne uno per riempire lo schermo di
    errori di riproduzione.
    """
    if dentro_kodi(t):
        # Un file tuo: lo apre Kodi, e restiamo noi a registrare il minuto.
        li.setProperty("IsPlayable", "true")
        indirizzo = url(azione="riproduci", percorso=pid, idx=idx)
        cartella = False
    else:
        # TUTTO IL RESTO PASSA DA s4me, ed e' il cuore della fusione.
        #
        # Il nostro elenco resta il nostro - con i capitoli, il segno di
        # dove sei, gli avvisi sui tagli italiani - ma il VIDEO lo trova
        # s4me, che ha 55 fonti e le aggiorna da solo. Noi non inseguiamo
        # piu' i siti che cambiano indirizzo: e' lavoro senza fine e lui lo
        # fa gia' meglio.
        #
        # E' anche cio' che ha tolto di mezzo il crollo di Kodi: qui non si
        # lancia niente da dentro una cartella, si mette semplicemente un
        # indirizzo. Kodi ci naviga sopra come su qualsiasi altra cartella.
        indirizzo = indirizzo_s4me(t)
        cartella = True
    xbmcplugin.addDirectoryItem(MANIGLIA, indirizzo, li, cartella)


def indirizzo_s4me(t):
    """L'indirizzo che chiede a s4me di trovare questo episodio."""
    from urllib.parse import quote_plus
    serie = catalogo.SERIE[t["serie"]]
    return ("plugin://plugin.video.s4me/?channel=lesaghe&action=findvideos"
            "&titolo_serie=%s&serie_id=%s&numero_ep=%d"
            % (quote_plus(serie["titolo"]), t["serie"], t["ep"]))


def apri(pid, idx):
    """Delega l'apertura al programma a parte. NON fa il lavoro qui.

    Farlo qui e' cio' che il 06/09/2026 ha fatto crollare Kodi due volte:
    dentro una richiesta di cartella Kodi tiene aperta la sua finestra di
    attesa, e s4me ne apriva una seconda. Kodi vede due finestre di attesa
    sovrapposte e si spegne di proposito ("two concurrent busydialogs").

    Qui si chiude subito la cartella e si lancia `avvio.py`, che gira per
    conto suo e puo' aprire tutte le finestre che vuole.
    """
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
    xbmc.executebuiltin("RunScript(plugin.video.saghe,apri,%s,%s)"
                        % (pid, int(idx)))


def riproduci(pid, idx):
    idx = int(idx)
    t = catalogo.tappa(pid, idx)
    if not t:
        xbmcgui.Dialog().notification("Le Saghe", "Tappa inesistente",
                                      xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(MANIGLIA, False, xbmcgui.ListItem())
        return

    serie = catalogo.SERIE[t["serie"]]
    fonte = fonti.fonte_migliore(t["serie"], t["ep"])

    # La fonte puo' essere cambiata fra il momento in cui l'elenco e' stato
    # disegnato e questo clic (un abbonamento scaduto, la cartella dei file
    # staccata). Invece di far comparire l'errore di Kodi si passa la mano
    # alla via delle cartelle, che sa spiegarsi.
    if fonte is None or fonte["tipo"] != "locale":
        xbmcplugin.setResolvedUrl(MANIGLIA, False, xbmcgui.ListItem())
        xbmc.executebuiltin("Container.Update(%s)"
                            % url(azione="apri", percorso=pid, idx=idx))
        return

    progresso.vai_a(pid, idx)

    # --- Riproduzione dentro Kodi: si registra il minuto ---
    if fonte["tipo"] == "locale":
        secondi, durata = progresso.ripresa(pid)
        li = xbmcgui.ListItem(path=fonte["percorso"])
        tag = li.getVideoInfoTag()
        tag.setTitle(t["etichetta"])
        tag.setTvShowTitle(serie["titolo"])
        tag.setEpisode(t["ep"])
        tag.setMediaType("episode")
        if secondi > 0 and durata > 0:
            li.setProperty("ResumeTime", str(secondi))
            li.setProperty("TotalTime", str(durata))
        progresso.apri_sessione(
            pid, idx, dentro_kodi=True,
            atteso="%s ep %d" % (serie["titolo"], t["ep"]),
            file_atteso=fonte["percorso"])
        xbmcplugin.setResolvedUrl(MANIGLIA, True, li)
        return

    # --- App Android: Kodi non vede il video, quindi non vede il minuto ---
    if fonte["tipo"] == "app":
        pacchetto = catalogo.FONTI[fonte["id"]]["pacchetto"]
        link = fonti.link_diretto(fonte["id"], t["serie"])
        progresso.apri_sessione(pid, idx, dentro_kodi=False,
                                atteso="%s ep %d" % (serie["titolo"], t["ep"]))
        xbmcgui.Dialog().notification(
            "Le Saghe",
            "%s - cerca l'episodio %d" % (serie["titolo"], t["ep"]),
            xbmcgui.NOTIFICATION_INFO, 7000)
        fonti.avvia_app(pacchetto, link)
        xbmcplugin.setResolvedUrl(MANIGLIA, False, xbmcgui.ListItem())
        return

    # --- Altro addon di Kodi ---
    xbmcgui.Dialog().ok(
        "Le Saghe",
        "Questa fonte ([B]%s[/B]) passa da un altro addon che non è ancora "
        "collegato.\n\nÈ il prossimo pezzo da costruire." % fonte["etichetta"])
    xbmcplugin.setResolvedUrl(MANIGLIA, False, xbmcgui.ListItem())


def _spiega_fonte_mancante(t, serie, perche=""):
    elenco = fonti.fonti_disponibili(t["serie"], t["ep"])
    if perche:
        testo = "[B]%s - episodio %d[/B]\n\n%s" % (serie["titolo"], t["ep"], perche)
    elif not elenco:
        testo = ("Per questa serie non è ancora configurata nessuna fonte.")
    else:
        nomi = ", ".join(f["etichetta"] for f in elenco)
        testo = ("[B]%s - episodio %d[/B]\n\n"
                 "Questo episodio esiste su: %s\n\n"
                 "Nessuna di queste è fra i tuoi abbonamenti. Puoi attivarne "
                 "uno, oppure indicare nelle impostazioni la cartella con i "
                 "tuoi file: la fonte locale ha sempre la precedenza e "
                 "nessuno può togliertela." % (serie["titolo"], t["ep"], nomi))
    # Invece di lasciare l'utente davanti a un muro: gli si offre di cercarlo
    # su s4me senza uscire da qui. Il titolo viene passato gia' scritto, cosi'
    # non deve ridigitarlo col telecomando.
    titolo_ricerca = ponte_s4me.titolo_per_ricerca(serie, t)
    if ponte_s4me.installato() and titolo_ricerca:
        scelta = xbmcgui.Dialog().yesno(
            "Fonte non disponibile",
            testo + "\n\n[B]Vuoi cercarlo su s4me?[/B]",
            nolabel="No, chiudi",
            yeslabel="Cerca '%s'" % titolo_ricerca,
            # Il pulsante gia' scelto deve essere quello che si vuole quasi
            # sempre. Con "No" preselezionato bastava un invio distratto per
            # chiudere tutto, e in salotto "Cerca" e' l'unica strada che c'e'.
            defaultbutton=getattr(xbmcgui, "DLG_YESNO_YES_BTN", 11))
        if scelta:
            # Prima si PROVA a farlo partire da solo: e' quello che l'utente
            # vuole davvero (non vedere la lista, vedere l'episodio).
            # Se non si riesce a decidere, apri_automatico porta comunque al
            # punto piu' profondo raggiunto, invece di lasciarlo alla ricerca.
            esito = ponte_s4me.apri_automatico(titolo_ricerca, t["ep"])
            if esito == "niente":
                ponte_s4me.cerca(titolo_ricerca)
            elif esito == "avvicinato":
                xbmcgui.Dialog().notification(
                    "Le Saghe",
                    "Non ho individuato l'episodio %d: eccoti al punto piu' vicino"
                    % t["ep"], xbmcgui.NOTIFICATION_INFO, 5000)
            return
    else:
        xbmcgui.Dialog().textviewer("Fonte non disponibile", testo)


# --------------------------------------------------------------------------
# Azioni secondarie
# --------------------------------------------------------------------------

def russo():
    """I canali russi per bambini, dal piu' facile al piu' difficile."""
    xbmcplugin.setPluginCategory(MANIGLIA, "Russo con i cartoni")

    li = _voce("Come usarli davvero\n[COLOR grey]Leggi prima questo[/COLOR]",
               russo_lib.CONSIGLIO, icona="DefaultAddonHelp.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="russo_consiglio"), li, False)

    for _liv, titolo_liv, canali in russo_lib.per_livello():
        for c in canali:
            li = _voce("%s\n[COLOR grey]%s - %s[/COLOR]" % (c["nome"], titolo_liv, c["eta"]),
                       "%s\n\n%s\n\n[B]Eta' a cui e' rivolto:[/B] %s"
                       % (c["nome"], c["perche"], c["eta"]),
                       icona="DefaultTVShows.png", riproducibile=True)
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="russo_guarda", canale=c["id"]), li, False)

    xbmcplugin.endOfDirectory(MANIGLIA)


def russo_consiglio():
    xbmcgui.Dialog().textviewer("Russo con i cartoni", russo_lib.CONSIGLIO)


def russo_guarda(cid):
    """Manda in onda il canale scelto. Sono flussi diretti: Kodi li apre."""
    c = russo_lib.canale(cid)
    if not c:
        xbmcplugin.setResolvedUrl(MANIGLIA, False, xbmcgui.ListItem())
        return
    li = xbmcgui.ListItem(path=c["url"])
    tag = li.getVideoInfoTag()
    tag.setTitle(c["nome"])
    tag.setPlot(c["perche"])
    tag.setMediaType("video")
    xbmcplugin.setResolvedUrl(MANIGLIA, True, li)


def capitoli(pid):
    """Elenco dei capitoli della saga: si sceglie e ci si sposta li'."""
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
    xbmcgui.Dialog().notification(
        "Le Saghe", "Sei all'inizio di: %s" % nome,
        xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin("Container.Refresh")


def salta(pid):
    totale = catalogo.lunghezza(pid)
    corrente = progresso.posizione(pid)
    scelta = xbmcgui.Dialog().numeric(
        0, "Tappa da cui ripartire (1-%d)" % totale, str(corrente))
    if not scelta:
        return
    try:
        n = max(1, min(int(scelta), totale))
    except ValueError:
        return
    progresso.vai_a(pid, n)
    xbmcgui.Dialog().notification(
        "Le Saghe", catalogo.descrizione_segmento(pid, n),
        xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin("Container.Refresh")


def elenco_film(pid):
    fl = schede.film(pid)
    xbmcplugin.setPluginCategory(
        MANIGLIA, "%s - i film" % catalogo.PERCORSI[pid]["titolo"])
    prima = catalogo.PERCORSI[pid]["segmenti"][0][0]
    fonte = fonti.fonte_migliore(prima, 1)
    for m in fl:
        anno = m.get("d") or "?"
        trama = m.get("p") or "Nessuna trama in italiano su TMDb."
        elenco = [f for f in m.get("f", []) if fonti.possiede(f)]
        if elenco:
            coda = "  [COLOR 997FA8D8]- %s[/COLOR]" % " / ".join(
                fonti.sigla(f) or f for f in elenco)
        elif m.get("f"):
            coda = "  [COLOR 99BBBBBB]- solo %s[/COLOR]" % " / ".join(
                fonti.sigla(f) or f for f in m["f"])
        else:
            coda = "  [COLOR red]- non in streaming[/COLOR]"
        # NON riproducibile, ed e' una cartella: apri_film apre un'app o il
        # ponte s4me, non restituisce un video a Kodi.
        li = _voce("%s  [COLOR grey](%s)[/COLOR]%s" % (m["t"], anno, coda),
                   "%s\n\n%s" % (m["t"], trama))
        if elenco:
            lg = fonti.logo(elenco[0])
            if lg:
                li.setArt({"clearlogo": lg})
        if m.get("i"):
            li.setArt({"poster": m["i"], "thumb": m["i"], "icon": m["i"]})
        tag = li.getVideoInfoTag()
        tag.setMediaType("movie")
        tag.setTitle(m["t"])
        if anno.isdigit():
            tag.setYear(int(anno))
        if m.get("p"):
            tag.setPlot(m["p"])
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="apri_film", percorso=pid, titolo=m["t"]),
            li, True)
    xbmcplugin.setContent(MANIGLIA, "movies")
    xbmcplugin.endOfDirectory(MANIGLIA)


def apri_film(pid, titolo):
    """Come `apri`, ma per un film. E' una CARTELLA, non una riproduzione.

    Anche qui prima si finiva su `setResolvedUrl(False)`, cioe' sull'errore
    di riproduzione di Kodi.
    """
    prima = catalogo.PERCORSI[pid]["segmenti"][0][0]
    fonte = fonti.fonte_migliore(prima, 1)
    if fonte and fonte["tipo"] == "app":
        xbmcgui.Dialog().notification(
            "Le Saghe", "Cerca: %s" % titolo, xbmcgui.NOTIFICATION_INFO, 8000)
        fonti.avvia_app(catalogo.FONTI[fonte["id"]]["pacchetto"])
    elif ponte_s4me.installato() and titolo:
        # Stessa cortesia degli episodi: invece di un muro, si offre di
        # cercarlo su s4me col titolo gia' scritto.
        if xbmcgui.Dialog().yesno(
                "Film",
                "[B]%s[/B]\n\nPer questo film non c'e' una fonte fra i tuoi "
                "abbonamenti.\n\n[B]Vuoi cercarlo su s4me?[/B]" % titolo,
                nolabel="No, chiudi", yeslabel="Cerca '%s'" % titolo,
                defaultbutton=getattr(xbmcgui, "DLG_YESNO_YES_BTN", 11)):
            ponte_s4me.cerca(titolo)
    else:
        xbmcgui.Dialog().ok(
            "Le Saghe",
            "Per questo film non c'è ancora una fonte configurata. %s"
            % titolo)
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)


def tagli(pid):
    """Elenco dei punti in cui l'Italia ha interrotto questa saga."""
    elenco = catalogo.tutti_i_tagli(pid)
    xbmcplugin.setPluginCategory(
        MANIGLIA, "%s - dove ti hanno interrotto" % catalogo.PERCORSI[pid]["titolo"])

    simboli = {"stop": "[COLOR red]# FERMATI QUI[/COLOR]",
               "salto": "[COLOR orange]* MAI TRASMESSO[/COLOR]",
               "nota": "[COLOR grey]- contesto[/COLOR]"}

    for idx, serie_id, tg in elenco:
        serie = catalogo.SERIE[serie_id]
        etichetta = "%s -  %s, episodio %d" % (
            simboli.get(tg["tipo"], ""), serie["titolo"], tg["ep"])

        descrizione = "%s\n\n%s\n\n[COLOR grey]Tappa %d della catena.[/COLOR]" % (
            etichetta.replace("[COLOR red]", "").replace("[COLOR orange]", "")
                     .replace("[COLOR grey]", "").replace("[/COLOR]", ""),
            tg["cosa"], idx)

        li = _voce(etichetta, descrizione)
        li.addContextMenuItems([
            ("Riparti da qui",
             "RunPlugin(%s)" % url(azione="vai", percorso=pid, idx=idx)),
        ])
        metti_tappa(pid, idx, catalogo.tappa(pid, idx), li)

    if not elenco:
        li = _voce("Nessun taglio documentato per questa saga.")
        xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, False)

    xbmcplugin.endOfDirectory(MANIGLIA)


def spiega(pid):
    p = catalogo.PERCORSI[pid]
    righe = [p["spiegazione"], "", "[B]Come è composta la catena:[/B]"]
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


def azzera(pid):
    if xbmcgui.Dialog().yesno(
            "Le Saghe",
            "Azzerare il progresso di [B]%s[/B]?\n"
            "Tornerai al primo episodio." % catalogo.PERCORSI[pid]["titolo"]):
        progresso.azzera(pid)
        xbmc.executebuiltin("Container.Refresh")


# --------------------------------------------------------------------------
# Instradamento
# --------------------------------------------------------------------------

def instrada(qs):
    p = dict(parse_qsl(qs[1:]))
    azione = p.get("azione")
    pid = p.get("percorso")

    if not azione:
        menu_principale()
    elif azione == "percorso":
        menu_percorso(pid)
    elif azione == "sfoglia":
        sfoglia(pid, p.get("da", 1))
    elif azione == "apri":
        apri(pid, p.get("idx", 1))
    elif azione == "riproduci":
        riproduci(pid, p.get("idx", 1))
    elif azione == "salta":
        salta(pid)
    elif azione == "capitoli":
        capitoli(pid)
    elif azione == "russo":
        russo()
    elif azione == "russo_consiglio":
        russo_consiglio()
    elif azione == "russo_guarda":
        russo_guarda(p.get("canale", ""))
    elif azione == "gruppo":
        menu_gruppo(p.get("gruppo", ""))
    elif azione == "vetrina":
        apri_vetrina()
    elif azione == "linea":
        menu_linea()
    elif azione == "misura":
        misura_linea()
    elif azione == "stato_linea":
        xbmcgui.Dialog().textviewer("La mia linea", taratura.racconta())
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
    elif azione == "cerca":
        menu_ricerca(p.get("testo", ""))
    elif azione == "regola_s4me":
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        xbmc.executebuiltin("RunScript(plugin.video.saghe,regola_s4me)")
    elif azione == "diagnosi":
        diagnosi(pid)
    elif azione == "scorda":
        motore.dimentica()
        xbmcgui.Dialog().notification(
            "Le Saghe", "Ricomincio a imparare da zero",
            xbmcgui.NOTIFICATION_INFO, 4000)
    elif azione == "abbonamenti":
        pannello_abbonamenti()
    elif azione == "altro":
        menu_altro(pid)
    elif azione == "film":
        elenco_film(pid)
    elif azione == "apri_film":
        apri_film(pid, p.get("titolo", ""))
    elif azione == "tagli":
        tagli(pid)
    elif azione == "spiega":
        spiega(pid)
    elif azione == "azzera":
        azzera(pid)
    elif azione == "vai":
        progresso.vai_a(pid, int(p["idx"]))
        xbmc.executebuiltin("Container.Refresh")
    elif azione == "visto":
        progresso.segna_visto(pid, int(p["idx"]), avanza=False)
        xbmc.executebuiltin("Container.Refresh")
    elif azione == "nonvisto":
        progresso.togli_visto(pid, int(p["idx"]))
        xbmc.executebuiltin("Container.Refresh")
    elif azione == "anomalie":
        an = progresso.anomalie()
        righe = []
        for a in an[::-1]:
            righe.append("%s\n   chiesto:  %s\n   partito:  %s\n"
                         % (a["quando"], a["atteso"], a["ottenuto"]))
        xbmcgui.Dialog().textviewer(
            "Episodi sbagliati", "\n".join(righe) or "Nessuna anomalia.")
    elif azione == "impostazioni":
        ADDON.openSettings()
    else:
        menu_principale()


if __name__ == "__main__":
    instrada(sys.argv[2])
