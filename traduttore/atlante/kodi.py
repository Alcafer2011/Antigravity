# -*- coding: utf-8 -*-
"""KODI: lo stato di UN apparecchio, dalla sua copia in copie/<apparecchio>.

- ogni add-on: nome, versione, autore, se e' di sistema o installato, a cosa
  serve (i "punti di innesto"), da chi dipende e se quelle dipendenze ci
  sono davvero in versione giusta
- se e' ACCESO nel database (un add-on copiato a mano resta spento: 10/09)
- le impostazioni che contano (skin, lingua, webserver, salvaschermo...)
- trailer automatico della skin e YouTube mai configurato (blocco del 10/09)
- backup rimasti dentro addons/ (il fantasma del 10/09)
- gli errori Python nel formato di Kodi (Error Type / Error Contents /
  Traceback) con il file e la riga DENTRO l'add-on che li ha causati
"""

import collections
import hashlib
import io
import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET

PUNTI = {
    "xbmc.gui.skin": "skin", "xbmc.service": "servizio", "xbmc.python.pluginsource": "plugin",
    "xbmc.python.script": "script", "xbmc.python.module": "modulo Python",
    "xbmc.addon.repository": "repository", "xbmc.python.library": "libreria",
    "kodi.resource.images": "immagini", "kodi.resource.language": "lingua",
    "xbmc.pvrclient": "TV (PVR)", "kodi.inputstream": "inputstream",
    "xbmc.subtitle.module": "sottotitoli", "xbmc.metadata.scraper.movies": "scraper film",
    "xbmc.metadata.scraper.tvshows": "scraper serie", "kodi.context.item": "menu contestuale",
    "xbmc.metadata.scraper.library": "scraper libreria", "xbmc.metadata.scraper.albums": "scraper album",
    "xbmc.metadata.scraper.artists": "scraper artisti", "kodi.peripheral": "periferiche",
    "kodi.vfs": "file system", "kodi.imagedecoder": "immagini (decoder)", "kodi.gameclient": "giochi",
}
IMPOSTAZIONI_CHIAVE = ("lookandfeel.skin", "locale.language", "locale.audiolanguage",
                       "locale.subtitlelanguage", "services.webserver", "services.webserverport",
                       "services.webserverauthentication", "services.esenabled", "services.esallinterfaces",
                       "screensaver.mode", "screensaver.time", "general.addonupdates",
                       "addons.unknownsources", "videoplayer.autoplaynextitem",
                       "input.enablejoystick", "lookandfeel.startupwindow", "debug.showloginfo",
                       "videoscreen.screen", "videoscreen.resolution", "debug.extralogging")
# Add-on che su box (APK) e Raspberry (/usr/lib/kodi) viaggiano con Kodi e
# non stanno nelle cartelle copiate: se "mancano" nella copia, forse ci sono.
PROBABILI_DI_SISTEMA = ("script.module.pil", "script.module.pycryptodome", "inputstream.", "pvr.",
                        "peripheral.", "vfs.", "imagedecoder.", "audiodecoder.", "audioencoder.",
                        "game.", "visualization.", "screensaver.", "metadata.", "resource.", "kodi.",
                        "skin.estuary", "service.xbmc.versioncheck", "webinterface.")


def _versione_tupla(v):
    parti = re.findall(r"\d+", v or "")
    return tuple(int(x) for x in parti[:4]) or (0,)


