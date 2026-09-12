# -*- coding: utf-8 -*-
"""OGNI COSA AL SUO POSTO: il controllo delle collocazioni.

PERCHE' (l'utente, 12/09/2026)
    "devi anche verificare con python, con un controllore o te stesso, che
    tutte le cose cadano nel posto giusto: documentari nei documentari, film
    nei film ecc, divisi e ottimizzati nel modo corretto".
    Le prove di prima guardavano se le RICERCHE rispondono; questa guarda se la
    VIDEOTECA e' ordinata: che dentro Documentari non ci finisca la cucina, che
    un film non stia fra le serie, che ogni voce porti dove dice di portare.

DUE CONTROLLI, e il secondo serve perche' il primo non basta
    1. SULLE LISTE (senza Kodi): catalogo, scaffali e schede. Percorsi orfani,
       serie che nessuno usa, doppioni fra sezioni, film senza anno, canali
       YouTube con un identificativo sbagliato, voci con un tipo che non esiste.
    2. DAL VIVO (col Kodi del PC): si aprono davvero i menu, uno per uno, e si
       guarda DOVE porta ogni riga. Una voce puo' essere scritta giusta nelle
       liste e finire lo stesso nel posto sbagliato, perche' e' il codice a
       decidere l'indirizzo. Qui si controlla il risultato, non l'intenzione.

USO
    python prova_struttura.py              liste + dal vivo
    python prova_struttura.py --solo-liste senza Kodi (velocissimo)
    python prova_struttura.py --non-aprire
Uscita: atlante/uscita/STRUTTURA.html
"""

import argparse
import base64
import html
import importlib.util
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(QUI, "plugin.video.saghe")
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, "atlante"))
sys.path.insert(0, ADDON)

USCITA = os.path.join(QUI, "atlante", "uscita", "STRUTTURA.html")
BASE = "plugin://plugin.video.saghe/"


def modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CATALOGO = modulo("catalogo_pc", os.path.join(ADDON, "resources", "lib", "catalogo.py"))
SCOPERTE = modulo("scoperte_pc", os.path.join(ADDON, "resources", "lib", "scoperte.py"))


def guasto(elenco, dove, cosa, gravita="alto"):
    elenco.append({"dove": dove, "cosa": cosa, "gravita": gravita})


# --------------------------------------------------------------- 1. le liste

def controlla_catalogo(guasti):
    percorsi = CATALOGO.PERCORSI
    gruppi = getattr(CATALOGO, "GRUPPI", {})
    ordine = list(getattr(CATALOGO, "ORDINE_PERCORSI", []))
    nei_gruppi = [pid for g in gruppi.values() for pid in g.get("percorsi", [])]

    for pid in percorsi:
        if pid not in ordine and pid not in nei_gruppi:
            guasto(guasti, "catalogo", "la saga '%s' non sta ne' nel menu principale ne' in un "
                                       "raggruppamento: non si raggiunge da nessuna parte" % pid)
    doppi = [pid for pid in ordine if pid in nei_gruppi]
    for pid in doppi:
        guasto(guasti, "catalogo", "la saga '%s' compare due volte: nel menu principale E in un "
                                   "raggruppamento" % pid, "medio")
    for pid in ordine + nei_gruppi:
        if pid not in percorsi:
            guasto(guasti, "catalogo", "il menu nomina la saga '%s', che nel catalogo non esiste" % pid)

    usate = set()
    for pid, p in percorsi.items():
        segmenti = p.get("segmenti") or []
        if not segmenti:
            guasto(guasti, "catalogo", "la saga '%s' non ha nessuna serie dentro" % pid)
        for seg in segmenti:
            sid = seg[0]
            usate.add(sid)
            if sid not in CATALOGO.SERIE:
                guasto(guasti, "catalogo", "la saga '%s' usa la serie '%s', che non esiste" % (pid, sid))
    for sid in CATALOGO.SERIE:
        if sid not in usate:
            guasto(guasti, "catalogo", "la serie '%s' non e' usata da nessuna saga: e' invisibile" % sid, "medio")


