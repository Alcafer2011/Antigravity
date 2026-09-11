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
DA_ACCENDERE = ("plugin.video.saghe", "service.videoteca.guardiano", "inputstream.rtmp", "skin.arctic.zephyr.mod",
                "script.skinshortcuts", "script.embuary.helper", "script.embuary.info",
                "plugin.video.themoviedb.helper", "repository.videoteca",
                # ResolveURL e il suo repository (11/09/2026): vedi _pacchetti_extra
                "repository.resolveurl", "script.module.resolveurl", "script.module.six",
                "script.module.kodi-six", "script.module.pyqrcode")
ORA = time.strftime("%Y%m%d-%H%M%S")
EMBUARY_IT = ('<settings version="2">\n    <setting id="language_code">it</setting>\n'
              '    <setting id="country_code">IT</setting>\n</settings>\n')


def _guisettings_sicure(testo, password=None):
    """Origini sconosciute SPENTE: servono solo per installare uno zip a mano; gli
    aggiornamenti dai repository gia' installati funzionano lo stesso (11/09/2026).
    Con `password` (solo il PC): l'API di Kodi chiede utente e password - box e
    Raspberry ce l'avevano gia', il banco no, e sulla rete di casa chiunque poteva
    comandarlo."""
    import re as _re
    testo = _re.sub(r'<setting id="addons.unknownsources"[^>]*>[^<]*</setting>',
                    '<setting id="addons.unknownsources">false</setting>', testo)
    if password:
        testo = _re.sub(r'<setting id="services.webserverauthentication"[^>]*?(?:/>|>[^<]*</setting>)',
                        '<setting id="services.webserverauthentication">true</setting>', testo)
        testo = _re.sub(r'<setting id="services.webserverpassword"[^>]*?(?:/>|>[^<]*</setting>)',
                        lambda _m: '<setting id="services.webserverpassword">%s</setting>' % password, testo)
    return testo


def _suono_apertura(testo):
    """Il suono di NOVIX all'accensione passa da PlaySFX, cioe' dai suoni
    dell'interfaccia: con "Suoni dell'interfaccia: mai" non si sente. L'11/09/2026
    sul box era cosi' (audiooutput.guisoundmode = 0). Si passa a "solo quando non
    si riproduce" (1) e si toglie la serie di bip dei tasti (lookandfeel.soundskin
    vuoto): il suono dell'apertura si', i bip a ogni tasto no. Se non era "mai",
    non si tocca niente."""
    if not re.search(r'<setting id="audiooutput.guisoundmode"[^>]*>0</setting>', testo):
        return testo
    testo = re.sub(r'<setting id="audiooutput.guisoundmode"[^>]*>0</setting>',
                   '<setting id="audiooutput.guisoundmode">1</setting>', testo)
    return re.sub(r'<setting id="lookandfeel.soundskin"[^>]*?(?:/>|>[^<]*</setting>)',
                  '<setting id="lookandfeel.soundskin"></setting>', testo)


YOUTUBE_PRONTO = {
    "kodion.setup_wizard": "false",
    # YouTube rilancia la procedura se questo numero e' sotto la data della sua
    # uscita (1767970800, vedi setup_wizard_enabled in abstract_settings.py)
    "kodion.setup_wizard.forced_runs": "1767970800",
    "youtube.language": "it-IT",
    "youtube.region": "IT",
}


def _youtube_pronto(attuale):
    """Le impostazioni di YouTube con lingua, regione e procedura gia' fatta."""
    import re as _re
    testo = attuale if "<settings" in attuale else '<settings version="2">\n</settings>\n'
    for chiave, valore in YOUTUBE_PRONTO.items():
        riga = '<setting id="%s">%s</setting>' % (chiave, valore)
        modello = r'<setting id="%s"[^>]*?(?:/>|>[^<]*</setting>)' % _re.escape(chiave)
        if _re.search(modello, testo):
            testo = _re.sub(modello, lambda _m: riga, testo)
        else:
            testo = testo.replace("</settings>", "    %s\n</settings>" % riga)
    return testo


