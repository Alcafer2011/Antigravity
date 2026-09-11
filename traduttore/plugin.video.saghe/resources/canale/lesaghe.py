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


def _json_atomico(percorso, dati, **opzioni):
    """Scrive in un file provvisorio e lo sostituisce in un colpo: se il box si
    spegne a meta' resta il file vecchio intero, non un JSON troncato
    (vedi resources/lib/salva.py: qui dentro s4me quel modulo non si importa)."""
    import io as _io
    import json as _json
    import os as _os
    provvisorio = percorso + ".tmp"
    with _io.open(provvisorio, "w", encoding="utf-8") as f:
        f.write(_json.dumps(dati, **opzioni))
    _os.replace(provvisorio, percorso)

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
        # Le saghe cresciute: la sentinella scrive quanti episodi hanno
        # adesso le serie in corso, e senza questo pezzo gli episodi nuovi
        # esisterebbero nell'add-on ma non si aprirebbero da qui.
        try:
            import json as _json
            import xbmcvfs as _vfs
            _f = _vfs.translatePath(
                "special://profile/addon_data/plugin.video.saghe/aggiunte.json")
            if _vfs.exists(_f):
                with open(_f, "r", encoding="utf-8") as _g:
                    spazio["applica_aggiunte"](_json.load(_g))
        except Exception as _e:
            logger.info("Le Saghe: crescite non applicate: %s" % _e)
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

# I siti giusti per ogni TIPO di serie.
#
# IL GUASTO DEL 06/09/2026, notato dall'utente: "la serie turca a catalogo
# c'e', riproducibile no". Non era un sito rotto ne' un titolo sbagliato:
# cercavamo una telenovela turca con attori veri su cinque siti di CARTONI
# GIAPPONESI. Non l'avremmo trovata mai, per quanto aspettassimo.
#
# Ogni serie del catalogo dice di che tipo e' (`tipo`); qui si dice dove si
# cerca quel tipo. Chi non lo dichiara e' un cartone, che e' quello che
# erano tutte quando questo codice e' nato.
CANALI_PER_TIPO = {
    # I CARTONI. Prima i tre che rispondono piu' in fretta, poi VVVVID che e'
    # ufficiale, gratuito e italiano (quando ce l'ha, e' la fonte migliore
    # che esista), poi gli altri.
    "anime": ["animeworld", "animeunity", "animesaturn", "aniplay",
              "vvvvid", "toonitalia", "animeforce", "dreamsub",
              "cb01anime", "animeuniverse"],
    # LE SERIE CON ATTORI VERI. Prima i servizi ufficiali e GRATUITI - Rai,
    # Mediaset, La7, Pluto - perche' quando ce l'hanno partono subito e
    # senza sorprese; solo dopo i siti che raccolgono da altrove.
    # guardaserieicu e' fuori apposta: su questa installazione non si carica
    # ("canale non caricabile") e provarlo costa 70 secondi a ogni episodio.
    "serie_tv": ["raiplay", "mediasetplay", "la7", "plutotv",
                 "eurostreaming", "streamingcommunity", "serietvu",
                 "mondoserietv", "altadefinizione01"],
}


# Canali di s4me che al 10/09/2026 danno errore di CODICE (non "il sito non
# ha la serie", proprio un'eccezione Python): saltarli fa risparmiare secondi
# e non lascia mezzo errore nel registro. Se s4me li ripara, si tolgono da
# qui. NON e' un giudizio sul sito: e' che lo scraper di s4me e' rotto.
CANALI_ROTTI = {"aniplay", "cb01anime"}


def _canali_per(serie):
    """Su quali siti ha senso cercare questa serie."""
    tipo = (serie or {}).get("tipo", "anime")
    lista = CANALI_PER_TIPO.get(tipo, CANALI)
    return [c for c in lista if c not in CANALI_ROTTI] or lista


# Quando l'add-on parte in automatico prova il PRIMO server della lista: se
# e' 'voe' (che di continuo da' l'errore inglese "Unexpected error on server
# voe") o uno morto, l'utente si becca il dialogo invece del video. Qui i
# server buoni salgono in cima e quelli traballanti scendono in fondo -
# nessuno viene tolto, cambia solo l'ordine in cui si provano.
SERVER_IN_FONDO = ("voe", "streamsb", "fembed", "streamlare", "upstream",
                   "vidoza", "userload")
