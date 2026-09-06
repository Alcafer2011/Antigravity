# -*- coding: utf-8 -*-
"""
Ponte verso s4me: quando Le Saghe non ha una fonte, si salta dritti alla
ricerca di s4me con il titolo GIA' SCRITTO, senza uscire dall'add-on.

COME FUNZIONA (letto nel codice di s4me, non indovinato)
    specials/search.py, funzione new_search():

        if item.search_text:
            searched_text = item.search_text
        else:
            searched_text = platformtools.dialog_input(...)

    Cioe': se l'Item porta gia' il testo, s4me NON apre la finestra di ricerca
    e cerca subito. Ed e' importante, perche' quella finestra e' modale e non
    si puo' pilotare da fuori.

    L'indirizzo si costruisce come fa core/item.py -> tourl():
        plugin://plugin.video.s4me/?<base64 del json dell'Item, urlencoded>
"""
import base64
import json

try:
    from urllib.parse import quote
except ImportError:                      # Python 2, non dovrebbe servire
    from urllib import quote             # noqa

import xbmc
import xbmcgui
import xbmcvfs

S4ME = "plugin.video.s4me"


def installato():
    """s4me c'e' e si puo' usare?"""
    try:
        return bool(xbmcvfs.exists("special://home/addons/%s/addon.xml" % S4ME))
    except Exception:
        return False


def indirizzo_ricerca(titolo, modo="all"):
    """L'indirizzo plugin:// che apre la ricerca di s4me gia' compilata.

    modo: 'all' cerca su tutti i canali (quello che serve a noi),
          'movie' o 'show' passano prima da TMDB.
    """
    voce = {
        "channel": "search",
        "action": "new_search",
        "path": "special",
        "search_text": titolo,
        "mode": modo,
        "title": titolo,
    }
    grezzo = json.dumps(voce).encode("utf-8")
    return "plugin://%s/?%s" % (S4ME, quote(base64.b64encode(grezzo).decode("ascii")))


def cerca(titolo, modo="all"):
    """Porta l'utente dentro i risultati di s4me per questo titolo.

    Si usa Container.Update: la navigazione resta nello stack, quindi il tasto
    'indietro' riporta dentro Le Saghe. Con RunPlugin invece si perderebbe il
    filo e l'utente si ritroverebbe altrove.
    """
    if not installato():
        xbmcgui.Dialog().ok("Le Saghe",
                            "s4me non risulta installato, quindi non posso "
                            "passargli la ricerca.")
        return False
    xbmc.executebuiltin("Container.Update(%s)" % indirizzo_ricerca(titolo, modo))
    return True


def titolo_per_ricerca(serie, tappa):
    """Cosa conviene scrivere nella casella di ricerca.

    Il numero di episodio NON si mette: s4me cerca opere, non puntate, e
    aggiungerlo fa fallire la ricerca. Si toglie anche quello che sta fra
    parentesi (spesso e' un'annotazione nostra, non parte del titolo).
    """
    t = (serie or {}).get("titolo") or ""
    if "(" in t:
        t = t.split("(")[0]
    return t.strip()


# ===========================================================================
# DISCESA AUTOMATICA (2026-09-05)
#
# L'utente non vuole "la lista di s4me": vuole l'episodio. Quindi qui si
# percorre l'albero di s4me da soli e si arriva il piu' vicino possibile al
# video, fermandosi a mostrare la lista SOLO se non si riesce a decidere.
#
# Si usa Files.GetDirectory di Kodi: e' Kodi stesso a interrogare s4me, quindi
# non si tocca il codice di s4me e la cosa non si rompe ai suoi aggiornamenti.
#
# NOTA IMPORTANTE, misurata sul campo: la stessa chiamata fatta da FUORI
# (webserver di Kodi, via rete) fallisce con "413 Content Too Large", perche'
# gli indirizzi di s4me contengono lo stato di tutti i risultati e diventano
# enormi. Da DENTRO l'add-on non c'e' questo limite: la chiamata e' in memoria.
# ===========================================================================

import re
import time

_RIPULISCI = re.compile(r"\[/?(B|I|UPPERCASE|LOWERCASE|CR|COLOR[^\]]*)\]", re.I)


def _rpc(metodo, params):
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params})
    try:
        return json.loads(xbmc.executeJSONRPC(corpo))
    except Exception:
        return {}


def _elenca(url):
    """Le voci dentro un indirizzo plugin://, come le vedrebbe l'utente."""
    r = _rpc("Files.GetDirectory", {"directory": url, "media": "video"})
    if "error" in r:
        return []
    return (r.get("result", {}) or {}).get("files", []) or []


def _testo(v):
    return _RIPULISCI.sub("", v.get("label") or "").strip()


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", _RIPULISCI.sub("", s or "").lower())


def _quanti_risultati(v):
    """I siti si presentano come 'ToonItalia [100]': il numero e' utile per
    provare prima quelli che hanno piu' roba."""
    m = re.search(r"\[(\d+)\]", _testo(v))
    return int(m.group(1)) if m else 0