def _embuary_italiano(attuale):
    """settings.xml di Embuary Info con lingua e paese italiani.

    Di fabbrica e' en/US: la "Scheda completa" delle tessere arrivava con la
    trama in inglese (provato sul banco il 10/09/2026). Si tocca solo lingua e
    paese, e senza default="true" (con quello Kodi puo' rimettere il valore di
    fabbrica). Va scritto a Kodi SPENTO: uscendo Kodi riscrive le impostazioni.
    """
    if not attuale or "<settings" not in attuale:
        return EMBUARY_IT
    t = attuale
    for k, v in (("language_code", "it"), ("country_code", "IT")):
        nuovo = '<setting id="%s">%s</setting>' % (k, v)
        if re.search(r'<setting id="%s"' % k, t):
            t = re.sub(r'<setting id="%s"[^>]*/>' % k, nuovo, t)
            t = re.sub(r'<setting id="%s"[^>]*>[^<]*</setting>' % k, nuovo, t)
        else:
            t = t.replace("</settings>", "    %s\n</settings>" % nuovo)
    return t
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


RESOLVEURL_REPO = "https://raw.githubusercontent.com/Gujal00/smrzips/master"
DIPENDENZE_RESOLVEURL = ("script.module.six", "script.module.kodi-six", "script.module.pyqrcode")


def _pacchetti_extra():
    """Le cartelle che viaggiano insieme alla Videoteca (11/09/2026).

    - repository.videoteca ricostruito SENZA <checksum>: sul Raspberry Kodi
      chiedeva addons.xml.md5 senza la password del repository privato,
      riceveva 404 e dava per illeggibile il repository intero. Un repository
      rotto non puo' aggiornare se stesso: va portato a mano, qui.
    - ResolveURL e il suo repository, che poi si aggiorna da solo: la seconda
      opinione quando un server di s4me non da' il video (lesaghe._server_vivi).
    - le tre dipendenze di ResolveURL, dal repository ufficiale di Kodi.
    Restituisce (cartella d'appoggio, [cartelle da mettere in addons/]).
    """
    import importlib.util
    import zipfile
    base = tempfile.mkdtemp(prefix="servi-extra-")
    spec = importlib.util.spec_from_file_location("costruisci_repo", os.path.join(QUI, "costruisci-repo-kodi.py"))
    repo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repo)
    cartelle = [repo.crea_repository_addon(base)]
    indice = urllib.request.urlopen(urllib.request.Request(RESOLVEURL_REPO + "/addons.xml",
                                                           headers={"User-Agent": "Kodi"}), timeout=60).read()
    indice = indice.decode("utf-8", "replace")
    for aid in ("repository.resolveurl", "script.module.resolveurl"):
        m = re.search(r'<addon\b[^>]*\bid="%s"[^>]*>' % re.escape(aid), indice)
        v = re.search(r'\bversion="([^"]+)"', m.group(0)) if m else None
        if not v:
            raise SystemExit("%s non c'e' nel repository di ResolveURL" % aid)
        locale = os.path.join(base, "%s-%s.zip" % (aid, v.group(1)))
        urllib.request.urlretrieve("%s/zips/%s/%s-%s.zip" % (RESOLVEURL_REPO, aid, aid, v.group(1)), locale)
        with zipfile.ZipFile(locale) as z:
            if "%s/addon.xml" % aid not in z.namelist():
                raise SystemExit("il pacchetto di %s non ha %s/addon.xml" % (aid, aid))
            z.extractall(base)
        os.remove(locale)
        cartelle.append(os.path.join(base, aid))
    spec = importlib.util.spec_from_file_location("installa_skin", os.path.join(QUI, "installa-skin.py"))
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    for aid in DIPENDENZE_RESOLVEURL:
        inst.installa(aid, "nexus", base)
    cartelle += [os.path.join(base, d) for d in DIPENDENZE_RESOLVEURL if os.path.isdir(os.path.join(base, d))]
    return base, cartelle


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
    appoggio, extra = _pacchetti_extra()
    with tarfile.open(tar, "w") as t:
        for cart, aid in ((ADDON, "plugin.video.saghe"), (GUARDIANO, "service.videoteca.guardiano")):
            for p, rel in _file(cart):
                t.add(p, arcname="%s/%s" % (aid, rel))
        for cart in extra:
            for p, rel in _file(cart):
                t.add(p, arcname="%s/%s" % (os.path.basename(cart), rel))
    shutil.rmtree(appoggio, ignore_errors=True)
    print("  Videoteca %s: %d file   guardiano %s   menu %d file   pacchetto %d KB"
          % (_versione(ADDON), len(impronte), _versione(GUARDIANO), len(os.listdir(MENU)), os.path.getsize(tar) // 1024))
    print("  insieme: %s" % ", ".join(os.path.basename(c) for c in extra))
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

FILE_API_PC = os.path.join(os.path.expanduser("~"), ".kodi-pc-api")


def _password_api_pc():
    """La password dell'API del Kodi del PC: creata la prima volta, poi sempre quella."""
    if not os.path.exists(FILE_API_PC):
        import secrets
        with io.open(FILE_API_PC, "w", encoding="utf-8") as f:
            f.write(secrets.token_urlsafe(12))
    with io.open(FILE_API_PC, encoding="utf-8") as f:
        return f.read().strip()


def _rpc(metodo, params=None, tempo=5):
    import base64
    corpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}}).encode()
    intestazioni = {"Content-Type": "application/json"}
    if os.path.exists(FILE_API_PC):
        segreto = "kodi:" + _password_api_pc()
        intestazioni["Authorization"] = "Basic " + base64.b64encode(segreto.encode()).decode()
    try:
        r = urllib.request.Request("http://127.0.0.1:8080/jsonrpc", corpo, intestazioni)
        return json.load(urllib.request.urlopen(r, timeout=tempo)).get("result")
    except Exception:
        return None


