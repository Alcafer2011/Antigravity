# -*- coding: utf-8 -*-
"""Un Kodi finto, quanto basta per aprire i menu dell'add-on sul PC.

PERCHE' ESISTE
    Finora ogni errore nel menu si scopriva solo davanti alla TV: il menu non
    si apriva e bisognava andare a leggere il log del box. Due guasti veri
    (datetime.strptime che dentro Kodi vale None, e una saga aggiunta al
    catalogo ma non all'ordine) sarebbero stati presi qui in un secondo.

COSA NON E'
    Non e' un emulatore. Non disegna niente, non riproduce niente. Registra
    solo le voci che l'add-on chiede di mettere a schermo, cosi' si puo'
    controllare che ci siano, in che ordine, con che immagini.
"""
import json
import os
import sys
import types

# Le voci che l'add-on ha chiesto di mostrare, nell'ordine.
VOCI = []
CONTENUTO = []
CATEGORIA = []

# Come e' stata aperta l'ultima tastiera, e cosa deve rispondere.
ULTIMO_INPUT = None
RISPOSTA_INPUT = ""


class ListItem(object):
    def __init__(self, label="", label2="", path=""):
        self.label = label
        # label2 va tenuta: dal 10/09/2026 il dettaglio (minuto di ripresa,
        # episodio) sta li', non piu' attaccato al titolo con un a capo.
        self.label2 = label2
        self.path = path
        self.arte = {}
        self.proprieta = {}
        self._tag = InfoTag()

    def setArt(self, d):
        self.arte.update(d)

    def setProperty(self, k, v):
        self.proprieta[k] = v

    def getVideoInfoTag(self):
        return self._tag

    def setInfo(self, *a, **k):
        pass

    def addContextMenuItems(self, voci, replaceItems=False):
        self.menu = list(voci)

    def setLabel(self, v):
        self.label = v

    def setLabel2(self, v):
        self.label2 = v

    def getLabel(self):
        return self.label

    def getLabel2(self):
        return self.label2

    def setPath(self, v):
        self.path = v

    def getProperty(self, k):
        return self.proprieta.get(k, "")


class InfoTag(object):
    def __init__(self):
        self.dati = {}

    def __getattr__(self, nome):
        if not nome.startswith("set"):
            raise AttributeError(nome)
        chiave = nome[3:].lower()

        def _metti(*valori):
            self.dati[chiave] = valori[0] if len(valori) == 1 else valori
        return _metti


class Dialog(object):
    risposte = []          # risposte da dare, in ordine, a yesno/select

    def notification(self, *a, **k):
        VOCI.append(("notifica", a[0] if a else "", a[1] if len(a) > 1 else ""))

    def ok(self, *a, **k):
        VOCI.append(("ok", a[0] if a else "", a[1] if len(a) > 1 else ""))

    def yesno(self, *a, **k):
        return bool(Dialog.risposte.pop(0)) if Dialog.risposte else False

    def yesnocustom(self, *a, **k):
        return Dialog.risposte.pop(0) if Dialog.risposte else 0

    def select(self, *a, **k):
        return Dialog.risposte.pop(0) if Dialog.risposte else -1

    def textviewer(self, *a, **k):
        VOCI.append(("testo", a[0] if a else "", ""))

    def input(self, *a, **k):
        """La tastiera. Registra COME e' stata aperta.

        Serve a provare che la casella parte vuota: era il difetto del
        06/09/2026, la casella arrivava gia' piena con la ricerca di prima e
        col telecomando non si riusciva a svuotarla.
        """
        global ULTIMO_INPUT
        ULTIMO_INPUT = {"heading": a[0] if a else "",
                        "defaultt": k.get("defaultt", a[1] if len(a) > 1 else "")}
        return RISPOSTA_INPUT


class DialogProgress(object):
    annullato = False

    def create(self, *a, **k):
        pass

    def update(self, *a, **k):
        pass

    def iscanceled(self):
        return DialogProgress.annullato

    def close(self):
        pass


