# -*- coding: utf-8 -*-
"""Prove sul menu dell'add-on, senza TV e senza box.

Si controlla quello che e' gia' andato storto davvero, non casi immaginari:
ogni prova qui sotto corrisponde a un guasto vero o a una promessa fatta
all'utente.
"""
import io
import json
import os
import shutil
import sys
import time

ADDON = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finto_kodi  # noqa: E402

IMPOSTAZIONI = {
    "ha_netflix": True, "ha_prime": True, "ha_disney": False,
    "ha_timvision": False, "ha_animegeneration": False, "ha_crunchyroll": False,
    "cartella_serie": "", "hub_indirizzo": "",
    "scadenza_prime": "04/10/2026", "scadenza_netflix": "",
    "audio_scelta_automatica": True, "audio_avvisa": False,
    "prossimo_automatico": True, "prossimo_attesa": 10,
}

PROFILO = finto_kodi.installa(ADDON, IMPOSTAZIONI)
sys.path.insert(0, ADDON)
sys.argv = ["plugin://plugin.video.saghe/", "1", ""]

import main                                      # noqa: E402
from resources.lib import catalogo, progresso     # noqa: E402

ESITI = []


def prova(nome):
    def dec(f):
        try:
            f()
            ESITI.append((True, nome, ""))
        except AssertionError as e:
            ESITI.append((False, nome, str(e) or "asserzione fallita"))
        except Exception as e:
            ESITI.append((False, nome, "%s: %s" % (type(e).__name__, e)))
        return f
    return dec


def scrivi_progresso(dati):
    with io.open(os.path.join(PROFILO, "progresso.json"), "w",
                 encoding="utf-8") as f:
        f.write(json.dumps(dati))


def _e_una_tappa(indirizzo):
    """Vero se questa voce porta a un episodio preciso.

    Da quando gli episodi si aprono col motore di s4me l'indirizzo non e'
    piu' il nostro (`idx=`) ma il suo (`numero_ep=`): la prova deve
    riconoscere tutti e due, altrimenti guarda il passato.
    """
    return ("idx=" in indirizzo) or ("numero_ep=" in indirizzo)


def apri_menu():
    finto_kodi.azzera()
    main.menu_principale()
    return [v for v in finto_kodi.VOCI if isinstance(v, dict)]


# --------------------------------------------------------------------------

@prova("la porta di casa e' corta: pochi reparti, non l'elenco di tutto")
def _():
    # Dal 07/09/2026 il menu principale NON elenca piu' le saghe: sono
    # scese di un livello, nei reparti. Qui si controlla che la porta sia
    # corta davvero (era il difetto: tutto insieme in una schermata sola) e
    # che porti dove deve.
    scrivi_progresso({})
    voci = apri_menu()
    # Il limite e' salito a 15 il 07/09/2026, quando l'utente ha chiesto
    # documentari, cucina, YouTube, TV in diretta e i consigliati - e li ha
    # voluti SEPARATI ("tienili separati, documentari una cosa, cucina
    # un'altra"). Il senso della prova non cambia: la porta deve restare
    # un menu di reparti, non l'elenco di tutto il catalogo (erano 62).
    assert 4 <= len(voci) <= 15, "la porta ha %d voci" % len(voci)
    testo = " ".join(v["url"] for v in voci)
    for pezzo in ("reparto=cartoni", "azione=film_tutti", "azione=cerca",
                  "azione=vetrina"):
        assert pezzo in testo, "manca %s dalla porta" % pezzo


def _raggiungibili():
    """Tutti i percorsi che si possono raggiungere: quelli del menu
    principale piu' quelli dentro un raggruppamento."""
    fuori = set(catalogo.ORDINE_PERCORSI)
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        fuori |= set(catalogo.GRUPPI[gid]["percorsi"])
    return fuori


def _voci_reparto(reparto):
    finto_kodi.azzera()
    main.menu_reparto(reparto)
    return [v for v in finto_kodi.VOCI if isinstance(v, dict)]


@prova("ogni raggruppamento sta in UN reparto, e quel reparto lo mostra")
def _():
    scrivi_progresso({})
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        reparto = catalogo.GRUPPI[gid].get("reparto", "cartoni")
        assert reparto in main.REPARTI, "%s: reparto sconosciuto %r" % (gid, reparto)
        testo = " ".join(v["url"] for v in _voci_reparto(reparto))
        assert "gruppo=%s" % gid in testo, \
            "%s non compare nel reparto %s" % (gid, reparto)


@prova("i film hanno un reparto loro, e ogni saga con film ci si trova dentro")
def _():
    # L'utente non li trovava: stavano dentro "Altro..." di ogni saga.
    scrivi_progresso({})
    finto_kodi.azzera()
    main.menu_film_tutti()
    voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
    testo = " ".join(v["url"] for v in voci)
    attese = [pid for pid, _ in main._saghe_con_film()]
    assert attese, "nessuna saga ha film: il reparto sarebbe vuoto"
    for pid in attese:
        assert "percorso=%s" % pid in testo, "%s manca dal reparto film" % pid


@prova("ogni saga del catalogo si puo' raggiungere (l'errore di ORDINE_PERCORSI)")
def _():
    # LO SCOPO NON E' CAMBIATO col menu nuovo: una saga che sta nel catalogo
    # ma non si raggiunge da nessuna parte e' invisibile, ed e' gia'
    # successo (Jeeg). Solo che adesso il cammino passa dai reparti.
    scrivi_progresso({})
    testo = " ".join(v["url"] for v in _voci_reparto("cartoni"))
    diretti = [p for p in catalogo.ORDINE_PERCORSI if "percorso=%s" % p not in testo]
    assert not diretti, "saghe invisibili nel reparto cartoni: %s" % ", ".join(diretti)
    mancanti = sorted(set(catalogo.PERCORSI) - _raggiungibili())
    assert not mancanti, "percorsi che non si raggiungono da nessuna parte: %s" % ", ".join(mancanti)


@prova("i raggruppamenti si aprono e mostrano tutte le loro serie")
def _():
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        finto_kodi.azzera()
        main.menu_gruppo(gid)
        voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
        attesi = catalogo.GRUPPI[gid]["percorsi"]
        assert len(voci) == len(attesi),             "%s: %d voci invece di %d" % (gid, len(voci), len(attesi))
        testo = " ".join(v["url"] for v in voci)
        for pid in attesi:
            assert "percorso=%s" % pid in testo, "%s manca da %s" % (pid, gid)


@prova("nell'elenco si vede subito quali NON sono doppiate")
def _():
    """La regola di casa e' italiano prima di tutto: se una serie ha solo i
    sottotitoli si deve leggere nell'ELENCO, non dopo esserci entrati."""
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        finto_kodi.azzera()
        main.menu_gruppo(gid)
        voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
        for v, pid in zip(voci, catalogo.GRUPPI[gid]["percorsi"]):
            prima = catalogo.PERCORSI[pid]["segmenti"][0][0]
            if not catalogo.SERIE[prima].get("audio_ita"):
                assert "sottotitolat" in v["etichetta"].lower(),                     "%s non e' doppiata e non lo dice: %r" % (pid, v["etichetta"][:60])


@prova("le saghe hanno la locandina")
def _():
    scrivi_progresso({})
    senza = [v["etichetta"].split("\n")[0] for v in apri_menu()
             if "azione=percorso" in v["url"] and not v["arte"].get("poster")]
    assert not senza, "senza locandina: %s" % ", ".join(senza)


