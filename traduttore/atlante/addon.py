# -*- coding: utf-8 -*-
"""ADDON: il nostro plugin.video.saghe letto come codice, non a occhio.

Tutti i guasti "silenziosi" della Videoteca hanno avuto la stessa forma: una
cosa che il codice chiede e che non esiste, e nessun registro che protesta.
- un collegamento a un'azione che il router non gestisce (riapre il menu)
- un RunScript con un comando che avvio.py non conosce
- un'impostazione letta ma mai dichiarata, o dichiarata senza default
- una finestra aperta DENTRO una cartella (i due busydialog del 06/09)
- un Container.Refresh che rilegge la cartella che lo ha lanciato (10/09)
- una riga della home che va in rete
- un file di risorse chiamato col nome sbagliato

IL CONTESTO CONTA (capito l'11/09/2026, dopo i primi falsi allarmi)
    La stessa finestra e' pericolosa se l'azione arriva da una CARTELLA
    (Kodi ha la sua rotellina davanti), ed e' giusta se arriva dal menu
    contestuale (RunPlugin: nessuna rotellina). Per ogni azione si guarda
    come viene collegata:
        runplugin  "RunPlugin(%s)" % url(azione=...)      -> sicuro
        cartella   addDirectoryItem(..., url(...), li, True) -> rischio
        voce       addDirectoryItem(..., url(...), li, False) -> riproduzione
        menu       riga della home (skinshortcuts)          -> cartella
    e per ogni funzione si risale a quali azioni la raggiungono.
"""

import ast
import collections
import io
import json
import os
import re

FINESTRE = {"Dialog", "DialogProgress", "WindowXML", "WindowXMLDialog", "WindowDialog"}
METODI_FINESTRA = {"ok", "yesno", "select", "multiselect", "input", "textviewer",
                   "contextmenu", "browse", "numeric", "yesnocustom", "doModal"}


def _file_py(cartella):
    for radice, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py") and ".bak" not in f and "prima" not in f:
                yield os.path.join(radice, f)


def _costante(nodo):
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else None


def _letture_indirette(moduli, dichiarate):
    """Impostazioni lette senza scriverne il nome nella getSetting: il nome sta in una
    tabella ("chiave_abbonamento": "ha_netflix"), passa da un aiutante
    (_impostazione("prossimo_attesa")) o si compone ("scadenza_" + fonte_id)."""
    testi, prefissi = set(), set()
    for m in moduli.values():
        for n in ast.walk(m.albero):
            if _costante(n):
                testi.add(n.value)
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and _costante(n.left):
                prefissi.add(n.left.value)
    return {k for k in dichiarate if k in testi or any(p and k.startswith(p) for p in prefissi)}


def _nome_chiamata(nodo):
    f = nodo.func
    if isinstance(f, ast.Name):
        return None, f.id
    if isinstance(f, ast.Attribute):
        base = f.value
        if isinstance(base, ast.Name):
            return base.id, f.attr
        if isinstance(base, ast.Call):
            b, n = _nome_chiamata(base)
            return (n or b), f.attr
        if isinstance(base, ast.Attribute):
            return base.attr, f.attr
        return None, f.attr
    return None, None


def _valori(nodi):
    fuori = []
    for c in nodi:
        if _costante(c):
            fuori.append(_costante(c))
        elif isinstance(c, (ast.Tuple, ast.List, ast.Set)):
            fuori += [_costante(x) for x in c.elts if _costante(x)]
    return fuori


def _e_split(nodo):
    """quale.split(":")[0]  oppure  quale.split(":")"""
    if isinstance(nodo, ast.Subscript):
        nodo = nodo.value
    return isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "split"


