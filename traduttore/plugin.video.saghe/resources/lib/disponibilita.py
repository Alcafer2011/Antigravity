# -*- coding: utf-8 -*-
"""IL CONTROLLORE DELLE LOCANDINE: un film che vedi deve essere un film che parte.

PERCHE' (l'utente, 11/09/2026)
    "ho la locandina di Oceania, quello nuovo appena uscito: lo clicco, si
    apre, ma riproduce il cartone animato. Ci vuole qualcuno che controlla
    davvero anche queste cose, perche' se ho una locandina quello riprodotto
    deve essere quello. E in tanti posti vedo delle locandine con la scritta
    'non in streaming', oppure clicco cerca cerca e poi non riproduce niente."
    Tre guasti:
      - il canale sceglieva il film solo dal TITOLO: "Oceania" del 2026 e il
        cartone del 2016 si chiamano uguale (ora conta anche l'anno, vedi
        lesaghe._anno_compatibile);
      - "non in streaming" la scriveva la Videoteca guardando SOLO la nostra
        lista degli abbonamenti, senza chiedere mai ai siti;
      - un film ancora in sala i siti non ce l'hanno, e lo si scopriva solo
        dopo averlo cliccato.

COME
    Quando nessuno usa la TV (niente in riproduzione, telecomando fermo da
    tre minuti) il servizio prova i film uno alla volta con la STESSA ricerca
    che si usa per guardarli: `lesaghe.verifica_film` dentro s4me - titolo,
    anno, server che danno davvero un video. L'esito finisce qui:
        pronto   un sito ce l'ha e il video si apre (e la rubrica ricorda
                 dove: al clic il film parte senza ricercare)
        assente  nessun sito ce l'ha, o solo di un altro anno
    Le tessere lo dicono, e "Al cinema ora" mette prima quelli pronti.
    Un "pronto" si ricontrolla dopo 3 giorni, un "assente" dopo 1: un film
    appena uscito dalle sale compare da solo il giorno che arriva sui siti.
"""

import io
import json
import os
import re
import threading
import time
import unicodedata

import xbmc
import xbmcvfs

from resources.lib import s4me_link

RINNOVA = {"pronto": 3 * 86400, "assente": 86400}
ESITO = "special://temp/videoteca-verifica.json"
PER_GIRO = 12
OGNI = 30 * 60
PRIMA_ATTESA = 10 * 60
FERMO_DA = 180


def _file():
    cartella = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(cartella):
        xbmcvfs.mkdirs(cartella)
    return os.path.join(cartella, "disponibilita.json")


