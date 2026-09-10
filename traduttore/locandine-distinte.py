# -*- coding: utf-8 -*-
"""Da' una locandina DIVERSA a ogni saga che ne condivide una.

IL GUASTO (utente, 07/09): "ci sono locandine uguali per saghe diverse".
Vero: le sei serie di Lupin avevano tutte e sei lo stesso poster, e cosi'
Ken 1/2 e Bleach/TYBW. Non e' un errore di dati - e' che TMDB ha UNA scheda
sola per tutto Lupin III, e le nostre sei serie ci puntano tutte.

COME SI RISOLVE, senza inventare
    TMDB, oltre al poster principale, tiene TUTTE le locandine caricate per
    quella serie (`/tv/{id}/images`): spesso decine, una per stagione, per
    edizione, per paese. Sono tutte locandine VERE di quella serie. Se ne
    da' una diversa a ognuna delle nostre.
    L'ordine di preferenza: prima quelle italiane, poi quelle senza lingua
    (le copertine senza scritte), poi le inglesi; a parita', quella con il
    voto piu' alto.

    Se TMDB non ne ha abbastanza si prova Kitsu, che le serie di anime le
    tiene SEPARATE (Lupin parte 1, parte 2, ...) e non vuole nessuna chiave.

NON si tocca chi ha gia' una locandina sua: si cambiano solo i doppioni,
e si lascia la prima serie del gruppo com'era.
"""

import io
import json
import os
import sys
import time
import urllib.request
from urllib.parse import quote

SCHEDE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "plugin.video.saghe", "resources", "schede")
CHIAVE = "a1ab8b8669da03637a4b98fa39c39228"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def chiedi(url, tentativi=2):
    for _ in range(tentativi):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=25) as f:
                return json.loads(f.read().decode("utf-8", "ignore"))
        except Exception:
            time.sleep(1.0)
    return {}


def carica():
    d = {}
    for n in sorted(os.listdir(SCHEDE)):
        if n.endswith(".json"):
            with io.open(os.path.join(SCHEDE, n), encoding="utf-8") as f:
                d[n[:-5]] = json.load(f)
    return d


def gruppi_doppi(schede):
    per_poster = {}
    for sid, s in schede.items():
        p = s.get("poster") or ""
        if p:
            per_poster.setdefault(p, []).append(sid)
    return {p: sorted(v) for p, v in per_poster.items() if len(v) > 1}


def locandine_tmdb(tmdb_id):
    """Tutte le locandine di quella serie, dalla migliore alla peggiore."""
    if not tmdb_id:
        return []
    d = chiedi("https://api.themoviedb.org/3/tv/%s/images?api_key=%s"
               "&include_image_language=it,null,en,ja" % (tmdb_id, CHIAVE))
    def rango(x):
        lingua = x.get("iso_639_1")
        ordine = {"it": 0, None: 1, "en": 2}.get(lingua, 3)
        return (ordine, -(x.get("vote_average") or 0))
    poster = sorted(d.get("posters") or [], key=rango)
    return ["https://image.tmdb.org/t/p/w780%s" % x["file_path"]
            for x in poster if x.get("file_path")]


def locandina_kitsu(titolo):
    d = chiedi("https://kitsu.io/api/edge/anime?filter%%5Btext%%5D=%s"
               "&page%%5Blimit%%5D=3" % quote(titolo))
    for v in (d.get("data") or []):
        a = v.get("attributes") or {}
        img = (a.get("posterImage") or {}).get("original") or ""
        if img:
            return img
    return ""


def main():
    scrivi = "--scrivi" in sys.argv
    schede = carica()
    doppi = gruppi_doppi(schede)
    if not doppi:
        print("nessuna locandina condivisa: niente da fare")
        return
    cambi = {}
    for poster, ids in doppi.items():
        primo, altri = ids[0], ids[1:]
        tmdb_id = schede[primo].get("tmdb")
        magazzino = [u for u in locandine_tmdb(tmdb_id) if u != poster]
        print("\n%s  (%d serie, tmdb %s, %d locandine alternative)"
              % (", ".join(ids), len(ids), tmdb_id, len(magazzino)))
        print("   %-16s tiene la sua" % primo)
        for sid in altri:
            nuova = magazzino.pop(0) if magazzino else locandina_kitsu(
                schede[sid].get("serie") or sid)
            if not nuova or nuova == poster:
                print("   %-16s NIENTE DI DIVERSO trovato" % sid)
                continue
            cambi[sid] = nuova
            print("   %-16s -> %s" % (sid, nuova[-32:]))
    print("\nda cambiare: %d serie" % len(cambi))
    if not scrivi:
        print("(prova a vuoto: rilancia con --scrivi per applicare)")
        return
    for sid, url in cambi.items():
        f = os.path.join(SCHEDE, sid + ".json")
        with io.open(f, encoding="utf-8") as h:
            d = json.load(h)
        d["poster"] = url
        with io.open(f, "w", encoding="utf-8") as h:
            h.write(json.dumps(d, ensure_ascii=False))
    print("scritte %d schede" % len(cambi))
    # verifica: non devono restare doppioni
    rimasti = gruppi_doppi(carica())
    print("locandine ancora condivise:", len(rimasti),
          list(rimasti.values()) if rimasti else "")


if __name__ == "__main__":
    main()
