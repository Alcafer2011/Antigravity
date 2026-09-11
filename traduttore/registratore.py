# -*- coding: utf-8 -*-
"""IL REGISTRATORE: cosa e' successo sulla TV, spiegato in una pagina.

PERCHE' (chiesto dall'utente l'11/09/2026)
    "dovrei provare con gli apparecchi ma credo ci voglia uno script che
    raccolga le informazioni mentre li sto utilizzando nel caso ci siano
    errori nel funzionamento, perche' io non saprei descrivertele".
    Sugli apparecchi la SCATOLA NERA del guardiano scrive tutto da sola
    (schermate, video partiti o no, messaggi, attese, errori, fotografie).
    Questo script la scarica insieme al registro di Kodi e ne fa un rapporto
    HTML: cosa e' andato storto, cosa stavi facendo in quel momento, la foto
    dello schermo, le righe del registro di quei secondi e la causa probabile.

USO
    python registratore.py box              le ultime 6 ore del box
    python registratore.py pi --ore 24      l'ultimo giorno del Raspberry
    python registratore.py pc --dal "2026-09-11 20:00"
    python registratore.py box --vivo       mentre usi la TV: stampa gli eventi
                                            man mano; Ctrl+C e fa il rapporto
    Aggiungi --non-aprire per non aprire la pagina alla fine.

DOVE FINISCE
    atlante/uscita/sessioni/<apparecchio>-<data>/sessione.html  (con le foto)
    e sessione.json accanto, da leggere per chi sistema i guasti.
"""

import argparse
import datetime
import html
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
from urllib.parse import parse_qsl, urlsplit

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(QUI, "atlante"))
import raccolta as R  # noqa: E402

USCITA = os.path.join(QUI, "atlante", "uscita", "sessioni")
SCATOLA = "userdata/addon_data/service.videoteca.guardiano/scatola_nera"

FINESTRE = {
    10000: "Home", 10025: "Video", 12005: "Video a schermo intero", 12006: "Visualizzazione musica",
    10138: "Attesa (rotellina)", 10160: "Attesa (rotellina)", 12002: "Messaggio", 10100: "Domanda si'/no",
    12000: "Elenco di scelta", 10147: "Testo", 10103: "Tastiera", 10107: "Notifica", 10106: "Menu del tasto MENU",
    12901: "Comandi del video", 10004: "Impostazioni", 10040: "Add-on", 10146: "Scheda dell'add-on",
    12003: "Scheda del titolo", 10131: "Impostazioni dell'add-on", 10101: "Avanzamento", 13000: "Finestra di script",
    10700: "TV", 10701: "Canali TV", 10702: "Guida TV", 10800: "File manager", 11000: "Salvaschermo",
}
AZIONI = {
    "percorso": "la saga", "sfoglia": "gli episodi della saga", "riproduci": "avvio dell'episodio",
    "widget": "una riga della home", "reparto": "il reparto", "gruppo": "il raggruppamento",
    "film": "i film della saga", "film_tutti": "i film delle saghe", "cinema": "Al cinema ora",
    "consigli": "Consigliati per te", "netflix": "Su Netflix ora", "tv": "TV in diretta",
    "tv_gruppo": "un gruppo di canali TV", "tv_apri": "un canale TV", "scaffale": "lo scaffale",
    "scaffale_cerca": "una ricerca nei cataloghi", "diretta": "un canale in diretta", "cerca": "Cerca",
    "linea": "La mia linea", "abbonamenti": "I miei abbonamenti", "russo": "Russo con i cartoni",
    "aggiornamenti": "Cerca aggiornamenti", "segnala": "Qualcosa non va?", "altro": "Altro della saga",
    "apri_film": "apertura di un film", "capitoli": "i capitoli", "consiglio_aggiungi": "aggiunta di un consiglio",
    "netflix_aggiungi": "aggiunta di un titolo da Netflix",
    "assistenza": "Aggiornamenti e segnalazioni", "cerca_di_nuovo": "una ricerca recente",
}
GENERI = {
    "video_non_partito": ("Video che non e' partito", "alto"),
    "kodi_chiuso_da_solo": ("Kodi si e' chiuso da solo", "alto"),
    "errore_python": ("Errore di un add-on", "alto"),
    "attesa_lunga": ("Attesa troppo lunga", "medio"),
    "messaggio": ("Messaggio di errore a schermo", "medio"),
    "registro": ("Errore nel registro di Kodi", "medio"),
    "segnalata": ("Segnalato da te", "alto"),
}
DIAGNOSI = [
    (r"two concurrent busydialogs", "Kodi ha aperto due rotelline insieme: una finestra aperta da dentro una cartella "
                                    "(il crollo del 06/09). Va spostata in avvio.py."),
    (r"(?i)playback failed|failed to open|openfile", "Il video non si e' aperto: il sito ha dato un indirizzo che non "
                                                      "funziona (cambiato, scaduto o bloccato)."),
    (r"(?i)\b40[34]\b", "Il sito ha rifiutato la richiesta (403/404): collegamento scaduto o sito cambiato."),
    (r"(?i)timed? ?out|timeout", "La fonte non ha risposto in tempo: linea lenta o sito giu'."),
    (r"ImportError|ModuleNotFoundError", "Manca un file dell'add-on: installazione a meta' (servi.py la rifa intera)."),
    (r"(?i)inputstream", "Problema del lettore dei flussi (inputstream.adaptive)."),
    (r"(?i)plugin\.video\.s4me|s4me", "L'errore nasce dentro s4me, il motore delle fonti."),
    (r"PermissionError|Permission denied", "Kodi non ha i permessi su un file (sul box: file rimasti di root)."),
    (r"(?i)memoryerror|out of memory|low memory", "Memoria finita sull'apparecchio."),
    (r"(?i)nessun[ao]? fonte|no sources|nessun risultato", "Nessun sito ha l'episodio in questo momento."),
]


