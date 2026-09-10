# -*- coding: utf-8 -*-
"""Aggiunge al catalogo le saghe anime venute DOPO gli anni Ottanta.

Stesso criterio di quelle gia' presenti: non un elenco di titoli, ma
CATENE - l'ordine reale in cui vanno guardati gli episodi, con scritto
il perche' quando l'ordine non e' ovvio.

Tutti i conteggi vengono da TMDb, chiesti il 06/09/2026 con
[verifica-post80.py]; il risultato grezzo sta in post80.json.

Le nuove saghe finiscono in un RAGGRUPPAMENTO a parte, "moderne", per la
stessa ragione delle turche: il menu principale resta quello degli anni
Ottanta, che e' il cuore di questo add-on, e le altre stanno su uno
scaffale suo, chiaramente etichettato.
"""
import io
import shutil

CAT = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe\resources\lib\catalogo.py"

SERIE = '''
    # ======================================================================
    # DAGLI ANNI NOVANTA A OGGI
    # Conteggi chiesti a TMDb il 06/09/2026.
    # ======================================================================

    "yuyu": {
        "titolo": "Yu Yu Hakusho",
        "anni": "1992-1994",
        "episodi": 112,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix"],
        "nota": "In Italia si chiamava 'Yu degli spettri'. Stesso autore di "
                "Hunter x Hunter: comincia come storia di fantasmi e diventa "
                "un torneo di combattimento.",
    },
    "slamdunk": {
        "titolo": "Slam Dunk",
        "anni": "1993-1996",
        "episodi": 101,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "L'anime finisce a meta' del campionato nazionale: il fumetto "
                "va avanti, l'anime no. Non e' un taglio italiano, manca "
                "anche in Giappone.",
    },
    "evangelion": {
        "titolo": "Neon Genesis Evangelion",
        "anni": "1995-1996",
        "episodi": 26,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix"],
        "nota": "Ventisei episodi, ma il finale vero e' il film 'The End of "
                "Evangelion': gli ultimi due episodi della serie furono "
                "girati senza soldi e senza tempo.",
    },
    "kenshin": {
        "titolo": "Kenshin - Samurai vagabondo",
        "anni": "1996-1998",
        "episodi": 94,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Dall'episodio 63 in poi la storia se la inventa l'anime: il "
                "fumetto prosegue altrove. La parte migliore, Kyoto, sta fra "
                "il 28 e il 62.",
    },
    "berserk": {
        "titolo": "Berserk",
        "anni": "1997-1998",
        "episodi": 25,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Racconta un solo arco, l'Eta' dell'Oro, e finisce di colpo "
                "senza concluderlo. Non e' un guasto: e' cosi'.",
    },
    "cowboy": {
        "titolo": "Cowboy Bebop",
        "anni": "1998-1999",
        "episodi": 26,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix"],
        "nota": "Ogni episodio si regge da solo, ma la storia di Spike va in "
                "ordine: dal 5 in poi conviene non saltare.",
    },
    "trigun": {
        "titolo": "Trigun",
        "anni": "1998",
        "episodi": 26,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Western fantascientifico. Il rifacimento del 2023 "
                "('Stampede') racconta la stessa storia in modo diverso e non "
                "e' un seguito.",
    },
    "gto": {
        "titolo": "GTO - Great Teacher Onizuka",
        "anni": "1999-2000",
        "episodi": 43,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "In Italia arrivo' su MTV, quasi integrale.",
    },
    "hxh99": {
        "titolo": "Hunter x Hunter (1999)",
        "anni": "1999-2001",
        "episodi": 62,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "La prima versione. Si ferma a meta' storia e prosegue solo "
                "in tre OVA. Piu' cupa e piu' lenta di quella del 2011.",
    },
    "hxh": {
        "titolo": "Hunter x Hunter (2011)",
        "anni": "2011-2014",
        "episodi": 148,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["crunchyroll"],
        "nota": "Rifacimento completo che riparte da zero e arriva molto piu' "
                "avanti, fino alle Formiche Chimera. E' la versione da "
                "guardare se se ne guarda una sola.",
    },
    "inuyasha": {
        "titolo": "Inuyasha",
        "anni": "2000-2010",
        "episodi": 193,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Gli episodi 1-167 sono la serie originale; dal 168 al 193 e' "
                "'The Final Act', girata nove anni dopo per dare alla storia "
                "il finale che le mancava.",
    },
    "yashahime": {
        "titolo": "Yashahime",
        "anni": "2020-2022",
        "episodi": 48,
        "verificato": True,
        "audio_ita": False,
        "sottotitoli_ita": True,
        "fonti": ["crunchyroll"],
        "nota": "Il seguito: protagoniste le figlie. ATTENZIONE, questa non "
                "e' doppiata in italiano, ci sono solo i sottotitoli.",
    },
    "fma03": {
        "titolo": "Fullmetal Alchemist (2003)",
        "anni": "2003-2004",
        "episodi": 51,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Fino all'episodio 25 circa segue il fumetto; poi il fumetto "
                "non era ancora finito e l'anime si inventa un finale tutto "
                "suo, molto diverso.",
    },
    "fmab": {
        "titolo": "Fullmetal Alchemist: Brotherhood",
        "anni": "2009-2010",
        "episodi": 64,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix", "prime"],
        "nota": "Non e' un seguito: e' la STESSA storia rifatta da capo, "
                "questa volta fedele al fumetto e conclusa davvero.",
    },
    "bleach": {
        "titolo": "Bleach",
        "anni": "2004-2012",
        "episodi": 366,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Finisce senza concludere: l'ultimo arco del fumetto resto' "
                "fuori per dieci anni.",
    },
    "bleach_tybw": {
        "titolo": "Bleach: Thousand-Year Blood War",
        "anni": "2022-2026",
        "episodi": 50,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["disney"],
        "nota": "Il finale mancante, ripreso nel 2022 esattamente dove la "
                "serie si era fermata. Ancora in corso.",
    },
    "deathnote": {
        "titolo": "Death Note",
        "anni": "2006-2007",
        "episodi": 37,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix"],
        "nota": "Trentasette episodi, nessun riempitivo, un finale vero.",
    },
    "codegeass": {
        "titolo": "Code Geass",
        "anni": "2006-2008",
        "episodi": 50,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Due stagioni da 25, di seguito: 'Lelouch of the Rebellion' e "
                "'R2'.",
    },
    "fairytail": {
        "titolo": "Fairy Tail",
        "anni": "2009-2019",
        "episodi": 328,
        "verificato": True,
        "audio_ita": True,
        "sottotitoli_ita": True,
        "fonti": [],
        "nota": "ATTENZIONE: il doppiaggio italiano copre solo la prima parte "
                "(circa i primi 175 episodi). Da li' in avanti esistono solo "
                "i sottotitoli.",
    },
    "opm": {
        "titolo": "One Punch Man",
        "anni": "2015-2025",
        "episodi": 36,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["prime"],
        "nota": "Tre stagioni da 12. La prima e' fatta da uno studio diverso "
                "e si vede: e' la piu' bella da guardare.",
    },
    "jojo": {
        "titolo": "Le bizzarre avventure di JoJo",
        "anni": "2012-2026",
        "episodi": 202,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix", "prime"],
        "nota": "Ogni parte cambia protagonista, epoca e paese, ma sono la "
                "stessa famiglia: vanno in ordine, dal nonno al nipote.",
    },
    "aot": {
        "titolo": "L'attacco dei giganti",
        "anni": "2013-2023",
        "episodi": 87,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["prime", "crunchyroll"],
        "nota": "Le quattro stagioni contate da TMDb sono 87 episodi; il "
                "finale del 2023-2024 e' uscito come due film-speciale e non "
                "e' compreso in questo conteggio.",
    },
    "mha": {
        "titolo": "My Hero Academia",
        "anni": "2016-2025",
        "episodi": 170,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["crunchyroll", "prime"],
        "nota": "Otto stagioni, conclusa nel 2025.",
    },
    "blackclover": {
        "titolo": "Black Clover",
        "anni": "2017-2021",
        "episodi": 170,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix", "crunchyroll"],
        "nota": "Si ferma all'episodio 170 e prosegue in un film su Netflix.",
    },
    "demonslayer": {
        "titolo": "Demon Slayer",
        "anni": "2019-2024",
        "episodi": 63,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix", "prime", "crunchyroll"],
        "nota": "Gli episodi 27-33 sono il 'Treno Mugen', uscito prima al "
                "cinema come film: in questa catena stanno al loro posto "
                "nella storia, fra la prima e la seconda stagione.",
    },
    "vinland": {
        "titolo": "Vinland Saga",
        "anni": "2019-2023",
        "episodi": 48,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix", "prime"],
        "nota": "Vichinghi, storico. La seconda stagione cambia completamente "
                "tono rispetto alla prima: e' voluto.",
    },
    "jjk": {
        "titolo": "Jujutsu Kaisen",
        "anni": "2020-2026",
        "episodi": 59,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["crunchyroll", "netflix"],
        "nota": "Il film 'Jujutsu Kaisen 0' e' un antefatto, ma va guardato "
                "DOPO la prima stagione: se lo si guarda prima si rovina una "
                "sorpresa.",
    },
    "chainsaw": {
        "titolo": "Chainsaw Man",
        "anni": "2022",
        "episodi": 12,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["crunchyroll", "prime"],
        "nota": "Dodici episodi, poi la storia prosegue al cinema.",
    },
    "shamanking01": {
        "titolo": "Shaman King (2001)",
        "anni": "2001-2002",
        "episodi": 64,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "La versione che passo' in Italia. Il finale se lo inventa: "
                "il fumetto non era finito.",
    },
    "shamanking21": {
        "titolo": "Shaman King (2021)",
        "anni": "2021-2022",
        "episodi": 52,
        "verificato": True,
        "audio_ita": True,
        "fonti": ["netflix"],
        "nota": "Rifacimento completo e fedele, con il finale vero. Non e' un "
                "seguito: ricomincia da capo.",
    },
    "souleater": {
        "titolo": "Soul Eater",
        "anni": "2008-2009",
        "episodi": 51,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Dall'episodio 36 circa si stacca dal fumetto e chiude a modo "
                "suo.",
    },
    "steinsgate": {
        "titolo": "Steins;Gate",
        "anni": "2011",
        "episodi": 24,
        "verificato": True,
        "audio_ita": False,
        "sottotitoli_ita": True,
        "fonti": ["crunchyroll"],
        "nota": "ATTENZIONE: non e' doppiata in italiano, solo sottotitoli. "
                "Viaggi nel tempo; i primi episodi sono lenti apposta.",
    },
    "digimon": {
        "titolo": "Digimon Adventure",
        "anni": "1999-2001",
        "episodi": 104,
        "verificato": True,
        "audio_ita": True,
        "fonti": [],
        "nota": "Episodi 1-54 la prima serie, 55-104 'Digimon Adventure 02', "
                "il seguito diretto con gli stessi ragazzi tre anni dopo.",
    },
'''

