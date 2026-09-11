# -*- coding: utf-8 -*-
"""DOCUMENTARI, CUCINA, YOUTUBE: gli scaffali che non sono saghe.

PERCHE' ESISTE (chiesto il 07/09/2026)
    "sono appassionato di documentari, passavo le giornate intere a
    guardarli su Sky, su tutti i canali: animali, alieni, fisica, Monster
    Garage, Come e' fatto, Chernobyl... a mia moglie invece piace
    MasterChef e tutti quelli di cucina."
    E poi: "i documentari, qualsiasi tipo esistente, mettilo in elenco;
    stessa cosa per quelli da cucina" - e "tutte separate, anche dentro la
    sezione, per avere tutto ordinato".

LE TRE REGOLE DI QUESTO FILE
    1. PRIMA IL CATALOGO, POI LA DIRETTA. Detto dall'utente: "preferisco on
       demand che live - scelgo quello che voglio guardare io, come e
       quando". La diretta sta in fondo, come ripiego.
    2. TUTTO SEPARATO. Documentari, cucina e YouTube sono tre scaffali
       distinti, e dentro ognuno le voci stanno in gruppi con la loro
       intestazione. Niente calderoni.
    3. OGNI GENERE E' UNA VOCE. Non "cerca un documentario": sessanta
       generi gia' scritti, che col telecomando si aprono con un tasto.

COME SONO FATTI GLI INDIRIZZI (11/09/2026)
    Il catalogo di un canale si apre con la testa codificata come la scrive
    s4me (`_s4me`, vedi resources/lib/s4me_link.py): in chiaro funzionava, ma
    lasciava un errore nel registro a ogni apertura.
    La RICERCA non passa piu' da qui: `action=search` di un canale riapriva la
    tastiera invece di usare la parola gia' scritta. I generi li cerca
    ricerca_siti.py su tutti i cataloghi insieme (CANALI_CATALOGHI).

I CANALI DI YOUTUBE
    Si aprono con l'identificativo del canale, non col nome: col nome si
    finisce facilmente su un canale che gli somiglia. Presi il 07/09/2026.
"""



def _s4me(canale, azione="mainlist"):
    """plugin://plugin.video.s4me/?<testa codificata>. Scritto qui a mano, senza
    importare s4me_link, perche' fai-menu-arctic.py carica questo file da solo."""
    import base64
    import json
    from urllib.parse import quote
    testa = json.dumps({"action": azione, "channel": canale}, separators=(",", ":"), sort_keys=True)
    return "plugin://plugin.video.s4me/?" + quote(base64.b64encode(testa.encode("utf-8")).decode("ascii"), safe="")


YT_CANALE = "plugin://plugin.video.youtube/channel/%s/"
YT_CERCA = "plugin://plugin.video.youtube/kodion/search/query/?q=%s"

# I cataloghi su cui si prova ogni ricerca, in quest'ordine.
CATALOGHI_RICERCA = (("RaiPlay", "raiplay"),
                     ("Discovery+", "discoveryplus"),
                     ("La7", "la7"),
                     ("Pluto TV", "plutotv"),
                     ("Paramount", "paramount"),
                     ("Mediaset Infinity", "mediasetplay"))
CANALI_CATALOGHI = tuple(c for _nome, c in CATALOGHI_RICERCA)


# --------------------------------------------------------------------------
# DOCUMENTARI
# --------------------------------------------------------------------------

CATALOGHI_DOC = [
    ("RaiPlay", "raiplay",
     "Il piu' ricco di documentari in italiano, e gratuito: Rai Storia, "
     "Geo, Ulisse, le teche. Tutto a catalogo."),
    ("Discovery+", "discoveryplus",
     "Qui stanno 'Come e' fatto', i programmi di moto e motori, i lavori "
     "impossibili. E' il piu' vicino a quello che guardavi su Sky."),
    ("La7", "la7", "Le Teche La7: Atlantide e gli speciali di storia."),
    ("Pluto TV", "plutotv", "Gratuito, con intere categorie di documentari."),
    ("Paramount", "paramount", "Documentari e reportage."),
]

