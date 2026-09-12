# -*- coding: utf-8 -*-
"""LE CHIAVI DI YOUTUBE SUGLI APPARECCHI.

PERCHE' (11-12/09/2026)
    Sul box, aprendo il trailer di un film, compariva "YouTube: key.requirement":
    l'add-on YouTube dalla versione 7 non ha piu' chiavi proprie, e senza quelle
    personali non cerca e non riproduce niente. L'utente ha creato il progetto su
    Google Cloud e le tre chiavi (chiave API, ID client, client secret).

DOVE STANNO LE CHIAVI, E PERCHE' NON QUI
    In `%USERPROFILE%\\.youtube-api-keys.json`, FUORI dal progetto: sono segreti,
    e questo file finisce su GitHub. Qui si legge solo quel file.
    Formato: {"api_key": "...", "client_id": "...", "client_secret": "..."}

COSA SCRIVE, SU OGNI APPARECCHIO
    userdata/addon_data/plugin.video.youtube/
      - settings.xml   youtube.api.key / .id / .secret (le tre voci che l'utente
                       vedrebbe in Impostazioni > API)
      - api_keys.json  keys.user: l'add-on legge da qui quando lavora
    Kodi va FERMO mentre si scrive settings.xml, se no lo riscrive lui uscendo.

USO
    python youtube_chiavi.py            pc, box e pi
    python youtube_chiavi.py box pi
    python youtube_chiavi.py --mostra   dice solo cosa c'e' adesso, senza scrivere
"""

import io
import json
import os
import re
import sys
import tempfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(QUI, "atlante"))
import raccolta as R      # noqa: E402  percorsi, adb, password del Raspberry

FILE_CHIAVI = os.path.join(os.path.expanduser("~"), ".youtube-api-keys.json")
CARTELLA = "userdata/addon_data/plugin.video.youtube"
VOCI = (("youtube.api.key", "api_key"), ("youtube.api.id", "client_id"),
        ("youtube.api.secret", "client_secret"))


def chiavi():
    with io.open(FILE_CHIAVI, encoding="utf-8") as f:
        d = json.load(f)
    mancanti = [k for _id, k in VOCI if not d.get(k)]
    if mancanti:
        raise SystemExit("in %s mancano: %s" % (FILE_CHIAVI, ", ".join(mancanti)))
    return d


def _nascondi(valore):
    return (valore[:8] + "..." + valore[-4:]) if len(valore) > 14 else "***"


def settings_con_chiavi(testo, d):
    """Le tre voci scritte dentro settings.xml (creandolo se non c'e')."""
    if "<settings" not in (testo or ""):
        testo = '<settings version="2">\n</settings>\n'
    for id_voce, campo in VOCI:
        riga = '<setting id="%s">%s</setting>' % (id_voce, d[campo])
        testo, quante = re.subn(r'<setting id="%s"[^>]*?(?:/>|>[^<]*</setting>)' % re.escape(id_voce),
                                riga, testo)
        if not quante:
            testo = testo.replace("</settings>", "    %s\n</settings>" % riga)
    # La procedura guidata non deve ripartire e le chiavi personali vanno usate.
    if 'id="kodion.setup_wizard"' not in testo:
        testo = testo.replace("</settings>", '    <setting id="kodion.setup_wizard">false</setting>\n</settings>')
    return testo


def api_keys_json(testo, d):
    try:
        dati = json.loads(testo) if testo and testo.strip() else {}
    except ValueError:
        dati = {}
    keys = dati.setdefault("keys", {})
    keys.setdefault("developer", {})
    keys["user"] = {"api_key": d["api_key"], "client_id": d["client_id"],
                    "client_secret": d["client_secret"]}
    return json.dumps(dati, indent=4)


# --------------------------------------------------------------------------

def pc(d, mostra=False):
    kodi = os.path.expandvars(r"%APPDATA%\Kodi")
    cartella = os.path.join(kodi, *CARTELLA.split("/"))
    os.makedirs(cartella, exist_ok=True)
    p_set = os.path.join(cartella, "settings.xml")
    p_api = os.path.join(cartella, "api_keys.json")
    if mostra:
        return _racconta("pc", _leggi_locale(p_set), _leggi_locale(p_api))
    import subprocess
    acceso = "kodi.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    if acceso:
        subprocess.run(["taskkill", "/IM", "kodi.exe", "/F"], capture_output=True)
        time.sleep(4)
    with io.open(p_set, "w", encoding="utf-8") as f:
        f.write(settings_con_chiavi(_leggi_locale(p_set), d))
    with io.open(p_api, "w", encoding="utf-8") as f:
        f.write(api_keys_json(_leggi_locale(p_api), d))
    print("  pc: chiavi scritte%s" % (" (Kodi era acceso: riavvialo)" if acceso else ""))
    return True