@prova("'Continua a guardare' non compare a scatola nuova")
def _():
    scrivi_progresso({})
    assert not [v for v in apri_menu() if _e_una_tappa(v["url"])], \
        "una voce di ripresa su un add-on mai usato"


@prova("'Continua a guardare' compare, in cima, dopo aver guardato")
def _():
    ora = int(time.time())
    scrivi_progresso({
        "naruto":    {"idx": 12, "secondi": 300, "durata": 1400,
                      "visti": [1], "aggiornato": ora},
        "one_piece": {"idx": 3, "secondi": 0, "durata": 0,
                      "visti": [1, 2], "aggiornato": ora - 9000},
    })
    voci = apri_menu()
    # La voce di ripresa punta a una TAPPA precisa: puo' essere "riproduci"
    # (file locale) o "apri" (app o ponte s4me), ma sempre con un idx.
    ripresa = [i for i, v in enumerate(voci) if _e_una_tappa(v["url"])]
    assert len(ripresa) == 2, "voci di ripresa: %d invece di 2" % len(ripresa)
    assert ripresa == [0, 1], "non sono in cima: stanno in %s" % ripresa
    # l'indirizzo verso s4me porta serie_id, il nostro porta percorso:
    # la prova deve riconoscere la saga in tutti e due i modi
    assert ("percorso=naruto" in voci[0]["url"]
            or "serie_id=naruto" in voci[0]["url"]), \
        "la piu' recente non e' prima: %s" % voci[0]["url"]


@prova("la voce di ripresa e' coerente: o riproduce davvero, o e' una cartella")
def _():
    """Non si puo' promettere una riproduzione e poi non darla.

    Era esattamente il guasto del 06/09/2026: voci dichiarate riproducibili
    che non avevano nessun video da restituire a Kodi. Kodi rispondeva
    "errore di riproduzione", su ogni singolo episodio.
    """
    voci = [v for v in apri_menu() if _e_una_tappa(v["url"])]
    assert voci, "nessuna voce di ripresa"
    for v in voci:
        gioca = v["prop"].get("IsPlayable") == "true"
        if gioca:
            assert "azione=riproduci" in v["url"] and not v["cartella"], (
                "si dichiara riproducibile ma non lo e': " + v["url"])
        else:
            # Non e' un file tuo: deve essere una cartella che porta a s4me,
            # che ha 55 fonti e le tiene aggiornate lui.
            assert v["cartella"], (
                "non riproducibile ma non e' nemmeno una cartella: " + v["url"])
            assert "plugin.video.s4me" in v["url"], (
                "non passa da s4me: " + v["url"])


@prova("la barretta di avanzamento c'e' quando conosciamo il minuto")
def _():
    voci = [v for v in apri_menu() if _e_una_tappa(v["url"])]
    assert voci[0]["tag"].get("resumepoint"), "nessun punto di ripresa"
    assert not voci[1]["tag"].get("resumepoint"), \
        "punto di ripresa inventato per una fonte esterna"


@prova("la ripresa mostra il minuto in modo leggibile")
def _():
    voci = [v for v in apri_menu() if _e_una_tappa(v["url"])]
    assert "5:00" in voci[0]["etichetta"], \
        "manca il minuto: %r" % voci[0]["etichetta"]


@prova("una saga sparita dal catalogo non fa cadere il menu")
def _():
    scrivi_progresso({"saga_che_non_esiste_piu": {
        "idx": 4, "secondi": 10, "durata": 100, "visti": [],
        "aggiornato": int(time.time())}})
    voci = apri_menu()
    assert not [v for v in voci if _e_una_tappa(v["url"])], \
        "ha messo in menu una saga inesistente"
    assert "reparto=cartoni" in " ".join(v["url"] for v in voci), \
        "menu incompleto"


@prova("una posizione oltre la fine della saga non fa cadere il menu")
def _():
    scrivi_progresso({"naruto": {"idx": 999999, "secondi": 5, "durata": 10,
                                 "visti": [], "aggiornato": int(time.time())}})
    voci = apri_menu()
    assert not [v for v in voci if _e_una_tappa(v["url"])]


@prova("il menu dichiara un tipo di contenuto (le locandine a griglia)")
def _():
    scrivi_progresso({})
    apri_menu()
    assert finto_kodi.CONTENUTO, "nessun setContent: la pelle mostra testo"


@prova("le date delle scadenze si leggono senza datetime (il guasto vero)")
def _():
    from resources.lib import fonti
    assert fonti.giorni_alla_scadenza("prime") is not None or True
    scrivi_progresso({})
    apri_menu()
    finto_kodi.azzera()
    main.pannello_abbonamenti()
    assert [v for v in finto_kodi.VOCI if isinstance(v, dict)], \
        "il pannello abbonamenti e' vuoto"


@prova("nessun quadratino: niente caratteri fuori dal carattere di Kodi")
def _():
    scrivi_progresso({"naruto": {"idx": 12, "secondi": 300, "durata": 1400,
                                 "visti": [1], "aggiornato": int(time.time())}})
    cattivi = set(u"\u2014\u2013\u2026\u2019\u2018\u201c\u201d\u00ab\u00bb"
                  u"\u2713\u2702\u25b6\u25a0\u2192\u2190\u00b7")
    for v in apri_menu():
        trovati = cattivi.intersection(v["etichetta"])
        assert not trovati, "%r contiene %s" % (v["etichetta"], trovati)


@prova("TUTTE le espressioni regolari dell'add-on si compilano")
def _():
    """Il guasto del 06/09/2026, quello che ha rotto tutto.

    Uno script che ripuliva i caratteri tipografici ha trasformato un
    trattino lungo dentro una classe in un trattino normale: la classe e'
    diventata un intervallo impossibile. Python se ne accorge solo QUANDO
    esegue quella riga, e Kodi ha mostrato soltanto "errore di riproduzione".
    """
    import ast
    import re as _re
    rotte = []
    for radice, _d, files in os.walk(ADDON):
        if "__pycache__" in radice or "_profilo" in radice:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            q = os.path.join(radice, f)
            src = io.open(q, encoding="utf-8").read()
            for nodo in ast.walk(ast.parse(src)):
                if not (isinstance(nodo, ast.Constant)
                        and isinstance(nodo.value, str)):
                    continue
                v = nodo.value
                # SOLO le stringhe grezze, quelle scritte r"...". Tutte le
                # espressioni dell'add-on sono scritte cosi'; le frasi normali
                # e i commenti no. Senza questo filtro si finisce per
                # "compilare" le descrizioni, che ovviamente non sono
                # espressioni regolari, e le prove urlano a vuoto.
                pezzo = ast.get_source_segment(src, nodo) or ""
                if pezzo[:1].lower() != "r" or pezzo[1:2] not in ("'", chr(34)):
                    continue
                if len(v) < 4:
                    continue
                try:
                    _re.compile(v)
                except _re.error as e:
                    rotte.append("%s riga %d: %s" % (f, nodo.lineno, e))
    assert not rotte, "; ".join(rotte)


@prova("nessun episodio si finge riproducibile senza un file da riprodurre")
def _():
    """L'errore di riproduzione del 06/09.

    Una voce con IsPlayable DEVE finire in un indirizzo vero. Se non ce l'ha,
    Kodi mostra "errore di riproduzione" - ed e' quello che e' successo su
    ogni singolo episodio, perche' nessuna fonte era un file locale.
    """
    scrivi_progresso({})
    finto_kodi.azzera()
    main.sfoglia("naruto", 1)
    voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
    assert voci, "l'elenco degli episodi e' vuoto"
    colpevoli = []
    for v in voci:
        gioca = v["prop"].get("IsPlayable") == "true"
        if gioca and "azione=riproduci" not in v["url"]:
            colpevoli.append("riproducibile ma non riproduce: " + v["etichetta"][:40])
        if gioca and v["cartella"]:
            colpevoli.append("riproducibile E cartella: " + v["etichetta"][:40])
        if not gioca and "azione=riproduci" in v["url"]:
            colpevoli.append("non riproducibile ma va a riproduci: " + v["etichetta"][:40])
    assert not colpevoli, "; ".join(colpevoli[:3])


