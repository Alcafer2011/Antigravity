# -*- coding: utf-8 -*-
"""CHI PARLA CON CHI, E COSA SI ASPETTA: la mappa dei dialoghi fra Kodi, la
skin, la Videoteca, s4me e i servizi in rete, coi guasti segnati sulle frecce.

PERCHE' (l'utente, 11/09/2026)
    "mostrami come le applicazioni - nostro addon, skin, s4me e Kodi -
    dialogano tra loro e chi si aspetta cosa e da chi per funzionare. Ma devi
    farli trovare dallo script py, per capire tutto assieme come funziona e
    dove c'e' il buco".
    Il buco del giorno era proprio su una freccia: la Videoteca chiamava s4me
    con `action=Search`, un'azione che s4me non ha. Nessun registro della
    Videoteca lo diceva; lo diceva il codice di s4me, dall'altra parte.

COME
    Ogni freccia e' un CONTRATTO letto nei file, non scritto a mano:
      chi chiama, chi risponde, con che cosa (un indirizzo, un comando, un
      file), cosa si aspetta chi chiama - e la PROVA che regge o si rompe,
      presa dall'altra parte (il codice di chi risponde, il registro, lo
      stato del guardiano), apparecchio per apparecchio.
      verde    regge
      arancio  regge con riserva
      rosso    rotto
      grigio   non verificabile dai file
"""

import ast
import glob
import html
import io
import json
import os
import re

QUI = os.path.dirname(os.path.abspath(__file__))
TRADUTTORE = os.path.dirname(QUI)
SORGENTE = os.path.join(TRADUTTORE, "plugin.video.saghe")
MENU = os.path.join(TRADUTTORE, "menu-arctic")
COLORI = {"regge": "#2e7d32", "riserva": "#ef6c00", "rotto": "#c62828", "ignoto": "#90a4ae"}
NOMI_STATO = {"regge": "regge", "riserva": "regge con riserva", "rotto": "ROTTO", "ignoto": "non verificabile"}
APPARECCHI = ("pc", "box", "pi")

# (id, nome, colonna, riga, a cosa serve)
NODI = [
    ("kodi", "Kodi e telecomando", 0, 1, "Il programma che gira sull'apparecchio: legge i tasti, apre le finestre, chiama gli add-on."),
    ("repo", "Repository Videoteca", 0, 3, "repository.videoteca: dice a Kodi dove prendere gli aggiornamenti (GitHub privato)."),
    ("skin", "Skin Arctic Zephyr", 1, 0, "Disegna tutto: menu, righe di locandine, testata, schede."),
    ("menu", "Menu e righe (skinshortcuts)", 1, 1, "I file del menu: quali voci ci sono e quali righe della Videoteca sotto ogni voce."),
    ("schede", "Schede (Embuary, TMDb Helper)", 1, 2, "Le schede dettaglio e le righe automatiche della skin."),
    ("guardiano", "Guardiano", 1, 3, "Ogni 15 minuti controlla la Videoteca e tiene la scatola nera."),
    ("main", "Videoteca: main.py", 2, 0, "Il cuore: righe della home, menu, catalogo, ricerca."),
    ("avvio", "Videoteca: avvio.py", 2, 1, "Tutto quello che apre finestre: tastiera, avvisi, aggiornamenti."),
    ("servizio", "Videoteca: service.py", 2, 2, "In sottofondo: cache di Netflix, cinema, loghi; il controllore dei film."),
    ("lesaghe", "Canale Le Saghe (in s4me)", 3, 0, "Il nostro codice DENTRO s4me: trova episodi e film, cerca sui siti, prova i server."),
    ("s4me", "s4me", 3, 1, "Il motore delle fonti: canali dei siti, risolutori dei server, riproduzione."),
    ("resolveurl", "ResolveURL", 3, 2, "Seconda opinione sui server video; si aggiorna da solo dal suo repository."),
    ("siti", "Siti (canali di s4me)", 4, 0, "AnimeWorld, StreamingCommunity, RaiPlay...: dove stanno episodi e film."),
    ("server", "Server video", 4, 1, "voe, streamtape, dood...: i posti da cui arriva il file del video."),
    ("rete", "TMDb, TVmaze, fanart.tv", 4, 2, "Schede, locandine, loghi, elenco di Netflix e del cinema."),
    ("github", "GitHub", 4, 3, "Da qui arrivano gli aggiornamenti: della Videoteca (privato) e di s4me (stream4me)."),
]