def controlla_film(guasti):
    cartella = os.path.join(ADDON, "resources", "film")
    if not os.path.isdir(cartella):
        return
    for nome in sorted(os.listdir(cartella)):
        if not nome.endswith(".json"):
            continue
        pid = nome[:-5]
        if pid not in CATALOGO.PERCORSI:
            guasto(guasti, "film", "c'e' l'elenco film di '%s', ma quella saga non esiste" % pid, "medio")
        try:
            with io.open(os.path.join(cartella, nome), encoding="utf-8") as f:
                film = json.load(f)
        except (OSError, ValueError) as e:
            guasto(guasti, "film", "l'elenco film di '%s' non si legge: %s" % (pid, e))
            continue
        visti = set()
        for m in film:
            titolo = (m.get("t") or "").strip()
            if not titolo:
                guasto(guasti, "film", "in '%s' c'e' un film senza titolo" % pid)
                continue
            if titolo.lower() in visti:
                guasto(guasti, "film", "in '%s' il film '%s' e' ripetuto" % (pid, titolo), "medio")
            visti.add(titolo.lower())
            anno = str(m.get("d", ""))[:4]
            if not re.match(r"^(19|20)\d{2}$", anno):
                # SENZA ANNO NON E' PIU' UN GUASTO (12/09/2026): sono i film
                # soltanto ANNUNCIATI, e la data non ce l'ha nemmeno TMDb.
                # L'add-on adesso li mostra come "in arrivo" e non manda
                # nessuno a cercarli, quindi qui si segnalano come promemoria -
                # il giorno che escono, l'anno va messo.
                guasto(guasti, "film", "'%s' (%s) non ha una data: e' un film solo annunciato. "
                                       "La Videoteca lo mostra come 'in arrivo' e non lo cerca; "
                                       "quando uscira' va rimesso l'anno" % (titolo, pid), "medio")


# Parole che dicono di che scaffale e' una voce: se compaiono nello scaffale
# sbagliato, qualcosa e' finito nel posto sbagliato.
DI_CUCINA = re.compile(r"(?i)ricett|cucin|chef|pasticc|pizza|pasta|dolci|torte|gelat|cocktail|vino|"
                       r"masterchef|bake off|cannavacciuolo|barbieri|cracco|ramsay|borghese|mezzogiorno")
DI_DOCUMENTARI = re.compile(r"(?i)documentar|dinosaur|vichingh|piramid|nasa|universo|vulcan|squal|"
                            r"archeolog|guerra mondiale|olocaust|serial killer|mafia|titanic|chernobyl")


def controlla_scaffali(guasti):
    etichette = {}
    for quale in ("documentari", "cucina", "youtube"):
        try:
            gruppi = SCOPERTE.scaffale(quale)
        except Exception as e:
            guasto(guasti, "scaffali", "lo scaffale '%s' non si costruisce: %s" % (quale, e))
            continue
        for intestazione, voci in gruppi:
            for voce in voci:
                if len(voce) != 4:
                    guasto(guasti, "scaffali", "voce malformata in %s/%s: %r" % (quale, intestazione, voce))
                    continue
                etichetta, indirizzo, _nota, tipo = voce
                # I CATALOGHI stanno in piu' scaffali per forza: RaiPlay ha sia
                # documentari sia cucina, e non e' un doppione ma la stessa
                # porta aperta da due stanze (falso allarme del primo giro).
                if tipo != "catalogo":
                    etichette.setdefault(etichetta.lower(), []).append(quale)
                if not (tipo.startswith("cerca:") or tipo.startswith("diretta:")
                        or tipo in ("catalogo", "youtube", "canale")):
                    guasto(guasti, "scaffali", "'%s' (%s) ha un tipo sconosciuto: '%s'"
                           % (etichetta, quale, tipo), "medio")
                if quale == "youtube" and "youtube" in (indirizzo or ""):
                    if not re.search(r"/channel/UC[0-9A-Za-z_-]{20,}/", indirizzo or ""):
                        guasto(guasti, "scaffali", "il canale YouTube '%s' non ha un identificativo "
                                                   "valido: col nome si finisce su un canale sosia" % etichetta, "medio")
                # la prova vera: cucina dentro documentari e viceversa
                testo = "%s %s" % (etichetta, tipo)
                if quale == "documentari" and DI_CUCINA.search(testo) and not DI_DOCUMENTARI.search(testo):
                    guasto(guasti, "scaffali", "'%s' sta nei DOCUMENTARI ma sembra di cucina" % etichetta)
                if quale == "cucina" and DI_DOCUMENTARI.search(testo) and not DI_CUCINA.search(testo):
                    guasto(guasti, "scaffali", "'%s' sta nella CUCINA ma sembra un documentario" % etichetta)
    for etichetta, dove in etichette.items():
        if len(set(dove)) > 1:
            guasto(guasti, "scaffali", "'%s' compare in piu' scaffali: %s" % (etichetta, ", ".join(sorted(set(dove)))), "medio")


