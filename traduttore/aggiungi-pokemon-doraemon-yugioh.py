# -*- coding: utf-8 -*-
"""Aggiunge Pokemon, Doraemon e Yu-Gi-Oh al catalogo, coi loro film.

Chiesto il 07/09/2026. Conteggi chiesti a TMDb lo stesso giorno.

DUE SCELTE DA SPIEGARE

1. DORAEMON HA DUE SERIE, e non sono la stessa cosa: quella del 1979
   (1836 episodi) e quella del 2005 (1464). In Italia si e' vista soprattutto
   la seconda. Sono due vie separate, come Dragon Ball Z e Kai: chi vuole
   l'originale lo trova, ma la via principale e' quella del 2005.

2. YU-GI-OH E' UNA CATENA VERA. Duel Monsters, GX, 5D's, Zexal, Arc-V e
   VRAINS raccontano generazioni diverse nello stesso mondo, in ordine:
   972 episodi di fila. E' esattamente il caso per cui questo add-on esiste.

3. POKEMON e' una serie sola lunghissima (1235 episodi su 25 stagioni):
   niente da rimettere in ordine, ma va nel catalogo perche' i film si
   incastrano fra le stagioni ed e' li' che serve una mano.
"""
import io
import shutil

CAT = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe\resources\lib\catalogo.py"

SERIE = '''
    # ---- Pokemon, Doraemon, Yu-Gi-Oh (aggiunti il 07/09/2026) ----

    "pokemon": {
        "titolo": "Pokemon",
        "anni": "1997-2023",
        "episodi": 1235,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix", "prime"],
        "nota": "Venticinque stagioni. La storia di Ash finisce con la "
                "stagione 25: da li' in poi i protagonisti cambiano.",
    },
    "doraemon2005": {
        "titolo": "Doraemon",
        "anni": "2005-2026",
        "episodi": 1464,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "La versione moderna, quella passata in Italia su Boing. "
                "Ancora in corso in Giappone.",
    },
    "doraemon1979": {
        "titolo": "Doraemon (1979)",
        "anni": "1979-2005",
        "episodi": 1836,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "La serie storica, milleottocento episodi in ventisei anni. "
                "In Italia se n'e' vista solo una parte.",
    },
    "yugioh_dm": {
        "titolo": "Yu-Gi-Oh! Duel Monsters",
        "anni": "2000-2004",
        "episodi": 224,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Quella con Yugi: e' da qui che comincia tutto.",
    },
    "yugioh_gx": {
        "titolo": "Yu-Gi-Oh! GX",
        "anni": "2004-2008",
        "episodi": 180,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Una generazione dopo, nella scuola dei duellanti.",
    },
    "yugioh_5ds": {
        "titolo": "Yu-Gi-Oh! 5D's",
        "anni": "2008-2011",
        "episodi": 154,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "I duelli in moto.",
    },
    "yugioh_zexal": {
        "titolo": "Yu-Gi-Oh! Zexal",
        "anni": "2011-2014",
        "episodi": 146,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "",
    },
    "yugioh_arcv": {
        "titolo": "Yu-Gi-Oh! Arc-V",
        "anni": "2014-2017",
        "episodi": 148,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "",
    },
    "yugioh_vrains": {
        "titolo": "Yu-Gi-Oh! VRAINS",
        "anni": "2017-2019",
        "episodi": 120,
        "verificato": True,
        "audio_ita": False,
        "sottotitoli_ita": True,
        "fonti": [],
        "nota": "ATTENZIONE: in italiano non e' mai arrivata; ci sono solo "
                "i sottotitoli.",
    },
'''

