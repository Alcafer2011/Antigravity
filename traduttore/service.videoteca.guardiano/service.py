# -*- coding: utf-8 -*-
"""IL GUARDIANO DELLA VIDEOTECA: controlla da solo, sempre, sugli apparecchi.

PERCHE' (chiesto dall'utente l'11/09/2026: "installa degli script nei box
che controllano sempre tutto")
    I guasti della Videoteca si scoprivano davanti alla TV, giorni dopo:
    - un add-on installato a meta' (miolista.py mancante sul box: ogni riga
      della home cadeva con ImportError)
    - il menu della home sparito dopo una reinstallazione della skin
    - un backup rimasto dentro addons/ che faceva girare codice vecchio
    - un trailer partito da solo con YouTube mai configurato (Kodi bloccato)
    Il guardiano li guarda ogni 15 minuti, li scrive in un file che l'atlante
    raccoglie, e avvisa solo per i problemi NUOVI e gravi, mai durante un video.

COSA RIPARA DA SOLO (poco, e solo cose sicure)
    Il menu della home di Arctic Zephyr, se i file di skinshortcuts spariscono:
    li rimette da resources/menu e toglie il .hash. Si vede al riavvio.
    Tutto il resto lo SEGNALA: riparare codice o database a Kodi acceso fa
    piu' danni di quanti ne toglie.

LA SCATOLA NERA (1.2.0, chiesta dall'utente l'11/09/2026)
    Oltre ai controlli ogni 15 minuti, ogni secondo guarda cosa succede
    sullo schermo e scrive quello che cambia: vedi scatola.py. Sul PC la
    legge `traduttore/registratore.py`.

REGOLE DI UN SERVIZIO BUONO
    niente finestre (solo notifiche), niente attese che Kodi non puo'
    interrompere (monitor.waitForAbort), registro letto a pezzi dall'ultimo
    punto, file scritti in modo atomico, ogni controllo nel suo try.
"""

import hashlib
import io
import json
import os
import re
import shutil
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import scatola as _scatola

ID = "service.videoteca.guardiano"
PRIMO_GIRO = 90
OGNI = 15 * 60
SOGLIA_CALDO = 80
MAX_REGISTRO = 2 * 1024 * 1024
ADDON_CHIAVE = ("plugin.video.saghe", "plugin.video.s4me", "script.skinshortcuts", "skin.arctic.zephyr.mod",
                "inputstream.adaptive", "script.embuary.helper", "plugin.video.themoviedb.helper")
NOSTRI = ("plugin.video.saghe", ID)


def _t(s):
    return xbmcvfs.translatePath(s)


def _log(msg, livello=xbmc.LOGINFO):
    xbmc.log("[Guardiano] %s" % msg, livello)


def _dati():
    d = _t("special://profile/addon_data/%s/" % ID)
    if not xbmcvfs.exists(d):
        xbmcvfs.mkdirs(d)
    return d


def _scrivi_json(nome, dati):
    p = os.path.join(_dati(), nome)
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(dati, ensure_ascii=False, indent=1))
    os.replace(tmp, p)


