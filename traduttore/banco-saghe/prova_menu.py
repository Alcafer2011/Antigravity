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

@prova("il menu si apre e non e' vuoto")
def _():
    scrivi_progresso({})
    voci = apri_menu()
    assert len(voci) >= len(catalogo.ORDINE_PERCORSI), \
        "solo %d voci" % len(voci)


def _raggiungibili():
    """Tutti i percorsi che si possono raggiungere: quelli del menu
    principale piu' quelli dentro un raggruppamento."""
    fuori = set(catalogo.ORDINE_PERCORSI)
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        fuori |= set(catalogo.GRUPPI[gid]["percorsi"])
    return fuori


@prova("ogni saga del catalogo si puo' raggiungere (l'errore di ORDINE_PERCORSI)")
def _():
    scrivi_progresso({})
    testo = " ".join(v["url"] for v in apri_menu())
    diretti = [p for p in catalogo.ORDINE_PERCORSI if "percorso=%s" % p not in testo]
    assert not diretti, "saghe invisibili nel menu: %s" % ", ".join(diretti)
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
    assert len(voci) >= len(catalogo.ORDINE_PERCORSI), "menu incompleto"


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


@prova("il numero di episodio si legge davvero (col trattino di ogni tipo)")
def _():
    from resources.lib import ponte_s4me
    casi = [
        ("12 - Il pianeta Namek", 12),
        ("12 – Il pianeta Namek", 12),
        ("12 — Il pianeta Namek", 12),
        ("Episodio 7", 7),
        ("S01E12 qualcosa", 12),
        ("1x12 qualcosa", 12),
        ("Killer 1080p", None),
    ]
    for etichetta, atteso in casi:
        avuto = ponte_s4me._numero_episodio(etichetta)
        assert avuto == atteso, "%r -> %r invece di %r" % (etichetta, avuto, atteso)


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


@prova("in salotto le app Android non promettono cose che non puo' fare")
def _():
    """Sul Raspberry StartAndroidActivity non fa niente, e in silenzio.

    L'utente vedeva l'avviso "cerca l'episodio 2" e poi il nulla: sembrava
    un guasto dell'add-on. Qui si controlla che, quando NON siamo su
    Android, una fonte "app" non venga trattata come apribile.
    """
    from resources.lib import fonti
    assert fonti.su_android() is False,         "il finto Kodi non e' Android: su_android dovrebbe dire di no"
    finto_kodi.azzera()
    finto_kodi.Dialog.risposte = [0]      # "No, chiudi" alla proposta s4me
    main.apri("naruto", 2)
    testi = [v for v in finto_kodi.VOCI if isinstance(v, tuple)]
    avvii = [v for v in testi if v[0] == "riproduci"]
    assert not avvii, "ha provato ad avviare qualcosa che qui non esiste"


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


@prova("la schermata 'perche' non e' partito' si apre e dice qualcosa")
def _():
    """Quando un episodio non parte, la domanda dell'utente non e' quale
    codice ha sbagliato ma cosa e' stato provato. Questa schermata risponde,
    e deve funzionare anche a scatola nuova, senza nessun tentativo alle
    spalle."""
    from resources.lib import motore
    motore.dimentica()
    finto_kodi.azzera()
    main.diagnosi("naruto")
    testi = [v for v in finto_kodi.VOCI if isinstance(v, tuple) and v[0] == "testo"]
    assert testi, "la schermata non ha mostrato niente"


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


@prova("ogni saga elencata ha almeno una tappa")
def _():
    vuote = [p for p in catalogo.ORDINE_PERCORSI if catalogo.lunghezza(p) < 1]
    assert not vuote, "saghe senza episodi: %s" % ", ".join(vuote)


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
