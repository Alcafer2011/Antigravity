# -*- coding: utf-8 -*-
"""IL CONTROLLO DELLE RICERCHE: si prova TUTTO, non due voci a campione.

PERCHE' (l'utente, 12/09/2026)
    "io ti ho detto solo due sezioni, cioe' fast and loud e chernobyl, non ho
    potuto verificare tutto". Giusto: quelle erano due prove sue, non l'elenco
    dei guasti. Qui si provano tutte le voci che nella Videoteca fanno una
    ricerca - i generi dei documentari, quelli di cucina, i programmi, i titoli
    delle saghe - e si guarda cosa risponde davvero.

COSA MISURA, per ogni voce
    voci       quante righe arrivano a schermo (dopo il filtro di pertinenza)
    scartati   quante risposte dei siti non c'entravano con la domanda
    siti       quanti siti hanno risposto
    secondi    quanto ha aspettato
    e le prime righe, per poterle leggere una per una.

COME LEGGERLO
    - VUOTA: nessun risultato. Puo' essere giusto (quel programma sui siti non
      c'e') o un guasto (il catalogo non risponde piu'): il rapporto separa
      "nessuno ha risposto" da "hanno risposto ma non c'entrava niente".
    - SOSPETTA: arrivano righe, ma la prima non somiglia a quello che hai
      chiesto. Sono le "due Maria De Filippi dentro Chernobyl".

USO (vuole il Kodi del PC acceso: e' il banco di prova, non serve agli apparecchi)
    python prova_ricerche.py                      tutto (lento: una ricerca ogni pochi secondi)
    python prova_ricerche.py --quante 20          solo le prime 20 voci di ogni gruppo
    python prova_ricerche.py --solo documentari   documentari | cucina | saghe
    python prova_ricerche.py --non-aprire
"""

import argparse
import base64
import html
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(QUI, "plugin.video.saghe")
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, "atlante"))
sys.path.insert(0, ADDON)

import servi  # noqa: E402  solo per la password dell'API del Kodi del PC
from resources.lib import s4me_link, scoperte  # noqa: E402

USCITA = os.path.join(QUI, "atlante", "uscita", "RICERCHE.html")
PW = servi._password_api_pc()


def rpc(metodo, parametri, tempo=180):
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": parametri}).encode()
    richiesta = urllib.request.Request("http://127.0.0.1:8080/jsonrpc", corpo,
                                       {"Content-Type": "application/json"})
    if PW:
        richiesta.add_header("Authorization", "Basic " + base64.b64encode(("kodi:%s" % PW).encode()).decode())
    return json.loads(urllib.request.urlopen(richiesta, timeout=tempo).read())


