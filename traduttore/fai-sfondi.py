# -*- coding: utf-8 -*-
"""TROVA LO SFONDO 16:9 delle voci di Documentari, Cucina e YouTube.

PERCHE'
    Le tessere della home ora sono ORIZZONTALI, come quelle di Netflix.
    Per 220 voci su 409 l'immagine larga c'e' gia' (le saghe, i film, le
    serie, il cinema). Per le altre 189 abbiamo solo la LOCANDINA VERTICALE
    trovata da `copertine.py`: dentro una cornice 16:9 sta centrata fra due
    bande scure. Non e' sbagliata, ma non e' il colpo d'occhio giusto.

    TMDb, oltre al poster, ha i `backdrop`: sono proprio immagini 16:9. Basta
    chiederli. `copertine.json` pero' tiene solo l'INDIRIZZO dell'immagine,
    non l'identificativo TMDb, quindi la ricerca va rifatta per titolo.

LE REGOLE DI CONFRONTO NON SI RISCRIVONO
    Si importa `copertine.py` e si usano le SUE funzioni (`_combacia`,
    `_chiedi`, `_query_pulita`). Riscriverle qui vorrebbe dire averne due
    versioni che col tempo si scostano, e la soglia dei titoli e' proprio
    quella che evita "Terra Nova al posto di Terra amara".
    `copertine.py` importa `xbmcvfs`, che fuori da Kodi non esiste: si mette
    un finto modulo prima dell'import. Serve solo per i percorsi dei file,
    che qui non usiamo.

QUANDO NON C'E' NIENTE
    Uno chef e' una PERSONA: TMDb non ha un backdrop per una persona. Quelle
    voci restano senza sfondo largo e prendono la tessera scura generata,
    col titolo scritto dalla skin. E' giusto cosi': meglio una tessera
    pulita che l'immagine di un programma che non c'entra.

USO
    python fai-sfondi.py            cerca e scrive resources/sfondi.json
    python fai-sfondi.py --riprova  ricerca anche quelle gia' senza sfondo
"""

import io
import json
import os
import sys
import types
import importlib.util
from urllib.parse import quote

QUI = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(QUI, "plugin.video.saghe")
LIB = os.path.join(ADDON, "resources", "lib")
FUORI = os.path.join(ADDON, "resources", "sfondi.json")

# TMDb da' il backdrop in piu' misure: w780 e' abbastanza per una tessera
# larga 288 anche su uno schermo 4K, e pesa un terzo di original.
IMG = "https://image.tmdb.org/t/p/w780%s"


def _carica(nome):
    """Importa un modulo dell'add-on fuori da Kodi."""
    if "xbmcvfs" not in sys.modules:          # finto: serve solo ai percorsi
        finto = types.ModuleType("xbmcvfs")
        finto.translatePath = lambda p: p
        finto.exists = lambda p: True
        finto.mkdirs = lambda p: None
        sys.modules["xbmcvfs"] = finto
    spec = importlib.util.spec_from_file_location(nome, os.path.join(LIB, nome + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sfondo_tmdb(cop, titolo, tema=False):
    """Il backdrop 16:9 di un programma. "" se non c'e' niente di sicuro."""
    for lingua in ("it-IT", "en-US"):
        d = cop._chiedi("https://api.themoviedb.org/3/search/multi"
                        "?api_key=%s&language=%s&query=%s"
                        % (cop.CHIAVE_TMDB, lingua, quote(titolo)))
        risultati = (d.get("results") or [])[:8]
        # 1) il titolo deve combaciare davvero: e' la soglia che evita di
        #    mettere un'immagine sbagliata, che e' PEGGIO di nessuna
        #    immagine perche' sembra giusta.
        for r in risultati:
            nome = r.get("name") or r.get("title") or ""
            if r.get("backdrop_path") and cop._combacia(nome, titolo):
                return IMG % r["backdrop_path"]
        # 2) per i TEMI ("Vulcani", "Deserti") va bene il primo
        #    documentario: un documentario sui vulcani sta bene sotto
        #    "Vulcani". Stessa regola gia' usata per le locandine.
        if tema:
            for r in risultati:
                if (r.get("backdrop_path")
                        and r.get("media_type") in ("tv", "movie")
                        and 99 in (r.get("genre_ids") or [])):
                    return IMG % r["backdrop_path"]
    return ""


def main():
    cop = _carica("copertine")
    sc = _carica("scoperte")
    try:
        with io.open(FUORI, encoding="utf-8") as f:
            gia = json.load(f) or {}
    except Exception:
        gia = {}
    riprova = "--riprova" in sys.argv

    voci = []
    for sezione in ("documentari", "cucina", "youtube"):
        for intestazione, elenco in sc.scaffale(sezione):
            for etichetta, _ind, _nota, tipo in elenco:
                # I CATALOGHI (RaiPlay, Discovery+) e la DIRETTA si saltano,
                # come per le locandine: cercandoli su TMDb "Paramount" e
                # "Pluto TV" prendevano il primo titolo che conteneva quella
                # parola. Un'immagine sbagliata sembra giusta.
                if tipo == "catalogo" or tipo.startswith("diretta:"):
                    continue
                voci.append((etichetta, tipo))

    trovati, saltati, nuovi = 0, 0, 0
    for i, (etichetta, tipo) in enumerate(voci, 1):
        if etichetta in gia and not riprova:
            if gia[etichetta]:
                trovati += 1
            else:
                saltati += 1
            continue
        # la query pulita, non l'etichetta decorata: "American Chopper (le
        # moto Harley)" su TMDb non esiste, "American Chopper" si'.
        q = tipo.split(":", 1)[1] if tipo.startswith("cerca:") else etichetta
        url = sfondo_tmdb(cop, q, tema=True)
        gia[etichetta] = url
        nuovi += 1
        if url:
            trovati += 1
        else:
            saltati += 1
        print("  %3d/%d  %-38s %s" % (i, len(voci), etichetta[:38],
                                      "ok" if url else "-"))

    with io.open(FUORI, "w", encoding="utf-8") as f:
        f.write(json.dumps(gia, ensure_ascii=False, indent=1, sort_keys=True))
    print("\n%d voci: %d con sfondo largo, %d senza (tessera scura col titolo)"
          % (len(voci), trovati, saltati))
    print("cercate ora: %d   ->  %s" % (nuovi, FUORI))
    return 0


if __name__ == "__main__":
    sys.exit(main())
