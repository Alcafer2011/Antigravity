# -*- coding: utf-8 -*-
"""Le Saghe - punto di ingresso del plugin."""

import io
import json
import os
import html
import re
import sys
import time
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib import (abbonamenti, catalogo, cinema as _cinema, fonti,
                          progresso, scoperte, ricerca, russo as russo_lib,
                          schede, taratura, vetrina)

# LE SAGHE CHE SONO CRESCIUTE
# La sentinella scrive quanti episodi hanno adesso le serie ancora in corso;
# qui si allungano le catene PRIMA di disegnare qualunque elenco, altrimenti
# gli episodi nuovi ci sarebbero ma non si vedrebbero.
try:
    from resources.lib import sentinella as _sentinella
    catalogo.applica_aggiunte(_sentinella.leggi_aggiunte())
    from resources.lib import consigli as _consigli
    catalogo.applica_serie_nuove(_consigli.serie_mie())
except Exception as _e:
    xbmc.log("[Le Saghe] crescite non applicate: %s" % _e, xbmc.LOGWARNING)

ADDON = xbmcaddon.Addon()
MANIGLIA = int(sys.argv[1])
BASE = sys.argv[0]

PAGINA = 100  # tappe per pagina quando si sfoglia


def url(**kwargs):
    return BASE + "?" + urlencode(kwargs)


def _voce(etichetta, descrizione="", cartella=True, url_voce=None,
          icona="DefaultVideo.png", riproducibile=False, sotto=""):
    # `sotto` = la seconda riga ("659 episodi - mai cominciata"). Sta in
    # label2 e NON dentro l'etichetta con un a capo: sulla tessera in stile
    # Netflix il titolo si scrive SOPRA l'immagine, e una seconda riga
    # usciva dalla tessera finendo sopra la riga sotto. In piu' la testata
    # della home vuole gia' le due cose separate (Label e Label2).
    li = xbmcgui.ListItem(label=etichetta, label2=sotto)
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

        # Titolo e dettaglio SEPARATI (label / label2), non uniti da un a
        # capo: sulla tessera in stile Netflix il titolo si scrive sopra
        # l'immagine, e la seconda riga usciva dalla tessera.
        li = xbmcgui.ListItem(label=p["titolo"],
                              label2="%s - %s" % (titolo_ep, coda))
        # "riproducibile" NON si decide qui: lo decide metti_tappa, in un
        # posto solo, guardando se la fonte e' davvero un file che Kodi apre.

        tag = li.getVideoInfoTag()
        # Il titolo e' la SAGA, corto. "Dragon Ball - Dragon Ball, episodio
        # 1..." nella testata di Arctic Zephyr veniva troncato a meta'
        # (visto sul banco il 10/09/2026); l'episodio sta gia' in label2 e
        # nella trama.
        tag.setTitle(p["titolo"])
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
        # La scritta del titolo sopra la tessera, come nelle altre righe.
        if _logo_titolo(t["serie"]):
            arte["clearlogo"] = _logo_titolo(t["serie"])
        if arte:
            li.setArt(arte)

        metti_tappa(pid, r["idx"], t, li)
        messe += 1

    return messe


# --------------------------------------------------------------------------
# Menu principale
# --------------------------------------------------------------------------

# Il nome della casa. Sta qui, in un posto solo, perche' compare in ogni
# intestazione: cambiarlo e' una riga.
NOME = "La Videoteca di Alessandro"

# La nostra icona. Serve come RIPIEGO dove non c'e' una locandina: l'utente
# ha notato che sui film non compariva (molti film vecchi su TMDb non hanno
# la copertina, e restava l'icona grigia di Kodi).
# GUASTO VERO (07/09/2026): questo percorso puntava a `icon.png` nella
# radice dell'add-on, dove NON C'E'. L'icona vera sta in `resources/`
# (lo dice addon.xml). Risultato: ogni voce senza copertina - le fonti, i
# temi, i canali - disegnava un quadrato NERO invece dell'icona, e in una
# riga di locandine sembrano buchi. Non dava nessun errore: un'immagine
# che non si trova, per Kodi, e' semplicemente niente.
ICONA = "special://home/addons/plugin.video.saghe/resources/icon.png"

# Il segnaposto per le tessere senza locandina (temi, servizi). E' un vero
# file locale: carica sempre, uguale per tutte, e non lascia la tessera
# NERA ne' fa pescare alla skin la texture del vicino (l'utente: "locandine
# nere" / "Goku ultraistinto su mezzo elenco").
SEGNAPOSTO = "special://home/addons/plugin.video.saghe/resources/segnaposto.png"

# LE BANDIERE DEI GRUPPI TV. Prima si prendeva il logo del primo canale del
# gruppo che ne avesse uno: veniva fuori "7 Gold" per l'Italia (l'utente:
# "quella italiana con un 7 non e' idonea") e NIENTE per la Russia, perche'
# nessuno dei primi canali russi ha il logo - tessera nera.
# Un gruppo di canali non ha un logo suo: la bandiera e' l'unica immagine
# che dice davvero cosa c'e' dentro, e non dipende da quale canale capita
# per primo nella lista.
BANDIERE = {
    "italy": "italia", "italia": "italia", "it": "italia",
    "russia": "russia", "russian": "russia", "ru": "russia",
}


# LE TESSERE COL NOME SCRITTO SOPRA.
# 39 voci su 409 non hanno una locandina, e non e' un difetto: "Lievitati",
# "Barbecue", "Predatori" sono ricerche a TEMA, non programmi - un poster
# loro non esiste, e prenderne uno a caso e' peggio che non averlo.
# Fin qui portavano tutte lo stesso segnaposto scuro e VUOTO, e l'utente
# vedeva "ancora tantissime locandine nere". Aveva ragione: da noi il nome
# compare solo sotto la tessera SELEZIONATA, quindi una fila di voci a tema
# era una fila di buchi.
# La risposta si e' vista guardando Netflix davvero (10/09/2026): le loro
# tessere hanno il titolo scritto SOPRA l'immagine. Quindi ora ogni voce
# senza locandina ha la sua tessera col nome disegnato sopra, generata sul
# PC da `traduttore/fai-tessere.py` e spedita con l'add-on.
_TESSERE = None
_SFONDI = None


def _leggi_risorsa(nome):
    """Un file JSON dentro l'add-on. {} se manca, con una riga di registro.

    `xbmcvfs` NON e' importato in cima a questo file: si importa qui.
    Senza, il NameError finiva in un `except` muto e le immagini restavano
    tutte scure, senza un errore da nessuna parte - il modo in cui si sono
    nascosti quasi tutti i guasti di questo add-on.
    """
    try:
        import json as _json
        import xbmcvfs as _vfs
        p = _vfs.translatePath(
            "special://home/addons/plugin.video.saghe/resources/" + nome)
        with open(p, encoding="utf-8") as f:
            d = _json.load(f) or {}
        xbmc.log("[Le Saghe] %s: %d voci" % (nome, len(d)), xbmc.LOGINFO)
        return d
    except Exception as e:
        xbmc.log("[Le Saghe] %s non letto: %s" % (nome, e), xbmc.LOGWARNING)
        return {}


def _sfondo_largo(etichetta):
    """Lo sfondo 16:9 trovato su TMDb, se c'e'. Lo cerca fai-sfondi.py."""
    global _SFONDI
    if _SFONDI is None:
        _SFONDI = _leggi_risorsa("sfondi.json")
    return _SFONDI.get(etichetta) or ""


def _tessera(etichetta):
    """La tessera 16:9 generata, se c'e'. Altrimenti il segnaposto muto."""
    global _TESSERE
    if _TESSERE is None:
        _TESSERE = _leggi_risorsa("tessere/indice.json")
    nome = _TESSERE.get(etichetta)
    if not nome:
        return SEGNAPOSTO
    return ("special://home/addons/plugin.video.saghe/resources/tessere/%s"
            % nome)


def _arte_scoperta(li, copertina, etichetta):
    """L'immagine di una voce di documentari / cucina / YouTube.

    IL TRANELLO, visto a schermo il 10/09/2026: mettendo la stessa immagine
    su `poster`, `thumb` e `icon`, la skin la prendeva dal ramo `thumb` -
    che e' pensato per le immagini ORIZZONTALI e le STIRA nella cornice
    16:9. Le locandine verticali venivano fuori larghe e schiacciate.
    Quindi:
      - locandina verticale vera -> SOLO `poster`, e la skin usa il ramo che
        ne tiene la forma (letterbox);
      - nessuna locandina -> la tessera generata, che e' gia' 16:9, va
        dichiarata come `landscape`.
    `_voce` mette `thumb` da sola: qui va tolto, se no vince lui.
    """
    # In ordine, dal meglio al peggio:
    #   1. lo SFONDO 16:9 vero, trovato su TMDb (fai-sfondi.py)
    #   2. la tessera 16:9 costruita SOPRA la locandina (fai-tessere.py):
    #      la locandina nitida al centro su una sua copia sfocata, cosi'
    #      l'immagine vera non si butta e non restano bande nere
    #   3. la tessera scura, col titolo scritto dalla skin
    # La locandina verticale resta come `poster` per le schede e gli
    # elenchi, dove la forma verticale e' quella giusta.
    largo = _sfondo_largo(etichetta) or _tessera(etichetta)
    arte = {"landscape": largo, "thumb": largo, "icon": largo}
    # `thumb` non deve restare quello messo da _voce: la skin lo preferisce
    # a `poster` e STIRAVA le locandine verticali nella cornice 16:9.
    arte["poster"] = copertina or ""
    li.setArt(arte)
    return li


