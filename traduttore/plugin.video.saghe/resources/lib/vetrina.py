# -*- coding: utf-8 -*-
"""
LA VETRINA: la schermata a righe orizzontali.

PERCHE' ESISTE
    Dentro Kodi la grafica la disegna la PELLE, e una pelle mostra elenchi
    verticali. Le righe che scorrono di lato - quelle che fanno sembrare
    Netflix Netflix - non si possono chiedere a una pelle: vanno disegnate.
    Questo modulo apre una finestra NOSTRA, con il nostro disegno
    (`resources/skins/Default/1080i/vetrina.xml`), e la riempie.

COSA CI SI TROVA
    riga 0: Continua a guardare - le saghe toccate di recente
    riga 1: Le tue saghe - tutte, in ordine di catalogo

    Due righe e non sei: su un apparecchio da salotto ogni riga in piu' e'
    tempo di attesa all'apertura, e con 33 percorsi il tempo si sente.

COME SI COMPORTA
    Scegliendo una voce si chiude la vetrina e si apre la cosa scelta con
    gli strumenti normali dell'add-on. La vetrina NON riproduce e non
    decide niente: e' una vetrina. Tutta la logica resta dove era, e questo
    e' il motivo per cui aprirla non puo' rompere niente.

SE QUALCOSA VA STORTO
    `apri()` non solleva mai: se il file del disegno manca o Kodi non
    riesce a costruire la finestra, si torna indietro e si usa il menu
    normale. Una schermata bella che impedisce di guardare la TV sarebbe
    un peggioramento.
"""

import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import catalogo, progresso, schede

ADDON = xbmcaddon.Addon()
_PERCORSO = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))

RIGA_CONTINUA = 100
RIGA_SAGHE = 101
RIGA_NOVITA = 102
TITOLO = 201
SOTTO = 202
TRAMA = 203


def _voce(titolo, sotto, trama, serie_id, indirizzo, pid=None):
    li = xbmcgui.ListItem(label=titolo, label2=sotto)
    arte = {}
    # Con `pid` si usa la locandina PROPRIA della saga (due saghe che partono
    # dalla stessa serie non devono avere lo stesso poster); senza, quella
    # della serie.
    if pid:
        po = schede.poster_percorso(pid)
        sf = schede.sfondo_percorso(pid)
    else:
        po = schede.poster(serie_id)
        sf = schede.sfondo(serie_id)
    if po:
        arte["poster"] = arte["thumb"] = arte["icon"] = po
    if sf:
        arte["fanart"] = sf
    if arte:
        li.setArt(arte)
    # l'indirizzo viaggia come proprieta': al clic si legge da li'
    li.setProperty("indirizzo", indirizzo)
    li.setProperty("trama", trama or "")
    return li


def _novita():
    """Le novita' di s4me, dalla cache. NON va in rete: sarebbe una rotellina.

    La Vetrina si era gia' rovinata una volta perche' costruiva tutto a
    schermo aperto. Qui si legge SOLO quello che c'e' gia' su disco.

    E l'aggiornamento non si chiede nemmeno da qui, nonostante fosse in un
    filo a parte: provato il 07/09/2026, s4me apre una SUA finestra di
    avanzamento ("Novita' in Anime - completato in 6/7 canali") che
    compare sopra la Vetrina. Due finestre sovrapposte sono esattamente
    cio' che fa chiudere Kodi. L'aggiornamento lo fa il servizio, dove non
    c'e' nessuna finestra aperta: vedi service.py.
    """
    from resources.lib import novita as _n
    fuori = []
    try:
        for v in _n.leggi():
            li = xbmcgui.ListItem(label=v.get("titolo", ""),
                                  label2=v.get("sotto", ""))
            arte = {"poster": v.get("immagine", ""),
                    "thumb": v.get("immagine", ""),
                    "icon": v.get("immagine", "")}
            if v.get("sfondo"):
                arte["fanart"] = v["sfondo"]
            li.setArt(arte)
            li.setProperty("indirizzo", v.get("indirizzo", ""))
            li.setProperty("trama", v.get("trama", ""))
            fuori.append(li)
    except Exception as e:
        xbmc.log("[Le Saghe] vetrina, novita': %s" % e, xbmc.LOGWARNING)
    return fuori


def _continua(base):
    """Le saghe toccate di recente, la piu' fresca per prima."""
    fuori = []
    for r in progresso.recenti(10):
        pid = r["percorso"]
        p = catalogo.PERCORSI.get(pid)
        if not p:
            continue
        t = catalogo.tappa(pid, r["idx"])
        if not t:
            continue
        sch = schede.episodio(t["serie"], t["ep"])
        titolo_ep = sch["titolo"] or ("Episodio %d" % t["ep"])
        fuori.append(_voce(
            p["titolo"],
            "Riprendi da: %s" % titolo_ep,
            sch["trama"] or p.get("spiegazione", ""),
            t["serie"],
            "%s?azione=apri&percorso=%s&idx=%d" % (base, pid, r["idx"]),
            pid=pid))
    return fuori


