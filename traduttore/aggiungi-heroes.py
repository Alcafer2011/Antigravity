# -*- coding: utf-8 -*-
"""Aggiunge Super Dragon Ball Heroes al catalogo: serie, percorso, archi.

Scritto come file e non come comando: qui dentro ci sono apostrofi e
accenti, e passandoli dalla riga di comando si rovinano.
"""
import io

P = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe\resources\lib\catalogo.py"
t = io.open(P, encoding="utf-8").read()

CAMBI = []

# 1) la serie
CAMBI.append((
    '''    "dbs": {
        "titolo": "Dragon Ball Super",''',
    '''    "sdbh": {
        "titolo": "Super Dragon Ball Heroes",
        "anni": "2018-2023",
        "episodi": 54,
        "verificato": True,
        # NON esiste un doppiaggio italiano: si guarda sottotitolato.
        # Va detto, perche' la regola di casa e' italiano prima di tutto e
        # qui quella regola non si puo' rispettare.
        "audio_ita": False,
        "fonti": ["youtube"],
        "nota": "Anime promozionale, non fa parte della storia principale: "
                "e' un 'e se' dove i personaggi di tutte le epoche si "
                "scontrano fra loro, viaggi nel tempo compresi. Nasce per "
                "pubblicizzare un gioco di carte e uscito gratis in rete, "
                "episodi brevi. I gemelli Kamin e Oren, che si fondono in "
                "Kamioren, stanno nell'arco del conflitto universale.",
    },

    "dbs": {
        "titolo": "Dragon Ball Super",'''))

# 2) il percorso, subito dopo la via veloce
CAMBI.append((
    '''    "naruto": {
        "titolo": "Naruto",''',
    '''    "heroes": {
        "titolo": "Dragon Ball Heroes",
        "sottotitolo": "Il fuori-programma: tutte le epoche che si scontrano",
        "segmenti": [
            ("sdbh", 1, 54),
        ],
        "spiegazione": (
            "Sta FUORI dalla catena principale, ed e' voluto: non e' un "
            "seguito ne' un antefatto, e' un 'e se'. Goku incontra se stesso "
            "di altre epoche, i cattivi tornano dal passato, si viaggia nel "
            "tempo. Metterlo dentro Dragon Ball avrebbe rotto l'ordine "
            "cronologico che tiene in piedi tutto il resto.\\n\\n"
            "Nasce per pubblicizzare un gioco di carte ed e' uscito gratis "
            "in rete a episodi brevi: e' per questo che si trova su YouTube "
            "e non nei cataloghi degli abbonamenti.\\n\\n"
            "Attenzione: NON esiste un doppiaggio italiano. Questa e' "
            "l'unica saga del catalogo che si guarda per forza sottotitolata."
        ),
    },

    "naruto": {
        "titolo": "Naruto",'''))

# 3) i capitoli
CAMBI.append((
    '''    "naruto": [
        ("Il Paese delle Onde",''',
    '''    "heroes": [
        ("Arco del pianeta prigione",                  1,   6),
        ("Arco del conflitto universale",              7,  19),
        ("Arco della creazione dell'universo",        20,  30),
        ("Arco della nuova guerra spazio-temporale",  31,  38),
        ("Arco della missione ultra divina",          39,  48),
        ("Arco degli invasori demoniaci",             49,  54),
    ],

    "naruto": [
        ("Il Paese delle Onde",'''))

# 4) l'ordine del menu. Senza questo la saga NON SI VEDE.
CAMBI.append((
    '''    "naruto", "naruto_veloce",''',
    '''    "heroes",
    "naruto", "naruto_veloce",'''))

fatti = 0
for vecchio, nuovo in CAMBI:
    if vecchio not in t:
        print("  NON TROVATO: %s" % vecchio.strip().split("\n")[0][:60])
        continue
    t = t.replace(vecchio, nuovo, 1)
    fatti += 1

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("modifiche applicate: %d su %d" % (fatti, len(CAMBI)))