# --------------------------------------------------------------------------
# LE AZIONI SU UNA TESSERA (il tasto menu del telecomando)
#
# Chiesto dall'utente il 10/09/2026 guardando Netflix: "quando clicchi su una
# locandina netflix dice aggiungi alla mia lista oppure riproduci o valuta
# con il pollice". E poi: "si potrebbe usare questo sistema per la
# riproduzione e per aggiungerle ai nostri cataloghi che poi vanno a cercare
# ovunque".
#
# E' esattamente cosi': "Aggiungi alla Videoteca" NON e' una scorciatoia a
# parte, passa dalla STESSA strada dei Consigliati (`consigli.aggiungi`), che
# crea la serie E il suo percorso. Da li' in poi la cerca il motore delle
# fonti su tutti i siti, come qualunque altra saga. Una strada sola.
# --------------------------------------------------------------------------

def _azioni(li, chiave, titolo, indirizzo="", arte=None, trama="",
            sotto="", tmdb=""):
    """Attacca il menu contestuale a una voce.

    `chiave` deve essere STABILE nel tempo: il percorso per una saga,
    "tmdb_<id>" per un titolo preso da Netflix o dai consigli. Se cambia, la
    voce in lista e il pollice si perdono.
    """
    from resources.lib import miolista
    voci = []
    if indirizzo:
        voci.append(("Riproduci",
                     "Container.Update(%s)" % indirizzo))
    if miolista.in_lista(chiave):
        voci.append(("Togli da La mia lista",
                     "RunPlugin(%s)" % url(azione="lista_togli", chiave=chiave)))
    else:
        voci.append(("Aggiungi a La mia lista",
                     "RunPlugin(%s)" % url(azione="lista_metti", chiave=chiave,
                                           titolo=titolo, dove=indirizzo)))
    p = miolista.pollice(chiave)
    voci.append((("Togli il mi piace" if p == "su" else "Mi piace"),
                 "RunPlugin(%s)" % url(azione="pollice", chiave=chiave, verso="su")))
    voci.append((("Togli il non mi piace" if p == "giu" else "Non mi piace"),
                 "RunPlugin(%s)" % url(azione="pollice", chiave=chiave, verso="giu")))
    if tmdb:
        voci.append(("Aggiungi alla Videoteca (la cerca ovunque)",
                     "RunPlugin(%s)" % url(azione="netflix_aggiungi",
                                           tmdb=tmdb, tipo="serietv")))
    li.addContextMenuItems(voci)
    return li


def _voce_netflix(v):
    """Una scheda di "Su Netflix ora", con le sue azioni."""
    from resources.lib import consigli as _c, miolista
    sid = "tmdb_%s" % v["id"]
    gia = sid in _c.serie_mie()
    p = miolista.pollice(sid)
    segno = {"su": "  [COLOR grey](mi piace)[/COLOR]",
             "giu": "  [COLOR grey](non mi piace)[/COLOR]"}.get(p, "")
    li = xbmcgui.ListItem(
        label=v["titolo"],
        label2=(("Ce l'hai gia'" if gia else
                 "%s%s  -  OK per aggiungerla alla Videoteca"
                 % (v.get("anno", ""),
                    ("  voto %s" % v["voto"]) if v.get("voto") else "")) + segno))
    arte = {"poster": v.get("poster", ""), "icon": v.get("poster", "")}
    if v.get("sfondo"):
        # lo sfondo 16:9 e' anche l'immagine della TESSERA, non solo lo
        # sfondone della testata: la tessera e' orizzontale.
        arte["fanart"] = arte["landscape"] = arte["thumb"] = v["sfondo"]
    # La scritta del titolo: dalla cache che riempie il servizio, mai la rete.
    from resources.lib import loghi
    lg = loghi.logo("movie" if v.get("tipo") == "film" else "tv", v.get("id"))
    if lg:
        arte["clearlogo"] = lg
    li.setArt(arte)
    tag = li.getVideoInfoTag()
    tag.setTitle(v["titolo"])
    if v.get("trama"):
        tag.setPlot(v["trama"])

    # Chi c'e' gia' porta alla SUA CATENA. Il percorso di una serie aggiunta
    # si chiama "mia_<id serie>" (lo crea catalogo.applica_serie_nuove): si
    # controlla che esista DAVVERO invece di fidarsi del nome. Un pulsante
    # che porta a un'azione inesistente non da' errore, riapre il menu e
    # basta - e' gia' successo con "riproduci" il 07/09.
    pid_mio = "mia_" + sid
    if gia and pid_mio in catalogo.PERCORSI:
        dove, cartella = url(azione="percorso", percorso=pid_mio), True
    elif gia:
        dove, cartella = url(azione="reparto", reparto="serietv"), True
    else:
        # CARTELLA anche questa: stesso motivo dei Consigliati.
        # netflix_aggiungi chiude con endOfDirectory(succeeded=False).
        dove, cartella = url(azione="netflix_aggiungi", tmdb=str(v["id"]),
                             tipo=v.get("tipo") or "serietv"), True
    _azioni(li, sid, v["titolo"], arte=arte, trama=v.get("trama", ""),
            tmdb="" if gia else str(v["id"]))
    xbmcplugin.addDirectoryItem(MANIGLIA, dove, li, cartella)


def _bandiera_gruppo(nome):
    """La bandiera del gruppo TV, se e' un paese che conosciamo."""
    chiave = BANDIERE.get((nome or "").strip().lower())
    if not chiave:
        return ""
    return ("special://home/addons/plugin.video.saghe/resources/bandiere/%s.png"
            % chiave)


_LOGHI_TITOLO = None


def _logo_titolo(serie_id):
    """La scritta del titolo (clearlogo) di una serie, da TMDb.

    Su skin come Arctic Zephyr il clearlogo e' il titolo disegnato sopra la
    locandina scelta, come fa Netflix: all'utente e' piaciuto appena l'ha
    visto. Lo prepara `traduttore/fai-loghi.py` in
    `resources/loghi_titolo.json` (82 serie su 93 il 10/09/2026); qui si
    legge soltanto, mai la rete.
    """
    global _LOGHI_TITOLO
    if _LOGHI_TITOLO is None:
        _LOGHI_TITOLO = _leggi_risorsa("loghi_titolo.json")
    return _LOGHI_TITOLO.get(serie_id) or ""


def _copertina(li, serie_id):
    """Mette locandina e sfondo di una serie su una voce. Silenzioso se non ci sono."""
    arte = {}
    po = schede.poster(serie_id)
    sf = schede.sfondo(serie_id)
    lg = _logo_titolo(serie_id)
    if po:
        arte["poster"] = arte["thumb"] = arte["icon"] = po
    if sf:
        arte["fanart"] = sf
    if lg:
        arte["clearlogo"] = lg
    if arte:
        li.setArt(arte)
    return li


def _copertina_percorso(li, pid):
    """Come _copertina ma per una SAGA: usa il poster proprio del percorso se
    ne ha uno, altrimenti quello della prima serie. Cosi' due saghe che
    partono dalla stessa serie non finiscono con la stessa identica locandina."""
    arte = {}
    po = schede.poster_percorso(pid)
    sf = schede.sfondo_percorso(pid)
    # Il logo del titolo di una saga e' quello della sua PRIMA serie: e' il
    # nome con cui la saga si riconosce.
    seg = (catalogo.PERCORSI.get(pid) or {}).get("segmenti") or []
    lg = _logo_titolo(seg[0][0]) if seg else ""
    if po:
        arte["poster"] = arte["thumb"] = arte["icon"] = po
    if sf:
        arte["fanart"] = sf
    if lg:
        arte["clearlogo"] = lg
    if arte:
        li.setArt(arte)
    return li


def _voce_percorso(pid):
    """La riga di una saga: titolo, a che punto sei, locandina.

    Stessa riga in tre posti diversi (reparto, raggruppamento, ricerca):
    scritta una volta sola, cosi' non si possono scostare fra loro.
    """
    p = catalogo.PERCORSI[pid]
    totale = catalogo.lunghezza(pid)
    idx = progresso.posizione(pid)
    quanti_visti = len(progresso.visti(pid))
    if quanti_visti == 0:
        stato = "%d episodi - mai cominciata" % totale
    else:
        stato = "%d%% vista - %d episodi su %d" % (
            progresso.percentuale(pid, totale), quanti_visti, totale)

    li = _voce(p["titolo"], sotto=stato,
               descrizione="%s\n\nSei arrivato a: %s"
               % (p["sottotitolo"], catalogo.descrizione_segmento(pid, idx)))
    _copertina_percorso(li, pid)
    # Le azioni del menu contestuale (tasto menu del telecomando). La chiave
    # stabile di una saga e' il suo PERCORSO: non cambia se la serie cresce
    # o se le si cambia il titolo, quindi la voce in lista e il pollice non
    # si perdono.
    _azioni(li, pid, p["titolo"],
            indirizzo=url(azione="percorso", percorso=pid))
    return li


