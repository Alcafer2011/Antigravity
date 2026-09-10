# -*- coding: utf-8 -*-
"""CHAT: tutto quello che l'utente ha chiesto, segnalato e deciso.

FONTI
    - le chat di Claude Code (~/.claude/projects/*/*.jsonl), tutte
    - i messaggi scritti MENTRE Claude lavorava: non stanno nelle righe
      "user" ma negli allegati `queued_command` con origin.kind == "human"
      (scoperto l'11/09/2026: senza, si perdevano proprio le correzioni)
    - le memorie (~/.claude/projects/*/memory/*.md), tutte e tre le cartelle
    - i documenti di lavoro della Videoteca in Antigravity

COSA NE FA
    Ripulisce i messaggi (selezioni dell'editor, promemoria di sistema,
    messaggi fra sessioni), li data, e a ciascuno da' un TIPO (problema,
    richiesta, gusto, decisione, domanda) e degli ARGOMENTI. Le parole
    chiave sono in italiano come le usa l'utente: si allargano qui sotto,
    non nel codice.
"""

import glob
import io
import json
import os
import re

CASA = os.path.expanduser("~")
PROGETTI = os.path.join(CASA, ".claude", "projects")
QUI = os.path.dirname(os.path.abspath(__file__))
ANTIGRAVITY = os.path.abspath(os.path.join(QUI, "..", ".."))

DOCUMENTI = [
    os.path.join(ANTIGRAVITY, "traduttore", "LAVORI-VIDEOTECA-*.md"),
    os.path.join(ANTIGRAVITY, "memoria-condivisa", "STATO.md"),
]

# Argomento -> parole che lo fanno riconoscere (minuscole, senza accenti).
ARGOMENTI = {
    "skin e aspetto": ["skin", "arctic", "zephyr", "estuary", "bingie", "fuse", "netflix style",
                       "stile netflix", "tema netflix", "aspetto", "grafica", "moderne", "stilizzat",
                       "bello", "brutto", "carattere", "font", "colori"],
    "home e righe": ["home", "riga", "righe", "widget", "schermata principale", "menu", "voce",
                     "sezione", "sezioni", "reparto", "scaffale"],
    "locandine e loghi": ["locandin", "poster", "tessera", "tessere", "logo", "loghi", "clearlogo",
                          "sfondo", "fanart", "immagin", "copertin", "titoli scritti"],
    "tasto ok e navigazione": ["tasto ok", "premo ok", "telecomando", "non si apre", "non apre",
                               "cliccare", "clicco", "non parte", "errore di riproduzione", "navig"],
    "riproduzione e fonti": ["riproduc", "episodio", "episodi", "s4me", "fonte", "fonti", "streaming",
                             "buffer", "qualita", "si ferma", "carica", "caricamento", "prossimo episodio"],
    "netflix e abbonamenti": ["netflix", "prime", "amazon", "disney", "abbonament", "scade"],
    "consigli e la mia lista": ["consigli", "consigliat", "la mia lista", "pollice", "mi piace"],
    "documentari cucina youtube": ["documentar", "cucina", "youtube", "canale", "canali youtube",
                                   "fast n", "harley", "masterchef"],
    "tv in diretta e iptv": ["iptv", "tv in diretta", "canali tv", "diretta", "epg", "guida tv", "pvr"],
    "saghe e catalogo": ["saga", "saghe", "catalogo", "dragon ball", "naruto", "one piece", "anime",
                         "cartoni", "serie tv", "film", "capitol"],
    "lingua italiano": ["italiano", "italiana", "inglese", "sottotitol", "doppiat", "audio", "lingua"],
    "avvisi e finestre": ["avviso", "notifica", "finestra", "riquadro", "schede che appaiono", "popup"],
    "aggiornamenti e installazione": ["aggiorna", "repository", "installa", "deploy", "versione",
                                      "download", "sovrascriv"],
    "apparecchi": ["box", "8k", "raspberry", "salotto", "libreelec", "tv", "banco", "pc", "riavvi"],
    "stabilita e blocchi": ["crash", "si blocca", "bloccat", "si chiude", "si spegne", "lento",
                            "freeze", "non risponde", "bug", "problem"],
    "lavoro di claude": ["contesto", "sessione", "memoria", "script", "report", "analizz", "commit",
                         "git", "push"],
}

