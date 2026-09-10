# -*- coding: utf-8 -*-
"""Costruisce l'elenco dei FILM di ogni saga, dove ancora manca.

Sei saghe (Dragon Ball, Zodiaco, Ken, Holly, Mazinga) avevano gia' il loro
elenco; le altre no. Qui si fanno le mancanti, con lo stesso identico
formato, cosi' `elenco_film()` in main.py non cambia di una riga:

    [{"t": titolo, "d": anno, "p": trama, "i": locandina, "f": [fonti]}]

IL RUMORE E' IL PROBLEMA VERO, non la ricerca. Cercare "Bleach" su TMDb
restituisce candeggina, gruppi musicali e film americani. Quindi si tiene
una cosa solo se supera TRE controlli insieme:
  - e' un cartone animato (genere 16)
  - e' giapponese (lingua originale ja)
  - il nome della saga compare davvero nel titolo originale o inglese
Le saghe con una parola comune (Berserk, Trigun) restano comunque da
guardare a occhio: per questo il conteggio finale viene stampato.

Le FONTI non si indovinano: si chiede a TMDb chi ha davvero il film in
streaming IN ITALIA (`watch/providers`, regione IT), e si tengono solo i
servizi che questa casa conosce.

    python costruisci-film.py
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w500"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

QUI = os.path.dirname(os.path.abspath(__file__))
DESTINAZIONE = os.path.join(QUI, "plugin.video.saghe", "resources", "film")

# I nomi con cui TMDb conosce i servizi che abbiamo, e come li chiamiamo noi.
SERVIZI = {
    "Netflix": "netflix",
    "Netflix Standard with Ads": "netflix",
    "Amazon Prime Video": "prime",
    "Amazon Video": "prime",
    "Disney Plus": "disney",
    "Crunchyroll": "crunchyroll",
    "Mediaset Infinity": "infinity",
    "Timvision": "timvision",
    "TIMVISION": "timvision",
    "Pluto TV": "pluto",
}

# percorso -> parole con cui cercare. Piu' d'una quando la saga ha film
# usciti sotto nomi diversi (i robot di Go Nagai sono il caso peggiore).
# Un percorso con lista vuota e' un percorso per cui i film NON esistono, e
# lo si dice apposta invece di lasciare un buco.
RICERCHE = {
    "gonagai":       ["Mazinger", "Devilman", "Getter Robo", "Grendizer",
                      "Great Mazinger"],
    "lupin":         ["Lupin III", "Lupin the Third"],
    "naruto":        ["Naruto"],
    "naruto_veloce": ["Naruto"],
    "one_piece":     ["One Piece"],
    "gundam":        ["Mobile Suit Gundam"],
    "matsumoto":     ["Galaxy Express 999", "Captain Harlock", "Arcadia"],
    "lamu":          ["Urusei Yatsura", "Lamu"],
    "heroes":        [],   # anime promozionale: non ha film
    "m_yuyu":        ["Yu Yu Hakusho"],
    "m_slamdunk":    ["Slam Dunk"],
    "m_evangelion":  ["Evangelion"],
    "m_kenshin":     ["Rurouni Kenshin", "Kenshin"],
    "m_hxh":         ["Hunter x Hunter"],
    "m_hxh99":       ["Hunter x Hunter"],
    "m_inuyasha":    ["InuYasha"],
    "m_fma":         ["Fullmetal Alchemist"],
    "m_fma03":       ["Fullmetal Alchemist"],
    "m_bleach":      ["Bleach"],
    "m_deathnote":   ["Death Note"],
    "m_codegeass":   ["Code Geass"],
    "m_jojo":        ["JoJo"],
    "m_aot":         ["Attack on Titan", "Shingeki no Kyojin"],
    "m_mha":         ["My Hero Academia"],
    "m_blackclover": ["Black Clover"],
    "m_demonslayer": ["Demon Slayer", "Kimetsu no Yaiba"],
    "m_vinland":     [],
    "m_jjk":         ["Jujutsu Kaisen"],
    "m_opm":         [],
    "m_chainsaw":    ["Chainsaw Man"],
    "m_berserk":     ["Berserk"],
    "m_cowboy":      ["Cowboy Bebop"],
    "m_trigun":      ["Trigun"],
    "m_gto":         [],
    "m_souleater":   [],
    "m_shamanking":  [],
    "m_fairytail":   ["Fairy Tail"],
    "m_steinsgate":  ["Steins;Gate"],
    "m_digimon":     ["Digimon"],
    # Aggiunti il 07/09/2026 insieme alle loro serie. Sono i tre casi in cui
    # i film contano piu' che altrove: Pokemon ne fa uno all'anno, Doraemon
    # pure (in Giappone sono un appuntamento fisso), e i film di Yu-Gi-Oh
    # raccontano pezzi di storia che nelle serie non ci sono.
    "m_pokemon":      ["Pokemon", "Pokemon il film", "Pokemon the Movie"],
    "m_doraemon":     ["Doraemon"],
    "m_doraemon1979": ["Doraemon"],
    "m_yugioh":       ["Yu-Gi-Oh", "Yu-Gi-Oh! il film", "Yugioh"],
}


def get(percorso, **extra):
    par = {"api_key": K}
    par.update(extra)
    url = "%s%s?%s" % (BASE, percorso, urllib.parse.urlencode(par))
    for tentativo in range(4):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=25) as f:
                return json.loads(f.read().decode("utf-8"))
        except Exception:
            if tentativo == 3:
                return {}
            time.sleep(1.5 * (tentativo + 1))
    return {}


def _nudo(s):
    """Solo lettere e cifre, minuscole: 'Hunter x Hunter:' -> 'hunterxhunter'."""
    return "".join(c for c in (s or "").lower() if c.isalnum())


def _pertinente(film, parola, posizione):
    """Cartone animato + giapponese, poi il titolo O la pertinenza di TMDb.

    Il controllo sul titolo da solo NON basta e ci ha gia' fatto perdere dei
    film: 'Lamu' in originale si chiama 'Urusei Yatsura' e in italiano
    'Lamu - Only You', e il titolo originale su TMDb e' scritto in
    giapponese, quindi non combacia con niente. Percio' si accetta anche un
    risultato che TMDb mette FRA I PRIMI: se ha capito la domanda, la sua
    graduatoria vale piu' di un confronto di lettere.
    """
    if 16 not in (film.get("genre_ids") or []):
        return False
    if film.get("original_language") != "ja":
        return False
    p = _nudo(parola)
    if any(p in _nudo(film.get(c)) for c in ("original_title", "title")):
        return True
    return posizione < 5


def fonti_italiane(film_id):
    d = get("/movie/%d/watch/providers" % film_id)
    it = (d.get("results") or {}).get("IT") or {}
    fuori = []
    for tipo in ("flatrate", "free", "ads"):
        for p in it.get(tipo, []):
            nostro = SERVIZI.get(p.get("provider_name"))
            if nostro and nostro not in fuori:
                fuori.append(nostro)
    return fuori


def film_della_saga(parole):
    trovati = {}
    for parola in parole:
        # Cinque pagine e non due: con due, Pokemon dava tre film su
        # venticinque - i suoi escono uno all'anno da trent'anni.
        for pagina in (1, 2, 3, 4, 5):
            d = get("/search/movie", query=parola, language="it-IT",
                    page=pagina, include_adult="false")
            for posizione, f in enumerate(d.get("results", [])):
                if f["id"] in trovati:
                    continue
                if not _pertinente(f, parola, posizione if pagina == 1 else 99):
                    continue
                trovati[f["id"]] = f
            if pagina >= (d.get("total_pages") or 1):
                break
            time.sleep(0.2)
    return sorted(trovati.values(), key=lambda f: f.get("release_date") or "")


def main():
    if not os.path.isdir(DESTINAZIONE):
        print("manca %s" % DESTINAZIONE)
        return 1

    totale = 0
    for pid in sorted(RICERCHE):
        destinazione = os.path.join(DESTINAZIONE, pid + ".json")
        if os.path.exists(destinazione):
            print("  %-16s gia' fatto, non lo tocco" % pid)
            continue

        elenco = []
        for f in film_della_saga(RICERCHE[pid]):
            elenco.append({
                "t": (f.get("title") or f.get("original_title") or "").strip(),
                "d": (f.get("release_date") or "")[:4],
                "p": (f.get("overview") or "").strip(),
                "i": (IMG + f["poster_path"]) if f.get("poster_path") else "",
                "f": fonti_italiane(f["id"]),
            })
            time.sleep(0.15)

        with io.open(destinazione, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(elenco, ensure_ascii=False,
                                separators=(",", ":")))
        totale += len(elenco)
        con_fonte = sum(1 for m in elenco if m["f"])
        con_trama = sum(1 for m in elenco if m["p"])
        print("  %-16s %3d film   con fonte %3d   con trama %3d"
              % (pid, len(elenco), con_fonte, con_trama))

    print("\nTOTALE: %d film aggiunti" % totale)
    return 0


if __name__ == "__main__":
    sys.exit(main())
