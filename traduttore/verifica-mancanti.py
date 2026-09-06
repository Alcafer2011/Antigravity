# -*- coding: utf-8 -*-
"""Controlla, uno per uno, i candidati da aggiungere al catalogo.

Il censimento generale sputa troppo rumore: podcast, parodie fatte dai fan,
serie omonime che non c'entrano niente (fra i risultati di One Piece e'
uscito perfino "Aqua Teen Hunger Force"). Qui invece si chiede a TMDb la
scheda ESATTA di ogni candidato scelto a mano, per sapere due cose che
contano davvero:

  - quanti episodi ha per davvero
  - se esiste in italiano

L'ULTIMA E' LA DOMANDA CHE CONTA DI PIU'. La regola di casa e': doppiaggio
italiano prima di tutto, poi i sottotitoli. Una serie senza doppiaggio si
aggiunge lo stesso, ma va DETTO, non scoperto davanti alla TV.
"""
import io
import json
import sys
import time
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"

# saga -> [(id TMDb, come la chiamiamo noi, perche' ci interessa)]
CANDIDATI = {
    "zodiaco": [
        (61389, "The Lost Canvas", "antefatto: la guerra precedente contro Ade"),
        (44317, "Saint Seiya Omega", "seguito diretto, generazione nuova"),
        (62428, "Soul of Gold", "cosa succede ai Gold dopo Ade"),
        (90855, "Knights of the Zodiac (Netflix)", "rifacimento in grafica 3D"),
        (78122, "Saintia Sho", "storia parallela"),
    ],
    "ken": [
        (68203, "Fist of the Blue Sky", "antefatto, lo zio di Ken"),
        (23436, "La leggenda di Raoul", "la stessa storia dal lato di Raoul"),
    ],
    "holly": [
        (24106, "Road to 2002", "il seguito: Holly in Europa"),
        (77240, "Captain Tsubasa 2018", "rifacimento moderno completo"),
        (63102, "Shin Captain Tsubasa", "gli OAV fra la prima e la seconda"),
    ],
    "gonagai": [
        (68586, "Devilman 1972", "l'altro grande Go Nagai"),
        (75208, "Devilman Crybaby", "rifacimento Netflix"),
        (17772, "Shin Jeeg", "il seguito di Jeeg"),
    ],
    "mazinga": [
        (232022, "Grendizer U", "il nuovo Goldrake"),
    ],
    "lupin": [
        (45860, "La donna chiamata Fujiko Mine", "la serie su Fujiko"),
    ],
    "gundam": [
        (46512, "0080 War in the Pocket", "Universal Century, dopo l'originale"),
        (72677, "0083 Stardust Memory", "Universal Century"),
        (25797, "Victory Gundam", "Universal Century, chiude la linea"),
        (45500, "Unicorn", "Universal Century, il piu' recente"),
        (21730, "Gundam Wing", "trasmesso in Italia"),
        (64375, "Iron-Blooded Orphans", "moderno, molto amato"),
        (196400, "The Witch from Mercury", "moderno, su Netflix"),
    ],
    "matsumoto": [
        (82182, "Queen Emeraldas", "stesso universo"),
        (45266, "Space Symphony Maetel", "seguito di Galaxy Express"),
        (13339, "Space Battleship Yamato", "l'altro caposaldo di Matsumoto"),
    ],
    "lamu": [
        (154524, "Lamu 2022", "rifacimento moderno"),
    ],
    "one_piece": [
        (111110, "One Piece dal vero (Netflix)", "adattamento con attori veri"),
    ],
}

# Altri titoli da cercare per nome, quando l'identificativo non lo so
DA_NOME = {
    "gundam": ["Mobile Suit Gundam: The 08th MS Team"],
    "lupin": ["Lupin the 3rd Part 4", "Lupin the 3rd Part 5", "Lupin the 3rd Part 6"],
    "ken": ["Souten no Ken Regenesis"],
}


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1.5)
    return {}


def italiano(tid):
    """C'e' un doppiaggio italiano? Si guarda dove la serie e' distribuita
    in Italia: se un servizio la offre qui, quasi sempre e' doppiata o
    almeno sottotitolata."""
    d = get("https://api.themoviedb.org/3/tv/%d/watch/providers?api_key=%s" % (tid, K))
    it = (d.get("results") or {}).get("IT") or {}
    dove = []
    for chiave in ("flatrate", "free", "ads"):
        for p in it.get(chiave, []):
            dove.append(p["provider_name"])
    return sorted(set(dove))


def scheda(tid):
    d = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it" % (tid, K))
    if not d.get("id"):
        return None
    return {
        "id": tid,
        "nome": d.get("name") or "",
        "originale": d.get("original_name") or "",
        "anno": (d.get("first_air_date") or "")[:4],
        "episodi": d.get("number_of_episodes") or 0,
        "stagioni": d.get("number_of_seasons") or 0,
        "dove": italiano(tid),
    }


def main():
    for saga in sorted(CANDIDATI):
        print("=" * 74)
        print("%s" % saga.upper())
        for tid, nostro, perche in CANDIDATI[saga]:
            s = scheda(tid)
            if not s:
                print("   %-34s NON TROVATO su TMDb (id %d)" % (nostro, tid))
                continue
            dove = ", ".join(s["dove"]) if s["dove"] else "nessun servizio in Italia"
            print("   %-34s %s  %4d ep  |  %s" % (nostro[:34], s["anno"], s["episodi"], dove))
            print("   %-34s   %s" % ("", perche))
        for nome in DA_NOME.get(saga, []):
            d = get("https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s"
                    % (K, urllib.parse.quote(nome)))
            r = (d.get("results") or [])[:1]
            if not r:
                print("   %-34s non trovato cercando per nome" % nome[:34])
                continue
            s = scheda(r[0]["id"])
            dove = ", ".join(s["dove"]) if s["dove"] else "nessun servizio in Italia"
            print("   %-34s %s  %4d ep  |  %s  (id=%d)"
                  % (nome[:34], s["anno"], s["episodi"], dove, s["id"]))
        print()
    return 0


import urllib.parse  # noqa: E402  (serve solo in DA_NOME)

if __name__ == "__main__":
    sys.exit(main())