# ------------------------------------------------------------------ download

def _dal_pc(dest):
    kodi = os.path.expandvars(r"%APPDATA%\Kodi")
    s = os.path.join(kodi, *SCATOLA.split("/"))
    if os.path.isdir(s):
        shutil.copytree(s, os.path.join(dest, "scatola"), dirs_exist_ok=True)
    for f in ("kodi.log", "kodi.old.log"):
        if os.path.exists(os.path.join(kodi, f)):
            shutil.copyfile(os.path.join(kodi, f), os.path.join(dest, f))
    return time.time()


def _dal_box(dest, con_foto=True):
    if not R._adb_pronto():
        raise SystemExit("il box non risponde ad adb")
    elenco = "%s/*.jsonl %s/sessione.json" % (SCATOLA, SCATOLA)
    if con_foto:
        elenco += " %s/scatti" % SCATOLA
    cmd = "cd %s && tar -cf /sdcard/registratore.tar %s temp/kodi.log temp/kodi.old.log 2>/dev/null; echo fatto" % (R.BOX_KODI, elenco)
    R._adb("shell", "su -c \"%s\"" % cmd, tempo=300)
    locale = os.path.join(dest, "box.tar")
    R._adb("pull", "/sdcard/registratore.tar", locale, tempo=600)
    R._adb("shell", "su -c 'rm -f /sdcard/registratore.tar'")
    _estrai(locale, dest)
    orologio = R._adb("shell", "date +%s").strip()
    return float(orologio) if orologio.isdigit() else time.time()