PERCORSI = '''
    # ======================================================================
    # DAGLI ANNI NOVANTA A OGGI - raggruppamento "moderne"
    # ======================================================================

    "m_yuyu": {
        "titolo": "Yu Yu Hakusho",
        "sottotitolo": "Yu degli spettri, tutti e 112 gli episodi",
        "segmenti": [("yuyu", 1, 112)],
        "spiegazione": (
            "In Italia usci' come 'Yu degli spettri'. E' dello stesso autore "
            "di Hunter x Hunter e si vede: comincia come storia di fantasmi e "
            "finisce come torneo di combattimento."
        ),
    },
    "m_slamdunk": {
        "titolo": "Slam Dunk",
        "sottotitolo": "La serie completa",
        "segmenti": [("slamdunk", 1, 101)],
        "spiegazione": (
            "Non aspettarti la finale: l'anime si ferma a meta' del "
            "campionato nazionale e non riprende. Non e' un taglio italiano, "
            "manca anche in Giappone. Il fumetto invece finisce."
        ),
    },
    "m_evangelion": {
        "titolo": "Evangelion",
        "sottotitolo": "La serie del 1995",
        "segmenti": [("evangelion", 1, 26)],
        "spiegazione": (
            "Ventisei episodi. Gli ultimi due furono girati senza piu' soldi "
            "ne' tempo e non concludono niente: il finale vero e' il film "
            "'The End of Evangelion'. I film non stanno ancora in questa "
            "catena."
        ),
    },
    "m_kenshin": {
        "titolo": "Kenshin - Samurai vagabondo",
        "sottotitolo": "La serie originale",
        "segmenti": [("kenshin", 1, 94)],
        "spiegazione": (
            "La parte che conta e' Kyoto, dall'episodio 28 al 62. Dal 63 in "
            "poi il fumetto era finito e l'anime va avanti inventando: molti "
            "si fermano li'."
        ),
    },
    "m_hxh": {
        "titolo": "Hunter x Hunter",
        "sottotitolo": "La versione del 2011, quella completa",
        "segmenti": [("hxh", 1, 148)],
        "spiegazione": (
            "Esistono due versioni della stessa storia, come Dragon Ball Z e "
            "Kai. Questa del 2011 riparte da zero e arriva molto piu' avanti: "
            "centoquarantotto episodi fino alle Formiche Chimera. Se se ne "
            "guarda una sola, e' questa."
        ),
    },
    "m_hxh99": {
        "titolo": "Hunter x Hunter - via del 1999",
        "sottotitolo": "La prima versione, piu' cupa e incompiuta",
        "segmenti": [("hxh99", 1, 62)],
        "spiegazione": (
            "La versione originale: piu' lenta, piu' cupa, con musiche "
            "diverse. Si ferma pero' a meta' storia e prosegue solo in tre "
            "OVA difficili da trovare. Le due vie hanno progressi separati: "
            "puoi tenerle tutte e due."
        ),
    },
    "m_inuyasha": {
        "titolo": "Inuyasha",
        "sottotitolo": "La serie, il finale girato nove anni dopo, e il seguito",
        "segmenti": [
            ("inuyasha",  1, 193),
            ("yashahime", 1,  48),
        ],
        "spiegazione": (
            "Gli episodi 1-167 sono la serie del 2000, che finisce senza "
            "finale. Dal 168 al 193 e' 'The Final Act', girata nel 2009 "
            "apposta per concluderla: qui e' di fila, come va guardata. Dopo "
            "viene Yashahime, il seguito con le figlie - ma quello NON e' "
            "doppiato in italiano, solo sottotitoli."
        ),
    },
    "m_fma": {
        "titolo": "Fullmetal Alchemist",
        "sottotitolo": "Brotherhood: la storia intera, fedele al fumetto",
        "segmenti": [("fmab", 1, 64)],
        "spiegazione": (
            "Attenzione al tranello: esistono due Fullmetal Alchemist e non "
            "sono uno il seguito dell'altro. Questa del 2009 e' la storia "
            "completa, fedele al fumetto e conclusa. E' quella da guardare "
            "per prima."
        ),
    },
    "m_fma03": {
        "titolo": "Fullmetal Alchemist - via del 2003",
        "sottotitolo": "La prima versione, con un finale tutto suo",
        "segmenti": [("fma03", 1, 51)],
        "spiegazione": (
            "Fino all'episodio 25 circa e' la stessa storia; poi il fumetto "
            "non era ancora finito e l'anime prosegue inventandosi un finale "
            "completamente diverso. Vale la pena, ma DOPO Brotherhood: "
            "guardata per prima confonde e basta."
        ),
    },
    "m_bleach": {
        "titolo": "Bleach",
        "sottotitolo": "La serie e il finale ripreso dieci anni dopo",
        "segmenti": [
            ("bleach",      1, 366),
            ("bleach_tybw", 1,  50),
        ],
        "spiegazione": (
            "Bleach si fermo' nel 2012 all'episodio 366 lasciando fuori "
            "l'ultimo arco del fumetto. Nel 2022 l'hanno ripreso esattamente "
            "da li': 'Thousand-Year Blood War' e' la continuazione diretta, "
            "non un rifacimento. Qui i due pezzi sono uno dietro l'altro."
        ),
    },
    "m_deathnote": {
        "titolo": "Death Note",
        "sottotitolo": "Trentasette episodi, nessun riempitivo",
        "segmenti": [("deathnote", 1, 37)],
        "spiegazione": (
            "Una delle poche serie di questo elenco che non ha un solo "
            "episodio di riempimento e finisce dove doveva finire."
        ),
    },
    "m_codegeass": {
        "titolo": "Code Geass",
        "sottotitolo": "Le due stagioni, di fila",
        "segmenti": [("codegeass", 1, 50)],
        "spiegazione": (
            "Venticinque episodi piu' venticinque: 'Lelouch of the Rebellion' "
            "e 'R2' sono una storia sola, spezzata solo dalla messa in onda."
        ),
    },
    "m_jojo": {
        "titolo": "Le bizzarre avventure di JoJo",
        "sottotitolo": "Tutte le parti, dal nonno al nipote",
        "segmenti": [("jojo", 1, 202)],
        "spiegazione": (
            "Ogni parte cambia protagonista, epoca e continente - Inghilterra "
            "1880, Giappone 1938, il viaggio in Egitto, l'Italia del 2001 - "
            "ma sono tutti la stessa famiglia, in ordine di generazione. "
            "Vanno guardate in ordine: e' l'unica serie qui dentro dove "
            "saltare una parte rende la successiva incomprensibile."
        ),
    },
    "m_aot": {
        "titolo": "L'attacco dei giganti",
        "sottotitolo": "Le quattro stagioni in ordine",
        "segmenti": [("aot", 1, 87)],
        "spiegazione": (
            "Ottantasette episodi. Il finale, uscito nel 2023-2024, non e' un "
            "episodio ma due film-speciale: non e' in questo conteggio."
        ),
    },
    "m_mha": {
        "titolo": "My Hero Academia",
        "sottotitolo": "Dalla prima all'ottava stagione",
        "segmenti": [("mha", 1, 170)],
        "spiegazione": (
            "Centosettanta episodi, conclusa nel 2025."
        ),
    },
    "m_blackclover": {
        "titolo": "Black Clover",
        "sottotitolo": "La serie televisiva",
        "segmenti": [("blackclover", 1, 170)],
        "spiegazione": (
            "Si ferma all'episodio 170 e prosegue in un film. I primi venti "
            "episodi sono i piu' lenti: chi li supera di solito arriva in "
            "fondo."
        ),
    },
    "m_demonslayer": {
        "titolo": "Demon Slayer",
        "sottotitolo": "Con il Treno Mugen al posto giusto",
        "segmenti": [("demonslayer", 1, 63)],
        "spiegazione": (
            "Qui c'e' il caso che questo add-on esiste per risolvere: il "
            "'Treno Mugen' usci' al cinema come film, e chi guarda solo le "
            "stagioni televisive salta un pezzo di storia. Nella catena sta "
            "al suo posto, agli episodi 27-33, fra la prima e la seconda "
            "stagione."
        ),
    },
    "m_vinland": {
        "titolo": "Vinland Saga",
        "sottotitolo": "Le due stagioni",
        "segmenti": [("vinland", 1, 48)],
        "spiegazione": (
            "Vichinghi, storico, adulto. La seconda stagione cambia "
            "completamente tono rispetto alla prima: non e' un calo, e' "
            "voluto e va superato."
        ),
    },
    "m_jjk": {
        "titolo": "Jujutsu Kaisen",
        "sottotitolo": "La serie in ordine di visione",
        "segmenti": [("jjk", 1, 59)],
        "spiegazione": (
            "Il film 'Jujutsu Kaisen 0' racconta fatti PRECEDENTI, ma va "
            "guardato DOPO la prima stagione: messo prima rovina una "
            "sorpresa. Anche l'inizio della seconda stagione e' un antefatto, "
            "ed e' voluto."
        ),
    },
    "m_opm": {
        "titolo": "One Punch Man",
        "sottotitolo": "Tre stagioni da dodici",
        "segmenti": [("opm", 1, 36)],
        "spiegazione": (
            "La prima stagione e' fatta da uno studio diverso dalle altre due "
            "e la differenza di disegno si vede parecchio."
        ),
    },
    "m_chainsaw": {
        "titolo": "Chainsaw Man",
        "sottotitolo": "La prima stagione",
        "segmenti": [("chainsaw", 1, 12)],
        "spiegazione": (
            "Dodici episodi, poi la storia prosegue al cinema."
        ),
    },
    "m_berserk": {
        "titolo": "Berserk",
        "sottotitolo": "La serie del 1997",
        "segmenti": [("berserk", 1, 25)],
        "spiegazione": (
            "Racconta un solo arco, l'Eta' dell'Oro, e si interrompe di colpo "
            "senza concluderlo. Va saputo prima di cominciare."
        ),
    },
    "m_cowboy": {
        "titolo": "Cowboy Bebop",
        "sottotitolo": "Ventisei episodi",
        "segmenti": [("cowboy", 1, 26)],
        "spiegazione": (
            "Quasi ogni episodio si regge da solo, ma la storia di Spike va "
            "in ordine: dal quinto in poi conviene non saltare."
        ),
    },
    "m_trigun": {
        "titolo": "Trigun",
        "sottotitolo": "La serie del 1998",
        "segmenti": [("trigun", 1, 26)],
        "spiegazione": (
            "Western fantascientifico. Il 'Trigun Stampede' del 2023 non e' "
            "un seguito: e' la stessa storia raccontata daccapo in modo molto "
            "diverso."
        ),
    },
    "m_gto": {
        "titolo": "GTO",
        "sottotitolo": "Great Teacher Onizuka",
        "segmenti": [("gto", 1, 43)],
        "spiegazione": (
            "In Italia arrivo' su MTV quasi integrale, che per l'epoca era "
            "un'eccezione."
        ),
    },
    "m_souleater": {
        "titolo": "Soul Eater",
        "sottotitolo": "La serie completa",
        "segmenti": [("souleater", 1, 51)],
        "spiegazione": (
            "Dall'episodio 36 circa si stacca dal fumetto e chiude a modo "
            "suo, perche' il fumetto non era finito."
        ),
    },
    "m_shamanking": {
        "titolo": "Shaman King",
        "sottotitolo": "Le due versioni: quella vista in Italia e quella vera",
        "segmenti": [
            ("shamanking01", 1, 64),
            ("shamanking21", 1, 52),
        ],
        "spiegazione": (
            "La versione del 2001 e' quella passata in Italia, e il finale se "
            "lo inventa perche' il fumetto non era ancora finito. Quella del "
            "2021 NON e' un seguito: ricomincia da capo ed e' fedele, col "
            "finale vero. Sono di fila perche' cosi' si vede la differenza, "
            "ma se hai fretta guarda solo la seconda."
        ),
    },
    "m_fairytail": {
        "titolo": "Fairy Tail",
        "sottotitolo": "Tutte e otto le stagioni in un filo solo",
        "segmenti": [("fairytail", 1, 328)],
        "spiegazione": (
            "Trecentoventotto episodi divisi in otto stagioni con nomi "
            "diversi, che e' esattamente il motivo per cui esiste questo "
            "add-on: qui sono un elenco unico numerato da 1 a 328. "
            "ATTENZIONE: il doppiaggio italiano copre circa i primi 175 "
            "episodi. Da li' in poi ci sono solo i sottotitoli."
        ),
    },
    "m_steinsgate": {
        "titolo": "Steins;Gate",
        "sottotitolo": "Ventiquattro episodi - solo sottotitoli",
        "segmenti": [("steinsgate", 1, 24)],
        "spiegazione": (
            "ATTENZIONE: non esiste doppiaggio italiano, solo i sottotitoli. "
            "I primi episodi sono lenti apposta: quello che sembra tempo "
            "perso serve tutto dalla meta' in poi."
        ),
    },
    "m_digimon": {
        "titolo": "Digimon",
        "sottotitolo": "Adventure e Adventure 02, di fila",
        "segmenti": [("digimon", 1, 104)],
        "spiegazione": (
            "Gli episodi 1-54 sono 'Digimon Adventure', dal 55 al 104 e' "
            "'Adventure 02', il seguito diretto con gli stessi ragazzi tre "
            "anni dopo."
        ),
    },
'''