def _kodi_pc_acceso():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq kodi.exe"], capture_output=True, text=True)
    return "kodi.exe" in r.stdout.lower()


def _vestito_modulo():
    import importlib.util
    spec = importlib.util.spec_from_file_location("vestito_servi", os.path.join(GUARDIANO, "vestito.py"))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _vestito_testi(leggi_file, scrivi_file):
    """Il logo NOVIX sulla skin di un apparecchio lontano: leggi_file(nome) -> testo o None,
    scrivi_file(nome, testo). A Kodi FERMO: la skin si rilegge al riavvio (11/09/2026)."""
    vestito = _vestito_modulo()
    esiti = []
    for nome, cuci, _segno in vestito.FILE:
        testo = leggi_file(nome)
        if not testo or "<" not in testo:
            esiti.append("%s manca" % nome)
            continue
        nuovo, esito = cuci(testo)
        if esito == "cucito":
            scrivi_file(nome, nuovo)
        esiti.append("%s %s" % (nome, esito))
    return ", ".join(esiti)


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
    skin_pc = os.path.join(addons, "skin.arctic.zephyr.mod")
    if os.path.isdir(skin_pc):
        print("  logo NOVIX sulla skin: %s" % ", ".join("%s %s" % kv for kv in _vestito_modulo().applica(skin_pc).items()))
    print("  " + _vestito_modulo().assicura_splash(kodi, os.path.join(addons, "plugin.video.saghe", "resources", "media", "logo")))
    emb = os.path.join(kodi, "userdata", "addon_data", "script.embuary.info")
    os.makedirs(emb, exist_ok=True)
    p_emb = os.path.join(emb, "settings.xml")
    attuale = io.open(p_emb, encoding="utf-8").read() if os.path.exists(p_emb) else ""
    with io.open(p_emb, "w", encoding="utf-8") as f:
        f.write(_embuary_italiano(attuale))
    print("  Embuary Info in italiano (Scheda completa)")
    gs = os.path.join(kodi, "userdata", "guisettings.xml")
    if os.path.exists(gs):
        vecchio = io.open(gs, encoding="utf-8").read()
        with io.open(gs, "w", encoding="utf-8") as f:
            f.write(_suono_apertura(_guisettings_sicure(vecchio, password=_password_api_pc())))
        print("  origini sconosciute spente")
    # YouTube del banco: mai aperto, alla prima riga chiedeva la procedura guidata.
    # Box e Pi sono gia' configurati: si tocca solo il PC.
    p_yt = os.path.join(kodi, "userdata", "addon_data", "plugin.video.youtube", "settings.xml")
    os.makedirs(os.path.dirname(p_yt), exist_ok=True)
    attuale_yt = io.open(p_yt, encoding="utf-8").read() if os.path.exists(p_yt) else ""
    with io.open(p_yt, "w", encoding="utf-8") as f:
        f.write(_youtube_pronto(attuale_yt))
    print("  YouTube in italiano, senza procedura guidata")
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
    cartella_skin = "%s/addons/skin.arctic.zephyr.mod/1080i" % k

    def _leggi_box(nome):
        locale = os.path.join(tempfile.gettempdir(), "servi-vestito-box-" + nome)
        if os.path.exists(locale):
            os.remove(locale)
        _su("cp %s/%s /sdcard/servi-vestito.xml" % (cartella_skin, nome))
        R._adb("pull", "/sdcard/servi-vestito.xml", locale)
        _su("rm -f /sdcard/servi-vestito.xml")
        return io.open(locale, encoding="utf-8", errors="replace").read() if os.path.exists(locale) else None

    def _scrivi_box(nome, testo):
        locale = os.path.join(tempfile.gettempdir(), "servi-vestito-box-" + nome)
        with io.open(locale, "w", encoding="utf-8", newline="") as fh:
            fh.write(testo)
        R._adb("push", locale, "/sdcard/servi-vestito.xml")
        _su("cp /sdcard/servi-vestito.xml %s/%s && chown %s %s/%s && rm /sdcard/servi-vestito.xml"
            % (cartella_skin, nome, proprietario, cartella_skin, nome))
    print("  logo NOVIX sulla skin: %s" % _vestito_testi(_leggi_box, _scrivi_box))
    logo_box = "%s/addons/plugin.video.saghe/resources/media/logo" % k
    esito_splash = _su("mkdir -p %s/media && cp %s/splash.jpg %s/splash.png %s/media/ && chown -R %s %s/media && echo messo"
                       % (k, logo_box, logo_box, k, proprietario, k))
    print("  splash NOVIX: %s" % ("messo" if "messo" in esito_splash else "NON messo " + esito_splash[-120:]))
    emb = "%s/userdata/addon_data/script.embuary.info" % k
    attuale = _su("cat %s/settings.xml 2>/dev/null" % emb)
    locale_emb = os.path.join(tempfile.gettempdir(), "servi-embuary.xml")
    with io.open(locale_emb, "w", encoding="utf-8") as f:
        f.write(_embuary_italiano(attuale if "<settings" in attuale else ""))
    R._adb("push", locale_emb, "/sdcard/servi-embuary.xml")
    _su("mkdir -p %s && cp /sdcard/servi-embuary.xml %s/settings.xml && rm /sdcard/servi-embuary.xml && chown -R %s %s"
        % (emb, emb, proprietario, emb))
    print("  Embuary Info in italiano (Scheda completa)")
    gs_testo = _su("cat %s/userdata/guisettings.xml" % k, tempo=120)
    if "<settings" in gs_testo:
        locale_gs = os.path.join(tempfile.gettempdir(), "servi-guisettings.xml")
        with io.open(locale_gs, "w", encoding="utf-8") as f:
            f.write(_suono_apertura(_guisettings_sicure(gs_testo)))
        R._adb("push", locale_gs, "/sdcard/servi-guisettings.xml")
        _su("cp /sdcard/servi-guisettings.xml %s/userdata/guisettings.xml && chown %s %s/userdata/guisettings.xml && rm /sdcard/servi-guisettings.xml"
            % (k, proprietario, k))
        print("  origini sconosciute spente")
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