def _voce_gruppo(gid):
    g = catalogo.GRUPPI[gid]
    puntate = sum(catalogo.lunghezza(p) for p in g["percorsi"])
    li = _voce("%s\n[COLOR grey]%d serie, %d puntate - %s[/COLOR]"
               % (g["titolo"], len(g["percorsi"]), puntate, g["sottotitolo"]),
               g["spiegazione"], icona=g.get("icona", "DefaultTVShows.png"))
    if g["percorsi"]:
        _copertina_percorso(li, g["percorsi"][0])
    return li


def _gruppi_del_reparto(reparto):
    """I raggruppamenti che appartengono a un reparto.

    Un raggruppamento senza `reparto` scritto e' roba da guardare, quindi
    finisce fra i cartoni: e' dove stavano tutti prima che i reparti
    esistessero, e cosi' aggiungerne uno nuovo non lo fa sparire.
    """
    fuori = []
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        if catalogo.GRUPPI[gid].get("reparto", "cartoni") == reparto:
            fuori.append(gid)
    return fuori


def _saghe_con_film():
    """Le saghe che hanno davvero un elenco di film, con quanti ne hanno."""
    fuori = []
    for pid in catalogo.PERCORSI:
        try:
            quanti = len(schede.film(pid) or [])
        except Exception:
            quanti = 0
        if quanti:
            fuori.append((pid, quanti))
    fuori.sort(key=lambda x: (-x[1], catalogo.PERCORSI[x[0]]["titolo"]))
    return fuori


