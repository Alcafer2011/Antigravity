# -*- coding: utf-8 -*-
"""
Scarica da TMDb titoli, trame e immagini di ogni episodio, in italiano, e le
scrive dentro l'addon come schede pronte.

Si esegue sul PC, non sul box: cosi' l'addon parte gia' completo e non deve
fare 600 chiamate di rete al primo avvio.

    python costruisci-schede.py <chiave_tmdb>
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w500"
IMG_POSTER = "https://image.tmdb.org/t/p/w500"

DESTINAZIONE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "plugin.video.saghe", "resources", "schede")

# offset = quanti episodi della stessa scheda TMDb appartengono alla serie
# precedente. Ken 1 e Ken 2 su TMDb sono un'unica voce da 152 episodi.
TMDB = {
    "db":                {"id": 12609,  "offset": 0},
    "dbz":               {"id": 12971,  "offset": 0},
    "daima":             {"id": 236994, "offset": 0},
    "dbs":               {"id": 62715,  "offset": 0},
    "gt":                {"id": 12697,  "offset": 0},
    "ss":                {"id": 42444,  "offset": 0},
    "ss_hades":          {"id": 67199,  "offset": 0},
    "ken1":              {"id": 56387,  "offset": 0},
    "ken2":              {"id": 56387,  "offset": 109},
    "holly":             {"id": 25707,  "offset": 0},
    "holly2":            {"id": 65835,  "offset": 0},
    "mazinga":           {"id": 19253,  "offset": 0},
    "mazinga_edition_z": {"id": 36249,  "offset": 0},
}


def chiama(percorso, chiave, **extra):
    par = {"api_key": chiave, "language": "it-IT"}
    par.update(extra)
    url = "%s%s?%s" % (BASE, percorso, urllib.parse.urlencode(par))
    for tentativo in range(4):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if tentativo == 3:
                raise
            time.sleep(1.5 * (tentativo + 1))
    return {}


def scarica_serie(serie_id, chiave):
    conf = TMDB[serie_id]
    testa = chiama("/tv/%d" % conf["id"], chiave)

    stagioni = sorted(
        [s for s in testa.get("seasons", []) if s.get("season_number", 0) > 0],
        key=lambda s: s["season_number"])

    scheda = {
        "serie": testa.get("name") or "",
        "poster": (IMG_POSTER + testa["poster_path"]) if testa.get("poster_path") else "",
        "sfondo": ("https://image.tmdb.org/t/p/w1280" + testa["backdrop_path"])
                  if testa.get("backdrop_path") else "",
        "episodi": {},
    }

    assoluto = 0
    for st in stagioni:
        dati = chiama("/tv/%d/season/%d" % (conf["id"], st["season_number"]), chiave)
        for ep in dati.get("episodes", []):
            assoluto += 1
            numero = assoluto - conf["offset"]
            if numero < 1:
                continue  # appartiene alla serie precedente
            scheda["episodi"][str(numero)] = {
                "t": (ep.get("name") or "").strip(),
                "p": (ep.get("overview") or "").strip(),
                "i": (IMG + ep["still_path"]) if ep.get("still_path") else "",
                "d": (ep.get("air_date") or "")[:10],
            }
        time.sleep(0.25)

    return scheda


def main():
    if len(sys.argv) < 2:
        print("uso: python costruisci-schede.py <chiave_tmdb>")
        return 1
    chiave = sys.argv[1]

    os.makedirs(DESTINAZIONE, exist_ok=True)
    totale_ep = 0
    con_trama = 0
    con_immagine = 0

    for serie_id in TMDB:
        try:
            scheda = scarica_serie(serie_id, chiave)
        except Exception as e:
            print("  ERRORE %-20s %s" % (serie_id, e))
            continue

        percorso = os.path.join(DESTINAZIONE, serie_id + ".json")
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(scheda, f, ensure_ascii=False, separators=(",", ":"))

        n = len(scheda["episodi"])
        t = sum(1 for e in scheda["episodi"].values() if e["p"])
        i = sum(1 for e in scheda["episodi"].values() if e["i"])
        totale_ep += n
        con_trama += t
        con_immagine += i
        print("  %-20s %4d episodi   trame %4d   immagini %4d   %s"
              % (serie_id, n, t, i, scheda["serie"]))

    print()
    print("TOTALE: %d episodi, %d con trama italiana (%d%%), %d con immagine (%d%%)"
          % (totale_ep, con_trama, 100 * con_trama // max(totale_ep, 1),
             con_immagine, 100 * con_immagine // max(totale_ep, 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