SERVER_IN_CIMA = ("streamtape", "dood", "doodstream", "mixdrop", "vidguard",
                  "streamwish", "filelions", "wolfstream", "luluvdo", "vtube",
                  "supervideo", "maxstream", "hdload")


def _pota_server(server):
    def rango(s):
        sid = (getattr(s, "server", "") or "").lower()
        if sid in SERVER_IN_FONDO:
            return 2
        if sid in SERVER_IN_CIMA:
            return 0
        return 1
    try:
        return sorted(server or [], key=rango)
    except Exception:
        return server


def _apri_sessione_nostra(item):
    """Dice al servizio di Le Saghe cosa sta per partire, cosi' puo' fare il
    conto alla rovescia verso il prossimo episodio ANCHE quando il video lo
    apre s4me (e non il nostro `azione=riproduci`). Scrive lo stesso file
    `sessione.json` che scriverebbe `progresso.apri_sessione`."""
    pid = getattr(item, "percorso", "") or ""
    try:
        idx = int(getattr(item, "idx", 0) or 0)
    except (TypeError, ValueError):
        idx = 0
    if not pid or not idx:
        return
    try:
        import json as _json
        import time as _time
        import xbmcvfs as _vfs
        base = _vfs.translatePath(
            "special://profile/addon_data/plugin.video.saghe/")
        if not os.path.isdir(base):
            os.makedirs(base)
        with open(os.path.join(base, "sessione.json"), "w",
                  encoding="utf-8") as f:
            _json.dump({"percorso": pid, "idx": idx, "dentro_kodi": True,
                        "atteso": getattr(item, "titolo_serie", ""),
                        "file_atteso": "", "controllata": True,
                        "avviata": int(_time.time())}, f)
    except Exception as e:
        logger.info("Le Saghe: sessione non aperta: %s" % e)


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


# Parole che non distinguono niente: se restano sole, due titoli diversi
# sembrano lo stesso.
PAROLE_VUOTE = {"la", "le", "il", "lo", "i", "gli", "un", "una", "uno",
                "di", "del", "della", "dei", "e", "the", "of", "a",
                "stagione", "season", "ita", "sub", "streaming", "serie", "tv"}


def _copertura(trovato, voluto):
    """Quanta parte del titolo VOLUTO compare in quello TROVATO, 0-100.

    IL GUASTO DEL 07/09/2026: cercando "Terra amara" il risolutore ha
    accettato "Terra Nova". Con la vecchia misura i due titoli si
    somigliavano al 50% - una parola su due - e la soglia era 30.
    Ma le due parole non pesano uguale: "terra" e' generica, "amara" e' il
    nome della serie. Contare la SOVRAPPOSIZIONE premia i titoli corti che
    condividono una parola qualunque.

    Qui si misura un'altra cosa: quante delle parole che ho CHIESTO ci sono
    davvero. "Terra Nova" contiene "terra" ma non "amara": 50%, si rifiuta.
    "Terra amara - Stagione 1" le contiene tutte e due: 100%, si accetta,
    anche se e' piu' lungo.
    """
    import re
    import unicodedata

    def parole(s):
        s = unicodedata.normalize("NFKD", str(s or ""))
        s = "".join(x for x in s if not unicodedata.combining(x)).lower()
        p = set(re.sub(r"[^a-z0-9]+", " ", s).split())
        significative = p - PAROLE_VUOTE
        return significative or p      # un titolo di sole parole vuote resta se'

    pv = parole(voluto)
    if not pv:
        return 0
    return int(100.0 * len(pv & parole(trovato)) / len(pv))


# Sotto questa copertura non si apre niente: meglio dire "non l'ho trovata"
# che far partire la serie sbagliata. E' successo con Terra Nova.
COPERTURA_MINIMA = 80

# Le parole che DISTINGUONO una serie da un'altra della stessa saga: se il
# risultato ne ha una che la serie voluta non ha, e' un'ALTRA serie.
# IL GUASTO (10/09/2026): chiesto "Dragon Ball" episodio 1, s4me ha aperto
# "Dragon Ball GT" episodio 1 - GT contiene "dragon" e "ball", quindi la
# copertura era 100% e ha pareggiato con la serie giusta.
MARCATORI_SERIE = {
    "gt", "z", "kai", "super", "ultra", "daima", "af", "evolution",
    "shippuden", "boruto", "next", "generations", "reboot", "remake",
    "crystal", "brotherhood", "2003", "2011", "movie", "ova", "special",
}