def stato_ricerca():
    """Lo stato che il canale scrive durante la ricerca (siti, scartati, lenti)."""
    p = os.path.expandvars(r"%APPDATA%\Kodi\cache\videoteca-ricerca-siti.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def _piatto(t):
    t = unicodedata.normalize("NFKD", str(t or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).split()


VUOTE = {"il", "lo", "la", "i", "gli", "le", "un", "una", "uno", "di", "del", "della", "dei",
         "e", "the", "of", "a", "and", "n", "documentario", "documentari", "ricette", "cucina"}


def somiglia(trovato, voluto):
    """Quante delle parole chieste ci sono nella riga trovata (0-100)."""
    chieste = set(_piatto(voluto)) - VUOTE
    if not chieste:
        return 100
    return int(100.0 * len(chieste & set(_piatto(trovato))) / len(chieste))


def pulisci(etichetta):
    return re.sub(r"\[/?[A-Za-z][^\]]*\]", "", etichetta or "").strip()


def come_cerca_la_videoteca(testo):
    """La domanda come la fa l'add-on, non come e' scritta nel menu.

    `menu_scaffale_cerca` toglie "documentario/cucina/ricette" davanti: i
    cataloghi cercano nei TITOLI, e quasi nessun titolo contiene quella parola.
    Senza questa riga la prova misurerebbe una ricerca che nella Videoteca non
    avviene mai (e infatti dava "Lezioni di documentario")."""
    pulito = re.sub(r"(?i)^(documentari[oi]?|cucina|ricett[ae])\s+", "", testo).strip()
    # E senza la nota fra parentesi: nel catalogo le serie si distinguono con
    # "(terza serie)", "(rifacimento 2022)", ma sui siti quella scritta non
    # esiste - il canale infatti prova anche il titolo nudo
    # (lesaghe._titoli_da_provare, 12/09/2026).
    pulito = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*", " ", pulito).strip()
    return pulito or testo


def parola_piu_forte(testo):
    """La parola che porta il significato: la piu' lunga sopra le tre lettere.
    E' il ripiego che fa la Videoteca quando un genere non trova niente
    (main.menu_scaffale_cerca, 12/09/2026): "pizza fatta in casa" -> "pizza"."""
    parole = sorted((p for p in re.split(r"[^0-9A-Za-zÀ-ÿ']+", testo) if len(p) > 3), key=len, reverse=True)
    return parole[0] if parole else ""


def prova(testo, canali=(), con_ripiego=True):
    testo = come_cerca_la_videoteca(testo)
    indirizzo = s4me_link.indirizzo({"channel": "lesaghe", "action": "cerca_siti"},
                                    testo=testo, canali=",".join(canali), tempo=30)
    inizio = time.time()
    try:
        r = rpc("Files.GetDirectory", {"directory": indirizzo, "media": "video",
                                       "properties": ["title", "year"]})
        errore = r.get("error")
        file_voci = (r.get("result") or {}).get("files") or []
    except Exception as e:
        errore, file_voci = {"message": str(e)}, []
    righe = [pulisci(v.get("label", "")) for v in file_voci
             if v.get("file") and s4me_link.leggi(v["file"]).get("action")]
    st = stato_ricerca()
    esito = {"testo": testo, "righe": righe, "secondi": round(time.time() - inizio, 1),
             "errore": (errore or {}).get("message", "") if errore else "",
             "siti": st.get("totale", 0) if st.get("testo") == testo else 0,
             "scartati": st.get("scartati", 0) if st.get("testo") == testo else 0,
             "trovati": st.get("trovati", 0) if st.get("testo") == testo else 0}
    # Il ripiego dell'add-on: se non c'e' niente si richiede la parola forte.
    # Senza questo la prova misurerebbe una Videoteca diversa da quella vera.
    forte = parola_piu_forte(testo)
    if con_ripiego and canali and not righe and forte and forte.lower() != testo.lower():
        secondo = prova(forte, canali, con_ripiego=False)
        if secondo["righe"]:
            secondo["testo"] = "%s -> '%s'" % (testo, forte)
            secondo["ripiego"] = forte
            return secondo
    esito["voto"] = somiglia(righe[0], testo) if righe else 0
    if righe:
        esito["giudizio"] = "buona" if esito["voto"] >= 60 else "sospetta"
    elif esito["trovati"]:
        esito["giudizio"] = "tutto scartato"
    else:
        esito["giudizio"] = "vuota"
    return esito


def voci_da_provare(solo, quante):
    """(gruppo, voci, canali). I CANALI NON SONO SEMPRE GLI STESSI, ed e' il
    guasto della prima prova (12/09/2026): documentari e cucina nella Videoteca
    si cercano sui CATALOGHI (RaiPlay, Discovery+, La7, Pluto, Paramount,
    Mediaset), non sui 16 siti di film e serie. Provandoli sui siti sbagliati
    uscivano 97 "tutto scartato" che non erano guasti, solo la domanda fatta
    alla porta sbagliata."""
    gruppi = []
    if solo in (None, "documentari"):
        for intestazione, voci in scoperte.GENERI_DOC:
            gruppi.append(("Documentari - " + intestazione,
                           [(v[0], v[1]) for v in voci][:quante], scoperte.CANALI_CATALOGHI))
    if solo in (None, "cucina"):
        for intestazione, voci in scoperte.GENERI_CUCINA:
            gruppi.append(("Cucina - " + intestazione,
                           [(v[0], v[1]) for v in voci][:quante], scoperte.CANALI_CATALOGHI))
    if solo in (None, "saghe"):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "catalogo_pc", os.path.join(ADDON, "resources", "lib", "catalogo.py"))
            cat = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cat)
            titoli = [(s.get("titolo", ""), s.get("titolo", "")) for s in cat.SERIE.values()]
            visti, unici = set(), []
            for etichetta, query in titoli:
                if query and query.lower() not in visti:
                    visti.add(query.lower())
                    unici.append((etichetta, query))
            gruppi.append(("Serie del catalogo", unici[:quante], ()))
        except Exception as e:
            print("  (catalogo non letto: %s)" % e)
    return gruppi