def menu_principale():
    """La porta di casa: pochi reparti, non duemila righe.

    PERCHE' E' CAMBIATO (07/09/2026, chiesto dall'utente): prima qui dentro
    c'era tutto insieme - saghe, raggruppamenti, abbonamenti, strumenti - e
    i film stavano nascosti dentro "Altro..." di ogni singola saga. Con 62
    percorsi e 96 serie non era piu' un menu, era un elenco. Adesso la porta
    ha sei voci e ogni cosa sta nel suo reparto.
    """
    xbmcplugin.setPluginCategory(MANIGLIA, NOME)
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

    li = _voce("Cerca...\n[COLOR grey]saghe, episodi, capitoli, film, canali[/COLOR]",
               "Una casella sola per tutto il catalogo. Non guarda accenti "
               "ne' maiuscole, e le parole possono stare in qualsiasi ordine.",
               icona="DefaultAddonsSearch.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="cerca"), li, True)

    # --- i reparti ---
    quante = len(catalogo.ORDINE_PERCORSI) + sum(
        len(catalogo.GRUPPI[g]["percorsi"]) for g in _gruppi_del_reparto("cartoni"))
    li = _voce("Cartoni animati - le saghe\n[COLOR grey]%d saghe, in ordine "
               "di episodio[/COLOR]" % quante,
               "Le catene: gli episodi uno dietro l'altro nell'ordine in cui "
               "vanno guardati, anche quando la storia passa da una serie "
               "all'altra. Dagli anni Ottanta a oggi.",
               icona="DefaultTVShows.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="reparto", reparto="cartoni"), li, True)

    conta_film = _saghe_con_film()
    li = _voce("I film delle saghe\n[COLOR grey]%d film, divisi per saga[/COLOR]"
               % sum(n for _, n in conta_film),
               "I film stanno QUI, non mischiati agli episodi: sono una cosa "
               "diversa e si guardano in un altro momento. Divisi per saga, "
               "in ordine di uscita, con scritto dove si trovano.",
               icona="DefaultMovies.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="film_tutti"), li, True)

    # AL CINEMA ORA.
    # L'elenco lo prepara `cinema.py` chiedendolo a TMDB (le sale ITALIANE);
    # la fonte da cui guardarli la cerca il nostro canale dentro s4me, che e'
    # l'unico posto da cui si possono chiamare i siti dei film.
    # La voce si mostra solo se il cartellone e' stato scaricato: meglio
    # nessuna voce che una voce che si apre su un elenco vuoto.
    try:
        quanti_cinema = len(_cinema.leggi())
    except Exception:
        quanti_cinema = 0
    if quanti_cinema:
        li = _voce("Al cinema ora\n[COLOR grey]%d film nelle sale italiane"
                   "[/COLOR]" % quanti_cinema,
                   "I film in programmazione al cinema in questo momento. "
                   "Aprendone uno lo cerco sui siti dei film; se e' troppo "
                   "fresco perche' ci sia gia', te lo cerco su Prime Video.",
                   icona="DefaultAddonVideo.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="cinema"), li, True)

    gruppi_serie = _gruppi_del_reparto("serietv")
    if gruppi_serie:
        quante = sum(len(catalogo.GRUPPI[g]["percorsi"]) for g in gruppi_serie)
        li = _voce("Serie TV\n[COLOR grey]%d serie con attori veri[/COLOR]"
                   % quante,
                   "Le serie non animate, tenute separate dai cartoni: turche "
                   "doppiate in italiano, e quello che aggiungeremo.",
                   icona="DefaultAddonPVRClient.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="reparto", reparto="serietv"), li, True)

    li = _voce("Consigliati per te\n[COLOR grey]scelti guardando cosa "
               "guardi[/COLOR]",
               "Cosa somiglia alle saghe che segui. Ogni proposta dice "
               "anche perche' te la propone, e con un tasto la aggiungi "
               "alla Videoteca con la sua scheda.",
               icona="DefaultAddonVideo.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="consigli"), li, True)

    li = _voce("Su Netflix ora\n[COLOR grey]anime e serie TV nel catalogo "
               "Netflix Italia, per genere[/COLOR]",
               "Scegline uno e lo aggiungo alla Videoteca nella sezione "
               "giusta, con la ricerca su piu' fonti come tutto il resto.",
               icona="DefaultNetworkShares.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="netflix"), li, True)

    li = _voce("TV in diretta\n[COLOR grey]771 canali, Italia e Russia[/COLOR]",
               "La tua lista TV, qui dentro: non serve piu' uscire dalla "
               "Videoteca per guardare la diretta.",
               icona="DefaultAddonPVRClient.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="tv"), li, True)

    li = _voce("Documentari\n[COLOR grey]animali, spazio, fisica, storia, "
               "motori[/COLOR]",
               "Quello che guardavi su Sky, preso dai cataloghi gratuiti: "
               "RaiPlay, Discovery, La7, Pluto. Prima il catalogo - scegli "
               "tu cosa e quando - la diretta solo come ripiego.",
               icona="DefaultAddonPVRClient.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="scaffale", scaffale="documentari"), li, True)

    li = _voce("Cucina\n[COLOR grey]MasterChef e i programmi di cucina[/COLOR]",
               "Dai cataloghi gratuiti: Real Time, Mediaset, RaiPlay.",
               icona="DefaultAddonPVRClient.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="scaffale", scaffale="cucina"), li, True)

    li = _voce("I tuoi canali YouTube\n[COLOR grey]Elisa True Crime, Omega "
               "Click[/COLOR]",
               "I canali che segui, aperti col loro indirizzo vero.",
               icona="DefaultAddonPVRClient.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="scaffale", scaffale="youtube"), li, True)

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


REPARTI = {
    "cartoni": ("Cartoni animati - le saghe",
                "Le catene degli episodi, in ordine di visione."),
    "serietv": ("Serie TV",
                "Le serie con attori veri, separate dai cartoni."),
}


def menu_reparto(reparto):
    """Un reparto: le sue saghe sciolte piu' i suoi raggruppamenti."""
    titolo, spiega = REPARTI.get(reparto, (NOME, ""))
    xbmcplugin.setPluginCategory(MANIGLIA, titolo)
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    # Le saghe degli anni Ottanta stanno sciolte solo nel reparto cartoni:
    # sono il cuore dell'add-on e vanno viste subito, senza un'altra porta.
    if reparto == "cartoni":
        for pid in catalogo.ORDINE_PERCORSI:
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="percorso", percorso=pid),
                _voce_percorso(pid), True)

    for gid in _gruppi_del_reparto(reparto):
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="gruppo", gruppo=gid), _voce_gruppo(gid), True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_cinema():
    """La sezione "Al cinema ora": i film nelle sale italiane, uno per uno.

    Le voci sono le stesse della riga nella Vetrina - vedi _voci_cinema.
    Aprendone una si passa al nostro canale dentro s4me, che e' l'unico
    posto da cui si possono chiamare i siti dei film.
    """
    xbmcplugin.setPluginCategory(MANIGLIA, "Al cinema ora")
    _voci_cinema()
    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_film_tutti():
    """Tutti i film, divisi per saga.

    Prima stavano dentro "Altro..." di ogni saga: c'erano, ma non li trovava
    nessuno - l'utente ha detto proprio "non ho trovato i film delle mie
    saghe anime". Adesso hanno un reparto loro, in prima pagina.
    """
    xbmcplugin.setPluginCategory(MANIGLIA, "I film delle saghe")
    xbmcplugin.setContent(MANIGLIA, "movies")

    elenco = _saghe_con_film()
    if not elenco:
        li = _voce("Nessun film in catalogo",
                   "Gli elenchi dei film si costruiscono sul computer con "
                   "costruisci-film.py e arrivano dentro l'add-on.",
                   icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, False)
        xbmcplugin.endOfDirectory(MANIGLIA)
        return

    for pid, quanti in elenco:
        p = catalogo.PERCORSI[pid]
        # Quanti di questi film puoi davvero vedere oggi con i tuoi
        # abbonamenti: e' l'informazione che decide se vale la pena entrare.
        try:
            miei = sum(1 for m in schede.film(pid)
                       if any(fonti.possiede(f) for f in m.get("f", [])))
        except Exception:
            miei = 0
        coda = ("[COLOR 997FA8D8]%d li hai[/COLOR]" % miei) if miei else \
               "[COLOR grey]nessuno nei tuoi abbonamenti[/COLOR]"
        li = _voce("%s\n[COLOR grey]%d film - %s[/COLOR]"
                   % (p["titolo"], quanti, coda),
                   "I film di %s, in ordine di uscita." % p["titolo"])
        _copertina_percorso(li, pid)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="film", percorso=pid), li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


# --------------------------------------------------------------------------
# I RIQUADRI PER LA HOME
#
# La schermata iniziale in stile Netflix non e' un menu dell'add-on: e' la
# HOME DI KODI, disegnata dalla skin. Ma la skin non sa niente delle nostre
# saghe, quindi i suoi elenchi li riempie chiedendoli QUI, con un indirizzo
# plugin:// scritto dentro il disegno (`<content>`).
#
# Sono elenchi "piatti", senza intestazioni ne' voci di servizio: chi li
# legge e' una riga di locandine, non una cartella da sfogliare.
# --------------------------------------------------------------------------

def _logo_gruppo_tv(idgruppo):
    """Il logo del primo canale del gruppo che ne abbia uno."""
    try:
        r = _rpc("PVR.GetChannels", {
            "channelgroupid": int(idgruppo), "properties": ["thumbnail"],
            "limits": {"start": 0, "end": 12}})
        # _rpc torna la risposta INTERA: i canali stanno sotto "result",
        # non alla radice. (Guasto vero: la riga restava con l'icona.)
        for c in ((r.get("result") or {}).get("channels") or []):
            if c.get("thumbnail"):
                return c["thumbnail"]
    except Exception:
        pass
    return ""


def _voci_cinema():
    """Le voci dei film in sala. Le usano DUE posti: la riga della Vetrina e
    la sezione "Al cinema ora" del menu.

    Prima la sezione del menu metteva una voce sola - "Al cinema ora" - che
    portava dentro s4me: chi la apriva trovava un vicolo cieco con dentro il
    nome della sezione che aveva appena aperto. Adesso i due posti mostrano
    la stessa cosa, che e' quello che uno si aspetta.

    Si legge il file preparato dal servizio: nessuna rete, quindi la riga
    compare subito come le altre. Ogni voce punta dritta al nostro canale
    dentro s4me, che cerchera' la fonte all'apertura.
    """
    xbmcplugin.setContent(MANIGLIA, "movies")
    from urllib.parse import quote
    for f in _cinema.leggi():
        li = xbmcgui.ListItem(label=f["titolo"],
                              label2=f.get("anno", ""))
        arte = {}
        if f.get("poster"):
            arte["poster"] = arte["thumb"] = arte["icon"] = f["poster"]
        if f.get("sfondo"):
            arte["fanart"] = f["sfondo"]
        from resources.lib import loghi
        if loghi.logo("movie", f.get("tmdb")):
            arte["clearlogo"] = loghi.logo("movie", f.get("tmdb"))
        if arte:
            li.setArt(arte)
        tag = li.getVideoInfoTag()
        tag.setTitle(f["titolo"])
        if f.get("trama"):
            tag.setPlot(f["trama"])
        if f.get("anno"):
            try:
                tag.setYear(int(f["anno"]))
            except Exception:
                pass
        xbmcplugin.addDirectoryItem(
            MANIGLIA,
            "plugin://plugin.video.s4me/?channel=lesaghe"
            "&action=cinema_fonti&titolo_film=%s&titolo_originale=%s"
            % (quote(f["titolo"]), quote(f.get("originale", ""))),
            li, True)


def _pulisci_s4me(etichetta):
    """Da un'etichetta grezza di s4me a (titolo, dettaglio).

    L'altra sessione di prova (10/09/2026) ha visto le Novita' sulle tessere
    in stile Netflix con le etichette cosi' come le scrive s4me:
        "[B]Biaoren - S01 E06[/B] [AnimeUnity]"
    Tag di formattazione di Kodi, episodio e sito tutti nel titolo. Sopra
    una locandina e' illeggibile. Si separa:
        titolo    -> "Biaoren"
        dettaglio -> "S01 E06 - AnimeUnity"
    Se l'etichetta non ha questa forma si toglie solo la formattazione.
    """
    s = html.unescape(re.sub(r"\[/?(?:B|I|COLOR[^\]]*|UPPERCASE|LOWERCASE)\]", "",
                             etichetta or "")).strip()
    sito = ""
    m = re.search(r"\s*\[([^\]]+)\]\s*$", s)
    if m:
        sito = m.group(1).strip()
        s = s[:m.start()].strip()
    episodio = ""
    m = re.search(r"\s+-\s+(S\d+\s*E\d+)\s*$", s, re.I)
    if m:
        episodio = m.group(1).upper().replace("  ", " ")
        s = s[:m.start()].strip()
    return s, " - ".join(x for x in (episodio, sito) if x)


def widget(quale):
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    if quale == "continua":
        # Le stesse voci di "Continua a guardare", senza altro attorno.
        _riga_continua()

    elif quale == "saghe":
        for pid in catalogo.ORDINE_PERCORSI:
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="percorso", percorso=pid),
                _voce_percorso(pid), True)
        for gid in _gruppi_del_reparto("cartoni"):
            for pid in catalogo.GRUPPI[gid]["percorsi"]:
                xbmcplugin.addDirectoryItem(
                    MANIGLIA, url(azione="percorso", percorso=pid),
                    _voce_percorso(pid), True)

    elif quale == "film":
        xbmcplugin.setContent(MANIGLIA, "movies")
        for pid, quanti in _saghe_con_film():
            p = catalogo.PERCORSI[pid]
            li = _voce("%s" % p["titolo"], "%d film" % quanti, icona=ICONA)
            _copertina_percorso(li, pid)
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="film", percorso=pid), li, True)

    elif quale == "serietv":
        for gid in _gruppi_del_reparto("serietv"):
            for pid in catalogo.GRUPPI[gid]["percorsi"]:
                xbmcplugin.addDirectoryItem(
                    MANIGLIA, url(azione="percorso", percorso=pid),
                    _voce_percorso(pid), True)

    elif quale == "cinema":
        _voci_cinema()
    elif quale == "consigli":
        from resources.lib import consigli as _c
        mie = _c.serie_mie()
        for v in _c.leggi():
            sid = "tmdb_%s" % v["id"]
            li = xbmcgui.ListItem(label=v["titolo"],
                                  label2=v.get("motivo", ""))
            arte = {}
            if v.get("immagine"):
                arte["poster"] = arte["thumb"] = arte["icon"] = v["immagine"]
            if v.get("sfondo"):
                arte["fanart"] = v["sfondo"]
            from resources.lib import loghi
            if loghi.logo("tv", v.get("id")):
                arte["clearlogo"] = loghi.logo("tv", v.get("id"))
            if arte:
                li.setArt(arte)
            tag = li.getVideoInfoTag()
            tag.setTitle(v["titolo"])
            if v.get("trama"):
                tag.setPlot(v["trama"])
            azione = "consiglio_togli" if sid in mie else "consiglio_aggiungi"
            # CARTELLA, non voce semplice. Su skin come Arctic Zephyr la
            # riga non ha un onclick per le voci che non sono cartelle: con
            # OK la voce andava al riproduttore e dava "errore di
            # riproduzione" (trovato dalla sessione di prova il 10/09/2026).
            # aggiungi_consiglio/togli_consiglio chiudono gia' con
            # endOfDirectory(succeeded=False): fanno il lavoro e si resta li'.
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione=azione, id=str(v["id"])), li, True)

    elif quale == "tv":
        xbmcplugin.setContent(MANIGLIA, "videos")
        if not _gruppi_tv():
            # Stessa cura della lista vuota: niente schermata nera muta.
            li = _voce("Nessun canale TV",
                       "La lista dei canali non e' caricata su questo "
                       "apparecchio. Controlla che l'add-on IPTV Simple sia "
                       "acceso e abbia la lista.", icona=SEGNAPOSTO)
            li.setArt({"poster": SEGNAPOSTO, "thumb": SEGNAPOSTO,
                       "landscape": SEGNAPOSTO, "icon": SEGNAPOSTO})
            xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="tv"), li, True)
        for g in _gruppi_tv():
            nome = (g.get("label") or "").lower()
            if "tutti" in nome:
                continue          # il gruppo "tutti" e' la somma degli altri
            # La BANDIERA del paese. Il logo del primo canale col logo dava
            # "7 Gold" per l'Italia e niente per la Russia: dipendeva da
            # quale canale capitava per primo. La bandiera dice cosa c'e'
            # dentro e non cambia mai.
            img = (_bandiera_gruppo(g.get("label"))
                   or _logo_gruppo_tv(g["channelgroupid"]) or SEGNAPOSTO)
            li = _voce(g["label"], "I canali del gruppo %s." % g["label"],
                       icona=img)
            # `landscape`: la bandiera e' 16:9 come la tessera. Messa su
            # `poster` la skin la trattava da locandina verticale e la
            # centrava fra due bande.
            li.setArt({"landscape": img, "thumb": img, "icon": img})
            xbmcplugin.addDirectoryItem(
                MANIGLIA,
                url(azione="tv_gruppo", gruppo=str(g["channelgroupid"])),
                li, True)

    elif quale.split(":")[0] in ("documentari", "cucina", "youtube"):
        # UNA RIGA PER GRUPPO (scelta dell'utente, 10/09/2026 sera).
        # Prima era UNA striscia sola: 143 tessere per i documentari, con
        # dentro delle tessere-titolo scure a fare da separatore. Due difetti
        # veri, tutti e due detti dall'utente:
        #   - "la voce quella con fast and loud non esiste" - esisteva, ma
        #     stava verso la centesima tessera: irraggiungibile.
        #   - "appare un'icona nera chiamata a catalogo" - le tessere-titolo,
        #     in una riga di locandine, sembrano buchi.
        # Adesso `che` puo' portare l'indice del gruppo ("documentari:6") e
        # il titolo del gruppo diventa il TITOLO DELLA RIGA, che e' il posto
        # dove un titolo si legge davvero. Senza indice si comporta come
        # prima (tutto insieme): serve al menu dentro l'add-on.
        xbmcplugin.setContent(MANIGLIA, "videos")
        from resources.lib import copertine
        copertine_note = copertine.leggi()
        pezzi = quale.split(":")
        gruppi = scoperte.scaffale(pezzi[0])
        if len(pezzi) > 1:
            try:
                i = int(pezzi[1])
                gruppi = [gruppi[i]] if 0 <= i < len(gruppi) else []
            except ValueError:
                gruppi = []
        for intestazione, voci in gruppi:
            for etichetta, indirizzo, nota, tipo in voci:
                if tipo.startswith("cerca:"):
                    indirizzo = url(azione="scaffale_cerca",
                                    cosa=tipo.split(":", 1)[1])
                elif tipo.startswith("diretta:"):
                    indirizzo = url(azione="diretta",
                                    canale=tipo.split(":", 1)[1])
                # Locandina vera se c'e'; altrimenti il SEGNAPOSTO (un file
                # locale, sempre uguale): non l'icona dell'addon come poster
                # (la skin la riusava -> "Goku ultraistinto su mezzo
                # elenco") e non vuoto (tessera NERA).
                li = _voce(etichetta, nota, icona=ICONA)
                _arte_scoperta(li, copertine_note.get(etichetta), etichetta)
                xbmcplugin.addDirectoryItem(MANIGLIA, indirizzo, li, True)

    elif quale.split(":")[0] == "netflix":
        # SU NETFLIX ORA, in TRE righe: Serie TV, Film, Anime.
        # Sono le stesse tre di Netflix, guardate sul loro sito: nel menu in
        # alto "Serie" e "Film" sono voci di primo livello, e fra i generi
        # dei film "Anime" c'e' come voce propria. L'utente, vedendo la riga
        # unica: "sono due categorie diverse". Aveva ragione.
        # Legge la SOLA cache: la riempie il servizio. Una riga della home
        # non va mai in rete.
        from resources.lib import netflix as _nf
        pezzi = quale.split(":")
        sezione = pezzi[1] if len(pezzi) > 1 else "serietv"
        for v in _nf.riga(sezione):
            _voce_netflix(v)

    elif quale == "lista":
        # LA MIA LISTA. Netflix ce l'ha nel menu in alto; qui e' una riga,
        # perche' la home e' fatta di righe. Le voci ci finiscono dal menu
        # contestuale di qualunque tessera.
        from resources.lib import miolista
        if not miolista.elenco():
            # Una riga vuota apriva una schermata tutta NERA senza una parola
            # (visto sul banco il 10/09/2026). Meglio una tessera che dice
            # come si riempie. Cartella, per lo stesso motivo dei Consigliati.
            li = _voce("La tua lista e' vuota",
                       "Su qualunque locandina premi il tasto MENU del "
                       "telecomando e scegli 'Aggiungi a La mia lista'.",
                       icona=SEGNAPOSTO)
            li.setArt({"poster": SEGNAPOSTO, "thumb": SEGNAPOSTO,
                       "landscape": SEGNAPOSTO, "icon": SEGNAPOSTO})
            xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, True)
        for v in miolista.elenco():
            li = xbmcgui.ListItem(label=v.get("titolo", ""),
                                  label2=v.get("sotto", ""))
            if v.get("arte"):
                li.setArt(v["arte"])
            tag = li.getVideoInfoTag()
            tag.setTitle(v.get("titolo", ""))
            if v.get("trama"):
                tag.setPlot(v["trama"])
            _azioni(li, v.get("chiave", ""), v.get("titolo", ""))
            xbmcplugin.addDirectoryItem(
                MANIGLIA, v.get("indirizzo") or url(), li, True)

    elif quale == "novita":
        # Le novita' di s4me, dalla cache: mai la rete, mai una rotellina.
        from resources.lib import novita as _n
        for v in _n.leggi():
            titolo, sotto = _pulisci_s4me(v.get("titolo", ""))
            li = xbmcgui.ListItem(label=titolo,
                                  label2=" - ".join(x for x in (sotto, v.get("sotto", "")) if x))
            arte = {"poster": v.get("immagine", ""),
                    "thumb": v.get("immagine", ""),
                    "icon": v.get("immagine", "")}
            if v.get("sfondo"):
                arte["fanart"] = v["sfondo"]
            li.setArt(arte)
            tag = li.getVideoInfoTag()
            tag.setTitle(titolo)
            if v.get("trama"):
                tag.setPlot(html.unescape(v["trama"]))
            xbmcplugin.addDirectoryItem(MANIGLIA, v.get("indirizzo", ""),
                                        li, True)

    # Niente cache: un riquadro che mostra ieri e' peggio di uno vuoto.
    xbmcplugin.endOfDirectory(MANIGLIA, cacheToDisc=False)


