# -*- coding: utf-8 -*-
"""IL LOGO: NOVIX. Marchio, lettera a nastro, splash e animazione d'apertura.

PERCHE' (l'utente, 11/09/2026)
    "vorrei un logo in stile Netflix animato in apertura, e persistente in
    tutte le sezioni dell'add-on proprio come Netflix". Il nome l'ha scelto lui
    fra NOVIX, ZEFIRA, VIDORA e LUMIRA.
    E poi, vista la prima animazione: "non far apparire il logo della skin
    Arctic, lascia solo il nostro, cosi' il suo tempo e' piu' lungo e puo'
    avere un'espansione maggiore con le bande, e non lineare ma a diffusione
    stile Netflix".

LE SCELTE
    - NOME: NOVIX. Lettere Bahnschrift Bold Condensed, rosso cinema, quelle ai
      lati piu' alte (la "curva" dei marchi da cinema).
    - LETTERA A NASTRO: una N di tre bande, la diagonale rossa sopra le due
      verticali scure, con l'ombra delle pieghe. Sta al posto del logo di Kodi
      in ogni schermata (service.videoteca.guardiano/vestito.py).
    - SPLASH: la stessa N su nero, al posto dell'immagine di Kodi che compare
      all'accensione (special://home/media/splash.jpg).
    - ANIMAZIONE, 4,8 secondi (120 fotogrammi da 40 ms):
        1. la N si accende al centro (0 - 1 s);
        2. TUFFO NELLA N: la lettera cresce sempre piu' in fretta e si scioglie
           in 140 strisce di luce, ognuna col suo colore, la sua larghezza e la
           sua velocita'. Si allargano per DIFFUSIONE, non in linea retta:
           partono piano e poi esplodono verso i bordi (u elevato alla sua
           potenza), piu' larghe man mano che "si avvicinano", con un alone;
        3. le strisce si spengono e dal buio emerge NOVIX, attraversato da un
           lampo di luce;
        4. tutto sfuma nella home.

USO
    python fai-logo.py      tutto in plugin.video.saghe/resources/media/logo
"""

import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

QUI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(QUI, "plugin.video.saghe", "resources", "media", "logo")
CARATTERE = r"C:\Windows\Fonts\bahnschrift.ttf"
NOME = "NOVIX"
ALTO, BASSO = (255, 45, 45), (160, 6, 15)
W, H = 1280, 720
FOTOGRAMMI = 120
# 220 strisce distribuite su TUTTA la larghezza: "le bande falle allargare a tutto lo schermo" (11/09/2026)
STRISCE = 220
TAVOLOZZA = [(229, 9, 20), (255, 45, 45), (255, 90, 60), (255, 140, 70), (214, 30, 110), (170, 30, 160),
             (110, 40, 210), (60, 90, 230), (255, 190, 120), (255, 240, 230)]


def _font(misura):
    f = ImageFont.truetype(CARATTERE, misura)
    f.set_variation_by_name("Bold Condensed")
    return f


def _sfumatura(w, h, alto, basso):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(alto[i] + (basso[i] - alto[i]) * t) for i in range(3)) + (255,))
    return img


