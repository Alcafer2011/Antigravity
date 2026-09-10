# -*- coding: utf-8 -*-
"""REGOLE: da tutti i risultati a un ELENCO UNICO di problemi, e le regole di casa.

Ogni problema (reperto):
    id        SAG-001...
    livello   critico | alto | medio | basso | info
    tipo      malfunzionamento | instabilita | vulnerabilita | incoerenza |
              prestazioni | aspetto | manutenzione
    area      addon | codice | menu | pc | box | pi
    titolo, dettaglio, dove [file:riga], rimedio, regola

LE REGOLE DI CASA sono le lezioni pagate care in queste settimane. Ognuna ha
la data in cui e' stata imparata e un controllo automatico: se il controllo
non si puo' fare dai file, lo dice ("da verificare a mano").
"""

import collections
import os

LIVELLI = ["critico", "alto", "medio", "basso", "info"]
PESO = {"critico": 25, "alto": 10, "medio": 4, "basso": 1, "info": 0}
ART_IMPORTANTI = {"poster", "fanart", "thumb", "landscape", "clearlogo", "banner", "keyart",
                  "clearart", "icon", "discart", "characterart"}
ADDON_CHIAVE = {"plugin.video.saghe": "critico", "skin.arctic.zephyr.mod": "critico",
                "script.skinshortcuts": "critico", "plugin.video.s4me": "alto",
                "script.embuary.helper": "alto", "script.embuary.info": "medio",
                "plugin.video.themoviedb.helper": "alto", "inputstream.adaptive": "alto",
                "pvr.iptvsimple": "medio", "plugin.video.youtube": "medio", "skin.saghe": "medio"}
ERRORI_CHE_ROMPONO = ("ImportError", "ModuleNotFoundError", "NameError", "SyntaxError", "PermissionError",
                      "AttributeError", "TypeError", "KeyError", "IndentationError")


class _Elenco(object):
    def __init__(self):
        self.voci = []

    def aggiungi(self, livello, tipo, area, titolo, dettaglio="", dove=None, rimedio="", regola=""):
        self.voci.append({"livello": livello, "tipo": tipo, "area": area, "titolo": titolo,
                          "dettaglio": dettaglio, "dove": [d for d in (dove or []) if d][:15],
                          "rimedio": rimedio, "regola": regola})