SCAFFALI = {
    "documentari": ("Documentari",
                    "Animali, spazio, fisica, storia, motori. Prima i "
                    "cataloghi - scegli tu cosa e quando - e la diretta "
                    "solo come ripiego."),
    "youtube": ("I tuoi canali YouTube",
                "Elisa True Crime, Omega Click e le ricerche sui temi che "
                "ti piacciono."),
    "cucina": ("Cucina",
               "MasterChef e tutti i programmi di cucina, dai cataloghi "
               "gratuiti."),
}


def menu_scaffale(quale):
    """Documentari, cucina o YouTube: a gruppi, con l'intestazione sopra.

    L'utente: "tutte separate anche dentro la sezione, per avere tutto
    ordinato". Quindi ogni gruppo ha la sua riga di titolo e le voci non si
    mescolano mai fra loro.
    """
    from resources.lib import copertine
    copertine_note = copertine.leggi()
    titolo, spiega = SCAFFALI.get(quale, ("Scoperte", ""))
    xbmcplugin.setPluginCategory(MANIGLIA, titolo)
    xbmcplugin.setContent(MANIGLIA, "videos")

    for intestazione, voci in scoperte.scaffale(quale):
        if intestazione:
            li = _voce("[COLOR grey]%s[/COLOR]" % intestazione, spiega,
                       icona=ICONA)
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="scaffale", scaffale=quale), li, False)

        for etichetta, indirizzo, nota, tipo in voci:
            if tipo.startswith("cerca:"):
                cosa = tipo.split(":", 1)[1]
                indirizzo = url(azione="scaffale_cerca", cosa=cosa)
                nota = nota or ("Apre la ricerca di '%s' sui cataloghi "
                                "gratuiti e su YouTube." % cosa)
            elif tipo.startswith("diretta:"):
                indirizzo = url(azione="diretta",
                                canale=tipo.split(":", 1)[1])
            li = _voce(etichetta, nota, icona=ICONA)
            _arte_scoperta(li, copertine_note.get(etichetta), etichetta)
            xbmcplugin.addDirectoryItem(MANIGLIA, indirizzo, li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_scaffale_cerca(cosa):
    """La stessa ricerca su tutti i cataloghi: si sceglie chi ha risposto."""
    xbmcplugin.setPluginCategory(MANIGLIA, "Cerca: %s" % cosa)
    xbmcplugin.setContent(MANIGLIA, "videos")
    li = _voce("[COLOR grey]Scegli dove cercare '%s'[/COLOR]" % cosa,
               "Ogni catalogo risponde per conto suo: se il primo non ha "
               "niente, prova il secondo. Non c'e' un posto solo che le "
               "abbia tutte.", icona=ICONA)
    xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, False)
    for nome, indirizzo in scoperte.dove_cercare(cosa):
        li = _voce("Cerca su %s" % nome, "Apre %s con '%s' gia' scritto."
                   % (nome, cosa), icona=ICONA)
        xbmcplugin.addDirectoryItem(MANIGLIA, indirizzo, li, True)
    # E su YouTube, che ce l'ha quasi sempre.
    li = _voce("Cerca su YouTube",
               "Quasi tutto quello che non sta nei cataloghi sta qui.",
               icona=ICONA)
    xbmcplugin.addDirectoryItem(
        MANIGLIA, scoperte.YT_CERCA % cosa.replace(" ", "+"), li, True)
    xbmcplugin.endOfDirectory(MANIGLIA)


