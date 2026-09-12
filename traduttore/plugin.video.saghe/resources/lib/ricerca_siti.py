# -*- coding: utf-8 -*-
"""LA RICERCA SU TUTTI I SITI, DA SOLA.

PERCHE' (l'utente, 11/09/2026)
    "le ricerche devono essere tutte automatiche, non devo scegliere io da
    dove fargli fare la ricerca, che ad ogni modo non funziona ho provato".
    Aveva ragione due volte:
      - la pagina della ricerca elencava dieci porte ("Cerca su AnimeWorld",
        "Cerca su RaiPlay"...) da provare una per una, e i generi dei
        documentari facevano lo stesso con sei cataloghi;
      - le porte non si aprivano. `action=Search` in s4me non esiste
        ("module 'specials.search' has no attribute 'Search'"), e
        `action=search` di un canale riapre la TASTIERA invece di usare la
        parola gia' scritta (registro del Raspberry, 13:05-13:12).

COME
    Il lavoro lo fa il nostro canale DENTRO s4me (`lesaghe.cerca_siti`): solo
    li' si possono chiamare i siti. Li interroga tutti insieme, ognuno nel
    suo filo, e dopo `tempo` secondi risponde con quello che e' arrivato.
    Da qui lo si chiede come una cartella qualunque (Files.GetDirectory):
    Kodi fa girare s4me e restituisce le sue voci, che la Videoteca mette
    nella SUA pagina sotto i risultati del catalogo. Una pagina, zero scelte.

    Le risposte restano 12 ore (1 ora se non si e' trovato niente): ripetere
    una ricerca o tornare indietro nella pagina e' immediato.
    L'avanzamento lo scrive il canale in `STATO`; la barra la disegna
    avvio.py, fuori dalla cartella.
"""

import hashlib
import io
import json
import os
import time

import xbmc
import xbmcvfs

from resources.lib import s4me_link

TEMPO = 25
ORE_CACHE = 12
ORE_CACHE_VUOTA = 1
STATO = "special://temp/videoteca-ricerca-siti.json"


def s4me_presente():
    return xbmc.getCondVisibility("System.HasAddon(plugin.video.s4me)")


def _cartella():
    c = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.saghe/ricerche_siti/")
    if not os.path.isdir(c):
        os.makedirs(c, exist_ok=True)
    return c


# Cambia quando cambia il MODO di cercare: le risposte memorizzate col modo
# vecchio non valgono piu'. 2 = filtro di pertinenza e una voce per titolo
# (12/09/2026): senza questo, "chernobyl" avrebbe risposto per 12 ore con
# l'elenco di prima, Maria De Filippi compresa.
VERSIONE_RICERCA = 6


def _file(testo, canali):
    firma = "v%d|%s|%s" % (VERSIONE_RICERCA, (testo or "").strip().lower(), ",".join(canali))
    return os.path.join(_cartella(), hashlib.md5(firma.encode("utf-8")).hexdigest() + ".json")


def dalla_cache(testo, canali=()):
    """La risposta memorizzata, se e' ancora fresca; altrimenti None."""
    try:
        with io.open(_file(testo, tuple(canali or ())), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    ore = ORE_CACHE if d.get("voci") else ORE_CACHE_VUOTA
    if time.time() - d.get("quando", 0) > ore * 3600:
        return None
    return d


def svuota_cache():
    cartella = _cartella()
    for nome in os.listdir(cartella):
        if nome.endswith(".json"):
            try:
                os.remove(os.path.join(cartella, nome))
            except OSError as errore:
                xbmc.log("[Le Saghe] ricerche dei siti: %s non tolto: %s" % (nome, errore), xbmc.LOGDEBUG)


def stato():
    """L'avanzamento scritto dal canale dentro s4me: {testo, totale, fatti, trovati, lenti, fine}."""
    try:
        with io.open(xbmcvfs.translatePath(STATO), encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def cerca(testo, canali=(), tempo=TEMPO):
    """Chiede a s4me di cercare `testo` sui siti (tutti, o solo `canali`).

    Restituisce {"testo", "voci": [{etichetta, file, cartella, arte, trama, anno}],
    "siti", "lenti", "secondi", "quando"} e la memorizza."""
    canali = tuple(canali or ())
    fuori = {"testo": testo, "voci": [], "siti": 0, "lenti": [], "scartati": 0,
             "secondi": 0, "quando": time.time()}
    if not (testo or "").strip() or not s4me_presente():
        return fuori
    inizio = time.time()
    richiesta = {"jsonrpc": "2.0", "id": 1, "method": "Files.GetDirectory",
                 "params": {"directory": s4me_link.indirizzo({"channel": "lesaghe", "action": "cerca_siti"},
                                                              testo=testo, canali=",".join(canali),
                                                              tempo=int(tempo)),
                            "media": "video", "properties": ["art", "plot", "title", "year"]}}
    try:
        risposta = json.loads(xbmc.executeJSONRPC(json.dumps(richiesta)))
    except (ValueError, TypeError) as errore:
        xbmc.log("[Le Saghe] ricerca sui siti: risposta illeggibile: %s" % errore, xbmc.LOGWARNING)
        return fuori
    if "error" in risposta:
        xbmc.log("[Le Saghe] ricerca sui siti: Kodi risponde %s" % risposta["error"], xbmc.LOGWARNING)
        return fuori
    for f in (risposta.get("result") or {}).get("files") or []:
        # Con zero risultati s4me aggiunge da se' una voce "Nessun elemento"
        # (render_items): non ha azione, e nella nostra pagina sembrerebbe un
        # risultato da aprire.
        if not f.get("file") or not s4me_link.leggi(f["file"]).get("action"):
            continue
        fuori["voci"].append({"etichetta": f.get("label", ""), "file": f["file"],
                              "cartella": f.get("filetype") == "directory",
                              "arte": {k: v for k, v in (f.get("art") or {}).items() if v},
                              "trama": f.get("plot", ""), "anno": f.get("year") or 0})
    st = stato()
    if st.get("testo") == testo:
        fuori["siti"] = st.get("totale", 0)
        fuori["lenti"] = st.get("lenti") or []
        # Quanti risultati il canale ha buttato via perche' non c'entravano
        # con la ricerca (12/09/2026): la pagina lo dice, cosi' "pochi
        # risultati" non si confonde con "i siti non hanno risposto".
        fuori["scartati"] = st.get("scartati", 0)
    fuori["secondi"] = round(time.time() - inizio, 1)
    fuori["quando"] = time.time()
    try:
        from resources.lib import salva
        salva.json_atomico(_file(testo, canali), fuori, ensure_ascii=False)
    except Exception as errore:
        xbmc.log("[Le Saghe] ricerca sui siti non memorizzata: %s" % errore, xbmc.LOGDEBUG)
    return fuori


def voci(testo, canali=(), tempo=TEMPO):
    """La risposta memorizzata o, se non c'e', una ricerca nuova."""
    return dalla_cache(testo, canali) or cerca(testo, canali, tempo)
