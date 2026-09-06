# -*- coding: utf-8 -*-
"""Cerca le serie turche che in Italia esistono DOPPIATE.

PERCHE' HA SENSO NEL NOSTRO ADD-ON
    Le serie turche in Italia hanno lo stesso identico problema degli anime
    degli anni Ottanta, ed e' il problema che questo add-on esiste per
    risolvere: arrivano a pezzi, cambiano nome, saltano episodi, vengono
    spostate di canale o interrotte a meta'. Chi le segue non sa mai dove
    e' arrivato ne' cosa gli manca.

COME SI DECIDE COSA ENTRA
    Due filtri, in quest'ordine:
      1. paese di origine TR
      2. e soprattutto: esiste su un servizio ITALIANO
    Il secondo filtro e' quello che conta. Se una serie e' distribuita in
    Italia, e' doppiata: da noi le serie turche si trasmettono doppiate,
    non sottotitolate. Se non la distribuisce nessuno, quasi sicuramente in
    italiano non esiste, e metterla nel catalogo sarebbe una presa in giro.
"""
import io
import json
import sys
import time
import urllib.parse
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1.5)
    return {}


def dove_in_italia(tid):
    d = get("https://api.themoviedb.org/3/tv/%d/watch/providers?api_key=%s" % (tid, K))
    it = (d.get("results") or {}).get("IT") or {}
    dove = []
    for chiave in ("flatrate", "free", "ads"):
        for p in it.get(chiave, []):
            dove.append(p["provider_name"])
    return sorted(set(dove))


def main():
    visti = {}
    # le piu' popolari, piu' una ricerca sui titoli italiani noti
    for pagina in (1, 2, 3, 4):
        d = get("https://api.themoviedb.org/3/discover/tv?api_key=%s"
                "&with_origin_country=TR&sort_by=popularity.desc&page=%d" % (K, pagina))
        for t in d.get("results", []):
            visti[t["id"]] = t

    # i titoli con cui sono passate in Italia: se una l'ha trasmessa Mediaset,
    # il nome italiano e' quello che l'utente conosce
    for nome in ("Terra amara", "Endless Love", "Daydreamer", "Love is in the air",
                 "My Home My Destiny", "Brave and Beautiful", "Segreti di famiglia",
                 "La ragazza e l'ufficiale", "Cherry Season", "Mr Wrong",
                 "Come sorelle", "Sadakat", "Hercai", "Infedele", "Viola come il mare"):
        d = get("https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s&language=it"
                % (K, urllib.parse.quote(nome)))
        for t in d.get("results", [])[:3]:
            if "TR" in (t.get("origin_country") or []):
                visti[t["id"]] = t

    righe = []
    for tid, t in visti.items():
        dove = dove_in_italia(tid)
        if not dove:
            continue
        det = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it" % (tid, K))
        righe.append({
            "id": tid,
            "nome": det.get("name") or t.get("name"),
            "originale": det.get("original_name") or "",
            "anno": (det.get("first_air_date") or "")[:4],
            "fine": (det.get("last_air_date") or "")[:4],
            "episodi": det.get("number_of_episodes") or 0,
            "stagioni": det.get("number_of_seasons") or 0,
            "voto": det.get("vote_average") or 0,
            "dove": dove,
        })
        time.sleep(0.15)

    righe.sort(key=lambda r: (-r["voto"], -r["episodi"]))
    print("SERIE TURCHE DISPONIBILI IN ITALIA: %d\n" % len(righe))
    print("%-40s %-9s %5s %4s  %s" % ("titolo italiano", "anni", "ep", "voto", "dove"))
    print("-" * 108)
    for r in righe:
        anni = r["anno"] + ("-" + r["fine"] if r["fine"] and r["fine"] != r["anno"] else "")
        print("%-40s %-9s %5d %4.1f  %s"
              % ((r["nome"] or "")[:40], anni, r["episodi"], r["voto"],
                 ", ".join(r["dove"])[:44]))
    io.open("turche.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(righe, ensure_ascii=False, indent=1))
    print("\n(dettagli in turche.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