def _rtmp_pi(run, sftp):
    """inputstream.rtmp dal repository di LibreELEC: pvr.iptvsimple lo chiede e sul
    Raspberry non c'era da nessuna parte (atlante, 11/09/2026). Kodi fermo."""
    import gzip
    if run("ls -d %s/addons/inputstream.rtmp /usr/lib/kodi/addons/inputstream.rtmp 2>/dev/null" % R.PI_KODI):
        return "inputstream.rtmp gia' presente"
    repo = "/usr/share/kodi/addons/repository.libreelec.tv/addon.xml"
    info = run("grep -o -E '<info>[^<]*' %s" % repo).replace("<info>", "").strip()
    datadir = run("grep -o -E '<datadir[^>]*>[^<]*' %s" % repo).split(">", 1)[-1].strip().rstrip("/")
    if not info or not datadir:
        return "inputstream.rtmp NON installato: repository di LibreELEC non letto"
    dati = urllib.request.urlopen(urllib.request.Request(info, headers={"User-Agent": "Kodi"}), timeout=60).read()
    indice = (gzip.decompress(dati) if info.endswith(".gz") else dati).decode("utf-8", "replace")
    m = re.search(r'<addon\b[^>]*\bid="inputstream\.rtmp"[^>]*\bversion="([^"]+)"', indice)
    if not m:
        return "inputstream.rtmp NON installato: non c'e' nel repository di LibreELEC"
    locale = os.path.join(tempfile.gettempdir(), "inputstream.rtmp-%s.zip" % m.group(1))
    urllib.request.urlretrieve("%s/inputstream.rtmp/inputstream.rtmp-%s.zip" % (datadir, m.group(1)), locale)
    sftp.put(locale, "/tmp/inputstream.rtmp.zip")
    esito = run("cd %s/addons && unzip -o -q /tmp/inputstream.rtmp.zip && rm /tmp/inputstream.rtmp.zip && echo fatto" % R.PI_KODI)
    return "inputstream.rtmp %s %s" % (m.group(1), "installato" if "fatto" in esito else "NON installato: " + esito[-200:])


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
    cartella_skin = "%s/addons/skin.arctic.zephyr.mod/1080i" % k

    def _leggi_pi(nome):
        try:
            with sftp.open("%s/%s" % (cartella_skin, nome), "r") as fh:
                return fh.read().decode("utf-8", "replace")
        except IOError:
            return None

    def _scrivi_pi(nome, testo):
        with sftp.open("%s/%s" % (cartella_skin, nome), "w") as fh:
            fh.write(testo.encode("utf-8"))
    print("  logo NOVIX sulla skin: %s" % _vestito_testi(_leggi_pi, _scrivi_pi))
    logo_pi = "%s/addons/plugin.video.saghe/resources/media/logo" % k
    esito_splash = run("mkdir -p %s/media && cp %s/splash.jpg %s/splash.png %s/media/ && echo messo" % (k, logo_pi, logo_pi, k))
    print("  splash NOVIX: %s" % ("messo" if "messo" in esito_splash else "NON messo " + esito_splash[-120:]))
    emb = "%s/userdata/addon_data/script.embuary.info" % k
    attuale = run("cat %s/settings.xml 2>/dev/null" % emb)
    run("mkdir -p %s" % emb)
    with sftp.open("%s/settings.xml" % emb, "w") as fh:
        fh.write(_embuary_italiano(attuale if "<settings" in attuale else ""))
    print("  Embuary Info in italiano (Scheda completa)")
    with sftp.open("%s/userdata/guisettings.xml" % k, "r") as fh:
        gs_testo = fh.read().decode("utf-8", "replace")
    if "<settings" in gs_testo:
        with sftp.open("%s/userdata/guisettings.xml" % k, "w") as fh:
            fh.write(_suono_apertura(_guisettings_sicure(gs_testo)))
        print("  origini sconosciute spente")
    print("  " + _rtmp_pi(run, sftp))
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