# Ogni genere e' una voce a se'. Raggruppati per argomento, cosi' si scorre
# con la freccia senza leggere tutto.
GENERI_DOC = [
    ("NATURA E ANIMALI", [
        ("Animali selvatici", "documentario animali selvatici"),
        ("Predatori", "documentario predatori leoni"),
        ("Oceani e mare", "documentario oceani"),
        ("Squali", "documentario squali"),
        ("Insetti", "documentario insetti"),
        ("Uccelli", "documentario uccelli"),
        ("Foreste e giungla", "documentario foresta amazzonia"),
        ("Deserti", "documentario deserto"),
        ("Poli e ghiacci", "documentario artico antartide"),
        ("Vulcani", "documentario vulcani"),
        ("Meteo estremo", "documentario uragani tornado"),
        ("Ambiente e clima", "documentario cambiamento climatico"),
    ]),
    ("SPAZIO E SCIENZA", [
        ("Universo e cosmo", "documentario universo"),
        ("Sistema solare e pianeti", "documentario sistema solare"),
        ("Buchi neri", "documentario buchi neri"),
        ("NASA e missioni spaziali", "documentario nasa missioni"),
        ("Sbarco sulla Luna", "documentario sbarco luna"),
        ("Marte", "documentario marte"),
        ("Fisica", "documentario fisica"),
        ("Fisica quantistica", "documentario fisica quantistica"),
        ("Matematica", "documentario matematica"),
        ("Einstein e i grandi scienziati", "documentario einstein"),
        ("Evoluzione", "documentario evoluzione darwin"),
        ("Genetica e DNA", "documentario dna genetica"),
        ("Cervello e mente", "documentario cervello"),
        ("Medicina e corpo umano", "documentario corpo umano"),
        ("Intelligenza artificiale", "documentario intelligenza artificiale"),
    ]),
    ("PREISTORIA E ARCHEOLOGIA", [
        ("Dinosauri", "documentario dinosauri"),
        ("Preistoria e uomo primitivo", "documentario preistoria"),
        ("Archeologia", "documentario archeologia"),
        ("Antico Egitto", "documentario antico egitto"),
        ("Piramidi", "documentario piramidi"),
        ("Antica Roma", "documentario antica roma"),
        ("Antica Grecia", "documentario antica grecia"),
        ("Maya, Inca e Aztechi", "documentario maya inca"),
        ("Vichinghi", "documentario vichinghi"),
        ("Samurai e Giappone antico", "documentario samurai"),
        ("Antica Cina", "documentario antica cina"),
    ]),
    ("STORIA", [
        ("Medioevo", "documentario medioevo"),
        ("Rinascimento", "documentario rinascimento"),
        ("Prima guerra mondiale", "documentario prima guerra mondiale"),
        ("Seconda guerra mondiale", "documentario seconda guerra mondiale"),
        ("Nazismo e Hitler", "documentario nazismo"),
        ("Olocausto", "documentario olocausto"),
        ("Guerra fredda", "documentario guerra fredda"),
        ("Vietnam", "documentario vietnam"),
        ("Storia d'Italia", "documentario storia italia"),
        ("Anni di piombo e terrorismo", "documentario anni di piombo"),
        ("Esplorazioni e scoperte", "documentario esplorazioni"),
    ]),
    # I PROGRAMMI, non i temi: sono quelli che l'utente guardava su Sky, a
    # nome e cognome. "tutti, non lasciarne nessuno".
    ("I PROGRAMMI DI DISCOVERY E SKY", [
        # Query = nome CANONICO del programma (spesso l'originale inglese):
        # TMDB li ha tutti, ma li indicizza col titolo con cui sono nati.
        ("Come e' fatto (How It's Made)", "How It's Made"),
        ("Come si fa (How Do They Do It?)", "How Do They Do It?"),
        ("Caccia all'oro (Gold Rush)", "Gold Rush"),
        ("Caccia all'oro: il fiume bianco", "Gold Rush: White Water"),
        ("La pesca piu' pericolosa (Deadliest Catch)", "Deadliest Catch"),
        ("Camionisti di ghiaccio (Ice Road Truckers)", "Ice Road Truckers"),
        ("Affari di famiglia (Pawn Stars)", "Pawn Stars"),
        ("Affari al buio (Storage Wars)", "Storage Wars"),
        ("Cash or Trash", "Cash or Trash"),
        ("Boscaioli (Ax Men)", "Ax Men"),
        ("Alaska: ultima frontiera", "Alaska: The Last Frontier"),
        ("Oro di Bering (Bering Sea Gold)", "Bering Sea Gold"),
        ("Il mistero di Oak Island", "The Curse of Oak Island"),
        ("Miti da sfatare (MythBusters)", "MythBusters"),
        ("Indagini ad alta quota (Air Crash Investigation)", "Air Crash Investigation"),
        ("Mega costruzioni (Build It Bigger)", "Build It Bigger"),
        ("Sopravvissuti (Man vs. Wild)", "Man vs. Wild"),
        ("Nudi e crudi (Naked and Afraid)", "Naked and Afraid"),
        ("Vado a vivere nel bosco (Alone)", "Alone"),
        ("Border Security", "Border Security: Australia's Front Line"),
        ("Cacciatori di fantasmi (Ghost Adventures)", "Ghost Adventures"),
        ("Antichi astronauti (Ancient Aliens)", "Ancient Aliens"),
        ("Ristoranti da incubo (Kitchen Nightmares)", "Kitchen Nightmares"),
        ("Cake Boss", "Cake Boss"),
        ("Sepolti in casa (Hoarders)", "Hoarders"),
        ("Dr. Pimple Popper", "Dr. Pimple Popper"),
        ("Vite al limite (My 600-lb Life)", "My 600-lb Life"),
    ]),
    # L'utente (10/09/2026): "Fast N' Loud e quello delle Harley dovrebbero
    # avere una loro sezione con le loro locandine". Prima stavano annegati
    # nei 40 programmi di Discovery, fra Cake Boss e Dr. Pimple Popper. Qui
    # sono programmi VERI (nome ufficiale + come li chiama l'utente), cosi'
    # TMDB trova il poster giusto.
    ("MOTORI, GARAGE E RESTAURI", [
        ("Fast N' Loud", "Fast N' Loud"),
        ("American Chopper (le moto Harley)", "American Chopper"),
        ("Orange County Choppers (American Chopper)", "American Chopper"),
        ("Monster Garage", "Monster Garage"),
        ("Overhaulin' - Nuova vita alle auto", "Overhaulin'"),
        ("Affari a quattro ruote (Wheeler Dealers)", "Wheeler Dealers"),
        ("Vegas Rat Rods", "Vegas Rat Rods"),
        ("Iron Resurrection", "Iron Resurrection"),
        ("Garage Squad", "Garage Squad"),
        ("Bitchin' Rides (Kindig Customs)", "Bitchin' Rides"),
        ("Roadkill", "Roadkill"),
        ("Chop Shop: Londra (car restoration)", "Chop Shop: London Garage"),
    ]),
    ("MOTORI E INGEGNERIA", [
        ("Harley Davidson e la sua storia", "Harley and the Davidsons"),
        ("Automobili e Formula 1 (Drive to Survive)", "Formula 1: Drive to Survive"),
        ("Aerei e aviazione", "documentario aerei aviazione"),
        ("Treni", "documentario treni"),
        ("Navi e transatlantici", "documentario navi"),
        ("Grandi costruzioni (Impossible Engineering)", "Impossible Engineering"),
        ("Ingegneria e ponti", "documentario ingegneria ponti"),
        ("Fabbriche e industria (Ultimate Factories)", "Ultimate Factories"),
        ("Tecnologia e informatica", "documentario tecnologia"),
    ]),
    ("DISASTRI E MISTERI", [
        ("Chernobyl", "chernobyl"),
        ("Titanic", "documentario titanic"),
        ("Disastri aerei", "documentario disastri aerei"),
        ("Catastrofi naturali", "documentario catastrofi"),
        ("Alieni e UFO", "documentario alieni ufo"),
        # "Antichi astronauti" sta gia' fra i programmi di Discovery: qui
        # sarebbe un doppione, e la prova sul banco lo prende.
        ("Misteri irrisolti", "documentario misteri"),
        ("Complotti", "documentario complotti"),
        ("Triangolo delle Bermuda", "documentario triangolo bermuda"),
    ]),
    ("CRONACA E CRIMINE", [
        ("Cronaca nera italiana", "documentario delitto italiano"),
        ("Serial killer", "documentario serial killer"),
        ("Mafia e Cosa Nostra", "documentario mafia"),
        ("Narcos e droga", "documentario narcotraffico"),
        ("Processi celebri", "documentario processo"),
        ("Carceri", "documentario carcere"),
        ("Rapine e truffe", "documentario rapina truffa"),
    ]),
    ("SOCIETA', ARTE E VIAGGI", [
        ("Viaggi e culture", "documentario viaggi"),
        ("Religioni", "documentario religione"),
        ("Economia e finanza", "documentario economia"),
        ("Politica", "documentario politica"),
        ("Musica e biografie", "documentario musica biografia"),
        ("Arte e pittura", "documentario arte"),
        ("Architettura", "documentario architettura"),
        ("Fotografia", "documentario fotografia"),
        ("Moda", "documentario moda"),
        ("Sport", "documentario sport"),
        ("Montagna ed Everest", "documentario everest montagna"),
        ("Subacquea", "documentario subacquea"),
        ("Sopravvivenza", "documentario sopravvivenza"),
    ]),
]