def _leggi_addon_xml(p):
    try:
        radice = ET.parse(p).getroot()
    except Exception:
        with io.open(p, encoding="utf-8", errors="replace") as h:
            t = h.read()
        m = re.search(r'<addon\b[^>]*id="([^"]+)"[^>]*version="([^"]+)"', t, re.S)
        return {"id": m.group(1), "versione": m.group(2), "nome": "", "autore": "",
                "punti": [], "librerie": [], "dipendenze": [], "xml_rotto": True} if m else None
    if radice.tag != "addon":
        return None
    dip = [(i.get("addon"), i.get("version") or "", i.get("optional") == "true")
           for i in radice.iter("import")]
    punti, librerie = [], []
    for e in radice.iter("extension"):
        pt = e.get("point") or ""
        if pt in ("xbmc.addon.metadata", "kodi.addon.metadata"):
            continue
        punti.append(PUNTI.get(pt, pt))
        if e.get("library"):
            librerie.append("%s=%s" % (PUNTI.get(pt, pt), e.get("library")))
    return {"id": radice.get("id"), "versione": radice.get("version") or "",
            "nome": radice.get("name") or "", "autore": radice.get("provider-name") or "",
            "punti": punti, "librerie": librerie, "dipendenze": dip}


def _addon_in(cartella, dove):
    fuori = {}
    if not os.path.isdir(cartella):
        return fuori
    for d in sorted(os.listdir(cartella)):
        p = os.path.join(cartella, d, "addon.xml")
        if os.path.exists(p):
            a = _leggi_addon_xml(p)
            if a:
                a["dove"] = dove
                a["cartella"] = d
                fuori.setdefault(a["id"], a)
    return fuori


def _database(cartella_userdata):
    dbdir = os.path.join(cartella_userdata, "Database")
    if not os.path.isdir(dbdir):
        return None, ""
    dbs = sorted((f for f in os.listdir(dbdir) if re.match(r"Addons\d+\.db$", f)),
                 key=lambda f: int(re.findall(r"\d+", f)[0]))
    if not dbs:
        return None, ""
    p = os.path.join(dbdir, dbs[-1])
    try:
        c = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
        righe = c.execute("SELECT addonID, enabled, disabledReason, origin, installDate FROM installed").fetchall()
        c.close()
    except Exception as e:
        return {"_errore": str(e)}, dbs[-1]
    return {r[0]: {"acceso": bool(r[1]), "motivo_spento": r[2], "origine": r[3], "installato": r[4]}
            for r in righe}, dbs[-1]


def _impostazioni(cartella_userdata):
    p = os.path.join(cartella_userdata, "guisettings.xml")
    fuori = {}
    if not os.path.exists(p):
        return fuori
    with io.open(p, encoding="utf-8", errors="replace") as h:
        t = h.read()
    for k in IMPOSTAZIONI_CHIAVE:
        m = re.search(r'<setting id="%s"([^>]*)>([^<]*)</setting>' % re.escape(k), t)
        if m:
            fuori[k] = {"valore": m.group(2), "predefinito": 'default="true"' in m.group(1)}
    return fuori


def _impostazioni_addon(cartella_userdata, aid):
    p = os.path.join(cartella_userdata, "addon_data", aid, "settings.xml")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8", errors="replace") as h:
        t = h.read()
    return dict(re.findall(r'<setting id="([^"]+)"[^>]*>([^<]*)</setting>', t))


def _normalizza(msg):
    msg = re.sub(r"0x[0-9a-fA-F]+", "0x..", msg)
    msg = re.sub(r"\b\d{2,}\b", "#", msg)
    msg = re.sub(r"/storage/emulated/0/Android/data/org\.xbmc\.kodi/files/\.kodi", "~", msg)
    return msg.strip()[:220]


def _errore_python(blocco):
    """Un rapporto di errore Python come lo scrive Kodi."""
    tipo = re.search(r"Error Type:\s*<class '([^']+)'>", blocco)
    contenuto = re.search(r"Error Contents:\s*(.+)", blocco)
    file_righe = re.findall(r'File "([^"]+)", line (\d+), in (\S+)', blocco)
    addon, dove, funzione = "?", "", ""
    for f, riga, fn in file_righe:
        m = re.search(r"addons[\\/]+([^\\/]+)[\\/]+(.+)$", f)
        if m and "<frozen" not in f:
            addon, dove, funzione = m.group(1), "%s:%s" % (m.group(2).replace("\\", "/"), riga), fn
    if not tipo:
        ultima = [r.strip() for r in blocco.splitlines() if re.match(r"\s*\w+(Error|Exception)\b", r)]
        if ultima:
            t = ultima[-1].split(":", 1)
            return addon, t[0], t[1].strip() if len(t) > 1 else "", dove, funzione
        return addon, "", "", dove, funzione
    return addon, tipo.group(1), contenuto.group(1).strip() if contenuto else "", dove, funzione