GRUPPO = '''    "moderne": {
        "titolo": "Dagli anni Novanta a oggi",
        "sottotitolo": "Le saghe venute dopo, con lo stesso criterio",
        "icona": "DefaultTVShows.png",
        "spiegazione": (
            "Il menu principale e' quello degli anni Ottanta: e' il cuore di "
            "questo add-on e resta com'e'. Qui dentro ci sono le saghe "
            "arrivate dopo, trattate esattamente allo stesso modo - non un "
            "elenco di titoli, ma l'ordine reale in cui gli episodi vanno "
            "guardati, con scritto il perche' quando l'ordine non e' ovvio. "
            "I casi che contano di piu': DEMON SLAYER, dove il 'Treno Mugen' "
            "era un film e chi guarda solo le stagioni salta un pezzo di "
            "storia; BLEACH, che si fermo' nel 2012 e riprese nel 2022; "
            "INUYASHA, il cui finale fu girato nove anni dopo; FULLMETAL "
            "ALCHEMIST e HUNTER x HUNTER, che esistono in due versioni della "
            "stessa storia come Dragon Ball Z e Kai - qui sono due vie "
            "separate, con progressi separati. "
            "Tre non sono doppiate in italiano e c'e' scritto nella loro "
            "scheda: Yashahime, Steins;Gate e la seconda meta' di Fairy Tail."
        ),
        "percorsi": [
            "m_demonslayer", "m_aot", "m_jojo", "m_hxh", "m_hxh99",
            "m_fma", "m_fma03", "m_bleach", "m_inuyasha", "m_mha",
            "m_jjk", "m_vinland", "m_deathnote", "m_codegeass",
            "m_evangelion", "m_cowboy", "m_berserk", "m_trigun",
            "m_kenshin", "m_yuyu", "m_slamdunk", "m_gto",
            "m_fairytail", "m_blackclover", "m_opm", "m_souleater",
            "m_shamanking", "m_steinsgate", "m_chainsaw", "m_digimon",
        ],
    },
'''