# ------------------------------------------------------------- 2. dal vivo

PW = None


def rpc(metodo, parametri, tempo=180):
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": parametri}).encode()
    richiesta = urllib.request.Request("http://127.0.0.1:8080/jsonrpc", corpo,
                                       {"Content-Type": "application/json"})
    if PW:
        richiesta.add_header("Authorization", "Basic " + base64.b64encode(("kodi:%s" % PW).encode()).decode())
    return json.loads(urllib.request.urlopen(richiesta, timeout=tempo).read())


def azione_di(indirizzo):
    if not (indirizzo or "").startswith(BASE):
        return ""
    campi = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(indirizzo).query))
    return campi.get("azione", "")


def parametri_di(indirizzo):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(indirizzo).query))


# Cosa PUO' stare dentro cosa. La chiave e' l'azione del menu che si apre, il
# valore le azioni ammesse per le sue righe (piu' gli indirizzi di altri
# add-on, che si controllano a parte).
AMMESSE = {
    "scaffale": {"scaffale", "scaffale_cerca", "diretta", "tv_apri", ""},
    "scaffale_cerca": {"", "cerca"},
    "reparto": {"percorso", "gruppo", "reparto", "scaffale", "film_tutti", "cinema", "netflix",
                "consigli", "tv", "cerca", "linea", "abbonamenti", "russo", "assistenza", ""},
    "gruppo": {"percorso", "gruppo", ""},
    # "tagli" = "Dove la TV italiana ti ha interrotto": e' una voce vera della
    # saga, non un errore (il primo giro del controllo la segnalava, 12/09/2026).
    "percorso": {"sfoglia", "film", "capitoli", "altro", "riproduci", "azzera", "spiega", "salta",
                 "vai", "stato_linea", "percorso", "tagli", "visto", "nonvisto", "anomalie",
                 "russo", "cerca", ""},
    "film": {"apri_film", "film", ""},
    "film_tutti": {"apri_film", "film", "percorso", ""},
}


def figli(indirizzo, tempo=120):
    r = rpc("Files.GetDirectory", {"directory": indirizzo, "media": "video",
                                   "properties": ["title"]}, tempo=tempo)
    if "error" in r:
        return None, r["error"].get("message", "errore")
    return ((r.get("result") or {}).get("files") or []), ""


def controlla_dal_vivo(guasti, profondita=2):
    visti = set()

    def scendi(indirizzo, livello, catena):
        if indirizzo in visti or livello > profondita:
            return
        visti.add(indirizzo)
        azione = azione_di(indirizzo)
        voci, errore = figli(indirizzo)
        if errore:
            guasto(guasti, "dal vivo", "%s non si apre: %s" % (catena, errore))
            return
        ammesse = AMMESSE.get(azione)
        for v in voci:
            figlio = v.get("file", "")
            etichetta = re.sub(r"\[/?[A-Za-z][^\]]*\]", "", v.get("label", "")).strip()
            sotto_azione = azione_di(figlio)
            if figlio.startswith(BASE) and ammesse is not None and sotto_azione not in ammesse:
                guasto(guasti, "dal vivo", "dentro '%s' la voce '%s' porta a '%s', che li' non "
                                           "dovrebbe starci" % (catena, etichetta, sotto_azione or "?"))
            # i documentari devono restare documentari anche nell'indirizzo
            if azione == "scaffale":
                mio = parametri_di(indirizzo).get("scaffale", "")
                suo = parametri_di(figlio).get("scaffale", mio)
                if suo and suo != mio:
                    guasto(guasti, "dal vivo", "dentro lo scaffale '%s' la voce '%s' punta allo "
                                               "scaffale '%s'" % (mio, etichetta, suo))
            if figlio.startswith(BASE) and sotto_azione in ("scaffale", "reparto", "gruppo", "percorso", "film"):
                scendi(figlio, livello + 1, "%s > %s" % (catena, etichetta))

    for quale in ("documentari", "cucina", "youtube"):
        scendi(BASE + "?azione=scaffale&scaffale=" + quale, 1, "Scaffale " + quale)
    scendi(BASE, 0, "Home")


