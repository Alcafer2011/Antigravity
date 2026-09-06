# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# LE SAGHE - canale per s4me
#
# COS'E'
#     Non e' un canale come gli altri: non va a leggere nessun sito. Porta
#     dentro s4me il CATALOGO CRONOLOGICO dell'add-on "Le Saghe" - le serie
#     rimesse in fila nell'ordine in cui vanno guardate, saltando da una
#     serie all'altra nel punto giusto - e poi, per trovare il video, chiede
#     agli altri canali di s4me.
#
# PERCHE' COSI'
#     s4me sa gia' fare benissimo la parte difficile: inseguire i siti che
#     cambiano indirizzo, risolvere i video, riprodurli senza pubblicita'
#     (non le blocca: risale al file diretto, e la pagina non viene mai
#     aperta). Rifare quel lavoro sarebbe stupido.
#     Quello che s4me non ha e' l'ORDINE: ti da' l'elenco di Dragon Ball
#     Super, non ti dice che Super va guardato DENTRO Z, fra l'episodio 288
#     e il 289. Quello lo mettiamo noi.
#
# IL CATALOGO NON STA QUI
#     Si legge da `plugin.video.saghe/resources/lib/catalogo.py`, che e' un
#     file di soli dati, senza nessuna importazione. Cosi' il catalogo
#     resta UNO SOLO: si aggiorna aggiornando il nostro add-on, e questo
#     canale non va toccato.
#
# SOPRAVVIVENZA AGLI AGGIORNAMENTI
#     s4me si aggiorna spesso (quasi sempre solo per i domini dei provider).
#     Questo file viene rimesso al suo posto a ogni avvio di Kodi dal
#     "custode" dentro l'add-on Le Saghe. Se sparisce, torna da solo.
# ---------------------------------------------------------------------------

import os
import sys

from core import support
from core.item import Item
from platformcode import config, logger

# --------------------------------------------------------------------------
# Il catalogo, letto dall'add-on Le Saghe
# --------------------------------------------------------------------------

NOSTRO_ADDON = "plugin.video.saghe"


def _radice_nostra():
    try:
        import xbmcvfs
        return xbmcvfs.translatePath("special://home/addons/%s" % NOSTRO_ADDON)
    except Exception:
        return ""


_catalogo = None
_schede = {}


def catalogo():
    """Il catalogo cronologico. Caricato una volta sola per sessione."""
    global _catalogo
    if _catalogo is not None:
        return _catalogo
    radice = _radice_nostra()
    percorso = os.path.join(radice, "resources", "lib", "catalogo.py")
    if not os.path.exists(percorso):
        logger.error("Le Saghe: catalogo non trovato in %s" % percorso)
        _catalogo = {}
        return _catalogo
    spazio = {}
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            exec(compile(f.read(), percorso, "exec"), spazio)
        _catalogo = spazio
    except Exception as e:
        logger.error("Le Saghe: catalogo illeggibile: %s" % e)
        _catalogo = {}
    return _catalogo


def scheda(serie_id):
    """Locandine e titoli degli episodi di una serie."""
    if serie_id in _schede:
        return _schede[serie_id]
    import json
    percorso = os.path.join(_radice_nostra(), "resources", "schede",
                            serie_id + ".json")
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            _schede[serie_id] = json.load(f)
    except Exception:
        _schede[serie_id] = {"poster": "", "sfondo": "", "episodi": {}}
    return _schede[serie_id]


def _catena(pid):
    c = catalogo()
    try:
        return c["catena"](pid)
    except Exception as e:
        logger.error("Le Saghe: catena di %s non costruita: %s" % (pid, e))
        return []


# --------------------------------------------------------------------------
# I menu
# --------------------------------------------------------------------------

PER_PAGINA = 60          # su una TV oltre non si scorre, si soffre


