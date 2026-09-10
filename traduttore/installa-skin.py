# -*- coding: utf-8 -*-
"""INSTALLA UNA SKIN (e tutto cio' che le serve) DAL REPOSITORY UFFICIALE.

PERCHE' UNO SCRIPT E NON "installa da Kodi"
    Kodi sa installare da solo, ma bisogna essere davanti alla TV col
    telecomando. Qui gli apparecchi sono tre (banco sul PC, Raspberry del
    salotto, box 8K) e la stessa skin va messa su tutti uguale. A mano si
    sbaglia, e sul box non c'e' nemmeno la tastiera.

DA DOVE SCARICA
    `mirrors.kodi.tv`, cioe' il repository UFFICIALE di Kodi. Non serve
    accendere le "origini sconosciute" e non si scarica da nessun sito di
    terzi. Le skin che stanno li' sono quelle rilasciate dal progetto Kodi.

LA CATENA DELLE DIPENDENZE
    Una skin da sola non basta: Arctic Zephyr Mod vuole script.skinshortcuts,
    script.embuary.helper, plugin.video.themoviedb.helper e altri, e quelli
    a loro volta ne vogliono altri ancora. Lo script segue la catena fino in
    fondo. Le dipendenze che cominciano per `xbmc.` sono pezzi di Kodi
    stesso: non si scaricano, si controlla solo che la versione basti.

USO
    python installa-skin.py skin.arctic.zephyr.mod omega  <cartella addons>
    python installa-skin.py skin.copacetic        nexus   <cartella addons>

    Per il PC:        %APPDATA%\\Kodi\\addons
    Per gli altri:    si scarica qui e poi si copia (vedi porta-skin.py)
"""

import gzip
import io
import os
import re
import sys
import urllib.request
import zipfile

MIRROR = "https://mirrors.kodi.tv/addons/%s"
QUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(QUI, "_skin_scaricate")


def _scarica(url, byte=True):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read() if byte else r.read().decode("utf-8", "replace")


def indice(versione):
    """L'elenco di tutti gli add-on di quella versione di Kodi."""
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "addons-%s.xml" % versione)
    if not os.path.exists(p):
        dati = _scarica((MIRROR % versione) + "/addons.xml.gz")
        testo = gzip.decompress(dati).decode("utf-8", "replace")
        io.open(p, "w", encoding="utf-8").write(testo)
    return io.open(p, encoding="utf-8").read()


def scheda(testo, aid):
    m = re.search(r'<addon\b[^>]*id="%s".*?</addon>' % re.escape(aid),
                  testo, re.S)
    return m.group(0) if m else ""


def catena(testo, aid, visti=None):
    """Tutti gli add-on da installare, dipendenze comprese, senza doppioni."""
    visti = visti if visti is not None else []
    if aid in visti or aid.startswith("xbmc."):
        return visti
    b = scheda(testo, aid)
    if not b:
        print("   ATTENZIONE: %s non c'e' in questo repository" % aid)
        return visti
    visti.append(aid)
    for dip, _v in re.findall(r'<import addon="([^"]+)"(?: version="([^"]+)")?', b):
        catena(testo, dip, visti)
    return visti


def versione_di(testo, aid):
    b = scheda(testo, aid)
    m = re.search(r'version="([^"]+)"', b)
    return m.group(1) if m else ""


def installa(aid, kodi, dest):
    testo = indice(kodi)
    lista = catena(testo, aid)
    if not lista:
        return 1
    print("da installare: %d add-on\n" % len(lista))
    os.makedirs(CACHE, exist_ok=True)
    for i, a in enumerate(lista, 1):
        ver = versione_di(testo, a)
        nome = "%s-%s.zip" % (a, ver)
        p = os.path.join(CACHE, nome)
        if not os.path.exists(p):
            url = "%s/%s/%s" % (MIRROR % kodi, a, nome)
            try:
                open(p, "wb").write(_scarica(url))
            except Exception as e:
                print("  %2d/%d  %-38s NON scaricato: %s" % (i, len(lista), a, e))
                continue
        # Gia' presente e della stessa versione: non si tocca. Reinstallare
        # sopra a un add-on che funziona e' il modo piu' facile per rompere
        # una configurazione che c'era.
        cartella = os.path.join(dest, a)
        axml = os.path.join(cartella, "addon.xml")
        if os.path.exists(axml):
            t = io.open(axml, encoding="utf-8", errors="replace").read()
            m = re.search(r'<addon\b[^>]*?version="([^"]+)"', t, re.S)
            if m and m.group(1) == ver:
                print("  %2d/%d  %-38s gia' presente (v%s)" % (i, len(lista), a, ver))
                continue
        with zipfile.ZipFile(p) as z:
            z.extractall(dest)
        print("  %2d/%d  %-38s installato v%s" % (i, len(lista), a, ver))
    return 0


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    aid, kodi, dest = sys.argv[1], sys.argv[2], os.path.expandvars(sys.argv[3])
    if not os.path.isdir(dest):
        print("La cartella degli add-on non esiste:", dest)
        return 1
    print("Installo %s per Kodi %s in %s\n"
          % (aid, "20 (nexus)" if kodi == "nexus" else "21 (omega)", dest))
    return installa(aid, kodi, dest)


if __name__ == "__main__":
    sys.exit(main())