def _addon(e, a):
    for s in a["errori_sintassi"]:
        e.aggiungi("critico", "malfunzionamento", "addon", "Errore di sintassi", s, [s],
                   "Correggere: il modulo non si carica e tutto quello che lo importa cade.")
    for az in a["azioni_senza_gestore"]:
        e.aggiungi("alto", "malfunzionamento", "addon", "Collegamento a un'azione che non esiste: %s" % az,
                   "Una voce porta a azione=%s ma il router di main.py non la gestisce: premendo OK si riapre "
                   "il menu senza errori (successo con 'riproduci' il 07/09)." % az,
                   a["azioni_collegate"].get(az), "Aggiungere il ramo nel router o correggere il nome.",
                   "ogni collegamento porta a un'azione esistente")
    for c in a["runscript_senza_comando"]:
        e.aggiungi("alto", "malfunzionamento", "addon", "RunScript con un comando sconosciuto: %s" % c,
                   "avvio.py non ha il comando: scrive solo 'comando sconosciuto' nel registro.",
                   a["runscript_usati"].get(c), "Aggiungere il comando in avvio.main().", "ogni RunScript ha il suo comando")
    imp = a["impostazioni"]
    for k in imp["senza_default"]:
        e.aggiungi("alto", "malfunzionamento", "addon", "Impostazione senza valore predefinito: %s" % k,
                   "Kodi scarta le impostazioni senza <default> ('unable to read setting', 10/09).",
                   ["resources/settings.xml"],
                   "Aggiungere <default/> (e <constraints><allowempty>true</allowempty></constraints> se puo' essere vuota).",
                   "impostazioni dichiarate con default")
    for k in imp["usate_non_dichiarate"]:
        e.aggiungi("medio", "malfunzionamento", "addon", "Impostazione letta ma non dichiarata: %s" % k,
                   "getSetting restituisce sempre stringa vuota: il codice crede che sia 'spenta'.",
                   imp["usate"].get(k), "Dichiararla in resources/settings.xml o togliere la lettura.")
    if imp["dichiarate_mai_usate"]:
        e.aggiungi("basso", "manutenzione", "addon", "Impostazioni dichiarate e mai lette (%d)" % len(imp["dichiarate_mai_usate"]),
                   ", ".join(imp["dichiarate_mai_usate"]), ["resources/settings.xml"],
                   "Toglierle o collegarle: l'utente le cambia e non succede niente.")

    # finestre: il rischio dipende da DOVE arriva l'azione
    per_funzione = collections.OrderedDict()
    for f in a["finestre_in_cartella"]:
        if f.get("rischio") == "nessuno":
            continue
        per_funzione.setdefault((f["funzione"], f.get("rischio")), []).append(f)
    for (fn, rischio), lista in per_funzione.items():
        liv = {"cartella": "alto", "voce": "medio"}.get(rischio, "basso")
        # Il crollo del 06/09 veniva da barre di avanzamento e finestre di altri
        # add-on sopra la rotellina di Kodi. Una tastiera o un si'/no da una
        # cartella sono comuni e reggono: pesano meno.
        pesanti = {x["chiamata"] for x in lista} & {"DialogProgress", "xbmcgui.DialogProgress", "WindowXML",
                                                     "WindowXMLDialog", "WindowDialog", "Dialog.doModal",
                                                     "DialogProgress.doModal", "xbmcgui.WindowXML", "xbmcgui.WindowXMLDialog"}
        if liv == "alto" and not pesanti:
            liv = "medio"
        azioni = sorted({x for f in lista for x in f.get("azioni", [])})
        ctx = sorted({x for f in lista for x in f.get("contesti", [])})
        e.aggiungi(liv, "instabilita", "addon", "Finestra aperta dentro una cartella: %s()" % fn,
                   "Si aprono %s. Azioni che arrivano qui: %s (collegate come: %s). %s" % (
                       ", ".join(sorted({x["chiamata"] for x in lista})), ", ".join(azioni) or "nessuna trovata",
                       ", ".join(ctx) or "?",
                       {"cartella": "Da una CARTELLA Kodi ha gia' la sua rotellina davanti: rischio dei due busydialog "
                                    "che chiudono Kodi (06/09) o di riquadri che si ripetono (10/09).",
                        "voce": "Da una voce da riprodurre: la finestra compare mentre Kodi aspetta il video.",
                        }.get(rischio, "Non si e' capito chi la chiama: da verificare.")),
                   [x["dove"] for x in lista],
                   "Chiudere subito la cartella e fare il lavoro in avvio.py con RunScript (vedi _in_disparte)."
                   if rischio == "cartella" else "Verificare il percorso e, se serve, spostare in avvio.py.",
                   "dentro una cartella solo elenchi" if rischio == "cartella" else "")
    senza = {c["funzione"] for c in a["cartelle_senza_contenuto"]}
    for r in a["refresh_in_cartella"]:
        if r.get("rischio") == "nessuno":
            continue
        grave = r.get("rischio") == "cartella" and r["funzione"] in senza
        liv = "alto" if grave else ("medio" if r.get("rischio") == "cartella" else "basso")
        e.aggiungi(liv, "instabilita", "addon", "Container.Refresh in main.py: %s()" % r["funzione"],
                   ("Azioni: %s (collegate come %s). " % (", ".join(r.get("azioni", [])) or "?", ", ".join(r.get("contesti", [])) or "?")) +
                   ("La funzione chiude la cartella senza contenuto e poi fa Refresh: Kodi rilegge la stessa cartella "
                    "e rifa' l'azione (il ciclo del tasto OK, 10/09)." if grave else
                    "Un Refresh lanciato da qui rilegge la pagina corrente: verificare che non sia quella che ha eseguito l'azione."),
                   [r["dove"]], "Spostare il Refresh in avvio.py e farlo solo sulla home.",
                   "nessun Refresh che rilegge la cartella che l'ha lanciato" if grave else "")
    for r in a["rete_nelle_righe"]:
        e.aggiungi("alto", "prestazioni", "addon", "Una riga della home va in rete", " -> ".join(r["catena"]), [],
                   "Leggere solo dalla cache e far riempire la cache al servizio.", "le righe della home non vanno mai in rete")
    for r in a["risorse_mancanti"]:
        e.aggiungi("alto", "malfunzionamento", "addon", "Risorsa mancante: %s" % r["file"], "", r["dove"],
                   "Creare il file o correggere il nome.")
    m = a.get("menu") or {}
    for s in m.get("senza_target", []):
        e.aggiungi("critico", "malfunzionamento", "menu", "Riga della home senza target: %s" % s,
                   "Senza widgetTarget il tasto OK non apre niente e nessun registro lo dice (10/09).",
                   ["traduttore/menu-arctic/skin.arctic.zephyr.mod.properties"], "Rigenerare con fai-menu-arctic.py.",
                   "ogni riga della home ha target")
    for s in m.get("spente", []):
        e.aggiungi("medio", "malfunzionamento", "menu", "Riga del menu nascosta: %s" % s,
                   "Le righe 2-6 senza widgetEnable.N=yes non compaiono.",
                   ["traduttore/menu-arctic/skin.arctic.zephyr.mod.properties"], "widgetEnable.N=yes")
    for c in m.get("che_non_gestiti", []):
        e.aggiungi("alto", "malfunzionamento", "menu", "Riga del menu che l'add-on non conosce: che=%s" % c,
                   "widget() non ha un ramo per questo valore: la riga resta vuota.", ["traduttore/menu-arctic"],
                   "Aggiungere il ramo in widget() o correggere il menu.")