def _testo(p):
    try:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _json(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _funzioni(p):
    try:
        return {n.name for n in ast.parse(_testo(p)).body if isinstance(n, ast.FunctionDef)}
    except SyntaxError:
        return set()


def _peggiore(stati):
    for s in ("rotto", "riserva", "regge"):
        if s in stati:
            return s
    return "ignoto"


def _copia_s4me(copie):
    for app in APPARECCHI:
        p = os.path.join(copie, app, "addons", "plugin.video.s4me")
        if os.path.isdir(p):
            return p
    return os.path.expandvars(r"%APPDATA%\Kodi\addons\plugin.video.s4me")


def _azioni_launcher(s4):
    t = _testo(os.path.join(s4, "platformcode", "launcher.py"))
    return set(re.findall(r"item\.action\s*==\s*['\"](\w+)['\"]", t))


# ---------------------------------------------------------------------------- i contratti letti nel codice

def indirizzi_verso_s4me(sorgente=SORGENTE):
    """Ogni indirizzo che la Videoteca costruisce verso s4me: canale, azione, file:riga, formato."""
    fuori = []
    for p in sorted(glob.glob(os.path.join(sorgente, "**", "*.py"), recursive=True)):
        rel = os.path.relpath(p, sorgente).replace("\\", "/")
        testo = _testo(p)
        try:
            albero = ast.parse(testo)
        except SyntaxError:
            continue
        for n in ast.walk(albero):
            if isinstance(n, ast.Call):
                nome = getattr(n.func, "attr", "") or getattr(n.func, "id", "")
                if nome == "indirizzo" and n.args and isinstance(n.args[0], ast.Dict):
                    campi = {}
                    for k, v in zip(n.args[0].keys, n.args[0].values):
                        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                            campi[k.value] = v.value
                    fuori.append({"canale": campi.get("channel", "?"), "azione": campi.get("action", "?"),
                                  "dove": "%s:%d" % (rel, n.lineno), "formato": "codificato"})
                elif nome == "_s4me" and rel.endswith("scoperte.py"):
                    fuori.append({"canale": "<cataloghi>", "azione": "mainlist", "dove": "%s:%d" % (rel, n.lineno),
                                  "formato": "codificato"})
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and "plugin://plugin.video.s4me/?" in n.value:
                c = re.search(r"channel=(\w+)", n.value)
                a = re.search(r"action=(\w+)", n.value)
                if c or a:
                    fuori.append({"canale": c.group(1) if c else "?", "azione": a.group(1) if a else "?",
                                  "dove": "%s:%d" % (rel, n.lineno), "formato": "in chiaro"})
    return fuori


def _comandi_avvio():
    t = _testo(os.path.join(SORGENTE, "avvio.py"))
    comandi = set(re.findall(r'comando == "(\w+)"', t))
    for m in re.finditer(r'"(\w+)":\s*_\w+', t):
        comandi.add(m.group(1))
    return comandi


def _menu_skin():
    """(comandi RunScript, azioni plugin) nei file del menu della skin."""
    t = _testo(os.path.join(MENU, "mainmenu.DATA.xml")) + _testo(os.path.join(MENU, "powermenu.DATA.xml"))
    return (set(re.findall(r"RunScript\(plugin\.video\.saghe,(\w+)", t)),
            set(re.findall(r"plugin://plugin\.video\.saghe/\?azione=(\w*)", t)))


# ---------------------------------------------------------------------------- le frecce

def analizza(R, copie):
    a = R.get("addon") or {}
    app_k = R.get("apparecchi") or {}
    s4 = R.get("s4me") or {}
    s4_app = s4.get("apparecchi") or {}
    copia_s4me = _copia_s4me(copie)
    frecce = []

    def freccia(da, verso, cosa, aspetta, per_app, prove):
        stati = [v for v in per_app.values() if v]
        frecce.append({"n": len(frecce) + 1, "da": da, "a": verso, "cosa": cosa, "aspetta": aspetta,
                       "per_app": per_app, "stato": _peggiore(stati), "prove": [x for x in prove if x][:12]})

    presenti = [app for app in APPARECCHI if not (app_k.get(app) or {}).get("errore")]

    # 1. menu -> skin
    per, prove = {}, []
    for app in presenti:
        file_menu = (app_k[app] or {}).get("menu_skinshortcuts") or []
        per[app] = "regge" if "mainmenu.DATA.xml" in file_menu else "rotto"
        if per[app] == "rotto":
            prove.append("%s: in addon_data/script.skinshortcuts manca mainmenu.DATA.xml (il menu e' quello di fabbrica)" % app)
    freccia("menu", "skin", "i file del menu (mainmenu.DATA.xml, .properties)",
            "che ci siano, senza prefisso della skin nel nome, e che la skin li ricostruisca (.hash tolto)", per, prove)

    # 2. skin -> main: le righe della home
    righe = (a.get("menu") or {}).get("righe") or []
    gestiti = set(a.get("widget_gestiti") or [])
    orfane = [r for r in righe if r.get("che") and r["che"] not in gestiti and r["che"].split(":")[0] not in gestiti]
    stato = "rotto" if orfane else ("regge" if righe else "ignoto")
    freccia("skin", "main", "plugin://plugin.video.saghe/?azione=widget&che=<riga>",
            "che main.widget() conosca ogni riga e risponda subito, senza rete",
            {app: stato for app in presenti},
            ["%d righe nel menu, %d gestite da widget()" % (len(righe), len(righe) - len(orfane))]
            + ["riga sconosciuta: %s (%s)" % (r["che"], r.get("voce", "")) for r in orfane])

    # 3. menu -> avvio / main: i pulsanti del menu
    comandi = _comandi_avvio()
    rs, az = _menu_skin()
    gest = set(a.get("azioni_gestite") or {})
    manca_rs = sorted(c for c in rs if c not in comandi)
    manca_az = sorted(x for x in az if x and x not in gest)
    freccia("menu", "avvio", "RunScript(plugin.video.saghe,<comando>) e ?azione=<azione> dai pulsanti del menu",
            "che avvio.py abbia il comando e main.py l'azione",
            {app: ("rotto" if manca_rs or manca_az else "regge") for app in presenti},
            ["comandi dal menu: %s" % ", ".join(sorted(rs)) or "-", "azioni dal menu: %s" % ", ".join(sorted(x or "(menu principale)" for x in az))]
            + ["comando sconosciuto: %s" % c for c in manca_rs] + ["azione sconosciuta: %s" % x for x in manca_az])

    # 4. main -> avvio
    senza = a.get("runscript_senza_comando") or []
    freccia("main", "avvio", "RunScript(plugin.video.saghe,<comando>,<argomenti>) per tutto cio' che apre finestre",
            "che il comando esista, e che dalla cartella non si apra nessuna finestra",
            {app: ("rotto" if senza else "regge") for app in presenti},
            ["comandi usati: %d" % len(a.get("runscript_usati") or {})] + ["senza comando: %s" % c for c in senza])

    # 5. main -> lesaghe / s4me: gli indirizzi
    indirizzi = indirizzi_verso_s4me()
    lesaghe_f = _funzioni(os.path.join(SORGENTE, "resources", "canale", "lesaghe.py"))
    launcher = _azioni_launcher(copia_s4me)
    cataloghi = []
    try:
        for n in ast.parse(_testo(os.path.join(SORGENTE, "resources", "lib", "scoperte.py"))).body:
            if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CATALOGHI_RICERCA" for t in n.targets):
                cataloghi = [c for _nome, c in ast.literal_eval(n.value)]
    except (SyntaxError, ValueError):
        pass
    verso_lesaghe, verso_s4me = [], []
    for ind in indirizzi:
        esito, nota = "regge", ""
        if ind["canale"] == "lesaghe":
            if ind["azione"] not in lesaghe_f:
                esito, nota = "rotto", "lesaghe.py non ha la funzione %s" % ind["azione"]
            verso_lesaghe.append((ind, esito, nota))
            continue
        if ind["canale"] == "<cataloghi>":
            mancanti = [c for c in cataloghi if not os.path.exists(os.path.join(copia_s4me, "channels", c + ".py"))]
            if mancanti:
                esito, nota = "riserva", "canali assenti in s4me: %s" % ", ".join(mancanti)
        elif ind["canale"] == "search":
            if ind["azione"] not in _funzioni(os.path.join(copia_s4me, "specials", "search.py")):
                esito, nota = "rotto", "specials/search.py non ha %s" % ind["azione"]
        else:
            funzioni = _funzioni(os.path.join(copia_s4me, "channels", ind["canale"] + ".py"))
            if not funzioni:
                esito, nota = "rotto", "s4me non ha il canale %s" % ind["canale"]
            elif ind["azione"] == "search":
                esito, nota = "riserva", "action=search da un indirizzo riapre la tastiera (launcher.search)"
            elif ind["azione"] not in funzioni and ind["azione"] not in launcher:
                esito, nota = "rotto", "il canale %s non ha %s" % (ind["canale"], ind["azione"])
        if ind["formato"] == "in chiaro" and esito == "regge":
            esito, nota = "riserva", "indirizzo in chiaro: s4me scrive un errore a ogni apertura"
        verso_s4me.append((ind, esito, nota))
    for lista, verso, cosa in ((verso_lesaghe, "lesaghe", "indirizzi s4me verso il nostro canale (findvideos, cinema_fonti, cerca_siti, verifica_film)"),
                               (verso_s4me, "s4me", "indirizzi s4me verso i cataloghi e i canali di s4me")):
        stato = _peggiore([e for _i, e, _n in lista]) if lista else "ignoto"
        freccia("main" if verso == "lesaghe" else "main", verso, cosa,
                "che il canale e l'azione esistano davvero dall'altra parte, con la testa codificata",
                {app: stato for app in presenti},
                ["%s -> %s/%s [%s]%s" % (i["dove"], i["canale"], i["azione"], i["formato"], (" - " + n) if n else "")
                 for i, _e, n in sorted(lista, key=lambda x: ["rotto", "riserva", "regge"].index(x[1]))])

    # 6. s4me -> lesaghe: il nostro canale dentro s4me
    per, prove = {}, []
    sorgente_md5 = (s4.get("nostro_canale") or {}).get("testo_md5", "")
    for app in presenti:
        d = s4_app.get(app) or {}
        if not d.get("installato"):
            per[app] = "rotto"
            prove.append("%s: s4me non installato" % app)
        elif not d.get("lesaghe_md5"):
            per[app] = "rotto"
            prove.append("%s: channels/lesaghe.py non c'e' (il custode non l'ha messo)" % app)
        elif d["lesaghe_md5"] != sorgente_md5:
            per[app] = "riserva"
            prove.append("%s: lesaghe.py e' una versione diversa dal sorgente (riavviare Kodi: il custode lo ricopia)" % app)
        else:
            per[app] = "regge"
    freccia("s4me", "lesaghe", "il file channels/lesaghe.py messo dal custode",
            "che ci sia e sia uguale al sorgente", per, prove or ["uguale al sorgente su tutti gli apparecchi"])

    # 7. lesaghe -> siti
    nostro = s4.get("nostro_canale") or {}
    usati = set(nostro.get("CANALI_FILM") or [])
    for v in (nostro.get("CANALI_PER_TIPO") or {}).values():
        usati.update(v)
    per, prove = {}, []
    for app in presenti:
        d = s4_app.get(app) or {}
        canali = d.get("canali") or {}
        assenti = sorted(c for c in usati if c not in canali)
        spenti = sorted(c for c in usati if c in canali and not canali[c].get("acceso"))
        errori = {c: e for c, e in ((d.get("registro") or {}).get("canali_in_errore") or {}).items()
                  if c in usati and e.get("volte_adesso")}
        per[app] = "rotto" if len(assenti) > len(usati) / 2 else ("riserva" if assenti or errori else ("regge" if canali else "ignoto"))
        if assenti:
            prove.append("%s: assenti in s4me %s" % (app, ", ".join(assenti)))
        if spenti:
            prove.append("%s: spenti da s4me (siti morti), il canale li salta da solo: %s" % (app, ", ".join(spenti)))
        for c, e in errori.items():
            prove.append("%s: %s in errore x%d (%s)" % (app, c, e["volte"], e["errore"][:80]))
    freccia("lesaghe", "siti", "canale.search(testo), episodios(), findvideos() sui canali di s4me",
            "che i canali delle nostre liste ci siano, siano accesi e rispondano", per, prove)

    # 8. s4me -> server
    per, prove = {}, []
    for app in presenti:
        srv = ((s4_app.get(app) or {}).get("registro") or {}).get("server") or {}
        if not srv:
            per[app] = "ignoto"
            continue
        brutti = {k: v for k, v in srv.items() if v["brutti"] and v["brutti"] >= v["tentativi"] / 2.0}
        schermo = [k for k, v in brutti.items() if v["esiti"].get("riquadro d'errore a schermo")]
        per[app] = "rotto" if schermo else ("riserva" if brutti else "regge")
        for k, v in sorted(srv.items(), key=lambda x: -x[1]["tentativi"])[:8]:
            prove.append("%s: %s %d tentativi - %s%s" % (app, k, v["tentativi"], ", ".join("%s %d" % e for e in v["esiti"].items()),
                                                         (" - link cancellati %d/%d" % (v["link_cancellati"], v["link_provati"]))
                                                         if v.get("link_provati") else ""))
    freccia("s4me", "server", "resolve_video_urls_for_playing(server, url)",
            "un file video che parte; se il server lo ha cancellato, che si passi a un altro senza riquadri",
            per, prove)

    # 9. lesaghe -> resolveurl
    per = {app: ("regge" if (s4_app.get(app) or {}).get("resolveurl") else "riserva") for app in presenti}
    freccia("lesaghe", "resolveurl", "resolveurl.HostedMediaFile(url).resolve() quando s4me non ce la fa",
            "che ResolveURL sia installato (e aggiornato dal suo repository)", per,
            ["%s: %s" % (app, "installato" if v == "regge" else "NON installato") for app, v in per.items()])

    # 10. servizio -> rete (le cache)
    per, prove = {}, []
    attese = ("netflix_cache.json", "cinema.json", "loghi_tmdb.json", "dettagli_tmdb.json")
    for app in presenti:
        cart = os.path.join(copie, app, "userdata", "addon_data", "plugin.video.saghe")
        ci_sono = [f for f in attese if os.path.exists(os.path.join(cart, f))]
        per[app] = "regge" if len(ci_sono) >= 3 else ("riserva" if ci_sono else "rotto")
        prove.append("%s: cache presenti %s" % (app, ", ".join(ci_sono) or "nessuna"))
    freccia("servizio", "rete", "TMDb /discover, /movie/now_playing, /images, TVmaze, fanart.tv",
            "risposte JSON; il servizio le scrive in cache e le righe leggono solo la cache", per, prove)

    # 11. servizio -> lesaghe: il controllore dei film
    per, prove = {}, []
    for app in presenti:
        dati = _json(os.path.join(copie, app, "userdata", "addon_data", "plugin.video.saghe", "disponibilita.json"))
        if dati is None:
            per[app] = "ignoto"
            prove.append("%s: il controllore non ha ancora scritto niente" % app)
        else:
            pronti = sum(1 for v in dati.values() if v.get("stato") == "pronto")
            per[app] = "regge"
            prove.append("%s: %d film controllati, %d pronti, %d non ancora in streaming" % (app, len(dati), pronti, len(dati) - pronti))
    freccia("servizio", "lesaghe", "Files.GetDirectory su lesaghe.verifica_film (quando la TV non si usa)",
            "l'esito in special://temp/videoteca-verifica.json, senza aprire niente a schermo", per, prove)

    # 12. skin -> schede
    per, prove = {}, []
    for app in presenti:
        k = app_k[app] or {}
        errori = [e for e in ((k.get("registro") or {}).get("errori_python") or [])
                  if e.get("addon", "").startswith(("plugin.video.themoviedb.helper", "script.embuary")) and e.get("volte_adesso")]
        addon = k.get("addons") or {}
        accesi = all((addon.get(x) or {}).get("acceso") is not False for x in ("script.embuary.info", "plugin.video.themoviedb.helper") if x in addon)
        per[app] = "riserva" if errori else ("regge" if accesi else "rotto")
        for e in errori[:3]:
            prove.append("%s: %s %s x%d" % (app, e["addon"], e["tipo"], e["volte_adesso"]))
    freccia("skin", "schede", "RunScript(script.embuary.info,...) e le righe di TMDb Helper",
            "schede in italiano e risposte valide da TMDb", per, prove)

    # 13. kodi -> repo -> github
    per, prove = {}, []
    for app in presenti:
        k = app_k[app] or {}
        testo_errori = " ".join(m for m, _n in ((k.get("registro") or {}).get("errori") or []))
        rotto = "kodi-s4me-addon-personale" in testo_errori and ("failed read" in testo_errori or "Failed with code 404" in testo_errori)
        presente = "repository.videoteca" in (k.get("addons") or {})
        per[app] = "rotto" if rotto else ("regge" if presente else "rotto")
        if rotto:
            prove.append("%s: nel registro 'CRepository: failed read' sul nostro repository (niente aggiornamenti)" % app)
        elif not presente:
            prove.append("%s: repository.videoteca non installato" % app)
    freccia("kodi", "repo", "addons.xml del repository (una volta al giorno o col pulsante Cerca aggiornamenti)",
            "che il repository sia installato, acceso e leggibile", per, prove or ["leggibile su tutti"])
    freccia("repo", "github", "raw.githubusercontent.com/Alcafer2011/kodi-s4me-addon-personale (privato, con token)",
            "addons.xml e gli zip; senza <checksum>, che Kodi chiedeva senza password (404)",
            dict(per), list(prove))

    # 14. s4me -> github (si aggiorna da solo)
    per, prove = {}, []
    a_monte = (s4.get("a_monte") or {}).get("s4me_ultimo") or {}
    for app in presenti:
        d = s4_app.get(app) or {}
        ultimi = ((d.get("registro") or {}).get("aggiornamenti") or [])
        dietro = a_monte.get("commit") and d.get("commit") and not a_monte["commit"].startswith(d["commit"][:10])
        per[app] = "riserva" if dietro else ("regge" if ultimi or d.get("commit") else "ignoto")
        prove.append("%s: commit %s%s" % (app, (d.get("commit") or "?")[:10], ("; ultimo controllo: %s" % ultimi[-1]["testo"]) if ultimi else ""))
    if a_monte:
        prove.append("su GitHub (stable): %s del %s - %s" % (a_monte.get("commit", "")[:10], a_monte.get("data", "")[:10], a_monte.get("messaggio", "")))
    freccia("s4me", "github", "api.github.com/repos/stream4me/addon/commits?sha=stable (updater.check all'avvio)",
            "che s4me insegua i siti che cambiano dominio", per, prove)

    # 15. guardiano -> kodi
    per, prove = {}, []
    for app in presenti:
        g = (app_k[app] or {}).get("guardiano")
        if not g:
            per[app] = "riserva"
            prove.append("%s: nessuno stato del guardiano" % app)
            continue
        testo = json.dumps(g, ensure_ascii=False)
        per[app] = "riserva" if re.search(r'"(critico|alto|rosso)"', testo) else "regge"
        prove.append("%s: ultimo giro %s" % (app, g.get("quando", "?")))
    freccia("guardiano", "kodi", "controlli ogni 15 minuti + scatola nera (stato.json)",
            "Videoteca intera, menu presente, nessun errore nuovo", per, prove)

    svg = disegna(frecce)
    return {"nodi": [{"id": i, "nome": n, "spiega": s} for i, n, _c, _r, s in NODI], "frecce": frecce, "svg": svg,
            "indirizzi_s4me": indirizzi}


# ---------------------------------------------------------------------------- il disegno

def disegna(frecce):
    larg, alt, passo_x, passo_y, w, h = 1040, 430, 208, 96, 176, 54
    pos = {i: (18 + c * passo_x, 40 + r * passo_y) for i, _n, c, r, _s in NODI}
    parti = ['<svg viewBox="0 0 %d %d" class="graf mappa" role="img" style="max-width:100%%"><title>Mappa dei dialoghi</title>' % (larg, alt),
             '<defs><marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
             '<path d="M0 0L10 5L0 10z" fill="#607d8b"/></marker></defs>']
    colonne = ["Kodi", "Skin e menu", "Videoteca", "s4me e risolutori", "Internet"]
    for c, nome in enumerate(colonne):
        parti.append('<text x="%d" y="22" class="etic" style="font-weight:700">%s</text>' % (18 + c * passo_x, html.escape(nome)))
    etichette = []
    for f in frecce:
        if f["da"] not in pos or f["a"] not in pos:
            continue
        (x1, y1), (x2, y2) = pos[f["da"]], pos[f["a"]]
        if x2 > x1:
            ax, ay, bx, by = x1 + w, y1 + h / 2, x2, y2 + h / 2
            c1x, c1y, c2x, c2y = ax + 50, ay, bx - 50, by
        elif x2 < x1:
            ax, ay, bx, by = x1, y1 + h / 2, x2 + w, y2 + h / 2
            c1x, c1y, c2x, c2y = ax - 50, ay, bx + 50, by
        else:
            giu = y2 > y1
            ax, ay = x1 + w * 0.25, (y1 + h) if giu else y1
            bx, by = x2 + w * 0.25, y2 if giu else (y2 + h)
            c1x, c1y, c2x, c2y = ax - 30, ay, bx - 30, by
        colore = COLORI[f["stato"]]
        parti.append('<path d="M%.0f %.0f C%.0f %.0f %.0f %.0f %.0f %.0f" fill="none" stroke="%s" stroke-width="3"%s marker-end="url(#punta)"/>'
                     % (ax, ay, c1x, c1y, c2x, c2y, bx, by, colore, ' stroke-dasharray="6 4"' if f["stato"] == "ignoto" else ""))
        t = 0.5
        mx = (1 - t) ** 3 * ax + 3 * (1 - t) ** 2 * t * c1x + 3 * (1 - t) * t ** 2 * c2x + t ** 3 * bx
        my = (1 - t) ** 3 * ay + 3 * (1 - t) ** 2 * t * c1y + 3 * (1 - t) * t ** 2 * c2y + t ** 3 * by
        etichette.append('<circle cx="%.0f" cy="%.0f" r="10" fill="%s"/><text x="%.0f" y="%.0f" text-anchor="middle" '
                         'style="font-size:11px;font-weight:700;fill:#fff">%d</text>' % (mx, my, colore, mx, my + 4, f["n"]))
    for i, nome, _c, _r, spiega in NODI:
        x, y = pos[i]
        stati = [f["stato"] for f in frecce if i in (f["da"], f["a"])]
        bordo = COLORI[_peggiore(stati)] if stati else "#90a4ae"
        parti.append('<g><title>%s</title><rect x="%d" y="%d" width="%d" height="%d" rx="9" fill="#fff" stroke="%s" stroke-width="2"/>'
                     '<text x="%d" y="%d" text-anchor="middle" style="font-size:12.5px;font-weight:600;fill:#263238">%s</text></g>'
                     % (html.escape(spiega), x, y, w, h, bordo, x + w / 2, y + h / 2 + 4, html.escape(nome)))
    parti.extend(etichette)
    legenda = [("regge", "regge"), ("riserva", "regge con riserva"), ("rotto", "rotto"), ("ignoto", "non verificabile")]
    for j, (k, testo) in enumerate(legenda):
        parti.append('<rect x="%d" y="%d" width="22" height="6" fill="%s"/><text x="%d" y="%d" class="etic">%s</text>'
                     % (18 + j * 190, alt - 16, COLORI[k], 46 + j * 190, alt - 9, testo))
    parti.append("</svg>")
    return "".join(parti)


def problemi(mappa):
    fuori = []
    nomi = {i: n for i, n, _c, _r, _s in NODI}
    for f in mappa.get("frecce") or []:
        if f["stato"] not in ("rotto", "riserva"):
            continue
        apps = [a for a, s in f["per_app"].items() if s == f["stato"]]
        fuori.append({"livello": "alto" if f["stato"] == "rotto" else "basso", "tipo": "incoerenza", "area": "addon",
                      "titolo": "Dialogo %s: %s -> %s (freccia %d, %s)" % (NOMI_STATO[f["stato"]], nomi.get(f["da"], f["da"]),
                                                                          nomi.get(f["a"], f["a"]), f["n"], ", ".join(apps)),
                      "dettaglio": "Con cosa: %s\nChi chiama si aspetta: %s\n\n%s" % (f["cosa"], f["aspetta"], "\n".join(f["prove"])),
                      "dove": [], "rimedio": "Vedi la mappa dei dialoghi nel rapporto, freccia %d." % f["n"]})
    return fuori