# --------------------------------------------------------------------------
# VERSIONI E REPOSITORY (11/09/2026: il pulsante "Cerca aggiornamenti")
# --------------------------------------------------------------------------

CLONE_REPO = os.path.join(os.path.expanduser("~"), "kodi-s4me-addon-personale")
PUBBLICATO = os.path.join(QUI, ".pubblicato.json")
NOSTRI = ((ADDON, "plugin.video.saghe"), (GUARDIANO, "service.videoteca.guardiano"))


def _tupla(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def _impronta(cartella):
    """Il codice di un add-on in un numero, senza il numero di versione."""
    h = hashlib.md5()
    for p, rel in sorted(_file(cartella), key=lambda x: x[1]):
        if rel == "resources/impronte.json":
            continue
        with open(p, "rb") as f:
            dati = f.read()
        if rel == "addon.xml":
            dati = re.sub(rb'(<addon\b[^>]*?\bversion=")[^"]+', rb"\1", dati)
        h.update(rel.encode("utf-8"))
        h.update(dati)
    return h.hexdigest()


def _pubblicate():
    p = os.path.join(CLONE_REPO, "zips", "addons.xml")
    if not os.path.exists(p):
        return {}
    with io.open(p, encoding="utf-8") as f:
        indice = f.read()
    fuori = {}
    for m in re.finditer(r"<addon\b[^>]*>", indice):
        ident, ver = re.search(r'\bid="([^"]+)"', m.group(0)), re.search(r'\bversion="([^"]+)"', m.group(0))
        if ident and ver:
            fuori[ident.group(1)] = ver.group(1)
    return fuori


def _alza_versione(cartella, sopra):
    p = os.path.join(cartella, "addon.xml")
    with io.open(p, encoding="utf-8") as f:
        testo = f.read()
    base = max(_versione(cartella), sopra, key=_tupla)
    pezzi = (list(_tupla(base)) + [0, 0, 0])[:3]
    nuova = "%d.%d.%d" % (pezzi[0], pezzi[1], pezzi[2] + 1)
    testo = re.sub(r'(<addon\b[^>]*?\bversion=")[^"]+', lambda m: m.group(1) + nuova, testo, count=1)
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(testo)
    return nuova


def versioni():
    """Kodi aggiorna SOLO se il numero sale: con lo stesso numero e codice diverso
    non succede niente (il 10/09 repository e apparecchi erano tutti e due 1.0.0).
    Codice cambiato rispetto a quello pubblicato -> versione alzata qui, da sola."""
    titolo("VERSIONI")
    try:
        with io.open(PUBBLICATO, encoding="utf-8") as f:
            stato = json.load(f)
    except (OSError, ValueError):
        stato = {}
    pubblicate = _pubblicate()
    for cartella, aid in NOSTRI:
        adesso, fuori = _versione(cartella), pubblicate.get(aid, "")
        if (stato.get(aid) or {}).get("impronta") == _impronta(cartella):
            print("  %-28s %s (uguale a quella pubblicata)" % (aid, adesso))
        elif fuori and _tupla(adesso) <= _tupla(fuori):
            print("  %-28s %s -> %s (codice cambiato)" % (aid, adesso, _alza_versione(cartella, fuori)))
        else:
            print("  %-28s %s (pubblicata: %s)" % (aid, adesso, fuori or "mai"))


def _indice_su_github():
    """addons.xml letto dall'API di GitHub: raw.githubusercontent tiene copie di
    qualche minuto, l'API no - si verifica quello che c'e' davvero."""
    with io.open(os.path.join(os.path.expanduser("~"), ".videoteca-repo-token"), encoding="utf-8") as f:
        segreto = f.read().strip()
    r = urllib.request.Request("https://api.github.com/repos/Alcafer2011/kodi-s4me-addon-personale/contents/zips/addons.xml?ref=main",
                               headers={"Authorization": "token " + segreto, "User-Agent": "servi.py",
                                        "Accept": "application/vnd.github.raw"})
    return urllib.request.urlopen(r, timeout=30).read().decode("utf-8", "replace")


def pubblica():
    titolo("REPOSITORY (per il pulsante Cerca aggiornamenti)")
    if not os.path.isdir(os.path.join(CLONE_REPO, ".git")):
        print("  manca il clone %s: non pubblico" % CLONE_REPO)
        return False
    subprocess.run(["git", "-C", CLONE_REPO, "pull", "--ff-only", "-q"], capture_output=True, text=True, timeout=120)
    r = subprocess.run([sys.executable, os.path.join(QUI, "costruisci-repo-kodi.py"), CLONE_REPO],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("  costruzione NON riuscita:\n%s%s" % (r.stdout[-800:], r.stderr[-800:]))
        return False
    subprocess.run(["git", "-C", CLONE_REPO, "add", "-A"], capture_output=True, text=True)
    messaggio = "Videoteca %s, guardiano %s" % (_versione(ADDON), _versione(GUARDIANO))
    c = subprocess.run(["git", "-C", CLONE_REPO, "commit", "-q", "-m", messaggio], capture_output=True, text=True)
    if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
        print("  commit NON riuscito: %s" % (c.stdout + c.stderr)[-400:])
        return False
    p = subprocess.run(["git", "-C", CLONE_REPO, "push", "-q"], capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        print("  push NON riuscito: %s" % p.stderr[-400:])
        return False
    try:
        indice = _indice_su_github()
    except Exception as e:
        print("  pubblicato, ma non verificato su GitHub: %s" % e)
        return False
    ok = True
    stato = {}
    for cartella, aid in NOSTRI:
        m = re.search(r'<addon\b[^>]*\bid="%s"[^>]*\bversion="([^"]+)"' % re.escape(aid), indice)
        su_github = m.group(1) if m else "assente"
        giusta = su_github == _versione(cartella)
        ok = ok and giusta
        print("  %-28s su GitHub %s %s" % (aid, su_github, "OK" if giusta else "DIVERSA da %s" % _versione(cartella)))
        stato[aid] = {"versione": _versione(cartella), "impronta": _impronta(cartella),
                      "quando": time.strftime("%Y-%m-%d %H:%M")}
    if ok:
        with io.open(PUBBLICATO, "w", encoding="utf-8") as f:
            json.dump(stato, f, ensure_ascii=False, indent=1)
        print("  il pulsante lo vede entro ~5 minuti (raw.githubusercontent tiene una copia)")
    return ok


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) > 1 and argv[1] == "dipendenze":
        # python servi.py dipendenze box pi
        return 0 if all([dipendenze(a) for a in (argv[2:] or ["box", "pi"])]) else 1
    riavvia = "--senza-riavvio" not in argv
    dove = [a for a in argv[1:] if not a.startswith("--")] or ["tutti"]
    solo_pubblica = dove == ["pubblica"]
    if "tutti" in dove:
        dove = ["pc", "box", "pi"]
    dove = [a for a in dove if a != "pubblica"]
    prove()
    versioni()
    tar, impronte = prepara()
    esiti = {}
    for app in dove:
        try:
            esiti[app] = {"pc": servi_pc, "box": servi_box, "pi": servi_pi}[app](tar, impronte, riavvia)
        except Exception as e:
            print("  %s NON RIUSCITO: %s" % (app, e))
            esiti[app] = False
    os.remove(tar)
    # Si pubblica solo quello che si e' appena installato bene: cosi' il pulsante
    # "Cerca aggiornamenti" porta agli altri apparecchi esattamente questo codice.
    if solo_pubblica or (esiti and all(esiti.values()) and "--senza-pubblicare" not in argv):
        esiti["repository"] = pubblica()
    titolo("ESITO")
    for app, ok in esiti.items():
        print("  %-4s %s" % (app, "OK" if ok else "DA CONTROLLARE"))
    return 0 if all(esiti.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
