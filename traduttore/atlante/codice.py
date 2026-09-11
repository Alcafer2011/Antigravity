# -*- coding: utf-8 -*-
"""CODICE: i guasti che si trovano leggendo il codice Python e gli XML.

Ogni controllo produce REPERTI: {controllo, file, riga, testo, livello, tipo}.
Il livello lo decide questo modulo in base al danno che fa a chi guarda la TV,
non all'eleganza del codice.

    critico   rompe una funzione a ogni uso (errore sicuro)
    alto      rompe in certe condizioni, o blocca Kodi
    medio     rende instabile o fragile (una volta su tante, al calore, a rete giu')
    basso     non si vede, ma e' un rischio o un debito
    info      da sapere
"""

import ast
import io
import os
import re
import xml.etree.ElementTree as ET

# API di Kodi sparite o cambiate. (espressione, livello, spiegazione)
API_KODI = [
    (r"\bxbmc\.translatePath\s*\(", "critico",
     "xbmc.translatePath non esiste piu' da Kodi 19: si usa xbmcvfs.translatePath"),
    (r"ListItem\([^)]*\b(iconImage|thumbnailImage)\s*=", "critico",
     "iconImage/thumbnailImage tolti da Kodi 19: si usa setArt"),
    (r"\.(setIconImage|setThumbnailImage)\s*\(", "critico", "tolti da Kodi 19: si usa setArt"),
    (r"\bxbmc\.LOG(NOTICE|SEVERE)\b", "critico", "LOGNOTICE/LOGSEVERE tolti da Kodi 19: LOGINFO/LOGERROR"),
    (r"\bxbmc\.abortRequested\b", "critico", "xbmc.abortRequested tolto: xbmc.Monitor().abortRequested()"),
    (r"Dialog\(\)\.ok\([^()]*,[^()]*,[^()]*,", "alto",
     "Dialog().ok con piu' di 2 argomenti: da Kodi 19 accetta solo (titolo, messaggio)"),
    (r"\.setInfo\s*\(", "basso",
     "ListItem.setInfo e' deprecato da Kodi 20: riempie il registro di avvisi; si usa getVideoInfoTag()"),
    (r"\.addStreamInfo\s*\(", "basso", "addStreamInfo deprecato da Kodi 20: InfoTagVideo.addVideoStream"),
    (r"\.setCast\s*\(", "info", "setCast del ListItem deprecato: InfoTagVideo.setCast con xbmc.Actor"),
    (r"\bgetSetting\(\s*['\"][^'\"]+['\"]\s*\)\s*==\s*['\"](true|false)['\"]", "basso",
     "confronto di un booleano come testo: getSettingBool e' piu' sicuro"),
]

SICUREZZA = [
    (r"(?i)\b(api_?key|chiave(_tmdb)?|token|secret|password|passwd)\b\s*=\s*['\"][A-Za-z0-9_\-]{12,}['\"]",
     "medio", "chiave o credenziale scritta nel codice: chi ha il file la legge (e il repository e' su GitHub)"),
    (r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}", "alto",
     "token GitHub scritto nel codice: da' accesso al repository privato"),
    (r"(?i)verify\s*=\s*False|_create_unverified_context|CERT_NONE", "medio",
     "verifica dei certificati SSL spenta: qualcuno in mezzo puo' cambiare le risposte"),
    (r"(?<![\w.])eval\s*\(|(?<![\w.])exec\s*\(", "alto", "eval/exec: esegue testo come codice"),
    (r"pickle\.loads?\s*\(", "medio", "pickle: caricare dati non fidati esegue codice"),
    (r"shell\s*=\s*True|os\.system\s*\(", "medio", "comando di sistema passato alla shell"),
    (r"['\"]http://(?!127\.0\.0\.1|localhost|192\.168\.)", "basso",
     "indirizzo http senza cifratura verso internet"),
]


def _py(cartella):
    for radice, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py") and ".bak" not in f and "prima" not in f:
                yield os.path.join(radice, f)


def _rel(cartella, p):
    return os.path.relpath(p, cartella).replace("\\", "/")