# --- LINGUA -----------------------------------------------------------------
# I siti di s4me sono italiani, ma nei risultati convivono tre cose diverse:
# doppiato in italiano, sottotitolato, e originale. Noi vogliamo SEMPRE il
# doppiato: e' l'unica versione che ha senso per come si guarda in famiglia.
# I marcatori sono quelli veri visti nelle etichette dei canali.
_ITALIANO = ("[ita]", "(ita)", " ita ", "italiano", "doppiat")
_SOTTOTITOLI = ("sub ita", "subita", "[sub", "sottotitol", "vostfr")
_ALTRE_LINGUE = ("[eng]", "(eng)", "[jap]", "(jap)", " raw ", "[esp]", "[fra]", "[ger]")


def rango_lingua(etichetta):
    """La lingua come PRIORITA' ASSOLUTA, non come punteggio da sommare.

    Scelta esplicita dell'utente: prima sempre il doppiaggio italiano, poi i
    sottotitoli, e solo in ultimo altre lingue. Un titolo che somiglia di piu'
    ma e' in giapponese NON deve mai vincere su uno doppiato.

    3 = doppiato in italiano
    2 = non dichiarato (sui siti italiani di solito vuol dire doppiato)
    1 = sottotitolato in italiano
    0 = altra lingua
    """
    e = " " + (etichetta or "").lower() + " "
    if any(x in e for x in _ALTRE_LINGUE):
        return 0
    if any(x in e for x in _SOTTOTITOLI):
        return 1
    if any(x in e for x in _ITALIANO):
        return 3
    return 2


def punteggio_lingua(etichetta):
    """Quanto vale questa voce dal punto di vista della lingua.

    +40 doppiato in italiano, -60 sottotitolato, -80 altra lingua.
    Sono grandi apposta: meglio un titolo che somiglia un po' meno ma e' in
    italiano, che quello perfetto in giapponese.
    """
    e = " " + (etichetta or "").lower() + " "
    p = 0
    if any(x in e for x in _ITALIANO):
        p += 40
    if any(x in e for x in _SOTTOTITOLI):
        p -= 60
    if any(x in e for x in _ALTRE_LINGUE):
        p -= 80
    return p


def _somiglia(etichetta, titolo):
    """Quanto questa voce somiglia al titolo cercato. 0 = per niente.

    Alla somiglianza del titolo si somma il punteggio della lingua: cosi' fra
    due voci che somigliano uguale vince quella in italiano.
    """
    a, b = _norm(etichetta), _norm(titolo)
    if not a or not b:
        return 0
    if a == b:
        base = 100
    elif b in a:
        # piu' corta e' la voce, meglio e': 'Dragon Ball Z' batte
        # 'Dragon Ball Z Kai - The Final Chapters'
        base = 80 - min(30, len(a) - len(b))
    elif a in b:
        base = 50
    else:
        return 0
    return base + punteggio_lingua(etichetta)


# I modi in cui i siti scrivono il numero di episodio. Sono ANCORATI: si
# accetta solo il numero che sta in una posizione da "numero di episodio",
# mai una cifra qualunque pescata dentro il titolo.
#
# Nasce da un guasto vero (05/09/2026): cercando un numero qualsiasi,
# l'episodio "Killer" e un altro finivano sullo stesso video, perche' bastava
# una cifra nel titolo o nella qualita' ("1080p") per far scattare il match.
_FORME_EPISODIO = (
    r"(?:episodi[oa]|ep\.?|puntata|capitolo)\s*[-#:]?\s*0*(\d{1,4})\b",
    # "12 - Il pianeta Namek": numero, un segno di separazione, spazio.
    #
    # Il separatore NON e' scritto come elenco di trattini, ed e' una scelta
    # voluta. Prima c'era una classe con dentro il trattino lungo e quello
    # medio; uno script che ripuliva i caratteri tipografici (i "quadratini"
    # nei titoli) li ha trasformati in trattini normali e la classe e'
    # diventata "[-- - .)]", cioe' un intervallo di caratteri impossibile.
    # Risultato il 06/09/2026: "errore di riproduzione" su OGNI episodio, su
    # tutti e due gli apparecchi, senza nessun messaggio comprensibile.
    #
    # "un segno qualunque che non sia lettera, cifra o spazio" copre tutti i
    # trattini che esistono, il punto e la parentesi, e soprattutto non
    # contiene nessun carattere che qualcuno possa ripulire per sbaglio.
    r"^\s*0*(\d{1,4})\s*[^\w\s]\s",
    r"\b[sS]\d{1,2}\s*[eE]\s*0*(\d{1,4})\b",  # S01E12
    r"\b\d{1,2}x0*(\d{1,4})\b",                # 1x12
)