def _dal_pi(dest, con_foto=True):
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(R.PI, username="root", password=R._password_pi(), timeout=15)
    base = "/storage/.kodi"
    elenco = "%s/*.jsonl %s/sessione.json" % (SCATOLA, SCATOLA) + (" %s/scatti" % SCATOLA if con_foto else "")
    _i, o, _e = c.exec_command("cd %s && tar -cf /tmp/registratore.tar %s temp/kodi.log temp/kodi.old.log 2>/dev/null; "
                               "date +%%s" % (base, elenco), timeout=300)
    orologio = o.read().decode().strip().splitlines()
    sftp = c.open_sftp()
    locale = os.path.join(dest, "pi.tar")
    sftp.get("/tmp/registratore.tar", locale)
    sftp.close()
    c.exec_command("rm -f /tmp/registratore.tar")
    c.close()
    _estrai(locale, dest)
    return float(orologio[-1]) if orologio and orologio[-1].isdigit() else time.time()


def _estrai(tar, dest):
    with tarfile.open(tar) as t:
        for m in t.getmembers():
            if not m.isfile():
                continue
            nome = m.name
            if "/scatola_nera/" in nome:
                rel = os.path.join("scatola", nome.split("/scatola_nera/", 1)[1])
            elif nome.endswith(("kodi.log", "kodi.old.log")):
                rel = os.path.basename(nome)
            else:
                continue
            q = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(q), exist_ok=True)
            with t.extractfile(m) as sorgente, open(q, "wb") as out:
                shutil.copyfileobj(sorgente, out)
    os.remove(tar)


SCARICA = {"pc": _dal_pc, "box": _dal_box, "pi": _dal_pi}


# ------------------------------------------------------------------ lettura

def _eventi(cartella, dal, al):
    fuori = []
    s = os.path.join(cartella, "scatola")
    for f in sorted(os.listdir(s)) if os.path.isdir(s) else []:
        if not f.endswith(".jsonl"):
            continue
        with io.open(os.path.join(s, f), encoding="utf-8", errors="replace") as h:
            for riga in h:
                try:
                    e = json.loads(riga)
                except ValueError:
                    continue
                if dal <= e.get("ts", 0) <= al:
                    fuori.append(e)
    return sorted(fuori, key=lambda e: e.get("ts", 0))


def _registro(cartella, scarto, dal, al):
    """Le righe importanti del registro, con l'ora convertita in quella del PC."""
    fuori = []
    for nome in ("kodi.old.log", "kodi.log"):
        p = os.path.join(cartella, nome)
        if not os.path.exists(p):
            continue
        with io.open(p, encoding="utf-8", errors="replace") as h:
            for riga in h:
                m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+ T:\d+\s+(\w+)\s+<[^>]*>:\s?(.*)$", riga)
                if not m:
                    if fuori and fuori[-1]["livello"] in ("error", "fatal"):
                        fuori[-1]["testo"] += "\n" + riga.rstrip()[:300]
                    continue
                livello = m.group(2).lower()
                if livello not in ("error", "fatal", "warning"):
                    continue
                ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")) - scarto
                if dal - 60 <= ts <= al + 60:
                    fuori.append({"ts": ts, "livello": livello, "testo": m.group(3)[:600]})
    return fuori