def _piatto(testo):
    t = unicodedata.normalize("NFKD", str(testo or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def chiave_cinema(tmdb_id):
    return "movie/%s" % tmdb_id


def chiave_film(pid, titolo):
    return "film/%s/%s" % (pid, _piatto(titolo))


def leggi():
    try:
        with io.open(_file(), encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def stato(chiave, dati=None):
    """'pronto', 'assente' o '' (mai controllato)."""
    return ((dati if dati is not None else leggi()).get(chiave) or {}).get("stato", "")


def ordina_cinema(film):
    """I film del cartellone, prima quelli che si possono guardare davvero."""
    dati = leggi()
    rango = {"pronto": 0, "": 1, "assente": 2}
    return sorted(film, key=lambda f: rango.get(stato(chiave_cinema(f.get("tmdb")), dati), 1))


def racconta(chiave, dati=None):
    """Una riga per la trama della tessera."""
    v = (dati if dati is not None else leggi()).get(chiave) or {}
    quando = time.strftime("%d/%m", time.localtime(v.get("quando", 0))) if v.get("quando") else ""
    if v.get("stato") == "pronto":
        return "[B]Pronto da guardare[/B] - trovato su %s (controllato il %s)" % (v.get("canale") or "un sito", quando)
    if v.get("stato") == "assente":
        return "[B]Non ancora in streaming[/B] - nessun sito lo ha (controllato il %s, lo ricontrollo ogni giorno)" % quando
    return ""


def _salva(dati):
    try:
        from resources.lib import salva
        salva.json_atomico(_file(), dati, ensure_ascii=False)
    except Exception as errore:
        xbmc.log("[Le Saghe] disponibilita' non salvata: %s" % errore, xbmc.LOGWARNING)


def _da_controllare():
    """Tutti i film con una locandina: il cartellone e i film delle saghe
    (quelli che non stanno gia' in un abbonamento: li si apre con la sua app)."""
    fuori = []
    try:
        from resources.lib import cinema
        for f in cinema.leggi():
            if f.get("tmdb"):
                fuori.append({"chiave": chiave_cinema(f["tmdb"]), "titolo": f.get("titolo", ""),
                              "originale": f.get("originale", ""), "anno": f.get("anno", "")})
    except Exception as errore:
        xbmc.log("[Le Saghe] controllore: cartellone non letto: %s" % errore, xbmc.LOGDEBUG)
    try:
        from resources.lib import netflix
        for v in netflix.riga("film"):
            fuori.append({"chiave": chiave_cinema(v["id"]), "titolo": v.get("titolo", ""),
                          "originale": v.get("originale", ""), "anno": v.get("anno", "")})
    except Exception as errore:
        xbmc.log("[Le Saghe] controllore: film di Netflix non letti: %s" % errore, xbmc.LOGDEBUG)
    try:
        from resources.lib import catalogo, fonti, schede
        for pid in catalogo.PERCORSI:
            for m in schede.film(pid):
                if any(fonti.possiede(x) for x in m.get("f", [])):
                    continue
                fuori.append({"chiave": chiave_film(pid, m.get("t", "")), "titolo": m.get("t", ""),
                              "originale": "", "anno": m.get("d", "")})
    except Exception as errore:
        xbmc.log("[Le Saghe] controllore: film delle saghe non letti: %s" % errore, xbmc.LOGDEBUG)
    return fuori


def controlla(voce):
    """Prova UN film dentro s4me. L'esito (dict) oppure None se s4me non ha risposto."""
    try:
        os.remove(xbmcvfs.translatePath(ESITO))
    except OSError:
        pass
    indirizzo = s4me_link.indirizzo({"channel": "lesaghe", "action": "verifica_film"},
                                    titolo_film=voce["titolo"], titolo_originale=voce.get("originale", ""),
                                    anno=voce.get("anno", ""), chiave=voce["chiave"])
    richiesta = {"jsonrpc": "2.0", "id": 1, "method": "Files.GetDirectory",
                 "params": {"directory": indirizzo, "media": "video"}}
    try:
        xbmc.executeJSONRPC(json.dumps(richiesta))
        with io.open(xbmcvfs.translatePath(ESITO), encoding="utf-8") as f:
            esito = json.load(f)
    except (OSError, ValueError) as errore:
        xbmc.log("[Le Saghe] controllore: %s senza esito: %s" % (voce["titolo"], errore), xbmc.LOGDEBUG)
        return None
    return esito if esito.get("chiave") == voce["chiave"] else None


def _libero():
    return (not xbmc.getCondVisibility("Player.HasMedia")
            and xbmc.getCondVisibility("System.IdleTime(%d)" % FERMO_DA))


def giro(monitor, massimo=PER_GIRO):
    """Controlla i film piu' urgenti (mai visti, poi i piu' vecchi). Quanti ne ha fatti."""
    if not xbmc.getCondVisibility("System.HasAddon(plugin.video.s4me)"):
        return 0
    dati = leggi()
    adesso = time.time()

    def scaduto(v):
        vecchio = dati.get(v["chiave"])
        return not vecchio or adesso - vecchio.get("quando", 0) > RINNOVA.get(vecchio.get("stato"), 86400)

    candidati = sorted((v for v in _da_controllare() if scaduto(v)),
                       key=lambda v: (dati.get(v["chiave"]) or {}).get("quando", 0))
    fatti = 0
    for v in candidati[:massimo]:
        if not _libero():
            break
        esito = controlla(v)
        if esito:
            esito.update({"titolo": v["titolo"], "anno": v.get("anno", "")})
            dati[v["chiave"]] = esito
            _salva(dati)
            fatti += 1
            xbmc.log("[Le Saghe] controllore: %s (%s) -> %s %s" % (v["titolo"], v.get("anno", ""), esito.get("stato"),
                                                                    esito.get("canale", "")), xbmc.LOGINFO)
        if monitor.waitForAbort(3):
            break
    return fatti


def avvia():
    """Il filo del controllore: aspetta dieci minuti, poi un giro ogni mezz'ora."""
    def _lavora():
        monitor = xbmc.Monitor()
        if monitor.waitForAbort(PRIMA_ATTESA):
            return
        while not monitor.abortRequested():
            try:
                if _libero():
                    giro(monitor)
            except Exception as errore:
                xbmc.log("[Le Saghe] controllore: giro non riuscito: %s" % errore, xbmc.LOGWARNING)
            if monitor.waitForAbort(OGNI):
                return
    filo = threading.Thread(target=_lavora, name="controllore-locandine")
    filo.daemon = True
    filo.start()
