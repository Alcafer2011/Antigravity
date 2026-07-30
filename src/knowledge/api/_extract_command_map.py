"""
Estrae la mappa reale COMANDO/UI di ZW3D dall'installazione:
  - dai .zcui (ribbon/menu): bottone (action) -> ribbon page/group
  - dai .tcmd (comandi): template name -> function (DLL) + parametri
  - dai .ui (Qt): finestre
Produce ZW3D-COMMAND-MAP.json strutturato per l'addestramento di Efesto.
Autore: Hermes (agente orchestratore). Uso difensivo/analisi lecita dei file di
installazione ZW3D (leggere, non modificare binari).
"""
import os, re, json, glob

ZWROOT = r"C:\Program Files\ZWSOFT\ZW3D 2025"
OUT = r"C:\Users\infoa\EfestoAI\knowledge\api\ZW3D-COMMAND-MAP.json"

# 1) .zcui -> azioni ribbon
ribbon = []
for z in glob.glob(os.path.join(ZWROOT, "**", "*.zcui"), recursive=True):
    try:
        t = open(z, encoding="utf-8", errors="ignore").read()
    except:
        continue
    # pagina e gruppo correnti
    for m in re.finditer(r'<RibbonPage\b[^>]*?name="([^"]*)"[^>]*?text="([^"]*)"', t):
        pass
    # control action inside page/group
    # estrai gerarchia: trova pagina, gruppo, poi control action
    for m in re.finditer(r'<RibbonPage\b[^>]*?name="(?P<page>[^"]*)"[^>]*?text="(?P<ptext>[^"]*)".*?(?=<RibbonPage|<RibbonPages>)', t, re.S):
        page = m.group("page"); ptext = m.group("ptext")
        seg = m.group(0)
        for gm in re.finditer(r'<RibbonGroup\b[^>]*?name="(?P<grp>[^"]*)"[^>]*?text="(?P<gtext>[^"]*)".*?(?=<RibbonGroup|<RibbonPage)', seg, re.S):
            grp = gm.group("grp"); gtext = gm.group("gtext")
            for am in re.finditer(r'<Control\b[^>]*?action="(?P<act>[^"]*)"', gm.group(0)):
                act = am.group("act")
                ribbon.append({"source": os.path.relpath(z, ZWROOT), "page": page, "pageText": ptext, "group": grp, "groupText": gtext, "action": act})

# 2) .tcmd -> template -> function + params
tcmd = []
for tc in glob.glob(os.path.join(ZWROOT, "apilibs", "**", "*.tcmd"), recursive=True) + \
         glob.glob(os.path.join(ZWROOT, "AppMenu", "**", "*.tcmd"), recursive=True):
    try:
        t = open(tc, encoding="utf-8", errors="ignore").read()
    except:
        continue
    tmpl = re.search(r'<template name="([^"]*)"', t)
    if not tmpl: continue
    name = tmpl.group(1)
    fn = re.search(r'<property name="function">([^<]*)</property>', t)
    params = re.findall(r'<parameter\b[^>]*?description="([^"]*)"', t)
    tcmd.append({"file": os.path.relpath(tc, ZWROOT), "template": name, "function": fn.group(1) if fn else None, "nParams": len(params), "params": params[:20]})

# 3) Sintesi azioni uniche
actions = {}
for r in ribbon:
    a = r["action"]
    actions.setdefault(a, {"pages": set(), "groups": set(), "sources": set()})
    actions[a]["pages"].add(r["pageText"])
    actions[a]["groups"].add(r["groupText"])
    actions[a]["sources"].add(r["source"])

unique_actions = len(actions)
# mappa action -> function (se il template esiste con stesso nome)
tcmd_by_fn = {x["function"]: x for x in tcmd if x["function"]}
action_to_function = {}
for a in actions:
    # action ID_!X o ID_~X -> comando X
    cmd = re.sub(r'^ID_[!~]', '', a)
    if cmd in tcmd_by_fn:
        action_to_function[a] = tcmd_by_fn[cmd]["function"]

out = {
    "meta": {
        "generato_da": "Hermes agente orchestratore",
        "data": "2026-07-26",
        "sorgente": ZWROOT,
        "metodo": "lettura file di installazione ZW3D (.zcui/.tcmd), analisi lecita",
        "n_ribbon_entries": len(ribbon),
        "n_unique_actions": unique_actions,
        "n_tcmd_files": len(tcmd),
        "n_actions_with_function": len(action_to_function),
    },
    "ribbon_entries": ribbon[:6000],   # cap per dimensione
    "tcmd_entries": tcmd,
    "action_to_function": action_to_function,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(out, f, indent=1)
print("scritto", OUT)
print("ribbon entries:", len(ribbon), "| unique actions:", unique_actions, "| tcmd:", len(tcmd), "| action->function:", len(action_to_function))