# Tipo -> espressioni (la prima che combacia vince, nell'ordine).
TIPI = [
    ("problema", r"non (funziona|va|parte|si apre|apre|vedo|si vede|carica|trovo|c'e|c e|riproduce|legge|"
                 r"compare|appare|risponde|si sente|capisco cosa)|errore|errori|bug|problem|si blocca|bloccat|"
                 r"crash|nero|vuot|sbagliat|non si |rott|ancora la roba vecchia|non riesco|sparit|scompar|"
                 r"doppi|lent[oaie]\b|troppo|si accende sempre|parte sempre|si spegne|si chiude|si riavvia|"
                 r"manca\b|mancano|salta|ripete|incastr|impalla|freeze|scatta|non ha|vecchi[oa] e"),
    ("gusto", r"mi piace|non mi piace|preferisco|bell[oaie]\b|brutt|stile|moderne|stilizzat|a tema|"
              r"elegant|carin|orribil|confus|intuitiv"),
    ("domanda", r"\?\s*$|^(come|perche|cosa|quale|quali|dove|quando|dobbiamo|devo|posso|riesci|e se|ma se|"
                r"esiste|esistono|si puo|ce un|c'e un)\b"),
    ("richiesta", r"\b(vorrei|voglio|fai|fammi|crea|aggiungi|metti|togli|toglila|sistema|correggi|implementa|"
                  r"installa|installala|riavvia|riavvial[oia]|deve|devono|dovrebbe|dovrebbero|devi|dovresti|"
                  r"serve|servono|bisogna|occorre|procedi|continua|ricorda|ricordati|spegni|spegnila|accendi|"
                  r"non farla|non far|tassativamente|usa|prova|controlla|verifica|cerca|analizza|trova|rendi|"
                  r"cambia|sostituisci|sposta|elimina|rimuovi|aggiorna|scarica|imposta|abilita|disabilita|"
                  r"attiva|disattiva|separa|dividi|ordina|mostra|nascondi|traduci|scrivi|leggi|apri|chiudi|"
                  r"blocca|ferma|consigliami|pusha|committa|salva|evidenza|metti in)\b"),
    ("decisione", r"^(ok|si|sì|va bene|perfetto|procedi|vai|dai|no|esatto|giusto|confermo|fallo)\b"),
]

RUMORE = [
    (r"<ide_selection>.*?</ide_selection>", ""),
    (r"<ide_opened_file>.*?</ide_opened_file>", ""),
    (r"<system-reminder>.*?</system-reminder>", ""),
    (r"<command-[a-z-]+>.*?</command-[a-z-]+>", ""),
    (r"<local-command-[a-z-]+>.*?</local-command-[a-z-]+>", ""),
    (r"\[Request interrupted by user[^\]]*\]", ""),
]


def _normale(testo):
    t = testo.lower()
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u")):
        t = t.replace(a, b)
    return t


def _pulisci(testo):
    for schema, sost in RUMORE:
        testo = re.sub(schema, sost, testo, flags=re.S)
    return testo.strip()


def classifica(testo):
    n = _normale(testo)
    argomenti = [a for a, parole in ARGOMENTI.items() if any(p in n for p in parole)]
    tipo = "nota"
    for nome, schema in TIPI:
        if re.search(schema, n, re.M):
            tipo = nome
            break
    return tipo, argomenti


def _videoteca(argomenti, testo):
    n = _normale(testo)
    chiave = ("kodi", "videoteca", "saghe", "addon", "add-on", "skin", "box", "raspberry", "locandin",
              "netflix", "s4me", "episod", "widget", "home", "arctic", "iptv", "tessere", "logo")
    return any(k in n for k in chiave) or bool(set(argomenti) - {"lavoro di claude", "apparecchi"})


def _testo_blocchi(contenuto):
    if isinstance(contenuto, str):
        return contenuto
    if isinstance(contenuto, list):
        return "\n".join(x.get("text", "") for x in contenuto
                         if isinstance(x, dict) and x.get("type") == "text")
    return ""