class _Modulo(object):
    def __init__(self, nome, percorso, sorgente):
        self.nome, self.percorso, self.sorgente = nome, percorso, sorgente
        self.albero = ast.parse(sorgente)
        self.alias, self.funzioni = {}, {}
        self.chiamate = collections.defaultdict(set)
        self.genitori = {}
        for n in ast.walk(self.albero):
            for figlio in ast.iter_child_nodes(n):
                self.genitori[figlio] = n
            if isinstance(n, ast.ImportFrom):
                for a in n.names:
                    self.alias[a.asname or a.name] = ((n.module or "") + "." + a.name).strip(".")
            elif isinstance(n, ast.Import):
                for a in n.names:
                    self.alias[a.asname or a.name] = a.name
        for n in self.albero.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funzioni[n.name] = n
        for nome_f, f in self.funzioni.items():
            for c in ast.walk(f):
                if isinstance(c, ast.Call):
                    self.chiamate[nome_f].add(_nome_chiamata(c))

    def funzione_di(self, riga):
        for nome, f in self.funzioni.items():
            if f.lineno <= riga <= getattr(f, "end_lineno", f.lineno):
                return nome
        return "(modulo)"

    def contesto_url(self, chiamata):
        """Come viene usato un url(azione=...): runplugin, cartella, voce, altro."""
        n = chiamata
        for _ in range(6):
            g = self.genitori.get(n)
            if g is None:
                break
            if isinstance(g, ast.BinOp) and _costante(g.left) and "RunPlugin" in _costante(g.left):
                return "runplugin"
            if isinstance(g, ast.JoinedStr) and any("RunPlugin" in (_costante(v) or "") for v in g.values):
                return "runplugin"
            if isinstance(g, ast.Call):
                _b, fn = _nome_chiamata(g)
                if fn == "addDirectoryItem":
                    cart = g.args[3] if len(g.args) > 3 else next((k.value for k in g.keywords if k.arg == "isFolder"), None)
                    if isinstance(cart, ast.Constant):
                        return "cartella" if cart.value else "voce"
                    return "cartella?"
                if fn in ("executebuiltin",) and g.args and "RunPlugin" in (_costante(g.args[0]) or ""):
                    return "runplugin"
            if isinstance(g, (ast.Assign, ast.FunctionDef, ast.Return)):
                if isinstance(g, ast.Assign):
                    # dove, cartella = url(...), True   -> guarda il secondo valore della tupla
                    if isinstance(g.value, ast.Tuple) and len(g.value.elts) == 2 and \
                            isinstance(g.value.elts[1], ast.Constant) and isinstance(g.value.elts[1].value, bool):
                        return "cartella" if g.value.elts[1].value else "voce"
                return "variabile"
            n = g
        return "altro"


def _aggiungi(d, chiave, valore, limite=10):
    if len(d[chiave]) < limite:
        d[chiave].append(valore)


def analizza(cartella_addon, cartella_menu=None):
    moduli, errori_sintassi = {}, []
    for p in _file_py(cartella_addon):
        nome = os.path.relpath(p, cartella_addon).replace("\\", "/")[:-3].replace("/", ".")
        with io.open(p, encoding="utf-8", errors="replace") as h:
            src = h.read()
        try:
            moduli[nome] = _Modulo(nome, p, src)
        except SyntaxError as e:
            errori_sintassi.append("%s:%s %s" % (nome, e.lineno, e.msg))

    azioni_gestite, rami_router = {}, {}
    link = collections.defaultdict(list)
    contesti = collections.defaultdict(set)
    widget_gestiti, comandi_avvio = set(), {}
    runscript = collections.defaultdict(list)
    art, proprieta, infotag = (collections.defaultdict(list) for _ in range(3))
    contenuti, builtin, impost_usate, risorse = (collections.defaultdict(list) for _ in range(4))
    finestre, refresh, senza_contenuto = [], [], []

    for nome, m in moduli.items():
        rel = os.path.relpath(m.percorso, cartella_addon).replace("\\", "/")
        for n in ast.walk(m.albero):
            riga = getattr(n, "lineno", 0)
            dove = "%s:%d" % (rel, riga)
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and nome == "main":
                t = n.test
                if isinstance(t.left, ast.Name) and t.left.id == "azione":
                    corpo_fine = max(getattr(b, "end_lineno", b.lineno) for b in n.body)
                    chiamate = {_nome_chiamata(c)[1] for b in n.body for c in ast.walk(b) if isinstance(c, ast.Call)}
                    for v in _valori(t.comparators):
                        azioni_gestite.setdefault(v, dove)
                        rami_router[v] = {"da": n.body[0].lineno, "a": corpo_fine,
                                          "funzioni": sorted(x for x in chiamate if x and x in m.funzioni)}
            if isinstance(n, ast.Compare):
                if isinstance(n.left, ast.Name):
                    if n.left.id == "azione" and nome == "main":
                        for v in _valori(n.comparators):
                            azioni_gestite.setdefault(v, dove)
                    elif n.left.id == "quale" and nome == "main":
                        widget_gestiti.update(_valori(n.comparators))
                    elif n.left.id == "comando" and nome == "avvio":
                        for v in _valori(n.comparators):
                            comandi_avvio.setdefault(v, dove)
                elif _e_split(n.left) and nome == "main":
                    widget_gestiti.update(_valori(n.comparators))
            if isinstance(n, ast.Assign):
                # arte["clearlogo"] = ...   (la forma piu' usata nel nostro codice)
                for bersaglio in n.targets:
                    if isinstance(bersaglio, ast.Subscript) and isinstance(bersaglio.value, ast.Name) and \
                            bersaglio.value.id in ("arte", "art", "immagini") and _costante(bersaglio.slice):
                        _aggiungi(art, _costante(bersaglio.slice), dove)
            if isinstance(n, ast.Call):
                base, fn = _nome_chiamata(n)
                if fn == "url":
                    for k in n.keywords:
                        if k.arg == "azione" and _costante(k.value):
                            a = _costante(k.value)
                            _aggiungi(link, a, dove)
                            contesti[a].add(m.contesto_url(n))
                if fn == "setArt" and n.args and isinstance(n.args[0], ast.Dict):
                    for k in n.args[0].keys:
                        if _costante(k):
                            _aggiungi(art, _costante(k), dove)
                if fn == "setProperty" and n.args and _costante(n.args[0]):
                    _aggiungi(proprieta, _costante(n.args[0]), dove)
                if fn and re.match(r"set(Title|Plot|PlotOutline|Year|Episode|Season|MediaType|TvShowTitle|Rating|"
                                   r"Genres|Duration|ResumePoint|Premiered|UniqueIDs|Trailer|Tagline|Studios|"
                                   r"Countries|Cast|Votes|OriginalTitle|Directors|Writers|FirstAired|Path|"
                                   r"Filenameandpath|DbId|Mpaa|UserRating|Top250|IMDBNumber)$", fn):
                    _aggiungi(infotag, fn, dove)
                if fn == "setContent" and len(n.args) > 1 and _costante(n.args[1]):
                    _aggiungi(contenuti, _costante(n.args[1]), dove)
                if fn == "executebuiltin" and n.args:
                    s = _costante(n.args[0])
                    if s is None and isinstance(n.args[0], ast.BinOp):
                        s = _costante(n.args[0].left)
                    if s:
                        cmd = re.match(r"([A-Za-z.]+)", s)
                        _aggiungi(builtin, cmd.group(1) if cmd else s, dove)
                        rs = re.match(r"RunScript\(plugin\.video\.saghe\s*,\s*([A-Za-z0-9_]+)", s)
                        if rs:
                            _aggiungi(runscript, rs.group(1), dove)
                        if s.startswith("Container.Refresh") and nome == "main":
                            refresh.append({"dove": dove, "riga": riga, "funzione": m.funzione_di(riga)})
                if fn in ("getSetting", "getSettingBool", "getSettingInt", "getSettingNumber",
                          "getSettingString", "setSetting", "setSettingBool") and n.args and \
                        _costante(n.args[0]) and base not in ("s4", "s4me"):
                    _aggiungi(impost_usate, _costante(n.args[0]), dove)
                if fn == "_leggi_risorsa" and n.args and _costante(n.args[0]):
                    _aggiungi(risorse, "resources/" + _costante(n.args[0]), dove)
                if nome == "main" and (fn in FINESTRE - {"Dialog"} and base in ("xbmcgui", None) or
                                       (base in ("Dialog", "DialogProgress") and fn in METODI_FINESTRA)):
                    finestre.append({"dove": dove, "riga": riga, "funzione": m.funzione_di(riga),
                                     "chiamata": "%s.%s" % (base, fn) if base else fn})
                if nome == "main" and fn == "endOfDirectory":
                    for k in n.keywords:
                        if k.arg == "succeeded" and isinstance(k.value, ast.Constant) and k.value.value is False:
                            senza_contenuto.append({"dove": dove, "funzione": m.funzione_di(riga)})
            s = _costante(n)
            if s:
                for a in re.findall(r"plugin://plugin\.video\.saghe/\?[^\"'\s]*?azione=([A-Za-z0-9_]+)", s):
                    _aggiungi(link, a, dove)
                    contesti[a].add("indirizzo")

    # ---- ROUTER, RIGHE E COMANDI A TABELLA (11/09/2026: instrada, widget e il main di
    #      avvio.py sono dizionari; senza leggerli sembrerebbe sparito ogni collegamento)
    for nome_mod, m in moduli.items():
        rel_m = os.path.relpath(m.percorso, cartella_addon).replace("\\", "/")
        for n in m.albero.body:
            if not (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.Dict)):
                continue
            var = n.targets[0].id
            if nome_mod == "main" and var == "AZIONI":
                for k, v in zip(n.value.keys, n.value.values):
                    if not _costante(k):
                        continue
                    azioni_gestite.setdefault(_costante(k), "%s:%d" % (rel_m, k.lineno))
                    chiamate = {_nome_chiamata(c)[1] for c in ast.walk(v) if isinstance(c, ast.Call)}
                    if isinstance(v, ast.Name):
                        chiamate.add(v.id)
                    rami_router[_costante(k)] = {"da": v.lineno, "a": getattr(v, "end_lineno", v.lineno),
                                                 "funzioni": sorted(x for x in chiamate if x and x in m.funzioni)}
            elif nome_mod == "main" and var == "RIGHE_HOME":
                widget_gestiti.update(_costante(k) for k in n.value.keys if _costante(k))
        if nome_mod == "avvio":
            for n in ast.walk(m.albero):
                if isinstance(n, ast.Dict) and n.keys and all(_costante(k) for k in n.keys) \
                        and all(isinstance(v, ast.Name) for v in n.values):
                    for k in n.keys:
                        comandi_avvio.setdefault(_costante(k), "%s:%d" % (rel_m, k.lineno))

    # ---- chi raggiunge una funzione di main.py: azioni del router e funzioni intermedie
    main = moduli.get("main")
    raggiunta_da = collections.defaultdict(set)
    if main:
        grafo = {f: {c[1] for c in main.chiamate.get(f, ()) if c[1] in main.funzioni and c[0] is None}
                 for f in main.funzioni}
        for az, ramo in rami_router.items():
            coda, visti = list(ramo["funzioni"]), set()
            while coda:
                f = coda.pop()
                if f in visti:
                    continue
                visti.add(f)
                raggiunta_da[f].add(az)
                coda.extend(grafo.get(f, ()))

    def azioni_per(voce):
        if voce["funzione"] == "instrada":
            return {az for az, r in rami_router.items() if r["da"] <= voce["riga"] <= r["a"]}
        return raggiunta_da.get(voce["funzione"], set())

    if "widget" in widget_gestiti or True:
        contesti["widget"].add("menu")
    cartella_widget = {"widget"}
    for voce in finestre + refresh:
        az = azioni_per(voce)
        voce["azioni"] = sorted(az)
        ctx = set()
        for a in az:
            ctx |= contesti.get(a, set())
            if a in cartella_widget:
                ctx.add("menu")
        voce["contesti"] = sorted(ctx)
        if not az:
            voce["rischio"] = "sconosciuto"
        elif ctx and ctx <= {"runplugin"}:
            voce["rischio"] = "nessuno"
        elif ctx and voce in refresh and ctx <= {"runplugin", "voce"}:
            # Un Refresh da una voce che non e' cartella: Kodi la esegue come RunPlugin,
            # non rilegge la cartella che l'ha lanciata. Nessun ciclo.
            voce["rischio"] = "nessuno"
        elif ctx & {"cartella", "cartella?", "menu", "indirizzo"}:
            voce["rischio"] = "cartella"
        elif "voce" in ctx:
            voce["rischio"] = "voce"
        else:
            voce["rischio"] = "sconosciuto"
    senza = {c["funzione"] for c in senza_contenuto}
    for r in refresh:
        r["chiude_senza_contenuto"] = r["funzione"] in senza or any(
            c["funzione"] == "instrada" for c in senza_contenuto) and r["funzione"] == "instrada" and False

    # ---- impostazioni dichiarate
    dichiarate = {}
    sx = os.path.join(cartella_addon, "resources", "settings.xml")
    if os.path.exists(sx):
        with io.open(sx, encoding="utf-8", errors="replace") as h:
            t = h.read()
        for mm in re.finditer(r'<setting\s+id="([^"]+)"([^>]*?)(/>|>(.*?)</setting>)', t, re.S):
            corpo = mm.group(4) or ""
            tipo = re.search(r'type="([^"]+)"', mm.group(2))
            dichiarate[mm.group(1)] = {"tipo": tipo.group(1) if tipo else "",
                                       "default": "<default" in corpo or 'default="' in mm.group(2),
                                       "vuoto_permesso": "allowempty" in corpo}

    # ---- rete raggiungibile da widget()
    def risolvi(mod, alias_nome, fn):
        if alias_nome is None:
            if fn in mod.funzioni:
                return mod.nome, fn
            dest = mod.alias.get(fn)
            if dest and dest.rsplit(".", 1)[0] in moduli and dest.rsplit(".", 1)[-1] in moduli[dest.rsplit(".", 1)[0]].funzioni:
                return dest.rsplit(".", 1)[0], dest.rsplit(".", 1)[-1]
            return None
        dest = mod.alias.get(alias_nome)
        if dest and dest in moduli and fn in moduli[dest].funzioni:
            return dest, fn
        return None

    rete = []
    if main and "widget" in main.funzioni:
        visitati, coda = set(), [("main", "widget", ["main.widget"])]
        while coda:
            mod, fn, catena = coda.pop()
            if (mod, fn) in visitati or len(catena) > 10:
                continue
            visitati.add((mod, fn))
            mm = moduli[mod]
            for alias_nome, chiamato in mm.chiamate.get(fn, ()):
                if not chiamato:
                    continue
                if chiamato == "urlopen" or (alias_nome in ("requests",) and chiamato in ("get", "post")):
                    rete.append({"catena": catena + ["%s.%s" % (alias_nome, chiamato)]})
                    continue
                r = risolvi(mm, alias_nome, chiamato)
                if r:
                    coda.append((r[0], r[1], catena + ["%s.%s" % r]))

    mancanti = [{"file": k, "dove": v} for k, v in sorted(risorse.items())
                if not os.path.exists(os.path.join(cartella_addon, k))]

    # ---- menu della home (skinshortcuts)
    menu = {}
    if cartella_menu and os.path.isdir(cartella_menu):
        p = os.path.join(cartella_menu, "skin.arctic.zephyr.mod.properties")
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as h:
                props = json.load(h)
            per_voce = collections.defaultdict(dict)
            for _g, lab, k, v in (x[:4] for x in props):
                per_voce[lab][k] = v
            righe, senza_target, spente = [], [], []
            for lab, d in per_voce.items():
                for k, v in d.items():
                    mm = re.match(r"widgetPath(\.\d+)?$", k)
                    if not mm:
                        continue
                    suf = mm.group(1) or ""
                    che = v.split("che=")[-1] if "che=" in v else v
                    righe.append({"voce": lab, "posto": suf or ".1", "che": che, "nome": d.get("widgetName" + suf, "")})
                    if not d.get("widgetTarget" + suf):
                        senza_target.append("%s%s" % (lab, suf))
                    if suf and d.get("widgetEnable" + suf) != "yes":
                        spente.append("%s%s" % (lab, suf))
            base = {w.split(":")[0] for w in widget_gestiti}
            non_gestiti = sorted({r["che"] for r in righe if r["che"] not in widget_gestiti and r["che"].split(":")[0] not in base})
            menu = {"righe": righe, "senza_target": senza_target, "spente": spente,
                    "che_non_gestiti": non_gestiti, "voci": sorted(per_voce)}

    return {
        "cartella": cartella_addon,
        "moduli": {k: {"righe": len(m.sorgente.splitlines()), "funzioni": len(m.funzioni)} for k, m in sorted(moduli.items())},
        "errori_sintassi": errori_sintassi,
        "azioni_gestite": azioni_gestite,
        "rami_router": rami_router,
        "azioni_collegate": {k: v for k, v in sorted(link.items())},
        "contesti_azioni": {k: sorted(v) for k, v in sorted(contesti.items())},
        "azioni_senza_gestore": sorted(k for k in link if k not in azioni_gestite),
        "azioni_mai_collegate": sorted(k for k in azioni_gestite if k not in link),
        "widget_gestiti": sorted(widget_gestiti),
        "comandi_avvio": comandi_avvio,
        "runscript_usati": dict(runscript),
        "runscript_senza_comando": sorted(k for k in runscript if k not in comandi_avvio),
        "art_date": dict(sorted(art.items())),
        "proprieta_date": dict(sorted(proprieta.items())),
        "infotag": dict(sorted(infotag.items())),
        "tipi_contenuto": dict(contenuti),
        "comandi_kodi": dict(builtin),
        "impostazioni": {
            "dichiarate": dichiarate, "usate": dict(impost_usate),
            "usate_non_dichiarate": sorted(k for k in impost_usate if k not in dichiarate),
            "dichiarate_mai_usate": sorted(k for k in dichiarate if k not in impost_usate
                                           and k not in _letture_indirette(moduli, dichiarate)),
            "senza_default": sorted(k for k, v in dichiarate.items() if not v["default"]),
        },
        "finestre_in_cartella": finestre,
        "refresh_in_cartella": refresh,
        "cartelle_senza_contenuto": senza_contenuto,
        "rete_nelle_righe": rete,
        "risorse_mancanti": mancanti,
        "menu": menu,
    }
