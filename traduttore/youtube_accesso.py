# -*- coding: utf-8 -*-
"""COLLEGARE L'ACCOUNT YOUTUBE SENZA TOCCARE LA TV.

PERCHE'
    Con le sole chiavi l'add-on cerca e riproduce, ma non sa chi sei: niente
    iscrizioni, niente cronologia, niente "guarda piu' tardi". Per saperlo
    serve un accesso, e l'add-on lo chiede col metodo dei televisori - mostra
    un codice a schermo e tu lo digiti su google.com/device.
    Quel metodo pero' obbliga ad accendere la TV e a stare li' col telecomando.
    Qui si fa la STESSA identica cosa dal PC: si chiede il codice a Google, lo
    digiti dal telefono, e l'accesso ottenuto si scrive direttamente negli
    apparecchi. La TV resta spenta.

COME
    1. chiede a Google un codice (device code), con le TUE chiavi
    2. stampa il codice e apre google.com/device nel browser
    3. aspetta che tu lo confermi (controlla ogni 5 secondi)
    4. scrive access_token e refresh_token in
       userdata/addon_data/plugin.video.youtube/access_manager.json
       su box e Raspberry, a Kodi fermo

USO
    python youtube_accesso.py            box e pi
    python youtube_accesso.py box
    python youtube_accesso.py --mostra   dice solo chi e' collegato adesso
"""

import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(QUI, "atlante"))
import raccolta as R  # noqa: E402

FILE_CHIAVI = os.path.join(os.path.expanduser("~"), ".youtube-api-keys.json")
CARTELLA = "userdata/addon_data/plugin.video.youtube"
DEVICE_CODE_URL = "https://accounts.google.com/o/oauth2/device/code"
TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
SCOPE = "https://www.googleapis.com/auth/youtube"
# Le stesse intestazioni dell'add-on: Google rifiuta il flusso "televisore"
# a chi si presenta come uno script.
TESTA = {"Content-Type": "application/x-www-form-urlencoded",
         "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/61.0.3163.100 Safari/537.36"}


def chiavi():
    with io.open(FILE_CHIAVI, encoding="utf-8") as f:
        return json.load(f)


def _posta(url, dati):
    corpo = urllib.parse.urlencode(dati).encode("utf-8")
    richiesta = urllib.request.Request(url, corpo, TESTA)
    try:
        return json.loads(urllib.request.urlopen(richiesta, timeout=30).read().decode("utf-8"))
    except urllib.error.HTTPError as errore:
        testo = errore.read().decode("utf-8", "replace")
        try:
            return json.loads(testo)
        except ValueError:
            return {"error": "http %s" % errore.code, "error_description": testo[:200]}


def chiedi_codice(d):
    return _posta(DEVICE_CODE_URL, {"client_id": d["client_id"], "scope": SCOPE})


def aspetta_conferma(d, codice, attesa=5, minuti=25):
    """Interroga Google finche' non confermi sul telefono. (token) o None.

    VENTICINQUE MINUTI, non dieci (12/09/2026): il codice di Google vale mezz'ora
    e al primo tentativo e' scaduta prima l'attesa - l'utente stava ancora
    sistemando gli utenti di test nella console, e il collegamento si e' chiuso
    per niente."""
    scadenza = time.time() + minuti * 60
    while time.time() < scadenza:
        time.sleep(attesa)
        r = _posta(TOKEN_URL, {"client_id": d["client_id"], "client_secret": d["client_secret"],
                               "code": codice, "grant_type": "http://oauth.net/grant_type/device/1.0"})
        if r.get("access_token"):
            return r
        errore = r.get("error", "")
        if errore == "authorization_pending":
            continue
        if errore == "slow_down":
            attesa += 2
            continue
        print("   Google dice: %s (%s)" % (errore, r.get("error_description", "")))
        if errore in ("access_denied", "expired_token", "invalid_client"):
            return None
    return None


def accesso_json(testo, token):
    """Mette il token nell'utente 0 del file dell'add-on, lasciando il resto com'e'."""
    try:
        dati = json.loads(testo) if testo and testo.strip() else {}
    except ValueError:
        dati = {}
    am = dati.setdefault("access_manager", {})
    utenti = am.setdefault("users", {})
    utente = utenti.setdefault("0", {"name": "Default", "watch_later": "WL", "watch_history": "HL"})
    utente["access_token"] = token["access_token"]
    utente["refresh_token"] = token.get("refresh_token", "")
    utente["token_expires"] = int(time.time()) + int(token.get("expires_in", 3600))
    am.setdefault("current_user", 0)
    am.setdefault("last_origin", "plugin.video.youtube")
    am.setdefault("developers", {})
    return json.dumps(dati, indent=4, sort_keys=True)


