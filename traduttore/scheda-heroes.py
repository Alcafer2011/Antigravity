# -*- coding: utf-8 -*-
"""Costruisce la scheda di Super Dragon Ball Heroes: 54 episodi in fila.

PERCHE' SERVE
    L'utente ricordava episodi visti su YouTube ("quando sconfigge i due
    gemellini") e non li trovava nel menu: quella serie nel catalogo non
    c'era proprio. E' un'anime promozionale, fuori dalla storia principale,
    ed e' per questo che era stata lasciata fuori - ma lui l'ha vista, quindi
    ci deve stare.

LA NUMERAZIONE
    Su TMDb la serie e' divisa in sei stagioni (gli "archi"). Qui vengono
    messe in fila in una catena unica 1-54, perche' e' cosi' che si guarda:
    un episodio dopo l'altro. La corrispondenza fra il numero della catena e
    l'arco vive in catalogo.ARCHI.
"""
import io
import json
import os
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
IMG = "https://image.tmdb.org/t/p/"
SERIE_ID = 80020
# le stagioni NELL'ORDINE DI USCITA. La 0 (Speciali) resta fuori: non sono
# episodi della storia, e infilarli in mezzo confonderebbe la numerazione.
STAGIONI = [1, 2, 3, 4, 5, 6]
USCITA = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe\resources\schede\sdbh.json"


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    d = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it"
            % (SERIE_ID, K))
    dati = {
        "serie": d.get("name") or "Super Dragon Ball Heroes",
        "tmdb": SERIE_ID,
        "anno": (d.get("first_air_date") or "")[:4],
        "poster": IMG + "w780" + d["poster_path"] if d.get("poster_path") else "",
        "sfondo": IMG + "w1280" + d["backdrop_path"] if d.get("backdrop_path") else "",
        "episodi": {},
    }

    n = 0
    confini = []
    for s in STAGIONI:
        st = get("https://api.themoviedb.org/3/tv/%d/season/%d?api_key=%s&language=it"
                 % (SERIE_ID, s, K))
        primo = n + 1
        for e in st.get("episodes", []):
            n += 1
            dati["episodi"][str(n)] = {
                "t": e.get("name") or "",
                "p": e.get("overview") or "",
                "i": (IMG + "w500" + e["still_path"]) if e.get("still_path") else "",
                "d": e.get("air_date") or "",
            }
        confini.append((st.get("name") or ("Stagione %d" % s), primo, n))

    io.open(USCITA, "w", encoding="utf-8", newline="\n").write(
        json.dumps(dati, ensure_ascii=False, indent=1))

    print("scritti %d episodi in %s" % (n, os.path.basename(USCITA)))
    print()
    print("Da incollare in catalogo.ARCHI:")
    print('    "heroes": [')
    for nome, a, b in confini:
        print('        ("%s",%s %3d, %3d),' % (nome, " " * max(0, 44 - len(nome)), a, b))
    print("    ],")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
