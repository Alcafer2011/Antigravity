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
RAW_NUDO = "https://raw.githubusercontent.com/%s/%s/%s" % (UTENTE, REPO, RAMO)

# IL TOKEN, E PERCHE' STA QUI DENTRO
# Il repository su GitHub e' PRIVATO. raw.githubusercontent risponde 404 a
# chi non e' autenticato, e Kodi un 404 non lo racconta a nessuno: gli
# aggiornamenti semplicemente non arrivano mai, in silenzio.
# Il 10/09/2026 questo script ha rigenerato `repository.videoteca/addon.xml`
# SENZA token, cancellando quello buono: lo rimetteva uno script a parte che
# poi e' sparito. Un pezzo indispensabile non puo' stare in uno script che
# ci si deve ricordare di lanciare - sta qui, e se il token manca lo script
# si FERMA invece di pubblicare un repository che non funziona.
FILE_TOKEN = os.path.join(os.path.expanduser("~"), ".videoteca-repo-token")


def _raw():
    try:
        with open(FILE_TOKEN, encoding="utf-8") as f:
            tok = f.read().strip()
    except Exception:
        tok = ""
    if not tok:
        raise SystemExit(
            "MANCA IL TOKEN (%s).\n"
            "Il repository e' privato: senza token gli indirizzi danno 404 e\n"
            "Kodi non aggiorna niente, senza dirlo. Rimetti il file e rilancia."
            % FILE_TOKEN)
    return "https://%s:%s@raw.githubusercontent.com/%s/%s/%s" % (
        UTENTE, tok, UTENTE, REPO, RAMO)


RAW = RAW_NUDO

# DA DOVE: dalla SORGENTE, non piu' dal Kodi del PC (11/09/2026). Il 10/09 il
# PC era rimasto indietro e si stava per pubblicare la versione vecchia senza
# accorgersene. Ora servi.py prova il codice, lo installa e subito dopo lo
# pubblica da qui: quello che arriva col pulsante "Cerca aggiornamenti" e'
# esattamente quello installato. skin.saghe (vecchia, non piu' usata) resta
# presa dal Kodi del PC finche' c'e'.
SORGENTE = os.path.dirname(os.path.abspath(__file__))
KODI_ADDONS = os.path.expandvars(r"%APPDATA%\Kodi\addons")
DA_IMPACCHETTARE = [
    ("plugin.video.saghe", os.path.join(SORGENTE, "plugin.video.saghe")),
    ("service.videoteca.guardiano", os.path.join(SORGENTE, "service.videoteca.guardiano")),
    ("skin.saghe", os.path.join(KODI_ADDONS, "skin.saghe")),
]
TIENI_PACCHETTI = 3

REPO_ADDON_ID = "repository.videoteca"
# 1.0.1 (11/09/2026): senza <checksum>. Sul Raspberry Kodi chiedeva
# addons.xml.md5 SENZA la password del repository privato, riceveva 404 e
# dava tutto il repository per illeggibile ("CRepository: failed read"): gli
# aggiornamenti automatici non arrivavano. Il checksum e' facoltativo: senza,
# Kodi rilegge addons.xml a ogni giro, che pesa 5 KB.
REPO_ADDON_VER = "1.0.1"

ESCLUDI = re.compile(r"\.zip$|(__pycache__|\.pyc$|\.pyo$|\.git|\.bak|\.DS_Store|prima-|\.prima|\.tmp$)")


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
    """Impacchetta un add-on come lo vuole Kodi: UNA cartella col suo nome,
    e dentro `addon.xml`.

    IL GUASTO (trovato il 10/09/2026, e c'era da sempre).
    La base era `os.path.dirname(cartella_addon)`, cioe' la cartella che
    CONTIENE l'add-on. Cosi' `relpath` tornava gia' "plugin.video.saghe/..."
    e, unito a `dentro_zip_root`, veniva fuori
        plugin.video.saghe/plugin.video.saghe/addon.xml
    Kodi cerca `addon.xml` un livello piu' su, non lo trova, e l'installazione
    fallisce. Siccome tutti gli zip pubblicati sono stati fatti da qui,
    **il repository non ha mai potuto installare niente** - e nessuno se n'era
    accorto perche' gli apparecchi li avevo sempre aggiornati copiando i file
    a mano.
    La base giusta e' la cartella dell'add-on stessa.
    """
    os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for radice, _dirs, files in os.walk(cartella_addon):
            if ESCLUDI.search(radice):
                continue
            for f in files:
                p = os.path.join(radice, f)
                if ESCLUDI.search(p):
                    continue
                arc = os.path.join(dentro_zip_root,
                                   os.path.relpath(p, cartella_addon))
                z.write(p, arc.replace("\\", "/"))

    # SI CONTROLLA, non si spera: un pacchetto sbagliato non da' nessun
    # segno finche' qualcuno non prova a installarlo.
    atteso = dentro_zip_root + "/addon.xml"
    with zipfile.ZipFile(dest_zip) as z:
        if atteso not in z.namelist():
            raise SystemExit(
                "PACCHETTO SBAGLIATO: dentro %s non c'e' %s.\n"
                "Kodi cerca addon.xml esattamente li' e senza non installa."
                % (os.path.basename(dest_zip), atteso))


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
      <datadir zip="true">{raw}/zips/</datadir>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="it_IT">Aggiornamenti della Videoteca e della sua pelle.</summary>
    <description lang="it_IT">Repository personale: da qui Kodi aggiorna da solo plugin.video.saghe e skin.saghe.</description>
    <platform>all</platform>
  </extension>
</addon>
""".format(id=REPO_ADDON_ID, ver=REPO_ADDON_VER, raw=_raw())
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
    for aid, src in DA_IMPACCHETTARE:
        if not os.path.isdir(src):
            print("  SALTO %s: non c'e' in %s" % (aid, src))
            continue
        ver = versione(src)
        dest = os.path.join(zips, aid, "%s-%s.zip" % (aid, ver))
        zippa(src, aid, dest)
        # i pacchetti vecchi: se ne tengono pochi, il repository non deve crescere per sempre
        vecchi = sorted((p for p in os.listdir(os.path.dirname(dest)) if p.endswith(".zip")),
                        key=lambda p: os.path.getmtime(os.path.join(os.path.dirname(dest), p)))
        for p in vecchi[:-TIENI_PACCHETTI]:
            os.remove(os.path.join(os.path.dirname(dest), p))
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