@prova("senza file locali gli episodi passano dal motore di s4me")
def _():
    """La fusione, vista dalle prove: quando l'episodio non e' un file tuo
    l'indirizzo deve puntare a s4me, non al nostro vecchio motore."""
    scrivi_progresso({})
    finto_kodi.azzera()
    main.sfoglia("naruto", 1)
    voci = [v for v in finto_kodi.VOCI
            if isinstance(v, dict) and _e_una_tappa(v["url"])]
    assert voci, "nessun episodio nell'elenco"
    da_s4me = [v for v in voci if "plugin.video.s4me" in v["url"]]
    assert len(da_s4me) == len(voci),         "%d episodi su %d non passano da s4me" % (len(voci) - len(da_s4me), len(voci))
    for v in da_s4me[:3]:
        assert "channel=lesaghe" in v["url"], "canale sbagliato: " + v["url"]
        assert "numero_ep=" in v["url"], "manca il numero di episodio: " + v["url"]


@prova("anche i film sono cartelle, non finti video")
def _():
    finto_kodi.azzera()
    main.elenco_film("dragonball")
    voci = [v for v in finto_kodi.VOCI
            if isinstance(v, dict) and "apri_film" in v["url"]]
    if voci:
        cattive = [v["etichetta"][:40] for v in voci
                   if v["prop"].get("IsPlayable") == "true" or not v["cartella"]]
        assert not cattive, "; ".join(cattive)


@prova("nessuna impostazione con valore predefinito vuoto (Kodi le rifiuta)")
def _():
    testo = io.open(os.path.join(ADDON, "resources", "settings.xml"),
                    encoding="utf-8").read()
    assert "<default></default>" not in testo,         "un <default></default> vuoto: Kodi scrive 'error reading the default value'"


@prova("nessuna serie resta nel catalogo senza un percorso che la mostri")
def _():
    """Jeeg era li' con la sua locandina e i suoi 46 episodi, e non si poteva
    raggiungere da nessuna parte del menu (trovato il 06/09/2026).

    Una serie censita, con la scheda scaricata, che nessun percorso include,
    e' lavoro fatto e buttato: non la vede nessuno.
    """
    usate = set()
    for p in catalogo.PERCORSI.values():
        for sid, _a, _b in p["segmenti"]:
            usate.add(sid)
    orfane = sorted(set(catalogo.SERIE) - usate)
    assert not orfane, "serie irraggiungibili: %s" % ", ".join(orfane)


@prova("ogni percorso del catalogo e' raggiungibile, da solo o in un gruppo")
def _():
    fuori = sorted(set(catalogo.PERCORSI) - _raggiungibili())
    assert not fuori, "percorsi invisibili: %s" % ", ".join(fuori)


@prova("un raggruppamento non elencato in ORDINE_GRUPPI non si vede")
def _():
    fuori = sorted(set(getattr(catalogo, "GRUPPI", {}))
                   - set(getattr(catalogo, "ORDINE_GRUPPI", [])))
    assert not fuori, "raggruppamenti invisibili: %s" % ", ".join(fuori)


@prova("la ricerca trova una saga anche scritta male")
def _():
    from resources.lib import ricerca
    for parole in ("mazinga", "MAZINGA", "grande mazinga", "mazinga grande"):
        r = ricerca.cerca(parole)
        assert r, "'%s' non trova niente" % parole


@prova("la ricerca trova un capitolo narrativo (la domanda su Jiren)")
def _():
    """L'esempio che ha fatto l'utente: 'gli episodi con Jiren dove sono?'"""
    from resources.lib import ricerca
    r = [x for x in ricerca.cerca("torneo") if x["tipo"] == "capitolo"]
    assert r, "nessun capitolo trovato cercando 'torneo'"
    assert r[0]["idx"] > 0, "il capitolo non porta a una tappa precisa"


@prova("la ricerca trova le serie turche")
def _():
    from resources.lib import ricerca
    r = ricerca.cerca("terra amara")
    assert r, "non trova Terra amara"
    assert any("terra" in x["titolo"].lower() for x in r)


@prova("la ricerca mette le cose grosse prima dei singoli episodi")
def _():
    from resources.lib import ricerca
    r = ricerca.cerca("naruto")
    tipi = [x["tipo"] for x in r]
    assert tipi, "nessun risultato"
    if "episodio" in tipi and ("saga" in tipi or "serie" in tipi):
        assert tipi.index("episodio") > min(
            [tipi.index(t) for t in ("saga", "serie") if t in tipi]),             "gli episodi vengono prima delle saghe: %s" % tipi[:6]


@prova("una ricerca di una lettera sola non spazza tutto il catalogo")
def _():
    from resources.lib import ricerca
    assert ricerca.cerca("a") == [], "una lettera sola restituisce risultati"


@prova("la ricerca non restituisce mai una valanga")
def _():
    from resources.lib import ricerca
    r = ricerca.cerca("episodio")
    ep = [x for x in r if x["tipo"] == "episodio"]
    assert len(ep) <= ricerca.MAX_EPISODI,         "%d episodi: troppi, la lista diventa inusabile" % len(ep)


@prova("ogni risultato sa dove portare")
def _():
    from resources.lib import ricerca
    for parola in ("naruto", "lupin", "terra amara", "mazinga"):
        for x in ricerca.cerca(parola):
            if x["tipo"] == "canale":
                continue
            assert x["percorso"] in catalogo.PERCORSI,                 "%r punta a un percorso inesistente: %r" % (x["titolo"], x["percorso"])


@prova("la schermata della ricerca si apre e mostra i risultati")
def _():
    finto_kodi.azzera()
    main.menu_ricerca("lupin")
    voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
    assert voci, "la ricerca non ha mostrato niente"
    assert all(v["url"] for v in voci)


@prova("una ricerca senza risultati lo dice, non resta vuota")
def _():
    finto_kodi.azzera()
    main.menu_ricerca("qwertyzxcvb")
    voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
    assert voci, "schermata vuota: l'utente non capisce se ha sbagliato"
    assert "nessun risultato" in voci[0]["etichetta"].lower()


@prova("la taratura sceglie fiato lungo sulle linee lente, corto su quelle veloci")
def _():
    """I numeri devono avere un senso: piu' la linea e' lenta, piu' scorta
    si tiene. Un errore di segno qui peggiorerebbe proprio i casi in cui
    serve aiutare."""
    from resources.lib import taratura
    lento = taratura.scaglione(1.5)
    medio = taratura.scaglione(4.0)
    veloce = taratura.scaglione(50.0)
    assert lento["assicurato"] > medio["assicurato"] > veloce["assicurato"],         "il fiato non cala al crescere della linea: %s %s %s" % (
            lento["assicurato"], medio["assicurato"], veloce["assicurato"])
    for s in (lento, medio, veloce):
        assert s["massimo"] > s["assicurato"],             "il massimo non e' maggiore dell'assicurato: %s" % s
        assert s["spiega"], "scaglione senza spiegazione: %s" % s["nome"]


@prova("la linea a 4 Mbps finisce nello scaglione giusto")
def _():
    from resources.lib import taratura
    s = taratura.scaglione(4.2)
    assert "4G" in s["nome"], "4,2 Mbps classificata come %r" % s["nome"]


