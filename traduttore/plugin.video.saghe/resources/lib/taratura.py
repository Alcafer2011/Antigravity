# -*- coding: utf-8 -*-
"""
TARATURA: l'add-on si misura la linea e si regola da solo.

PERCHE'
    Kodi esce di fabbrica tarato per una linea di casa veloce. Qui la linea
    e' una SIM 4G che fa fra i 3 e i 5 Mbps e oscilla da sola: gli stessi
    valori che vanno bene in fibra qui fanno singhiozzare i video.
    Chiedere all'utente di indovinare dei numeri sarebbe scaricargli
    addosso un problema nostro. Meglio misurare.

COSA REGOLA, e la seconda conta piu' della prima
    1. IL FIATO: quanto si tiene da parte prima di cominciare
       (`ASSUREDBUFFERDURATION`) e quanto si accumula al massimo
       (`MAXBUFFERDURATION`). Quando la linea cala per venti secondi, la
       differenza fra un video che continua e uno che si pianta e' tutta li'.
    2. IL TETTO DI QUALITA' (`adaptivestream.bandwidth.max`, in Kbps, e
       `adaptivestream.res.max`). Un buffer grande RIMANDA soltanto il
       momento in cui il video si ferma; un tetto giusto fa in modo che non
       si fermi, perche' Netflix, Prime e ogni flusso adattivo non
       sceglieranno mai una versione che la linea non regge.

    Il tetto e' il 75% della linea misurata, non il 100%: il resto serve
    all'audio, alle intestazioni di rete e soprattutto ai cali.

COME MISURA
    Scarica qualche megabyte da un servizio pensato per questo e guarda
    quanto ci mette. Tre misure, e si tiene la MIGLIORE: sul 4G una misura
    sfortunata capita di continuo, e tarare sul momento peggiore vorrebbe
    dire tenere per sempre un buffer enorme.
"""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib import salva

ADDON = xbmcaddon.Addon()
_CARTELLA = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
_FILE = os.path.join(_CARTELLA, "taratura.json")

# Un indirizzo fatto apposta per misurare, che non appartiene a nessuna delle
# fonti video: cosi' la misura non dipende da quanto e' carico un sito.
_PROVA = "https://speed.cloudflare.com/__down?bytes=%d"
_BYTE = 4000000
_ATTESA = 12

# Le tarature. Le soglie sono in megabit al secondo.
#
# I numeri non sono a caso: il fiato serve a coprire i CALI della linea, non
# la sua velocita' media. Su una linea che oscilla molto (4G) si tiene piu'
# scorta anche quando la media sembra buona.
SCAGLIONI = [
    # (fino a Mbps, assicurato, massimo, risoluzione, come si chiama, cosa vuol dire)
    (2.0,  90, 240, "480p", "linea molto lenta",
     "Si tiene un fiato lungo: con meno di 2 Mbps ogni calo della linea "
     "si sente subito. I video partiranno un po' piu' tardi, ma si "
     "fermeranno molto meno."),
    (5.0,  60, 180, "720p", "linea 4G tipica",
     "Fiato piu' lungo del normale, perche' il 4G non e' lento: e' "
     "BALLERINO. Va bene per minuti e poi cala di colpo, ed e' li' che "
     "serve la scorta."),
    (15.0, 40, 120, "1080p", "linea buona",
     "Valori vicini a quelli di fabbrica: la linea regge, non serve "
     "accumulare."),
    (9999, 30,  90, "auto", "linea veloce",
     "Non serve tenere scorta: si parte prima, e la qualita' non viene "
     "limitata."),
]

# Quanta parte della linea si lascia usare al video.
#
# NON il 100%: servono margine per l'audio, per le intestazioni di rete e
# soprattutto per i cali. Un flusso scelto al limite esatto della linea si
# ferma alla prima oscillazione, e sul 4G le oscillazioni sono la norma.
QUOTA_VIDEO = 0.75


def _misura_una():
    """Megabit al secondo di UNA prova. Zero se non si e' potuto misurare.

    L'intestazione del browser NON e' un vezzo: senza, Cloudflare risponde
    403 e la misura fallisce sempre. Con curl funzionava e da dentro Kodi
    no, ed e' esattamente questo il motivo. (Guasto vero, 06/09/2026.)
    """
    import urllib.request
    try:
        inizio = time.time()
        letti = 0
        richiesta = urllib.request.Request(_PROVA % _BYTE, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "*/*",
        })
        with urllib.request.urlopen(richiesta, timeout=_ATTESA) as r:
            while True:
                pezzo = r.read(65536)
                if not pezzo:
                    break
                letti += len(pezzo)
                if time.time() - inizio > _ATTESA:
                    break
        durata = max(time.time() - inizio, 0.001)
        return (letti * 8.0 / 1000000.0) / durata
    except Exception:
        return 0.0


def misura(quante=3):
    """La velocita' della linea in Mbps. Si tiene la MIGLIORE delle prove.

    La migliore e non la media: sul 4G una misura sfortunata capita di
    continuo, e tarare sul momento peggiore vorrebbe dire tenersi per
    sempre un buffer enorme per colpa di dieci secondi storti.
    """
    valori = [_misura_una() for _ in range(max(1, quante))]
    valori = [v for v in valori if v > 0]
    return round(max(valori), 2) if valori else 0.0