DIRETTE_DOC = [
    ("Pluto TV Documentari", "Pluto TV Documentari"),
]


# --------------------------------------------------------------------------
# CUCINA
# --------------------------------------------------------------------------

CATALOGHI_CUCINA = [
    ("Discovery+ (Real Time)", "discoveryplus",
     "Il canale dei programmi di cucina: Bake Off, Il boss delle torte, "
     "Cortesie per gli ospiti."),
    ("Mediaset Infinity", "mediasetplay",
     "Cotto e mangiato e i programmi Mediaset."),
    ("RaiPlay", "raiplay",
     "E' sempre mezzogiorno e i programmi di cucina Rai."),
]

GENERI_CUCINA = [
    ("I PROGRAMMI", [
        ("MasterChef Italia", "masterchef italia"),
        ("MasterChef (tutte le edizioni)", "masterchef"),
        ("Cucine da incubo", "cucine da incubo"),
        ("Hell's Kitchen", "hell's kitchen"),
        ("Bake Off Italia", "bake off italia"),
        ("Il boss delle torte", "boss delle torte"),
        ("4 Ristoranti", "4 ristoranti"),
        ("Alessandro Borghese", "alessandro borghese"),
        ("Cotto e mangiato", "cotto e mangiato"),
        ("E' sempre mezzogiorno", "sempre mezzogiorno"),
        ("La prova del cuoco", "prova del cuoco"),
        ("Cortesie per gli ospiti", "cortesie per gli ospiti"),
        ("Top Chef", "top chef"),
    ]),
    ("GLI CHEF", [
        ("Antonino Cannavacciuolo", "cannavacciuolo"),
        ("Bruno Barbieri", "bruno barbieri"),
        ("Benedetta Rossi", "benedetta rossi"),
        ("Iginio Massari", "iginio massari"),
        ("Gordon Ramsay", "gordon ramsay"),
        ("Carlo Cracco", "cracco"),
        ("Chef stellati", "chef stellati documentario"),
    ]),
    ("IMPARARE A CUCINARE", [
        ("Ricette facili", "ricette facili"),
        ("Ricette veloci", "ricette veloci"),
        ("Primi piatti", "ricette primi piatti"),
        ("Secondi di carne", "ricette secondi carne"),
        ("Pesce", "ricette pesce"),
        ("Pasta fatta in casa", "pasta fatta in casa"),
        ("Pane e lievitati", "pane fatto in casa lievitati"),
        ("Pizza", "pizza fatta in casa"),
        ("Dolci e torte", "ricette dolci torte"),
        ("Pasticceria", "pasticceria ricette"),
        ("Cioccolato", "cioccolato ricette"),
        ("Gelato", "gelato fatto in casa"),
        ("Conserve e marmellate", "conserve marmellate"),
    ]),
    ("CUCINE DEL MONDO", [
        ("Cucina italiana", "cucina italiana"),
        ("Cucina regionale italiana", "cucina regionale italiana"),
        ("Cucina giapponese e sushi", "cucina giapponese sushi"),
        ("Cucina cinese", "cucina cinese"),
        ("Cucina indiana", "cucina indiana"),
        ("Cucina francese", "cucina francese"),
        ("Cucina messicana", "cucina messicana"),
        ("Street food", "street food"),
        ("Barbecue e grigliate", "barbecue grigliate"),
    ]),
    ("PARTICOLARI", [
        ("Vegetariano e vegano", "ricette vegetariane vegane"),
        ("Senza glutine", "ricette senza glutine"),
        ("Cucina light", "ricette light"),
        ("Cucina molecolare", "cucina molecolare"),
        ("Vino e abbinamenti", "vino abbinamenti"),
        ("Cocktail", "cocktail ricette"),
    ]),
]

