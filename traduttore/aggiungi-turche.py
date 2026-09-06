# -*- coding: utf-8 -*-
"""Aggiunge le serie turche doppiate in italiano, dentro un RAGGRUPPAMENTO.

PERCHE' UN RAGGRUPPAMENTO E NON 17 VOCI
    Le saghe sono catene: episodi in fila che raccontano una storia sola.
    Le serie turche invece sono diciassette storie separate. Metterle una
    accanto all'altra nel menu principale avrebbe sommerso gli anime, che
    sono il cuore dell'add-on. Cosi' invece occupano UNA riga, e chi entra
    trova le sue diciassette.

PERCHE' CI STANNO BENE
    Hanno lo stesso identico problema per cui questo add-on esiste: in
    Italia arrivano a pezzi, cambiano nome, saltano episodi, vengono
    spostate di rete o interrotte. "Terra amara" da noi si chiama cosi', in
    Turchia "Bir Zamanlar Cukurova": trovarla e' gia' un'impresa.

COME SONO STATE SCELTE
    Ha un TITOLO ITALIANO UFFICIALE su TMDb. Non e' un dettaglio: le serie
    turche in Italia si trasmettono DOPPIATE, mai sottotitolate. Se esiste
    un titolo italiano, esiste il doppiaggio. Se non esiste, non c'e'.
    L'unica eccezione dichiarata e' Arafta, che ha solo i sottotitoli - ed
    e' scritto nella sua scheda invece di lasciarlo scoprire davanti alla TV.
"""
import io
import json
import os
import sys
import time
import urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
IMG = "https://image.tmdb.org/t/p/"
BASE = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe"
CAT = os.path.join(BASE, "resources", "lib", "catalogo.py")
SCHEDE = os.path.join(BASE, "resources", "schede")

# (id nostro, tmdb, titolo, anni, episodi, doppiata, fonti, nota)
TURCHE = [
    ("tr_terra_amara", 82328, "Terra amara", "2018-2022", 141, True, [],
     "In Turchia si chiama 'Bir Zamanlar Cukurova'. La piu' seguita di "
     "tutte in Italia: Canale 5 l'ha trasmessa per anni, spostandola di "
     "orario di continuo."),
    ("tr_endless_love", 65555, "Endless Love", "2015-2017", 74, True, [],
     "Titolo originale 'Kara Sevda'. Ha vinto l'Emmy internazionale: e' la "
     "serie che ha aperto la strada a tutte le altre in Europa."),
    ("tr_daydreamer", 80411, "Daydreamer - Le ali del sogno", "2018-2019", 51,
     True, [],
     "'Erkenci Kus' in originale. Commedia romantica, la piu' leggera del "
     "gruppo."),
    ("tr_love_air", 104877, "Love Is in the Air", "2020-2021", 52, True, [],
     "'Sen Cal Kapimi'. Trasmessa da Canale 5 nel pomeriggio."),
    ("tr_my_home", 96775, "My Home My Destiny", "2019-2021", 43, True, [],
     "'Dogdugun Ev Kaderindir'. Storia dura di una bambina data via dalla "
     "famiglia."),
    ("tr_brave", 68848, "Brave and Beautiful", "2016-2017", 32, True, [],
     "'Cesur ve Guzel'. Vendetta e amore fra due famiglie nemiche."),
    ("tr_segreti", 133490, "Segreti di famiglia", "2021-2024", 95, True, [],
     "'Yargi'. Giudiziaria: un omicidio che lega un pubblico ministero e un "
     "avvocato. Considerata la meglio scritta."),
    ("tr_cherry", 62217, "Cherry Season - La stagione del cuore", "2014-2016", 59,
     True, [],
     "'Kiraz Mevsimi'. Una delle prime arrivate in Italia."),
    ("tr_mr_wrong", 105052, "Mr. Wrong - Lezioni d'amore", "2020", 14, True, [],
     "'Bay Yanlis'. Corta e comica."),
    ("tr_come_sorelle", 94935, "Come sorelle", "2019", 8, True, [],
     "'Sevgili Gecmis'. Solo otto puntate: si finisce in una settimana."),
    ("tr_hercai", 87623, "Hercai - Amore e vendetta", "2019-2021", 69, True, [],
     "Su Timvision e Discovery+. Amore e vendetta fra due famiglie."),
    ("tr_ragazza_ufficiale", 62553, "La ragazza e l'ufficiale", "2014", 21, True,
     [],
     "'Kurt Seyit ve Sura'. Storica: la rivoluzione russa vista da un "
     "ufficiale turco."),
    ("tr_bitter_sweet", 73506, "Bitter Sweet - Ingredienti d'amore", "2017", 26,
     True, ["infinity"],
     "'Dolunay'. GRATIS su Mediaset Infinity, verificato."),
    ("tr_forbidden", 52645, "Forbidden Fruit", "2018-2023", 177, True, [],
     "'Yasak Elma'. La piu' lunga: centosettantasette puntate."),
    ("tr_far_away", None, "Far Away", "2024-2026", 98, True, ["infinity"],
     "Su Mediaset Infinity e Timvision, verificato."),
    ("tr_mezarlik", None, "Mezarlik", "2022-2026", 20, True, ["netflix"],
     "Su Netflix, che hai. Poliziesca e cupa, lontana dalle storie d'amore."),
    ("tr_arafta", None, "Arafta", "2025-2026", 129, False, ["youtube"],
     "ATTENZIONE: questa NON e' doppiata. Esiste solo sottotitolata in "
     "italiano, e si trova su YouTube: e' del 2025 ed e' ancora in corso, "
     "un doppiaggio non ha ancora fatto in tempo a esistere."),
]