STILE = """
:root{--sfondo:#f6f5f2;--carta:#fff;--testo:#1d1d1f;--tenue:#6b6b70;--riga:#e4e2dc;--ok:#2e7d32;--no:#c62828;--forse:#b26a00}
@media (prefers-color-scheme:dark){:root{--sfondo:#141416;--carta:#1f1f23;--testo:#ececef;--tenue:#9a9aa2;--riga:#34343a;
--ok:#6fcf73;--no:#ff6b6b;--forse:#ffb74d}}
*{box-sizing:border-box}body{margin:0;padding:24px clamp(16px,4vw,48px);background:var(--sfondo);color:var(--testo);
font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}h1{font-size:28px;margin:0}h2{margin:32px 0 10px}
.tenue{color:var(--tenue)}.carte{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.carta{background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:14px}.numero{font-size:30px;font-weight:700}
.ok{color:var(--ok)}.no{color:var(--no)}.forse{color:var(--forse)}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--riga);padding:6px 8px;text-align:left;vertical-align:top}
.tab{overflow-x:auto;background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:8px}
.pill{display:inline-block;border:1px solid var(--riga);border-radius:99px;padding:0 8px;font-size:12px}
"""


def rapporto(risultati, secondi):
    def carta(n, testo, classe=""):
        return "<div class='carta'><div class='numero %s'>%s</div><div class='tenue'>%s</div></div>" % (classe, n, testo)

    tutti = [e for _g, voci in risultati for e in voci]
    conta = {g: sum(1 for e in tutti if e["giudizio"] == g)
             for g in ("buona", "sospetta", "tutto scartato", "vuota")}
    sezioni = []
    for gruppo, voci in risultati:
        righe = []
        for e in voci:
            classe = {"buona": "ok", "sospetta": "forse", "vuota": "no", "tutto scartato": "no"}[e["giudizio"]]
            prime = "<br>".join(html.escape(r[:90]) for r in e["righe"][:3]) or "<span class='tenue'>-</span>"
            righe.append("<tr><td>%s</td><td class='%s'>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%s s</td><td>%s</td></tr>"
                         % (html.escape(e["testo"]), classe, e["giudizio"], len(e["righe"]),
                            e["scartati"], e["siti"], e["secondi"], prime))
        sezioni.append("<h2>%s</h2><div class='tab'><table><tr><th>cercato</th><th>esito</th><th>righe</th>"
                       "<th>scartate</th><th>siti</th><th>tempo</th><th>prime righe</th></tr>%s</table></div>"
                       % (html.escape(gruppo), "".join(righe)))
    pagina = ("<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' "
              "content='width=device-width,initial-scale=1'><title>Le ricerche della Videoteca</title>"
              "<style>%s</style></head><body><h1>Le ricerche della Videoteca</h1>"
              "<div class='tenue'>%s - %d ricerche provate in %d minuti</div>"
              % (STILE, time.strftime("%d/%m/%Y %H:%M"), len(tutti), secondi // 60)
              + "<div class='carte'>" + carta(conta["buona"], "buone", "ok")
              + carta(conta["sospetta"], "sospette (la prima riga non c'entra)", "forse")
              + carta(conta["tutto scartato"], "hanno risposto, ma niente c'entrava", "no")
              + carta(conta["vuota"], "nessuna risposta", "no") + "</div>"
              + "".join(sezioni) + "</body></html>")
    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    with io.open(USCITA, "w", encoding="utf-8") as f:
        f.write(pagina)
    return USCITA


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Prova tutte le ricerche della Videoteca")
    a.add_argument("--quante", type=int, default=1000)
    a.add_argument("--solo", choices=("documentari", "cucina", "saghe"))
    a.add_argument("--non-aprire", action="store_true")
    o = a.parse_args(argv[1:])
    try:
        rpc("JSONRPC.Ping", {}, tempo=10)
    except Exception as e:
        raise SystemExit("Il Kodi del PC non risponde su 127.0.0.1:8080 (%s)" % e)
    inizio = time.time()
    risultati = []
    for gruppo, voci, canali in voci_da_provare(o.solo, o.quante):
        esiti = []
        print("%s (%d voci, %s)" % (gruppo, len(voci), ", ".join(canali) if canali else "tutti i siti"))
        for etichetta, query in voci:
            e = prova(query, canali)
            e["etichetta"] = etichetta
            esiti.append(e)
            print("   %-38s %-14s righe %-3d scartate %-3d %ss"
                  % (query[:38], e["giudizio"], len(e["righe"]), e["scartati"], e["secondi"]))
        risultati.append((gruppo, esiti))
    p = rapporto(risultati, int(time.time() - inizio))
    print("rapporto: %s" % p)
    if not o.non_aprire:
        import raccolta
        raccolta.apri_nel_browser(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