def leggi_chat():
    messaggi, sessioni = [], {}
    for f in sorted(glob.glob(os.path.join(PROGETTI, "*", "*.jsonl"))):
        cartella = os.path.basename(os.path.dirname(f))
        with io.open(f, encoding="utf-8", errors="replace") as h:
            for riga in h:
                try:
                    o = json.loads(riga)
                except ValueError:
                    continue
                sid = o.get("sessionId") or os.path.basename(f)[:-6]
                s = sessioni.setdefault(sid, {"cartella": cartella, "titolo": "", "inizio": "",
                                              "fine": "", "messaggi": 0, "cwd": ""})
                quando = o.get("timestamp") or ""
                if quando:
                    s["inizio"] = s["inizio"] or quando
                    s["fine"] = max(s["fine"], quando)
                if o.get("type") == "ai-title":
                    s["titolo"] = o.get("aiTitle") or o.get("title") or s["titolo"]
                testo, fonte = "", ""
                if o.get("type") == "user" and not o.get("isMeta"):
                    m = o.get("message") or {}
                    c = m.get("content")
                    if isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                        continue
                    testo, fonte = _testo_blocchi(c), "chat"
                    s["cwd"] = s["cwd"] or o.get("cwd", "")
                elif o.get("type") == "attachment":
                    a = o.get("attachment") or {}
                    if isinstance(a, dict) and a.get("type") == "queued_command" and \
                            (a.get("origin") or {}).get("kind") == "human":
                        testo, fonte = _testo_blocchi(a.get("prompt")), "scritto mentre lavorava"
                        quando = a.get("timestamp") or quando
                if not testo:
                    continue
                testo = _pulisci(testo)
                if not testo or testo.startswith("<cross-session-message") or \
                        testo.startswith("[Cross-session") or testo.startswith("Caveat:"):
                    continue
                tipo, argomenti = classifica(testo)
                s["messaggi"] += 1
                messaggi.append({"quando": quando, "sessione": sid, "cartella": cartella,
                                 "fonte": fonte, "testo": testo, "tipo": tipo,
                                 "argomenti": argomenti, "videoteca": _videoteca(argomenti, testo)})
    # lo stesso messaggio puo' comparire due volte (coda + riga utente): uno solo
    visti, unici = set(), []
    for m in sorted(messaggi, key=lambda x: x["quando"]):
        chiave = (m["sessione"], m["testo"][:200])
        if chiave in visti:
            continue
        visti.add(chiave)
        unici.append(m)
    return unici, sessioni


def leggi_memorie():
    fuori = []
    for f in sorted(glob.glob(os.path.join(PROGETTI, "*", "memory", "*.md"))):
        with io.open(f, encoding="utf-8", errors="replace") as h:
            testo = h.read()
        nome = re.search(r"^name:\s*(.+)$", testo, re.M)
        descr = re.search(r"^description:\s*(.+)$", testo, re.M)
        tipo = re.search(r"^\s*type:\s*(\w+)", testo, re.M)
        corpo = re.sub(r"^---.*?---\s*", "", testo, flags=re.S)
        _t, argomenti = classifica(corpo)
        fuori.append({"file": f, "cartella": os.path.basename(os.path.dirname(os.path.dirname(f))),
                      "nome": nome.group(1).strip() if nome else os.path.basename(f),
                      "descrizione": descr.group(1).strip().strip('"') if descr else "",
                      "tipo": tipo.group(1) if tipo else "",
                      "argomenti": argomenti, "videoteca": _videoteca(argomenti, corpo),
                      "modificato": os.path.getmtime(f), "testo": corpo})
    return fuori


def leggi_documenti():
    fuori = []
    for schema in DOCUMENTI:
        for f in sorted(glob.glob(schema)):
            with io.open(f, encoding="utf-8", errors="replace") as h:
                fuori.append({"file": f, "modificato": os.path.getmtime(f), "testo": h.read()})
    return fuori


def analizza():
    messaggi, sessioni = leggi_chat()
    return {"messaggi": messaggi, "sessioni": sessioni,
            "memorie": leggi_memorie(), "documenti": leggi_documenti()}
