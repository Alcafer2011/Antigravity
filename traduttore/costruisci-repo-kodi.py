# -*- coding: utf-8 -*-
"""Costruisce il REPOSITORY KODI per gli aggiornamenti automatici.

Prende plugin.video.saghe + skin.saghe (dal Kodi del PC, la copia testata),
li impacchetta come vuole Kodi, crea l'addon `repository.videoteca` che
punta a GitHub, e lascia tutto pronto in una cartella da `git push`.

USO
    python costruisci-repo-kodi.py [cartella-del-repo-clonato]

    Se non passi la cartella, la cerca in ~/kodi-s4me-addon-personale.
    PRIMA di lanciare, clona il repo GitHub vuoto:
        git clone https://github.com/Alcafer2011/kodi-s4me-addon-personale.git

DOPO
    cd <cartella-repo>
    git add -A && git commit -m "repo v..." && git push
    Poi su ogni Kodi, UNA volta:
      Impostazioni > Add-on > Installa da file zip >
      la cartella del repo > repository.videoteca > repository.videoteca-1.0.0.zip
    Da li' in poi: Installa da repository > Videoteca (Alcafer) > ...
    e Kodi aggiorna da solo quando alzi la `version` in addon.xml e rifai push.
"""

import hashlib
import os
import re
import shutil
import sys
import zipfile

UTENTE = "Alcafer2011"
REPO = "kodi-s4me-addon-personale"
RAMO = "main"
RAW = "https://raw.githubusercontent.com/%s/%s/%s" % (UTENTE, REPO, RAMO)

# Da dove prendere gli addon gia' testati (il Kodi del PC).
KODI_ADDONS = os.path.expandvars(r"%APPDATA%\Kodi\addons")
DA_IMPACCHETTARE = ["plugin.video.saghe", "skin.saghe"]

REPO_ADDON_ID = "repository.videoteca"
REPO_ADDON_VER = "1.0.0"

ESCLUDI = re.compile(r"(__pycache__|\.pyc$|\.pyo$|\.git|\.bak-|\.DS_Store)")


def versione(cartella_addon):
    x = open(os.path.join(cartella_addon, "addon.xml"), encoding="utf-8").read()
    m = re.search(r'<addon\b[^>]*\bversion="([^"]+)"', x)
    return m.group(1) if m else "0.0.1"


def blocco_addon_xml(cartella_addon):
    """L'<addon ...>...</addon> di un addon, senza la riga <?xml?>."""
    x = open(os.path.join(cartella_addon, "addon.xml"), encoding="utf-8").read()
    x = re.sub(r"<\?xml[^>]*\?>\s*", "", x, count=1)
    return x.strip()


def zippa(cartella_addon, dentro_zip_root, dest_zip):
    os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
    base = os.path.dirname(cartella_addon)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for radice, _dirs, files in os.walk(cartella_addon):
            if ESCLUDI.search(radice):
                continue
            for f in files:
                p = os.path.join(radice, f)
                if ESCLUDI.search(p):
                    continue
                arc = os.path.join(dentro_zip_root,
                                   os.path.relpath(p, base))
                z.write(p, arc)


def crea_repository_addon(dst):
    """L'addon `repository.videoteca`: dice a Kodi dove trovare gli altri."""
    d = os.path.join(dst, REPO_ADDON_ID)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<addon id="{id}" name="Videoteca di Alessandro (Alcafer)" version="{ver}" provider-name="Alcafer2011">
  <extension point="xbmc.addon.repository" name="Videoteca (Alcafer)">
    <dir>
      <info compressed="false">{raw}/zips/addons.xml</info>
      <checksum>{raw}/zips/addons.xml.md5</checksum>
      <datadir zip="true">{raw}/zips/</datadir>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="it_IT">Aggiornamenti della Videoteca e della sua pelle.</summary>
    <description lang="it_IT">Repository personale: da qui Kodi aggiorna da solo plugin.video.saghe e skin.saghe.</description>
    <platform>all</platform>
  </extension>
</addon>
""".format(id=REPO_ADDON_ID, ver=REPO_ADDON_VER, raw=RAW)
    open(os.path.join(d, "addon.xml"), "w", encoding="utf-8").write(xml)
    return d


def main():
    dst_repo = (sys.argv[1] if len(sys.argv) > 1
                else os.path.expanduser("~/" + REPO))
    if not os.path.isdir(dst_repo):
        print("NON trovo la cartella del repo:", dst_repo)
        print("Clona prima:  git clone https://github.com/%s/%s.git"
              % (UTENTE, REPO))
        return 1

    zips = os.path.join(dst_repo, "zips")
    os.makedirs(zips, exist_ok=True)

    blocchi = []
    fatti = []

    # 1) gli addon veri, dal Kodi del PC
    for aid in DA_IMPACCHETTARE:
        src = os.path.join(KODI_ADDONS, aid)
        if not os.path.isdir(src):
            print("  SALTO %s: non c'e' in %s" % (aid, KODI_ADDONS))
            continue
        ver = versione(src)
        dest = os.path.join(zips, aid, "%s-%s.zip" % (aid, ver))
        zippa(src, aid, dest)
        blocchi.append(blocco_addon_xml(src))
        fatti.append((aid, ver, dest))
        print("  %-22s v%s  ->  %s" % (aid, ver, os.path.relpath(dest, dst_repo)))

    # 2) l'addon repository
    rep_dir = crea_repository_addon(zips)
    dest = os.path.join(zips, REPO_ADDON_ID,
                        "%s-%s.zip" % (REPO_ADDON_ID, REPO_ADDON_VER))
    zippa(rep_dir, REPO_ADDON_ID, dest)
    blocchi.append(blocco_addon_xml(rep_dir))
    fatti.append((REPO_ADDON_ID, REPO_ADDON_VER, dest))
    print("  %-22s v%s  ->  %s" % (REPO_ADDON_ID, REPO_ADDON_VER,
                                   os.path.relpath(dest, dst_repo)))

    # 3) addons.xml + md5
    axml = ('<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'
            + "\n".join(blocchi) + "\n</addons>\n")
    open(os.path.join(zips, "addons.xml"), "w", encoding="utf-8").write(axml)
    md5 = hashlib.md5(axml.encode("utf-8")).hexdigest()
    open(os.path.join(zips, "addons.xml.md5"), "w", encoding="utf-8").write(md5)
    print("\n  addons.xml + .md5 scritti (%d addon).\n" % len(blocchi))

    print("ADESSO:")
    print("  cd %s" % dst_repo)
    print('  git add -A && git commit -m "repo aggiornato" && git push')
    print("\nLA PRIMA VOLTA, su ogni Kodi:")
    print("  Add-on > Installa da file zip > la cartella del repo >")
    print("  zips/%s/%s-%s.zip" % (REPO_ADDON_ID, REPO_ADDON_ID, REPO_ADDON_VER))
    print("  poi: Installa da repository > Videoteca (Alcafer)")
    print("\nPER AGGIORNARE in futuro: alza `version=` in addon.xml del")
    print("plugin (o della skin), rilancia questo script, git push. Kodi")
    print("prende la versione nuova da solo entro ~un giorno.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