def _leggi_locale(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def box(d, mostra=False):
    if not R._adb_pronto():
        print("  box: non risponde ad adb, saltato")
        return False
    k = R.BOX_KODI
    c = "%s/%s" % (k, CARTELLA)

    def su(cmd, tempo=120):
        return R._adb("shell", "su -c '%s'" % cmd, tempo=tempo) or ""

    testo_set = su("cat %s/settings.xml 2>/dev/null" % c)
    testo_api = su("cat %s/api_keys.json 2>/dev/null" % c)
    if mostra:
        return _racconta("box", testo_set, testo_api)
    proprietario = (su("stat -c %%U:%%G %s/addons" % k).strip() or "u0_a106:u0_a106")
    R._adb("shell", "am force-stop org.xbmc.kodi")
    time.sleep(3)
    for nome, nuovo in (("settings.xml", settings_con_chiavi(testo_set, d)),
                        ("api_keys.json", api_keys_json(testo_api, d))):
        locale = os.path.join(tempfile.gettempdir(), "youtube-" + nome)
        with io.open(locale, "w", encoding="utf-8", newline="") as f:
            f.write(nuovo)
        R._adb("push", locale, "/sdcard/youtube-chiavi-%s" % nome)
        su("mkdir -p %s && cp /sdcard/youtube-chiavi-%s %s/%s && chown -R %s %s"
           % (c, nome, c, nome, proprietario, c))
    print("  box: chiavi scritte (Kodi era fermo o e' stato fermato)")
    return True


def pi(d, mostra=False):
    import paramiko
    c_ssh = paramiko.SSHClient()
    c_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c_ssh.connect(R.PI, username="root", password=R._password_pi(), timeout=15)

    def run(cmd, tempo=120):
        _i, o, e = c_ssh.exec_command(cmd, timeout=tempo)
        return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

    c = "%s/%s" % (R.PI_KODI, CARTELLA)
    testo_set = run("cat %s/settings.xml 2>/dev/null" % c)
    testo_api = run("cat %s/api_keys.json 2>/dev/null" % c)
    if mostra:
        c_ssh.close()
        return _racconta("pi", testo_set, testo_api)
    run("systemctl stop kodi; sleep 3")
    sftp = c_ssh.open_sftp()
    run("mkdir -p %s" % c)
    with sftp.open("%s/settings.xml" % c, "w") as fh:
        fh.write(settings_con_chiavi(testo_set, d).encode("utf-8"))
    with sftp.open("%s/api_keys.json" % c, "w") as fh:
        fh.write(api_keys_json(testo_api, d).encode("utf-8"))
    sftp.close()
    run("systemctl start kodi")
    c_ssh.close()
    print("  pi: chiavi scritte, Kodi riavviato")
    return True


def _racconta(nome, testo_set, testo_api):
    print("  %s:" % nome)
    for id_voce, _campo in VOCI:
        m = re.search(r'<setting id="%s"[^>]*>([^<]*)</setting>' % re.escape(id_voce), testo_set or "")
        print("     %-20s %s" % (id_voce, _nascondi(m.group(1)) if m and m.group(1) else "VUOTA"))
    try:
        u = (json.loads(testo_api or "{}").get("keys") or {}).get("user") or {}
    except ValueError:
        u = {}
    print("     api_keys.json user:  %s" % (", ".join("%s=%s" % (k, _nascondi(v)) for k, v in sorted(u.items()) if v) or "VUOTO"))
    return True


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    mostra = "--mostra" in argv
    dove = [a for a in argv[1:] if not a.startswith("--")] or ["pc", "box", "pi"]
    d = {} if mostra else chiavi()
    if not mostra:
        print("Chiavi da %s: %s" % (FILE_CHIAVI, ", ".join("%s=%s" % (k, _nascondi(d[k]))
                                                           for _i, k in VOCI)))
    esiti = {}
    for a in dove:
        try:
            esiti[a] = {"pc": pc, "box": box, "pi": pi}[a](d, mostra)
        except Exception as e:
            print("  %s: NON riuscito: %s" % (a, e))
            esiti[a] = False
    return 0 if all(esiti.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
