# -*- coding: utf-8 -*-
#
# Traduttore IT — gestore di traduzioni per add-on Kodi.
#
# COSA FA
#   1. Elenca gli add-on installati e legge la loro versione.
#   2. Per ognuno che ha un PROFILO (resources/profili/<id>.json) confronta la
#      versione con l'ultima vista: capisce se e' NUOVO o e' stato AGGIORNATO.
#   3. Per quelli che scegli: fa un BACKUP dei file, applica la traduzione
#      italiana (solo sulle righe che mostrano testo all'utente), pulisce i
#      __pycache__ e segnala le stringhe tedesche/inglesi non ancora tradotte.
#
# PERCHE' SOPRAVVIVE AGLI AGGIORNAMENTI
#   Questo add-on vive per conto suo: un aggiornamento di un ALTRO add-on gli
#   riscrive i file, ma non tocca questo. Basta rilanciarlo (o lo fa il service)
#   e la traduzione torna. Il confronto di versione dice quando serve rifarlo.
#
# SICUREZZA
#   La sostituzione e' ANCORATA: cambia una stringa solo se sta su una riga che
#   mostra testo (menu, notifica, impostazione...). Non tocca log, docstring,
#   URL o logica tipo .replace("Serien","Filme"). Prima di scrivere fa il backup.

import os
import re
import sys
import json
import time
import shutil

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonId()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
DATA_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
PROFILI_DIR = os.path.join(ADDON_PATH, "resources", "profili")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
STATO_FILE = os.path.join(DATA_DIR, "stato.json")
ADDONS_HOME = xbmcvfs.translatePath("special://home/addons")

# Righe che MOSTRANO testo all'utente: solo qui si traduce.
ANCORE = ("addDir", "addItem", "ListItem(", "setLabel", "notification", "notify(",
          "Dialog", ".ok(", "yesno", "select", "cm.append", "set_category",
          "browse(", '"plot"', "'plot'", '"title"', "'title'", "heading", '"genre"', "'genre'")
# Righe da NON toccare mai, anche se sembrano di visualizzazione.
VIETATE = ("log(", "log_debug", ".replace(", "xbmc.log")


def _log(msg):
    xbmc.log("[Traduttore IT] %s" % msg, xbmc.LOGINFO)


def _carica_json(percorso, default=None):
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _salva_json(percorso, dati):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


def versione_addon(addon_id):
    try:
        a = xbmcaddon.Addon(addon_id)
        return a.getAddonInfo("version")
    except Exception:
        return None


def profili_disponibili():
    fuori = {}
    if not os.path.isdir(PROFILI_DIR):
        return fuori
    for nome in os.listdir(PROFILI_DIR):
        if nome.endswith(".json"):
            p = _carica_json(os.path.join(PROFILI_DIR, nome))
            if p.get("addon"):
                fuori[p["addon"]] = p
    return fuori


# ---------------------------------------------------------------- sostituzione

def _traduci_py(testo, traduzioni):
    """Sostituisce le stringhe SOLO sulle righe di visualizzazione."""
    cambi = 0
    out = []
    for riga in testo.split("\n"):
        if any(v in riga for v in VIETATE) or not any(a in riga for a in ANCORE):
            out.append(riga)
            continue
        nuova = riga
        for src, dst in traduzioni.items():
            for q in ('"', "'"):
                ago = q + src + q
                if ago in nuova:
                    dst_safe = dst.replace(q, "\\" + q)  # non chiudere la stringa se dst contiene l'apice
                    nuova = nuova.replace(ago, q + dst_safe + q)
                    cambi += 1
        out.append(nuova)
    return "\n".join(out), cambi


def _traduci_xml(testo, traduzioni):
    """settings.xml: traduce label='...' per intero e values='a|b|c' segmento a segmento."""
    cambi = [0]

    def sostituisci_label(m):
        val = m.group(2)
        if val in traduzioni:
            cambi[0] += 1
            return m.group(1) + traduzioni[val] + m.group(3)
        return m.group(0)

    def sostituisci_values(m):
        pezzi = m.group(2).split("|")
        nuovi = []
        for p in pezzi:
            if p in traduzioni:
                cambi[0] += 1
                nuovi.append(traduzioni[p])
            else:
                nuovi.append(p)
        return m.group(1) + "|".join(nuovi) + m.group(3)

    testo = re.sub(r'(label=")([^"]*)(")', sostituisci_label, testo)
    testo = re.sub(r'(values=")([^"]*)(")', sostituisci_values, testo)
    return testo, cambi[0]


def _stringhe_sospette(testo, traduzioni):
    """Righe di visualizzazione con testo tedesco (umlaut/ß) non ancora tradotto: possibili novita'."""
    viste = set()
    for riga in testo.split("\n"):
        if any(v in riga for v in VIETATE) or not any(a in riga for a in ANCORE):
            continue
        for m in re.finditer(r'(["\'])((?:\\.|(?!\1).)*?)\1', riga):
            s = m.group(2)
            if len(s) < 3 or s in traduzioni:
                continue
            if re.search(r'[ÄÖÜäöüß]', s) or re.search(r'\b(und|der|die|das|nicht|kein|keine|Fehler|Wiedergabe|Sender|Suche)\b', s):
                viste.add(s)
    return viste


