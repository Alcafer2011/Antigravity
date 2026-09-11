# -*- coding: utf-8 -*-
"""SERVI: installa la Videoteca INTERA (e il suo guardiano) sugli apparecchi.

PERCHE' (11/09/2026)
    Il box girava con main.py nuovo sopra moduli vecchi della 1.0.0: si
    copiavano "solo i file cambiati" e qualcuno restava indietro. Ogni riga
    della home cadeva con ImportError. Qui si installa SEMPRE tutto, si
    controlla file per file, e si guarda il registro dopo il riavvio.

COSA FA, per ogni apparecchio
    0. PROVE sul PC (se una fallisce non si installa niente):
       compilazione, pyflakes (nomi non definiti), banco di prova 92+8
    1. impronte.json: l'md5 di ogni file, che il guardiano usa per accorgersi
       di un'installazione a meta'
    2. Kodi fermato (sul box: prima si sveglia, a TV spenta resta a meta')
    3. le cartelle vecchie di plugin.video.saghe e del guardiano SPOSTATE in
       un backup FUORI da addons/ (un backup dentro addons/ puo' essere
       eseguito al posto del nuovo), poi l'add-on nuovo estratto intero
    4. sul box: chown all'utente di Kodi (copiati con su restano di root e
       Kodi non li legge)
    5. menu della home di Arctic Zephyr, .hash tolto
    6. backup estranei dentro addons/ spostati fuori
    7. add-on accesi nel database (copiati a mano restano spenti)
    8. md5 controllati sull'apparecchio
    9. Kodi riavviato, 70 secondi, e il registro NUOVO letto: errori Python
       della Videoteca = installazione non riuscita
   10. sul box: di nuovo in standby

USO
    python servi.py pc | box | pi | tutti   [--senza-riavvio]
"""

import compileall
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(QUI, "atlante"))
import raccolta as R      # noqa: E402  percorsi, adb, password del Raspberry
import kodi as K          # noqa: E402  lettura degli errori Python dal registro

ADDON = os.path.join(QUI, "plugin.video.saghe")
GUARDIANO = os.path.join(QUI, "service.videoteca.guardiano")
MENU = os.path.join(QUI, "menu-arctic")
DA_INSTALLARE = ("plugin.video.saghe", "service.videoteca.guardiano")
# repository.videoteca: senza, gli aggiornamenti automatici non arrivano. L'11/09
# era SPENTO sul Raspberry e mai registrato sul box.
DA_ACCENDERE = ("plugin.video.saghe", "service.videoteca.guardiano", "skin.arctic.zephyr.mod",
                "script.skinshortcuts", "script.embuary.helper", "script.embuary.info",
                "plugin.video.themoviedb.helper", "repository.videoteca")
ORA = time.strftime("%Y%m%d-%H%M%S")
SCARTA = re.compile(r"(__pycache__|\.pyc$|\.pyo$|\.bak|prima-|\.prima|\.tmp$)")
BACKUP_ESTRANEI = re.compile(r"(bak|prima|backup|\.old$|copia)", re.I)


def titolo(t):
    print("\n=== %s" % t)


# --------------------------------------------------------------------------
# 0-1. PROVE E PACCHETTO
# --------------------------------------------------------------------------