def _codice(e, c, cartella_addon):
    minori = collections.defaultdict(list)
    non_definiti = collections.defaultdict(list)
    for r in c["reperti"]:
        dove = "%s:%s" % (r["file"], r["riga"])
        if r["controllo"] == "pyflakes" and "undefined name" in r["testo"]:
            non_definiti[(r["file"], r["testo"])].append(dove)
            continue
        if r["livello"] in ("basso", "info") and r["controllo"] in ("pyflakes", "instabilita"):
            minori[(r["file"], r["controllo"], r["dettaglio"], r["livello"], r["tipo"])].append("%s  %s" % (dove, r["testo"]))
            continue
        e.aggiungi(r["livello"], r["tipo"], "codice", "%s: %s" % (r["controllo"], r["dettaglio"] or r["testo"]),
                   r["testo"], [dove], "")
    for (f, testo), dove in non_definiti.items():
        nome = testo.split("'")[1] if "'" in testo else testo
        esiste = os.path.exists(os.path.join(cartella_addon, "resources", "lib", nome + ".py"))
        e.aggiungi("critico", "malfunzionamento", "codice", "Nome non definito: %s in %s (%d punti)" % (nome, f, len(dove)),
                   "Appena l'esecuzione passa da una di queste righe Python si ferma con NameError e a schermo "
                   "compare l'errore dello script. %s" % (
                       "Il modulo resources/lib/%s.py esiste ma non e' importato qui." % nome if esiste else
                       "Non esiste nessun modulo con questo nome: e' stato tolto (per ponte_s4me: commit 77d75a7, "
                       "'Diradamento') ma le chiamate sono rimaste."),
                   dove, "Importare il modulo o sostituire le chiamate (per s4me: plugin://plugin.video.s4me/?channel=search&action=Search&search_text=...).")
    for (f, controllo, dettaglio, livello, tipo), righe in minori.items():
        e.aggiungi(livello, tipo, "codice", "%s in %s: %s (%d)" % (controllo, f, dettaglio, len(righe)),
                   "\n".join(righe[:40]), [x.split("  ")[0] for x in righe], "")