def _reperto(controllo, rel, riga, testo, livello, tipo, dettaglio=""):
    return {"controllo": controllo, "file": rel, "riga": riga, "testo": testo.strip()[:200],
            "livello": livello, "tipo": tipo, "dettaglio": dettaglio}


def _pyflakes(cartella):
    fuori = []
    try:
        from pyflakes import api, messages as M
    except ImportError:
        return [_reperto("pyflakes", "-", 0, "pyflakes non installato", "info", "manutenzione")]

    livelli = {
        M.UndefinedName: ("critico", "malfunzionamento", "nome non definito: NameError appena si passa di li'"),
        M.UndefinedExport: ("alto", "malfunzionamento", "esportato ma non definito"),
        M.UndefinedLocal: ("alto", "malfunzionamento", "variabile usata prima di assegnarla"),
        M.DuplicateArgument: ("alto", "malfunzionamento", "argomento ripetuto"),
        M.RedefinedWhileUnused: ("medio", "manutenzione", "ridefinito senza essere usato: una delle due copie e' morta"),
        M.ImportShadowedByLoopVar: ("medio", "malfunzionamento", "un ciclo sovrascrive un import"),
        M.UnusedImport: ("basso", "manutenzione", "import mai usato"),
        M.UnusedVariable: ("basso", "manutenzione", "variabile assegnata e mai usata"),
        M.ImportStarUsed: ("basso", "manutenzione", "import *"),
    }

    class Raccoglitore(object):
        def __init__(self):
            self.msgs = []

        def unexpectedError(self, nome, msg):
            self.msgs.append(("errore", nome, 0, str(msg)))

        def syntaxError(self, nome, msg, riga, col, testo):
            self.msgs.append(("sintassi", nome, riga or 0, "%s: %s" % (msg, (testo or "").strip())))

        def flake(self, m):
            self.msgs.append((m, m.filename, m.lineno, m.message % m.message_args))

    for p in _py(cartella):
        r = Raccoglitore()
        with io.open(p, encoding="utf-8", errors="replace") as h:
            api.check(h.read(), p, r)
        for m, nome, riga, testo in r.msgs:
            rel = _rel(cartella, p)
            if m in ("errore", "sintassi"):
                fuori.append(_reperto("pyflakes", rel, riga, testo, "critico", "malfunzionamento",
                                      "il file non si carica: tutto cio' che lo importa cade"))
                continue
            liv, tipo, spiega = livelli.get(type(m), ("basso", "manutenzione", type(m).__name__))
            fuori.append(_reperto("pyflakes", rel, riga, testo, liv, tipo, spiega))
    return fuori


def _schemi(cartella, schemi, controllo, tipo):
    fuori = []
    for p in _py(cartella):
        rel = _rel(cartella, p)
        with io.open(p, encoding="utf-8", errors="replace") as h:
            righe = h.read().splitlines()
        for i, riga in enumerate(righe, 1):
            if riga.lstrip().startswith("#"):
                continue
            for schema, livello, spiega in schemi:
                if re.search(schema, riga):
                    if controllo == "sicurezza" and "http://" in riga and (
                            ".m3u8" in riga or '"http://" +' in riga or "'http://' +" in riga):
                        livello, spiega = "info", ("flusso video di terzi, o indirizzo del quaderno comune in casa: "
                                                   "esiste solo in http e non porta dati personali")
                    if controllo == "sicurezza" and "exec(compile(" in riga:
                        # exec del NOSTRO catalogo.py (canale dentro s4me): non entra
                        # testo da fuori, quindi non e' una vulnerabilita'. Il rischio
                        # vero e' un altro: un errore in catalogo.py rompe anche s4me.
                        livello, spiega = "info", ("exec di un file dell'add-on (catalogo.py): non e' una "
                                                   "vulnerabilita', ma un errore di sintassi li' fa cadere anche il canale in s4me")
                    fuori.append(_reperto(controllo, rel, i, riga, livello, tipo, spiega))
    return fuori


