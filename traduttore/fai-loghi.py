# -*- coding: utf-8 -*-
"""TROVA IL LOGO DEL TITOLO (clearlogo) DI OGNI SERIE, DA TMDb.

PERCHE'
    Sulla skin Arctic Zephyr, sopra la locandina scelta, compare la SCRITTA
    DEL TITOLO disegnata - il "clearlogo". All'utente e' piaciuto subito
    ("mostra le locandine con i titoli scritti sopra belli"). E' la stessa
    cosa che fa Netflix.
    Il nostro add-on in `clearlogo` metteva invece il logo del SERVIZIO
    (Netflix, Prime...): con questa skin sarebbe comparso il marchio del
    servizio al posto del titolo. Quello e' stato tolto; qui si mette il
    logo giusto.

DA DOVE
    TMDb, `/tv/<id>/images`, lista `logos`: PNG trasparenti col titolo. Gli
    identificativi delle nostre serie stanno gia' in `resources/tmdb.json`.

LA LINGUA
    Il logo ITALIANO quando c'e'. Ma quasi sempre non c'e' (verificato il
    10/09: Dragon Ball, Naruto, One Piece, Holly e Benji, Ken hanno loghi
    solo inglesi o senza lingua). All'utente il logo piace comunque, quindi:
    italiano > senza lingua > inglese > qualunque. Un logo inglese sopra una
    locandina e' meglio di nessun logo; il titolo italiano resta nella
    testata e sulla tessera della nostra skin.

    Fra piu' loghi della stessa lingua si prende il piu' votato su TMDb, e
    a parita' il piu' largo: un logo quadrato sta male sopra una locandina.

USO
    python fai-loghi.py            scrive resources/loghi_titolo.json
    python fai-loghi.py --riprova  ricerca anche le serie gia' senza logo
"""

import io
import json
import os
import sys
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(QUI, "plugin.video.saghe", "resources")
FUORI = os.path.join(RES, "loghi_titolo.json")
CHIAVE = "a1ab8b8669da03637a4b98fa39c39228"
IMG = "https://image.tmdb.org/t/p/w500%s"
PREFERENZA = {"it": 0, None: 1, "": 1, "en": 2}


def _chiedi(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return {}


def logo(tmdb_id):
    d = _chiedi("https://api.themoviedb.org/3/tv/%s/images?api_key=%s"
                "&include_image_language=it,null,en" % (tmdb_id, CHIAVE))
    loghi = [x for x in (d.get("logos") or []) if x.get("file_path")]
    if not loghi:
        return ""

    def voto(x):
        lingua = x.get("iso_639_1")
        return (PREFERENZA.get(lingua, 3),
                -(x.get("vote_average") or 0),
                -(x.get("aspect_ratio") or 0))

    return IMG % sorted(loghi, key=voto)[0]["file_path"]


def main():
    with io.open(os.path.join(RES, "tmdb.json"), encoding="utf-8") as f:
        ids = json.load(f)
    try:
        with io.open(FUORI, encoding="utf-8") as f:
            gia = json.load(f) or {}
    except Exception:
        gia = {}
    riprova = "--riprova" in sys.argv

    # Piu' serie nostre possono avere lo stesso id TMDb (bleach e
    # bleach_tybw): si chiede una volta sola.
    per_id = {}
    trovati = nuovi = 0
    for sid in sorted(ids):
        conf = ids[sid]
        tid = conf.get("id") if isinstance(conf, dict) else conf
        if not tid:
            continue
        if sid in gia and not riprova:
            trovati += 1 if gia[sid] else 0
            continue
        if tid not in per_id:
            per_id[tid] = logo(tid)
            nuovi += 1
        gia[sid] = per_id[tid]
        trovati += 1 if gia[sid] else 0
        print("  %-24s %s" % (sid, "ok" if gia[sid] else "-"))

    with io.open(FUORI, "w", encoding="utf-8") as f:
        f.write(json.dumps(gia, ensure_ascii=False, indent=1, sort_keys=True))
    print("\n%d serie: %d con logo del titolo (chieste ora a TMDb: %d)  ->  %s"
          % (len(gia), trovati, nuovi, FUORI))
    return 0


if __name__ == "__main__":
    sys.exit(main())
