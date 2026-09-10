# -*- coding: utf-8 -*-
"""Verifica su TMDb i candidati anime POST anni Ottanta.

Stessa regola di [verifica-mancanti.py]: non si scrive niente nel catalogo
che non sia stato chiesto a TMDb. Conta il numero VERO di episodi e dice
se esiste il doppiaggio italiano, perche' una serie senza doppiaggio si
aggiunge lo stesso ma va DETTO, non scoperto davanti alla TV.
"""
import io
import json
import sys
import time
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# nome per la ricerca, anno atteso (per non prendere l'omonimo sbagliato)
CANDIDATI = [
    ("Yu Yu Hakusho", 1992), ("Slam Dunk", 1993),
    ("Neon Genesis Evangelion", 1995), ("Rurouni Kenshin", 1996),
    ("Detective Conan", 1996), ("Berserk", 1997), ("Pokemon", 1997),
    ("Cowboy Bebop", 1998), ("Trigun", 1998), ("Yu-Gi-Oh! Duel Monsters", 2000),
    ("Great Teacher Onizuka", 1999), ("Digimon Adventure", 1999),
    ("Hunter x Hunter", 1999), ("Hunter x Hunter", 2011),
    ("Inuyasha", 2000), ("InuYasha: The Final Act", 2009),
    ("Yashahime: Princess Half-Demon", 2020),
    ("Fullmetal Alchemist", 2003), ("Fullmetal Alchemist: Brotherhood", 2009),
    ("Bleach", 2004), ("Death Note", 2006), ("Code Geass", 2006),
    ("Fairy Tail", 2009), ("One Punch Man", 2015),
    ("JoJo's Bizarre Adventure", 2012), ("Attack on Titan", 2013),
    ("My Hero Academia", 2016), ("Black Clover", 2017),
    ("Demon Slayer: Kimetsu no Yaiba", 2019), ("Vinland Saga", 2019),
    ("Jujutsu Kaisen", 2020), ("Chainsaw Man", 2022),
    ("Sailor Moon", 1992), ("Shaman King", 2001), ("Shaman King", 2021),
    ("Soul Eater", 2008), ("Steins;Gate", 2011), ("Naruto Shippuden", 2007),
]


def get(u):
    for _ in range(3):
        try:
            r = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(r, timeout=25) as f:
                return json.loads(f.read().decode("utf-8"))
        except Exception as e:
            ultimo = e
            time.sleep(2)
    print("   !! %s" % ultimo)
    return {}


def cerca(nome, anno):
    q = urllib.parse.quote_plus(nome)
    d = get("https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s" % (K, q))
    migliore, scarto_min = None, 999
    for r in d.get("results", [])[:8]:
        data = r.get("first_air_date") or ""
        if len(data) < 4:
            continue
        scarto = abs(int(data[:4]) - anno)
        if scarto < scarto_min:
            migliore, scarto_min = r, scarto
    return migliore if scarto_min <= 2 else None


import urllib.parse

righe = []
for nome, anno in CANDIDATI:
    r = cerca(nome, anno)
    if not r:
        print("%-42s  NON TROVATA su TMDb" % nome)
        continue
    tid = r["id"]
    d = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it" % (tid, K))
    lingue = get("https://api.themoviedb.org/3/tv/%d/translations?api_key=%s" % (tid, K))
    ita = any(t.get("iso_639_1") == "it" for t in lingue.get("translations", []))
    stagioni = [(s.get("season_number"), s.get("episode_count"), (s.get("air_date") or "")[:4])
                for s in d.get("seasons", []) if s.get("season_number")]
    riga = {
        "nome": nome, "id": tid, "titolo_it": d.get("name"),
        "anno": (d.get("first_air_date") or "")[:4],
        "fine": (d.get("last_air_date") or "")[:4],
        "episodi": d.get("number_of_episodes"),
        "stagioni": stagioni, "scheda_it": ita,
        "trama": (d.get("overview") or "")[:200],
    }
    righe.append(riga)
    print("%-42s id=%-7d %s-%s  %4s ep  %d stag  scheda-it=%s"
          % (nome, tid, riga["anno"], riga["fine"], riga["episodi"],
             len(stagioni), "si" if ita else "NO"))

io.open("post80.json", "w", encoding="utf-8").write(
    json.dumps(righe, ensure_ascii=False, indent=1))
print("\nscritto post80.json (%d serie)" % len(righe))