def _apparecchio(e, app, k):
    if k.get("errore"):
        e.aggiungi("alto", "incoerenza", app, "Apparecchio non analizzato", k["errore"], [],
                   "Rilanciare: python atlante.py raccogli %s" % app)
        return
    if k.get("database_mancante"):
        e.aggiungi("info", "manutenzione", app, "Database degli add-on non raccolto",
                   "Senza Addons*.db non si sa chi e' acceso e chi no.", [], "Rilanciare la raccolta.")
    if not (k.get("registro") or {}).get("righe"):
        e.aggiungi("info", "manutenzione", app, "Nessun registro di Kodi raccolto",
                   "Senza kodi.log non si vedono gli errori a tempo di esecuzione.", [], "Rilanciare la raccolta.")
    addons = k.get("addons") or {}
    if k.get("skin_attiva") != "skin.arctic.zephyr.mod":
        e.aggiungi("alto", "incoerenza", app, "Skin attiva: %s (non Arctic Zephyr)" % (k.get("skin_attiva") or "?"),
                   "La home con menu, righe e loghi e' fatta per Arctic Zephyr: con un'altra skin la TV mostra ancora "
                   "la home vecchia (segnalato dall'utente l'11/09).", ["userdata/guisettings.xml"],
                   "A Kodi SPENTO: lookandfeel.skin=skin.arctic.zephyr.mod senza default=\"true\", add-on accesi nel DB.",
                   "stessa skin e stesso menu su tutti gli apparecchi")
    for aid, liv in ADDON_CHIAVE.items():
        a = addons.get(aid)
        if a and a.get("acceso") is False:
            e.aggiungi(liv, "malfunzionamento", app, "Add-on spento nel database: %s" % aid,
                       "Motivo nel DB: %s. Un add-on copiato a mano a Kodi acceso resta spento (10/09)." % a.get("motivo_spento"),
                       ["userdata/Database/%s" % k.get("database")],
                       "UPDATE installed SET enabled=1 WHERE addonID='%s' a Kodi spento." % aid)
    if k["conteggio"]["senza_riga_nel_db"]:
        e.aggiungi("medio", "incoerenza", app, "Add-on senza riga nel database (%d)" % len(k["conteggio"]["senza_riga_nel_db"]),
                   ", ".join(k["conteggio"]["senza_riga_nel_db"]), [],
                   "Kodi li registra al prossimo avvio, spesso SPENTI: controllare dopo il riavvio.")
    for d in k["dipendenze_rotte"]:
        forse = "forse" in d["problema"]
        e.aggiungi("basso" if forse else "alto", "malfunzionamento", app,
                   "Dipendenza %s: %s -> %s" % ("da verificare" if forse else "rotta", d["addon"], d["dipendenza"]),
                   "%s (richiesta %s). Se manca davvero, Kodi spegne l'add-on che ne ha bisogno." % (d["problema"], d["richiesta"] or "-"),
                   [], "Installare/aggiornare %s dal repository ufficiale." % d["dipendenza"],
                   "" if forse else "tutte le dipendenze presenti e accese")
    for b in k["backup_in_addons"]:
        e.aggiungi("critico", "malfunzionamento", app, "Backup dentro addons/: %s" % b,
                   "Kodi scandisce addons/ per cartelle: se il backup dichiara lo stesso id puo' girare QUELLO al posto "
                   "del codice nuovo (il fantasma del 10/09).", ["addons/%s" % b], "Spostarlo fuori da addons/.",
                   "nessun backup dentro addons/")
    if k.get("trailer_automatico") == "true" and not k.get("youtube_configurato"):
        e.aggiungi("alto", "instabilita", app, "Trailer automatico acceso e YouTube mai configurato",
                   "Il 10/09 alle 19:06 un trailer partito da solo ha installato YouTube e la sua procedura guidata "
                   "ha bloccato l'interfaccia.", ["addon_data/skin.arctic.zephyr.mod/settings.xml"],
                   "Spegnere home.netflix.autoplay.trailer o completare la procedura di YouTube.",
                   "trailer automatico spento finche' YouTube non e' configurato")
    elif "plugin.video.youtube" in addons and not k.get("youtube_configurato"):
        e.aggiungi("medio", "instabilita", app, "YouTube installato ma mai configurato",
                   "Al primo video parte la procedura guidata a finestre: se il video parte da una riga o da un "
                   "trailer puo' bloccare Kodi.", [], "Aprire YouTube una volta dalla TV e completarla.")
    if "skin.arctic.zephyr.mod" in addons and "mainmenu.DATA.xml" not in (k.get("menu_skinshortcuts") or []):
        attiva = k.get("skin_attiva") == "skin.arctic.zephyr.mod"
        e.aggiungi("critico" if attiva else "alto", "malfunzionamento", app, "Arctic Zephyr senza il menu della Videoteca",
                   "In addon_data/script.skinshortcuts ci sono solo: %s. Senza mainmenu.DATA.xml e .properties la home "
                   "mostra il menu di fabbrica (Film, Serie, Musica...) e nessuna riga della Videoteca.%s"
                   % (", ".join(k.get("menu_skinshortcuts") or []) or "niente",
                      " E la skin e' ATTIVA: e' quello che si vede in TV adesso." if attiva else ""),
                   ["userdata/addon_data/script.skinshortcuts/"],
                   "Copiare traduttore/menu-arctic/* e cancellare il .hash, poi riavviare Kodi.",
                   "stessa skin e stesso menu su tutti gli apparecchi")
    imp = k.get("impostazioni") or {}
    if (imp.get("services.webserver") or {}).get("valore") == "true" and \
            (imp.get("services.webserverauthentication") or {}).get("valore") == "false":
        e.aggiungi("medio", "vulnerabilita", app, "API di Kodi aperta senza password",
                   "Chiunque sulla rete puo' comandare Kodi (JSON-RPC sulla porta %s)." %
                   (imp.get("services.webserverport") or {}).get("valore", "8080"), ["userdata/guisettings.xml"],
                   "Accettabile solo sul banco PC; sugli apparecchi di casa mettere la password.", "API di Kodi protetta")
    if (imp.get("addons.unknownsources") or {}).get("valore") == "true":
        e.aggiungi("basso", "vulnerabilita", app, "Origini sconosciute accese",
                   "Si possono installare add-on da zip di chiunque.", [], "Tenerle spente quando non servono.")
    reg = k.get("registro") or {}
    for t in reg.get("errori_python", []):
        nostro = t["addon"] == "plugin.video.saghe"
        rompe = t["tipo"].split(".")[-1] in ERRORI_CHE_ROMPONO
        liv = ("critico" if rompe else "alto") if nostro else ("medio" if rompe else "basso")
        e.aggiungi(liv, "malfunzionamento", app, "%s in %s: %s" % (t["tipo"] or "Errore", t["addon"], t["contenuto"][:110]),
                   "Visto %d volte (prima %s, ultima %s). Funzione: %s.\n\n%s" % (
                       t["volte"], t["prima"], t["ultima"], t["funzione"] or "?", t["esempio"][:2200]),
                   [t["dove"]] if t["dove"] else [],
                   "Guardare la riga indicata: e' l'ultima dell'add-on prima dell'errore.",
                   "nessun errore Python dell'add-on nei registri" if nostro else "")
    inc = reg.get("include_invalidi") or []
    if inc:
        e.aggiungi("basso", "malfunzionamento", app, "Include della skin non trovati (%d)" % len(inc),
                   "; ".join("%s x%d" % x for x in inc[:12]) +
                   "\nAl primo avvio dopo aver tolto il .hash di skinshortcuts e' normale (si rigenera un secondo "
                   "dopo); se si ripete a ogni avvio la home resta vuota.", [], "")
    gravi = [x for x in reg.get("errori", []) if x[1] >= 20]
    if gravi:
        e.aggiungi("basso", "instabilita", app, "Errori ripetuti nel registro (%d tipi con 20+ volte)" % len(gravi),
                   "\n".join("%5dx  %s" % (n, msg) for msg, n in gravi[:25]), [], "")