class _Visita(ast.NodeVisitor):
    """Instabilita' che si vedono solo nella struttura del codice."""

    def __init__(self, rel, servizio):
        self.rel, self.servizio, self.fuori = rel, servizio, []
        self.funzione = "(modulo)"
        self.complessita = {}

    def _f(self, nodo, testo, livello, tipo, spiega):
        self.fuori.append(_reperto("instabilita", self.rel, getattr(nodo, "lineno", 0),
                                   "%s  [in %s]" % (testo, self.funzione), livello, tipo, spiega))

    def visit_FunctionDef(self, nodo):
        prima = self.funzione
        self.funzione = nodo.name
        rami = sum(isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp,
                                  ast.ExceptHandler, ast.IfExp)) for n in ast.walk(nodo))
        righe = getattr(nodo, "end_lineno", nodo.lineno) - nodo.lineno + 1
        self.complessita[nodo.name] = (rami, righe, nodo.lineno)
        self.generic_visit(nodo)
        self.funzione = prima

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ExceptHandler(self, nodo):
        corpo_vuoto = all(isinstance(b, ast.Pass) or (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant))
                          for b in nodo.body)
        if nodo.type is None:
            self._f(nodo, "except: nudo", "medio", "instabilita",
                    "prende anche l'uscita di Kodi (SystemExit): il servizio puo' non chiudersi")
        elif corpo_vuoto:
            self._f(nodo, "except ...: pass", "basso", "instabilita",
                    "errore ingoiato in silenzio: il guasto c'e' ma nessun registro lo dice")
        self.generic_visit(nodo)

    def visit_Call(self, nodo):
        f = nodo.func
        nome = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        if nome == "urlopen" and not any(k.arg == "timeout" for k in nodo.keywords) and len(nodo.args) < 3:
            self._f(nodo, "urlopen senza timeout", "alto", "instabilita",
                    "se il sito non risponde resta appeso per sempre (e con lui la riga o il servizio)")
        if nome == "sleep" and isinstance(f, ast.Attribute) and getattr(f.value, "id", "") == "time" and self.servizio:
            self._f(nodo, "time.sleep nel servizio", "medio", "instabilita",
                    "Kodi non riesce a chiudere il servizio mentre dorme: si usa monitor.waitForAbort")
        if nome == "Thread" and not any(k.arg == "daemon" for k in nodo.keywords):
            self._f(nodo, "Thread senza daemon", "basso", "instabilita", "puo' tenere Kodi aperto in chiusura")
        self.generic_visit(nodo)

    def visit_While(self, nodo):
        if isinstance(nodo.test, ast.Constant) and nodo.test.value is True:
            testo = ast.dump(nodo)
            if "waitForAbort" not in testo and "abortRequested" not in testo and "break" not in testo.lower():
                self._f(nodo, "while True senza uscita", "alto", "instabilita",
                        "ciclo che non guarda la chiusura di Kodi")
        self.generic_visit(nodo)


def _struttura(cartella):
    fuori, complesse, scritture = [], [], []
    for p in _py(cartella):
        rel = _rel(cartella, p)
        with io.open(p, encoding="utf-8", errors="replace") as h:
            src = h.read()
        try:
            albero = ast.parse(src)
        except SyntaxError:
            continue
        v = _Visita(rel, servizio=rel in ("service.py",) or "sentinella" in rel)
        v.visit(albero)
        fuori += v.fuori
        for nome, (rami, righe, riga) in v.complessita.items():
            complesse.append({"file": rel, "funzione": nome, "riga": riga, "rami": rami, "righe": righe})
        # scritture non atomiche di file di dati (json.dumps/json.dump dritti nel file finale)
        for i, riga in enumerate(src.splitlines(), 1):
            if re.search(r"io\.open\([^)]*['\"]w['\"]|open\([^)]*['\"]w['\"]", riga):
                blocco = "\n".join(src.splitlines()[i - 1:i + 3])
                if "json" in blocco and ".tmp" not in blocco and "os.replace" not in src[max(0, src.find(riga)):src.find(riga) + 600]:
                    scritture.append(_reperto("scrittura non atomica", rel, i, riga, "medio", "instabilita",
                                              "il file si scrive direttamente: se il box si spegne a meta' "
                                              "(riavvii da calore) resta un JSON troncato e i dati si perdono"))
    complesse.sort(key=lambda x: (-x["rami"], -x["righe"]))
    for c in complesse[:15]:
        if c["rami"] >= 40 or c["righe"] >= 200:
            fuori.append(_reperto("complessita", c["file"], c["riga"],
                                  "%s: %d rami, %d righe" % (c["funzione"], c["rami"], c["righe"]),
                                  "basso", "manutenzione",
                                  "funzione troppo lunga/ramificata: ogni modifica rischia di rompere un ramo lontano"))
    return fuori + scritture, complesse[:25]