def mainlist(item):
    """Le saghe, piu' i raggruppamenti (serie turche e compagnia)."""
    c = catalogo()
    if not c:
        return [Item(channel=item.channel, action="", folder=False,
                     title=support.typo(
                         "Catalogo non trovato: manca l'add-on Le Saghe",
                         "bold color kod"))]

    itemlist = []
    elenco = list(c.get("ORDINE_PERCORSI", []))
    for gid in c.get("ORDINE_GRUPPI", []):
        elenco.extend(c["GRUPPI"][gid]["percorsi"])

    for pid in elenco:
        p = c["PERCORSI"].get(pid)
        if not p:
            continue
        prima = p["segmenti"][0][0]
        sch = scheda(prima)
        itemlist.append(Item(
            channel=item.channel,
            action="episodios",
            title=support.typo(p["titolo"], "bold"),
            fulltitle=p["titolo"],
            show=p["titolo"],
            contentSerieName=p["titolo"],
            contentType="tvshow",
            percorso=pid,
            plot=p.get("spiegazione", "") or p.get("sottotitolo", ""),
            thumbnail=sch.get("poster", ""),
            fanart=sch.get("sfondo", ""),
        ))
    return itemlist


def episodios(item):
    """La catena di una saga: le tappe in ordine, a pagine."""
    c = catalogo()
    tappe = _catena(item.percorso)
    if not tappe:
        return []

    da = int(getattr(item, "da", 1) or 1)
    fine = min(da + PER_PAGINA - 1, len(tappe))
    itemlist = []

    for t in tappe[da - 1:fine]:
        serie = c["SERIE"][t["serie"]]
        sch = scheda(t["serie"])
        ep = sch.get("episodi", {}).get(str(t["ep"]), {})
        titolo_ep = ep.get("t") or ""

        etichetta = "%04d. %s" % (t["idx"], titolo_ep or t["etichetta"])
        # Se la serie non e' doppiata va detto QUI, nell'elenco: la regola
        # di casa e' italiano prima di tutto, e una brutta notizia data
        # tardi e' peggio di una brutta notizia.
        if not serie.get("audio_ita"):
            etichetta += support.typo("sottotitolata", "_ [] color kod")

        itemlist.append(Item(
            channel=item.channel,
            action="findvideos",
            title=etichetta,
            fulltitle=serie["titolo"],
            show=serie["titolo"],
            contentSerieName=serie["titolo"],
            contentType="episode",
            # QUI IL NUMERO E' LA TAPPA DELLA CATENA, non l'episodio della
            # sua serie. Sembra un dettaglio e decide una cosa grossa.
            #
            # s4me sa passare da solo all'episodio dopo, ma solo per le
            # serie messe nella sua videoteca: crea un file per episodio e
            # prende il successivo in ordine. Se qui mettessimo il numero
            # dentro la serie, Naruto 5 e Shippuden 5 sarebbero lo stesso
            # "1x5" e si pesterebbero i piedi nella videoteca.
            #
            # Con la tappa (1...1013, senza doppioni) la videoteca segue
            # esattamente il NOSTRO ordine cronologico: il "prossimo
            # episodio" automatico di s4me cammina sulla nostra catena,
            # saltando da una serie all'altra nel punto giusto.
            contentEpisodeNumber=t["idx"],
            contentSeason=1,
            titolo_serie=serie["titolo"],
            serie_id=t["serie"],
            numero_ep=t["ep"],
            audio_ita=bool(serie.get("audio_ita")),
            plot=ep.get("p", "") or serie.get("nota", ""),
            thumbnail=ep.get("i") or sch.get("poster", ""),
            fanart=sch.get("sfondo", ""),
        ))

    if fine < len(tappe):
        itemlist.append(Item(
            channel=item.channel, action="episodios",
            percorso=item.percorso, da=fine + 1,
            title=support.typo("Avanti  (%d-%d di %d)"
                               % (fine + 1, min(fine + PER_PAGINA, len(tappe)),
                                  len(tappe)), "bold color kod"),
            thumbnail=item.thumbnail, fanart=item.fanart))

    return itemlist