def _incroci(e, app, x, k):
    if x.get("errore"):
        return
    mancanti = x["saghe_mancanti_sull_apparecchio"]
    py_mancanti = [f for f in mancanti if f.endswith(".py") and f != "resources/lib/anteprime.py"]
    altri = [f for f in mancanti if f not in py_mancanti]
    if py_mancanti:
        e.aggiungi("critico", "malfunzionamento", app, "Moduli della Videoteca mancanti: %s" % ", ".join(py_mancanti),
                   "Ogni pezzo di codice che li importa cade con ImportError: sulla TV righe vuote ed errori dello script.",
                   ["addons/plugin.video.saghe/" + f for f in py_mancanti],
                   "Reinstallare TUTTO plugin.video.saghe dal sorgente (non solo i file cambiati) e ridare i file a Kodi (chown sul box).",
                   "stesso codice su PC, box e Raspberry")
    if altri:
        e.aggiungi("basso" if altri == ["resources/lib/anteprime.py"] else "alto", "incoerenza", app,
                   "File della Videoteca non presenti sull'apparecchio (%d)" % len(altri), ", ".join(altri),
                   [], "anteprime.py esiste solo nel sorgente e non e' importato: si puo' ignorare." if altri == ["resources/lib/anteprime.py"]
                   else "Copiarli.", "")
    if x["saghe_diversi_dal_sorgente"]:
        ver = ((k or {}).get("addons") or {}).get("plugin.video.saghe", {}).get("versione", "?")
        e.aggiungi("alto", "incoerenza", app, "Sulla TV gira una Videoteca diversa dal sorgente (%d file, versione %s)"
                   % (len(x["saghe_diversi_dal_sorgente"]), ver),
                   ", ".join(x["saghe_diversi_dal_sorgente"][:40]), [],
                   "Reinstallare i file indicati (md5 diversi) o l'intero add-on.", "stesso codice su PC, box e Raspberry")
    for f, fonts in x["font_nostre_finestre_mancanti"].items():
        e.aggiungi("alto", "aspetto", app, "Carattere inesistente nella skin: %s usa %s" % (f, ", ".join(fonts)),
                   "Con un carattere che la skin non definisce il testo non si vede o usa un ripiego.",
                   ["resources/skins/Default/1080i/%s" % f], "Usare font13 (l'unico comune a tutte le skin di casa).",
                   "le finestre dell'add-on usano caratteri esistenti")
    mancano_art = [a for a in x["art_che_non_diamo"] if a in ART_IMPORTANTI]
    if mancano_art:
        e.aggiungi("medio", "aspetto", app, "Immagini che la skin cerca e le nostre voci non danno: %s" % ", ".join(mancano_art),
                   "Letti: %s" % ", ".join("%s x%d" % (a, x["art_lette_dalla_skin"].get(a, 0)) for a in mancano_art),
                   [], "Valutare setArt anche con queste chiavi dove la skin le usa (tessere, testata).")
    et = sorted(x["etichette_che_non_riempiamo"], key=lambda z: -z["volte"])[:14]
    if et:
        e.aggiungi("basso", "aspetto", app, "Dati delle voci che la skin mostra e non riempiamo (%d)" % len(x["etichette_che_non_riempiamo"]),
                   "\n".join("%s (serve %s) letto %d volte, es. %s" % (z["etichetta"], z["serve"], z["volte"], ", ".join(z["dove"]))
                             for z in et), [], "Riempire con l'InfoTag dove il dato esiste (anno, generi, durata...).")


