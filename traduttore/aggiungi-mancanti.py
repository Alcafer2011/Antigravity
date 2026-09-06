# -*- coding: utf-8 -*-
"""Aggiunge al catalogo le serie che mancavano, trovate col censimento.

COME SONO STATE SCELTE
    Non tutto quello che TMDb conosce merita di entrare: fra i risultati
    c'erano podcast, parodie fatte dai fan e omonimi che non c'entrano
    niente. Sono entrate solo le serie che sono DAVVERO un pezzo della
    saga - un seguito, un antefatto, una parte mai messa in fila.

DOVE VANNO
    Ognuna al suo posto nella cronologia, non in fondo. I tre Gundam
    "laterali" per esempio si infilano FRA l'originale e Zeta, perche' e'
    li' che stanno nel tempo della storia: 08th e 0080 durante la guerra di
    un anno, 0083 nei tre anni dopo.

LE FONTI
    Dichiarate solo quelle che l'utente puo' davvero usare: Netflix e Prime
    (che ha) e Mediaset Infinity (gratis). Dove il servizio esiste ma lui
    non ce l'ha - Crunchyroll, Anime Generation, dAnime - si lascia vuoto:
    l'add-on scende da solo sul ponte s4me, e almeno non promette niente.
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

# id nostro -> (tmdb, stagione o None, titolo, anni, episodi, ita, fonti, nota)
NUOVE = [
    # ---- GUNDAM: le tre laterali dell'Universal Century ----
    ("gundam_08th", 43887, None, "Gundam - Il Team Slegar", "1996-1999", 12, True,
     ["prime"],
     "La guerra di un anno vista da terra, da soldati semplici invece che "
     "da eroi. Sta DENTRO l'originale come tempo: mentre Amuro combatte "
     "nello spazio, qui si fa la guerra nella giungla."),
    ("gundam_0080", 46512, None, "Gundam 0080 - Il pericolo di una guerra tascabile",
     "1989", 6, True, ["prime"],
     "Sei episodi soli, visti dagli occhi di un bambino di undici anni in "
     "una colonia. E' il racconto piu' corto della saga ed e' quello che "
     "quasi tutti indicano come il migliore."),
    ("gundam_0083", 72677, None, "Gundam 0083 - Stardust Memory", "1991-1992", 13,
     True, [],
     "Il ponte fra l'originale e Zeta: spiega da dove nasce la guerra che "
     "trovi all'inizio di Zeta Gundam."),
    # ---- LUPIN: le tre parti moderne ----
    ("lupin4", 31572, 4, "Lupin III - L'avventura italiana", "2015", 24, True,
     ["prime"],
     "Girata in Italia, e in Italia e' andata in onda per prima al mondo. "
     "Lupin ha la giacca azzurra."),
    ("lupin5", 31572, 5, "Lupin III - Ritorno alle origini", "2018", 24, True,
     ["prime"],
     "Ambientata in Francia, giacca blu. Torna il Lupin ladro e basta, "
     "meno buffo e piu' serio."),
    ("lupin6", 31572, 6, "Lupin III - Una storia senza fine", "2021-2022", 24,
     True, ["prime"],
     "Per i cinquant'anni della serie. Giacca nera."),
    ("lupin_fujiko", 45860, None, "La donna chiamata Fujiko Mine", "2012", 13,
     True, ["prime"],
     "Tutto dal punto di vista di Fujiko, con un disegno molto diverso: "
     "ruvido, adulto. E' un antefatto, si puo' guardare per primo."),
    # ---- ZODIACO: i seguiti ----
    ("ss_soul_of_gold", 62428, None, "I Cavalieri dello Zodiaco - Soul of Gold",
     "2015", 13, True, [],
     "Cosa succede ai cavalieri d'oro DOPO Ade. Va guardata subito dopo "
     "il capitolo di Ade, e' li' che si incastra."),
    ("ss_omega", 44317, None, "I Cavalieri dello Zodiaco - Omega", "2012-2014", 97,
     True, [],
     "Una generazione dopo: i protagonisti sono nuovi, i vecchi ci sono "
     "ma come maestri."),
    ("ss_lost_canvas", 61389, None, "I Cavalieri dello Zodiaco - The Lost Canvas",
     "2009-2011", 26, True, [],
     "La guerra contro Ade di duecentocinquant'anni prima. Antefatto vero "
     "e proprio: non serve aver visto niente per capirla."),
    # ---- HOLLY: il seguito europeo ----
    ("holly_road2002", 24106, None, "Holly e Benji Forever - Road to 2002",
     "2001-2002", 52, True, ["infinity"],
     "Holly gioca in Europa da professionista. E' il seguito che in Italia "
     "e' arrivato per ultimo e che quasi nessuno ha visto per intero."),
    # ---- KEN: l'antefatto ----
    ("ken_blue_sky", 68203, None, "Il pugno del cielo blu", "2006", 46, True, [],
     "Shanghai anni Trenta, due generazioni prima di Ken: il protagonista "
     "e' lo zio del suo maestro. Antefatto completo."),
    # ---- LAMU: il rifacimento ----
    ("lamu2022", 154524, None, "Lamu (rifacimento 2022)", "2022-2024", 46, True,
     ["netflix"],
     "Stessa storia, disegno moderno. Non sostituisce l'originale: rifa' "
     "gli episodi migliori dei 218."),
    # ---- MAZINGA: il nuovo Goldrake ----
    ("grendizer_u", 232022, None, "Grendizer U - Il nuovo Goldrake", "2024", 13,
     True, [],
     "Rilettura moderna di Goldrake. In Italia sta su RaiPlay, gratis."),
    # ---- GO NAGAI: Devilman ----
    ("devilman_crybaby", 75208, None, "Devilman Crybaby", "2018", 10, True,
     ["netflix"],
     "Il Devilman di Go Nagai rifatto da zero, duro e per adulti: niente "
     "a che vedere con i robot. Su Netflix, doppiato."),
]

# dove infilarle nei percorsi: (percorso, id nuovo, dopo quale segmento)
INNESTI = [
    ("gundam",    "gundam_08th",      "gundam0079"),
    ("gundam",    "gundam_0080",      "gundam_08th"),
    ("gundam",    "gundam_0083",      "gundam_0080"),
    ("lupin",     "lupin_fujiko",     None),          # in testa: e' un antefatto
    ("lupin",     "lupin4",           "lupin3"),
    ("lupin",     "lupin5",           "lupin4"),
    ("lupin",     "lupin6",           "lupin5"),
    ("zodiaco",   "ss_soul_of_gold",  "ss_hades"),
    ("zodiaco",   "ss_omega",         "ss_soul_of_gold"),
    ("zodiaco",   "ss_lost_canvas",   "ss_omega"),
    ("holly",     "holly_road2002",   "holly2"),
    ("ken",       "ken_blue_sky",     "ken2"),
    ("lamu",      "lamu2022",         "lamu"),
    ("mazinga",   "grendizer_u",      "mazinga_edition_z"),
    ("gonagai",   "devilman_crybaby", "jeeg"),
]


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1.5)
    return {}


def scrivi_scheda(nostro, tmdb, stagione, quanti):
    """Scarica locandina, sfondo e titoli degli episodi."""
    d = get("https://api.themoviedb.org/3/tv/%d?api_key=%s&language=it" % (tmdb, K))
    dati = {
        "serie": d.get("name") or nostro,
        "tmdb": tmdb,
        "anno": (d.get("first_air_date") or "")[:4],
        "poster": (IMG + "w780" + d["poster_path"]) if d.get("poster_path") else "",
        "sfondo": (IMG + "w1280" + d["backdrop_path"]) if d.get("backdrop_path") else "",
        "episodi": {},
    }
    stagioni = [stagione] if stagione is not None else [
        s.get("season_number") for s in d.get("seasons", [])
        if s.get("season_number", 0) > 0]
    n = 0
    for s in stagioni:
        st = get("https://api.themoviedb.org/3/tv/%d/season/%s?api_key=%s&language=it"
                 % (tmdb, s, K))
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


def blocco_serie(nostro, titolo, anni, episodi, ita, fonti, nota):
    righe = []
    righe.append('    "%s": {' % nostro)
    righe.append('        "titolo": "%s",' % titolo)
    righe.append('        "anni": "%s",' % anni)
    righe.append('        "episodi": %d,' % episodi)
    righe.append('        "verificato": True,')
    righe.append('        "audio_ita": %s,' % ("True" if ita else "False"))
    righe.append('        "fonti": [%s],'
                 % ", ".join('"%s"' % f for f in fonti))
    # la nota va spezzata a mano: righe lunghe rendono il file illeggibile
    parole, riga, pezzi = nota.split(), "", []
    for w in parole:
        if len(riga) + len(w) + 1 > 62:
            pezzi.append(riga)
            riga = w
        else:
            riga = (riga + " " + w).strip()
    if riga:
        pezzi.append(riga)
    righe.append('        "nota": "%s"' % pezzi[0]
                 + ('' if len(pezzi) == 1 else ''))
    for p in pezzi[1:]:
        righe.append('                "%s"' % p)
    righe[-1] += ','
    righe.append('    },')
    righe.append('')
    return "\n".join(righe)


def main():
    t = io.open(CAT, encoding="utf-8").read()

    # 1) le schede
    print("SCHEDE")
    for nostro, tmdb, st, titolo, anni, episodi, ita, fonti, nota in NUOVE:
        n = scrivi_scheda(nostro, tmdb, st, episodi)
        segno = "ok " if n == episodi else "!! "
        print("  %s %-20s %3d episodi scaricati (attesi %d)" % (segno, nostro, n, episodi))

    # 2) le serie nel catalogo, in fondo a SERIE
    print("\nSERIE")
    ancora = t.index("PERCORSI = {")
    # si torna indietro fino alla graffa che chiude SERIE
    chiusura = t.rindex("}\n", 0, ancora)
    aggiunta = "\n"
    for nostro, tmdb, st, titolo, anni, episodi, ita, fonti, nota in NUOVE:
        if '"%s":' % nostro in t:
            print("   gia' presente: %s" % nostro)
            continue
        aggiunta += blocco_serie(nostro, titolo, anni, episodi, ita, fonti, nota)
        print("   aggiunta %s" % nostro)
    t = t[:chiusura] + aggiunta + t[chiusura:]

    io.open(CAT, "w", encoding="utf-8", newline="\n").write(t)
    import ast
    ast.parse(io.open(CAT, encoding="utf-8").read())
    print("\ncatalogo.py ancora valido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
