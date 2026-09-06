# -*- coding: utf-8 -*-
"""
IL MOTORE DELLE FONTI: non una strada sola, ma un piano.

IL PROBLEMA CHE RISOLVE
    Prima l'add-on aveva una fonte per episodio: quella. Se non funzionava,
    l'utente vedeva un errore e si arrangiava. Gli add-on che comandano
    (Seren, Umbrella) fanno un'altra cosa: hanno un ELENCO ORDINATO di
    strade e le provano finche' una parte. E' l'unica differenza che conta
    davvero fra "quasi sempre parte" e "parte".

LE TRE IDEE
    1. PIANO. Per ogni episodio si costruisce un elenco ordinato di strade,
       dalla migliore all'ultima spiaggia. Chi chiama le prova in ordine.
    2. PRE-VOLO. Prima di far partire il video si bussa al collegamento per
       un paio di secondi. Se non risponde si passa alla strada successiva
       PRIMA che l'utente veda lo schermo nero. Un controllo che costa due
       secondi ne risparmia trenta di attesa inutile.
    3. MEMORIA. Di ogni tentativo si segna se e' andato bene e quanto ci ha
       messo. Dopo qualche serata l'add-on sa che per Naruto conviene
       partire da s4me e per Lupin da Prime: impara questa casa e questa
       linea, non una media di tutte le case del mondo.

QUELLO CHE QUESTO MODULO NON FA
    Non apre niente. Costruisce il piano e tiene la memoria; ad aprire ci
    pensa main.py. Tenerli separati e' cio' che permette di collaudare il
    piano sul PC, senza una TV e senza rete.
"""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

from . import catalogo, fonti

ADDON = xbmcaddon.Addon()
_CARTELLA = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
_FILE = os.path.join(_CARTELLA, "motore.json")

# Quanto si aspetta il pre-volo. Due secondi: sopra si sente come un ritardo,
# sotto si scartano collegamenti buoni ma lenti a rispondere.
ATTESA_PREVOLO = 2.0

# Dopo quanti successi di fila una fonte scavalca l'ordine del catalogo.
# Tre: uno puo' essere fortuna, due una coincidenza, tre e' un'abitudine.
SOGLIA_ABITUDINE = 3

# Oltre questo numero di fallimenti di fila una fonte scende in fondo, ma
# NON viene mai tolta: i siti tornano su, e toglierla per sempre
# significherebbe non accorgersene mai piu'.
SOGLIA_BOCCIATURA = 3

# Il peso del ponte s4me: alto, cosi' resta l'ultima spiaggia. Una fonte
# bocciata tre volte di fila finisce PIU' IN BASSO ancora, sotto il ponte.
PESO_PONTE = 99


# --------------------------------------------------------------------------
# La memoria
# --------------------------------------------------------------------------

def _leggi():
    try:
        if not os.path.exists(_FILE):
            return {}
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        # File rovinato: si riparte da zero. La memoria e' un aiuto, non un
        # requisito: senza, l'add-on funziona lo stesso.
        return {}


def _scrivi(dati):
    try:
        if not xbmcvfs.exists(_CARTELLA):
            xbmcvfs.mkdirs(_CARTELLA)
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False)
    except OSError:
        pass


def _voce(dati, serie_id, fonte_id):
    return dati.setdefault(serie_id, {}).setdefault(fonte_id, {
        "ok": 0, "ko": 0, "ok_fila": 0, "ko_fila": 0,
        "secondi": 0.0, "ultimo": 0,
    })


def ricorda(serie_id, fonte_id, riuscito, secondi=0.0):
    """Segna com'e' andato un tentativo. Chiamato dopo ogni apertura."""
    dati = _leggi()
    v = _voce(dati, serie_id, fonte_id)
    if riuscito:
        v["ok"] += 1
        v["ok_fila"] += 1
        v["ko_fila"] = 0
        # media mobile: le serate recenti pesano piu' di quelle vecchie
        v["secondi"] = round(v["secondi"] * 0.6 + float(secondi) * 0.4, 2)
    else:
        v["ko"] += 1
        v["ko_fila"] += 1
        v["ok_fila"] = 0
    v["ultimo"] = int(time.time())
    _scrivi(dati)


def scheda(serie_id, fonte_id):
    return _leggi().get(serie_id, {}).get(fonte_id, {})