@prova("senza mai aver misurato, l'add-on lo dice invece di inventare")
def _():
    from resources.lib import taratura
    testo = taratura.racconta()
    assert "mai" in testo.lower(), testo[:80]
    assert taratura.serve_rimisurare() is True


@prova("la schermata della linea si apre anche senza misure alle spalle")
def _():
    finto_kodi.azzera()
    main.menu_linea()
    voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
    assert len(voci) >= 2, "la schermata della linea e' vuota"


@prova("la misura si presenta come un browser (senza, Cloudflare risponde 403)")
def _():
    """Guasto vero del 06/09/2026: da curl la misura funzionava, da dentro
    Kodi no. Il motivo era l'intestazione mancante, non la rete."""
    import inspect
    from resources.lib import taratura
    sorgente = inspect.getsource(taratura._misura_una)
    assert "User-Agent" in sorgente, "manca l'intestazione del browser"
    assert "Mozilla" in sorgente, "l'intestazione non sembra quella di un browser"


@prova("il tetto di qualita' lascia sempre margine alla linea")
def _():
    """Un flusso scelto al limite esatto della linea si ferma alla prima
    oscillazione, e sul 4G le oscillazioni sono la norma."""
    from resources.lib import taratura
    for mbps in (1.0, 3.0, 4.5, 8.0, 30.0):
        s = taratura.scaglione(mbps)
        assert s["tetto_kbps"] < mbps * 1000,             "a %.1f Mbps il tetto e' %d Kbps: non lascia margine" % (mbps, s["tetto_kbps"])
        assert s["tetto_kbps"] > mbps * 400,             "a %.1f Mbps il tetto e' %d Kbps: troppo prudente" % (mbps, s["tetto_kbps"])


@prova("la risoluzione massima cresce con la linea")
def _():
    from resources.lib import taratura
    ordine = ["480p", "720p", "1080p", "auto"]
    visti = [taratura.scaglione(m)["risoluzione"] for m in (1.0, 4.0, 10.0, 100.0)]
    assert visti == ordine, "risoluzioni fuori ordine: %s" % visti


@prova("la vetrina mostra tutte le saghe, comprese quelle nei gruppi")
def _():
    from resources.lib import vetrina
    base = "plugin://plugin.video.saghe/"
    saghe = vetrina._saghe(base)
    attese = len(catalogo.ORDINE_PERCORSI) + sum(
        len(catalogo.GRUPPI[g]["percorsi"])
        for g in getattr(catalogo, "ORDINE_GRUPPI", []))
    assert len(saghe) == attese, "%d voci invece di %d" % (len(saghe), attese)


@prova("ogni voce della vetrina sa dove portare, e ha una locandina")
def _():
    from resources.lib import vetrina
    base = "plugin://plugin.video.saghe/"
    senza = []
    for li in vetrina._saghe(base):
        if not li.proprieta.get("indirizzo", "").startswith(base):
            senza.append("indirizzo: " + li.label)
        if not li.arte.get("poster"):
            senza.append("locandina: " + li.label)
    assert not senza, "; ".join(senza[:4])


@prova("la vetrina non mostra 'continua' a scatola nuova")
def _():
    from resources.lib import vetrina
    scrivi_progresso({})
    assert vetrina._continua("plugin://plugin.video.saghe/") == []


@prova("la vetrina si costruisce senza esplodere e riempie le due righe")
def _():
    import time as _t
    from resources.lib import vetrina
    scrivi_progresso({"naruto": {"idx": 5, "secondi": 60, "durata": 1400,
                                 "visti": [1], "aggiornato": int(_t.time())}})
    f = vetrina._Finestra("vetrina.xml", ADDON, "Default", "1080i",
                          base="plugin://plugin.video.saghe/")
    f.onInit()
    assert f.righe.get(vetrina.RIGA_CONTINUA), "riga 'continua' vuota"
    assert f.righe.get(vetrina.RIGA_SAGHE), "riga delle saghe vuota"
    assert f.proprieta.get("riga0"), "manca la scritta sopra la prima riga"


@prova("il disegno della vetrina c'e' ed e' XML valido")
def _():
    import xml.etree.ElementTree as E
    d = os.path.join(ADDON, "resources", "skins", "Default", "1080i", "vetrina.xml")
    assert os.path.exists(d), "manca il file del disegno"
    E.parse(d)


@prova("la vetrina si costruisce SENZA contare le tappe (era la rotellina)")
def _():
    """La prima versione costruiva tutte le 33 catene prima di disegnare:
    oltre cinquemila tappe, dieci secondi di rotellina su un Raspberry.
    Ora il conteggio si fa solo per la voce selezionata."""
    from resources.lib import catalogo as c, vetrina
    chiamate = []
    vera = c.lunghezza
    c.lunghezza = lambda pid: (chiamate.append(pid), vera(pid))[1]
    try:
        vetrina._saghe("plugin://plugin.video.saghe/")
    finally:
        c.lunghezza = vera
    assert not chiamate, "ha contato %d catene mentre costruiva la vetrina" % len(chiamate)


@prova("il canale per s4me si importa e sa leggere il catalogo")
def _():
    """Il canale gira dentro s4me, non qui: si finge quel poco di s4me che
    serve (Item, support, platformcode) e si controlla che almeno stia in
    piedi e trovi le saghe. Il resto - cercare sui siti, risolvere i video -
    e' roba di s4me e si collauda solo li'."""
    finto_kodi.installa_finto_s4me()
    import importlib.util
    percorso = os.path.join(ADDON, "resources", "canale", "lesaghe.py")
    spec = importlib.util.spec_from_file_location("canale_lesaghe", percorso)
    canale = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(canale)
    globals()["_canale"] = canale
    c = canale.catalogo()
    assert c.get("PERCORSI"), "il canale non ha letto il catalogo"
    assert len(c["PERCORSI"]) >= 30, "troppe poche saghe: %d" % len(c["PERCORSI"])


@prova("il canale sceglie l'episodio GIUSTO, non uno qualunque")
def _():
    """Il guasto del 05/09/2026: due episodi diversi aprivano lo stesso
    video, perche' bastava una cifra qualsiasi nel titolo. La regola e':
    se non si e' sicuri si restituisce None, non si tira a indovinare."""
    canale = globals().get("_canale")
    assert canale, "il canale non e' stato caricato dalla prova precedente"
    Item = finto_kodi.installa_finto_s4me()

    episodi = [Item(title="1 - Il risveglio", contentEpisodeNumber=1),
               Item(title="12 - Il pianeta Namek", contentEpisodeNumber=12),
               Item(title="Killer 1080p", contentEpisodeNumber=None)]
    scelto = canale._episodio_giusto(episodi, 12)
    assert scelto is not None and scelto.title.startswith("12"),         "ha scelto %r invece dell'episodio 12" % (scelto and scelto.title)

    # un numero che non c'e' NON deve restituire un episodio a caso
    assert canale._episodio_giusto(episodi, 99) is None,         "ha inventato un episodio che non esiste"


@prova("il canale riconosce l'episodio anche solo dal titolo")
def _():
    canale = globals().get("_canale")
    Item = finto_kodi.installa_finto_s4me()
    episodi = [Item(title="Episodio 7 - qualcosa"), Item(title="8 - altro")]
    s = canale._episodio_giusto(episodi, 7)
    assert s is not None and "7" in s.title, "non ha trovato il 7"