# Roba che contiene numeri e NON e' il numero di episodio: va tolta prima.
_RUMORE_NUMERICO = re.compile(
    r"\b(?:\d{3,4}p|[0-9.]+\s*[gmk]b|x?26[45]|h\.?26[45]|\d{4}\b)", re.I)


def _numero_episodio(etichetta):
    """Il numero di episodio scritto in questa etichetta, o None.

    None NON e' un fallimento da aggirare: vuol dire che non lo sappiamo, e
    tirare a indovinare e' esattamente quello che ha causato il guasto.
    """
    et = _RUMORE_NUMERICO.sub(" ", etichetta or "")
    for forma in _FORME_EPISODIO:
        m = re.search(forma, et, re.I)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def _episodio_giusto(voci, numero):
    """La voce dell'episodio chiesto, oppure None se non se ne e' certi.

    Due strade, in ordine:
      1) l'etichetta DICE il numero, in una delle forme riconosciute;
      2) nessuna etichetta porta numeri, ma la lista e' chiaramente una
         sequenza di episodi: allora vale la POSIZIONE (il dodicesimo e'
         l'episodio 12). Si accetta solo se la lista e' abbastanza lunga.
    Se restano piu' candidati o non si capisce, si torna None e l'utente
    sceglie: meglio un clic in piu' che il video sbagliato.
    """
    numerate = [(v, _numero_episodio(_testo(v))) for v in voci]
    trovate = [v for (v, n) in numerate if n == numero]
    if len(trovate) == 1:
        return trovate[0]
    if len(trovate) > 1:
        # piu' voci con lo stesso numero: sono i doppioni (mirror, qualita'
        # diverse). Si prende quella in italiano, se c'e'.
        trovate.sort(key=lambda v: rango_lingua(_testo(v)), reverse=True)
        return trovate[0]

    # nessuna etichetta numerata: si prova con la posizione
    quante_numerate = sum(1 for (_v, n) in numerate if n is not None)
    if quante_numerate == 0 and len(voci) >= numero >= 1:
        return voci[numero - 1]
    return None


def apri_automatico(titolo, episodio, modo="all", secondi_max=90):
    """Prova ad arrivare da solo all'episodio dentro s4me.

    Ritorna:
      'riprodotto'  -> e' partito il video
      'avvicinato'  -> non ho potuto decidere, ma ho portato l'utente al punto
                       piu' profondo raggiunto (gli restano uno o due clic)
      'niente'      -> non ho trovato nulla di utile
    """
    if not installato():
        return "niente"

    scadenza = time.time() + secondi_max
    prog = xbmcgui.DialogProgress()
    prog.create("Le Saghe", "Cerco '%s' su s4me..." % titolo)
    ultimo_livello = None

    def scaduto():
        return prog.iscanceled() or time.time() > scadenza

    try:
        siti = _elenca(indirizzo_ricerca(titolo, modo))
        siti = [v for v in siti if v.get("filetype") == "directory"]
        if not siti:
            return "niente"
        siti.sort(key=_quanti_risultati, reverse=True)
        ultimo_livello = indirizzo_ricerca(titolo, modo)

        for n, sito in enumerate(siti):
            if scaduto():
                break
            prog.update(int(20 + 60.0 * n / max(1, len(siti))),
                        "Guardo su %s..." % _testo(sito).split("[")[0].strip())

            opere = _elenca(sito["file"])
            if not opere:
                continue
            # la voce che somiglia di piu' al titolo
            # ORDINE: prima la lingua (assoluta), poi quanto somiglia il titolo.
            # E' una tupla, quindi la lingua decide sempre per prima.
            opere_ordinate = sorted(
                opere,
                key=lambda v: (rango_lingua(_testo(v)), _somiglia(_testo(v), titolo)),
                reverse=True)
            migliore = opere_ordinate[0]
            if _somiglia(_testo(migliore), titolo) < 20:
                continue                      # su questo sito non c'e' l'opera giusta
            ultimo_livello = sito["file"]

            if migliore.get("filetype") != "directory":
                continue
            episodi = _elenca(migliore["file"])
            if not episodi:
                continue
            ultimo_livello = migliore["file"]

            scelto = _episodio_giusto(episodi, episodio)
            if not scelto:
                continue

            if scelto.get("filetype") != "directory":
                prog.close()
                _rpc("Player.Open", {"item": {"file": scelto["file"]}})
                return "riprodotto"

            # ancora una cartella: di solito sono i mirror. Si prende il primo
            # che sia un file vero.
            mirror = _elenca(scelto["file"])
            ultimo_livello = scelto["file"]
            for m in mirror:
                if m.get("filetype") != "directory":
                    prog.close()
                    _rpc("Player.Open", {"item": {"file": m["file"]}})
                    return "riprodotto"
            break
    finally:
        try:
            prog.close()
        except Exception:
            pass

    if ultimo_livello:
        xbmc.executebuiltin("Container.Update(%s)" % ultimo_livello)
        return "avvicinato"
    return "niente"