def dimentica(serie_id=None):
    """Cancella la memoria, di una serie o di tutto. Serve alle prove e a
    chi ha cambiato linea o abbonamenti e vuole ripartire pulito."""
    if serie_id is None:
        _scrivi({})
        return
    dati = _leggi()
    dati.pop(serie_id, None)
    _scrivi(dati)


# --------------------------------------------------------------------------
# Il pre-volo
# --------------------------------------------------------------------------

def _raggiungibile(indirizzo, attesa=ATTESA_PREVOLO):
    """Il collegamento risponde? Solo per gli indirizzi di rete veri."""
    import urllib.error
    import urllib.request
    try:
        richiesta = urllib.request.Request(indirizzo, method="HEAD")
        richiesta.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(richiesta, timeout=attesa) as r:
            return 200 <= getattr(r, "status", 200) < 400
    except urllib.error.HTTPError as e:
        # 403 e 405 vogliono dire "c'e' ma non ti rispondo cosi'": il file
        # esiste. Scartarlo sarebbe un errore piu' grave che tenerlo.
        return e.code in (401, 403, 405, 429)
    except Exception:
        return False


def previsione(strada, attesa=ATTESA_PREVOLO):
    """(si_puo_provare, perche). Non apre niente: guarda e basta.

    Le strade che non sono un indirizzo di rete - un file tuo, un'app, un
    altro add-on - non si possono sondare da qui, e si dichiarano provabili:
    meglio provare e fallire che scartare per prudenza qualcosa che
    funzionava.
    """
    if strada["tipo"] == "locale":
        percorso = strada.get("percorso", "")
        if percorso and (os.path.exists(percorso) or xbmcvfs.exists(percorso)):
            return True, "il file c'e'"
        return False, "il file non c'e' piu'"

    indirizzo = strada.get("percorso", "")
    if indirizzo[:4] == "http":
        if _raggiungibile(indirizzo, attesa):
            return True, "il collegamento risponde"
        return False, "il collegamento non risponde"

    return True, "non si puo' sapere prima: si prova"


# --------------------------------------------------------------------------
# Il piano
# --------------------------------------------------------------------------

def _punteggio(serie_id, fonte_id, base):
    """Quanto in alto sta questa strada. Piu' basso = si prova prima.

    Si parte dall'ordine del catalogo (base) e lo si CORREGGE con
    l'esperienza, senza stravolgerlo: l'esperienza sposta, non riscrive.
    """
    s = scheda(serie_id, fonte_id)
    p = float(base)
    if s.get("ok_fila", 0) >= SOGLIA_ABITUDINE:
        p -= 1.5                       # ha funzionato tre volte di fila
    elif s.get("ok", 0) > s.get("ko", 0):
        p -= 0.5
    if s.get("ko_fila", 0) >= SOGLIA_BOCCIATURA:
        # Va SOTTO l'ultima spiaggia, non solo un po' piu' giu'.
        #
        # Se Prime ha fallito tre volte di fila, provarlo ancora per primo
        # e' testardaggine: meglio andare dritti su s4me e tenere Prime
        # come riserva. E' la prova a valore piu' alto del banco: con la
        # penalita' piccola di prima, una fonte rotta restava in testa per
        # sempre perche' il ponte ha comunque il peso piu' alto.
        p = PESO_PONTE + 1 + float(base)
    # a parita' di tutto, si preferisce la piu' veloce delle volte scorse
    p += min(float(s.get("secondi", 0)) / 60.0, 0.4)
    return p