# --------------------------------------------------------------------------
# Trovare il video: qui si chiede aiuto agli altri canali di s4me
# --------------------------------------------------------------------------

# I canali a cui chiedere, nell'ordine. Sono quelli anime italiani piu'
# solidi: si prova il primo che risponde. Non trenta, che vuol dire trenta
# cose che si rompono.
CANALI = ["animeworld", "animeunity", "animesaturn", "aniplay", "toonitalia"]


def _rango_lingua(voce):
    """Quanto e' buona la lingua di questo risultato.

    3 = doppiato in italiano, 2 = non dichiarato, 1 = sottotitolato.
    E' la regola di casa: doppiaggio italiano prima di tutto, poi i
    sottotitoli. Viene PRIMA della somiglianza del titolo, sempre.
    """
    lingua = (getattr(voce, "contentLanguage", "") or "").lower()
    testo = ((getattr(voce, "title", "") or "") + " " +
             (getattr(voce, "fulltitle", "") or "")).lower()
    if "sub" in lingua or "sub-ita" in testo:
        return 1
    if "ita" in lingua or "[ita]" in testo:
        return 3
    return 2


def _somiglia(a, b):
    """Quanto due titoli si assomigliano, 0-100. Senza accenti ne' segni."""
    import re
    import unicodedata

    def piatto(s):
        s = unicodedata.normalize("NFKD", str(s or ""))
        s = "".join(x for x in s if not unicodedata.combining(x)).lower()
        return set(re.sub(r"[^a-z0-9]+", " ", s).split())

    pa, pb = piatto(a), piatto(b)
    if not pa or not pb:
        return 0
    return int(100.0 * len(pa & pb) / max(len(pa), len(pb)))


def _modulo(nome):
    try:
        return __import__("channels.%s" % nome, None, None, ["channels"])
    except Exception as e:
        logger.error("Le Saghe: canale %s non caricabile: %s" % (nome, e))
        return None


# --------------------------------------------------------------------------
# La rubrica: dove abbiamo gia' trovato una serie
# --------------------------------------------------------------------------
#
# PERCHE' ESISTE
#     Senza, ogni singolo episodio rifa' la ricerca da capo su animeworld:
#     misurato, DUE MINUTI a episodio sulla linea di casa. Con 54 episodi di
#     Heroes vuol dire due ore di attesa per guardare una stagione.
#     La serie pero' e' sempre la stessa: una volta trovata, l'indirizzo si
#     scrive in rubrica e dal secondo episodio in poi si va dritti.
#
# COSA SUCCEDE SE L'INDIRIZZO INVECCHIA
#     I siti cambiano dominio di continuo. Se l'indirizzo in rubrica non
#     risponde piu', si cancella la voce e si rifa' la ricerca: la rubrica
#     e' una scorciatoia, mai una prigione.

def _rubrica_file():
    try:
        import xbmcvfs
        cartella = xbmcvfs.translatePath(
            "special://profile/addon_data/%s" % NOSTRO_ADDON)
        if not os.path.isdir(cartella):
            os.makedirs(cartella)
        return os.path.join(cartella, "rubrica_fonti.json")
    except Exception:
        return ""