def _parole_nude(s):
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return set(re.sub(r"[^a-z0-9]+", " ", s).split())


def _serie_sbagliata(nome_trovato, nomi_voluti):
    """Vero se il titolo trovato porta un marcatore (GT, Z, Shippuden...) che
    NESSUNO dei nomi voluti ha: e' un'altra serie della stessa saga."""
    trovate = _parole_nude(nome_trovato) & MARCATORI_SERIE
    if not trovate:
        return False
    voluti = set()
    for t in nomi_voluti:
        voluti |= _parole_nude(t)
    return bool(trovate - voluti)


def _titoli_da_provare(serie, titolo):
    """I nomi con cui cercare QUESTA serie, dal piu' preciso al piu' generico.

    Prima il nome della SERIE ('Dragon Ball GT'), non quello della saga
    ('Dragon Ball'): dentro una saga con piu' serie, cercare il nome della
    saga trova la serie sbagliata. Poi il titolo passato, poi gli alias
    (le turche cambiano nome fra Italia e Turchia).
    """
    fuori = []
    proprio = (serie or {}).get("titolo", "")
    if proprio:
        fuori.append(proprio)
    if titolo and titolo not in fuori:
        fuori.append(titolo)
    for alt in (serie or {}).get("alias", []):
        if alt and alt not in fuori:
            fuori.append(alt)
    return fuori


