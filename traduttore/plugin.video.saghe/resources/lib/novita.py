# -*- coding: utf-8 -*-
"""Le novita' di s4me, portate dentro la Vetrina.

PERCHE'
    La Vetrina - locandine grandi, righe che scorrono di lato - mostrava
    solo le NOSTRE saghe. Ma s4me ha una sezione "Novita'" che pesca dai
    suoi cinquanta siti, e non c'era modo di vederla con quell'aspetto:
    l'utente ha chiesto la stessa schermata anche per la roba di s4me.

COME, senza toccare s4me
    Non si importa niente di suo: si LEGGE la sua cartella come farebbe
    Kodi, con `Files.GetDirectory` via JSON-RPC. Cosi' funziona qualunque
    cosa lui cambi dentro, e se un giorno s4me non c'e' piu' la riga
    semplicemente non compare.

    Gli indirizzi di s4me sono JSON codificato in base64: NON si inventano.
    Si parte dal suo menu principale, si cerca la voce "Novita'", e da li'
    si scende. Se lui rinomina o riordina, noi lo seguiamo.

LA LENTEZZA E' IL VERO NEMICO
    Su questa linea da 4 Mbps interrogare i siti costa minuti. Quindi:
      - il risultato si scrive su disco e vale UN GIORNO;
      - se la cache non c'e' o e' vecchia, la riga NON blocca la Vetrina:
        si mostra quello che c'e' (anche niente) e si aggiorna in un filo
        a parte, cosi' la prossima apertura e' gia' pronta.
    La Vetrina si era gia' rovinata una volta per una rotellina di dieci
    secondi: non ci si ricasca.
"""

import io
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
S4ME = "plugin.video.s4me"

# Quanto vale la cache prima di essere rifatta.
DURATA = 24 * 60 * 60
# Quante voci per riga: oltre non si scorre, si soffre.
QUANTE = 20
# Quale sezione delle novita' di s4me interessa, in quest'ordine.
SEZIONI = ("Anime", "Serie TV", "Film")


def _file():
    cartella = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(cartella):
        xbmcvfs.mkdirs(cartella)
    return os.path.join(cartella, "novita.json")


def _rpc(metodo, parametri):
    richiesta = json.dumps({"jsonrpc": "2.0", "id": 1,
                            "method": metodo, "params": parametri})
    try:
        return json.loads(xbmc.executeJSONRPC(richiesta))
    except Exception as e:
        xbmc.log("[Le Saghe] novita': %s" % e, xbmc.LOGWARNING)
        return {}


def _cartella(indirizzo):
    d = _rpc("Files.GetDirectory",
             {"directory": indirizzo, "media": "video",
              "properties": ["art", "plot"]})
    return (d.get("result") or {}).get("files") or []


def _installato():
    return xbmcvfs.exists("special://home/addons/%s/addon.xml" % S4ME)


def _trova(voci, nome):
    """La voce il cui titolo comincia per `nome`, ignorando i colori."""
    import re
    for f in voci:
        pulito = re.sub(r"\[/?[A-Za-z][^\]]*\]", "", f.get("label", "")).strip()
        if pulito.lower().startswith(nome.lower()):
            return f
    return None


def _scarica():
    """Va a prendere le novita' da s4me. Lento: non chiamarlo a schermo."""
    if not _installato():
        return []

    radice = _cartella("plugin://%s/" % S4ME)
    voce = _trova(radice, "Novit")
    if not voce:
        xbmc.log("[Le Saghe] novita': s4me non ha piu' la voce 'Novita''",
                 xbmc.LOGINFO)
        return []

    sezioni = _cartella(voce["file"])
    fuori = []
    for nome in SEZIONI:
        s = _trova(sezioni, nome)
        if not s:
            continue
        for f in _cartella(s["file"])[:QUANTE]:
            arte = f.get("art") or {}
            immagine = arte.get("poster") or arte.get("thumb") or ""
            if not immagine:
                continue          # senza locandina in Vetrina non ci sta
            fuori.append({
                "titolo": f.get("label", ""),
                "sotto": nome,
                "trama": f.get("plot", "") or "",
                "immagine": immagine,
                "sfondo": arte.get("fanart", ""),
                "indirizzo": f.get("file", ""),
            })
        if fuori:
            break                 # una sezione basta: la prima che risponde
    return fuori


def leggi():
    """Le novita' salvate. Non va mai in rete: e' sicura a schermo."""
    try:
        with io.open(_file(), encoding="utf-8") as f:
            d = json.load(f)
        return d.get("voci") or []
    except Exception:
        return []


def _scrivi(voci):
    try:
        with io.open(_file(), "w", encoding="utf-8") as f:
            f.write(json.dumps({"quando": int(time.time()), "voci": voci},
                               ensure_ascii=False))
    except Exception as e:
        xbmc.log("[Le Saghe] novita' non salvate: %s" % e, xbmc.LOGWARNING)


def scaduta():
    try:
        with io.open(_file(), encoding="utf-8") as f:
            return (time.time() - json.load(f).get("quando", 0)) > DURATA
    except Exception:
        return True


def aggiorna_se_serve():
    """Rifa' la cache in un filo a parte. Torna subito, non blocca niente."""
    if not scaduta():
        return False
    import threading

    def _lavora():
        voci = _scarica()
        if voci:
            _scrivi(voci)
            xbmc.log("[Le Saghe] novita' aggiornate: %d voci" % len(voci),
                     xbmc.LOGINFO)

    t = threading.Thread(target=_lavora, daemon=True)
    t.daemon = True
    t.start()
    return True
