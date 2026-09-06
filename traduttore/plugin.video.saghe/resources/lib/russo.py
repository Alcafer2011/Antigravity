# -*- coding: utf-8 -*-
"""
RUSSO CON I CARTONI - imparare la lingua guardando la TV per bambini.

L'idea e' della compagna dell'utente ed e' buona: i cartoni per bambini
piccoli sono la cosa piu' vicina a un corso di lingua che esista in TV.
Parlano lentamente, ripetono, e quello che succede sullo schermo spiega le
parole senza bisogno di traduzione.

PERCHE' QUESTI CANALI E NON YOUTUBE
    Il primo tentativo e' stato YouTube: sul Raspberry non funziona senza
    configurare delle chiavi di accesso, e una sezione che non parte non serve
    a nessuno. Questi sono canali della lista IPTV gia' installata: vanno
    subito, trasmettono 24 ore su 24 e non chiedono niente.

QUELLI ELENCATI QUI SONO STATI PROVATI UNO PER UNO (05/09/2026).
    Su nove candidati ne rispondevano quattro: tutti quelli ospitati su un
    certo server erano morti, compresi Mult e STS Kids che sarebbero stati
    utili. Meglio quattro voci che funzionano che nove di cui cinque danno
    schermo nero.
    Se un giorno uno smette, non e' un guasto dell'add-on: i canali IPTV
    cambiano indirizzo di continuo. Si trovano gli altri nella lista TV.
"""

CANALI = [
    {
        "id": "karusel",
        "nome": "Карусель  (Carousel)",
        "url": "http://185.37.150.46/Karusel/index.m3u8",
        "livello": 1,
        "eta": "3-8 anni",
        "perche": "IL canale da cui cominciare. E' la televisione pubblica "
                  "russa per bambini: oltre ai cartoni ci sono programmi con "
                  "presentatori che parlano LENTAMENTE e scandiscono le "
                  "parole, fatti apposta per bambini che stanno imparando a "
                  "parlare. Se ne guardi uno solo, guarda questo.",
    },
    {
        "id": "mult_muzyka",
        "nome": "Мульт и музыка  (cartoni e canzoni)",
        "url": "http://hls127.freeott.top:8080/Mult_Muzika/video.m3u8",
        "livello": 1,
        "eta": "tutte",
        "perche": "Cartoni brevi e canzoni. Le canzoni servono in un modo "
                  "diverso dal parlato: restano in testa da sole, e con loro "
                  "restano le parole. Buono da tenere di sottofondo.",
    },
    {
        "id": "rutv_kids",
        "nome": "RU.TV Kids",
        "url": "https://rutvkids.ru/live/efir/index.m3u8",
        "livello": 2,
        "eta": "5-12 anni",
        "perche": "Canzoni per ragazzi con il testo che scorre sullo schermo. "
                  "Vedere le parole scritte mentre le senti e' il modo piu' "
                  "rapido per imparare a leggere il cirillico.",
    },
    {
        "id": "nickelodeon_ru",
        "nome": "Nickelodeon  (in russo)",
        "url": "http://stream.mcquack.net/443/index.m3u8",
        "livello": 3,
        "eta": "6-12 anni",
        "perche": "Cartoni moderni doppiati in russo. Qui si parla in fretta "
                  "e con frasi intere: e' il passo dopo, quando Карусель "
                  "comincia a sembrare facile. Se conosci gia' questi cartoni "
                  "in italiano e' anche piu' semplice seguirli.",
    },
]

LIVELLI = {
    1: "Si comincia da qui - parole poche e chiare",
    2: "Il passo dopo - parole anche scritte",
    3: "Quando i primi sembrano facili - si parla come in TV",
}

CONSIGLIO = (
    "[B]Come usarli davvero[/B]\n\n"
    "Non serve capire tutto: serve guardare spesso e poco. Venti minuti al "
    "giorno valgono piu' di tre ore la domenica.\n\n"
    "All'inizio guarda le immagini e lascia perdere le parole: il cervello "
    "aggancia da solo i suoni alle cose. Dopo qualche settimana comincerai a "
    "riconoscere le stesse parole che tornano sempre.\n\n"
    "I cartoni per i piu' piccoli non sono un ripiego: sono l'unica TV al "
    "mondo dove qualcuno parla apposta lentamente e ripete.\n\n"
    "[B]Se un canale non parte[/B]\n"
    "Non e' l'add-on: i canali IPTV cambiano indirizzo di continuo. Ne trovi "
    "altri nella lista TV, gruppo Russia."
)


def per_livello():
    """I canali raggruppati per difficolta', nell'ordine giusto."""
    fuori = []
    for liv in sorted(LIVELLI):
        canali = [c for c in CANALI if c["livello"] == liv]
        if canali:
            fuori.append((liv, LIVELLI[liv], canali))
    return fuori


def canale(cid):
    for c in CANALI:
        if c["id"] == cid:
            return c
    return None
