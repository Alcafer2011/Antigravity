# -*- coding: utf-8 -*-
"""Cerca, per ogni saga del catalogo, le serie che NON ci sono ancora.

PERCHE'
    Super Dragon Ball Heroes mancava e l'utente se n'e' accorto da solo,
    ricordandosi episodi visti su YouTube che nel menu non trovava. La
    domanda giusta e': quante altre ne mancano? Questo programma la fa a
    TMDb per tutte le saghe insieme, invece di andare a memoria.

COME LAVORA
    Per ogni saga si cercano su TMDb i suoi nomi (anche quelli originali:
    "Lamu" non trova niente, "Urusei Yatsura" si') e si elencano TUTTE le
    serie TV che tornano. Poi si toglie quello che il catalogo ha gia',
    confrontando gli identificativi TMDb quando ci sono e i titoli quando
    non ci sono.

COSA NON FA
    Non decide. Sputa un elenco da leggere: TMDb restituisce anche rifacimenti,
    riassunti, versioni doppiate diverse e cose omonime. Decidere cosa entra
    nel catalogo e' un giudizio, e va fatto guardando.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
BASE = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe"

# I nomi da cercare per ogni saga. Scritti a mano, e non ricavati dal titolo
# italiano, perche' quasi nessuna di queste serie si chiama su TMDb come si
# chiamava in TV da noi.
DA_CERCARE = {
    "dragonball":  ["Dragon Ball"],
    "naruto":      ["Naruto", "Boruto"],
    "one_piece":   ["One Piece"],
    "zodiaco":     ["Saint Seiya", "Knights of the Zodiac"],
    "ken":         ["Fist of the North Star", "Hokuto no Ken"],
    "holly":       ["Captain Tsubasa"],
    "gonagai":     ["Devilman", "Cutie Honey", "Jeeg"],
    "mazinga":     ["Mazinger", "Great Mazinger", "Grendizer", "UFO Robot"],
    "lupin":       ["Lupin the Third", "Lupin III"],
    "gundam":      ["Mobile Suit Gundam"],
    "matsumoto":   ["Captain Harlock", "Galaxy Express 999", "Queen Emeraldas",
                    "Space Battleship Yamato"],
    "lamu":        ["Urusei Yatsura"],
    "heroes":      ["Super Dragon Ball Heroes"],
}


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1.5)
    return {}


def cerca(nome):
    d = get("https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s"
            % (K, urllib.parse.quote(nome)))
    return d.get("results") or []


def catalogo_attuale():
    """Cosa il catalogo ha gia': identificativi TMDb e titoli normalizzati."""
    testo = io.open(os.path.join(BASE, "resources", "lib", "catalogo.py"),
                    encoding="utf-8").read()
    titoli = set()
    for m in re.finditer(r'"titolo"\s*:\s*"([^"]+)"', testo):
        titoli.add(normalizza(m.group(1)))
    tmdb = set()
    cartella = os.path.join(BASE, "resources", "schede")
    for f in os.listdir(cartella):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(io.open(os.path.join(cartella, f), encoding="utf-8"))
        except ValueError:
            continue
        if d.get("tmdb"):
            tmdb.add(int(d["tmdb"]))
        if d.get("serie"):
            titoli.add(normalizza(d["serie"]))
    return tmdb, titoli


def normalizza(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def main():
    tmdb_noti, titoli_noti = catalogo_attuale()
    print("Il catalogo conosce %d identificativi TMDb e %d titoli.\n"
          % (len(tmdb_noti), len(titoli_noti)))

    for saga in sorted(DA_CERCARE):
        visti = {}
        for nome in DA_CERCARE[saga]:
            for t in cerca(nome):
                visti[t["id"]] = t
        mancanti = []
        for tid, t in visti.items():
            if tid in tmdb_noti:
                continue
            nomi = {normalizza(t.get("name") or ""),
                    normalizza(t.get("original_name") or "")}
            if nomi & titoli_noti:
                continue
            mancanti.append(t)

        if not mancanti:
            print("%-12s  tutto quello che TMDb conosce e' gia' dentro" % saga)
            continue

        print("%-12s  %d serie non presenti nel catalogo:" % (saga, len(mancanti)))
        mancanti.sort(key=lambda x: (x.get("first_air_date") or "9999"))
        for t in mancanti:
            det = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it"
                      % (t["id"], K))
            ep = det.get("number_of_episodes") or 0
            paesi = ",".join(det.get("origin_country") or [])
            print("   %-46s %s  %4d ep  %-4s  id=%d"
                  % ((t.get("name") or "")[:46],
                     (t.get("first_air_date") or "????")[:4], ep, paesi, t["id"]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