def scaglione(mbps):
    for soglia, assicurato, massimo, risoluzione, nome, spiega in SCAGLIONI:
        if mbps <= soglia:
            return {"assicurato": assicurato, "massimo": massimo,
                    "risoluzione": risoluzione, "nome": nome, "spiega": spiega,
                    # il tetto in Kbps, che e' l'unita' che vuole
                    # inputstream.adaptive
                    "tetto_kbps": int(mbps * 1000 * QUOTA_VIDEO)}
    return {"assicurato": 60, "massimo": 180, "risoluzione": "auto",
            "nome": "sconosciuta", "spiega": "", "tetto_kbps": 0}


def applica(mbps):
    """Scrive i valori nell'add-on di streaming. (fatto, spiegazione).

    Regola DUE cose, ed e' la seconda quella che conta di piu':
      - quanto fiato tenere di scorta (il buffer)
      - **il tetto di qualita'**: cosi' Netflix, Prime e ogni flusso
        adattivo non scelgono mai una versione del video che la linea non
        regge. Un buffer grande rimanda il momento in cui si ferma; un
        tetto giusto fa in modo che non si fermi.
    """
    s = scaglione(mbps)
    try:
        isa = xbmcaddon.Addon("inputstream.adaptive")
    except Exception:
        return False, ("L'add-on di streaming (inputstream.adaptive) non e' "
                       "installato: non c'e' niente da regolare.")

    scritti = []
    try:
        isa.setSettingInt("ASSUREDBUFFERDURATION", s["assicurato"])
        isa.setSettingInt("MAXBUFFERDURATION", s["massimo"])
        scritti.append("fiato")
    except Exception as e:
        return False, "Non sono riuscito a scrivere il buffer: %s" % e

    # Il tetto di qualita'. Sta in un try a parte perche' i nomi di queste
    # impostazioni sono cambiati fra le versioni: se un giorno non ci sono
    # piu', il fiato deve restare regolato lo stesso.
    tetto = ""
    try:
        if s["tetto_kbps"] > 0:
            isa.setSettingInt("adaptivestream.bandwidth.max", s["tetto_kbps"])
            isa.setSettingInt("adaptivestream.bandwidth.init", s["tetto_kbps"])
            isa.setSettingString("adaptivestream.res.max", s["risoluzione"])
            tetto = ("\nTetto di qualita': [B]%d Kbps[/B] (%s), cioe' il %d%% "
                     "della linea. Il resto serve all'audio e ai cali."
                     % (s["tetto_kbps"], s["risoluzione"], int(QUOTA_VIDEO * 100)))
            scritti.append("qualita'")
    except Exception:
        tetto = ("\n[COLOR orange]Il tetto di qualita' non si e' potuto "
                 "impostare su questa versione dell'add-on di streaming.[/COLOR]")

    _ricorda(mbps, s)
    return True, ("Linea misurata: [B]%.1f Mbps[/B] - %s\n\n"
                  "Fiato di scorta: %d secondi assicurati, fino a %d.%s\n\n%s"
                  % (mbps, s["nome"], s["assicurato"], s["massimo"], tetto,
                     s["spiega"]))


def _ricorda(mbps, s):
    try:
        if not xbmcvfs.exists(_CARTELLA):
            xbmcvfs.mkdirs(_CARTELLA)
        storia = ultima().get("storia", [])
        storia.append({"quando": int(time.time()), "mbps": mbps})
        salva.json_atomico(_FILE, {"quando": int(time.time()), "mbps": mbps,
                       "scaglione": s["nome"],
                       "assicurato": s["assicurato"], "massimo": s["massimo"],
                       "tetto_kbps": s.get("tetto_kbps", 0),
                       "risoluzione": s.get("risoluzione", "auto"),
                       "storia": storia[-20:]}, ensure_ascii=False)
    except OSError as _errore:
        xbmc.log("[Le Saghe] _ricorda: errore ignorato: %s" % _errore, xbmc.LOGDEBUG)


def ultima():
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def serve_rimisurare(giorni=14):
    """Vero se non si misura da un po'. Una linea 4G cambia: cambia il
    ripetitore, cambia il tempo, si sposta l'antenna."""
    u = ultima()
    if not u.get("quando"):
        return True
    return (time.time() - u["quando"]) > giorni * 86400


def racconta():
    """Lo stato della taratura, in parole."""
    u = ultima()
    if not u:
        return ("La linea non e' mai stata misurata.\n\n"
                "Finche' non lo fai, Kodi usa valori pensati per una linea "
                "di casa veloce: su una SIM 4G sono quasi sempre sbagliati.")
    quando = time.strftime("%d/%m/%Y alle %H:%M", time.localtime(u["quando"]))
    righe = ["[B]Ultima misura:[/B] %s" % quando,
             "[B]Velocita':[/B] %.1f Mbps  (%s)" % (u.get("mbps", 0), u.get("scaglione", "")),
             "[B]Fiato di scorta:[/B] %d secondi assicurati, fino a %d"
             % (u.get("assicurato", 0), u.get("massimo", 0))]
    if u.get("tetto_kbps"):
        righe.append("[B]Tetto di qualita':[/B] %d Kbps  (%s)"
                     % (u["tetto_kbps"], u.get("risoluzione", "auto")))
    storia = u.get("storia", [])
    if len(storia) > 1:
        righe.append("")
        righe.append("[B]Le misure precedenti[/B]")
        for v in storia[-8:][::-1]:
            righe.append("  %s   %.1f Mbps"
                         % (time.strftime("%d/%m %H:%M", time.localtime(v["quando"])),
                            v["mbps"]))
    if serve_rimisurare():
        righe.append("")
        righe.append("[COLOR orange]Sono passate piu' di due settimane: "
                     "converrebbe rimisurare.[/COLOR]")
    return "\n".join(righe)