def _registro(cartella_log):
    errori, avvisi = collections.Counter(), collections.Counter()
    include_invalidi, focus = collections.Counter(), collections.Counter()
    python = collections.OrderedDict()
    righe_tot = 0
    for nome in ("kodi.old.log", "kodi.log"):
        p = os.path.join(cartella_log, nome)
        if not os.path.exists(p):
            continue
        with io.open(p, encoding="utf-8", errors="replace") as h:
            righe = h.read().splitlines()
        righe_tot += len(righe)
        i = 0
        while i < len(righe):
            r = righe[i]
            m = re.match(r"^\S+ \S+ T:\d+\s+(error|warning|fatal|critical)\s+<([^>]+)>:\s*(.*)$", r)
            if m:
                livello, gruppo, msg = m.group(1), m.group(2), m.group(3)
                if "EXCEPTION Thrown" in msg or "Python script error report" in msg or "Traceback" in msg:
                    j = i + 1
                    while j < len(righe) and j < i + 80 and not re.match(r"^\d{4}-\d{2}-\d{2} ", righe[j]):
                        j += 1
                    blocco = "\n".join(righe[i:j])
                    addon, tipo, contenuto, dove, funzione = _errore_python(blocco)
                    if tipo or contenuto:
                        k = (addon, tipo, _normalizza(contenuto))
                        g = python.setdefault(k, {"addon": addon, "tipo": tipo, "contenuto": contenuto,
                                                  "dove": dove, "funzione": funzione, "volte": 0,
                                                  "prima": r[:23], "ultima": r[:23], "esempio": blocco[:2500]})
                        g["volte"] += 1
                        g["ultima"] = r[:23]
                    i = j
                    continue
                chiave = "%s | %s" % (gruppo, _normalizza(msg))
                (errori if livello != "warning" else avvisi)[chiave] += 1
                if "invalid include" in msg:
                    include_invalidi[msg.split(":")[-1].strip()] += 1
                if "asked to focus" in msg:
                    focus[_normalizza(msg)] += 1
            i += 1
    return {"righe": righe_tot,
            "errori": errori.most_common(80), "avvisi": avvisi.most_common(50),
            "errori_python": list(python.values()),
            "include_invalidi": include_invalidi.most_common(), "focus_impossibile": focus.most_common(10)}


def _md5_cartella(cartella):
    fuori = {}
    for radice, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith((".py", ".xml", ".json", ".po")):
                p = os.path.join(radice, f)
                with open(p, "rb") as h:
                    fuori[os.path.relpath(p, cartella).replace("\\", "/")] = hashlib.md5(h.read()).hexdigest()
    return fuori