def prove():
    titolo("PROVE")
    for cart in (ADDON, GUARDIANO):
        if not compileall.compile_dir(cart, quiet=1, legacy=False):
            raise SystemExit("compilazione fallita: %s" % cart)
    print("  compilazione ok")
    r = subprocess.run([sys.executable, "-m", "pyflakes", ADDON, GUARDIANO], capture_output=True, text=True)
    nomi = [x for x in r.stdout.splitlines() if "undefined name" in x]
    if nomi:
        raise SystemExit("nomi non definiti:\n" + "\n".join(nomi))
    print("  pyflakes: nessun nome non definito")
    banco = os.path.join(QUI, "banco-saghe")
    for prova in ("prova_menu.py", "prova_servizio.py"):
        r = subprocess.run([sys.executable, prova], cwd=banco, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        esito = [x for x in r.stdout.splitlines() if "prove su" in x]
        if r.returncode != 0:
            fallite = [x for x in r.stdout.splitlines() if "FALLITA" in x]
            raise SystemExit("banco di prova %s NON superato:\n%s" % (prova, "\n".join(fallite) or r.stderr[-800:]))
        print("  %s: %s" % (prova, esito[-1].strip() if esito else "ok"))


def _versione(cartella):
    with io.open(os.path.join(cartella, "addon.xml"), encoding="utf-8") as f:
        m = re.search(r'<addon\b[^>]*\bversion="([^"]+)"', f.read())
    return m.group(1) if m else "?"


def _file(cartella):
    for radice, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            p = os.path.join(radice, f)
            rel = os.path.relpath(p, cartella).replace("\\", "/")
            if not SCARTA.search(rel):
                yield p, rel


def prepara():
    titolo("PACCHETTO")
    impronte = {}
    for p, rel in _file(ADDON):
        if rel == "resources/impronte.json":
            continue
        with open(p, "rb") as h:
            impronte[rel] = hashlib.md5(h.read()).hexdigest()
    with io.open(os.path.join(ADDON, "resources", "impronte.json"), "w", encoding="utf-8") as f:
        json.dump({"versione": _versione(ADDON), "file": impronte}, f, ensure_ascii=False, indent=0, sort_keys=True)
    scorta = os.path.join(GUARDIANO, "resources", "menu")
    os.makedirs(scorta, exist_ok=True)
    for f in os.listdir(MENU):
        shutil.copyfile(os.path.join(MENU, f), os.path.join(scorta, f))
    tar = os.path.join(tempfile.gettempdir(), "servi-%s.tar" % ORA)
    with tarfile.open(tar, "w") as t:
        for cart, aid in ((ADDON, "plugin.video.saghe"), (GUARDIANO, "service.videoteca.guardiano")):
            for p, rel in _file(cart):
                t.add(p, arcname="%s/%s" % (aid, rel))
    print("  Videoteca %s: %d file   guardiano %s   menu %d file   pacchetto %d KB"
          % (_versione(ADDON), len(impronte), _versione(GUARDIANO), len(os.listdir(MENU)), os.path.getsize(tar) // 1024))
    return tar, impronte


def _accendi_nel_db(percorso_db, presenti):
    c = sqlite3.connect(percorso_db)
    fatti = []
    for aid in DA_ACCENDERE:
        if aid not in presenti:
            continue
        c.execute("UPDATE installed SET enabled=1, disabledReason=0 WHERE addonID=?", (aid,))
        c.execute("INSERT INTO installed (addonID, enabled, installDate, origin, disabledReason) "
                  "SELECT ?, 1, datetime('now'), '', 0 WHERE NOT EXISTS (SELECT 1 FROM installed WHERE addonID=?)", (aid, aid))
        fatti.append(aid)
    c.commit()
    c.close()
    return fatti


def _errori_nel_registro(testo_log):
    cart = tempfile.mkdtemp(prefix="servi-log-")
    with io.open(os.path.join(cart, "kodi.log"), "w", encoding="utf-8") as f:
        f.write(testo_log)
    reg = K._registro(cart)
    shutil.rmtree(cart, ignore_errors=True)
    nostri = [e for e in reg["errori_python"] if e["addon"] in DA_INSTALLARE]
    return nostri, reg["errori_python"]


def _rapporto_registro(testo_log):
    nostri, tutti = _errori_nel_registro(testo_log)
    if nostri:
        print("  ERRORI DELLA VIDEOTECA DOPO IL RIAVVIO:")
        for e in nostri:
            print("    %s x%d  %s  (%s)" % (e["tipo"], e["volte"], e["contenuto"][:120], e["dove"]))
    else:
        print("  registro nuovo: nessun errore Python della Videoteca (%d di altri add-on)" % len(tutti))
    return not nostri


def _confronta(md5_remoti, impronte):
    mancanti = [f for f in impronte if f not in md5_remoti]
    diversi = [f for f in impronte if f in md5_remoti and md5_remoti[f] != impronte[f]]
    print("  md5 sull'apparecchio: %d file, mancanti %d, diversi %d" % (len(impronte), len(mancanti), len(diversi)))
    for f in (mancanti + diversi)[:10]:
        print("    ! %s" % f)
    return not mancanti and not diversi


# --------------------------------------------------------------------------
# PC
# --------------------------------------------------------------------------

def _rpc(metodo, params=None, tempo=5):
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}}).encode()
    try:
        r = urllib.request.Request("http://127.0.0.1:8080/jsonrpc", corpo, {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(r, timeout=tempo)).get("result")
    except Exception:
        return None


def _kodi_pc_acceso():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq kodi.exe"], capture_output=True, text=True)
    return "kodi.exe" in r.stdout.lower()


def servi_pc(tar, impronte, riavvia=True):
    titolo("PC (banco)")
    kodi = os.path.expandvars(r"%APPDATA%\Kodi")
    addons = os.path.join(kodi, "addons")
    backup = os.path.join(kodi, "backup-addon", ORA)
    if _kodi_pc_acceso():
        _rpc("Application.Quit")
        for _ in range(30):
            time.sleep(1)
            if not _kodi_pc_acceso():
                break
        else:
            subprocess.run(["taskkill", "/IM", "kodi.exe", "/F"], capture_output=True)
            time.sleep(3)
    print("  Kodi fermo")
    os.makedirs(backup, exist_ok=True)
    for aid in DA_INSTALLARE:
        if os.path.isdir(os.path.join(addons, aid)):
            shutil.move(os.path.join(addons, aid), os.path.join(backup, aid))
    for d in os.listdir(addons):
        if BACKUP_ESTRANEI.search(d):
            shutil.move(os.path.join(addons, d), os.path.join(backup, d))
            print("  spostato fuori da addons/: %s" % d)
    with tarfile.open(tar) as t:
        t.extractall(addons)
    menu = os.path.join(kodi, "userdata", "addon_data", "script.skinshortcuts")
    os.makedirs(menu, exist_ok=True)
    for f in os.listdir(MENU):
        shutil.copyfile(os.path.join(MENU, f), os.path.join(menu, f))
    for f in os.listdir(menu):
        if f.endswith(".hash"):
            os.remove(os.path.join(menu, f))
    dbdir = os.path.join(kodi, "userdata", "Database")
    db = sorted((f for f in os.listdir(dbdir) if re.match(r"Addons\d+\.db$", f)), key=lambda f: int(re.findall(r"\d+", f)[0]))[-1]
    print("  accesi nel database: %s" % ", ".join(_accendi_nel_db(os.path.join(dbdir, db), set(os.listdir(addons)))))
    remoti = {}
    for p, rel in _file(os.path.join(addons, "plugin.video.saghe")):
        with open(p, "rb") as h:
            remoti[rel] = hashlib.md5(h.read()).hexdigest()
    ok = _confronta(remoti, impronte)
    print("  backup: %s" % backup)
    if riavvia:
        subprocess.Popen([r"C:\Program Files\Kodi\kodi.exe"])
        for _ in range(90):
            time.sleep(1)
            if _rpc("JSONRPC.Ping", tempo=2) == "pong":
                break
        time.sleep(5)
        _rpc("Input.ExecuteAction", {"action": "togglefullscreen"})   # il banco resta SEMPRE in finestra
        time.sleep(65)
        with io.open(os.path.join(kodi, "kodi.log"), encoding="utf-8", errors="replace") as f:
            ok = _rapporto_registro(f.read()) and ok
    return ok


# --------------------------------------------------------------------------
# BOX 8K
# --------------------------------------------------------------------------

def _su(comando, tempo=300):
    R._adb_pronto()
    return R._adb("shell", "su -c \"%s\"" % comando, tempo=tempo)


def servi_box(tar, impronte, riavvia=True):
    titolo("BOX 8K")
    if not R._adb_pronto():
        print("  il box non risponde ad adb: saltato")
        return False
    k = R.BOX_KODI
    bk = "/sdcard/backup-addon-%s" % ORA
    proprietario = _su("stat -c %%U:%%G %s/addons" % k).strip() or "u0_a106:u0_a106"
    R._adb("push", tar, "/sdcard/servi.tar", tempo=900)
    print("  pacchetto sul box")
    if riavvia:
        R._adb("shell", "input keyevent KEYCODE_WAKEUP")
        time.sleep(10)
    R._adb_pronto()
    R._adb("shell", "am force-stop org.xbmc.kodi")
    time.sleep(4)
    print("  Kodi fermo")
    _su("mkdir -p %s" % bk)
    for aid in DA_INSTALLARE:
        _su("[ -d %s/addons/%s ] && mv %s/addons/%s %s/ ; true" % (k, aid, k, aid, bk))
    for d in _su("ls -a %s/addons" % k).split():
        if d not in (".", "..") and BACKUP_ESTRANEI.search(d):
            _su("mv '%s/addons/%s' %s/" % (k, d, bk))
            print("  spostato fuori da addons/: %s" % d)
    esito = _su("cd %s/addons && tar -xf /sdcard/servi.tar && rm /sdcard/servi.tar && chown -R %s %s && echo estratto"
                % (k, proprietario, " ".join(DA_INSTALLARE)))
    print("  %s (proprietario %s)" % ("add-on estratti" if "estratto" in esito else "ESTRAZIONE NON RIUSCITA: " + esito[-200:], proprietario))
    # TUTTO a Kodi, non solo quello appena copiato: l'11/09 repository.videoteca (root:root 770)
    # era invisibile a Kodi da giorni, e con lui gli aggiornamenti automatici; anche il canale
    # lesaghe.py dentro s4me non era di Kodi. Un chown qui costa due secondi.
    estranei = _su("cd %s/addons && find . ! -user %s 2>/dev/null | wc -l" % (k, proprietario.split(":")[0])).strip()
    _su("chown -R %s %s/addons %s/userdata/addon_data" % (proprietario, k, k), tempo=900)
    print("  ridati a Kodi addons/ e addon_data/ (file non suoi prima: %s)" % estranei)
    menu = "%s/userdata/addon_data/script.skinshortcuts" % k
    _su("mkdir -p %s && cp %s/addons/service.videoteca.guardiano/resources/menu/* %s/ && rm -f %s/*.hash && chown -R %s %s"
        % (menu, k, menu, menu, proprietario, menu))
    print("  menu della home copiato")
    db = _su("ls %s/userdata/Database | grep -E '^Addons[0-9]+\\.db$' | sort | tail -n 1" % k).strip()
    locale = os.path.join(tempfile.gettempdir(), "servi-box-%s" % db)
    _su("cp %s/userdata/Database/%s /sdcard/servi.db" % (k, db))
    R._adb("pull", "/sdcard/servi.db", locale)
    presenti = set(_su("ls %s/addons" % k).split())
    print("  accesi nel database %s: %s" % (db, ", ".join(_accendi_nel_db(locale, presenti))))
    R._adb("push", locale, "/sdcard/servi.db")
    _su("cp /sdcard/servi.db %s/userdata/Database/%s && chown %s %s/userdata/Database/%s && rm /sdcard/servi.db"
        % (k, db, proprietario, k, db))
    righe = _su("cd %s/addons/plugin.video.saghe && find . -type f ! -path '*__pycache__*' -exec md5sum {} +" % k, tempo=600)
    remoti = {}
    for r in righe.splitlines():
        parti = r.split(None, 1)
        if len(parti) == 2:
            remoti[parti[1].strip().lstrip("./")] = parti[0]
    ok = _confronta(remoti, impronte)
    print("  backup: %s" % bk)
    if riavvia:
        R._adb("shell", "monkey -p org.xbmc.kodi -c android.intent.category.LAUNCHER 1")
        time.sleep(75)
        _su("cp %s/temp/kodi.log /sdcard/servi-kodi.log" % k)
        log_locale = os.path.join(tempfile.gettempdir(), "servi-box-kodi.log")
        R._adb("pull", "/sdcard/servi-kodi.log", log_locale)
        _su("rm -f /sdcard/servi-kodi.log")
        with io.open(log_locale, encoding="utf-8", errors="replace") as f:
            ok = _rapporto_registro(f.read()) and ok
        R._adb("shell", "input keyevent KEYCODE_SLEEP")
        print("  box di nuovo in standby")
    return ok


# --------------------------------------------------------------------------
# RASPBERRY
# --------------------------------------------------------------------------

def servi_pi(tar, impronte, riavvia=True):
    import paramiko
    titolo("RASPBERRY")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(R.PI, username="root", password=R._password_pi(), timeout=15)

    def run(cmd, tempo=300):
        _i, o, e = c.exec_command(cmd, timeout=tempo)
        return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

    k = R.PI_KODI
    bk = "/storage/backup-addon/%s" % ORA
    sftp = c.open_sftp()
    sftp.put(tar, "/tmp/servi.tar")
    print("  pacchetto sul Raspberry")
    run("systemctl stop kodi; sleep 3")
    print("  Kodi fermo")
    run("mkdir -p %s" % bk)
    for aid in DA_INSTALLARE:
        run("[ -d %s/addons/%s ] && mv %s/addons/%s %s/ ; true" % (k, aid, k, aid, bk))
    for d in run("ls -a %s/addons" % k).split():
        if d not in (".", "..") and BACKUP_ESTRANEI.search(d):
            run("mv '%s/addons/%s' %s/" % (k, d, bk))
            print("  spostato fuori da addons/: %s" % d)
    esito = run("cd %s/addons && tar -xf /tmp/servi.tar && rm /tmp/servi.tar && echo estratto" % k)
    print("  %s" % ("add-on estratti" if "estratto" in esito else "ESTRAZIONE NON RIUSCITA: " + esito[-200:]))
    menu = "%s/userdata/addon_data/script.skinshortcuts" % k
    run("mkdir -p %s && cp %s/addons/service.videoteca.guardiano/resources/menu/* %s/ && rm -f %s/*.hash" % (menu, k, menu, menu))
    print("  menu della home copiato")
    db = run("ls %s/userdata/Database | grep -E '^Addons[0-9]+\\.db$' | sort | tail -n 1" % k).strip()
    locale = os.path.join(tempfile.gettempdir(), "servi-pi-%s" % db)
    sftp.get("%s/userdata/Database/%s" % (k, db), locale)
    presenti = set(run("ls %s/addons; ls /usr/share/kodi/addons" % k).split())
    print("  accesi nel database %s: %s" % (db, ", ".join(_accendi_nel_db(locale, presenti))))
    sftp.put(locale, "%s/userdata/Database/%s" % (k, db))
    righe = run("cd %s/addons/plugin.video.saghe && find . -type f ! -path '*__pycache__*' -exec md5sum {} +" % k, tempo=600)
    remoti = {}
    for r in righe.splitlines():
        parti = r.split(None, 1)
        if len(parti) == 2:
            remoti[parti[1].strip().lstrip("./")] = parti[0]
    ok = _confronta(remoti, impronte)
    print("  backup: %s" % bk)
    if riavvia:
        run("systemctl start kodi")
        time.sleep(70)
        log_locale = os.path.join(tempfile.gettempdir(), "servi-pi-kodi.log")
        sftp.get("%s/temp/kodi.log" % k, log_locale)
        with io.open(log_locale, encoding="utf-8", errors="replace") as f:
            ok = _rapporto_registro(f.read()) and ok
    else:
        run("systemctl start kodi")
    sftp.close()
    c.close()
    return ok


# --------------------------------------------------------------------------
# DIPENDENZE MANCANTI (dal repository ufficiale)
# --------------------------------------------------------------------------

def _codice_kodi(versione):
    return {"19": "matrix", "20": "nexus", "21": "omega", "22": "piers"}.get((versione or "").split(".")[0], "omega")


def _accendi_ids(percorso_db, ids):
    c = sqlite3.connect(percorso_db)
    for aid in ids:
        c.execute("UPDATE installed SET enabled=1, disabledReason=0 WHERE addonID=?", (aid,))
        c.execute("INSERT INTO installed (addonID, enabled, installDate, origin, disabledReason) "
                  "SELECT ?, 1, datetime('now'), 'repository.xbmc.org', 0 WHERE NOT EXISTS "
                  "(SELECT 1 FROM installed WHERE addonID=?)", (aid, aid))
    c.commit()
    c.close()


def dipendenze(app):
    """Installa le dipendenze che l'atlante trova ROTTE su un apparecchio.

    Solo quelle vere: le "forse di sistema" (binari e moduli che viaggiano con
    Kodi) non si toccano. Si scaricano dal repository UFFICIALE nella versione
    di Kodi dell'apparecchio, e si installano solo le cartelle che mancano: un
    modulo gia' presente non si sovrascrive (lo usano altri add-on).
    """
    import importlib.util
    titolo("DIPENDENZE %s" % app.upper())
    p = os.path.join(QUI, "atlante", "uscita", "atlante.json")
    if not os.path.exists(p):
        raise SystemExit("prima: python atlante/atlante.py raccogli %s && python atlante/atlante.py analizza" % app)
    with io.open(p, encoding="utf-8") as f:
        dati = json.load(f)["dati"]["apparecchi"][app]
    ids = sorted({d["dipendenza"] for d in dati.get("dipendenze_rotte", []) if "forse" not in d["problema"]})
    if not ids:
        print("  nessuna dipendenza rotta")
        return True
    versione = _codice_kodi((dati.get("manifesto") or {}).get("kodi"))
    spec = importlib.util.spec_from_file_location("installa_skin", os.path.join(QUI, "installa-skin.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    appoggio = tempfile.mkdtemp(prefix="servi-dip-")
    for aid in ids:
        mod.installa(aid, versione, appoggio)
    presenti = set(dati.get("addons") or {})
    nuovi = sorted(d for d in os.listdir(appoggio) if os.path.isdir(os.path.join(appoggio, d)) and d not in presenti)
    print("  %s (Kodi %s): rotte %s -> da installare %s" % (app, versione, ", ".join(ids), ", ".join(nuovi) or "niente"))
    if not nuovi:
        return True
    tar = os.path.join(tempfile.gettempdir(), "servi-dip-%s-%s.tar" % (app, ORA))
    with tarfile.open(tar, "w") as t:
        for d in nuovi:
            t.add(os.path.join(appoggio, d), arcname=d)
    shutil.rmtree(appoggio, ignore_errors=True)
    if app == "box":
        k = R.BOX_KODI
        proprietario = _su("stat -c %%U:%%G %s/addons" % k).strip() or "u0_a106:u0_a106"
        R._adb("push", tar, "/sdcard/servi-dip.tar", tempo=900)
        R._adb("shell", "input keyevent KEYCODE_WAKEUP")
        time.sleep(10)
        R._adb_pronto()
        R._adb("shell", "am force-stop org.xbmc.kodi")
        time.sleep(4)
        print("  " + _su("cd %s/addons && tar -xf /sdcard/servi-dip.tar && rm /sdcard/servi-dip.tar && chown -R %s %s && echo installati"
                         % (k, proprietario, " ".join(nuovi))))
        _su("chown -R %s %s/addons %s/userdata/addon_data" % (proprietario, k, k), tempo=900)   # tutto a Kodi (11/09)
        db = _su("ls %s/userdata/Database | grep -E '^Addons[0-9]+\\.db$' | sort | tail -n 1" % k).strip()
        locale = os.path.join(tempfile.gettempdir(), "servi-dip-box-%s" % db)
        _su("cp %s/userdata/Database/%s /sdcard/servi.db" % (k, db))
        R._adb("pull", "/sdcard/servi.db", locale)
        _accendi_ids(locale, nuovi)
        R._adb("push", locale, "/sdcard/servi.db")
        _su("cp /sdcard/servi.db %s/userdata/Database/%s && chown %s %s/userdata/Database/%s && rm /sdcard/servi.db"
            % (k, db, proprietario, k, db))
        R._adb("shell", "monkey -p org.xbmc.kodi -c android.intent.category.LAUNCHER 1")
        time.sleep(60)
        R._adb("shell", "input keyevent KEYCODE_SLEEP")
        print("  accesi nel database, Kodi riavviato, box in standby")
    elif app == "pi":
        import paramiko
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(R.PI, username="root", password=R._password_pi(), timeout=15)

        def run(cmd):
            _i, o, e = c.exec_command(cmd, timeout=300)
            return (o.read().decode() + e.read().decode()).strip()
        sftp = c.open_sftp()
        sftp.put(tar, "/tmp/servi-dip.tar")
        run("systemctl stop kodi; sleep 3")
        print("  " + run("cd %s/addons && tar -xf /tmp/servi-dip.tar && rm /tmp/servi-dip.tar && echo installati" % R.PI_KODI))
        db = run("ls %s/userdata/Database | grep -E '^Addons[0-9]+\\.db$' | sort | tail -n 1" % R.PI_KODI).strip()
        locale = os.path.join(tempfile.gettempdir(), "servi-dip-pi-%s" % db)
        sftp.get("%s/userdata/Database/%s" % (R.PI_KODI, db), locale)
        _accendi_ids(locale, nuovi)
        sftp.put(locale, "%s/userdata/Database/%s" % (R.PI_KODI, db))
        run("systemctl start kodi")
        sftp.close()
        c.close()
        print("  accesi nel database, Kodi riavviato")
    os.remove(tar)
    return True


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) > 1 and argv[1] == "dipendenze":
        # python servi.py dipendenze box pi
        return 0 if all([dipendenze(a) for a in (argv[2:] or ["box", "pi"])]) else 1
    riavvia = "--senza-riavvio" not in argv
    dove = [a for a in argv[1:] if not a.startswith("--")] or ["tutti"]
    if "tutti" in dove:
        dove = ["pc", "box", "pi"]
    prove()
    tar, impronte = prepara()
    esiti = {}
    for app in dove:
        try:
            esiti[app] = {"pc": servi_pc, "box": servi_box, "pi": servi_pi}[app](tar, impronte, riavvia)
        except Exception as e:
            print("  %s NON RIUSCITO: %s" % (app, e))
            esiti[app] = False
    os.remove(tar)
    titolo("ESITO")
    for app, ok in esiti.items():
        print("  %-4s %s" % (app, "OK" if ok else "DA CONTROLLARE"))
    return 0 if all(esiti.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
