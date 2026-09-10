# -*- coding: utf-8 -*-
"""
Memoria della posizione.

Due livelli, perche' le fonti sono di due nature diverse e prometterne una
sola sarebbe una bugia:

 - Riproduzione DENTRO Kodi (file locali, YouTube, Pluto): si registra il
    secondo esatto. Riprende come Netflix.
 - Riproduzione in un'APP Android (Netflix, Prime, Disney+, Crunchyroll):
    Kodi non ha alcun modo di sapere a che minuto sei arrivato, perche' il
    video non passa da lui. Si registra allora la tappa, e al rientro si
    chiede se l'episodio e' stato finito.

Lo stato vive in addon_data e non dipende dalla libreria di Kodi.
"""

import json
import os
import time

import xbmcvfs
import xbmcaddon

ADDON = xbmcaddon.Addon()
_CARTELLA = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
_FILE = os.path.join(_CARTELLA, "progresso.json")

# Oltre questa frazione di episodio si considera visto e si avanza da soli.
SOGLIA_COMPLETATO = 0.90


def _assicura_cartella():
    if not xbmcvfs.exists(_CARTELLA):
        xbmcvfs.mkdirs(_CARTELLA)


def _leggi_locale():
    _assicura_cartella()
    if not os.path.exists(_FILE):
        return {}
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        # File corrotto: meglio ripartire che bloccare l'addon.
        return {}


def _leggi():
    """Il registro locale, arricchito con quello comune del Raspberry.

    Se il quaderno comune non risponde (Raspberry spento, rete giu') si va
    avanti col locale: la sincronizzazione non deve MAI impedire di guardare
    un episodio.
    """
    locale = _leggi_locale()
    try:
        import sincro
        unito = sincro.unisci_da_remoto(locale)
        if unito != locale:
            _scrivi_locale(unito)
        return unito
    except Exception:
        return locale


def _scrivi_locale(dati):
    _assicura_cartella()
    tmp = _FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _FILE)
    except OSError:
        pass


def _scrivi(dati):
    """Salva qui E manda al quaderno comune, cosi' l'altro apparecchio lo sa."""
    _scrivi_locale(dati)
    try:
        import sincro
        unito = sincro.manda(dati)
        if unito and unito != dati:
            _scrivi_locale(unito)
    except Exception:
        pass


def _stato_percorso(dati, percorso_id):
    return dati.setdefault(percorso_id, {
        "idx": 1,
        "secondi": 0,
        "durata": 0,
        "visti": [],
        "aggiornato": 0,
    })


# --------------------------------------------------------------------------
# Lettura
# --------------------------------------------------------------------------

def posizione(percorso_id):
    """Tappa corrente (1-based) del percorso."""
    return int(_stato_percorso(_leggi(), percorso_id)["idx"])


def ripresa(percorso_id):
    """(secondi, durata) della tappa corrente. (0, 0) se si parte da capo."""
    s = _stato_percorso(_leggi(), percorso_id)
    return int(s.get("secondi", 0)), int(s.get("durata", 0))


def tutte():
    """Lo stato di TUTTI i percorsi toccati. Serve ai consigli.

    I consigli si basano su cosa guardi davvero: quali saghe hai aperto e
    quanti episodi hai visto. Quel dato e' gia' tutto qui dentro, non serve
    spiare niente d'altro.
    """
    try:
        return dict(_leggi())
    except Exception:
        return {}


def visti(percorso_id):
    return set(_stato_percorso(_leggi(), percorso_id).get("visti", []))


def e_visto(percorso_id, idx):
    return idx in visti(percorso_id)


def percentuale(percorso_id, totale):
    """Quanta parte del percorso e' stata vista, 0-100."""
    if totale <= 0:
        return 0
    return int(round(100.0 * len(visti(percorso_id)) / totale))


# --------------------------------------------------------------------------
# Scrittura
# --------------------------------------------------------------------------

def vai_a(percorso_id, idx):
    """Sposta la posizione senza toccare i visti (es. l'utente salta avanti)."""
    dati = _leggi()
    s = _stato_percorso(dati, percorso_id)
    if int(s["idx"]) != int(idx):
        s["secondi"] = 0
        s["durata"] = 0
    s["idx"] = int(idx)
    s["aggiornato"] = int(time.time())
    _scrivi(dati)


def salva_minuto(percorso_id, idx, secondi, durata):
    """Registra il punto esatto. Chiamata dal servizio durante la riproduzione."""
    dati = _leggi()
    s = _stato_percorso(dati, percorso_id)
    s["idx"] = int(idx)
    s["secondi"] = int(secondi)
    s["durata"] = int(durata)
    s["aggiornato"] = int(time.time())
    _scrivi(dati)