def installa(cartella_addon, impostazioni=None, profilo=None):
    """Mette i finti moduli in sys.modules. Da chiamare PRIMA di importare."""
    imp = dict(impostazioni or {})
    profilo = profilo or os.path.join(cartella_addon, "_profilo_di_prova")
    if not os.path.isdir(profilo):
        os.makedirs(profilo)

    # ---- xbmcaddon ----
    xbmcaddon = types.ModuleType("xbmcaddon")

    class Addon(object):
        def __init__(self, *a):
            pass

        def getAddonInfo(self, che):
            return {"path": cartella_addon, "profile": profilo,
                    "id": "plugin.video.saghe", "version": "1.0.0"}.get(che, "")

        def getSetting(self, k):
            return str(imp.get(k, ""))

        def getSettingBool(self, k):
            if k not in imp:
                raise ValueError(k)   # come Kodi: impostazione inesistente
            return bool(imp[k])

        def getSettingInt(self, k):
            if k not in imp:
                raise ValueError(k)
            return int(imp[k])

        def getLocalizedString(self, n):
            return ""

        def openSettings(self):
            pass

    xbmcaddon.Addon = Addon
    sys.modules["xbmcaddon"] = xbmcaddon

    # ---- xbmcvfs ----
    xbmcvfs = types.ModuleType("xbmcvfs")

    def _traduci(p):
        """Traduce i percorsi speciali di Kodi come farebbe Kodi.

        Serve al canale per s4me, che cerca il nostro add-on con
        `special://home/addons/plugin.video.saghe`. Senza questa
        traduzione trova una stringa che non e' una cartella e conclude
        che il catalogo non esiste.
        """
        p = str(p)
        if p.startswith("special://home/addons/plugin.video.saghe"):
            return p.replace("special://home/addons/plugin.video.saghe",
                             cartella_addon).replace("/", os.sep)
        if p.startswith("special://profile/addon_data/plugin.video.saghe"):
            return profilo
        return p

    xbmcvfs.translatePath = _traduci
    xbmcvfs.exists = os.path.exists
    xbmcvfs.mkdirs = lambda p: os.makedirs(p, exist_ok=True)
    sys.modules["xbmcvfs"] = xbmcvfs

    # ---- xbmcgui ----
    xbmcgui = types.ModuleType("xbmcgui")
    xbmcgui.ListItem = ListItem
    xbmcgui.Dialog = Dialog
    xbmcgui.DialogProgress = DialogProgress

    class WindowXML(object):
        """Una finestra finta: non disegna, ma tiene le voci che le
        vengono date, cosi' si puo' controllare COSA finirebbe a schermo."""

        def __init__(self, *a, **k):
            self.righe = {}
            self.proprieta = {}
            self.fuoco = None

        def getControl(self, cid):
            finestra = self

            class Lista(object):
                def addItems(self, voci):
                    finestra.righe.setdefault(cid, []).extend(voci)

                def getSelectedItem(self):
                    v = finestra.righe.get(cid) or []
                    return v[0] if v else None

                def setLabel(self, v):
                    pass

                def setText(self, v):
                    pass
            return Lista()

        def setProperty(self, k, v):
            self.proprieta[k] = v

        def setFocusId(self, cid):
            self.fuoco = cid

        def getFocusId(self):
            return self.fuoco

        def doModal(self):
            self.onInit()

        def close(self):
            pass

        def onInit(self):
            pass

    xbmcgui.WindowXML = WindowXML
    xbmcgui.WindowXMLDialog = WindowXML
    for n, v in (("NOTIFICATION_INFO", 0), ("NOTIFICATION_WARNING", 1),
                 ("NOTIFICATION_ERROR", 2),
                 ("INPUT_ALPHANUM", 0), ("INPUT_NUMERIC", 1),
                 ("INPUT_DATE", 2), ("INPUT_TIME", 3),
                 ("INPUT_IPADDRESS", 4), ("INPUT_PASSWORD", 5),
                 ("DLG_YESNO_YES_BTN", 11), ("DLG_YESNO_NO_BTN", 10)):
        setattr(xbmcgui, n, v)
    sys.modules["xbmcgui"] = xbmcgui

    # ---- xbmc ----
    xbmc = types.ModuleType("xbmc")
    xbmc.LOGINFO = xbmc.LOGWARNING = xbmc.LOGERROR = xbmc.LOGDEBUG = 0
    xbmc.log = lambda *a, **k: None
    xbmc.executebuiltin = lambda *a, **k: None
    xbmc.getCondVisibility = lambda *a: False
    xbmc.sleep = lambda ms: None
    xbmc.executeJSONRPC = lambda s: json.dumps({"result": {}})
    xbmc.translatePath = lambda p: p

    class Monitor(object):
        def abortRequested(self):
            return False

        def waitForAbort(self, s=0):
            return False

    class Player(object):
        def isPlayingVideo(self):
            return False

        def play(self, *a, **k):
            VOCI.append(("riproduci", a[0] if a else "", ""))

        def getTime(self):
            return 0

        def getTotalTime(self):
            return 0

        def getPlayingFile(self):
            return ""

    xbmc.Monitor = Monitor
    xbmc.Player = Player
    sys.modules["xbmc"] = xbmc

    # ---- xbmcplugin ----
    xbmcplugin = types.ModuleType("xbmcplugin")

    def addDirectoryItem(maniglia, url, li, cartella=False, totale=0):
        VOCI.append({"url": url, "etichetta": li.label,
                     "etichetta2": getattr(li, "label2", ""),
                     "cartella": bool(cartella),
                     "arte": dict(li.arte), "prop": dict(li.proprieta),
                     "tag": dict(li._tag.dati)})
        return True

    xbmcplugin.addDirectoryItem = addDirectoryItem
    xbmcplugin.addDirectoryItems = lambda h, voci, n=0: [
        addDirectoryItem(h, u, l, c) for u, l, c in voci]
    xbmcplugin.endOfDirectory = lambda *a, **k: None
    xbmcplugin.setContent = lambda h, c: CONTENUTO.append(c)
    xbmcplugin.setPluginCategory = lambda h, c: CATEGORIA.append(c)
    xbmcplugin.setResolvedUrl = lambda h, ok, li: VOCI.append(
        ("risolto", bool(ok), getattr(li, "path", "")))
    xbmcplugin.addSortMethod = lambda *a, **k: None
    for n in ("SORT_METHOD_NONE", "SORT_METHOD_UNSORTED", "SORT_METHOD_LABEL"):
        setattr(xbmcplugin, n, 0)
    sys.modules["xbmcplugin"] = xbmcplugin

    return profilo