def marchio(nome=NOME, alto=ALTO, basso=BASSO, altezza=300, curva=0.16):
    """La scritta, lettere piu' alte ai lati, su fondo trasparente."""
    f = _font(altezza)
    lettere = []
    n = max(1, len(nome) - 1)
    for i, c in enumerate(nome):
        box = f.getbbox(c)
        maschera = Image.new("L", (box[2] - box[0] + 20, box[3] - box[1] + 20), 0)
        ImageDraw.Draw(maschera).text((10 - box[0], 10 - box[1]), c, font=f, fill=255)
        posto = (i - n / 2.0) / (n / 2.0)
        maschera = maschera.resize((maschera.width, int(maschera.height * (1 + curva * posto * posto))), Image.LANCZOS)
        colore = _sfumatura(maschera.width, maschera.height, alto, basso)
        colore.putalpha(maschera)
        lettere.append(colore)
    spazio = int(altezza * 0.03)
    larg = sum(x.width for x in lettere) + spazio * (len(lettere) - 1)
    alt = max(x.height for x in lettere)
    tela = Image.new("RGBA", (larg + 40, alt + 40), (0, 0, 0, 0))
    x = 20
    for l in lettere:
        tela.alpha_composite(l, (x, 20 + (alt - l.height) // 2))
        x += l.width + spazio
    ombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ombra.putalpha(tela.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda a: int(a * 0.55)))
    fondo = Image.new("RGBA", (tela.width + 10, tela.height + 10), (0, 0, 0, 0))
    fondo.alpha_composite(ombra, (6, 8))
    fondo.alpha_composite(tela, (0, 0))
    return fondo.crop(fondo.getbbox())


def _maschera(lato, punti):
    m = Image.new("L", (lato, lato), 0)
    ImageDraw.Draw(m).polygon(punti, fill=255)
    return m


def monogramma(lato=512):
    """La N a nastro: due bande verticali scure e la diagonale rossa sopra, con le pieghe in ombra."""
    s = lato / 512.0
    img = Image.new("RGBA", (lato, lato), (0, 0, 0, 0))
    sinistra = _maschera(lato, [(104 * s, 36 * s), (206 * s, 36 * s), (206 * s, 476 * s), (104 * s, 476 * s)])
    destra = _maschera(lato, [(306 * s, 36 * s), (408 * s, 36 * s), (408 * s, 476 * s), (306 * s, 476 * s)])
    diagonale = _maschera(lato, [(104 * s, 36 * s), (206 * s, 36 * s), (408 * s, 476 * s), (306 * s, 476 * s)])
    vuoto = Image.new("RGBA", img.size, (0, 0, 0, 0))
    scuro = _sfumatura(lato, lato, (150, 5, 14), (92, 2, 8))
    img.alpha_composite(Image.composite(scuro, vuoto, sinistra))
    img.alpha_composite(Image.composite(scuro, vuoto, destra))
    piega = diagonale.filter(ImageFilter.GaussianBlur(16 * s))
    velo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    velo.putalpha(ImageChops.multiply(piega, ImageChops.lighter(sinistra, destra)).point(lambda a: int(a * 0.75)))
    img.alpha_composite(velo)
    img.alpha_composite(Image.composite(_sfumatura(lato, lato, (255, 44, 44), (214, 8, 20)), vuoto, diagonale))
    return img


def _metti(tela, pezzo, cx, cy, scala=1.0, trasparenza=1.0):
    """Incolla `pezzo` centrato in (cx, cy), anche se esce dai bordi (la N ingrandita e' piu' grande dello schermo)."""
    if scala <= 0 or trasparenza <= 0.003:
        return
    w, h = max(1, int(pezzo.width * scala)), max(1, int(pezzo.height * scala))
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    # si ritaglia prima di ingrandire: una N larga 4000 punti non serve intera
    vx0, vy0, vx1, vy1 = max(0, x0), max(0, y0), min(tela.width, x0 + w), min(tela.height, y0 + h)
    if vx1 <= vx0 or vy1 <= vy0:
        return
    sx0, sy0 = (vx0 - x0) / scala, (vy0 - y0) / scala
    sx1, sy1 = (vx1 - x0) / scala, (vy1 - y0) / scala
    p = pezzo.resize((vx1 - vx0, vy1 - vy0), Image.LANCZOS, box=(sx0, sy0, sx1, sy1))
    if trasparenza < 1:
        p.putalpha(p.getchannel("A").point(lambda a: int(a * trasparenza)))
    tela.alpha_composite(p, (vx0, vy0))


def _dolce(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _accelera(t, potenza=2.4):
    return max(0.0, min(1.0, t)) ** potenza


def _strisce():
    caso = random.Random(11)
    fuori = []
    for _ in range(STRISCE):
        fuori.append({"posto": caso.uniform(-1.0, 1.0),         # dove nasce e dove arriva (-1 bordo sinistro, +1 destro)
                      "velocita": caso.uniform(0.85, 1.25),
                      "potenza": caso.uniform(1.3, 2.4),         # la diffusione: piu' alta = parte piu' piano, esplode dopo
                      "larghezza": caso.choice([2, 2, 3, 4, 5, 7, 10, 14, 20, 30]),
                      "colore": caso.choice(TAVOLOZZA),
                      "luce": caso.uniform(0.35, 1.0),
                      "ritardo": caso.uniform(0.0, 0.05)})
    return fuori


def _profilo_verticale():
    """Le strisce sono piu' luminose al centro dello schermo e sfumano verso l'alto e il basso."""
    m = Image.new("L", (1, H))
    for y in range(H):
        d = (y - H / 2) / (H / 2)
        m.putpixel((0, y), int(255 * math.exp(-2.2 * d * d)))
    return m.resize((W, H))


def fotogramma(t, lettera, scritta, strisce, profilo):
    tela = Image.new("RGB", (W, H), (0, 0, 0))
    cx, cy = W / 2, H / 2

    # 2. le strisce di luce: diffusione non lineare dal centro della N verso i bordi
    if 0.20 < t < 0.90:
        strato = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(strato)
        # si spengono prima che arrivi la scritta: sopra le strisce accese NOVIX non si leggeva
        spegni = 1 - _dolce((t - 0.60) / 0.14)
        for s in strisce:
            u = (t - 0.22 - s["ritardo"]) / 0.28          # ai bordi in poco piu' di un secondo
            if u <= 0:
                continue
            u = min(u, 1.0)
            diffusione = u ** s["potenza"]
            accendi = _dolce(u / 0.12)
            # partono dentro la N e si diffondono fino ai bordi: alla fine coprono tutto lo schermo
            x = cx + s["posto"] * (90 + (W * 0.56) * diffusione * s["velocita"])
            # le larghe crescono meno e brillano meno: fili di luce, non muri colorati
            larg = s["larghezza"] * (1 + (4 if s["larghezza"] < 14 else 2) * diffusione)
            luce = s["luce"] * accendi * spegni * (0.7 if s["larghezza"] >= 14 else 1.0)
            if luce <= 0.01 or x + larg < 0 or x - larg > W:
                continue
            colore = tuple(int(c * luce) for c in s["colore"])
            d.rectangle([x - larg / 2, 0, x + larg / 2, H], fill=colore)
        strato = Image.composite(strato, Image.new("RGB", (W, H)), profilo)
        alone = strato.filter(ImageFilter.GaussianBlur(14))
        tela = ImageChops.add(tela, alone)
        tela = ImageChops.add(tela, strato.filter(ImageFilter.GaussianBlur(1.5)))

    # 1. e 2. la N: si accende, poi il tuffo (cresce sempre piu' in fretta e si dissolve nelle strisce)
    accesa = 0.45 + 0.55 * _dolce(t / 0.18)
    tuffo = _accelera((t - 0.20) / 0.42)
    scala = 0.92 * (1 + 7 * tuffo)          # la N grande fin dall'inizio (11/09/2026)
    trasparenza = accesa * (1 - _dolce((t - 0.30) / 0.26))
    if trasparenza > 0.01:
        n_strato = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _metti(n_strato, lettera, cx, cy, scala, trasparenza)
        bagliore = n_strato.filter(ImageFilter.GaussianBlur(22))
        base = tela.convert("RGBA")
        base.alpha_composite(bagliore)
        base.alpha_composite(n_strato)
        tela = base.convert("RGB")

    # 3. NOVIX emerge dal buio, e un lampo di luce lo attraversa
    comparsa = _dolce((t - 0.68) / 0.16)
    if comparsa > 0:
        s_strato = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _metti(s_strato, scritta, cx, cy, 1.18 - 0.18 * comparsa, comparsa)
        lampo_t = (t - 0.74) / 0.16
        if 0 < lampo_t < 1:
            fascia = Image.new("L", (W, H), 0)
            x = -300 + lampo_t * (W + 600)
            ImageDraw.Draw(fascia).polygon([(x - 90, 0), (x + 40, 0), (x + 150, H), (x + 20, H)], fill=200)
            fascia = ImageChops.multiply(fascia.filter(ImageFilter.GaussianBlur(30)), s_strato.getchannel("A"))
            lampo = Image.new("RGBA", (W, H), (255, 235, 225, 0))
            lampo.putalpha(fascia)
            s_strato.alpha_composite(lampo)
        base = tela.convert("RGBA")
        base.alpha_composite(s_strato.filter(ImageFilter.GaussianBlur(12)).point(lambda v: v // 2))
        base.alpha_composite(s_strato)
        tela = base.convert("RGB")

    # 4. il buio prima della home
    buio = _dolce((t - 0.94) / 0.06)
    if buio > 0:
        tela = Image.blend(tela, Image.new("RGB", (W, H)), buio)
    return tela


def suono(percorso, durata=5.2, frequenza=48000):
    """Il suono dell'apertura, NOSTRO (quello di Netflix e' un marchio registrato), in tempo coi fotogrammi.

    L'utente, 11/09/2026: "metti anche un suono di sottofondo al logo, come fa Netflix".
      0,12 s  un colpo sordo e morbido: la N che si accende
      1,0-3,3 s  un soffio che cresce e si schiarisce, con un tono che sale: le strisce che si diffondono
      3,30 s  "ta", breve
      3,58 s  "DUM", profondo e lungo: NOVIX che emerge
    e un riverbero da sala. Sintetizzato qui, campione per campione: nessun file preso da fuori."""
    import struct
    import wave
    n = int(durata * frequenza)
    sinistra, destra = [0.0] * n, [0.0] * n

    def colpo(inizio, armoniche, decadimento, forza):
        i0 = int(inizio * frequenza)
        for i in range(i0, min(n, i0 + int(frequenza * decadimento * 5))):
            t = (i - i0) / float(frequenza)
            inviluppo = math.exp(-t / decadimento) * min(1.0, t / 0.004)
            v = forza * inviluppo * sum(a * math.sin(2 * math.pi * f * t) for f, a in armoniche)
            sinistra[i] += v
            destra[i] += v

    def schiocco(inizio, forza, lunghezza=0.06, seme=1):
        caso, y = random.Random(seme), 0.0
        i0 = int(inizio * frequenza)
        for i in range(i0, min(n, i0 + int(frequenza * lunghezza))):
            t = (i - i0) / float(frequenza)
            y += 0.18 * (caso.uniform(-1, 1) - y)
            v = forza * y * math.exp(-t / (lunghezza / 4))
            sinistra[i] += v
            destra[i] += v

    colpo(0.12, [(55, 1.0), (110, 0.4)], 0.35, 0.45)
    schiocco(0.12, 0.25)
    caso = random.Random(3)
    ys = yd = 0.0
    for i in range(int(1.0 * frequenza), int(3.3 * frequenza)):
        t = i / float(frequenza)
        u = (t - 1.0) / 2.3
        inviluppo = (math.sin(math.pi * min(1.0, u * 0.92)) ** 2) * (0.25 + 0.75 * u)
        taglio = 0.02 + 0.22 * u                       # il soffio si schiarisce man mano
        ys += taglio * (caso.uniform(-1, 1) - ys)
        yd += taglio * (caso.uniform(-1, 1) - yd)      # due soffi diversi: il suono si allarga
        tono = 0.25 * math.sin(2 * math.pi * (110 + 110 * u * u) * t) + 0.12 * math.sin(2 * math.pi * (165.5 + 165 * u * u) * t)
        sinistra[i] += inviluppo * (0.55 * ys + 0.30 * tono)
        destra[i] += inviluppo * (0.55 * yd + 0.30 * tono)
    colpo(3.30, [(98, 1.0), (196, 0.5), (294, 0.2)], 0.18, 0.55)
    schiocco(3.30, 0.3, seme=2)
    colpo(3.58, [(49, 1.0), (98, 0.7), (147, 0.3), (196, 0.15)], 1.3, 0.85)
    schiocco(3.58, 0.45, seme=3)

    # il riverbero: echi brevi, un po' diversi a destra e a sinistra
    uscita_s, uscita_d = sinistra[:], destra[:]
    for ritardo, guadagno in ((0.031, 0.35), (0.047, 0.30), (0.071, 0.25), (0.113, 0.20), (0.173, 0.15), (0.257, 0.10)):
        ks, kd = int(ritardo * frequenza), int(ritardo * 1.07 * frequenza)
        for i in range(ks, n):
            uscita_s[i] += guadagno * sinistra[i - ks]
        for i in range(kd, n):
            uscita_d[i] += guadagno * destra[i - kd]
    picco = max(max(abs(v) for v in uscita_s), max(abs(v) for v in uscita_d)) or 1.0
    scala = 0.89 / picco                               # -1 dB
    coda = int(0.4 * frequenza)
    with wave.open(percorso, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(frequenza)
        blocchi = []
        for i in range(n):
            sfuma = min(1.0, (n - i) / float(coda))
            blocchi.append(struct.pack("<hh", int(uscita_s[i] * scala * sfuma * 32767), int(uscita_d[i] * scala * sfuma * 32767)))
        w.writeframes(b"".join(blocchi))


def main(_argv):
    os.makedirs(os.path.join(DEST, "intro"), exist_ok=True)
    marchio().save(os.path.join(DEST, "marchio.png"), optimize=True)
    lettera = monogramma(512)
    lettera.save(os.path.join(DEST, "monogramma.png"), optimize=True)
    lettera.resize((128, 128), Image.LANCZOS).save(os.path.join(DEST, "monogramma-128.png"), optimize=True)
    Image.new("RGB", (16, 16), (0, 0, 0)).save(os.path.join(DEST, "nero.png"))
    scritta = marchio()
    scritta = scritta.resize((int(W * 0.50), int(scritta.height * W * 0.50 / scritta.width)), Image.LANCZOS)
    strisce, profilo = _strisce(), _profilo_verticale()
    # lo splash di Kodi: la N accesa, cosi' l'animazione riparte da dove lo splash la lascia
    splash = fotogramma(0.18, lettera, scritta, strisce, profilo).resize((1920, 1080), Image.LANCZOS)
    splash.save(os.path.join(DEST, "splash.jpg"), quality=90)
    splash.save(os.path.join(DEST, "splash.png"), optimize=True)
    for vecchio in os.listdir(os.path.join(DEST, "intro")):
        os.remove(os.path.join(DEST, "intro", vecchio))
    peso = 0
    for n in range(FOTOGRAMMI):
        p = os.path.join(DEST, "intro", "%03d.jpg" % n)
        fotogramma(n / (FOTOGRAMMI - 1.0), lettera, scritta, strisce, profilo).save(p, quality=86, optimize=True)
        peso += os.path.getsize(p)
    suono(os.path.join(DEST, "suono.wav"))
    print("%s: %d fotogrammi (%.1f s), %d KB di animazione, splash e suono pronti (%d KB)"
          % (NOME, FOTOGRAMMI, FOTOGRAMMI * 0.04, peso // 1024, os.path.getsize(os.path.join(DEST, "suono.wav")) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