def piano(serie_id, ep, su_android=None):
    """L'elenco ordinato delle strade da provare per questo episodio.

    Ogni voce: id, etichetta, tipo, percorso, dentro_kodi, perche.
    L'ultima e' sempre il ponte s4me, se c'e': e' l'ultima spiaggia, e
    un'ultima spiaggia deve esserci sempre.
    """
    if su_android is None:
        su_android = fonti.su_android()

    strade = []
    for base, f in enumerate(fonti.fonti_disponibili(serie_id, ep)):
        if not f["posseduta"]:
            continue
        if f["tipo"] == "app" and not su_android:
            # qui le app non esistono: dichiararle sarebbe una bugia
            continue
        f = dict(f)
        f["base"] = base
        f["perche"] = "fonte dichiarata nel catalogo"
        s = scheda(serie_id, f["id"])
        if s.get("ok_fila", 0) >= SOGLIA_ABITUDINE:
            f["perche"] = "ha funzionato le ultime %d volte" % s["ok_fila"]
        elif s.get("ko_fila", 0) >= SOGLIA_BOCCIATURA:
            f["perche"] = "ultimamente non funziona: provata per ultima"
        strade.append(f)

    # L'ultima spiaggia va aggiunta PRIMA di ordinare, non dopo.
    #
    # Sembra un dettaglio e non lo e': aggiungendola dopo, il suo peso non
    # veniva mai confrontato con quello delle altre, e una fonte bocciata
    # tre volte restava comunque davanti al ponte. Il banco l'ha preso
    # subito, ma solo perche' la prova guardava l'ORDINE e non il punteggio.
    try:
        from . import ponte_s4me
        if ponte_s4me.installato():
            strade.append({
                "id": "s4me",
                "etichetta": "Cerca su s4me",
                "tipo": "ponte",
                "percorso": "",
                "dentro_kodi": True,
                "posseduta": True,
                "base": PESO_PONTE,
                "perche": "ultima spiaggia: si cerca per titolo",
            })
        else:
            xbmc.log("[Le Saghe] il ponte s4me NON risulta installato: "
                     "l'ultima spiaggia non c'e'", xbmc.LOGWARNING)
    except Exception as e:
        # PRIMA questo errore veniva ingoiato in silenzio, e il risultato
        # era un piano senza ultima spiaggia: si premeva play e non
        # succedeva niente. Un guasto muto e' peggio di un guasto rumoroso.
        xbmc.log("[Le Saghe] il ponte s4me non si e' potuto aggiungere al "
                 "piano: %s" % e, xbmc.LOGERROR)

    strade.sort(key=lambda f: _punteggio(serie_id, f["id"], f["base"]))

    # Il piano finisce nel registro a ogni tentativo. Costa niente e ha
    # gia' evitato ore di supposizioni: senza, "non funziona" resta una
    # frase e non diventa mai un fatto.
    xbmc.log("[Le Saghe] piano per %s ep %s: %s"
             % (serie_id, ep, " > ".join("%s(%s)" % (s["id"], s["tipo"])
                                         for s in strade) or "VUOTO"),
             xbmc.LOGINFO)
    return strade


def spiega_piano(serie_id, ep):
    """Il piano in parole, per la schermata 'perche' non parte'."""
    righe = []
    for n, s in enumerate(piano(serie_id, ep), 1):
        sc = scheda(serie_id, s["id"])
        conto = ""
        if sc.get("ok") or sc.get("ko"):
            conto = "  [%d riuscite, %d fallite]" % (sc.get("ok", 0), sc.get("ko", 0))
        righe.append("%d. %s%s\n   %s" % (n, s["etichetta"], conto, s["perche"]))
    if not righe:
        righe.append("Nessuna strada: per questa serie non c'e' nessuna fonte "
                     "fra quelle che possiedi, e il ponte s4me non e' installato.")
    return "\n".join(righe)


# --------------------------------------------------------------------------
# Il registro dei tentativi (per la diagnosi)
# --------------------------------------------------------------------------

_REGISTRO = os.path.join(_CARTELLA, "tentativi.json")
MAX_REGISTRO = 40


def annota(serie_id, ep, fonte_id, esito, dettaglio=""):
    """Tiene le ultime quaranta cose successe, per poterle raccontare.

    Serve a rispondere alla domanda "perche' non e' partito?" senza far
    aprire il registro di Kodi a nessuno.
    """
    try:
        righe = []
        if os.path.exists(_REGISTRO):
            with open(_REGISTRO, "r", encoding="utf-8") as f:
                righe = json.load(f)
        righe.append({
            "quando": time.strftime("%d/%m %H:%M"),
            "serie": serie_id, "ep": ep, "fonte": fonte_id,
            "esito": esito, "dettaglio": dettaglio,
        })
        with open(_REGISTRO, "w", encoding="utf-8") as f:
            json.dump(righe[-MAX_REGISTRO:], f, ensure_ascii=False)
    except (OSError, ValueError):
        pass


def registro():
    try:
        with open(_REGISTRO, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []
