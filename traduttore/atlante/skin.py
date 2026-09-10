# -*- coding: utf-8 -*-
"""SKIN: cosa legge e cosa pretende una skin di Kodi, file per file.

Una skin non "chiama" l'add-on: LEGGE. Legge le immagini di ogni voce
(ListItem.Art(poster)), le etichette (ListItem.Plot, ListItem.Year...), le
proprieta' (ListItem.Property(x), Window(Home).Property(x)), e riempie le
liste da indirizzi (<content target="videos">plugin://...</content>).
Se l'add-on non da' una di queste cose, a schermo resta un buco e NESSUN
registro lo dice. Qui si fa l'elenco completo di cosa legge, con file e riga,
cosi' si puo' confrontare con cosa l'add-on da' davvero (vedi incroci.py).

Arctic Zephyr costruisce la home con script.skinshortcuts: le proprieta'
dei widget (widgetPath, widgetTarget, widgetEnable.N...) stanno in
shortcuts/template.xml e overrides.xml, e si leggono anche quelle.
"""

import collections
import io
import os
import re

SCHEMI = {
    "art": re.compile(r"ListItem(?:Absolute|NoWrap)?\.Art\(([^)\]]+)\)", re.I),
    "proprieta_voce": re.compile(r"ListItem(?:Absolute|NoWrap)?\.Property\(([^)\]]+)\)", re.I),
    "etichetta_voce": re.compile(r"ListItem(?:Absolute|NoWrap)?\.([A-Za-z0-9_]+)(?![A-Za-z0-9_(])"),
    "proprieta_finestra": re.compile(r"Window(?:\(([^)]*)\))?\.Property\(([^)\]]+)\)", re.I),
    "skin_testo": re.compile(r"Skin\.(?:String|SetString)\(([^,)\]]+)", re.I),
    "skin_interruttore": re.compile(r"Skin\.(?:HasSetting|ToggleSetting|SetBool|Reset)\(([^,)\]]+)", re.I),
    "contenuto_tipo": re.compile(r"Container(?:\(\d+\))?\.Content\(([^)\]]+)\)", re.I),
    "variabile_usata": re.compile(r"\$VAR\[([^\]]+)\]"),
    "espressione_usata": re.compile(r"\$EXP\[([^\]]+)\]"),
    "localizza": re.compile(r"\$LOCALIZE\[(\d+)\]"),
}
AZIONI_TAG = ("onclick", "onload", "onunload", "onfocus", "onunfocus", "onback", "onup",
              "ondown", "onleft", "onright", "oninfo")
ETICHETTE_IGNORATE = {"Art", "Property"}


def _xml(cartella):
    for radice, _d, files in os.walk(cartella):
        for f in files:
            if f.lower().endswith(".xml"):
                yield os.path.join(radice, f)