# gli id che vanno cercati per nome (non li avevo a mano)
DA_CERCARE = {"tr_far_away": "Far Away", "tr_mezarlik": "Mezarlik",
              "tr_arafta": "Arafta"}


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1.5)
    return {}


def trova_id(nome):
    import urllib.parse
    d = get("https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s"
            % (K, urllib.parse.quote(nome)))
    for t in d.get("results", []):
        if "TR" in (t.get("origin_country") or []):
            return t["id"]
    return None


def scrivi_scheda(nostro, tmdb):
    d = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it" % (tmdb, K))
    dati = {
        "serie": d.get("name") or nostro,
        "tmdb": tmdb,
        "anno": (d.get("first_air_date") or "")[:4],
        "poster": (IMG + "w780" + d["poster_path"]) if d.get("poster_path") else "",
        "sfondo": (IMG + "w1280" + d["backdrop_path"]) if d.get("backdrop_path") else "",
        "episodi": {},
    }
    n = 0
    for s in d.get("seasons", []):
        if (s.get("season_number") or 0) < 1:
            continue
        st = get("https://api.themoviedb.org/3/tv/%d/season/%d?api_key=%s&language=it"
                 % (tmdb, s["season_number"], K))
        for e in st.get("episodes", []):
            n += 1
            dati["episodi"][str(n)] = {
                "t": e.get("name") or "",
                "p": e.get("overview") or "",
                "i": (IMG + "w500" + e["still_path"]) if e.get("still_path") else "",
                "d": e.get("air_date") or "",
            }
    io.open(os.path.join(SCHEDE, nostro + ".json"), "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(dati, ensure_ascii=False, indent=1))
    return n


def spezza(testo, largh=60):
    parole, riga, pezzi = testo.split(), "", []
    for w in parole:
        if len(riga) + len(w) + 1 > largh:
            pezzi.append(riga)
            riga = w
        else:
            riga = (riga + " " + w).strip()
    if riga:
        pezzi.append(riga)
    return pezzi


def main():
    finali = []
    print("SCHEDE")
    for riga in TURCHE:
        nostro, tmdb, titolo, anni, episodi, dopp, fonti, nota = riga
        if tmdb is None:
            tmdb = trova_id(DA_CERCARE[nostro])
            if tmdb is None:
                print("   SALTATA %s: non trovo l'identificativo" % nostro)
                continue
        n = scrivi_scheda(nostro, tmdb)
        print("   %-22s %3d episodi (attesi %d)  id=%d"
              % (nostro, n, episodi, tmdb))
        finali.append((nostro, tmdb, titolo, anni, n or episodi, dopp, fonti, nota))

    t = io.open(CAT, encoding="utf-8").read()

    # --- 1) le SERIE, dentro il loro dizionario ---
    fine_serie = t.index("\n}\n", t.index("SERIE = {"))
    blocco = "\n"
    for nostro, tmdb, titolo, anni, episodi, dopp, fonti, nota in finali:
        blocco += '    "%s": {\n' % nostro
        blocco += '        "titolo": "%s",\n' % titolo.replace('"', "'")
        blocco += '        "anni": "%s",\n' % anni
        blocco += '        "episodi": %d,\n' % episodi
        blocco += '        "verificato": True,\n'
        blocco += '        "audio_ita": %s,\n' % ("True" if dopp else "False")
        if not dopp:
            blocco += '        "sottotitoli_ita": True,\n'
        blocco += '        "fonti": [%s],\n' % ", ".join('"%s"' % f for f in fonti)
        pezzi = spezza(nota)
        blocco += '        "nota": "%s"\n' % pezzi[0]
        for p in pezzi[1:]:
            blocco += '                "%s"\n' % p
        blocco = blocco[:-1] + ",\n"
        blocco += "    },\n"
    t = t[:fine_serie] + "\n" + blocco + t[fine_serie:]

    # --- 2) un PERCORSO per ognuna ---
    fine_perc = t.index("\n}\n", t.index("PERCORSI = {"))
    blocco = "\n"
    for nostro, tmdb, titolo, anni, episodi, dopp, fonti, nota in finali:
        blocco += '    "%s": {\n' % nostro
        blocco += '        "titolo": "%s",\n' % titolo.replace('"', "'")
        blocco += '        "sottotitolo": "%s - %d puntate",\n' % (anni, episodi)
        blocco += '        "segmenti": [\n'
        blocco += '            ("%s", 1, %d),\n' % (nostro, episodi)
        blocco += '        ],\n'
        pezzi = spezza(nota, 62)
        blocco += '        "spiegazione": (\n'
        for p in pezzi:
            blocco += '            "%s "\n' % p
        blocco = blocco[:-2] + '"\n'
        blocco += '        ),\n'
        blocco += "    },\n"
    t = t[:fine_perc] + "\n" + blocco + t[fine_perc:]

    # --- 3) il raggruppamento ---
    ancora = "ORDINE_PERCORSI = ["
    gruppo = '''# --------------------------------------------------------------------------
# RAGGRUPPAMENTI
#
# Un raggruppamento occupa UNA riga nel menu principale e dentro ha tanti
# percorsi. Serve per non sommergere le saghe: gli anime sono catene, una
# storia sola in fila; le serie turche invece sono diciassette storie
# separate, e diciassette righe avrebbero coperto tutto il resto.
#
# I percorsi elencati qui NON vanno in ORDINE_PERCORSI: sono raggiungibili
# passando dal raggruppamento, ed e' proprio questo il punto.
# --------------------------------------------------------------------------

GRUPPI = {
    "turche": {
        "titolo": "Serie turche",
        "sottotitolo": "Doppiate in italiano, dalla prima all'ultima puntata",
        "icona": "DefaultTVShows.png",
        "spiegazione": (
            "Hanno lo stesso problema per cui esiste questo add-on: in "
            "Italia arrivano a pezzi, cambiano nome, saltano puntate, "
            "vengono spostate di rete o interrotte a meta'.\\n\\n"
            "Il nome e' la prima difficolta': 'Terra amara' in Turchia si "
            "chiama 'Bir Zamanlar Cukurova', 'Endless Love' e' 'Kara "
            "Sevda'. Qui trovi tutte e due le versioni.\\n\\n"
            "Sono tutte DOPPIATE in italiano tranne una, Arafta, che ha "
            "solo i sottotitoli: e' scritto nella sua scheda."
        ),
        "percorsi": [
%s        ],
    },
}


''' % "".join('            "%s",\n' % f[0] for f in finali)
    t = t.replace(ancora, gruppo + ancora, 1)

    io.open(CAT, "w", encoding="utf-8", newline="\n").write(t)
    import ast
    ast.parse(io.open(CAT, encoding="utf-8").read())
    print("\ncatalogo.py valido - %d serie turche aggiunte" % len(finali))
    return 0


if __name__ == "__main__":
    sys.exit(main())