def segna_visto(percorso_id, idx, avanza=True, massimo=None):
    """Marca la tappa come vista e, se richiesto, passa alla successiva."""
    dati = _leggi()
    s = _stato_percorso(dati, percorso_id)
    idx = int(idx)

    elenco = s.setdefault("visti", [])
    if idx not in elenco:
        elenco.append(idx)
        elenco.sort()

    if avanza:
        prossima = idx + 1
        if massimo is not None and prossima > massimo:
            prossima = massimo
        s["idx"] = prossima
    s["secondi"] = 0
    s["durata"] = 0
    s["aggiornato"] = int(time.time())
    _scrivi(dati)


def togli_visto(percorso_id, idx):
    dati = _leggi()
    s = _stato_percorso(dati, percorso_id)
    elenco = s.setdefault("visti", [])
    if int(idx) in elenco:
        elenco.remove(int(idx))
    _scrivi(dati)


def azzera(percorso_id):
    dati = _leggi()
    dati[percorso_id] = {
        "idx": 1, "secondi": 0, "durata": 0, "visti": [],
        "aggiornato": int(time.time()),
    }
    _scrivi(dati)


# --------------------------------------------------------------------------
# Sessione corrente: il ponte fra il plugin e il servizio.
# Il plugin scrive qui cosa sta per partire, il servizio legge e segue.
# --------------------------------------------------------------------------

_FILE_SESSIONE = os.path.join(_CARTELLA, "sessione.json")


def apri_sessione(percorso_id, idx, dentro_kodi, atteso="", file_atteso=""):
    """Registra cosa sta per partire.

    `atteso` e `file_atteso` servono alla sentinella: se poi va in onda
    qualcos'altro, se ne accorge invece di lasciartelo scoprire a meta'
    episodio.
    """
    _assicura_cartella()
    try:
        with open(_FILE_SESSIONE, "w", encoding="utf-8") as f:
            json.dump({
                "percorso": percorso_id,
                "idx": int(idx),
                "dentro_kodi": bool(dentro_kodi),
                "atteso": atteso,
                "file_atteso": file_atteso,
                "controllata": False,
                "avviata": int(time.time()),
            }, f)
    except OSError:
        pass


def marca_controllata():
    """La sentinella ha gia' verificato questa sessione: non ripetere."""
    s = sessione()
    if not s:
        return
    s["controllata"] = True
    try:
        with open(_FILE_SESSIONE, "w", encoding="utf-8") as f:
            json.dump(s, f)
    except OSError:
        pass


def marca_visto_play():
    """Il video di questa sessione E' PARTITO almeno una volta. Serve al
    servizio per distinguere 'finito' da 'non ancora partito' quando il
    video lo apre s4me e ci mette secondi a risolvere la fonte."""
    s = sessione()
    if not s or s.get("visto_play"):
        return
    s["visto_play"] = True
    try:
        with open(_FILE_SESSIONE, "w", encoding="utf-8") as f:
            json.dump(s, f)
    except OSError:
        pass


def registra_anomalia(atteso, ottenuto):
    """Scrive nel diario degli errori: serve a capire se e' un caso o un vizio."""
    _assicura_cartella()
    percorso = os.path.join(_CARTELLA, "anomalie.json")
    try:
        elenco = []
        if os.path.exists(percorso):
            with open(percorso, "r", encoding="utf-8") as f:
                elenco = json.load(f)
        elenco.append({
            "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
            "atteso": atteso,
            "ottenuto": ottenuto,
        })
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(elenco[-200:], f, ensure_ascii=False, indent=1)
    except (OSError, ValueError):
        pass


def anomalie():
    percorso = os.path.join(_CARTELLA, "anomalie.json")
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def sessione():
    if not os.path.exists(_FILE_SESSIONE):
        return None
    try:
        with open(_FILE_SESSIONE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return None


def chiudi_sessione():
    try:
        if os.path.exists(_FILE_SESSIONE):
            os.remove(_FILE_SESSIONE)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Continua a guardare
# --------------------------------------------------------------------------

def recenti(quanti=4):
    """Le saghe toccate di recente, dalla piu' fresca alla piu' vecchia.

    Serve alla riga "Continua a guardare" in cima al menu: chi accende la TV
    quasi sempre vuole riprendere una cosa sola, e farla cercare fra quattordici
    saghe e' una scortesia.

    Si guarda "aggiornato" e non i "visti": chi ha cominciato un episodio dieci
    minuti fa e non l'ha finito e' proprio la persona che va servita per prima,
    e per lei i visti sono ancora zero.
    """
    dati = _leggi()
    righe = []
    for pid, s in dati.items():
        if not isinstance(s, dict):
            continue
        quando = int(s.get("aggiornato", 0) or 0)
        if quando <= 0:
            continue
        righe.append({
            "percorso": pid,
            "idx": int(s.get("idx", 1) or 1),
            "secondi": int(s.get("secondi", 0) or 0),
            "durata": int(s.get("durata", 0) or 0),
            "visti": len(s.get("visti", []) or []),
            "aggiornato": quando,
        })
    righe.sort(key=lambda r: r["aggiornato"], reverse=True)
    return righe[:quanti]