def main():
    testo = io.open(CAT, encoding="utf-8").read()
    shutil.copy(CAT, CAT + ".prima-post80")

    if '"m_demonslayer"' in testo:
        print("gia' fatto: le saghe moderne sono gia' nel catalogo")
        return

    righe = testo.split("\n")

    # I confini dei dizionari: le righe che chiudono a colonna 0.
    # 0 FONTI, 1 SERIE, 2 TAGLI, 3 PERCORSI, 4 GRUPPI, 5 ARCHI
    chiusure = [i for i, r in enumerate(righe) if r == "}"]
    fine_serie, fine_percorsi, fine_gruppi = chiusure[1], chiusure[3], chiusure[4]

    # Controllo che stia mettendo la roba dove crede di metterla: e' gia'
    # successo di innestare una serie nel dizionario sbagliato.
    def apertura_piu_vicina(i):
        for j in range(i, -1, -1):
            r = righe[j]
            if r.endswith(" = {") and not r.startswith(" "):
                return r.split(" ")[0]
        return "?"

    for indice, atteso in ((fine_serie, "SERIE"),
                           (fine_percorsi, "PERCORSI"),
                           (fine_gruppi, "GRUPPI")):
        trovato = apertura_piu_vicina(indice)
        assert trovato == atteso, \
            "la riga %d chiude %s, non %s" % (indice + 1, trovato, atteso)

    # Dal fondo verso l'alto, cosi' gli indici restano validi.
    righe[fine_gruppi:fine_gruppi] = GRUPPO.rstrip("\n").split("\n")
    righe[fine_percorsi:fine_percorsi] = PERCORSI.rstrip("\n").split("\n")
    righe[fine_serie:fine_serie] = SERIE.rstrip("\n").split("\n")

    fuori = "\n".join(righe)
    fuori = fuori.replace('ORDINE_GRUPPI = ["turche"]',
                          'ORDINE_GRUPPI = ["moderne", "turche"]')
    assert '"moderne", "turche"' in fuori, "ORDINE_GRUPPI non aggiornato"

    io.open(CAT, "w", encoding="utf-8").write(fuori)
    print("catalogo aggiornato (copia di sicurezza: catalogo.py.prima-post80)")


main()