def _titolo_pulito(titolo):
    """Rimette gli spazi al posto dei '+'.

    IL GUASTO DEL 07/09/2026, visto nel registro: cercavamo letteralmente
    "Terra+amara". Nell'indirizzo che apre l'episodio gli spazi diventano
    '+' (e' come si scrivono i parametri di un indirizzo web), ma chi lo
    rilegge dall'altra parte scioglie i %20 e NON i '+': cosi' il titolo
    arrivava qui con dentro un piu'. Sui siti non esiste nessuna "Terra+
    amara", quindi la ricerca tornava vuota o - peggio - con roba a caso.
    """
    t = str(titolo or "")
    if "+" in t and " " not in t:
        t = t.replace("+", " ")
    return t.strip()


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
    f = _rubrica_file()
    if not f:
        return
    try:
        _json_atomico(f, dati, ensure_ascii=False)
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
    titolo = _titolo_pulito(getattr(item, "titolo_serie", "") or item.fulltitle)
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
                        _apri_sessione_nostra(item)
                        return _pota_server(server)
            except Exception as e:
                logger.info("Le Saghe: la rubrica non ha funzionato: %s" % e)
        # L'indirizzo in rubrica non vale piu': si dimentica e si ricerca.
        _rubrica_scorda(serie_id)

    # 2) La ricerca vera, che e' lenta: si fa una volta per serie.
    #    E si fa sui siti GIUSTI per il tipo di serie: cercare una serie
    #    turca sui siti di anime non da' zero risultati per sfortuna, li da'
    #    per costruzione.
    serie_del_catalogo = catalogo().get("SERIE", {}).get(serie_id, {})
    nomi = _titoli_da_provare(serie_del_catalogo, titolo)
    # Perche' ogni sito non ha funzionato. Se alla fine non si trova niente,
    # questo elenco finisce A SCHERMO invece del solito "nessuna fonte":
    # l'utente ha chiesto di sapere se una cosa a catalogo si puo' davvero
    # guardare, e "no, ed ecco perche'" e' una risposta, "no" non lo e'.
    motivi = []
    for nome in _canali_per(serie_del_catalogo):
        canale = _modulo(nome)
        if not canale:
            continue
        risultati = []
        for chiamala in nomi:
            try:
                ricerca = Item(channel=nome, action="search",
                               contentType="tvshow", search="", args="")
                risultati = canale.search(ricerca, chiamala) or []
            except Exception as e:
                logger.error("Le Saghe: ricerca su %s fallita: %s" % (nome, e))
                continue
            if risultati:
                break        # trovato con questo nome: gli altri non servono

        risultati = [r for r in risultati if getattr(r, "action", "")]
        if not risultati:
            continue

        def _nome(r):
            return getattr(r, "fulltitle", "") or getattr(r, "title", "")

        def _quanto(r):
            """La copertura migliore fra tutti i nomi della serie."""
            return max(_copertura(_nome(r), t) for t in nomi)

        # Scarta subito i titoli che sono un'ALTRA serie della saga
        # (Dragon Ball GT quando si vuole Dragon Ball): il marcatore "gt"
        # non e' fra i nomi voluti.
        buoni = [r for r in risultati
                 if not _serie_sbagliata(_nome(r), nomi)]
        if buoni:
            risultati = buoni

        # Prima la lingua (italiano batte sottotitolato), poi quanto e'
        # completo il titolo, e a parita' MENO parole in piu' (cosi'
        # "Dragon Ball" batte "Dragon Ball - Stagione 1").
        def _extra(r):
            pn = _parole_nude(_nome(r))
            return min(len(pn - _parole_nude(t)) for t in nomi)
        risultati.sort(
            key=lambda r: (_rango_lingua(r), _quanto(r), -_extra(r)),
            reverse=True)

        # Tutti i risultati che POSSONO essere questa serie (non solo il
        # primo): un sito lungo spesso spezza una serie in piu' voci
        # ("Dragon Ball Z" 1-x, poi la parte 2) e la puntata 147 sta nella
        # seconda. Si provano in ordine finche' uno ha l'episodio giusto.
        candidati = [r for r in risultati
                     if _quanto(r) >= COPERTURA_MINIMA
                     and not _serie_sbagliata(_nome(r), nomi)]
        if not candidati:
            m = risultati[0] if risultati else None
            logger.info("Le Saghe: su %s nessun risultato e' %r (migliore: %r)"
                        % (nome, titolo, _nome(m) if m else "-"))
            motivi.append("%s: c'e' solo '%s', che non e' questa serie"
                          % (nome, (_nome(m)[:40] if m else "niente")))
            continue

        scelto = None
        buono = None
        for cand in candidati[:5]:
            episodi = _episodi_di(canale, cand)
            if not episodi:
                continue
            e = _episodio_giusto(episodi, numero)
            if e:
                scelto, buono = e, cand
                break
        if not scelto:
            motivi.append("%s: ha la serie ma non l'episodio %d "
                          "(forse il sito lo numera diverso)" % (nome, numero))
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
                _rubrica_segna(serie_id, nome, buono)
            _apri_sessione_nostra(item)
            return _pota_server(server)
        motivi.append("%s: ha l'episodio ma nessun video che si apra" % nome)

    # ULTIMA SPIAGGIA: gli abbonamenti.
    #
    # Se nessuno dei canali ha l'episodio, puo' esserci su Netflix o su
    # Prime. Non si tira a indovinare: il catalogo SA gia' su quale
    # servizio sta ogni serie, e si offrono solo quelli - e solo se
    # l'add-on corrispondente e' installato.
    abbonamenti = _abbonamenti(getattr(item, "serie_id", ""), titolo)

    # RIPIEGO YOUTUBE, per QUALSIASI saga.
    # L'utente: "su YouTube ci sono episodi di Dragon Ball sottotitolati; se
    # non li abbiamo, mettili nelle mie saghe con la locandina". YouTube ha
    # moltissimi episodi vecchi, spesso sottotitolati e non altrove. Non e'
    # una fonte diretta (s4me non risolve il video), ma apre la ricerca
    # gia' scritta: un clic e sei sull'episodio. Vale per ogni serie, anche
    # quelle che si aggiungeranno.
    coda = list(abbonamenti or [])
    try:
        import xbmcvfs
        yt_ok = xbmcvfs.exists(
            "special://home/addons/plugin.video.youtube/addon.xml")
    except Exception:
        yt_ok = True
    if yt_ok:
        from urllib.parse import quote_plus
        sch = scheda(serie_id) if serie_id else {}
        q = "%s episodio %d sub ita" % (titolo, numero)
        coda.append(Item(
            channel=item.channel, action="", folder=True,
            url="plugin://plugin.video.youtube/kodion/search/query/?q=%s"
                % quote_plus(q),
            title=support.typo(
                "Cerca l'episodio %d su YouTube" % numero, "bold color KOD"),
            plot="Nessun sito aveva l'episodio %d di %s.\n\nYouTube ne ha "
                 "moltissimi, spesso sottotitolati in italiano. Questa voce "
                 "apre la ricerca gia' pronta: la qualita' cambia da un "
                 "video all'altro, controlla prima di guardare." % (numero, titolo),
            thumbnail=sch.get("poster", "") or "",
            fanart=sch.get("sfondo", "") or ""))

    if coda:
        return coda

    return [Item(
        channel=item.channel, action="", folder=False,
        title=support.typo(
            "Non l'ho trovato: ecco cosa ho provato" if motivi
            else "Nessuna fonte trovata per l'episodio %d" % numero,
            "bold color kod"),
        plot="Episodio %d di %s.\n\nHo cercato su %d siti:\n\n- %s\n\n"
             "Se il motivo e' sempre lo stesso, il sito e' cambiato e va "
             "aggiornato s4me; se dice che la serie non c'e', quella serie "
             "in italiano potrebbe non esistere in rete."
             % (numero, titolo, len(motivi), "\n- ".join(motivi))
             if motivi else
             "Nessun sito ha risposto per l'episodio %d di %s." % (numero, titolo))]