# ------------------------------------------------------------------ rapporto

STILE = """
:root{--sfondo:#f6f5f2;--carta:#fff;--testo:#1d1d1f;--tenue:#6b6b70;--riga:#e4e2dc;--ok:#2e7d32;--no:#c62828;--forse:#b26a00}
@media (prefers-color-scheme:dark){:root{--sfondo:#141416;--carta:#1f1f23;--testo:#ececef;--tenue:#9a9aa2;--riga:#34343a;
--ok:#6fcf73;--no:#ff6b6b;--forse:#ffb74d}}
*{box-sizing:border-box}body{margin:0;padding:24px clamp(16px,4vw,48px);background:var(--sfondo);color:var(--testo);
font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}h1{font-size:28px;margin:0}h2{margin:30px 0 10px}
.tenue{color:var(--tenue)}.carte{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:18px 0}
.carta{background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:14px}.numero{font-size:30px;font-weight:700}
.ok{color:var(--ok)}.no{color:var(--no)}.forse{color:var(--forse)}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--riga);padding:6px 8px;text-align:left;vertical-align:top}
.tab{overflow-x:auto;background:var(--carta);border:1px solid var(--riga);border-radius:12px;padding:8px}
"""


def rapporto(guasti, secondi, solo_liste):
    alti = [g for g in guasti if g["gravita"] == "alto"]
    medi = [g for g in guasti if g["gravita"] != "alto"]

    def carta(n, testo, classe=""):
        return "<div class='carta'><div class='numero %s'>%s</div><div class='tenue'>%s</div></div>" % (classe, n, testo)

    def tabella(elenco):
        return ("<div class='tab'><table><tr><th>dove</th><th>cosa non torna</th></tr>%s</table></div>"
                % "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(g["dove"]), html.escape(g["cosa"]))
                          for g in elenco))
    pagina = ("<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' "
              "content='width=device-width,initial-scale=1'><title>Ogni cosa al suo posto</title>"
              "<style>%s</style></head><body><h1>Ogni cosa al suo posto</h1>"
              "<div class='tenue'>%s - controllo in %d secondi%s</div>"
              % (STILE, time.strftime("%d/%m/%Y %H:%M"), secondi, " - solo liste" if solo_liste else "")
              + "<div class='carte'>" + carta(len(alti), "cose fuori posto", "no" if alti else "ok")
              + carta(len(medi), "da guardare", "forse" if medi else "ok") + "</div>"
              + (("<h2>Fuori posto</h2>" + tabella(alti)) if alti else
                 "<h2 class='ok'>Niente fuori posto</h2>")
              + (("<h2>Da guardare</h2>" + tabella(medi)) if medi else "")
              + "</body></html>")
    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    with io.open(USCITA, "w", encoding="utf-8") as f:
        f.write(pagina)
    return USCITA


def main(argv):
    global PW
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Controlla che ogni cosa stia nella sua sezione")
    a.add_argument("--solo-liste", action="store_true")
    a.add_argument("--non-aprire", action="store_true")
    o = a.parse_args(argv[1:])
    inizio = time.time()
    guasti = []
    print("1/2 le liste (catalogo, film, scaffali)...")
    controlla_catalogo(guasti)
    controlla_film(guasti)
    controlla_scaffali(guasti)
    print("    %d cose da segnalare" % len(guasti))
    if not o.solo_liste:
        import servi
        PW = servi._password_api_pc()
        print("2/2 dal vivo, aprendo i menu sul Kodi del PC...")
        try:
            controlla_dal_vivo(guasti)
        except Exception as e:
            print("    (dal vivo non riuscito: %s)" % e)
    for g in guasti:
        print("   [%s] %s: %s" % (g["gravita"], g["dove"], g["cosa"]))
    p = rapporto(guasti, int(time.time() - inizio), o.solo_liste)
    print("rapporto: %s" % p)
    if not o.non_aprire:
        import raccolta
        raccolta.apri_nel_browser(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