DIRETTE_CUCINA = [
    ("Gambero Rosso", "Gambero Rosso"),
]


# --------------------------------------------------------------------------
# YOUTUBE
# --------------------------------------------------------------------------

CANALI_YOUTUBE = [
    ("Elisa True Crime", "UCxH0MkY6v0sjZzmMgW9TSRQ",
     "Casi di cronaca raccontati per intero."),
    ("Omega Click", "UCLrgUeP56dUPUwp4vCy6RIQ",
     "Misteri, scienza e storie strane."),
]

# L'utente (10/09/2026): "i canali YouTube sono solo due, Elisa True Crime e
# Omega Click; adesso sono mischiati con documentari o episodi". Le ricerche
# generiche su YouTube stavano qui e sembravano altri canali: tolte. La
# sezione YouTube ora e' SOLO i due canali veri. Le ricerche a tema vivono
# gia' nei Documentari, dove ogni voce cerca anche su YouTube.
GENERI_YOUTUBE = []


# --------------------------------------------------------------------------

def _spiega(etichetta, cosa, dove):
    """Una descrizione VERA per ogni voce, non una riga vuota.

    L'utente, guardando la sezione a schermo: "mancano le informazioni".
    Aveva ragione: i generi non avevano nessuna descrizione, e nel pannello
    di sinistra restava un vuoto. Una riga che dice cosa succede premendo
    OK vale piu' di niente, e si scrive da sola dal nome del genere.
    """
    # La locandina puo' venire da TMDB in inglese, ma i cataloghi qui sotto
    # sono TUTTI italiani: RaiPlay, Discovery+/Real Time, Mediaset, La7 -
    # doppiaggio in italiano. Su YouTube la lingua cambia video per video.
    LINGUA = ("\n\n[Lingua] I cataloghi (RaiPlay, Discovery+, Mediaset, La7) "
              "sono italiani: audio in italiano. Se un programma esiste solo "
              "in originale, di norma parte coi sottotitoli italiani; se non "
              "ci sono, la voce lo dice quando apri.")
    if dove == "youtube":
        return ("Apre YouTube e cerca \"%s\".\n\nYouTube ha quasi tutto "
                "quello che i cataloghi non hanno, ma qualita' E lingua "
                "cambiano da un video all'altro: controlla prima di aprire."
                % cosa)
    if dove == "cucina":
        return ("Cerca \"%s\" nei cataloghi gratuiti (Real Time, Mediaset, "
                "RaiPlay) e su YouTube.\n\nOgni catalogo risponde per conto "
                "suo: se il primo non ha niente, prova il secondo." % cosa
                + LINGUA)
    return ("Cerca \"%s\" nei cataloghi gratuiti - RaiPlay, Discovery+, La7, "
            "Pluto TV, Paramount - e su YouTube.\n\nNon esiste un posto solo "
            "che li abbia tutti: si prova in ordine, ed e' per questo che la "
            "voce apre l'elenco dei cataloghi invece di una ricerca sola."
            % cosa + LINGUA)