def installa_finto_s4me():
    """Finge quel tanto di s4me che serve a importare i NOSTRI canali.

    Serve per collaudare `resources/canale/lesaghe.py` sul PC. Non finge
    s4me intero: solo `core.item.Item`, `core.support` e `platformcode`,
    cioe' le tre cose che i nostri canali importano. Tutto il resto - la
    ricerca sui siti, la risoluzione dei video - e' roba di s4me e si
    collauda solo li'.
    """
    import types as _t

    core = _t.ModuleType("core")
    core.__path__ = []
    sys.modules["core"] = core

    item_mod = _t.ModuleType("core.item")

    class Item(object):
        def __init__(self, **kw):
            self.__dict__.update(kw)

        def clone(self, **kw):
            d = dict(self.__dict__)
            d.update(kw)
            return Item(**d)

        def __getattr__(self, nome):
            return ""            # come l'Item vero: attributo mancante = vuoto

    item_mod.Item = Item
    sys.modules["core.item"] = item_mod
    core.item = item_mod

    support = _t.ModuleType("core.support")
    support.typo = lambda testo, stile="": str(testo)
    support.info = lambda *a, **k: None
    support.match = lambda *a, **k: None
    support.server = lambda *a, **k: []
    sys.modules["core.support"] = support
    core.support = support

    pc = _t.ModuleType("platformcode")
    pc.__path__ = []
    logger = _t.ModuleType("platformcode.logger")
    for n in ("info", "error", "debug"):
        setattr(logger, n, lambda *a, **k: None)
    config = _t.ModuleType("platformcode.config")
    config.get_setting = lambda *a, **k: ""
    pc.logger = logger
    pc.config = config
    sys.modules["platformcode"] = pc
    sys.modules["platformcode.logger"] = logger
    sys.modules["platformcode.config"] = config
    return Item


def azzera():
    global ULTIMO_INPUT
    ULTIMO_INPUT = None
    del VOCI[:]
    del CONTENUTO[:]
    del CATEGORIA[:]
