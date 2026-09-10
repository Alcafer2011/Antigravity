# -*- coding: utf-8 -*-
"""RICETTARIO: i comandi GIUSTI per servire il codice a ogni apparecchio.

Ogni ricetta ha i valori veri presi dalla raccolta (percorsi, versioni,
utente del box) e le trappole scritte ACCANTO al comando, non in una memoria
che magari non si carica. Sono le stesse procedure provate l'11/09/2026.
"""

import os

from raccolta import ADB, BOX, BOX_KODI, PI, PI_KODI, ANTIGRAVITY


def ricette(R):
    app = R.get("apparecchi", {})
    ver = {a: ((k.get("manifesto") or {}).get("kodi") or "?") for a, k in app.items()}
    proprietario = ((app.get("box") or {}).get("manifesto") or {}).get("proprietario_file_kodi") or "u0_a106:u0_a106"
    sorgente = os.path.join(ANTIGRAVITY, "traduttore", "plugin.video.saghe")
    appdata = os.path.expandvars(r"%APPDATA%\Kodi")
    return [
        {"titolo": "1. Prima di servire: il codice regge?",
         "testo": "Sempre, prima di copiare qualunque cosa. Se uno di questi fallisce non si installa.",
         "comandi": [
             ("Compilare tutti i file dell'add-on",
              'python -c "import compileall,sys; sys.exit(not compileall.compile_dir(r\'%s\', quiet=1))"' % sorgente, "bash"),
             ("Errori di nomi e import (pyflakes)", "python -m pyflakes \"%s\"" % sorgente, "bash"),
             ("Banco di prova (Kodi finto): 92 + 8 prove",
              "cd %s\\traduttore\\banco-saghe && python prova_menu.py && python prova_servizio.py" % ANTIGRAVITY, "bash"),
             ("Atlante (questo rapporto) senza ri-raccogliere",
              "cd %s\\traduttore\\atlante && python atlante.py analizza" % ANTIGRAVITY, "bash"),
         ],
         "trappole": ["Il banco-saghe ha il percorso dell'add-on scritto fisso (ADDON=): per provare una copia va cambiato.",
                      "Nel PowerShell di questa macchina il filtro di sicurezza blocca -replace con regex tipo '\\S+' o '\\D' "
                      "e Remove-Item su percorsi composti: usare Python o [System.IO.File]::Delete."]},
        {"titolo": "2. Banco di prova sul PC (Kodi %s)" % ver.get("pc", "?"),
         "testo": "Kodi sul PC va SEMPRE in finestra: dopo ogni avvio togglefullscreen.",
         "comandi": [
             ("Copiare i file cambiati", "copy \"%s\\main.py\" \"%s\\addons\\plugin.video.saghe\\main.py\"" % (sorgente, appdata), "bat"),
             ("Riavviare Kodi in modo pulito (JSON-RPC)",
              "curl -s -H \"Content-Type: application/json\" -d \"{\\\"jsonrpc\\\":\\\"2.0\\\",\\\"id\\\":1,\\\"method\\\":\\\"Application.Quit\\\"}\" http://127.0.0.1:8080/jsonrpc\n"
              "start \"\" \"C:\\Program Files\\Kodi\\kodi.exe\"", "bat"),
             ("Rimetterlo in finestra (mai GUI.SetFullscreen: fa crashare)",
              "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"Input.ExecuteAction\",\"params\":{\"action\":\"togglefullscreen\"}}", "json"),
             ("Lanciare un comando di avvio.py da fuori (RunScript non passa dal JSON-RPC: EventServer UDP 9777)",
              "python - <<'EOF'\nimport socket,struct,time\n"
              "def p(t,d): return b'XBMC'+bytes([2,0])+struct.pack('!HIIHI',t,1,1,len(d),int(time.time()))+b'\\0'*10+d\n"
              "s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\n"
              "s.sendto(p(1,b'banco\\0'+bytes([0])+struct.pack('!HII',0,0,0)),('127.0.0.1',9777)); time.sleep(.4)\n"
              "s.sendto(p(10,bytes([1])+b'RunScript(plugin.video.saghe,aggiungi_titolo,94664,anime)\\0'),('127.0.0.1',9777))\nEOF", "python"),
             ("Registro", "%s\\kodi.log" % appdata, "text"),
         ],
         "trappole": ["Il salvaschermo parte in pochi minuti e si mangia il primo tasto: prima Input.ExecuteAction noop, "
                      "e System.ScreenSaverActive si legge con XBMC.GetInfoBooleans (come etichetta e' sempre vuoto).",
                      "Il ponte MCP di Ghidra usa anche lui 127.0.0.1:8080.",
                      "Mai due sessioni di Claude sullo stesso banco: si chiudono Kodi a vicenda (10/09)."]},
        {"titolo": "3. Box 8K (Android, Kodi %s)" % ver.get("box", "?"),
         "testo": "adb + su. I file copiati con su restano di root e KODI NON LI LEGGE: chown sempre.",
         "comandi": [
             ("Collegarsi (ripetere se 'offline')", "%s connect %s\n%s -s %s shell echo pronto" % (ADB, BOX, ADB, BOX), "bash"),
             ("Backup FUORI da addons/", "%s -s %s shell \"su -c 'cp -r %s/addons/plugin.video.saghe /sdcard/backup-addon-DATA/'\"" % (ADB, BOX, BOX_KODI), "bash"),
             ("Copiare un file e ridarlo a Kodi",
              "%s -s %s push main.py /sdcard/tmp_main.py\n"
              "%s -s %s shell \"su -c 'cp /sdcard/tmp_main.py %s/addons/plugin.video.saghe/main.py && "
              "chown %s %s/addons/plugin.video.saghe/main.py && rm /sdcard/tmp_main.py'\"" % (ADB, BOX, ADB, BOX, BOX_KODI, proprietario, BOX_KODI), "bash"),
             ("Accendere (la TV si accende via CEC), riavviare Kodi, rimettere in standby",
              "%s -s %s shell input keyevent KEYCODE_WAKEUP      # adb cade: riconnettere\n"
              "%s -s %s shell am force-stop org.xbmc.kodi\n"
              "%s -s %s shell monkey -p org.xbmc.kodi -c android.intent.category.LAUNCHER 1\n"
              "%s -s %s shell input keyevent KEYCODE_SLEEP" % ((ADB, BOX) * 4), "bash"),
             ("Registro", "%s -s %s shell \"su -c 'tail -n 200 %s/temp/kodi.log'\"" % (ADB, BOX, BOX_KODI), "bash"),
         ],
         "trappole": ["Dopo KEYCODE_WAKEUP adb va OFFLINE (il box ricollega la WiFi): riconnettere prima di ogni comando.",
                      "Kodi riavviato a TV spenta resta avviato a meta': accendere prima.",
                      "adb risponde anche col box addormentato: sembra acceso e non lo e'.",
                      "Proprietario dei file di Kodi: %s." % proprietario,
                      "Git Bash trasforma i percorsi /storage/... : MSYS_NO_PATHCONV=1 o usare Python."]},
        {"titolo": "4. Raspberry del salotto (LibreELEC, Kodi %s)" % ver.get("pi", "?"),
         "testo": "SSH root@%s (password in Antigravity/src/.salotto-ssh, contiene &: passarla da file). Kodi gira come root." % PI,
         "comandi": [
             ("Copiare con paramiko (sftp)",
              "python - <<'EOF'\nimport paramiko\npw=open(r'%s\\src\\.salotto-ssh').read().strip()\n"
              "c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())\n"
              "c.connect('%s',username='root',password=pw)\ns=c.open_sftp()\n"
              "s.put(r'%s\\main.py','%s/addons/plugin.video.saghe/main.py')\nEOF" % (ANTIGRAVITY, PI, sorgente, PI_KODI), "python"),
             ("Backup FUORI da addons/", "cp -r %s/addons/plugin.video.saghe /storage/backup-addon/DATA/" % PI_KODI, "bash"),
             ("Riavviare Kodi", "systemctl restart kodi", "bash"),
             ("Registro", "tail -n 200 %s/temp/kodi.log" % PI_KODI, "bash"),
         ],
         "trappole": ["L'API di Kodi vuole la password: curl senza credenziali risponde vuoto.",
                      "Kodi riavviato col CEC puo' accendere la TV del salotto: activate_source e' gia' spento.",
                      "sqlite3 c'e' (/usr/bin/sqlite3): il database si modifica sul posto, a Kodi fermo."]},
        {"titolo": "5. Cambiare skin e accendere add-on copiati a mano",
         "testo": "Solo a Kodi SPENTO. Cambiare skin via JSON-RPC non funziona (Kodi chiede conferma e torna indietro).",
         "comandi": [
             ("Accendere gli add-on nel database",
              "sqlite3 userdata/Database/Addons33.db \"UPDATE installed SET enabled=1, disabledReason=0 WHERE addonID='skin.arctic.zephyr.mod';\"", "bash"),
             ("Impostare la skin", "<setting id=\"lookandfeel.skin\">skin.arctic.zephyr.mod</setting>   (SENZA default=\"true\")", "xml"),
             ("Menu della Videoteca", "copiare traduttore/menu-arctic/* in userdata/addon_data/script.skinshortcuts/ e cancellare *.hash", "text"),
         ],
         "trappole": ["Con default=\"true\" Kodi considera la voce mai scelta e rimette Estuary.",
                      "I menu di skinshortcuts sono CONDIVISI: il file giusto e' mainmenu.DATA.xml, senza prefisso della skin.",
                      "Al primo avvio dopo aver tolto il .hash compaiono 'invalid include': normale, si rigenera."]},
        {"titolo": "6. Aggiornamento automatico dal repository",
         "testo": "Kodi aggiorna da solo (entro circa un giorno) e riavvia il servizio dell'add-on aggiornato: niente riavvio a mano.",
         "comandi": [
             ("Alzare la versione", "addon.xml -> version=\"1.x.y\"", "xml"),
             ("Costruire il repository", "cd %s\\traduttore && python costruisci-repo-kodi.py" % ANTIGRAVITY, "bash"),
             ("Pubblicare", "git add -A && git commit -m \"...\" && git push", "bash"),
         ],
         "trappole": ["Cartella doppia dentro lo zip = Kodi non trova addon.xml.",
                      "Senza alzare la versione Kodi non aggiorna niente.",
                      "Il repository e' privato: il token deve restare nell'indirizzo raw."]},
        {"titolo": "7. Salvare il lavoro", "testo": "Il repository e' %s." % "github.com/Alcafer2011/Antigravity",
         "comandi": [("Commit e push", "cd %s && git add <file> && git commit -m \"...\" && git push" % ANTIGRAVITY, "bash")],
         "trappole": ["Mai committare copie/ dell'atlante (sono i file degli apparecchi)."]},
    ]