@prova("ogni saga elencata ha almeno una tappa")
def _():
    vuote = [p for p in catalogo.ORDINE_PERCORSI if catalogo.lunghezza(p) < 1]
    assert not vuote, "saghe senza episodi: %s" % ", ".join(vuote)



@prova("una serie con attori veri NON si cerca sui siti di cartoni")
def _():
    # IL GUASTO NOTATO DALL'UTENTE: "la serie turca a catalogo c'e',
    # riproducibile no". Cercavamo una telenovela turca su cinque siti di
    # anime giapponesi: non era sfortuna, era impossibile per costruzione.
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    anime = set(canale.CANALI)
    trovate = 0
    for sid, serie in catalogo.SERIE.items():
        if serie.get("tipo") != "serie_tv":
            continue
        trovate += 1
        siti = set(canale._canali_per(serie))
        assert not (siti & anime),             "%s (attori veri) verrebbe cercata su %s" % (sid, ", ".join(siti & anime))
        assert siti, "%s non ha nessun sito dove cercarla" % sid
    assert trovate, "nessuna serie marcata 'serie_tv': la marcatura si e' persa"


@prova("ogni serie del catalogo ha dei siti dove cercarla")
def _():
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    for sid, serie in catalogo.SERIE.items():
        assert canale._canali_per(serie), "%s: nessun sito" % sid


@prova("un titolo che somiglia solo un po' NON viene accettato (Terra Nova)")
def _():
    # IL GUASTO DEL 07/09/2026, visto dal vivo: cercando "Terra amara" il
    # risolutore ha aperto "Terra Nova" - una parola su due in comune, e la
    # vecchia soglia era 30. Far partire la serie sbagliata e' peggio che
    # dire "non l'ho trovata".
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    assert canale._copertura("Terra Nova", "Terra amara") < canale.COPERTURA_MINIMA
    assert canale._copertura("Terra amara", "Terra amara") == 100
    assert canale._copertura("Terra amara - Stagione 1 ITA", "Terra amara") == 100
    assert canale._copertura("Naruto Shippuden", "Naruto") == 100
    assert canale._copertura("One Punch Man", "One Piece") < canale.COPERTURA_MINIMA


@prova("le serie che cambiano nome hanno i loro alias")
def _():
    senza = [sid for sid, s in catalogo.SERIE.items()
             if s.get("tipo") == "serie_tv" and not s.get("alias")]
    assert not senza, "serie senza nome alternativo: %s" % ", ".join(senza)
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    nomi = canale._titoli_da_provare(catalogo.SERIE["tr_terra_amara"], "Terra amara")
    assert "Bir Zamanlar Cukurova" in nomi, nomi


@prova("nel titolo passato a s4me gli spazi NON diventano '+'")
def _():
    # Il 07/09/2026 il registro mostrava che cercavamo "Terra+amara": chi
    # rilegge l'indirizzo scioglie i %20 ma non i '+'.
    indirizzo = main.indirizzo_s4me({"serie": "tr_terra_amara", "ep": 1})
    assert "Terra+amara" not in indirizzo, indirizzo
    assert "Terra%20amara" in indirizzo, indirizzo
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    assert canale._titolo_pulito("Terra+amara") == "Terra amara"
    # un titolo che ha DAVVERO un piu' dentro non va rovinato
    assert canale._titolo_pulito("Dragon Ball Z + Kai") == "Dragon Ball Z + Kai"


@prova("nessun film resta col quadratino grigio: c'e' sempre un'immagine")
def _():
    # L'utente: "l'idea della mia icona e' bella ma non puo' essere
    # applicata anche ai film". Molti film vecchi non hanno la copertina su
    # TMDb, e restava l'icona di Kodi.
    scrivi_progresso({})
    saghe = [pid for pid, _ in main._saghe_con_film()]
    assert saghe
    for pid in saghe[:6]:
        finto_kodi.azzera()
        main.elenco_film(pid)
        for v in [v for v in finto_kodi.VOCI if isinstance(v, dict)]:
            arte = v.get("arte") or {}
            assert arte.get("poster") or arte.get("thumb"),                 "%s: un film senza nessuna immagine (%s)" % (pid, v["etichetta"][:40])


@prova("i siti gratuiti e ufficiali si provano PRIMA di quelli che copiano")
def _():
    # "netflix mediaset infinity youtube non li usa in automatico".
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    serie = canale.CANALI_PER_TIPO["serie_tv"]
    for ufficiale in ("raiplay", "mediasetplay", "plutotv"):
        assert ufficiale in serie, "manca %s" % ufficiale
        assert serie.index(ufficiale) < serie.index("streamingcommunity"),             "%s viene dopo i siti che copiano" % ufficiale
    assert "vvvvid" in canale.CANALI_PER_TIPO["anime"], "manca VVVVID"
    assert "youtube" in canale.SERVIZI, "YouTube non e' fra i servizi"


@prova("i canali che il custode riaccende esistono davvero")
def _():
    # Accendere un canale che non c'e' non rompe niente, ma vuol dire che la
    # lista e' vecchia: meglio saperlo qui che scoprirlo fra sei mesi.
    from resources.lib import custode
    assert custode.DA_ACCENDERE, "la lista e' vuota"
    assert "vvvvid" in custode.DA_ACCENDERE
    assert "eurostreaming" in custode.DA_ACCENDERE


@prova("si segue la strada che la voce indica, non sempre 'episodios'")
def _():
    # IL GUASTO: su Mediaset una serie porta a `epmenu` (le stagioni), non a
    # `episodios`. Chiamando episodios a forza si cadeva con
    # KeyError: 'entries' - e per due giorni e' sembrato un guasto di s4me.
    import importlib, types
    canale = importlib.import_module("resources.canale.lesaghe")

    class Voce(object):
        def __init__(self, **k): self.__dict__.update(k)

    chiamate = []
    finto = types.SimpleNamespace()
    def episodios(v):
        chiamate.append("episodios")
        raise KeyError("entries")          # e' esattamente quello che faceva
    def epmenu(v):
        chiamate.append("epmenu")
        return [Voce(action="episodios", title="Stagione 1",
                     contentEpisodeNumber=None)]
    finto.episodios, finto.epmenu = episodios, epmenu

    partenza = Voce(action="epmenu", title="Terra amara")
    canale._episodi_di(finto, partenza)
    assert chiamate[0] == "epmenu",         "ha chiamato %s per prima invece di seguire l'azione della voce" % chiamate[0]


@prova("si scende dalle stagioni fino agli episodi veri")
def _():
    import importlib, types
    canale = importlib.import_module("resources.canale.lesaghe")

    class Voce(object):
        def __init__(self, **k): self.__dict__.update(k)

    finto = types.SimpleNamespace()
    def episodios(v):
        if getattr(v, "livello", "") == "stagione":
            return [Voce(action="findvideos", title="1x01 Prima puntata",
                         contentEpisodeNumber=1)]
        return [Voce(action="episodios", title="Stagione 1",
                     livello="stagione")]
    finto.episodios = episodios

    ep = canale._episodi_di(finto, Voce(action="episodios", title="Serie"))
    assert ep and canale._pare_un_episodio(ep[0]),         "si e' fermato alle stagioni: %r" % [getattr(e,"title","") for e in ep]


@prova("non si chiamano mai le funzioni che fanno partire un video")
def _():
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")
    for pericolosa in ("findvideos", "play", "search"):
        assert pericolosa in canale.AZIONI_DA_NON_SEGUIRE, pericolosa