PERCORSI = '''
    "m_pokemon": {
        "titolo": "Pokemon",
        "sottotitolo": "Venticinque stagioni, di fila",
        "segmenti": [("pokemon", 1, 1235)],
        "spiegazione": (
            "Milleduecentotrentacinque episodi numerati da 1 a 1235: le "
            "stagioni hanno tutte un nome diverso e trovare il punto in cui "
            "si era arrivati e' sempre stato il problema. Qui e' un elenco "
            "solo.\\n\\nI film escono ogni anno e si incastrano fra le "
            "stagioni: li trovi nel reparto 'I film delle saghe'."
        ),
    },
    "m_doraemon": {
        "titolo": "Doraemon",
        "sottotitolo": "La serie del 2005, quella vista in Italia",
        "segmenti": [("doraemon2005", 1, 1464)],
        "spiegazione": (
            "Esistono due Doraemon e non sono la stessa cosa: questa del "
            "2005 e' quella passata in Italia su Boing, ed e' ancora in "
            "corso in Giappone. L'altra, del 1979, e' una via separata."
        ),
    },
    "m_doraemon1979": {
        "titolo": "Doraemon - la serie del 1979",
        "sottotitolo": "L'originale: 1836 episodi in ventisei anni",
        "segmenti": [("doraemon1979", 1, 1836)],
        "spiegazione": (
            "La serie storica. In Italia se n'e' vista solo una parte, e "
            "molti episodi non sono mai stati doppiati. Via separata da "
            "quella del 2005: i progressi non si disturbano."
        ),
    },
    "m_yugioh": {
        "titolo": "Yu-Gi-Oh!",
        "sottotitolo": "Tutte le generazioni in ordine, 972 episodi",
        "segmenti": [
            ("yugioh_dm",     1, 224),
            ("yugioh_gx",     1, 180),
            ("yugioh_5ds",    1, 154),
            ("yugioh_zexal",  1, 146),
            ("yugioh_arcv",   1, 148),
            ("yugioh_vrains", 1, 120),
        ],
        "spiegazione": (
            "Non sono sei serie diverse: sono sei generazioni dello stesso "
            "mondo, una dopo l'altra. Duel Monsters e' quella di Yugi; GX "
            "sta nella scuola dei duellanti; in 5D's si duella in moto; poi "
            "Zexal, Arc-V e VRAINS.\\n\\nATTENZIONE: VRAINS in italiano non "
            "e' mai arrivata, ha solo i sottotitoli - e' scritto anche "
            "nell'elenco degli episodi."
        ),
    },
'''


def main():
    testo = io.open(CAT, encoding="utf-8").read()
    if '"m_yugioh"' in testo:
        print("gia' fatto")
        return
    shutil.copy(CAT, CAT + ".prima-pokemon")

    righe = testo.split("\n")
    chiusure = [i for i, r in enumerate(righe) if r == "}"]
    fine_serie, fine_percorsi = chiusure[1], chiusure[3]

    def apertura(i):
        for j in range(i, -1, -1):
            if righe[j].endswith(" = {") and not righe[j].startswith(" "):
                return righe[j].split(" ")[0]
        return "?"

    assert apertura(fine_serie) == "SERIE", apertura(fine_serie)
    assert apertura(fine_percorsi) == "PERCORSI", apertura(fine_percorsi)

    righe[fine_percorsi:fine_percorsi] = PERCORSI.rstrip("\n").split("\n")
    righe[fine_serie:fine_serie] = SERIE.rstrip("\n").split("\n")

    fuori = "\n".join(righe)
    # nel raggruppamento delle moderne, subito dopo le altre lunghe
    vecchio = '"m_fairytail", "m_blackclover", "m_opm", "m_souleater",'
    nuovo = ('"m_fairytail", "m_blackclover", "m_opm", "m_souleater",\n'
             '            "m_pokemon", "m_doraemon", "m_doraemon1979",\n'
             '            "m_yugioh",')
    assert vecchio in fuori
    fuori = fuori.replace(vecchio, nuovo, 1)

    io.open(CAT, "w", encoding="utf-8", newline="\n").write(fuori)
    print("aggiunte: Pokemon, Doraemon (2005 e 1979), Yu-Gi-Oh (6 serie)")


main()
