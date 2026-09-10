# -*- coding: utf-8 -*-
"""DISEGNA UNA TESSERA COL NOME SCRITTO SOPRA per le voci senza locandina.

PERCHE'
    39 voci su 409 non hanno una locandina, e non e' un difetto da riparare:
    "Lievitati", "Barbecue", "Predatori" sono RICERCHE A TEMA, non programmi.
    Un poster loro non esiste, e prenderne uno a caso e' peggio che non
    averlo (una locandina sbagliata sembra giusta).
    Fin qui portavano tutte lo stesso segnaposto scuro e vuoto. L'utente,
    guardando lo schermo: "ancora tantissime locandine nere".

    Aveva ragione, e la risposta si vede su Netflix: **le loro tessere hanno
    il titolo scritto SOPRA l'immagine**. Da noi il nome compare solo sotto
    quella selezionata, quindi una fila di tessere a tema e' una fila di
    buchi. Basta scriverci sopra il nome e smettono di essere buchi.

COME
    Una PNG per etichetta, generata QUI sul PC e spedita con l'add-on: a
    Kodi non si chiede di disegnare testo su un'immagine, e il Raspberry non
    deve fare nessun lavoro in piu'.
    Il nome del file e' l'impronta dell'etichetta, cosi' non ci sono nomi
    strani da mettere in un percorso.

USO
    python fai-tessere.py
"""

import hashlib
import importlib.util
import io
import json
import os
import sys

import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

QUI = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(QUI, "plugin.video.saghe")
SCOPERTE = os.path.join(ADDON, "resources", "lib", "scoperte.py")
# LE COPERTINE NON STANNO NEL SORGENTE: vivono nei dati utente di ogni
# apparecchio (`addon_data/plugin.video.saghe/copertine.json`), sotto la
# chiave "voci". Al primo giro l'ho cercato dentro l'add-on, non l'ho
# trovato, e lo script ha disegnato una tessera di testo per TUTTE e 185 le
# voci - comprese le 145 che una locandina vera ce l'hanno. Si porta qui una
# copia presa dall'apparecchio, e se manca ci si ferma invece di indovinare.
COPERTINE = os.path.join(QUI, "copertine-dal-pi.json")
FUORI = os.path.join(ADDON, "resources", "tessere")
SFONDI = os.path.join(ADDON, "resources", "sfondi.json")

# Il doppio della cella (164x250): su uno schermo 4K non sgranano.
L, A = 512, 288      # 16:9, come le tessere di Netflix
FONDO = (26, 26, 28)
BORDO = (58, 58, 62)
TESTO = (243, 237, 227)
OCCHIELLO = (232, 162, 74)      # l'ambra della skin


def _font(punti, grassetto=False):
    nomi = (["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"] if grassetto
            else ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"])
    for n in nomi:
        for d in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "."):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, punti)
    return ImageFont.load_default()


def _a_capo(d, testo, font, larghezza):
    righe, riga = [], ""
    for parola in testo.split():
        prova = (riga + " " + parola).strip()
        if d.textlength(prova, font=font) <= larghezza:
            riga = prova
        else:
            if riga:
                righe.append(riga)
            riga = parola
    if riga:
        righe.append(riga)
    return righe


def tessera(etichetta, sezione):
    """Una tessera 16:9 scura, SENZA TESTO.

    Il nome NON si scrive qui: lo scrive la skin sopra l'immagine, come fa
    Netflix. Al primo giro l'avevo disegnato anche dentro, e a schermo
    compariva due volte ("Predatori" grande al centro e "Predatori" piccolo
    in basso).
    Serve comunque un'immagine vera e della forma giusta: senza, Kodi
    stirava la locandina verticale dentro la cornice orizzontale.
    """
    im = Image.new("RGB", (L, A), FONDO)
    d = ImageDraw.Draw(im)
    # Una trama appena accennata, se no la tessera sembra un buco nero.
    for x in range(-A, L, 26):
        d.line([(x, A), (x + A, 0)], fill=(32, 32, 35), width=1)
    d.rectangle([0, 0, L - 1, A - 1], outline=BORDO)
    # Una riga ambra in basso a sinistra: e' l'unico segno di colore, e
    # richiama la cornice del cursore.
    d.rectangle([0, A - 4, L, A], fill=(58, 44, 26))
    return im