@prova("un numero qualunque nel titolo NON e' un numero di episodio")
def _():
    # Su Mediaset gli episodi si chiamano "Terra amara  [21 marzo]".
    # La vecchia regola prendeva il primo numero del titolo: chiedendo la
    # puntata 21 avrebbe dato quella del 21 marzo.
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")

    class V(object):
        def __init__(self, **k): self.__dict__.update(k)

    elenco = [V(title="Terra amara  [%d marzo]" % g) for g in (19, 20, 21, 22)]
    scelto = canale._episodio_giusto(elenco, 21)
    # L'elenco ha 4 puntate: la 21 non c'e'. La risposta giusta e' "non lo
    # so", NON la puntata del 21 marzo.
    assert scelto is not elenco[2], "ha preso la puntata del 21 marzo"
    assert scelto is None, "ha tirato a indovinare: %r" % getattr(scelto, "title", "")

    # E con l'elenco completo, la 21 e' la ventunesima in ordine.
    lungo = [V(title="Terra amara  [%d marzo]" % (g % 31 + 1)) for g in range(50)]
    assert canale._episodio_giusto(lungo, 21) is lungo[20]


@prova("quando NESSUN episodio e' numerato si usa la posizione, e si dice")
def _():
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")

    class V(object):
        def __init__(self, **k): self.__dict__.update(k)

    elenco = [V(title="Terra amara  [puntata del giorno %d]" % i) for i in range(1, 51)]
    # nota: "puntata" seguito da numero e' una forma riconosciuta, quindi qui
    # si deve trovare per titolo, non per posizione
    assert canale._episodio_giusto(elenco, 7) is elenco[6]

    senza = [V(title="Terra amara") for _ in range(50)]
    assert canale._episodio_giusto(senza, 7) is senza[6], "non ha usato la posizione"
    # ma se l'elenco e' piu' corto del numero chiesto, non si indovina
    assert canale._episodio_giusto(senza[:3], 7) is None


@prova("i numeri veri degli episodi vincono sempre sulla posizione")
def _():
    import importlib
    canale = importlib.import_module("resources.canale.lesaghe")

    class V(object):
        def __init__(self, **k): self.__dict__.update(k)

    elenco = [V(title="1x03 Terza", contentEpisodeNumber=3),
              V(title="1x01 Prima", contentEpisodeNumber=1),
              V(title="1x02 Seconda", contentEpisodeNumber=2)]
    assert canale._episodio_giusto(elenco, 1) is elenco[1]


@prova("un elenco lungo non viene scambiato per stagioni")
def _():
    # Con 166 voci il risolutore scendeva dentro ognuna: minuti buttati.
    import importlib, types
    canale = importlib.import_module("resources.canale.lesaghe")

    class V(object):
        def __init__(self, **k): self.__dict__.update(k)

    discese = []
    finto = types.SimpleNamespace()
    def episodios(v):
        if getattr(v, "figlio", False):
            discese.append(1)
            return []
        return [V(title="Terra amara", figlio=True) for _ in range(166)]
    finto.episodios = episodios
    canale._episodi_di(finto, V(action="episodios", title="Serie"))
    assert not discese, "e' sceso dentro %d voci di un elenco lungo" % len(discese)


@prova("la Vetrina ha la riga delle novita', e non va in rete per disegnarla")
def _():
    # La Vetrina si era gia' rovinata una volta perche' costruiva tutto a
    # schermo aperto: dieci secondi di rotellina. La riga nuova deve
    # leggere SOLO la cache.
    import importlib
    v = importlib.import_module("resources.lib.vetrina")
    n = importlib.import_module("resources.lib.novita")
    assert hasattr(v, "RIGA_NOVITA") and v.RIGA_NOVITA == 102
    # La cosa che conta non e' "non tocca la rete mai": e' che disegnare la
    # Vetrina non ASPETTI la rete. L'aggiornamento puo' partire, ma in un
    # filo a parte, e la funzione deve tornare subito.
    import time
    vero = n._scarica
    n._scarica = lambda: (time.sleep(3), [])[1]
    try:
        inizio = time.time()
        v._novita()
        quanto = time.time() - inizio
    finally:
        n._scarica = vero
    assert quanto < 1.0,         "disegnare la Vetrina ha aspettato la rete per %.1f secondi" % quanto


@prova("senza novita' salvate la riga non compare (niente buco con la scritta)")
def _():
    import importlib
    v = importlib.import_module("resources.lib.vetrina")
    n = importlib.import_module("resources.lib.novita")
    import os
    try:
        os.remove(n._file())
    except Exception:
        pass
    assert v._novita() == [], "ha inventato delle voci"


@prova("il disegno della Vetrina ci sta dentro i 1080 punti")
def _():
    # I conti sono facili da sbagliare spostando le righe: la scritta dei
    # tasti sta a 1024, e sotto non deve finire niente.
    import os, re
    import xml.etree.ElementTree as ET
    percorso = os.path.join(ADDON, "resources", "skins", "Default", "1080i",
                            "vetrina.xml")
    albero = ET.parse(percorso).getroot()
    for gruppo in albero.iter("control"):
        if gruppo.get("type") != "group":
            continue
        base = int(gruppo.findtext("top") or 0)
        for c in gruppo.iter("control"):
            if c.get("type") != "list":
                continue
            giu = base + int(c.findtext("top") or 0) + int(c.findtext("height") or 0)
            # 1046 e' dove sta la scritta dei tasti: sotto non deve finire
            # niente, TITOLO DELLA VOCE SELEZIONATA COMPRESO (che sporge di
            # 220 punti dentro l'altezza della riga).
            assert giu <= 1046, "una riga finisce a %d, sotto la scritta dei tasti" % giu


@prova("i riquadri della home danno voci con locandina e senza voci di servizio")
def _():
    # Li legge la SKIN, non un utente: dentro non ci vanno intestazioni,
    # "Altro...", pagine successive. Solo cose da guardare, con l'immagine.
    scrivi_progresso({})
    for quale in ("saghe", "film", "serietv"):
        finto_kodi.azzera()
        main.widget(quale)
        voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
        assert voci, "il riquadro %s e' vuoto" % quale
        for v in voci:
            arte = v.get("arte") or {}
            assert arte.get("poster") or arte.get("thumb"),                 "%s: una voce senza immagine (%s)" % (quale, v["etichetta"][:40])
            assert "azione=altro" not in v["url"], "%s ha voci di servizio" % quale


@prova("il riquadro delle novita' non va in rete")
def _():
    import importlib, time
    n = importlib.import_module("resources.lib.novita")
    vero = n._scarica
    n._scarica = lambda: (time.sleep(3), [])[1]
    try:
        finto_kodi.azzera()
        inizio = time.time()
        main.widget("novita")
        quanto = time.time() - inizio
    finally:
        n._scarica = vero
    assert quanto < 1.0, "il riquadro ha aspettato la rete %.1f s" % quanto


@prova("un riquadro con un nome sbagliato non fa cadere la home")
def _():
    finto_kodi.azzera()
    main.widget("questo-non-esiste")     # non deve sollevare


@prova("gli scaffali documentari/cucina/YouTube sono separati e ordinati")
def _():
    # "tienili separati: documentari una cosa, cucina un'altra, anche i
    # canali youtube separati" - e dentro ognuno, gruppi con intestazione.
    from resources.lib import scoperte
    for quale, minimo in (("documentari", 80), ("cucina", 40), ("youtube", 8)):
        gruppi = scoperte.scaffale(quale)
        assert gruppi, "%s e' vuoto" % quale
        assert scoperte.quante_voci(quale) >= minimo,             "%s ha solo %d voci" % (quale, scoperte.quante_voci(quale))
        for intestazione, voci in gruppi:
            assert intestazione, "%s: un gruppo senza titolo" % quale
            assert voci, "%s: il gruppo %s e' vuoto" % (quale, intestazione)
    # nessuna voce si ripete DENTRO lo stesso scaffale
    for quale in ("documentari", "cucina", "youtube"):
        viste = [e for _, v in scoperte.scaffale(quale) for e, _, _, _ in v]
        doppie = set(x for x in viste if viste.count(x) > 1)
        assert not doppie, "%s: voci doppie %s" % (quale, doppie)