def apri_diretta(nome_canale):
    """Fa partire un canale della lista TV, cercandolo per nome."""
    import json
    richiesta = json.dumps({"jsonrpc": "2.0", "id": 1,
                            "method": "PVR.GetChannels",
                            "params": {"channelgroupid": "alltv"}})
    try:
        d = json.loads(xbmc.executeJSONRPC(richiesta))
        canali = (d.get("result") or {}).get("channels") or []
    except Exception:
        canali = []
    for c in canali:
        if nome_canale.lower() in (c.get("label") or "").lower():
            xbmc.Player().play("pvr://channels/tv/%s" % c["channelid"])
            xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
            return
    xbmcgui.Dialog().ok(
        "Non l'ho trovato",
        "Nella tua lista TV non c'e' un canale che si chiami "
        "'%s'.\n\nLe liste cambiano spesso: guarda in TV > Canali."
        % nome_canale)
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)


# --------------------------------------------------------------------------
# LA TV IN DIRETTA, dentro la Videoteca
#
# PERCHE' QUI (chiesto il 07/09/2026): "se il riproduttore iptv funziona
# anche dentro s4me sposta la lista dentro li' in una sezione dedicata,
# cosi' entro sempre solo in s4me". La TV era in un altro angolo di Kodi:
# adesso e' una sezione della Videoteca come le altre.
#
# COME SI APRE UN CANALE, e perche' non con un indirizzo
#     Un indirizzo pvr:// va scritto con l'identificativo interno del
#     canale e quello del client, e cambia se si tocca una lista: e' fragile.
#     Qui invece si chiede a Kodi di aprire il CANALE per numero
#     (`Player.Open` con `channelid`), che e' l'unica cosa che non cambia.
# --------------------------------------------------------------------------

def _rpc(metodo, parametri):
    import json
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": metodo,
             "params": parametri})))
    except Exception as e:
        xbmc.log("[Le Saghe] TV: %s" % e, xbmc.LOGWARNING)
        return {}


def _gruppi_tv():
    d = _rpc("PVR.GetChannelGroups", {"channeltype": "tv"})
    return (d.get("result") or {}).get("channelgroups") or []


def _canali_tv(gruppo):
    d = _rpc("PVR.GetChannels",
             {"channelgroupid": gruppo,
              "properties": ["thumbnail", "channelnumber"]})
    return (d.get("result") or {}).get("channels") or []


def menu_tv():
    """I gruppi di canali: Italia, Russia, e quelli che ci sono."""
    xbmcplugin.setPluginCategory(MANIGLIA, "TV in diretta")
    xbmcplugin.setContent(MANIGLIA, "videos")

    gruppi = _gruppi_tv()
    if not gruppi:
        li = _voce("Nessun canale TV",
                   "La lista dei canali non e' caricata. Controlla che "
                   "l'add-on IPTV Simple sia acceso.", icona=ICONA)
        # cartella: una voce semplice non riproducibile andrebbe al lettore
        xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, True)
        xbmcplugin.endOfDirectory(MANIGLIA)
        return

    # Prima Italia e Russia: sono le uniche due liste rimaste, e sono
    # quelle che si guardano.
    def peso(g):
        n = (g.get("label") or "").lower()
        if "ital" in n:
            return 0
        if "russ" in n:
            return 1
        if "tutti" in n:
            return 9
        return 5

    for g in sorted(gruppi, key=peso):
        quanti = len(_canali_tv(g["channelgroupid"]))
        if not quanti:
            continue
        # La stessa bandiera della riga nella home: le due strade devono
        # mostrare la STESSA cosa, se no meta' delle volte sembra un'altra
        # sezione.
        img = (_bandiera_gruppo(g.get("label"))
               or _logo_gruppo_tv(g["channelgroupid"]) or SEGNAPOSTO)
        li = _voce("%s\n[COLOR grey]%d canali[/COLOR]" % (g["label"], quanti),
                   "I canali del gruppo %s." % g["label"], icona=img)
        li.setArt({"poster": img, "thumb": img, "icon": img})
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="tv_gruppo", gruppo=str(g["channelgroupid"])),
            li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_tv_gruppo(gruppo):
    xbmcplugin.setPluginCategory(MANIGLIA, "TV in diretta")
    xbmcplugin.setContent(MANIGLIA, "videos")
    try:
        gruppo = int(gruppo)
    except (TypeError, ValueError):
        pass
    for c in _canali_tv(gruppo):
        immagine = c.get("thumbnail") or ICONA
        li = _voce(c.get("label", ""), "Canale %s." % c.get("channelnumber", ""),
                   icona=immagine)
        li.setArt({"thumb": immagine, "icon": immagine, "poster": immagine})
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="tv_apri", id=str(c["channelid"])), li, False)
    xbmcplugin.endOfDirectory(MANIGLIA)


def apri_canale_tv(identificativo):
    try:
        identificativo = int(identificativo)
    except (TypeError, ValueError):
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        return
    _rpc("Player.Open", {"item": {"channelid": identificativo}})
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)


def menu_consigli():
    """Consigliati per te: cosa somiglia a quello che guardi.

    Ogni voce dice ANCHE PERCHE' te la propone ("perche' guardi Dragon
    Ball e Naruto"): un consiglio senza motivo e' pubblicita', con il
    motivo e' un suggerimento.
    """
    from resources.lib import consigli
    xbmcplugin.setPluginCategory(MANIGLIA, "Consigliati per te")
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    voci = consigli.leggi()
    if not voci:
        li = _voce("Ancora nessun consiglio",
                   "I consigli si costruiscono guardando cosa guardi. "
                   "Vengono preparati in sottofondo: guarda qualcosa e "
                   "riprova fra un po'.", icona=ICONA)
        xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, False)
        xbmcplugin.endOfDirectory(MANIGLIA)
        return

    mie = consigli.serie_mie()
    for v in voci:
        sid = "tmdb_%s" % v["id"]
        gia = sid in mie
        stato = "[COLOR 997FA8D8]gia' aggiunta[/COLOR]" if gia else v.get("motivo", "")
        etichetta = "%s\n[COLOR grey]%s - %s[/COLOR]" % (
            v["titolo"], v.get("anno") or "anno sconosciuto", stato)
        li = _voce(etichetta,
                   "%s\n\n%s\n\nPremi OK per aggiungerla alla Videoteca."
                   % (v.get("motivo", ""), v.get("trama") or
                      "Nessuna trama in italiano."),
                   icona=ICONA)
        arte = {}
        if v.get("immagine"):
            arte["poster"] = arte["thumb"] = arte["icon"] = v["immagine"]
        if v.get("sfondo"):
            arte["fanart"] = v["sfondo"]
        if arte:
            li.setArt(arte)
        azione = "consiglio_togli" if gia else "consiglio_aggiungi"
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione=azione, id=str(v["id"])), li, False)

    xbmcplugin.endOfDirectory(MANIGLIA)


def aggiungi_consiglio(tmdb_id):
    """Aggiunge la serie proposta. Scarica anche la sua scheda."""
    # "anime": era il tipo predefinito di consigli.aggiungi.
    _in_disparte("aggiungi_titolo", tmdb_id, "anime")


# --------------------------------------------------------------------------
# SU NETFLIX ORA
# --------------------------------------------------------------------------

# LE TRE SEZIONI, le stesse della home e le stesse di Netflix: sul loro
# sito "Serie" e "Film" sono voci di primo livello e "Anime" e' un genere a
# se'. Mancavano i FILM, ed e' la prima cosa che ha notato l'utente.
_NF_SEZIONI = [
    ("serietv", "Serie TV su Netflix",
     "Serie con attori veri ora nel catalogo Netflix Italia."),
    ("film",    "Film su Netflix",
     "I film ora nel catalogo Netflix Italia, per genere."),
    ("anime",   "Anime su Netflix",
     "Serie animate giapponesi ora nel catalogo Netflix Italia."),
]


