# -*- coding: utf-8 -*-
"""Estrae il modulo Widevine dall'immagine di ripristino ChromeOS.

PERCHE' QUESTA STRADA
    Netflix e Prime Video mandano i film cifrati. Il modulo che li decifra
    (Widevine) Google non lo distribuisce sciolto per ARM: l'unico posto
    legittimo da cui prenderlo e' un'immagine ufficiale di ChromeOS, dove
    sta dentro Chrome. E' quello che fa anche l'aiutante di Kodi
    (inputstreamhelper); qui lo si fa sul PC perche' sulla linea 4G di casa
    un file da 1,2 GB scaricato dal Raspberry si interrompe a meta'.

QUALE IMMAGINE
    Lo spazio utente del Raspberry e' ARM a 32 bit (il nucleo e' a 64, ma
    quello che conta e' lo spazio utente). Serve quindi un'immagine ChromeOS
    a 32 bit: "bob". Prendere quella a 64 bit darebbe un modulo che non si
    carica, senza spiegare perche'.

COSA FA, IN ORDINE
    1. scompatta lo zip (dentro c'e' un'immagine di disco intera)
    2. legge la tabella delle partizioni e trova ROOT-A
    3. la monta in sola lettura
    4. copia libwidevinecdm.so
    5. smonta e pulisce

Va eseguito DENTRO WSL come root: servono i dispositivi di loop.
"""
import os
import re
import subprocess
import sys
import zipfile

CARTELLA = "/mnt/c/Users/infoa/AppData/Local/Temp/claude/" \
           "c--Users-infoa-OneDrive-Documenti-mia-estensione-vs-code/" \
           "207f9c80-f4bd-4425-b256-8d8daf11af1a/scratchpad/widevine"
ZIP = os.path.join(CARTELLA, "chromeos_bob.zip")
PUNTO = "/mnt/chromeos"
USCITA = os.path.join(CARTELLA, "libwidevinecdm.so")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def scompatta():
    with zipfile.ZipFile(ZIP) as z:
        nomi = [n for n in z.namelist() if n.endswith(".bin")]
        if not nomi:
            raise SystemExit("nello zip non c'e' nessuna immagine .bin")
        bin_path = os.path.join(CARTELLA, os.path.basename(nomi[0]))
        if os.path.exists(bin_path) and os.path.getsize(bin_path) > 1000000000:
            print("  immagine gia' scompattata")
            return bin_path
        print("  scompatto %s ..." % nomi[0])
        with z.open(nomi[0]) as sorg, open(bin_path, "wb") as dest:
            while True:
                pezzo = sorg.read(8 * 1024 * 1024)
                if not pezzo:
                    break
                dest.write(pezzo)
        return bin_path


def trova_root_a(bin_path):
    """L'offset in byte della partizione ROOT-A.

    Nelle immagini ChromeOS ROOT-A e' la partizione 3. Non ci si fida del
    numero: si prende la piu' grande, che e' sempre quella.
    """
    r = sh("fdisk -l -o Device,Start,Sectors,Size,Type '%s'" % bin_path)
    righe = [x for x in r.stdout.split("\n") if bin_path in x]
    migliore = None
    for x in righe:
        pezzi = x.split()
        try:
            inizio, settori = int(pezzi[1]), int(pezzi[2])
        except (IndexError, ValueError):
            continue
        if migliore is None or settori > migliore[1]:
            migliore = (inizio, settori, x.strip())
    if not migliore:
        print(r.stdout[:800])
        raise SystemExit("non ho trovato nessuna partizione")
    print("  partizione scelta: %s" % migliore[2])
    return migliore[0] * 512


def main():
    if os.geteuid() != 0:
        raise SystemExit("va eseguito come root dentro WSL")
    if not os.path.exists(ZIP):
        raise SystemExit("manca %s" % ZIP)

    print("1) scompatto")
    bin_path = scompatta()
    print("   %s  (%.1f GB)" % (os.path.basename(bin_path),
                                os.path.getsize(bin_path) / 1e9))

    print("2) cerco ROOT-A")
    offset = trova_root_a(bin_path)

    print("3) monto in sola lettura")
    os.makedirs(PUNTO, exist_ok=True)
    sh("umount %s 2>/dev/null" % PUNTO)
    r = sh("mount -o ro,loop,offset=%d '%s' %s" % (offset, bin_path, PUNTO))
    if r.returncode != 0:
        raise SystemExit("montaggio fallito: %s" % (r.stderr or r.stdout))

    print("4) cerco il modulo")
    r = sh("find %s -name 'libwidevinecdm.so' 2>/dev/null" % PUNTO)
    trovati = [x for x in r.stdout.split("\n") if x.strip()]
    if not trovati:
        sh("umount %s" % PUNTO)
        raise SystemExit("libwidevinecdm.so non trovato dentro l'immagine")
    sorgente = trovati[0]
    print("   %s" % sorgente)
    sh("cp '%s' '%s'" % (sorgente, USCITA))

    # la versione serve per sapere cosa si e' installato
    r = sh("strings '%s' | grep -m1 -E '^4\\.10\\.[0-9]+'" % USCITA)
    versione = (r.stdout or "").strip() or "sconosciuta"

    sh("umount %s" % PUNTO)
    print("5) fatto")
    print("   %s  (%.1f MB)  versione %s"
          % (USCITA, os.path.getsize(USCITA) / 1e6, versione))
    r = sh("file '%s'" % USCITA)
    print("   %s" % r.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