REGOLE_DI_CASA = [
    ("le righe della home non vanno mai in rete", "10/09", "addon"),
    ("dentro una cartella solo elenchi", "06/09", "addon"),
    ("nessun Refresh che rilegge la cartella che l'ha lanciato", "10/09", "addon"),
    ("ogni riga della home ha target", "10/09", "menu"),
    ("ogni collegamento porta a un'azione esistente", "07/09", "addon"),
    ("ogni RunScript ha il suo comando", "10/09", "addon"),
    ("impostazioni dichiarate con default", "10/09", "addon"),
    ("nessun backup dentro addons/", "10/09", "apparecchi"),
    ("stesso codice su PC, box e Raspberry", "10/09", "apparecchi"),
    ("stessa skin e stesso menu su tutti gli apparecchi", "11/09", "apparecchi"),
    ("le finestre dell'add-on usano caratteri esistenti", "10/09", "apparecchi"),
    ("trailer automatico spento finche' YouTube non e' configurato", "10/09", "apparecchi"),
    ("tutte le dipendenze presenti e accese", "10/09", "apparecchi"),
    ("nessun errore Python dell'add-on nei registri", "sempre", "apparecchi"),
    ("API di Kodi protetta", "05/09", "apparecchi"),
    ("clearlogo = logo del titolo, mai del servizio", "10/09", "addon"),
    ("l'italiano prima di tutto", "sempre", "a mano"),
    ("Kodi sul PC sempre in finestra, mai a schermo intero", "10/09", "a mano"),
    ("sul box non si riavvia Kodi a TV spenta", "04/09", "a mano"),
]


