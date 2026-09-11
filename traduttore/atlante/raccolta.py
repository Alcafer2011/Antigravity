# -*- coding: utf-8 -*-
"""RACCOLTA: copia sul PC i file di testo di Kodi dai tre apparecchi di casa.

PERCHE'
    Ogni analisi fatta "dal vivo" sugli apparecchi costa minuti, contesto e
    rischi (adb che cade quando il box si sveglia, la password dell'API, il
    filtro dei comandi). Qui si copia UNA volta tutto il testo che conta, e
    le analisi girano sulla copia, offline, quante volte si vuole.

COSA COPIA
    - add-on di SISTEMA (quelli che viaggiano con Kodi: script.module.pil,
      skin.estuary...) dove si possono leggere: PC e Raspberry. Sul box
      Android stanno dentro l'APK e non si leggono; sul Raspberry quelli
      BINARI (inputstream, pvr...) stanno in /usr/lib/kodi e non si copiano.
    - add-on INSTALLATI, dati degli add-on e impostazioni (userdata)
    - TUTTI i database degli add-on (Addons*.db), qualunque sia la misura:
      al primo giro (11/09/2026) il limite dei 3 MB aveva scartato proprio
      Addons33.db e l'analisi aveva letto un Addons27.db vecchio di mesi
    - i registri kodi.log e kodi.old.log, sempre
    Solo testo (.py .xml .json .txt .md .po it/en): niente immagini, niente
    cache, niente miniature.

DOVE
    traduttore/atlante/copie/<pc|box|pi>/
        sistema/   addons/   userdata/   log/
    e copie/<apparecchio>/manifesto.json con data, versione di Kodi, numeri.
"""

import glob
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
ANTIGRAVITY = os.path.abspath(os.path.join(QUI, "..", ".."))
COPIE = os.path.join(QUI, "copie")

ESTENSIONI = (".py", ".xml", ".json", ".txt", ".md", ".po", ".xsp", ".properties", ".hash")
LINGUE_BUONE = ("resource.language.it_it", "resource.language.en_gb")
MAX_BYTE = 3 * 1024 * 1024
SALTA_CARTELLE = ("__pycache__", "Thumbnails", "packages", "temp", "cache",
                  "archive_cache", "Savestates", ".git")

ADB = r"C:/rpi_backup/platform-tools/adb.exe"
BOX = "192.168.1.114:5555"
BOX_KODI = "/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi"
PI = "192.168.1.105"
PI_KODI = "/storage/.kodi"


def _buono(percorso, dimensione):
    p = percorso.replace("\\", "/")
    low = p.lower()
    if low.endswith(".db"):
        return os.path.basename(low).startswith("addons")
    if dimensione > MAX_BYTE:
        return False
    if any("/%s/" % c in "/" + p + "/" for c in SALTA_CARTELLE):
        return False
    if "resource.language." in low and not any(l in low for l in LINGUE_BUONE):
        return False
    if low.endswith(".po") and "/language/" in low and \
            not re.search(r"(it_it|en_gb|italian|english)", low):
        return False
    return low.endswith(ESTENSIONI)


def _svuota(cartella):
    if os.path.isdir(cartella):
        shutil.rmtree(cartella)
    os.makedirs(cartella, exist_ok=True)


def _versione_da_log(cartella_log):
    for nome in ("kodi.log", "kodi.old.log"):
        p = os.path.join(cartella_log, nome)
        if os.path.exists(p):
            with io.open(p, encoding="utf-8", errors="replace") as f:
                for i, riga in enumerate(f):
                    m = re.search(r"Starting Kodi \(([^)]+)\)", riga)
                    if m:
                        return m.group(1).strip()
                    if i > 400:
                        break
    return ""