def scaffale(quale):
    """Le voci di uno scaffale, in gruppi ordinati.

    Torna una lista di (intestazione, [(etichetta, indirizzo, nota, tipo)]).
    L'intestazione vuota vuol dire "nessun titolo sopra".
    """
    if quale == "documentari":
        fuori = [("A CATALOGO",
                  [(n, _s4me(c), nota, "catalogo") for n, c, nota in CATALOGHI_DOC])]
        for nome, generi in GENERI_DOC:
            fuori.append((nome, [(e, None, _spiega(e, q, "documentari"),
                                  "cerca:" + q) for e, q in generi]))
        fuori.append(("IN DIRETTA",
                      [(e, None, "Dalla tua lista TV.", "diretta:" + c)
                       for e, c in DIRETTE_DOC]))
        return fuori

    if quale == "cucina":
        fuori = [("A CATALOGO",
                  [(n, _s4me(c), nota, "catalogo") for n, c, nota in CATALOGHI_CUCINA])]
        for nome, generi in GENERI_CUCINA:
            fuori.append((nome, [(e, None, _spiega(e, q, "cucina"),
                                  "cerca:" + q) for e, q in generi]))
        fuori.append(("IN DIRETTA",
                      [(e, None, "Dalla tua lista TV.", "diretta:" + c)
                       for e, c in DIRETTE_CUCINA]))
        return fuori

    if quale == "youtube":
        fuori = [("I CANALI CHE SEGUI",
                  [(n, YT_CANALE % cid, nota, "youtube")
                   for n, cid, nota in CANALI_YOUTUBE])]
        for nome, generi in GENERI_YOUTUBE:
            fuori.append((nome, [(e, YT_CERCA % q.replace(" ", "+"),
                                  _spiega(e, q, "youtube"), "youtube")
                                 for e, q in generi]))
        return fuori

    return []


def quante_voci(quale):
    return sum(len(v) for _, v in scaffale(quale))