def _clearlogo_servizio(cartella_addon):
    import io
    p = os.path.join(cartella_addon, "main.py")
    fuori = []
    if not os.path.exists(p):
        return fuori
    righe = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    for i, r in enumerate(righe):
        if "clearlogo" in r and "=" in r and not r.lstrip().startswith("#"):
            if "fonti.logo" in "\n".join(righe[max(0, i - 4):i + 1]):
                fuori.append("main.py:%d" % (i + 1))
    return fuori


def trova(R):
    e = _Elenco()
    _addon(e, R["addon"])
    _codice(e, R["codice"], R["cartella_addon"])
    for app, k in R["apparecchi"].items():
        _apparecchio(e, app, k)
    for app, x in R["incroci"].items():
        _incroci(e, app, x, R["apparecchi"].get(app))
    for dove in _clearlogo_servizio(R["cartella_addon"]):
        e.aggiungi("medio", "aspetto", "addon", "clearlogo con il logo del servizio",
                   "Su Arctic Zephyr il clearlogo e' la scritta del titolo: con fonti.logo compare il marchio Netflix/Prime.",
                   [dove], "Usare loghi.logo o _logo_titolo.", "clearlogo = logo del titolo, mai del servizio")
    ordine = {l: i for i, l in enumerate(LIVELLI)}
    voci = sorted(e.voci, key=lambda v: (ordine[v["livello"]], v["area"], v["titolo"]))
    for i, v in enumerate(voci, 1):
        v["id"] = "SAG-%03d" % i
    regole = []
    for nome, quando, ambito in REGOLE_DI_CASA:
        legate = [v["id"] for v in voci if v["regola"] == nome]
        stato = "da verificare a mano" if ambito == "a mano" else ("violata" if legate else "rispettata")
        regole.append({"regola": nome, "imparata": quando, "ambito": ambito, "stato": stato, "problemi": legate})
    conteggi = {}
    for v in voci:
        conteggi.setdefault(v["area"], collections.Counter())[v["livello"]] += 1
    # Salute graduata: non va mai a zero per tanti problemi piccoli, crolla coi critici.
    punteggi = {a: int(round(100.0 / (1 + sum(PESO[l] * n for l, n in c.items()) / 30.0))) for a, c in conteggi.items()}
    return voci, regole, {"conteggi": {a: dict(c) for a, c in conteggi.items()}, "punteggi": punteggi}