def _xml(cartella):
    fuori = []
    for radice, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".xml"):
                continue
            p = os.path.join(radice, f)
            rel = _rel(cartella, p)
            try:
                ET.parse(p)
            except ET.ParseError as e:
                fuori.append(_reperto("xml", rel, getattr(e, "position", (0,))[0], str(e), "critico",
                                      "malfunzionamento", "XML malformato: Kodi non lo carica"))
    ax = os.path.join(cartella, "addon.xml")
    if os.path.exists(ax):
        with io.open(ax, encoding="utf-8", errors="replace") as h:
            t = h.read()
        for m in re.finditer(r"<(icon|fanart|screenshot)>([^<]+)</\1>", t):
            if not os.path.exists(os.path.join(cartella, m.group(2))):
                fuori.append(_reperto("addon.xml", "addon.xml", 0, m.group(0), "basso", "aspetto",
                                      "immagine dichiarata ma mancante"))
        m = re.search(r'<import addon="xbmc.python" version="([^"]+)"', t)
        if m and not m.group(1).startswith("3."):
            fuori.append(_reperto("addon.xml", "addon.xml", 0, m.group(0), "critico", "malfunzionamento",
                                  "xbmc.python < 3: Kodi 19+ non lo carica"))
    return fuori


def _risorse(cartella):
    """Percorsi di file dell'add-on scritti nel codice che non esistono."""
    fuori = []
    for p in _py(cartella):
        rel = _rel(cartella, p)
        with io.open(p, encoding="utf-8", errors="replace") as h:
            righe = h.read().splitlines()
        for i, riga in enumerate(righe, 1):
            for m in re.finditer(r"special://home/addons/plugin\.video\.saghe/([\w/.\-]+\.(?:png|jpg|json|xml))", riga):
                if not os.path.exists(os.path.join(cartella, m.group(1))):
                    fuori.append(_reperto("risorsa", rel, i, m.group(0), "medio", "aspetto",
                                          "file indicato ma assente: a schermo quadrato vuoto o nero"))
            for m in re.finditer(r"_leggi_risorsa\(\s*['\"]([^'\"]+)['\"]", riga):
                if not os.path.exists(os.path.join(cartella, "resources", m.group(1))):
                    fuori.append(_reperto("risorsa", rel, i, m.group(0), "alto", "malfunzionamento",
                                          "risorsa JSON assente: la funzione lavora su dati vuoti"))
    return fuori


def _compatibilita(cartella):
    """Il codice deve girare anche col Python piu' vecchio di casa (Kodi 20 del Raspberry)."""
    fuori = []
    for p in _py(cartella):
        rel = _rel(cartella, p)
        with io.open(p, encoding="utf-8", errors="replace") as h:
            src = h.read()
        try:
            ast.parse(src, feature_version=(3, 8))
        except SyntaxError as e:
            fuori.append(_reperto("compatibilita", rel, e.lineno or 0, str(e.msg), "alto", "malfunzionamento",
                                  "sintassi piu' nuova di Python 3.8: su un Kodi con Python vecchio non si carica"))
    return fuori


def analizza(cartella_addon):
    reperti = []
    reperti += _pyflakes(cartella_addon)
    reperti += _schemi(cartella_addon, API_KODI, "api kodi", "malfunzionamento")
    reperti += _schemi(cartella_addon, SICUREZZA, "sicurezza", "vulnerabilita")
    strutt, complesse = _struttura(cartella_addon)
    reperti += strutt
    reperti += _xml(cartella_addon)
    reperti += _risorse(cartella_addon)
    reperti += _compatibilita(cartella_addon)
    return {"reperti": reperti, "funzioni_complesse": complesse}