def _saghe(base):
    """Tutte le saghe, piu' i percorsi dentro i raggruppamenti.

    ATTENZIONE ALLA VELOCITA', ed e' il motivo per cui questa funzione e'
    scritta cosi' povera: contare le tappe di un percorso vuol dire
    COSTRUIRE la sua catena, e fra saghe e serie turche sono oltre
    cinquemila tappe. Farlo per tutte prima di disegnare qualcosa vuol dire
    dieci secondi di rotellina su un Raspberry. (Guasto vero, 06/09/2026:
    la prima versione della vetrina restava appesa a girare.)

    Qui si mettono solo le cose gratuite - titolo, locandina, sfondo,
    indirizzo - e il conteggio si fa DOPO, solo per la voce selezionata,
    in `_Finestra._aggiorna_testa`. E' anche il comportamento giusto: in
    una vetrina si guardano le locandine, non le percentuali.
    """
    fuori = []
    elenco = list(catalogo.ORDINE_PERCORSI)
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        elenco.extend(catalogo.GRUPPI[gid]["percorsi"])
    for pid in elenco:
        p = catalogo.PERCORSI.get(pid)
        if not p:
            continue
        li = _voce(
            p["titolo"], p.get("sottotitolo", ""),
            p.get("spiegazione", "") or p.get("sottotitolo", ""),
            p["segmenti"][0][0],
            "%s?azione=percorso&percorso=%s" % (base, pid),
            pid=pid)
        # si segna QUALE percorso e', cosi' il conteggio si puo' fare dopo
        li.setProperty("percorso", pid)
        fuori.append(li)
    return fuori


def _stato_percorso(pid):
    """A che punto sei in questa saga. Costoso: si chiama per UNA voce."""
    try:
        totale = catalogo.lunghezza(pid)
        visti = len(progresso.visti(pid))
        if visti:
            return "%d%% vista - %d tappe su %d" % (
                progresso.percentuale(pid, totale), visti, totale)
        return "%d tappe - mai cominciata" % totale
    except Exception:
        return ""


class _Finestra(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.base = kwargs.get("base", "plugin://plugin.video.saghe/")
        self.scelto = None
        # i conteggi gia' fatti: si calcolano una volta sola per saga
        self._stati = {}

    def onInit(self):
        try:
            continua = _continua(self.base)
            saghe = _saghe(self.base)
            novita = _novita()

            # La scritta sopra ogni riga passa da una proprieta' della
            # finestra: nel disegno c'e' $INFO[Window.Property(riga0)].
            self.setProperty("riga0", "CONTINUA A GUARDARE" if continua else "")
            self.setProperty("riga1", "LE TUE SAGHE" if saghe else "")
            self.setProperty("riga2", "NOVITA' DAI TUOI SITI" if novita else "")

            if continua:
                self.getControl(RIGA_CONTINUA).addItems(continua)
            self.getControl(RIGA_SAGHE).addItems(saghe)
            if novita:
                self.getControl(RIGA_NOVITA).addItems(novita)

            # Se non c'e' niente da riprendere si parte dalle saghe,
            # altrimenti il primo tasto premuto cadrebbe nel vuoto.
            self.setFocusId(RIGA_CONTINUA if continua else RIGA_SAGHE)
            self._aggiorna_testa()
        except Exception as e:
            xbmc.log("[Le Saghe] vetrina: %s" % e, xbmc.LOGWARNING)
            self.close()

    def _elemento(self):
        try:
            cid = self.getFocusId()
            if cid not in (RIGA_CONTINUA, RIGA_SAGHE, RIGA_NOVITA):
                return None
            lista = self.getControl(cid)
            return lista.getSelectedItem()
        except Exception:
            return None

    def _aggiorna_testa(self):
        li = self._elemento()
        if not li:
            return
        try:
            sotto = li.getLabel2()
            pid = li.getProperty("percorso")
            if pid:
                # il conteggio si fa QUI, per una voce sola: farlo per
                # tutte all'apertura costava dieci secondi di rotellina
                if pid not in self._stati:
                    self._stati[pid] = _stato_percorso(pid)
                if self._stati[pid]:
                    sotto = self._stati[pid]
            self.getControl(TITOLO).setLabel(li.getLabel())
            self.getControl(SOTTO).setLabel(sotto)
            self.getControl(TRAMA).setText(li.getProperty("trama"))
        except Exception:
            pass

    def onAction(self, action):
        # 9 = indietro, 10 = menu/esci: sono i due modi in cui una persona
        # cerca di uscire da una schermata.
        if action.getId() in (9, 10, 92):
            self.close()
            return
        self._aggiorna_testa()

    def onFocus(self, controlId):
        self._aggiorna_testa()

    def onClick(self, controlId):
        if controlId not in (RIGA_CONTINUA, RIGA_SAGHE):
            return
        li = self._elemento()
        if not li:
            return
        self.scelto = li.getProperty("indirizzo")
        self.close()


def apri(base):
    """Apre la vetrina. Restituisce l'indirizzo scelto, o None.

    Non solleva mai: se il disegno manca o Kodi non costruisce la finestra,
    si torna al menu normale. Una schermata bella che impedisce di guardare
    la TV sarebbe un peggioramento.
    """
    disegno = os.path.join(_PERCORSO, "resources", "skins", "Default",
                           "1080i", "vetrina.xml")
    if not os.path.exists(disegno):
        xbmc.log("[Le Saghe] manca il disegno della vetrina: %s" % disegno,
                 xbmc.LOGWARNING)
        return None
    try:
        f = _Finestra("vetrina.xml", _PERCORSO, "Default", "1080i", base=base)
        f.doModal()
        scelto = f.scelto
        del f
        return scelto
    except Exception as e:
        xbmc.log("[Le Saghe] la vetrina non si e' aperta: %s" % e,
                 xbmc.LOGERROR)
        return None