def _leggi_json(nome, predefinito):
    try:
        with io.open(os.path.join(_dati(), nome), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return predefinito


def _esito(nome, livello, testo, dettagli=None):
    return {"controllo": nome, "livello": livello, "testo": testo, "dettagli": dettagli or []}


# --------------------------------------------------------------------------
# I CONTROLLI
# --------------------------------------------------------------------------

def integrita():
    base = _t("special://home/addons/plugin.video.saghe/")
    imp = os.path.join(base, "resources", "impronte.json")
    if not os.path.exists(imp):
        return _esito("integrita", "attenzione", "Manca resources/impronte.json: installare la Videoteca con servi.py")
    with io.open(imp, encoding="utf-8") as f:
        impronte = json.load(f)
    mancanti, diversi = [], []
    for rel, md5 in (impronte.get("file") or {}).items():
        p = os.path.join(base, rel.replace("/", os.sep))
        if not os.path.exists(p):
            mancanti.append(rel)
            continue
        with open(p, "rb") as h:
            if hashlib.md5(h.read()).hexdigest() != md5:
                diversi.append(rel)
    if mancanti:
        return _esito("integrita", "problema", "Videoteca installata a meta': %d file mancanti" % len(mancanti), mancanti + diversi)
    if diversi:
        return _esito("integrita", "attenzione", "%d file della Videoteca diversi da quelli installati" % len(diversi), diversi)
    return _esito("integrita", "ok", "Videoteca %s intera (%d file)" % (impronte.get("versione", "?"), len(impronte.get("file") or {})))


def backup_in_addons():
    cartella = _t("special://home/addons/")
    trovati = [d for d in os.listdir(cartella) if re.search(r"(bak|prima|backup|\.old$|copia)", d, re.I)]
    if trovati:
        return _esito("backup", "problema", "Backup dentro addons/: Kodi puo' eseguire QUELLI al posto del codice nuovo", trovati)
    return _esito("backup", "ok", "Nessun backup dentro addons/")


def registro(stato):
    """Errori Python nuovi dall'ultimo giro, letti dal punto dove ci si era fermati."""
    p = os.path.join(_t("special://logpath"), "kodi.log")
    if not os.path.exists(p):
        return _esito("registro", "attenzione", "kodi.log non trovato"), stato
    misura = os.path.getsize(p)
    da = stato.get("registro_posizione", 0)
    if da > misura:
        da = 0                      # Kodi e' ripartito: registro nuovo
    da = max(da, misura - MAX_REGISTRO)
    with io.open(p, encoding="utf-8", errors="replace") as f:
        f.seek(da)
        testo = f.read()
    stato["registro_posizione"] = misura
    errori = {}
    for blocco in re.split(r"\n(?=\d{4}-\d{2}-\d{2} )", testo):
        if "Error Type:" not in blocco:
            continue
        tipo = re.search(r"Error Type:\s*<class '([^']+)'>", blocco)
        contenuto = re.search(r"Error Contents:\s*(.+)", blocco)
        addon, dove = "?", ""
        for f_, riga in re.findall(r'File "([^"]+)", line (\d+)', blocco):
            m = re.search(r"addons[\\/]+([^\\/]+)[\\/]+(.+)$", f_)
            if m:
                addon, dove = m.group(1), "%s:%s" % (m.group(2).replace("\\", "/"), riga)
        chiave = "%s|%s|%s" % (addon, tipo.group(1) if tipo else "?", (contenuto.group(1) if contenuto else "")[:160])
        e = errori.setdefault(chiave, {"addon": addon, "tipo": tipo.group(1) if tipo else "?",
                                       "contenuto": (contenuto.group(1) if contenuto else "")[:300],
                                       "dove": dove, "volte": 0})
        e["volte"] += 1
    elenco = sorted(errori.values(), key=lambda x: -x["volte"])
    nostri = [e for e in elenco if e["addon"] in NOSTRI]
    if nostri:
        return _esito("registro", "problema", "%d errori Python della Videoteca dall'ultimo controllo" % sum(e["volte"] for e in nostri), elenco[:20]), stato
    if elenco:
        return _esito("registro", "attenzione", "%d errori Python di altri add-on" % sum(e["volte"] for e in elenco), elenco[:20]), stato
    return _esito("registro", "ok", "Nessun errore Python nuovo"), stato


def skin_e_menu():
    skin = xbmc.getSkinDir()
    if skin != "skin.arctic.zephyr.mod":
        return _esito("menu", "attenzione", "Skin attiva: %s (la home della Videoteca e' fatta per Arctic Zephyr)" % skin)
    dati = _t("special://profile/addon_data/script.skinshortcuts/")
    servono = ("mainmenu.DATA.xml", "skin.arctic.zephyr.mod.properties")
    mancano = [f for f in servono if not os.path.exists(os.path.join(dati, f))]
    if not mancano:
        return _esito("menu", "ok", "Menu della Videoteca presente")
    scorta = _t("special://home/addons/%s/resources/menu/" % ID)
    if not os.path.isdir(scorta):
        return _esito("menu", "problema", "Menu della home sparito e nessuna copia di scorta", mancano)
    if not xbmcvfs.exists(dati):
        xbmcvfs.mkdirs(dati)
    for f in os.listdir(scorta):
        shutil.copyfile(os.path.join(scorta, f), os.path.join(dati, f))
    for f in os.listdir(dati):
        if f.endswith(".hash"):
            try:
                os.remove(os.path.join(dati, f))
            except OSError:
                pass
    _log("menu della home ripristinato: %s" % ", ".join(mancano), xbmc.LOGWARNING)
    return _esito("menu", "riparato", "Menu della home ripristinato: si vede al prossimo avvio di Kodi", mancano)


def leggibili():
    """Add-on che Kodi non riesce a LEGGERE: per lui non esistono, e nessuno lo dice.

    Sul box, un add-on copiato con su resta di root: repository.videoteca
    (root:root 770) e' stato invisibile per giorni, e con lui gli aggiornamenti
    automatici (11/09/2026). Il guardiano gira come Kodi, quindi vede
    esattamente quello che vede Kodi.
    """
    cartella = _t("special://home/addons/")
    chiusi = []
    for d in sorted(os.listdir(cartella)):
        p = os.path.join(cartella, d)
        if not os.path.isdir(p) or d in ("packages", "temp"):
            continue
        axml = os.path.join(p, "addon.xml")
        if not os.access(p, os.R_OK | os.X_OK) or (os.path.exists(axml) and not os.access(axml, os.R_OK)):
            chiusi.append(d)
        elif not os.path.exists(axml):
            try:
                os.listdir(p)
            except OSError:
                chiusi.append(d)
    if chiusi:
        return _esito("leggibili", "problema", "Add-on che Kodi non riesce a leggere (per lui non esistono): %s"
                      % ", ".join(chiusi[:5]), chiusi)
    return _esito("leggibili", "ok", "Tutti gli add-on sono leggibili da Kodi")


def addon_chiave():
    spenti, assenti = [], []
    for aid in ADDON_CHIAVE:
        if not xbmc.getCondVisibility("System.HasAddon(%s)" % aid):
            assenti.append(aid)
        elif not xbmc.getCondVisibility("System.AddonIsEnabled(%s)" % aid):
            spenti.append(aid)
    if spenti:
        return _esito("addon", "problema", "Add-on importanti spenti: %s" % ", ".join(spenti), spenti + assenti)
    if assenti:
        return _esito("addon", "attenzione", "Add-on non installati: %s" % ", ".join(assenti), assenti)
    return _esito("addon", "ok", "Add-on importanti installati e accesi")


def trailer():
    acceso = xbmc.getCondVisibility("Skin.HasSetting(home.netflix.autoplay.trailer)")
    youtube = os.path.exists(_t("special://profile/addon_data/plugin.video.youtube/settings.xml"))
    if acceso and not youtube:
        return _esito("trailer", "problema", "Trailer automatico acceso e YouTube mai configurato: al primo trailer Kodi puo' bloccarsi")
    if acceso:
        return _esito("trailer", "attenzione", "Trailer automatico acceso")
    return _esito("trailer", "ok", "Trailer automatico spento")


def macchina():
    note, livello = [], "ok"
    temperature = []
    for zona in range(10):
        p = "/sys/class/thermal/thermal_zone%d/temp" % zona
        try:
            with open(p) as f:
                v = int(f.read().strip())
                temperature.append(v / 1000.0 if v > 1000 else float(v))
        except (OSError, ValueError):
            continue
    if temperature:
        t = max(temperature)
        note.append("temperatura %.0f gradi" % t)
        if t >= SOGLIA_CALDO:
            livello = "problema"
    try:
        s = os.statvfs(_t("special://home/"))
        libero = s.f_bavail * s.f_frsize / 1024.0 / 1024.0
        note.append("spazio libero %.0f MB" % libero)
        if libero < 300:
            livello = "problema"
    except (AttributeError, OSError):
        pass
    try:
        note.append("registro %.1f MB" % (os.path.getsize(os.path.join(_t("special://logpath"), "kodi.log")) / 1048576.0))
    except OSError:
        pass
    testo = ", ".join(note) or "nessun dato"
    if livello == "problema":
        testo = "Attenzione: " + testo
    return _esito("macchina", livello, testo, {"temperature": temperature})


# --------------------------------------------------------------------------
# IL GIRO
# --------------------------------------------------------------------------

def vestito_skin():
    """Il vestito NOVIX sulla skin (vestito.py): l'apertura animata e la N in ogni schermata.

    Un aggiornamento di Arctic Zephyr riscrive i suoi file e il vestito sparisce:
    qui si ricuce, e si vede dal prossimo avvio di Kodi (11/09/2026)."""
    import vestito
    skin = xbmcvfs.translatePath("special://home/addons/skin.arctic.zephyr.mod/")
    if not os.path.isdir(skin):
        return _esito("vestito", "ok", "Arctic Zephyr non installata: niente da vestire")
    esiti = vestito.applica(skin)
    # lo splash di Kodi all'accensione: la N su nero, da cui riparte l'animazione
    try:
        esiti["splash"] = vestito.assicura_splash(
            xbmcvfs.translatePath("special://home/"),
            xbmcvfs.translatePath("special://home/addons/plugin.video.saghe/resources/media/logo/"))
    except OSError as e:
        esiti["splash"] = "non messo: %s" % e
    cuciti = [f for f, e in esiti.items() if e == "cucito"]
    strani = [f for f, e in esiti.items() if e in ("non riconosciuto", "manca")]
    if strani:
        return _esito("vestito", "attenzione", "la skin e' cambiata, il logo non si ricuce: %s" % ", ".join(strani), esiti)
    if cuciti:
        return _esito("vestito", "riparato", "logo NOVIX ricucito su %s: si vede dal prossimo avvio" % ", ".join(cuciti), esiti)
    return _esito("vestito", "ok", "logo NOVIX, splash e apertura animata al loro posto", esiti)


def giro():
    stato = _leggi_json("stato.json", {})
    esiti = []
    for controllo in (integrita, backup_in_addons, leggibili, skin_e_menu, addon_chiave, trailer, macchina, vestito_skin):
        try:
            esiti.append(controllo())
        except Exception as e:
            esiti.append(_esito(controllo.__name__, "attenzione", "controllo non riuscito: %s" % e))
    try:
        e, stato = registro(stato)
        esiti.append(e)
    except Exception as ex:
        esiti.append(_esito("registro", "attenzione", "controllo non riuscito: %s" % ex))

    gravi_prima = set(stato.get("gravi", []))
    gravi = ["%s: %s" % (e["controllo"], e["testo"]) for e in esiti if e["livello"] in ("problema", "riparato")]
    nuovi = [g for g in gravi if g not in gravi_prima]
    try:
        nera = SCATOLA.riassunto() if SCATOLA else None
    except Exception as ex:
        nera = {"errore": str(ex)}
    nuovo_stato = {
        "scatola_nera": nera,
        "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
        "versione": xbmcaddon.Addon(ID).getAddonInfo("version"),
        "kodi": xbmc.getInfoLabel("System.BuildVersion"),
        "piattaforma": "android" if xbmc.getCondVisibility("System.Platform.Android") else
                       ("linux" if xbmc.getCondVisibility("System.Platform.Linux") else "altro"),
        "esiti": esiti,
        "gravi": gravi,
        "registro_posizione": stato.get("registro_posizione", 0),
    }
    _scrivi_json("stato.json", nuovo_stato)
    storico = _leggi_json("storico.json", [])
    storico.append({"quando": nuovo_stato["quando"], "gravi": gravi,
                    "livelli": {e["controllo"]: e["livello"] for e in esiti}})
    _scrivi_json("storico.json", storico[-300:])
    for e in esiti:
        if e["livello"] != "ok":
            _log("%s [%s] %s" % (e["controllo"], e["livello"], e["testo"]),
                 xbmc.LOGWARNING if e["livello"] in ("problema", "riparato") else xbmc.LOGINFO)
    if nuovi and not xbmc.Player().isPlaying():
        xbmcgui.Dialog().notification("Guardiano della Videoteca", nuovi[0][:120] +
                                      (" (+%d)" % (len(nuovi) - 1) if len(nuovi) > 1 else ""),
                                      xbmcgui.NOTIFICATION_WARNING, 9000)


SCATOLA = None


class _Monitor(xbmc.Monitor):
    """Passa alla scatola nera le notifiche di Kodi (video, sonno, uscita...)."""

    def onNotification(self, mittente, metodo, dati):
        if SCATOLA:
            SCATOLA.notifica(mittente, metodo, dati)


def main():
    global SCATOLA
    try:
        SCATOLA = _scatola.Scatola()
    except Exception as e:
        _log("scatola nera spenta: %s" % e, xbmc.LOGWARNING)
    monitor = _Monitor()
    _log("avviato: primo controllo fra %d s, poi ogni %d minuti; scatola nera %s"
         % (PRIMO_GIRO, OGNI // 60, "accesa" if SCATOLA else "spenta"))
    prossimo = time.time() + PRIMO_GIRO
    while not monitor.abortRequested():
        if SCATOLA:
            SCATOLA.tick()
        if time.time() >= prossimo:
            try:
                giro()
            except Exception as e:
                _log("giro non riuscito: %s" % e, xbmc.LOGERROR)
            prossimo = time.time() + OGNI
        if monitor.waitForAbort(1):
            break
    if SCATOLA:
        SCATOLA.chiudi()


if __name__ == "__main__":
    main()