# Gli add-on degli abbonamenti, e come si chiede loro di cercare un titolo.
SERVIZI = {
    "netflix": ("Netflix", "plugin.video.netflix",
                "plugin://plugin.video.netflix/directory/search/search/%s/"),
    "prime": ("Prime Video", "plugin.video.amazon-test",
              "plugin://plugin.video.amazon-test/?mode=search&searchstring=%s"),
    "animegeneration": ("Anime Generation", "plugin.video.amazon-test",
                        "plugin://plugin.video.amazon-test/?mode=search&searchstring=%s"),
    # YouTube non e' un ripiego: per certe serie (Super Dragon Ball Heroes)
    # e' la fonte VERA, quella dove sono uscite. Ed e' installato su tutti e
    # due gli apparecchi, a differenza di Netflix e Prime.
    "youtube": ("YouTube", "plugin.video.youtube",
                "plugin://plugin.video.youtube/kodion/search/query/?q=%s"),
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


def _pare_un_episodio(v):
    """Vero se questa voce e' un episodio, non una stagione o un menu.

    IL SEGNALE PIU' AFFIDABILE NON E' IL TITOLO, e ci e' costato caro:
    Mediaset chiama i suoi episodi "Terra amara  [21 marzo]" - niente
    "1x01", nessun numero. Guardando solo il titolo sembravano stagioni, e
    il risolutore scendeva dentro tutti e 166 uno per uno: minuti di attesa
    per niente.
    Quello che i canali dicono sempre e' `contentType` e `action`: una voce
    che porta a `findvideos` E' un episodio, per definizione - e' l'ultimo
    passo prima del video.
    """
    if getattr(v, "contentEpisodeNumber", None):
        return True
    if str(getattr(v, "contentType", "")) == "episode":
        return True
    if str(getattr(v, "action", "")) == "findvideos":
        return True
    import re
    testo = getattr(v, "title", "") or getattr(v, "fulltitle", "")
    return bool(re.search(r"\d+\s*[xX]\s*\d+|episodi\w*\s*\d+", str(testo)))


# Funzioni che NON portano a un elenco di episodi: chiamarle qui vuol dire
# far partire un video o cadere.
AZIONI_DA_NON_SEGUIRE = ("findvideos", "play", "search", "mainlist", "")

# I nomi che un tasto del PLAYER porta nel titolo: se una "voce" si chiama
# cosi', non e' una stagione, e' un bottone - non ci si scende.
_PAROLE_PLAYER = ("server", "alternativ", "player", "mirror", "lettore",
                  "streamtape", "dood", "mixdrop", "vidguard", "voe",
                  "streamwish", "supervideo", "maxstream")


def _pare_una_stagione(v):
    """Vero se questa voce e' plausibilmente una STAGIONE (non un episodio,
    non un bottone del player)."""
    import re
    testo = str(getattr(v, "title", "") or getattr(v, "fulltitle", "")).lower()
    if any(p in testo for p in _PAROLE_PLAYER):
        return False
    azione = str(getattr(v, "action", "") or "")
    if azione in ("episodios", "epmenu", "seasons", "temporadas"):
        return True
    if re.search(r"stagion|season|parte|part\s*\d|serie\s*\d|arco|saga", testo):
        return True
    # una manciata di voci con un numero e senza segni di "episodio": puo'
    # essere "1", "2", "3" = le stagioni.
    return bool(re.fullmatch(r"[\s\-.]*\d{1,2}[\s\-.]*", testo))

# Oltre questo numero di voci non sono stagioni: sono gia' episodi. Nessuna
# serie ha cinquanta stagioni, ma tante ne hanno centosessanta di puntate.
MASSIME_STAGIONI = 12


def _episodi_di(canale, voce, profondita=2):
    """Gli episodi di una serie, seguendo la strada che la voce indica.

    TRE COSE IMPARATE IL 07/09/2026 dietro "la serie turca non parte".

    1. **La strada la dice la voce, non noi.** Qui si chiamava sempre
       `episodios()`. Ma i canali di s4me dicono da soli come si prosegue,
       nel campo `action` del risultato: su Mediaset una serie porta a
       `epmenu` (l'elenco delle STAGIONI), non a `episodios`. Chiamando
       `episodios` a forza si finiva in una richiesta senza il numero della
       stagione, e cadeva con `KeyError: 'entries'`.
       Per due giorni quell'errore e' sembrato un guasto di s4me. Era il
       nostro modo di chiamarlo.

    2. **Gli errori venivano ingoiati in silenzio** (`except: continue`):
       il risolutore trovava la pagina giusta e si fermava senza dire
       perche'. Adesso ogni inciampo si scrive nel registro.

    3. **Le serie TV hanno due livelli**, non uno: serie -> stagioni ->
       episodi. Con i cartoni quasi mai, con le serie e' la regola. Se
       quello che torna non sembrano episodi, si scende.
    """
    # Prima la funzione che la voce stessa dichiara, poi i nomi soliti.
    # `check` va per ULTIMO: su animeworld il risultato della ricerca porta
    # `action='check'`, ma `check()` restituisce i pulsanti del player
    # ("Server 1", "Alternativo"), NON l'elenco degli episodi. Scendendo in
    # quei due la ricerca si perdeva per minuti sulla linea lenta e
    # l'episodio profondo (Naruto 150, DBZ 147) non partiva.
    azione = str(getattr(voce, "action", "") or "")
    da_provare = []
    if azione not in AZIONI_DA_NON_SEGUIRE and azione != "check":
        da_provare.append(azione)
    for n in ("episodios", "epmenu"):
        if n not in da_provare:
            da_provare.append(n)
    if "check" not in da_provare:
        da_provare.append("check")

    for nome_funzione in da_provare:
        f = getattr(canale, nome_funzione, None)
        if not callable(f):
            continue
        try:
            fuori = f(voce) or []
        except Exception as e:
            logger.info("Le Saghe: %s() e' caduta: %s: %s"
                        % (nome_funzione, type(e).__name__, e))
            continue
        if not fuori:
            continue
        if any(_pare_un_episodio(v) for v in fuori):
            return fuori
        # Si scende SOLO in voci che SEMBRANO stagioni, e in POCHE.
        # Se `check()` restituisce due bottoni del player ("Server",
        # "Alternativo"), scendere dentro e' tempo buttato sulla linea
        # lenta e non porta agli episodi (Naruto 150, DBZ 147).
        if profondita > 0 and 1 <= len(fuori) <= MASSIME_STAGIONI:
            stagioni = [v for v in fuori if _pare_una_stagione(v)]
            if stagioni:
                logger.info("Le Saghe: %s() ha dato %d stagioni, scendo"
                            % (nome_funzione, len(stagioni)))
                for sotto in stagioni[:6]:
                    dentro = _episodi_di(canale, sotto, profondita - 1)
                    if dentro and any(_pare_un_episodio(v) for v in dentro):
                        return dentro
            else:
                logger.info("Le Saghe: %s() ha dato %d voci che non sono ne' "
                            "episodi ne' stagioni (bottoni del player?), "
                            "lascio stare" % (nome_funzione, len(fuori)))
            # niente di utile qui: si prova la funzione dopo, non `fuori`.
            continue
        return fuori
    return []


def _episodio_giusto(episodi, numero):
    """L'episodio col numero giusto. None se non si e' sicuri.

    None NON e' un fallimento da aggirare: vuol dire che non lo sappiamo,
    e tirare a indovinare e' come si finisce a guardare l'episodio
    sbagliato. E' gia' successo.
    """
    import re

    # 1) Il numero dichiarato dal canale: l'unico davvero sicuro.
    for e in episodi:
        n = getattr(e, "contentEpisodeNumber", None)
        try:
            if n is not None and int(n) == numero:
                return e
        except (TypeError, ValueError):
            pass

    # 2) Un numero scritto nel titolo in una forma che vuol dire "episodio":
    #    "1x05", "Episodio 5", "Ep. 5". NON un numero qualunque.
    #
    #    Prima qui c'era `\d{1,4}` su tutto il titolo, e su Mediaset gli
    #    episodi si chiamano "Terra amara  [21 marzo]": chiedendo la puntata
    #    21 avrebbe restituito quella del 21 marzo. Un numero che capita in
    #    un titolo non e' un numero di episodio.
    forme = (r"\d+\s*[xX]\s*0*%d(?:\D|$)" % numero,
             r"(?:^|\D)(?:ep|episodio|episode|puntata)\W*0*%d(?:\D|$)" % numero)
    for e in episodi:
        testo = str(getattr(e, "title", "") or "")
        if any(re.search(f, testo, re.I) for f in forme):
            return e

    # 3) NESSUNO degli episodi porta un numero, da nessuna parte.
    #    Succede sui servizi ufficiali: Mediaset elenca le puntate in ordine
    #    di messa in onda e le chiama tutte col nome della serie piu' la
    #    data. In quel caso la POSIZIONE nell'elenco e' il numero della
    #    puntata: e' l'unica informazione che c'e', ed e' quella giusta -
    #    ma solo se l'elenco e' completo (piu' lungo del numero chiesto) e
    #    se nessuna voce aveva un numero suo da contraddire.
    def _ha_un_numero(e):
        if getattr(e, "contentEpisodeNumber", None):
            return True
        return bool(re.search(r"\d+\s*[xX]\s*\d+|(?:ep|episodio|puntata)\W*\d+",
                              str(getattr(e, "title", "") or ""), re.I))

    if 1 <= numero <= len(episodi) and not any(_ha_un_numero(e) for e in episodi):
        scelto = episodi[numero - 1]
        logger.info("Le Saghe: nessun episodio e' numerato, prendo il %d in "
                    "ordine: %r" % (numero, str(getattr(scelto, "title", ""))[:60]))
        return scelto

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


# --------------------------------------------------------------------------
# AL CINEMA ORA
# --------------------------------------------------------------------------
#
# CHI DECIDE COSA C'E' AL CINEMA
#     Non s4me. Il suo aggregatore di novita' raccoglie "gli ultimi film
#     caricati dai siti", che non e' la stessa domanda: un film del 2019
#     messo online ieri finirebbe nel cartellone, un film in sala da un mese
#     che nessuno ha caricato ne resterebbe fuori.
#     L'elenco lo prepara `resources/lib/cinema.py` chiedendolo a TMDB
#     (le sale ITALIANE), lo scrive in `cinema.json`, e qui si legge quello.
#
# CHI TROVA IL VIDEO
#     Questa parte, e solo quando apri un film: cercare quaranta titoli su
#     otto siti all'apertura della sezione vorrebbe dire minuti di attesa
#     davanti a una schermata vuota. Cosi' invece la sezione compare subito.
#
# SE NON SI TROVA
#     Non si finge. Si dice sito per sito cosa e' successo, e si offre di
#     aprirlo su Prime Video o Netflix: sono film di sala, e' normale che i
#     siti pirata non li abbiano ancora.

# I siti da cui si pescano i FILM. Gli altri elenchi (CANALI_PER_TIPO) sono
# per le serie: cercare un film di sala su animeworld non ha senso.
# Ordine: prima quelli che rispondono e hanno le migliori copie.
CANALI_FILM = ["streamingcommunity", "altadefinizione01", "cineblog01",
               "filmpertutti", "ilgeniodellostreaming", "piratestreaming",
               "filmstreaming", "lordchannel"]


def _cartellone():
    """L'elenco preparato da cinema.py. Se manca, lista vuota."""
    try:
        import json as _json
        import os as _os
        import xbmcvfs as _vfs
        p = _os.path.join(
            _vfs.translatePath(
                "special://profile/addon_data/plugin.video.saghe/"),
            "cinema.json")
        with open(p, encoding="utf-8") as f:
            return (_json.load(f) or {}).get("film") or []
    except Exception as e:
        logger.info("Le Saghe: cartellone non leggibile: %s" % e)
        return []


def cinema(item):
    """La sezione: un film per riga, con locandina, trama e voto."""
    film = _cartellone()
    if not film:
        return [Item(
            channel=item.channel, action="", folder=False,
            title=support.typo("Cartellone non ancora scaricato", "bold color kod"),
            plot="L'elenco dei film in sala si aggiorna una volta al giorno, "
                 "all'avvio. Se hai appena acceso, riprova fra un minuto; se "
                 "il messaggio resta, manca la connessione.")]

    fuori = []
    for f in film:
        anno = f.get("anno") or ""
        voto = f.get("voto") or 0
        etichetta = f["titolo"] + (" (%s)" % anno if anno else "")
        fuori.append(Item(
            channel=item.channel, action="cinema_fonti", folder=True,
            title=support.typo(etichetta, "bold"),
            fulltitle=f["titolo"], show=f["titolo"],
            contentTitle=f["titolo"], contentType="movie",
            infoLabels={"title": f["titolo"], "year": anno,
                        "plot": f.get("trama", ""), "rating": voto},
            plot=f.get("trama", ""),
            thumbnail=f.get("poster", ""), fanart=f.get("sfondo", ""),
            titolo_film=f["titolo"],
            titolo_originale=f.get("originale", "")))
    return fuori


def cinema_fonti(item):
    """Cerca UN film di sala sui siti dei film. Stessa logica delle serie."""
    titolo = _titolo_pulito(getattr(item, "titolo_film", "") or item.fulltitle)
    originale = _titolo_pulito(getattr(item, "titolo_originale", ""))

    # Due tentativi: il titolo italiano e - se diverso - quello originale.
    # Molti siti archiviano col titolo inglese, ed e' l'unico modo di
    # trovarli senza indovinare.
    nomi = [titolo]
    if originale and originale.lower() != titolo.lower():
        nomi.append(originale)

    motivi = []
    for nome in CANALI_FILM:
        canale = _modulo(nome)
        if not canale:
            continue

        risultati = []
        for chiamala in nomi:
            try:
                ricerca = Item(channel=nome, action="search",
                               contentType="movie", search="", args="")
                risultati = canale.search(ricerca, chiamala) or []
            except Exception as e:
                logger.error("Le Saghe: ricerca film su %s fallita: %s" % (nome, e))
                continue
            if risultati:
                break

        risultati = [r for r in risultati if getattr(r, "action", "")]
        if not risultati:
            continue

        def _nome(r):
            return getattr(r, "fulltitle", "") or getattr(r, "title", "")

        def _quanto(r):
            return max(_copertura(_nome(r), t) for t in nomi)

        migliore = max(risultati, key=lambda r: (_quanto(r), _rango_lingua(r)))
        if _quanto(migliore) < COPERTURA_MINIMA:
            motivi.append("%s: c'e' solo '%s', che non e' questo film"
                          % (nome, _nome(migliore)[:40]))
            continue

        try:
            server = canale.findvideos(migliore) or []
        except Exception as e:
            logger.error("Le Saghe: findvideos film su %s fallito: %s" % (nome, e))
            motivi.append("%s: ha il film ma va in errore" % nome)
            continue

        if server:
            for s in server:
                s.channel = nome
            return _pota_server(server)
        motivi.append("%s: ha il film ma nessun video che si apra" % nome)

    # Non trovato sui siti. Per un film ANCORA IN SALA e' la normalita':
    # si offre di cercarlo sugli abbonamenti, che e' dove sara' per primo.
    import xbmcvfs
    from urllib.parse import quote

    fuori = []
    for chiave in ("prime", "netflix"):
        etichetta, addon, modello = SERVIZI[chiave]
        # Stessa verifica che usa _abbonamenti: si guarda se l'add-on c'e'
        # davvero sul disco. `xbmc` non e' importato in questo file.
        if not xbmcvfs.exists("special://home/addons/%s/addon.xml" % addon):
            continue
        fuori.append(Item(
            channel=item.channel, action="", folder=True,
            url=modello % quote(titolo),
            title=support.typo("Cercalo su %s" % etichetta, "bold color kod"),
            plot="%s non e' su nessuno dei siti. E' appena uscito al cinema, "
                 "quindi e' normale: qui lo cerco su %s."
                 % (titolo, etichetta)))

    fuori.append(Item(
        channel=item.channel, action="", folder=False,
        title=support.typo("Non l'ho trovato: ecco cosa ho provato" if motivi
                           else "Nessun sito ha risposto", "bold color kod"),
        plot="%s.\n\nHo cercato su %d siti:\n\n- %s\n\nPer un film ancora "
             "nelle sale e' normale non trovarlo: i siti lo caricano dopo."
             % (titolo, len(motivi), "\n- ".join(motivi))
             if motivi else
             "Nessuno dei siti dei film ha risposto per %s." % titolo))
    return fuori