def menu_netflix(sez="", g=""):
    """Tre livelli: sezioni -> generi -> titoli su Netflix IT adesso.
    Un titolo scelto viene AGGIUNTO alla Videoteca nella sezione giusta
    (anime -> Cartoni, serietv -> Serie TV), col percorso creato e visibile.
    Poi ricerca e riproduzione sono quelle di sempre: prima i siti gratuiti,
    e se ce l'ha solo Netflix il ripiego apre l'app col titolo gia' scritto.
    """
    from resources.lib import netflix, consigli
    xbmcplugin.setContent(MANIGLIA, "tvshows")

    if not sez:
        xbmcplugin.setPluginCategory(MANIGLIA, "Su Netflix ora")
        for s, tit, spiega in _NF_SEZIONI:
            li = _voce(tit, spiega, icona="DefaultNetworkShares.png")
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="netflix", sez=s), li, True)
        xbmcplugin.endOfDirectory(MANIGLIA, cacheToDisc=False)
        return

    # I generi li decide netflix.generi(): per i FILM sono i 22 del menu
    # vero di Netflix, guardato sul sito. Se restassero qui, questa
    # lista e quella del modulo si scosterebbero col tempo.
    generi = netflix.generi(sez)
    tit_sez = dict((s, t) for s, t, _ in _NF_SEZIONI).get(sez, "Netflix")

    if not g:
        xbmcplugin.setPluginCategory(MANIGLIA, tit_sez)
        for nome, gid in generi:
            li = _voce(nome, "%s - genere: %s.\n\nApre i titoli su Netflix "
                       "Italia adesso, dal piu' visto." % (tit_sez, nome),
                       icona="DefaultGenre.png")
            xbmcplugin.addDirectoryItem(
                MANIGLIA, url(azione="netflix", sez=sez, g=gid), li, True)
        xbmcplugin.endOfDirectory(MANIGLIA, cacheToDisc=False)
        return

    xbmcplugin.setPluginCategory(MANIGLIA, tit_sez)
    mie = consigli.serie_mie()
    try:
        elenco = netflix.per_genere(sez, g)
    except Exception as e:
        xbmc.log("[Le Saghe] netflix: %s" % e, xbmc.LOGWARNING)
        elenco = []
    if not elenco:
        li = _voce("Niente da mostrare",
                   "Netflix non ha risposto, o non c'e' nulla di questo "
                   "genere in questo momento. Riprova piu' tardi.", icona=ICONA)
        xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, False)
        xbmcplugin.endOfDirectory(MANIGLIA, cacheToDisc=False)
        return

    for v in elenco:
        sid = "tmdb_%s" % v["id"]
        gia = sid in mie
        stato = ("[COLOR 997FA8D8]gia' nella tua Videoteca[/COLOR]" if gia
                 else "voto %s" % v["voto"])
        li = _voce("%s\n[COLOR grey]%s - %s[/COLOR]"
                   % (v["titolo"], v.get("anno") or "?", stato),
                   "%s\n\n%s\n\nPremi OK per aggiungerla alla Videoteca: "
                   "finira' in %s, con la ricerca su piu' fonti come tutto "
                   "il resto."
                   % (v["titolo"], v.get("trama") or "Nessuna trama.",
                      "Cartoni animati" if sez == "anime" else "Serie TV"))
        arte = {}
        if v.get("poster"):
            arte["poster"] = arte["thumb"] = arte["icon"] = v["poster"]
        if v.get("sfondo"):
            arte["fanart"] = v["sfondo"]
        if arte:
            li.setArt(arte)
        if gia:
            azio = url(azione="netflix", sez=sez, g=g)
        else:
            azio = url(azione="netflix_aggiungi", tmdb=str(v["id"]),
                       tipo=("anime" if sez == "anime" else "serietv"))
        xbmcplugin.addDirectoryItem(MANIGLIA, azio, li, False)
    xbmcplugin.endOfDirectory(MANIGLIA, cacheToDisc=False)


def _in_disparte(comando, *argomenti):
    """Chiude SUBITO la cartella e fa il lavoro fuori, in avvio.py.

    Aggiungere o togliere una serie apre finestre e va in rete: dentro una
    cartella non si fa (vedi la testa di avvio.py). E niente
    Container.Refresh da qui: sul banco, il 10/09/2026, rileggeva questa
    stessa cartella e rifaceva l'aggiunta a ogni riquadro chiuso.
    """
    xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
    pezzi = [comando] + [str(a) for a in argomenti]
    # Finiscono dentro un comando di Kodi: solo lettere, numeri e trattino
    # basso, cosi' una virgola o una parentesi nell'indirizzo non possono
    # cambiarlo. (isalnum() da solo rifiutava "aggiungi_titolo": provato.)
    if not all(p and all(c.isalnum() or c == "_" for c in p) for p in pezzi):
        xbmc.log("[Le Saghe] argomenti non validi: %r" % pezzi, xbmc.LOGWARNING)
        return
    xbmc.executebuiltin("RunScript(plugin.video.saghe,%s)" % ",".join(pezzi))


def netflix_aggiungi(tmdb_id, tipo):
    _in_disparte("aggiungi_titolo", tmdb_id, tipo)


def togli_consiglio(tmdb_id):
    _in_disparte("togli_titolo", tmdb_id)


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


RICERCHE_MAX = 12


def _file_ricerche():
    import xbmcvfs
    cartella = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(cartella):
        xbmcvfs.mkdirs(cartella)
    return os.path.join(cartella, "ricerche.json")


def ricerche_recenti():
    try:
        with io.open(_file_ricerche(), encoding="utf-8") as f:
            d = json.load(f)
        return [t for t in d if isinstance(t, str)][:RICERCHE_MAX]
    except Exception:
        return []


def ricerche_recenti_aggiungi(testo):
    """La piu' recente in cima, senza doppioni. Se non si puo' scrivere, pazienza."""
    testo = (testo or "").strip()
    if not testo:
        return
    elenco = [t for t in ricerche_recenti() if t.lower() != testo.lower()]
    elenco.insert(0, testo)
    try:
        with io.open(_file_ricerche(), "w", encoding="utf-8") as f:
            f.write(json.dumps(elenco[:RICERCHE_MAX], ensure_ascii=False))
    except Exception as e:
        xbmc.log("[Le Saghe] non ho potuto salvare la ricerca: %s" % e,
                 xbmc.LOGWARNING)


def ricerche_recenti_svuota():
    try:
        os.remove(_file_ricerche())
    except Exception:
        pass