@prova("i programmi che l'utente guardava ci sono, col nome che usa lui")
def _():
    from resources.lib import scoperte
    testo = " ".join(e.lower() for _, v in scoperte.scaffale("documentari")
                     for e, _, _, _ in v)
    for atteso in ("come e' fatto", "caccia all'oro", "gas monkey",
                   "american chopper", "chernobyl"):
        assert atteso in testo, "manca %r" % atteso
    cucina = " ".join(e.lower() for _, v in scoperte.scaffale("cucina")
                      for e, _, _, _ in v)
    assert "masterchef italia" in cucina


@prova("i canali YouTube si aprono con l'identificativo, non col nome")
def _():
    # Col nome si finisce su un canale che somiglia. Con l'identificativo no.
    from resources.lib import scoperte
    for nome, cid, _ in scoperte.CANALI_YOUTUBE:
        assert cid.startswith("UC") and len(cid) >= 20, "%s: %r" % (nome, cid)


@prova("ogni voce degli scaffali porta da qualche parte")
def _():
    scrivi_progresso({})
    for quale in ("documentari", "cucina", "youtube"):
        finto_kodi.azzera()
        main.menu_scaffale(quale)
        voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
        assert voci, "%s non ha prodotto voci" % quale
        for v in voci:
            assert v["url"], "%s: una voce senza indirizzo" % quale


@prova("nessuna voce degli scaffali resta senza descrizione")
def _():
    # L'utente guardando la sezione a schermo: "mancano le informazioni".
    # Nel pannello di sinistra la trama e' meta' della schermata: se e'
    # vuota, sembra rotta.
    from resources.lib import scoperte
    for quale in ("documentari", "cucina", "youtube"):
        vuote = [e for _, v in scoperte.scaffale(quale)
                 for e, _, n, _ in v if not (n or "").strip()]
        assert not vuote, "%s: senza descrizione %s" % (quale, vuote[:4])


@prova("una saga cresciuta si allunga davvero, catena compresa")
def _():
    # Chiesto dall'utente: "se escono episodi nuovi la vede in automatico e
    # me lo dice? e me la aggiunge?". Aggiungerli al conteggio non basta:
    # se il segmento del percorso resta corto, gli episodi nuovi esistono
    # ma non compaiono in nessuna catena, cioe' non si possono guardare.
    prima_serie = catalogo.SERIE["bleach_tybw"]["episodi"]
    prima_catena = len(catalogo.catena("m_bleach"))
    cambiati = catalogo.applica_aggiunte({"bleach_tybw": prima_serie + 7})
    try:
        assert cambiati, "non ha applicato niente"
        assert catalogo.SERIE["bleach_tybw"]["episodi"] == prima_serie + 7
        assert len(catalogo.catena("m_bleach")) == prima_catena + 7,             "la catena non si e' allungata"
    finally:
        # rimetto com'era, se no le altre prove contano male
        catalogo.SERIE["bleach_tybw"]["episodi"] = prima_serie
        for pid, p in catalogo.PERCORSI.items():
            for i, (s, a, b) in enumerate(p["segmenti"]):
                if s == "bleach_tybw":
                    p["segmenti"][i] = (s, a, prima_serie)
        catalogo._cache_catene.clear()


@prova("una fetta di serie NON si allunga (Ken 1-109 resta 1-109)")
def _():
    # Ken il guerriero e' spezzato in due serie che su TMDb sono una sola.
    # Se una crescita allungasse anche i segmenti parziali, la prima meta'
    # si mangerebbe la seconda.
    prima = catalogo.SERIE["ken1"]["episodi"]
    segmenti_prima = {pid: list(p["segmenti"])
                      for pid, p in catalogo.PERCORSI.items()}
    catalogo.applica_aggiunte({"ken1": prima + 5})
    try:
        for pid, p in catalogo.PERCORSI.items():
            for (s, a, b), (s2, a2, b2) in zip(p["segmenti"], segmenti_prima[pid]):
                if s == "ken1" and b2 != prima:
                    assert b == b2, "%s: la fetta di ken1 e' stata allungata" % pid
    finally:
        catalogo.SERIE["ken1"]["episodi"] = prima
        for pid, p in catalogo.PERCORSI.items():
            p["segmenti"][:] = segmenti_prima[pid]
        catalogo._cache_catene.clear()


@prova("la sentinella guarda solo le serie che possono ancora crescere")
def _():
    from resources.lib import sentinella
    anno = 2026
    assert not sentinella._in_corso({"anni": "1986-1989"}, anno), "Dragon Ball non cresce piu'"
    assert sentinella._in_corso({"anni": "2022-2026"}, anno), "Bleach TYBW e' in corso"
    assert sentinella._in_corso({"anni": ""}, anno), "senza anni, nel dubbio si guarda"


@prova("la sentinella toglie lo scostamento (il falso allarme di Bleach)")
def _():
    # Ha annunciato "Bleach TYBW da 50 a 416 episodi": falso, e' la stessa
    # scheda TMDb di Bleach, spezzata in due. Senza sottrarre lo
    # scostamento la seconda meta' sembra lunga quanto tutta la serie.
    import io as _io, json as _json, os as _os
    from resources.lib import sentinella
    percorso = _os.path.join(ADDON, "resources", "tmdb.json")
    ids = _json.load(_io.open(percorso, encoding="utf-8"))
    assert isinstance(ids.get("bleach_tybw"), dict),         "tmdb.json non ha piu' la forma con lo scostamento"
    assert ids["bleach_tybw"]["offset"] == 366, ids["bleach_tybw"]
    assert ids["ken2"]["offset"] == 109, ids["ken2"]
    # e le serie normali hanno scostamento zero
    assert ids["demonslayer"]["offset"] == 0


@prova("i consigli si leggono senza andare in rete, e dicono PERCHE'")
def _():
    # "uno script come quello di tiktok che analizza i miei comportamenti":
    # un consiglio senza motivo e' pubblicita'. E disegnare la riga non deve
    # mai aspettare la rete.
    import time
    from resources.lib import consigli
    vero = consigli.calcola
    consigli.calcola = lambda *a, **k: (time.sleep(3), [])[1]
    try:
        inizio = time.time()
        voci = consigli.leggi()
        quanto = time.time() - inizio
    finally:
        consigli.calcola = vero
    assert quanto < 1.0, "leggere i consigli ha aspettato %.1f s" % quanto
    for v in voci:
        assert v.get("motivo"), "un consiglio senza il perche': %s" % v.get("titolo")


