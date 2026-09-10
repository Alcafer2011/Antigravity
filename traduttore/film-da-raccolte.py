# -*- coding: utf-8 -*-
"""Completa gli elenchi film usando le RACCOLTE di TMDb.

La ricerca normale trovava dieci film di Pokemon su venticinque: i titoli
sono tutti diversi ("Lucario e il mistero di Mew", "Il potere di tutti") e
la parola "Pokemon" non sempre c'e'. TMDb pero' li tiene raggruppati in una
RACCOLTA, e quella e' la lista completa fatta da loro.
"""
import io, json, os, time, urllib.parse, urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
IMG = "https://image.tmdb.org/t/p/w500"
UA = {"User-Agent": "Mozilla/5.0"}
DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "plugin.video.saghe", "resources", "film")
SERVIZI = {"Netflix": "netflix", "Amazon Prime Video": "prime",
           "Amazon Video": "prime", "Disney Plus": "disney",
           "Crunchyroll": "crunchyroll", "Mediaset Infinity": "infinity",
           "Timvision": "timvision", "TIMVISION": "timvision",
           "Pluto TV": "pluto"}

RACCOLTE = {
    "m_pokemon":      ["Pokemon", "Pokémon"],
    "m_yugioh":       ["Yu-Gi-Oh"],
    "m_doraemon":     ["Doraemon"],
    "m_doraemon1979": ["Doraemon"],
    "m_demonslayer":  ["Demon Slayer"],
    "m_evangelion":   ["Evangelion"],
    "m_jjk":          ["Jujutsu Kaisen"],
    "m_aot":          ["L'attacco dei giganti", "Attack on Titan"],
}


def get(u):
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=25) as f:
                return json.loads(f.read().decode())
        except Exception:
            time.sleep(2)
    return {}


def fonti(fid):
    d = get("https://api.themoviedb.org/3/movie/%d/watch/providers?api_key=%s" % (fid, K))
    it = (d.get("results") or {}).get("IT") or {}
    fuori = []
    for tipo in ("flatrate", "free", "ads"):
        for p in it.get(tipo, []):
            n = SERVIZI.get(p.get("provider_name"))
            if n and n not in fuori:
                fuori.append(n)
    return fuori


for pid, nomi in RACCOLTE.items():
    parti = {}
    for nome in nomi:
        d = get("https://api.themoviedb.org/3/search/collection?api_key=%s&query=%s&language=it-IT"
                % (K, urllib.parse.quote_plus(nome)))
        for r in d.get("results", [])[:3]:
            c = get("https://api.themoviedb.org/3/collection/%d?api_key=%s&language=it-IT"
                    % (r["id"], K))
            for f in c.get("parts", []):
                if f.get("original_language") == "ja":
                    parti[f["id"]] = f
    if not parti:
        print("  %-16s nessuna raccolta" % pid)
        continue

    destinazione = os.path.join(DEST, pid + ".json")
    vecchi = []
    if os.path.exists(destinazione):
        try:
            vecchi = json.load(io.open(destinazione, encoding="utf-8"))
        except Exception:
            vecchi = []
    gia = set(v.get("t", "") for v in vecchi)

    nuovi = 0
    for f in sorted(parti.values(), key=lambda x: x.get("release_date") or ""):
        titolo = (f.get("title") or f.get("original_title") or "").strip()
        if not titolo or titolo in gia:
            continue
        vecchi.append({
            "t": titolo,
            "d": (f.get("release_date") or "")[:4],
            "p": (f.get("overview") or "").strip(),
            "i": (IMG + f["poster_path"]) if f.get("poster_path") else "",
            "f": fonti(f["id"]),
        })
        gia.add(titolo)
        nuovi += 1
        time.sleep(0.15)

    vecchi.sort(key=lambda v: v.get("d") or "")
    io.open(destinazione, "w", encoding="utf-8").write(
        json.dumps(vecchi, ensure_ascii=False, separators=(",", ":")))
    print("  %-16s %3d film in tutto (%d nuovi dalla raccolta)"
          % (pid, len(vecchi), nuovi))