def analizza(cartella_copia):
    if not os.path.isdir(cartella_copia):
        return {"errore": "copia non trovata: %s (lanciare prima: atlante.py raccogli)" % cartella_copia}
    man = {}
    p = os.path.join(cartella_copia, "manifesto.json")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as h:
            man = json.load(h)
    app = man.get("apparecchio", "")
    # Il registro scrive "Starting Kodi (21.3 (21.3.0) Git:...)": parentesi dentro
    # parentesi. Nel rapporto serve solo il numero.
    numero = re.match(r"\s*(\d+(?:\.\d+)+)", man.get("kodi") or "")
    if numero:
        man["kodi"] = numero.group(1)
    addons = _addon_in(os.path.join(cartella_copia, "sistema"), "sistema")
    for aid, a in _addon_in(os.path.join(cartella_copia, "addons"), "utente").items():
        addons[aid] = a
    userdata = os.path.join(cartella_copia, "userdata")
    db, nome_db = _database(userdata)
    binari = set(man.get("addon_binari_di_sistema") or [])
    for aid, a in addons.items():
        if db is None:
            a["acceso"] = None
            continue
        stato = db.get(aid)
        if stato:
            a["acceso"] = stato["acceso"]
            if not stato["acceso"]:
                a["motivo_spento"] = stato.get("motivo_spento")
        else:
            a["acceso"] = True if a["dove"] == "sistema" else None
    rotte = []
    for aid, a in addons.items():
        if a.get("acceso") is False:
            continue
        for dip, ver, opz in a["dipendenze"]:
            if not dip or dip.startswith(("xbmc.", "kodi.")) or opz:
                continue
            d = addons.get(dip)
            if not d:
                if dip in binari:
                    continue
                forse = app in ("box", "pi") and dip.startswith(PROBABILI_DI_SISTEMA)
                rotte.append({"addon": aid, "dipendenza": dip, "richiesta": ver,
                              "problema": "non nella copia (forse di sistema: su %s non si copia)" % app if forse else "manca"})
            elif ver and _versione_tupla(d["versione"]) < _versione_tupla(ver):
                rotte.append({"addon": aid, "dipendenza": dip, "richiesta": ver,
                              "problema": "versione %s troppo vecchia" % d["versione"]})
            elif d.get("acceso") is False:
                rotte.append({"addon": aid, "dipendenza": dip, "richiesta": ver, "problema": "spenta nel database"})
    imp = _impostazioni(userdata)
    backup = []
    cart_addons = os.path.join(cartella_copia, "addons")
    for d in (os.listdir(cart_addons) if os.path.isdir(cart_addons) else []):
        if re.search(r"(bak|prima|\.old|copia|backup)", d, re.I):
            backup.append(d)
    az = _impostazioni_addon(userdata, "skin.arctic.zephyr.mod") or {}
    yt = _impostazioni_addon(userdata, "plugin.video.youtube")
    saghe = os.path.join(cart_addons, "plugin.video.saghe")
    shortcuts = os.path.join(userdata, "addon_data", "script.skinshortcuts")
    guardiano = None
    pg = os.path.join(userdata, "addon_data", "service.videoteca.guardiano", "stato.json")
    if os.path.exists(pg):
        try:
            with io.open(pg, encoding="utf-8") as h:
                guardiano = json.load(h)
        except ValueError:
            guardiano = {"errore": "stato.json del guardiano illeggibile"}
    return {
        "manifesto": man,
        "database": nome_db,
        "database_mancante": db is None,
        "skin_attiva": (imp.get("lookandfeel.skin") or {}).get("valore", ""),
        "impostazioni": imp,
        "addons": addons,
        "conteggio": {"totale": len(addons),
                      "installati": sum(1 for a in addons.values() if a["dove"] == "utente"),
                      "spenti": sorted(k for k, a in addons.items() if a.get("acceso") is False),
                      "senza_riga_nel_db": [] if db is None else
                      sorted(k for k, a in addons.items() if a["dove"] == "utente" and a.get("acceso") is None)},
        "dipendenze_rotte": rotte,
        "backup_in_addons": backup,
        "trailer_automatico": az.get("home.netflix.autoplay.trailer"),
        "youtube_configurato": bool(yt),
        "menu_skinshortcuts": sorted(os.listdir(shortcuts)) if os.path.isdir(shortcuts) else [],
        "guardiano": guardiano,
        "saghe_md5": _md5_cartella(saghe) if os.path.isdir(saghe) else {},
        "impostazioni_saghe": _impostazioni_addon(userdata, "plugin.video.saghe"),
        "registro": _registro(os.path.join(cartella_copia, "log")),
    }