def analizza(cartella_skin, nome=""):
    if not cartella_skin or not os.path.isdir(cartella_skin):
        return {"errore": "skin non trovata: %s" % cartella_skin}
    trovati = {k: collections.defaultdict(list) for k in SCHEMI}
    include_def, include_uso = {}, collections.defaultdict(list)
    var_def, exp_def = {}, {}
    comandi = collections.Counter()
    comandi_dove = collections.defaultdict(list)
    contenuti, finestre, font_usati = [], [], collections.Counter()
    shortcuts_prop = collections.defaultdict(list)
    n_file = 0
    for p in _xml(cartella_skin):
        n_file += 1
        rel = os.path.relpath(p, cartella_skin).replace("\\", "/")
        with io.open(p, encoding="utf-8", errors="replace") as h:
            righe = h.read().splitlines()
        testo = "\n".join(righe)
        if re.search(r"<window\b", testo):
            m = re.search(r"<window\b([^>]*)>", testo)
            finestre.append({"file": rel, "attributi": m.group(1).strip() if m else "",
                             "controlli": len(re.findall(r"<control\b", testo))})
        for i, riga in enumerate(righe, 1):
            dove = "%s:%d" % (rel, i)
            for chiave, schema in SCHEMI.items():
                for m in schema.finditer(riga):
                    if chiave == "proprieta_finestra":
                        valore = "%s:%s" % ((m.group(1) or "corrente").strip(), m.group(2).strip())
                    else:
                        valore = m.group(1).strip()
                    if chiave == "etichetta_voce" and valore in ETICHETTE_IGNORATE:
                        continue
                    if len(trovati[chiave][valore]) < 6:
                        trovati[chiave][valore].append(dove)
                    else:
                        trovati[chiave][valore].append(None)
            for m in re.finditer(r'<include\s+name="([^"]+)"', riga):
                include_def.setdefault(m.group(1), dove)
            for m in re.finditer(r"<include(?:\s+content=\"([^\"]+)\"|\s[^>]*)?>([^<]+)</include>", riga):
                include_uso[(m.group(2) or "").strip()].append(dove)
            for m in re.finditer(r'<include\s+content="([^"]+)"', riga):
                include_uso[m.group(1).strip()].append(dove)
            for m in re.finditer(r'<variable\s+name="([^"]+)"', riga):
                var_def.setdefault(m.group(1), dove)
            for m in re.finditer(r'<expression\s+name="([^"]+)"', riga):
                exp_def.setdefault(m.group(1), dove)
            for tag in AZIONI_TAG:
                for m in re.finditer(r"<%s\b[^>]*>([^<]+)</%s>" % (tag, tag), riga):
                    for c in re.findall(r"([A-Za-z][A-Za-z0-9.]*)\(", m.group(1)):
                        comandi[c] += 1
                        if len(comandi_dove[c]) < 4:
                            comandi_dove[c].append(dove)
            for m in re.finditer(r"<content\b([^>]*)>([^<]*)</content>", riga):
                target = re.search(r'target="([^"]*)"', m.group(1))
                contenuti.append({"dove": dove, "target": target.group(1) if target else "",
                                  "percorso": m.group(2).strip()})
            for m in re.finditer(r"<font>([^<$]+)</font>", riga):
                font_usati[m.group(1).strip()] += 1
            if rel.startswith("shortcuts/"):
                for m in re.finditer(r'attribute="name\|([^"]+)"|property="([^"]+)"', riga):
                    k = m.group(1) or m.group(2)
                    if len(shortcuts_prop[k]) < 3:
                        shortcuts_prop[k].append(dove)

    def compatta(d):
        return {k: {"volte": len(v), "dove": [x for x in v if x][:6]} for k, v in sorted(d.items())}

    font_definiti = []
    for cand in ("1080i/Font.xml", "xml/Font.xml", "720p/Font.xml", "16x9/Font.xml"):
        p = os.path.join(cartella_skin, cand)
        if os.path.exists(p):
            with io.open(p, encoding="utf-8", errors="replace") as h:
                font_definiti = sorted(set(re.findall(r"<name>([^<]+)</name>", h.read())))
            break
    generati = ("skinshortcuts-",)
    include_mancanti = sorted(k for k in include_uso if k and k not in include_def
                              and not k.startswith(generati) and "$PARAM" not in k)
    versione = ""
    addon_xml = os.path.join(cartella_skin, "addon.xml")
    if os.path.exists(addon_xml):
        with io.open(addon_xml, encoding="utf-8", errors="replace") as h:
            m = re.search(r'<addon\b[^>]*version="([^"]+)"', h.read())
            versione = m.group(1) if m else ""
    return {
        "nome": nome or os.path.basename(cartella_skin), "versione": versione, "file_xml": n_file,
        "finestre": finestre,
        "art": compatta(trovati["art"]),
        "etichette_voce": compatta(trovati["etichetta_voce"]),
        "proprieta_voce": compatta(trovati["proprieta_voce"]),
        "proprieta_finestra": compatta(trovati["proprieta_finestra"]),
        "impostazioni_testo": compatta(trovati["skin_testo"]),
        "impostazioni_interruttore": compatta(trovati["skin_interruttore"]),
        "tipi_contenuto": compatta(trovati["contenuto_tipo"]),
        "comandi": {k: {"volte": v, "dove": comandi_dove[k]} for k, v in comandi.most_common()},
        "contenuti": contenuti,
        "include_definiti": len(include_def),
        "include_mancanti": include_mancanti,
        "include_generati_da_skinshortcuts": sorted(k for k in include_uso if k.startswith(generati)),
        "variabili_mancanti": sorted(k for k in trovati["variabile_usata"] if k not in var_def),
        "espressioni_mancanti": sorted(k for k in trovati["espressione_usata"] if k not in exp_def),
        "font_definiti": font_definiti,
        "font_usati": dict(font_usati.most_common()),
        "proprieta_widget_skinshortcuts": {k: v for k, v in sorted(shortcuts_prop.items())},
    }