def _catalogo():
    try:
        spec = importlib.util.spec_from_file_location("catalogo_registratore",
                                                      os.path.join(QUI, "plugin.video.saghe", "resources", "lib", "catalogo.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {pid: p.get("titolo", pid) for pid, p in mod.PERCORSI.items()}
    except Exception:
        return {}


def _leggibile(cartella, titoli):
    """Da un indirizzo di Kodi a parole: dove si trovava l'utente."""
    if not cartella:
        return ""
    if cartella.startswith("plugin://plugin.video.saghe"):
        q = dict(parse_qsl(urlsplit(cartella).query))
        azione = q.get("azione", "")
        if not azione:
            return "Videoteca, menu principale"
        testo = "Videoteca, %s" % AZIONI.get(azione, azione)
        if q.get("percorso"):
            testo += " \"%s\"" % titoli.get(q["percorso"], q["percorso"])
        for k in ("che", "reparto", "gruppo", "scaffale", "cosa", "canale", "testo"):
            if q.get(k):
                testo += " (%s)" % q[k]
        if q.get("idx"):
            testo += ", tappa %s" % q["idx"]
        return testo
    if cartella.startswith("plugin://plugin.video.s4me"):
        # La testa degli indirizzi di s4me e' codificata (s4me_link.py, 11/09/2026).
        spec = importlib.util.spec_from_file_location(
            "s4me_link_registratore", os.path.join(QUI, "plugin.video.saghe", "resources", "lib", "s4me_link.py"))
        link = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(link)
        q = link.leggi(cartella)
        testo = "s4me, %s %s" % (q.get("channel", ""), q.get("action", ""))
        for k in ("testo", "titolo_serie", "titolo_film"):
            if q.get(k):
                testo += " \"%s\"" % q[k]
        return testo
    if cartella.startswith("plugin://"):
        return "add-on %s" % cartella.split("/")[2]
    return cartella[:120]


def _racconta(e, titoli):
    t = e.get("tipo")
    if t == "schermata":
        nome = FINESTRE.get(e.get("finestra"), e.get("nome", ""))
        dove = _leggibile(e.get("cartella", ""), titoli)
        return "Apre %s%s%s" % (nome, (" - " + dove) if dove else "",
                                (" (dalla voce \"%s\")" % e["da_voce"]) if e.get("da_voce") else "")
    if t == "finestra":
        return "Compare %s%s" % (FINESTRE.get(e.get("dialogo"), e.get("genere", "")),
                                 (": %s %s" % (e.get("titolo", ""), e.get("testo", ""))) if e.get("titolo") or e.get("testo") else "")
    if t == "video_chiesto":
        return "Chiede il video \"%s\"" % (e.get("titolo") or e.get("da_voce") or "")
    if t == "video_partito":
        return "Il video parte dopo %s secondi" % e.get("attesa")
    if t == "video_fermato":
        return "Il video si ferma dopo %s secondi%s" % (e.get("durata"), " (finito)" if e.get("finito") else "")
    if t == "attesa_finita":
        return "La rotellina sparisce dopo %s secondi" % e.get("secondi")
    if t == "anomalia":
        return "PROBLEMA - %s: %s" % (GENERI.get(e.get("genere"), (e.get("genere"), ""))[0], e.get("testo", ""))
    if t == "registro":
        return "Registro: %s" % e.get("testo", "")
    if t == "kodi":
        return "Kodi: %s" % e.get("metodo", "")
    if t == "kodi_avviato":
        return "Kodi si accende (%s)" % e.get("versione", "")
    if t == "kodi_chiuso":
        return "Kodi si chiude"
    if t == "messaggio_addon":
        return "Messaggio da %s: %s" % (e.get("mittente"), e.get("metodo"))
    return t


def _causa(testi):
    tutto = "\n".join(testi)
    return [spiega for schema, spiega in DIAGNOSI if re.search(schema, tutto)]


# ------------------------------------------------------------------ rapporto

STILE = """
:root{--sfondo:#f6f5f2;--carta:#fff;--testo:#1d1d1f;--tenue:#6b6b70;--riga:#e4e2dc;--alto:#c62828;--medio:#e08a00;
--ok:#2e7d32;--blu:#1e5aa8}
@media (prefers-color-scheme:dark){:root{--sfondo:#141416;--carta:#1f1f23;--testo:#ececef;--tenue:#9a9aa2;--riga:#34343a;
--alto:#ff6b6b;--medio:#ffb347;--ok:#6fcf73;--blu:#7fb0ff}}
*{box-sizing:border-box}body{margin:0;padding:24px clamp(16px,4vw,48px);background:var(--sfondo);color:var(--testo);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
h1{font-size:28px;margin:0 0 4px}h2{margin:36px 0 12px;font-size:21px}.tenue{color:var(--tenue)}
.carte{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0}
.carta{background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:14px}
.numero{font-size:30px;font-weight:700}.alto{color:var(--alto)}.medio{color:var(--medio)}.ok{color:var(--ok)}
.problema{background:var(--carta);border:1px solid var(--riga);border-left:6px solid var(--medio);border-radius:12px;
padding:16px;margin:14px 0}.problema.alto{border-left-color:var(--alto)}
.problema h3{margin:0 0 6px;font-size:17px}.passi{margin:8px 0;padding-left:20px}.passi li{margin:2px 0}
.causa{background:rgba(30,90,168,.08);border-radius:8px;padding:8px 12px;margin:10px 0}
img.foto{max-width:100%;border-radius:8px;border:1px solid var(--riga);margin-top:8px}
details{margin-top:8px}pre{white-space:pre-wrap;word-break:break-word;background:rgba(127,127,127,.1);padding:10px;
border-radius:8px;font-size:12.5px;max-height:360px;overflow:auto}
.tabella{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px}
td,th{border-bottom:1px solid var(--riga);padding:6px 8px;text-align:left;vertical-align:top}
tr.anomalia td{background:rgba(198,40,40,.08)}td.ora{white-space:nowrap;color:var(--tenue)}
"""


def _foto(cartella_sessione, cartella, nome):
    if not nome:
        return ""
    sorgente = os.path.join(cartella, "scatola", "scatti", nome)
    if not os.path.exists(sorgente):
        return ""
    dest_nome = os.path.splitext(nome)[0] + ".jpg"
    dest = os.path.join(cartella_sessione, "scatti", dest_nome)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        from PIL import Image
        with Image.open(sorgente) as im:
            im = im.convert("RGB")
            im.thumbnail((1280, 1280))
            im.save(dest, "JPEG", quality=82)
    except Exception:
        dest_nome = nome
        shutil.copyfile(sorgente, os.path.join(cartella_sessione, "scatti", nome))
    return "scatti/" + dest_nome


def rapporto(app, cartella, scarto, dal, al, destinazione):
    titoli = _catalogo()
    eventi = _eventi(cartella, dal, al)
    registro = _registro(cartella, scarto, dal, al)
    anomalie = [e for e in eventi if e.get("tipo") == "anomalia"]
    video_chiesti = sum(1 for e in eventi if e.get("tipo") == "video_chiesto")
    video_partiti = [e for e in eventi if e.get("tipo") == "video_partito"]
    attese = [e.get("attesa", 0) for e in video_partiti]
    errori_registro = [r for r in registro if r["livello"] in ("error", "fatal")]
    os.makedirs(destinazione, exist_ok=True)

    pezzi = []
    for a in anomalie:
        genere, livello = GENERI.get(a.get("genere"), (a.get("genere", "problema"), "medio"))
        prima = [e for e in eventi if e["ts"] < a["ts"] and e.get("tipo") in
                 ("schermata", "video_chiesto", "video_partito", "finestra")][-6:]
        vicine = [r for r in registro if a["ts"] - 25 <= r["ts"] <= a["ts"] + 5]
        cause = _causa([a.get("testo", ""), a.get("traccia", "")] + [r["testo"] for r in vicine])
        foto = _foto(destinazione, cartella, a.get("scatto"))
        pezzi.append(
            "<div class='problema %s'><h3>%s - %s</h3><div>%s</div>" % (livello, a["t"][11:], html.escape(genere),
                                                                         html.escape(a.get("testo", "")))
            + ("<div class='tenue'>Dov'eri: %s%s</div>" % (html.escape(_leggibile(a.get("cartella", ""), titoli) or "-"),
                                                          (" - voce \"%s\"" % html.escape(a["voce"])) if a.get("voce") else ""))
            + ("<div><b>Cosa stavi facendo:</b><ol class='passi'>%s</ol></div>"
               % "".join("<li><span class='tenue'>%s</span> %s</li>" % (e["t"][11:], html.escape(_racconta(e, titoli)))
                         for e in prima) if prima else "")
            + "".join("<div class='causa'><b>Causa probabile:</b> %s</div>" % html.escape(c) for c in cause)
            + ("<img class='foto' src='%s' alt='lo schermo in quel momento'>" % foto if foto else "")
            + ("<details><summary>Righe del registro di quei secondi (%d)</summary><pre>%s</pre></details>"
               % (len(vicine), html.escape("\n".join("%s %s %s" % (datetime.datetime.fromtimestamp(r["ts"]).strftime("%H:%M:%S"),
                                                                    r["livello"].upper(), r["testo"]) for r in vicine)))
               if vicine else "")
            + ("<details><summary>Errore completo</summary><pre>%s</pre></details>" % html.escape(a["traccia"])
               if a.get("traccia") else "")
            + "</div>")

    righe = []
    for e in eventi:
        if e.get("tipo") == "registro":
            continue
        righe.append("<tr class='%s'><td class='ora'>%s</td><td>%s</td></tr>"
                     % ("anomalia" if e.get("tipo") == "anomalia" else "", e["t"][5:],
                        html.escape(_racconta(e, titoli))))
    gruppi = {}
    for r in errori_registro:
        chiave = re.sub(r"\d+", "#", r["testo"].split("\n")[0])[:140]
        gruppi[chiave] = gruppi.get(chiave, 0) + 1

    def carta(numero, testo, classe=""):
        return "<div class='carta'><div class='numero %s'>%s</div><div class='tenue'>%s</div></div>" % (classe, numero, testo)

    nome_app = {"box": "Box 8K", "pi": "Raspberry del salotto", "pc": "PC (banco)"}[app]
    pagina = ("<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
              "initial-scale=1'><title>Registratore %s</title><style>%s</style></head><body>" % (nome_app, STILE)
              + "<h1>Cosa e' successo sul %s</h1><div class='tenue'>dal %s al %s (ora del PC)</div>" % (
                  nome_app, datetime.datetime.fromtimestamp(dal).strftime("%d/%m %H:%M"),
                  datetime.datetime.fromtimestamp(al).strftime("%d/%m %H:%M"))
              + "<div class='carte'>"
              + carta(len(anomalie), "problemi trovati", "alto" if anomalie else "ok")
              + carta("%d / %d" % (len(video_partiti), video_chiesti), "video partiti su chiesti",
                      "ok" if len(video_partiti) >= video_chiesti else "medio")
              + carta(("%.0f s" % (sum(attese) / len(attese))) if attese else "-", "attesa media prima del video")
              + carta(sum(1 for e in eventi if e.get("tipo") == "schermata"), "schermate aperte")
              + carta(len(errori_registro), "errori nel registro di Kodi", "medio" if errori_registro else "ok")
              + carta(sum(1 for a in anomalie if a.get("genere") == "segnalata"), "segnalati da te")
              + "</div>"
              + "<h2>Cosa e' andato storto</h2>"
              + ("".join(pezzi) if pezzi else "<p class='ok'>Nessun problema in questo periodo.</p>")
              + ("<h2>Errori del registro, raggruppati</h2><div class='tabella'><table><tr><th>volte</th><th>messaggio</th></tr>%s"
                 "</table></div>" % "".join("<tr><td>%d</td><td>%s</td></tr>" % (n, html.escape(k))
                                            for k, n in sorted(gruppi.items(), key=lambda x: -x[1])[:40]) if gruppi else "")
              + "<h2>Tutto quello che e' successo, in ordine</h2><div class='tabella'><table>%s</table></div>" % "".join(righe)
              + (("<p class='tenue'>Nessun evento: la scatola nera c'e' dal guardiano 1.2.0. Se l'apparecchio e' "
                  "appena stato aggiornato, usalo un po' e rilancia.</p>") if not eventi else "")
              + "</body></html>")
    p = os.path.join(destinazione, "sessione.html")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(pagina)
    with io.open(os.path.join(destinazione, "sessione.json"), "w", encoding="utf-8") as f:
        json.dump({"apparecchio": app, "dal": dal, "al": al, "eventi": eventi, "registro": registro[-2000:]},
                  f, ensure_ascii=False, indent=1)
    return p, len(anomalie), len(eventi)


# ------------------------------------------------------------------ dal vivo

def dal_vivo(app):
    print("Registro dal vivo il %s: usa pure la TV. Ctrl+C quando hai finito.\n" % app)
    titoli = _catalogo()
    visti = set()
    inizio = time.time()
    try:
        while True:
            appoggio = tempfile.mkdtemp(prefix="registratore-vivo-")
            try:
                if app == "pc":
                    _dal_pc(appoggio)
                else:
                    SCARICA[app](appoggio, con_foto=False)
                for e in _eventi(appoggio, inizio - 5, time.time() + 3600):
                    chiave = (e.get("ts"), e.get("tipo"))
                    if chiave in visti or e.get("tipo") == "registro":
                        continue
                    visti.add(chiave)
                    segno = "!!" if e.get("tipo") == "anomalia" else "  "
                    print("%s %s  %s" % (segno, e["t"][11:], _racconta(e, titoli)))
            except SystemExit:
                raise
            except Exception as errore:
                print("   (lettura non riuscita: %s)" % errore)
            finally:
                shutil.rmtree(appoggio, ignore_errors=True)
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nFinito: preparo il rapporto...")
    return inizio


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Il registratore della Videoteca")
    a.add_argument("apparecchio", choices=("box", "pi", "pc"))
    a.add_argument("--ore", type=float, default=6)
    a.add_argument("--dal", help="AAAA-MM-GG HH:MM (ora del PC)")
    a.add_argument("--vivo", action="store_true")
    a.add_argument("--non-aprire", action="store_true")
    o = a.parse_args(argv[1:])
    al = time.time()
    dal = al - o.ore * 3600
    if o.dal:
        dal = time.mktime(time.strptime(o.dal, "%Y-%m-%d %H:%M"))
    if o.vivo:
        dal = dal_vivo(o.apparecchio)
        al = time.time()
    appoggio = tempfile.mkdtemp(prefix="registratore-")
    try:
        print("Scarico scatola nera e registro dal %s..." % o.apparecchio)
        orologio = SCARICA[o.apparecchio](appoggio)
        # Gli eventi hanno l'ora assoluta; il registro l'ora locale dell'apparecchio,
        # che puo' essere diversa da quella del PC (il Raspberry sta in UTC): si allinea.
        scarto = _scarto_ora(appoggio, orologio)
        destinazione = os.path.join(USCITA, "%s-%s" % (o.apparecchio, time.strftime("%Y%m%d-%H%M")))
        p, n_anomalie, n_eventi = rapporto(o.apparecchio, appoggio, scarto, dal, al, destinazione)
    finally:
        shutil.rmtree(appoggio, ignore_errors=True)
    print("%d eventi, %d problemi -> %s" % (n_eventi, n_anomalie, p))
    if not o.non_aprire:
        R.apri_nel_browser(p)
    return 0


def _scarto_ora(cartella, orologio_apparecchio):
    """Secondi da togliere all'ora scritta nel registro per avere l'ora vera."""
    ultimo = None
    p = os.path.join(cartella, "kodi.log")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8", errors="replace") as h:
            for riga in h:
                m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", riga)
                if m:
                    ultimo = m.group(1)
    s = os.path.join(cartella, "scatola")
    eventi = []
    for f in sorted(os.listdir(s))[-1:] if os.path.isdir(s) else []:
        if f.endswith(".jsonl"):
            with io.open(os.path.join(s, f), encoding="utf-8", errors="replace") as h:
                eventi = [json.loads(r) for r in h if r.strip().startswith("{")][-1:]
    if eventi and "t" in eventi[0]:
        # l'evento porta sia l'ora locale dell'apparecchio (t) sia quella assoluta (ts)
        return time.mktime(time.strptime(eventi[0]["t"], "%Y-%m-%d %H:%M:%S")) - eventi[0]["ts"]
    if ultimo:
        return round((time.mktime(time.strptime(ultimo, "%Y-%m-%d %H:%M:%S")) - orologio_apparecchio) / 3600) * 3600
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