def _rubrica_leggi():
    import json
    f = _rubrica_file()
    try:
        with open(f, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def _rubrica_scrivi(dati):
    import json
    f = _rubrica_file()
    if not f:
        return
    try:
        with open(f, "w", encoding="utf-8") as fp:
            json.dump(dati, fp, ensure_ascii=False)
    except Exception:
        pass


def _rubrica_prendi(serie_id):
    return _rubrica_leggi().get(serie_id)


def _rubrica_segna(serie_id, canale, voce):
    dati = _rubrica_leggi()
    dati[serie_id] = {
        "canale": canale,
        "url": getattr(voce, "url", ""),
        "titolo": getattr(voce, "fulltitle", "") or getattr(voce, "title", ""),
        "lingua": getattr(voce, "contentLanguage", ""),
    }
    _rubrica_scrivi(dati)


def _rubrica_scorda(serie_id):
    dati = _rubrica_leggi()
    if serie_id in dati:
        del dati[serie_id]
        _rubrica_scrivi(dati)


def findvideos(item):
    """Cerca l'episodio sui canali di s4me e restituisce i suoi server.

    L'ordine con cui si sceglie fra i risultati NON e' la somiglianza del
    titolo: prima viene la LINGUA. Un risultato doppiato in italiano che
    somiglia un po' meno batte sempre un sottotitolato perfetto.
    """
    titolo = getattr(item, "titolo_serie", "") or item.fulltitle
    numero = int(getattr(item, "numero_ep", 0) or 0)
    if not titolo or not numero:
        return []

    serie_id = getattr(item, "serie_id", "")

    # 1) La scorciatoia: se questa serie l'abbiamo gia' trovata, si va dritti
    #    all'elenco degli episodi senza rifare la ricerca.
    nota = _rubrica_prendi(serie_id) if serie_id else None
    if nota:
        canale = _modulo(nota["canale"])
        if canale:
            try:
                voce = Item(channel=nota["canale"], action="episodios",
                            url=nota["url"], contentType="tvshow",
                            fulltitle=nota.get("titolo", titolo),
                            title=nota.get("titolo", titolo),
                            contentSerieName=titolo)
                episodi = _episodi_di(canale, voce)
                scelto = _episodio_giusto(episodi, numero)
                if scelto:
                    server = canale.findvideos(scelto) or []
                    if server:
                        for s in server:
                            s.channel = nota["canale"]
                        return server
            except Exception as e:
                logger.info("Le Saghe: la rubrica non ha funzionato: %s" % e)
        # L'indirizzo in rubrica non vale piu': si dimentica e si ricerca.
        _rubrica_scorda(serie_id)

    # 2) La ricerca vera, che e' lenta: si fa una volta per serie.
    for nome in CANALI:
        canale = _modulo(nome)
        if not canale:
            continue
        try:
            ricerca = Item(channel=nome, action="search", contentType="tvshow",
                           search="", args="")
            risultati = canale.search(ricerca, titolo) or []
        except Exception as e:
            logger.error("Le Saghe: ricerca su %s fallita: %s" % (nome, e))
            continue

        risultati = [r for r in risultati if getattr(r, "action", "")]
        if not risultati:
            continue

        risultati.sort(key=lambda r: (_rango_lingua(r),
                                      _somiglia(getattr(r, "fulltitle", "") or
                                                getattr(r, "title", ""), titolo)),
                       reverse=True)
        migliore = risultati[0]
        if _somiglia(getattr(migliore, "fulltitle", "") or
                     getattr(migliore, "title", ""), titolo) < 30:
            continue                      # su questo canale non c'e' la serie

        episodi = _episodi_di(canale, migliore)
        scelto = _episodio_giusto(episodi, numero)
        if not scelto:
            continue

        try:
            server = canale.findvideos(scelto) or []
        except Exception as e:
            logger.error("Le Saghe: findvideos su %s fallito: %s" % (nome, e))
            continue
        if server:
            for s in server:
                s.channel = nome          # senza, s4me non sa chi riproduce
            if serie_id:
                _rubrica_segna(serie_id, nome, migliore)
            return server

    # ULTIMA SPIAGGIA: gli abbonamenti.
    #
    # Se nessuno dei canali ha l'episodio, puo' esserci su Netflix o su
    # Prime. Non si tira a indovinare: il catalogo SA gia' su quale
    # servizio sta ogni serie, e si offrono solo quelli - e solo se
    # l'add-on corrispondente e' installato.
    abbonamenti = _abbonamenti(getattr(item, "serie_id", ""), titolo)
    if abbonamenti:
        return abbonamenti

    return [Item(channel=item.channel, action="", folder=False,
                 title=support.typo(
                     "Nessuna fonte trovata per l'episodio %d" % numero,
                     "bold color kod"))]


# Gli add-on degli abbonamenti, e come si chiede loro di cercare un titolo.
SERVIZI = {
    "netflix": ("Netflix", "plugin.video.netflix",
                "plugin://plugin.video.netflix/directory/search/search/%s/"),
    "prime": ("Prime Video", "plugin.video.amazon-test",
              "plugin://plugin.video.amazon-test/?mode=search&searchstring=%s"),
    "animegeneration": ("Anime Generation", "plugin.video.amazon-test",
                        "plugin://plugin.video.amazon-test/?mode=search&searchstring=%s"),
}


def _abbonamenti(serie_id, titolo):
    """Le voci per aprire gli abbonamenti su cui la serie esiste davvero."""
    import xbmcvfs
    try:
        from urllib.parse import quote_plus
    except ImportError:
        from urllib import quote_plus

    c = catalogo()
    serie = c.get("SERIE", {}).get(serie_id, {})
    fuori = []
    visti = set()
    for fid in serie.get("fonti", []):
        if fid not in SERVIZI:
            continue
        nome, addon, modello = SERVIZI[fid]
        if addon in visti:
            continue
        if not xbmcvfs.exists("special://home/addons/%s/addon.xml" % addon):
            continue                      # non installato: non si promette
        visti.add(addon)
        fuori.append(Item(
            channel="lesaghe", action="", folder=True,
            url=modello % quote_plus(titolo),
            title=support.typo(
                "Non trovato in rete - cerca su %s" % nome, "bold color kod"),
            plot="Il catalogo dice che questa serie sta su %s, che possiedi. "
                 "Si apre la ricerca gia' scritta: l'episodio va scelto a "
                 "mano, perche' quei servizi non si lasciano comandare da "
                 "fuori." % nome))
    return fuori


def _episodi_di(canale, voce):
    """Gli episodi di una serie, qualunque sia il nome della funzione."""
    for nome_funzione in ("episodios", "check"):
        f = getattr(canale, nome_funzione, None)
        if not f:
            continue
        try:
            fuori = f(voce) or []
        except Exception:
            continue
        if fuori:
            return fuori
    return []


def _episodio_giusto(episodi, numero):
    """L'episodio col numero giusto. None se non si e' sicuri.

    None NON e' un fallimento da aggirare: vuol dire che non lo sappiamo,
    e tirare a indovinare e' come si finisce a guardare l'episodio
    sbagliato. E' gia' successo.
    """
    import re
    for e in episodi:
        n = getattr(e, "contentEpisodeNumber", None)
        try:
            if n is not None and int(n) == numero:
                return e
        except (TypeError, ValueError):
            pass
    for e in episodi:
        testo = getattr(e, "title", "") or ""
        m = re.search(r"(?:^|\D)(\d{1,4})(?:\D|$)", testo)
        if m and int(m.group(1)) == numero:
            return e
    return None


def search(item, text):
    """Cerca fra le saghe del catalogo, non in rete."""
    c = catalogo()
    if not c:
        return []
    fuori = []
    for pid, p in c.get("PERCORSI", {}).items():
        if _somiglia(p["titolo"], text) >= 40:
            prima = p["segmenti"][0][0]
            sch = scheda(prima)
            fuori.append(Item(
                channel=item.channel, action="episodios",
                title=support.typo(p["titolo"], "bold"),
                fulltitle=p["titolo"], show=p["titolo"],
                contentSerieName=p["titolo"], contentType="tvshow",
                percorso=pid, thumbnail=sch.get("poster", ""),
                fanart=sch.get("sfondo", "")))
    return fuori