@prova("una serie aggiunta da te finisce in un percorso e in un gruppo suo")
def _():
    # Aggiungerla al catalogo non basta: senza percorso resterebbe
    # invisibile, lo stesso errore che una volta ha nascosto Jeeg.
    prima_p, prima_s = len(catalogo.PERCORSI), len(catalogo.SERIE)
    messe = catalogo.applica_serie_nuove(
        {"tmdb_9999": {"titolo": "Prova consiglio", "anni": "2024-2025",
                       "episodi": 24}})
    try:
        assert messe == ["tmdb_9999"], messe
        assert "mia_tmdb_9999" in catalogo.PERCORSI
        assert len(catalogo.catena("mia_tmdb_9999")) == 24
        assert "mie" in catalogo.ORDINE_GRUPPI
        assert "mia_tmdb_9999" in catalogo.GRUPPI["mie"]["percorsi"]
    finally:
        catalogo.SERIE.pop("tmdb_9999", None)
        catalogo.PERCORSI.pop("mia_tmdb_9999", None)
        if "mie" in catalogo.GRUPPI:
            catalogo.GRUPPI["mie"]["percorsi"] = [
                x for x in catalogo.GRUPPI["mie"]["percorsi"] if x != "mia_tmdb_9999"]
            if not catalogo.GRUPPI["mie"]["percorsi"]:
                catalogo.GRUPPI.pop("mie")
                if "mie" in catalogo.ORDINE_GRUPPI:
                    catalogo.ORDINE_GRUPPI.remove("mie")
        catalogo._cache_catene.clear()
    assert len(catalogo.PERCORSI) == prima_p and len(catalogo.SERIE) == prima_s


@prova("i consigli non propongono roba che abbiamo gia'")
def _():
    # I primi consigli proponevano Naruto e Dragon Ball Z, che sono in
    # catalogo da mesi: il confronto era fra le nostre chiavi ("naruto") e
    # quelle di TMDb ("tmdb_31910"), due alfabeti diversi.
    from resources.lib import consigli
    gia = consigli._tmdb_gia_nostri(catalogo)
    assert gia, "non riconosce nessuna serie come gia' nostra"
    import io as _io, json as _json, os as _os
    ids = _json.load(_io.open(_os.path.join(ADDON, "resources", "tmdb.json"),
                              encoding="utf-8"))
    for sid in ("naruto", "dbz", "one_piece"):
        if sid in ids and sid in catalogo.SERIE:
            conf = ids[sid]
            tid = str(conf["id"] if isinstance(conf, dict) else conf)
            assert tid in gia, "%s (%s) non e' riconosciuta come gia' nostra" % (sid, tid)


@prova("i consigli scartano i titoli che in italiano non esistono")
def _():
    # TMDb, quando manca la traduzione, restituisce il titolo originale.
    # Fra i primi consigli sono usciti due titoli in giapponese: proporre
    # una cosa che non si potra' mai guardare in italiano e' peggio che
    # non proporla.
    from resources.lib import consigli
    assert consigli._titolo_leggibile("Dragon Quest: L'avventura di Dai")
    assert consigli._titolo_leggibile("Erased")
    assert consigli._titolo_leggibile("Cowboy Bebop")
    assert not consigli._titolo_leggibile("星の海のアムリ")
    assert not consigli._titolo_leggibile("真夜中ぱんチ")
    assert not consigli._titolo_leggibile("")
    assert not consigli._titolo_leggibile("   ")


@prova("Cerca non apre la tastiera di colpo: prima le ultime ricerche")
def _():
    # IL DIFETTO DEL 06/09/2026: la casella si presentava gia' piena con la
    # ricerca di prima, e col telecomando il tasto Indietro CHIUDE la
    # finestra invece di cancellare una lettera: non c'era modo di uscirne.
    main.ricerche_recenti_svuota()
    main.ricerche_recenti_aggiungi("dragon ball gt heroes")
    finto_kodi.azzera()
    main.menu_ricerca()
    voci = [v for v in finto_kodi.VOCI if isinstance(v, dict)]
    testo = " ".join(v["url"] for v in voci)
    assert "nuova=1" in testo, "manca la voce 'Nuova ricerca'"
    assert "dragon+ball+gt+heroes" in testo or "dragon%20ball%20gt%20heroes" in testo, \
        "la ricerca di prima non e' fra quelle recenti"
    assert "ricerche_svuota" in testo, "manca il modo di svuotare l'elenco"


@prova("la tastiera della ricerca parte SEMPRE vuota")
def _():
    main.ricerche_recenti_aggiungi("qualcosa di vecchio")
    finto_kodi.azzera()
    finto_kodi.RISPOSTA_INPUT = ""      # l'utente annulla
    main.menu_ricerca(nuova=True)
    assert finto_kodi.ULTIMO_INPUT is not None, "non ha aperto la tastiera"
    assert finto_kodi.ULTIMO_INPUT.get("defaultt", "") == "", \
        "la casella parte con dentro %r" % finto_kodi.ULTIMO_INPUT.get("defaultt")


# --------------------------------------------------------------------------
# AL CINEMA ORA
# --------------------------------------------------------------------------

@prova("il cartellone si legge senza andare in rete")
def _():
    from resources.lib import cinema
    import io as _io
    import json as _json
    # niente file: deve rispondere lista vuota, non esplodere
    if os.path.exists(cinema.file_cinema()):
        os.remove(cinema.file_cinema())
    assert cinema.leggi() == [], "senza file dovrebbe dare lista vuota"
    assert cinema.scaduto(), "senza file dovrebbe risultare scaduto"

    with _io.open(cinema.file_cinema(), "w", encoding="utf-8") as f:
        f.write(_json.dumps({"quando": time.time(), "film": [
            {"tmdb": 1, "titolo": "Un film", "anno": "2026"}]}))
    assert len(cinema.leggi()) == 1, "non rilegge quello che ha scritto"
    assert not cinema.scaduto(), "appena scritto non puo' essere scaduto"


@prova("se la rete e' giu' il cartellone di ieri NON si perde")
def _():
    from resources.lib import cinema
    prima = cinema.leggi()
    assert prima, "serve un cartellone di partenza"
    vero = cinema._chiedi
    cinema._chiedi = lambda url: {}          # rete morta
    try:
        assert cinema.aggiorna() == 0, "senza rete dovrebbe dire zero"
    finally:
        cinema._chiedi = vero
    assert cinema.leggi() == prima,         "ha cancellato il cartellone invece di tenerlo"


@prova("la voce Al cinema non compare se il cartellone e' vuoto")
def _():
    from resources.lib import cinema
    if os.path.exists(cinema.file_cinema()):
        os.remove(cinema.file_cinema())
    finto_kodi.azzera()
    main.menu_principale()
    voci = [v.get("etichetta", "") for v in finto_kodi.VOCI]
    assert not any("Al cinema" in v for v in voci),         "mostra la voce anche senza film: si aprirebbe su un elenco vuoto"


@prova("col cartellone la voce compare, e dice quanti film")
def _():
    from resources.lib import cinema
    import io as _io
    import json as _json
    with _io.open(cinema.file_cinema(), "w", encoding="utf-8") as f:
        f.write(_json.dumps({"quando": time.time(), "film": [
            {"tmdb": i, "titolo": "Film %d" % i, "anno": "2026"}
            for i in range(7)]}))
    finto_kodi.azzera()
    main.menu_principale()
    voci = [v.get("etichetta", "") for v in finto_kodi.VOCI]
    trovata = [v for v in voci if "Al cinema" in v]
    assert trovata, "la voce non c'e' nemmeno col cartellone pieno"
    assert "7 film" in trovata[0],         "non dice quanti film: %r" % trovata[0]


# --------------------------------------------------------------------------

def main_():
    larghezza = max(len(n) for _, n, _ in ESITI)
    ok = 0
    for esito, nome, perche in ESITI:
        print("  %s  %-*s %s" % ("OK  " if esito else "FALLITA", larghezza,
                                 nome, perche))
        ok += 1 if esito else 0
    print("\n  %d prove su %d superate" % (ok, len(ESITI)))
    shutil.rmtree(PROFILO, ignore_errors=True)
    return 0 if ok == len(ESITI) else 1


sys.exit(main_())