# ---------------------------------------------------------------- applicazione

def pulisci_pycache(radice):
    for dirpath, dirnames, _ in os.walk(radice):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)


def applica_profilo(profilo, dry=False):
    addon_id = profilo["addon"]
    ver = versione_addon(addon_id) or "?"
    base = os.path.join(ADDONS_HOME, addon_id)
    if not os.path.isdir(base):
        return {"ok": False, "msg": "non installato"}

    traduzioni = profilo.get("traduzioni", {})
    files = profilo.get("file", [])
    tot_cambi = 0
    sospette = set()
    dest_backup = os.path.join(BACKUP_DIR, addon_id, ver)

    for rel in files:
        fpath = os.path.join(base, *rel.split("/"))
        if not os.path.isfile(fpath):
            continue
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            testo = f.read()

        if fpath.endswith(".xml"):
            nuovo, cambi = _traduci_xml(testo, traduzioni)
        else:
            nuovo, cambi = _traduci_py(testo, traduzioni)
            sospette |= _stringhe_sospette(testo, traduzioni)

        if cambi and not dry:
            # backup dell'originale (una volta per versione)
            bkp = os.path.join(dest_backup, *rel.split("/"))
            if not os.path.exists(bkp):
                os.makedirs(os.path.dirname(bkp), exist_ok=True)
                shutil.copy2(fpath, bkp)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(nuovo)
        tot_cambi += cambi

    if tot_cambi and not dry:
        pulisci_pycache(base)

    return {"ok": True, "cambi": tot_cambi, "versione": ver,
            "sospette": sorted(sospette), "backup": dest_backup}


def stato_addon(profili, stato):
    """Elenco (id, etichetta, chiave_stato) per la UI."""
    righe = []
    for addon_id, profilo in sorted(profili.items()):
        ver = versione_addon(addon_id)
        if ver is None:
            continue  # non installato: non lo mostriamo
        prec = stato.get(addon_id, {})
        if not prec:
            marca = "NUOVO"
        elif prec.get("versione") != ver:
            marca = "AGGIORNATO -> da ritradurre"
        elif prec.get("tradotto"):
            marca = "gia' tradotto"
        else:
            marca = "da tradurre"
        righe.append((addon_id, "%s  [%s]  v%s" % (addon_id, marca, ver)))
    return righe


# ---------------------------------------------------------------------- avvio

def esegui(headless_ids=None):
    profili = profili_disponibili()
    stato = _carica_json(STATO_FILE, {})

    if not profili:
        if not headless_ids:
            xbmcgui.Dialog().ok("Traduttore IT", "Nessun profilo di traduzione trovato in resources/profili.")
        return

    righe = stato_addon(profili, stato)
    if not righe:
        if not headless_ids:
            xbmcgui.Dialog().ok("Traduttore IT", "Nessun add-on con profilo risulta installato.")
        return

    if headless_ids is not None:
        # modalita' senza interfaccia: applica agli id chiesti (o a tutti)
        scelti = [i for (i, _) in righe] if not headless_ids else [i for (i, _) in righe if i in headless_ids]
    else:
        idx = xbmcgui.Dialog().multiselect("Traduttore IT — scegli cosa tradurre",
                                           [e for (_, e) in righe])
        if not idx:
            return
        scelti = [righe[i][0] for i in idx]

    riepilogo = []
    for addon_id in scelti:
        r = applica_profilo(profili[addon_id])
        if not r.get("ok"):
            riepilogo.append("%s: %s" % (addon_id, r.get("msg")))
            continue
        stato[addon_id] = {"versione": r["versione"], "tradotto": True,
                           "quando": time.strftime("%Y-%m-%d %H:%M:%S")}
        nota = "%s: %d stringhe tradotte (v%s)" % (addon_id, r["cambi"], r["versione"])
        if r["sospette"]:
            nota += "\n   possibili NUOVE stringhe da tradurre: %d" % len(r["sospette"])
            _log("%s nuove stringhe: %s" % (addon_id, " | ".join(r["sospette"])))
        riepilogo.append(nota)

    _salva_json(STATO_FILE, stato)
    _log("Riepilogo:\n" + "\n".join(riepilogo))

    if headless_ids is None:
        xbmcgui.Dialog().textviewer("Traduttore IT — fatto",
            "\n".join(riepilogo) +
            "\n\nRiavvia Kodi (o riapri l'add-on) per vedere l'interfaccia in italiano." +
            "\nBackup salvato in:\n" + BACKUP_DIR)
        if xbmcgui.Dialog().yesno("Traduttore IT", "Riavvio Kodi ora per applicare le modifiche?"):
            xbmc.executebuiltin("RestartApp")


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    if args and args[0] == "apply":
        ids = set(args[1:]) if len(args) > 1 and args[1] != "all" else None
        esegui(headless_ids=ids if ids else set())
    else:
        esegui(headless_ids=None)