def menu_cronologia_ricerche():
    """Le ultime ricerche, e la voce per farne una nuova.

    Sta PRIMA della tastiera apposta: sul telecomando scrivere e' lento, e
    quasi sempre si cerca di nuovo la stessa cosa.
    """
    xbmcplugin.setPluginCategory(MANIGLIA, "Cerca")
    xbmcplugin.setContent(MANIGLIA, "files")

    li = _voce("[B]Nuova ricerca...[/B]\n[COLOR grey]si apre la tastiera, "
               "vuota[/COLOR]",
               "La casella parte sempre vuota: non ti ritrovi piu' dentro la "
               "ricerca di ieri da cancellare col telecomando.",
               icona="DefaultAddonsSearch.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="cerca", nuova="1"), li, True)

    recenti = ricerche_recenti()
    for t in recenti:
        li = _voce(t, "Ripeti questa ricerca.", icona="DefaultAddonsSearch.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="cerca", testo=t), li, True)

    if recenti:
        li = _voce("[COLOR grey]Svuota le ricerche[/COLOR]",
                   "Cancella l'elenco qui sopra.", icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="ricerche_svuota"), li, False)

    xbmcplugin.endOfDirectory(MANIGLIA)


# I posti dove cercare fuori dal nostro catalogo, in ordine di utilita'.
# Sono gli stessi che usa s4me: qui pero' si aprono UNO PER UNO invece che
# tutti insieme.
FUORI = [
    ("Tutti i 55 siti di s4me", "search",
     "La ricerca globale di s4me: li interroga tutti. E' la piu' completa e "
     "la piu' lenta - su questa linea puo' volerci qualche minuto."),
    ("AnimeWorld", "animeworld", "Cartoni, doppiati e sottotitolati."),
    ("AnimeUnity", "animeunity", "Cartoni."),
    ("VVVVID", "vvvvid", "Ufficiale, gratuito e legale."),
    ("StreamingCommunity", "streamingcommunity", "Film e serie."),
    ("Eurostreaming", "eurostreaming", "Serie TV."),
    ("RaiPlay", "raiplay", "Ufficiale e gratuito."),
    ("Mediaset Infinity", "mediasetplay", "Ufficiale e gratuito."),
    ("Discovery+", "discoveryplus", "Documentari e programmi."),
    ("YouTube", None, "Quasi tutto quello che gli altri non hanno."),
]


def _cerca_anche_fuori(testo):
    """Le stesse ricerche che farebbe s4me, in coda ai nostri risultati.

    PERCHE' NON SI FONDONO I RISULTATI (chiesto: "includi direttamente le
    sue 55 cosi non si perde tempo")
        Perche' si perderebbe MOLTO piu' tempo. La ricerca globale di s4me
        interroga cinquantacinque siti uno per uno: provata il 07/09/2026,
        dopo tre minuti non aveva ancora risposto. Se i suoi risultati
        finissero dentro questa pagina, la pagina resterebbe bianca per tutto
        quel tempo - anche quando quello che cerchi ce l'avevamo gia' noi.

        Cosi' invece i nostri risultati compaiono subito, e sotto ci sono le
        stesse porte che apre s4me, una per una: quella completa (tutti e 55)
        e quelle singole per chi sa gia' dove guardare. Nessuna distinzione
        da fare, nessun errore possibile: e' tutto nella stessa pagina.
    """
    try:
        from urllib.parse import quote
    except ImportError:
        from urllib import quote
    if not testo:
        return

    li = _voce("[COLOR grey]CERCA ANCHE FUORI DAL CATALOGO[/COLOR]",
               "Qui sopra c'e' quello che abbiamo noi. Qui sotto le stesse "
               "ricerche che farebbe s4me.", icona=ICONA)
    xbmcplugin.addDirectoryItem(MANIGLIA, url(), li, False)

    q = quote(testo)
    for nome, canale, nota in FUORI:
        if canale is None:
            indirizzo = ("plugin://plugin.video.youtube/kodion/search/"
                         "query/?q=%s" % testo.replace(" ", "+"))
        elif canale == "search":
            indirizzo = ("plugin://plugin.video.s4me/?channel=search"
                         "&action=Search&search_text=%s" % q)
        else:
            indirizzo = ("plugin://plugin.video.s4me/?channel=%s"
                         "&action=search&search_text=%s" % (canale, q))
        li = _voce("Cerca '%s' su %s" % (testo, nome), nota, icona=ICONA)
        li.setArt({"poster": ICONA, "thumb": ICONA, "icon": ICONA})
        xbmcplugin.addDirectoryItem(MANIGLIA, indirizzo, li, True)


def menu_ricerca(testo="", nuova=False):
    """Una casella sola per tutto il catalogo.

    IL DIFETTO DEL 06/09/2026, raccontato dall'utente: aprendo "Cerca" la
    casella si presentava con dentro la ricerca di prima ("dragon ball gt
    heroes"), e premendo Indietro per cancellarla si usciva invece di
    cancellare. Non e' un capriccio della tastiera: sul telecomando il tasto
    Indietro CHIUDE la finestra, non toglie una lettera. Con la casella gia'
    piena non c'e' modo di svuotarla, e si resta in trappola.

    Due rimedi, insieme:
      - la casella parte SEMPRE vuota (`defaultt=""` scritto apposta);
      - "Cerca" non apre piu' la tastiera di colpo: mostra prima le ultime
        ricerche, cosi' ripetere una ricerca non richiede di scrivere, e
        c'e' una voce per svuotare l'elenco.
    """
    if not testo and not nuova:
        menu_cronologia_ricerche()
        return
    if not testo:
        testo = xbmcgui.Dialog().input(
            "Cerca fra saghe, episodi, capitoli, film e canali",
            defaultt="", type=xbmcgui.INPUT_ALPHANUM)
    if not testo:
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        return
    ricerche_recenti_aggiungi(testo)

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

    _cerca_anche_fuori(testo)
    xbmcplugin.endOfDirectory(MANIGLIA)


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
                # Il logo del SERVIZIO resta solo come icona. In `clearlogo`
                # no: su skin come Arctic Zephyr il clearlogo e' la SCRITTA
                # DEL TITOLO disegnata sopra la locandina, e ci sarebbe
                # comparso il marchio Netflix al posto del nome della serie.
                # Il servizio e' gia' scritto nella descrizione ("Partira'
                # da").
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
        indirizzo = indirizzo_s4me(t, pid)
        cartella = True
    xbmcplugin.addDirectoryItem(MANIGLIA, indirizzo, li, cartella)


def indirizzo_s4me(t, pid=""):
    """L'indirizzo che chiede a s4me di trovare questo episodio.

    GLI SPAZI SI SCRIVONO %20, NON '+'. Con quote_plus "Terra amara"
    diventava "Terra+amara", e chi lo rilegge dall'altra parte scioglie i
    %20 ma non i '+': il 07/09/2026 il risolutore cercava letteralmente
    "Terra+amara" sui siti. Con quote il titolo arriva intero.

    `pid` e `idx` (la tappa della catena) viaggiano insieme: senza, il
    servizio non sa quale saga sta partendo e non puo' fare il conto alla
    rovescia verso il prossimo episodio quando il video lo apre s4me.
    """
    from urllib.parse import quote
    serie = catalogo.SERIE[t["serie"]]
    extra = ("&percorso=%s&idx=%d" % (pid, t["idx"])) if pid else ""
    return ("plugin://plugin.video.s4me/?channel=lesaghe&action=findvideos"
            "&titolo_serie=%s&serie_id=%s&numero_ep=%d%s"
            % (quote(serie["titolo"]), t["serie"], t["ep"], extra))


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
        # GUASTO VERO (07/09/2026): qui si mandava a `azione="apri"`, che nel
        # dispatcher NON ESISTE. Un'azione sconosciuta cade nel ramo finale e
        # riapre il menu principale: si premeva "guarda" e si tornava a casa,
        # senza un errore, senza niente. Ora si passa la mano a s4me con lo
        # stesso indirizzo che usano le cartelle degli episodi - la strada
        # che funziona.
        progresso.vai_a(pid, idx)
        xbmcplugin.setResolvedUrl(MANIGLIA, False, xbmcgui.ListItem())
        # PlayMedia, non Container.Update: con l'autoplay di s4me acceso il
        # video parte da solo (serve al conto alla rovescia del prossimo
        # episodio, che deve FAR PARTIRE il video, non aprire una cartella).
        xbmc.executebuiltin("PlayMedia(%s)" % indirizzo_s4me(t, pid))
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
        # NIENTE logo del servizio in `clearlogo`: su skin come Arctic
        # Zephyr quello e' il titolo disegnato sopra la locandina, e ci
        # sarebbe comparso il marchio del servizio. Il servizio e' gia'
        # scritto nella coda dell'etichetta.
        if m.get("i"):
            li.setArt({"poster": m["i"], "thumb": m["i"], "icon": m["i"]})
        else:
            # Niente copertina su TMDb: meglio la nostra icona che il
            # quadratino grigio di Kodi. E' quello che l'utente non vedeva
            # sui film.
            li.setArt({"poster": ICONA, "thumb": ICONA, "icon": ICONA})
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
    elif azione == "widget":
        widget(p.get("che", "saghe"))
    elif azione == "consigli":
        menu_consigli()
    elif azione == "consiglio_aggiungi":
        aggiungi_consiglio(p.get("id", ""))
    elif azione == "netflix":
        menu_netflix(p.get("sez", ""), p.get("g", ""))
    elif azione == "netflix_aggiungi":
        netflix_aggiungi(p.get("tmdb", ""), p.get("tipo", "anime"))
    elif azione == "consiglio_togli":
        togli_consiglio(p.get("id", ""))
    elif azione == "tv":
        menu_tv()
    elif azione == "tv_gruppo":
        menu_tv_gruppo(p.get("gruppo", ""))
    elif azione == "tv_apri":
        apri_canale_tv(p.get("id", ""))
    elif azione == "scaffale":
        menu_scaffale(p.get("scaffale", "documentari"))
    elif azione == "scaffale_cerca":
        menu_scaffale_cerca(p.get("cosa", ""))
    elif azione == "diretta":
        apri_diretta(p.get("canale", ""))
    elif azione == "reparto":
        menu_reparto(p.get("reparto", "cartoni"))
    elif azione == "film_tutti":
        menu_film_tutti()
    elif azione == "cinema":
        menu_cinema()
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
        menu_ricerca(p.get("testo", ""), nuova=(p.get("nuova") == "1"))
    elif azione == "ricerche_svuota":
        ricerche_recenti_svuota()
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        xbmc.executebuiltin("Container.Refresh")
    elif azione == "regola_s4me":
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
        xbmc.executebuiltin("RunScript(plugin.video.saghe,regola_s4me)")
    elif azione == "regola_s4me_muto":
        # Regola s4me SENZA aprire niente: nessuna finestra, nessun
        # riepilogo, e si saltano le leve che si tirerebbero dietro una
        # procedura guidata. Serve per sistemare un apparecchio mentre lo si
        # sta usando - e per farlo da fuori, visto che RunScript non si puo'
        # lanciare dalle chiamate remote ma una cartella si'.
        # Non apre finestre, quindi qui dentro e' sicuro: vedi avvio.py.
        import avvio
        avvio._regola_s4me(muto=True)
        xbmcplugin.endOfDirectory(MANIGLIA, succeeded=False)
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

    # --- LA MIA LISTA E I POLLICI (menu contestuale della tessera) ---
    elif azione == "lista_metti":
        from resources.lib import miolista
        miolista.aggiungi(p.get("chiave", ""), p.get("titolo", ""),
                          p.get("dove", ""))
        xbmcgui.Dialog().notification("La mia lista",
                                      "Aggiunto: %s" % p.get("titolo", ""),
                                      ICONA, 2500)
        xbmc.executebuiltin("Container.Refresh")
    elif azione == "lista_togli":
        from resources.lib import miolista
        miolista.togli(p.get("chiave", ""))
        xbmcgui.Dialog().notification("La mia lista", "Tolto.", ICONA, 2000)
        xbmc.executebuiltin("Container.Refresh")
    elif azione == "pollice":
        from resources.lib import miolista
        v = miolista.metti_pollice(p.get("chiave", ""), p.get("verso", ""))
        xbmcgui.Dialog().notification(
            "Grazie",
            {"su": "Te ne proporro' di simili.",
             "giu": "Non te lo ripropongo piu'."}.get(v, "Giudizio tolto."),
            ICONA, 2500)
        xbmc.executebuiltin("Container.Refresh")

    else:
        # UN'AZIONE CHE NON ESISTE NON DEVE SPARIRE IN SILENZIO.
        # Il 07/09 "riproduci" mandava a un'azione mai scritta: si tornava al
        # menu principale, senza errore e senza una riga nel registro. Un
        # errore di battitura poteva restare li' per settimane.
        if azione:
            xbmc.log("[Le Saghe] azione sconosciuta: %r (indirizzo: %s)"
                     % (azione, sys.argv[2]), xbmc.LOGWARNING)
        menu_principale()


if __name__ == "__main__":
    instrada(sys.argv[2])