def _manifesto(app, dest, note, extra=None):
    conta = {}
    for sotto in ("sistema", "addons", "userdata", "log"):
        n = 0
        for _r, _d, files in os.walk(os.path.join(dest, sotto)):
            n += len(files)
        conta[sotto] = n
    m = {"apparecchio": app, "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
         "kodi": _versione_da_log(os.path.join(dest, "log")),
         "file": conta, "note": note,
         "database": sorted(os.path.basename(p) for p in glob.glob(os.path.join(dest, "userdata", "Database", "Addons*.db")))}
    m.update(extra or {})
    with io.open(os.path.join(dest, "manifesto.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    return m


# --------------------------------------------------------------------------
# PC
# --------------------------------------------------------------------------

def _copia_locale(sorgente, dest):
    n = 0
    for radice, dirs, files in os.walk(sorgente):
        dirs[:] = [d for d in dirs if d not in SALTA_CARTELLE]
        for f in files:
            p = os.path.join(radice, f)
            try:
                dim = os.path.getsize(p)
            except OSError:
                continue
            rel = os.path.relpath(p, sorgente)
            if not _buono(rel, dim):
                continue
            q = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(q), exist_ok=True)
            try:
                shutil.copyfile(p, q)
                n += 1
            except OSError:
                pass
    return n


def raccogli_pc():
    dest = os.path.join(COPIE, "pc")
    _svuota(dest)
    appdata = os.path.expandvars(r"%APPDATA%\Kodi")
    _copia_locale(r"C:\Program Files\Kodi\addons", os.path.join(dest, "sistema"))
    _copia_locale(os.path.join(appdata, "addons"), os.path.join(dest, "addons"))
    _copia_locale(os.path.join(appdata, "userdata"), os.path.join(dest, "userdata"))
    os.makedirs(os.path.join(dest, "log"), exist_ok=True)
    for nome in ("kodi.log", "kodi.old.log"):
        p = os.path.join(appdata, nome)
        if os.path.exists(p):
            shutil.copyfile(p, os.path.join(dest, "log", nome))
    return _manifesto("pc", dest, "Kodi sul PC Windows, banco di prova")


# --------------------------------------------------------------------------
# BOX 8K (Android, adb + su)
# --------------------------------------------------------------------------

def _adb(*argomenti, tempo=300):
    r = subprocess.run([ADB, "-s", BOX] + list(argomenti), capture_output=True,
                       text=True, timeout=tempo)
    return (r.stdout + r.stderr).strip()


def _adb_pronto(secondi=90):
    """adb cade quando il box si sveglia (ricollega la WiFi): si riprova."""
    fine = time.time() + secondi
    while time.time() < fine:
        subprocess.run([ADB, "connect", BOX], capture_output=True, timeout=20)
        try:
            if _adb("shell", "echo pronto", tempo=15) == "pronto":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def _find_espressione():
    nomi = " -o ".join("-name '*%s'" % e for e in ESTENSIONI)
    return "\\( %s \\)" % nomi


def _estrai_tar(percorso_tar, dest, mappa):
    """Estrae l'archivio mettendo ogni radice remota nella sua sottocartella."""
    n = 0
    with tarfile.open(percorso_tar) as t:
        for m in t.getmembers():
            if not m.isfile():
                continue
            nome = m.name.lstrip("./")
            for prefisso, sotto in mappa:
                if nome.startswith(prefisso):
                    rel = nome[len(prefisso):].lstrip("/")
                    # I REGISTRI SI PRENDONO SEMPRE: .log non e' fra le
                    # estensioni e con il debug acceso superano i 3 MB.
                    if sotto != "log" and not _buono(rel, m.size):
                        break
                    q = os.path.join(dest, sotto, rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(q), exist_ok=True)
                    with t.extractfile(m) as sorg, open(q, "wb") as out:
                        shutil.copyfileobj(sorg, out)
                    n += 1
                    break
    return n


def raccogli_box():
    dest = os.path.join(COPIE, "box")
    if not _adb_pronto():
        raise RuntimeError("il box non risponde ad adb")
    _svuota(dest)
    espr = _find_espressione()
    cmd = ("cd %s && (find addons userdata -type f %s -size -3000k 2>/dev/null "
           "| grep -v -E '/(__pycache__|Thumbnails|packages|temp)/'; "
           "ls userdata/Database/Addons*.db temp/kodi.log temp/kodi.old.log 2>/dev/null) > /sdcard/atlante.lista; "
           "tar -cf /sdcard/atlante.tar -T /sdcard/atlante.lista && echo ok" % (BOX_KODI, espr))
    esito = _adb("shell", "su -c \"%s\"" % cmd, tempo=600)
    if "ok" not in esito:
        raise RuntimeError("tar sul box non riuscito: %s" % esito[-300:])
    locale = os.path.join(COPIE, "box.tar")
    _adb_pronto()
    _adb("pull", "/sdcard/atlante.tar", locale, tempo=900)
    _adb("shell", "su -c 'rm -f /sdcard/atlante.tar /sdcard/atlante.lista'")
    _estrai_tar(locale, dest, [("addons/", "addons"), ("userdata/", "userdata"),
                               ("temp/", "log")])
    os.remove(locale)
    # Chi possiede i file di Kodi: quello che si copia con su resta di root e
    # Kodi non lo legge (11/09/2026). Serve al ricettario per il chown.
    proprietario = _adb("shell", "su -c 'stat -c %%U:%%G %s/addons'" % BOX_KODI).strip()
    # File che Kodi non possiede: se i permessi non lo lasciano leggere, per Kodi
    # quell'add-on NON ESISTE e nessun registro lo dice (repository.videoteca, 11/09).
    utente = proprietario.split(":")[0] or "u0_a106"
    non_di_kodi = _adb("shell", "su -c \"cd %s && find addons userdata/addon_data ! -user %s 2>/dev/null | head -n 300\""
                       % (BOX_KODI, utente)).split()
    return _manifesto("box", dest, "Box 8K Android: gli add-on di sistema stanno nell'APK e non sono copiati",
                      {"proprietario_file_kodi": proprietario, "non_di_kodi": non_di_kodi})


# --------------------------------------------------------------------------
# RASPBERRY (LibreELEC, SSH)
# --------------------------------------------------------------------------

def _password_pi():
    with io.open(os.path.join(ANTIGRAVITY, "src", ".salotto-ssh"), encoding="utf-8") as f:
        return f.read().strip()


def raccogli_pi():
    import paramiko
    dest = os.path.join(COPIE, "pi")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(PI, username="root", password=_password_pi(), timeout=15)
    _svuota(dest)
    espr = _find_espressione()
    cmd = ("cd / && (find usr/share/kodi/addons storage/.kodi/addons storage/.kodi/userdata "
           "-type f %s -size -3000k 2>/dev/null | grep -v -E '/(__pycache__|Thumbnails|packages|temp)/'; "
           "ls storage/.kodi/userdata/Database/Addons*.db storage/.kodi/temp/kodi.log "
           "storage/.kodi/temp/kodi.old.log 2>/dev/null) "
           "> /tmp/atlante.lista && tar -cf /tmp/atlante.tar -T /tmp/atlante.lista && echo ok" % espr)
    _i, o, e = c.exec_command(cmd, timeout=600)
    esito = o.read().decode() + e.read().decode()
    if "ok" not in esito:
        c.close()
        raise RuntimeError("tar sul Raspberry non riuscito: %s" % esito[-300:])
    _i, o, _e = c.exec_command("ls /usr/lib/kodi/addons 2>/dev/null", timeout=30)
    binari = o.read().decode().split()
    locale = os.path.join(COPIE, "pi.tar")
    sftp = c.open_sftp()
    sftp.get("/tmp/atlante.tar", locale)
    sftp.close()
    c.exec_command("rm -f /tmp/atlante.tar /tmp/atlante.lista")
    c.close()
    _estrai_tar(locale, dest, [("usr/share/kodi/addons/", "sistema"),
                               ("storage/.kodi/addons/", "addons"),
                               ("storage/.kodi/userdata/", "userdata"),
                               ("storage/.kodi/temp/", "log")])
    os.remove(locale)
    return _manifesto("pi", dest, "Raspberry Pi 4, LibreELEC", {"addon_binari_di_sistema": binari})


RACCOGLITORI = {"pc": raccogli_pc, "box": raccogli_box, "pi": raccogli_pi}


def raccogli(apparecchi=("pc", "box", "pi")):
    esiti = {}
    for app in apparecchi:
        inizio = time.time()
        try:
            m = RACCOGLITORI[app]()
            m["secondi"] = round(time.time() - inizio, 1)
            esiti[app] = m
            print("  %-4s ok  %s  kodi %s  db %s  (%.0f s)" % (app, m["file"], m["kodi"] or "?",
                                                              ",".join(m.get("database") or []) or "NESSUNO", m["secondi"]))
        except Exception as ex:
            esiti[app] = {"errore": str(ex)}
            print("  %-4s NON RACCOLTO: %s" % (app, ex))
    return esiti