def _scarica(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def tessera_da_locandina(url):
    """Una tessera 16:9 costruita SOPRA la locandina verticale.

    Il caso: 77 voci non hanno uno sfondo largo su TMDb ma una locandina
    ce l'hanno. Buttarla per mettere un rettangolo scuro sarebbe uno spreco;
    metterla dentro la cornice 16:9 lascia due bande nere ai lati.
    Cosi' invece si usa la locandina DUE volte: una copia ingrandita e
    sfocata riempie tutta la tessera, e sopra ci sta la locandina nitida al
    centro. E' il modo con cui i lettori musicali riempiono lo sfondo con la
    copertina del disco: i colori sono sempre quelli giusti, perche' vengono
    dall'immagine stessa.
    """
    loc = _scarica(url)
    # lo sfondo: ritagliato a 16:9 dal centro, sfocato e scurito
    lp, ap = loc.size
    lato = min(lp, ap * L // A)
    alt = lato * A // L
    x, y = (lp - lato) // 2, max(0, (ap - alt) // 2)
    sfondo = loc.crop((x, y, x + lato, y + alt)).resize((L, A), Image.LANCZOS)
    sfondo = sfondo.filter(ImageFilter.GaussianBlur(radius=L // 22))
    sfondo = Image.blend(sfondo, Image.new("RGB", (L, A), FONDO), 0.45)
    # la locandina nitida al centro, alta quanto la tessera
    h = A - 16
    w = max(1, int(loc.size[0] * h / loc.size[1]))
    sfondo.paste(loc.resize((w, h), Image.LANCZOS), ((L - w) // 2, 8))
    d = ImageDraw.Draw(sfondo)
    d.rectangle([0, 0, L - 1, A - 1], outline=BORDO)
    return sfondo


def main():
    spec = importlib.util.spec_from_file_location("scoperte", SCOPERTE)
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    try:
        with io.open(COPERTINE, encoding="utf-8") as f:
            copertine = (json.load(f) or {}).get("voci") or {}
    except Exception as e:
        print("MANCA %s (%s).\nPrendilo dall'apparecchio:\n"
              "  scp root@192.168.1.105:"
              "/storage/.kodi/userdata/addon_data/plugin.video.saghe/"
              "copertine.json %s" % (COPERTINE, e, COPERTINE))
        return 1
    if not copertine:
        print("Il file delle copertine e' vuoto: mi fermo, se no disegno una "
              "tessera di testo anche sopra le locandine vere.")
        return 1
    print("copertine vere lette: %d" % len(copertine))

    if not os.path.isdir(FUORI):
        os.makedirs(FUORI)

    try:
        with io.open(SFONDI, encoding="utf-8") as f:
            sfondi = json.load(f) or {}
    except Exception:
        sfondi = {}
    print("sfondi 16:9 gia' trovati: %d" % sum(1 for v in sfondi.values() if v))

    mappa, fatte, composte = {}, 0, 0
    for sezione, nome in (("documentari", "Documentari"),
                          ("cucina", "Cucina"),
                          ("youtube", "YouTube")):
        for intestazione, voci in sc.scaffale(sezione):
            for etichetta, _ind, _nota, _tipo in voci:
                if sfondi.get(etichetta):
                    continue          # ha gia' uno sfondo largo vero
                # La VERSIONE entra nel nome del file. Kodi tiene in cache le
                # immagini PER NOME: rigenerando una tessera con lo stesso
                # nome, a schermo restava quella vecchia (le tessere col
                # testo continuavano a comparire dopo che le avevo tolte).
                # Cambiando versione si cambia nome e la cache non c'entra.
                chiave = "v3_" + hashlib.md5(
                    etichetta.encode("utf-8")).hexdigest()[:16]
                loc = copertine.get(etichetta)
                im = None
                if loc:
                    try:
                        im = tessera_da_locandina(loc)
                        composte += 1
                    except Exception as e:
                        print("   (locandina non scaricata: %s) %s" % (etichetta, e))
                if im is None:
                    im = tessera(etichetta, intestazione or nome)
                im.save(os.path.join(FUORI, chiave + ".png"))
                mappa[etichetta] = chiave + ".png"
                fatte += 1

    with io.open(os.path.join(FUORI, "indice.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(mappa, ensure_ascii=False, indent=1, sort_keys=True))
    print("tessere: %d in tutto - %d composte dalla locandina, "
          "%d scure col solo titolo  ->  %s"
          % (fatte, composte, fatte - composte, FUORI))
    for e in sorted(mappa)[:8]:
        print("   %-34s %s" % (e, mappa[e]))
    if fatte > 8:
        print("   ... e altre %d" % (fatte - 8))
    return 0


if __name__ == "__main__":
    sys.exit(main())