def _racconta(nome, testo):
    try:
        u = ((json.loads(testo or "{}").get("access_manager") or {}).get("users") or {}).get("0") or {}
    except ValueError:
        u = {}
    quando = u.get("token_expires", -1)
    print("  %-4s accesso: %s   scade: %s" % (
        nome, "SI" if u.get("refresh_token") else "no",
        time.strftime("%d/%m %H:%M", time.localtime(quando)) if quando and quando > 0 else "-"))


def box(token, mostra=False):
    if not R._adb_pronto():
        print("  box: non risponde ad adb, saltato")
        return False
    c = "%s/%s" % (R.BOX_KODI, CARTELLA)

    def su(cmd, tempo=120):
        return R._adb("shell", "su -c '%s'" % cmd, tempo=tempo) or ""

    testo = su("cat %s/access_manager.json 2>/dev/null" % c)
    if mostra:
        _racconta("box", testo)
        return True
    proprietario = (su("stat -c %%U:%%G %s/addons" % R.BOX_KODI).strip() or "u0_a106:u0_a106")
    R._adb("shell", "am force-stop org.xbmc.kodi")
    time.sleep(3)
    locale = os.path.join(tempfile.gettempdir(), "youtube-access_manager.json")
    with io.open(locale, "w", encoding="utf-8", newline="") as f:
        f.write(accesso_json(testo, token))
    R._adb("push", locale, "/data/local/tmp/youtube-access.json")
    su("mkdir -p %s && cat /data/local/tmp/youtube-access.json > %s/access_manager.json && chown -R %s %s"
       % (c, c, proprietario, c))
    print("  box: accesso scritto")
    return True


def pi(token, mostra=False):
    import paramiko
    c_ssh = paramiko.SSHClient()
    c_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c_ssh.connect(R.PI, username="root", password=R._password_pi(), timeout=15)

    def run(cmd, tempo=120):
        _i, o, e = c_ssh.exec_command(cmd, timeout=tempo)
        return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

    c = "%s/%s" % (R.PI_KODI, CARTELLA)
    testo = run("cat %s/access_manager.json 2>/dev/null" % c)
    if mostra:
        _racconta("pi", testo)
        c_ssh.close()
        return True
    run("systemctl stop kodi; sleep 3")
    sftp = c_ssh.open_sftp()
    run("mkdir -p %s" % c)
    with sftp.open("%s/access_manager.json" % c, "w") as fh:
        fh.write(accesso_json(testo, token).encode("utf-8"))
    sftp.close()
    run("systemctl start kodi")
    c_ssh.close()
    print("  pi: accesso scritto, Kodi riavviato")
    return True


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    mostra = "--mostra" in argv
    dove = [a for a in argv[1:] if not a.startswith("--")] or ["box", "pi"]
    if mostra:
        for a in dove:
            {"box": box, "pi": pi}[a](None, mostra=True)
        return 0
    d = chiavi()
    r = chiedi_codice(d)
    if not r.get("user_code"):
        raise SystemExit("Google non ha dato il codice: %s" % r)
    print("\n=========================================================")
    print("  APRI:    %s" % r.get("verification_url", "https://www.google.com/device"))
    print("  CODICE:  %s" % r["user_code"])
    print("  (vale %d minuti)" % (int(r.get("expires_in", 1800)) // 60))
    print("=========================================================\n")
    sys.stdout.flush()
    try:
        os.startfile(r.get("verification_url", "https://www.google.com/device"))
    except Exception:
        pass
    token = aspetta_conferma(d, r["device_code"], attesa=int(r.get("interval", 5)))
    if not token:
        raise SystemExit("accesso non confermato: nessuna modifica agli apparecchi")
    print("accesso ottenuto (scade fra %d minuti, si rinnova da solo)"
          % (int(token.get("expires_in", 3600)) // 60))
    esiti = {}
    for a in dove:
        try:
            esiti[a] = {"box": box, "pi": pi}[a](token)
        except Exception as e:
            print("  %s: NON riuscito: %s" % (a, e))
            esiti[a] = False
    return 0 if all(esiti.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
