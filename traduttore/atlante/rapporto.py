# -*- coding: utf-8 -*-
"""RAPPORTO: REPORT.html (da leggere come un PDF) e REQUISITI.html.

Solo HTML: l'utente legge nel browser (11/09/2026). Il contenuto si
costruisce UNA volta come elenco di blocchi (titolo, paragrafo, tabella,
grafico, codice, dettagli); _md() resta solo per chi volesse un testo.
I grafici sono SVG scritti a mano: niente librerie, niente internet.
"""

import base64
import collections
import datetime
import html
import io
import json
import os
import re

COLORI = {"critico": "#c62828", "alto": "#ef6c00", "medio": "#f9a825", "basso": "#1565c0", "info": "#78909c"}
EMOJI = {"critico": "🔴", "alto": "🟠", "medio": "🟡", "basso": "🔵", "info": "⚪"}
NOMI_TIPO = {"malfunzionamento": "Malfunzionamento", "instabilita": "Instabilità", "vulnerabilita": "Vulnerabilità",
             "incoerenza": "Incoerenza", "prestazioni": "Prestazioni", "aspetto": "Aspetto", "manutenzione": "Manutenzione"}
NOMI_AREA = {"addon": "Add-on (logica)", "codice": "Codice Python/XML", "menu": "Menu della home",
             "pc": "PC (banco)", "box": "Box 8K", "pi": "Raspberry"}
LIVELLI = ["critico", "alto", "medio", "basso", "info"]

RUOLI = {
    "skin.arctic.zephyr.mod": "La SKIN: disegna tutto. Legge le voci dell'add-on e le mette in tessere, testata, menu.",
    "skin.saghe": "La skin vecchia della Videoteca (Estuary ricolorata con Home.xml generata).",
    "skin.estuary": "La skin di fabbrica di Kodi.",
    "script.skinshortcuts": "Costruisce MENU e RIGHE della home di Arctic Zephyr dai file in addon_data (mainmenu.DATA.xml + .properties).",
    "script.embuary.helper": "Aiutante della skin: righe automatiche, proprietà della finestra, ricerca.",
    "script.embuary.info": "Schede dettaglio da TMDb (cast, trama, pulsanti); di fabbrica in inglese.",
    "plugin.video.themoviedb.helper": "Righe e informazioni da TMDb per la skin; trailer; lettori.",
    "plugin.video.saghe": "LA VIDEOTECA: catalogo, righe della home (azione=widget), ripresa, consigli, Netflix, loghi, avvisi.",
    "plugin.video.s4me": "Il MOTORE DELLE FONTI: 55 siti, trova e riproduce gli episodi; ospita il canale 'Le Saghe'.",
    "plugin.video.youtube": "YouTube: canali, trailer. Al primo avvio apre una procedura guidata a finestre.",
    "inputstream.adaptive": "Riproduce flussi DASH/HLS (Netflix, YouTube, molti siti).",
    "pvr.iptvsimple": "TV in diretta da liste M3U, con guida EPG.",
    "service.upnext": "Propone l'episodio successivo a fine visione.",
    "script.globalsearch": "Ricerca globale della skin.",
    "script.module.pil": "Elaborazione immagini: viaggia CON Kodi, non sta nel repository.",
    "plugin.video.netflix": "Netflix dentro Kodi.", "plugin.video.amazon-test": "Prime Video dentro Kodi.",
    "script.pannello8k": "Pannello del box: temperatura, stato, allarmi.",
    "script.traduttore.it": "Traduttore italiano degli add-on.",
    "repository.videoteca": "Il nostro repository: aggiornamenti automatici della Videoteca.",
}

SCHEMA_FLUSSO = """flowchart LR
  TV([Telecomando]) --> SKIN[Arctic Zephyr<br/>la skin]
  SS[script.skinshortcuts<br/>menu e righe] -->|include generati| SKIN
  MENU[(mainmenu.DATA.xml<br/>.properties)] --> SS
  SKIN -->|"content plugin://…?azione=widget&che=…"| MAIN[plugin.video.saghe<br/>main.py]
  MAIN -->|legge solo cache| CACHE[(addon_data<br/>netflix, consigli,<br/>cinema, loghi)]
  SERV[service.py<br/>servizio] -->|riempie in un filo| CACHE
  SERV -->|TMDb| NET((Internet))
  SKIN -->|OK su una tessera| MAIN
  MAIN -->|RunScript| AVVIO[avvio.py<br/>finestre, avvisi]
  MAIN -->|episodio| S4ME[plugin.video.s4me<br/>55 fonti]
  S4ME --> PLAYER[Lettore di Kodi<br/>inputstream.adaptive]
  SKIN --> EMB[embuary / TMDb Helper]
"""


# ---------------------------------------------------------------- blocchi

def titolo(t, livello=2, ancora=""):
    return {"t": "titolo", "testo": t, "livello": livello, "ancora": ancora or re.sub(r"\W+", "-", t.lower()).strip("-")}


def para(t):
    return {"t": "para", "testo": t}


def tabella(intestazione, righe, classe=""):
    return {"t": "tabella", "int": intestazione, "righe": righe, "classe": classe}


def codice(testo, lingua=""):
    return {"t": "codice", "testo": testo, "lingua": lingua}


def dettagli(sommario, blocchi):
    return {"t": "dettagli", "sommario": sommario, "blocchi": blocchi}


def grafico(svg, md):
    return {"t": "grafico", "svg": svg, "md": md}


def elenco(voci):
    return {"t": "elenco", "voci": voci}


def mermaid(testo):
    return {"t": "mermaid", "testo": testo}


# ---------------------------------------------------------------- grafici SVG

def _ciambella(valori, titolo_g):
    tot = sum(v for _, v, _ in valori) or 1
    import math
    cx, cy, r, s = 110, 110, 80, 34
    parti, ang = [], -math.pi / 2
    for nome, v, colore in valori:
        if not v:
            continue
        a2 = ang + 2 * math.pi * v / tot
        grande = 1 if a2 - ang > math.pi else 0
        x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2, y2 = cx + r * math.cos(a2 - 1e-6), cy + r * math.sin(a2 - 1e-6)
        parti.append('<path d="M%.1f %.1f A%d %d 0 %d 1 %.1f %.1f" stroke="%s" stroke-width="%d" fill="none"/>'
                     % (x1, y1, r, r, grande, x2, y2, colore, s))
        ang = a2
    legenda = "".join('<rect x="240" y="%d" width="14" height="14" fill="%s"/><text x="262" y="%d">%s: %d</text>'
                      % (40 + i * 26, c, 52 + i * 26, html.escape(n), v) for i, (n, v, c) in enumerate(valori))
    return ('<svg viewBox="0 0 420 230" class="graf" role="img"><title>%s</title>%s'
            '<text x="110" y="106" text-anchor="middle" class="grande">%d</text>'
            '<text x="110" y="128" text-anchor="middle" class="piccolo">problemi</text>%s</svg>'
            % (html.escape(titolo_g), "".join(parti), tot, legenda))


def _barre(valori, titolo_g, colore="#37474f", massimo=None, larghezza=560):
    massimo = massimo or max([v for _, v in valori] + [1])
    h = 26 * len(valori) + 20
    righe = []
    for i, (n, v) in enumerate(valori):
        w = int((larghezza - 230) * v / massimo) if massimo else 0
        c = colore(n) if callable(colore) else colore
        righe.append('<text x="0" y="%d" class="etic">%s</text><rect x="210" y="%d" width="%d" height="18" rx="3" fill="%s"/>'
                     '<text x="%d" y="%d" class="val">%s</text>'
                     % (22 + i * 26, html.escape(str(n))[:34], 8 + i * 26, max(w, 1), c, 216 + w, 22 + i * 26, v))
    return '<svg viewBox="0 0 %d %d" class="graf" role="img"><title>%s</title>%s</svg>' % (larghezza, h, html.escape(titolo_g), "".join(righe))


def _barre_md(valori, larghezza=30):
    massimo = max([v for _, v in valori] + [1])
    return "\n".join("`%-32s` %s %s" % (str(n)[:32], "█" * max(1 if v else 0, int(larghezza * v / massimo)), v) for n, v in valori)


def _salute_colore(p):
    return "#2e7d32" if p >= 80 else ("#f9a825" if p >= 50 else ("#ef6c00" if p >= 25 else "#c62828"))


# ---------------------------------------------------------------- contenuto

SEGNI_STATO = {"regge": "🟢 regge", "riserva": "🟠 riserva", "rotto": "🔴 ROTTO", "ignoto": "⚪ non verificabile"}


def _immagine(percorso, stile=""):
    try:
        with open(percorso, "rb") as f:
            dati = base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return ""
    tipo = "image/png" if percorso.lower().endswith(".png") else "image/jpeg"
    return '<img src="data:%s;base64,%s" style="%s" alt="">' % (tipo, dati, stile)


def _storia_svg(storia):
    """Problemi per livello, analisi dopo analisi: barre impilate."""
    ultime = storia[-12:]
    massimo = max([sum(s["conta"].values()) for s in ultime] + [1])
    larg, alt, fondo = 760, 250, 200
    passo = (larg - 60) / max(1, len(ultime))
    parti = ['<svg viewBox="0 0 %d %d" class="graf" role="img"><title>Andamento dei problemi</title>' % (larg, alt)]
    for i, s in enumerate(ultime):
        x = 50 + i * passo
        y = fondo
        for livello in reversed(LIVELLI):
            n = s["conta"].get(livello, 0)
            h = (fondo - 20) * n / massimo
            if n:
                parti.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" fill="%s"><title>%s: %d</title></rect>'
                             % (x, y - h, passo * 0.7, h, COLORI[livello], livello, n))
            y -= h
        parti.append('<text x="%.0f" y="%.0f" text-anchor="middle" class="val">%d</text>' % (x + passo * 0.35, y - 4, sum(s["conta"].values())))
        parti.append('<text x="%.0f" y="%d" text-anchor="middle" class="etic" style="font-size:10px">%s</text>'
                     % (x + passo * 0.35, fondo + 16, html.escape(s["quando"][5:16].replace("T", " "))))
    for j, livello in enumerate(LIVELLI):
        parti.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/><text x="%d" y="%d" class="etic">%s</text>'
                     % (50 + j * 120, alt - 18, COLORI[livello], 66 + j * 120, alt - 8, livello))
    parti.append("</svg>")
    return "".join(parti)


def _sezioni_nuove(R):
    """A. mappa dei dialoghi, B. s4me visto da dentro, C. il logo, D. correzioni (11/09/2026)."""
    B = []
    mappa = R.get("dialoghi") or {}
    if mappa.get("frecce"):
        B.append(titolo("A. Chi parla con chi: la mappa dei dialoghi", ancora="mappa"))
        B.append(para("Ogni freccia e' un **contratto letto nei file**: chi chiama, con che cosa, cosa si aspetta, e la prova presa "
                      "dall'altra parte (il codice di chi risponde, il registro, lo stato del guardiano). **Verde** regge, "
                      "**arancio** regge con riserva, **rosso** e' rotto, **grigio** non si puo' verificare dai file. Il numero "
                      "sulla freccia rimanda alla tabella; il bordo di ogni riquadro prende il colore della sua freccia peggiore."))
        B.append(grafico(mappa["svg"], ""))
        nomi = {n["id"]: n["nome"] for n in mappa.get("nodi", [])}
        conta = collections.Counter(f["stato"] for f in mappa["frecce"])
        B.append(para("Frecce: %s." % ", ".join("%s %d" % (SEGNI_STATO[s], conta.get(s, 0)) for s in ("rotto", "riserva", "regge", "ignoto"))))
        B.append(tabella(["N.", "Chi chiama → chi risponde", "Con che cosa", "Chi chiama si aspetta", "Stato", "PC", "Box", "Pi"],
                         [[str(f["n"]), "%s → %s" % (nomi.get(f["da"], f["da"]), nomi.get(f["a"], f["a"])), f["cosa"], f["aspetta"],
                           SEGNI_STATO[f["stato"]]] + [SEGNI_STATO.get(f["per_app"].get(a, ""), "-").split(" ")[0] for a in ("pc", "box", "pi")]
                          for f in mappa["frecce"]]))
        for f in mappa["frecce"]:
            if f["prove"]:
                B.append(dettagli("Freccia %d: %s → %s — le prove (%s)" % (f["n"], nomi.get(f["da"], f["da"]), nomi.get(f["a"], f["a"]),
                                                                          SEGNI_STATO[f["stato"]]), [codice("\n".join(f["prove"]))]))

    s4 = R.get("s4me") or {}
    if s4.get("apparecchi"):
        B.append(titolo("B. s4me visto da dentro", ancora="s4me"))
        B.append(para("Com'e' fatto il motore delle fonti su ogni apparecchio, e cosa e' successo **davvero** quando lo si e' usato: "
                      "ogni tentativo su un server letto nel registro filo per filo, le cartelle che non si sono aperte, i canali "
                      "in errore. \"Adesso\" = dopo l'ultimo avvio di Kodi; il resto e' storico."))
        righe = []
        for app, d in s4["apparecchi"].items():
            if not d.get("installato"):
                righe.append([NOMI_AREA.get(app, app), "NON installato", "", "", "", "", "", ""])
                continue
            reg = d.get("registro") or {}
            righe.append([NOMI_AREA.get(app, app), d["versione"], (d.get("commit") or "")[:10],
                          "%d accesi su %d" % (sum(1 for c in d["canali"].values() if c["acceso"]), len(d["canali"])),
                          str(len(d["server"])), str((d.get("impostazioni") or {}).get("autoplay", "?")),
                          "sì" if d.get("resolveurl") else "NO",
                          "%d (adesso %d)" % (reg.get("indirizzi_in_chiaro", 0), reg.get("indirizzi_in_chiaro_adesso", 0))])
        B.append(tabella(["Apparecchio", "Versione", "Commit", "Canali", "Server", "Autoplay", "ResolveURL", "Indirizzi in chiaro"], righe))
        for app, d in s4["apparecchi"].items():
            if not d.get("installato"):
                continue
            reg = d.get("registro") or {}
            srv = reg.get("server") or {}
            blocchi = []
            if srv:
                val = [("%s (%d)" % (k, v["tentativi"]), v["brutti"]) for k, v in sorted(srv.items(), key=lambda x: -x[1]["tentativi"])[:15]]
                blocchi.append(para("**Tentativi andati male, server per server** (fra parentesi i tentativi in tutto):"))
                blocchi.append(grafico(_barre(val, "Tentativi andati male per server", "#c62828"), ""))
                blocchi.append(tabella(["Server", "Tentativi (adesso)", "Come sono finiti", "Link cancellati / provati", "Alternativa ResolveURL", "Ultimi indirizzi"],
                                       [[k, "%d (%d)" % (v["tentativi"], v.get("tentativi_adesso", 0)),
                                         ", ".join("%s %d" % e for e in v["esiti"].items()),
                                         "%s / %s" % (v.get("link_cancellati", "-"), v.get("link_provati", "-")),
                                         v.get("alternativa_resolveurl") or "-", ", ".join(v["indirizzi"][-3:])]
                                        for k, v in sorted(srv.items(), key=lambda x: -x[1]["tentativi"])]))
            if reg.get("cartelle_fallite"):
                blocchi.append(tabella(["Canale", "Azione", "Volte", "Adesso"],
                                       [[c["canale"], c["azione"], str(c["volte"]), str(c.get("volte_adesso", 0))] for c in reg["cartelle_fallite"]]))
            if reg.get("canali_in_errore"):
                blocchi.append(tabella(["Canale in errore", "Volte (adesso)", "Righe del codice", "Errore"],
                                       [[k, "%d (%d)" % (e["volte"], e.get("volte_adesso", 0)), ", ".join(str(r) for r in e["righe"][:6]), e["errore"]]
                                        for k, e in sorted(reg["canali_in_errore"].items(), key=lambda x: -x[1]["volte"])]))
            if reg.get("ricerche"):
                blocchi.append(tabella(["Quando", "Cosa ha deciso il nostro canale"], [[r["quando"], r["testo"]] for r in reg["ricerche"][-15:]]))
            blocchi.append(dettagli("Tutti i canali di s4me (%d)" % len(d["canali"]), [tabella(
                ["Canale", "Nome", "Acceso", "Lingue", "Categorie", "Dominio"],
                [[k, c["nome"], "sì" if c["acceso"] else "no", ", ".join(c["lingue"]), ", ".join(c["categorie"]), c.get("dominio", "")]
                 for k, c in sorted(d["canali"].items())])]))
            B.append(dettagli("%s — %d tentativi sui server, %d cartelle fallite, %d canali in errore"
                              % (NOMI_AREA.get(app, app), sum(v["tentativi"] for v in srv.values()),
                                 len(reg.get("cartelle_fallite") or []), len(reg.get("canali_in_errore") or {})), blocchi))
        a_m = s4.get("a_monte") or {}
        if a_m:
            B.append(titolo("A monte: chi aggiorna i collegamenti", 3))
            ultimo = a_m.get("s4me_ultimo") or {}
            B.append(para("**s4me** (github.com/stream4me/addon, ramo stable) si aggiorna da solo a ogni avvio: ultimo aggiornamento "
                          "**%s** — %s. I domini dei siti stanno in `channels.json`: e' li' che insegue i siti che cambiano indirizzo."
                          % ((ultimo.get("data") or "?")[:10], ultimo.get("messaggio", ""))))
            if a_m.get("s4me_server_toccati"):
                B.append(tabella(["Quando s4me ha toccato i server", "Cosa"], [[c["data"], c["messaggio"]] for c in a_m["s4me_server_toccati"]]))
            if a_m.get("resolveurl_plugin"):
                B.append(para("**ResolveURL** (github.com/Gujal00/ResolveURL) e' l'alternativa che si aggiorna da sola dal suo repository: "
                              "copre **%d** server. La Videoteca lo installa insieme a se' e il nostro canale lo prova quando un server di "
                              "s4me non da' il video." % len(a_m["resolveurl_plugin"])))
            if a_m.get("resolveurl_ultimi"):
                B.append(tabella(["Ultimi aggiornamenti di ResolveURL", "Cosa"], [[c["data"], c["messaggio"]] for c in a_m["resolveurl_ultimi"]]))
        if s4.get("domini_provati"):
            B.append(tabella(["Sito usato dal nostro canale", "Risposta adesso"], [[u, r] for u, r in sorted(s4["domini_provati"].items())]))

    logo = os.path.join(R.get("cartella_addon", ""), "resources", "media", "logo")
    if os.path.exists(os.path.join(logo, "marchio.png")):
        B.append(titolo("C. Il logo NOVIX", ancora="logo"))
        B.append(para("Scelto da te fra NOVIX, ZEFIRA, VIDORA e LUMIRA. La **N a nastro** prende il posto del logo di Kodi in alto a "
                      "sinistra di ogni schermata di Arctic Zephyr; all'accensione lo **splash** di Kodi e' la N, poi parte "
                      "l'**animazione** di 4,8 secondi col suo suono (il tuffo nella N che si scioglie in strisce di luce fino ai bordi, poi il ta-DUM) e si va dritti "
                      "alla home, senza piu' la schermata col logo di Arctic Zephyr. Lo cuce sulla skin `service.videoteca.guardiano/vestito.py`, e il guardiano lo ricuce se un "
                      "aggiornamento della skin lo toglie. Disegnato da `traduttore/fai-logo.py`."))
        B.append({"t": "html", "html": '<div style="background:#000;padding:30px;border-radius:10px;text-align:center">%s%s</div>'
                  % (_immagine(os.path.join(logo, "marchio.png"), "max-width:55%;vertical-align:middle"),
                     _immagine(os.path.join(logo, "monogramma.png"), "width:130px;margin-left:40px;vertical-align:middle"))})
        cartella_intro = os.path.join(logo, "intro")
        fotogrammi = sorted(os.listdir(cartella_intro)) if os.path.isdir(cartella_intro) else []
        scelti = [fotogrammi[i] for i in (10, 34, 46, 58, 70, 84, 96, 106, 112) if i < len(fotogrammi)]
        B.append(para("**L'animazione, fotogramma per fotogramma:**"))
        B.append({"t": "html", "html": '<div style="display:flex;flex-wrap:wrap;gap:6px">%s</div>'
                  % "".join(_immagine(os.path.join(cartella_intro, f), "width:32%;min-width:150px;border-radius:4px") for f in scelti)})
        stato_vestito = []
        for app in ("pc", "box", "pi"):
            skin = os.path.join(R.get("copie", ""), app, "addons", "skin.arctic.zephyr.mod", "1080i")
            esiti = []
            for nome, segno in (("Startup.xml", "videoteca-apertura-3"), ("Includes_Defs.xml", "videoteca-vestito-1")):
                p = os.path.join(skin, nome)
                if not os.path.exists(p):
                    esiti.append("manca")
                    continue
                with io.open(p, encoding="utf-8", errors="replace") as f:
                    testo = f.read()
                esiti.append("cucito" if segno in testo else ("versione 1 (3 s, poi il logo della skin)"
                                                              if "videoteca-vestito-1" in testo else "non ancora"))
            stato_vestito.append([NOMI_AREA.get(app, app), esiti[0], esiti[1]])
        B.append(tabella(["Apparecchio (copia dell'ultima raccolta)", "Apertura animata col suono (Startup.xml)", "N in ogni schermata (Kodi_Logo)"], stato_vestito))

    storia = R.get("storia") or []
    if storia:
        B.append(titolo("D. Correzioni: prima e dopo", ancora="correzioni"))
        B.append(para("Ogni analisi lascia la sua fotografia: qui come cambiano i problemi da una volta all'altra, e l'elenco di "
                      "quelli spariti e di quelli nuovi rispetto all'analisi precedente."))
        B.append(grafico(_storia_svg(storia), ""))
        if len(storia) >= 2:
            prima, dopo = storia[-2], storia[-1]
            spariti = sorted(set(prima["chiavi"]) - set(dopo["chiavi"]))
            nuovi = sorted(set(dopo["chiavi"]) - set(prima["chiavi"]))
            B.append(para("Rispetto all'analisi del **%s**: **%d problemi spariti**, **%d nuovi**." % (prima["quando"].replace("T", " "), len(spariti), len(nuovi))))
            if spariti:
                B.append(dettagli("✅ Spariti (%d)" % len(spariti), [tabella(["Problema"], [[prima["chiavi"][k]] for k in spariti])]))
            if nuovi:
                B.append(dettagli("🆕 Nuovi (%d)" % len(nuovi), [tabella(["Problema"], [[dopo["chiavi"][k]] for k in nuovi])]))
    return B


def _costruisci(R, voci, regole, salute, ricette):
    B = []
    ora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    conta = collections.Counter(v["livello"] for v in voci)
    B.append({"t": "copertina", "titolo": "Atlante della Videoteca",
              "sotto": "Kodi, LibreELEC, Arctic Zephyr e plugin.video.saghe: com'è fatto tutto, cosa non va, cosa vuole Alessandro",
              "data": ora,
              "numeri": [(l, conta.get(l, 0)) for l in LIVELLI]})

    # 1. SINTESI
    B.append(titolo("1. In una pagina", ancora="sintesi"))
    critici = [v for v in voci if v["livello"] in ("critico", "alto")]
    B.append(para("Problemi trovati: **%d** — %s." % (len(voci), ", ".join("%s %s %d" % (EMOJI[l], l, conta.get(l, 0)) for l in LIVELLI))))
    B.append(grafico(_ciambella([(l, conta.get(l, 0), COLORI[l]) for l in LIVELLI], "Problemi per livello"),
                     "```mermaid\npie title Problemi per livello\n%s\n```" % "\n".join('  "%s" : %d' % (l, conta.get(l, 0)) for l in LIVELLI if conta.get(l))))
    tipi = collections.Counter(v["tipo"] for v in voci)
    val = [(NOMI_TIPO.get(t, t), n) for t, n in tipi.most_common()]
    B.append(titolo("Per tipo di problema", 3))
    B.append(grafico(_barre(val, "Per tipo"), _barre_md(val)))
    B.append(titolo("Salute per area (100 = nessun problema)", 3))
    sal = sorted(salute["punteggi"].items(), key=lambda x: x[1])
    B.append(grafico(_barre([(NOMI_AREA.get(a, a), p) for a, p in sal], "Salute", colore=lambda n: "#455a64", massimo=100)
                     .replace('fill="#455a64"', 'fill="#2e7d32"'),
                     _barre_md([(NOMI_AREA.get(a, a), p) for a, p in sal])))
    B.append(tabella(["Area", "Salute", "🔴", "🟠", "🟡", "🔵", "⚪"],
                     [[NOMI_AREA.get(a, a), "%d/100" % p] + [str(salute["conteggi"].get(a, {}).get(l, 0)) for l in LIVELLI] for a, p in sal]))
    if critici:
        B.append(titolo("Da sistemare per primi", 3))
        B.append(tabella(["ID", "Livello", "Dove", "Problema"],
                         [[v["id"], "%s %s" % (EMOJI[v["livello"]], v["livello"]), NOMI_AREA.get(v["area"], v["area"]), v["titolo"]] for v in critici[:40]]))

    B.extend(_sezioni_nuove(R))

    # 2. APPARECCHI E PROGRAMMI
    B.append(titolo("2. Gli apparecchi e i programmi in gioco", ancora="apparecchi"))
    righe = []
    for app, k in R["apparecchi"].items():
        if k.get("errore"):
            righe.append([NOMI_AREA.get(app, app), "non raccolto", "-", "-", "-", "-", k["errore"][:80]])
            continue
        man = k["manifesto"]
        righe.append([NOMI_AREA.get(app, app), man.get("kodi") or "?", k.get("skin_attiva") or "?",
                      str(k["conteggio"]["totale"]), str(len(k["conteggio"]["spenti"])), str(len(k["dipendenze_rotte"])),
                      man.get("quando", "")])
    B.append(tabella(["Apparecchio", "Kodi", "Skin attiva", "Add-on", "Spenti", "Dipendenze rotte", "Raccolto"], righe))
    B.append(titolo("Come lavorano insieme", 3))
    B.append(para("Il percorso di ogni cosa che vedi in TV. Le frecce sono chiamate vere, lette nel codice e nei file della skin."))
    B.append(mermaid(SCHEMA_FLUSSO))
    B.append(elenco([
        "**La skin non chiama l'add-on: lo legge.** Ogni riga della home è un indirizzo `plugin://plugin.video.saghe/?azione=widget&che=…` scritto da skinshortcuts; Kodi esegue `main.py`, che restituisce le voci con immagini ed etichette.",
        "**Le righe leggono solo le cache** (`addon_data/plugin.video.saghe/*.json`). Le riempie `service.py` in un filo a parte: Netflix, Consigliati, Cinema, loghi dei titoli, copertine, sentinella.",
        "**Il tasto OK** apre la voce nella finestra indicata dal *target* della riga. Le azioni che aprono finestre (aggiungere una serie, avvisi) chiudono subito la cartella e passano ad `avvio.py` con RunScript.",
        "**Gli episodi** li trova e riproduce **s4me**, attraverso il canale 'Le Saghe' che vive dentro s4me.",
    ]))
    for app, k in R["apparecchi"].items():
        if k.get("errore"):
            continue
        righe = []
        for aid, a in sorted(k["addons"].items(), key=lambda x: (x[1]["dove"], x[0])):
            if a["dove"] == "sistema" and aid not in RUOLI and not aid.startswith(("skin.", "script.module.pil")):
                continue
            stato = "acceso" if a.get("acceso") else ("SPENTO" if a.get("acceso") is False else "non nel DB")
            righe.append([aid, a["versione"], ", ".join(sorted(set(a["punti"]))) or "-", stato, RUOLI.get(aid, a.get("nome", ""))])
        B.append(dettagli("%s — %d add-on (clic per aprire)" % (NOMI_AREA.get(app, app), len(righe)),
                          [tabella(["Id", "Versione", "Ruolo tecnico", "Stato", "A cosa serve"], righe)]))

    # 3. PROBLEMI
    B.append(titolo("3. Tutti i problemi, dal più grave", ancora="problemi"))
    B.append(para("Ogni problema ha un identificativo (SAG-nnn) da citare quando si lavora. *Dove* indica file e riga."))
    for l in LIVELLI:
        sotto = [v for v in voci if v["livello"] == l]
        if not sotto:
            continue
        B.append(titolo("%s %s (%d)" % (EMOJI[l], l.capitalize(), len(sotto)), 3))
        for v in sotto:
            corpo = []
            if v["dettaglio"]:
                corpo.append(codice(v["dettaglio"]) if "\n" in v["dettaglio"] and len(v["dettaglio"]) > 160 else para(v["dettaglio"]))
            meta = "**Tipo:** %s · **Area:** %s" % (NOMI_TIPO.get(v["tipo"], v["tipo"]), NOMI_AREA.get(v["area"], v["area"]))
            if v["regola"]:
                meta += " · **Regola di casa:** %s" % v["regola"]
            corpo.append(para(meta))
            if v["dove"]:
                corpo.append(para("**Dove:** " + ", ".join("`%s`" % d for d in v["dove"])))
            if v["rimedio"]:
                corpo.append(para("**Rimedio:** " + v["rimedio"]))
            B.append(dettagli("%s %s — %s" % (v["id"], EMOJI[l], v["titolo"]), corpo))

    # 4. REGOLE DI CASA
    B.append(titolo("4. Le regole di casa", ancora="regole"))
    B.append(para("Lezioni imparate a caro prezzo, ognuna controllata automaticamente quando i file lo permettono."))
    segno = {"rispettata": "✅ rispettata", "violata": "❌ violata", "da verificare a mano": "✋ a mano"}
    B.append(tabella(["Regola", "Imparata", "Stato", "Problemi"],
                     [[r["regola"], r["imparata"], segno[r["stato"]], ", ".join(r["problemi"]) or "-"] for r in regole]))

    # 5. SKIN
    B.append(titolo("5. Cosa pretende la skin", ancora="skin"))
    for app, sk in R["skin"].items():
        if not sk or sk.get("errore"):
            continue
        blocchi = [para("**%s %s** — %d file XML, %d finestre." % (sk["nome"], sk["versione"], sk["file_xml"], len(sk["finestre"])))]
        art = sorted(sk["art"].items(), key=lambda x: -x[1]["volte"])[:25]
        blocchi.append(grafico(_barre([(k, v["volte"]) for k, v in art], "Immagini lette", "#6a1b9a"), _barre_md([(k, v["volte"]) for k, v in art])))
        et = sorted(sk["etichette_voce"].items(), key=lambda x: -x[1]["volte"])[:40]
        blocchi.append(tabella(["Dato della voce letto", "Volte", "Esempi"], [[k, str(v["volte"]), ", ".join(v["dove"][:2])] for k, v in et]))
        blocchi.append(tabella(["Proprietà della voce", "Volte"], [[k, str(v["volte"])] for k, v in sorted(sk["proprieta_voce"].items(), key=lambda x: -x[1]["volte"])[:40]]))
        blocchi.append(tabella(["Proprietà di finestra", "Volte"], [[k, str(v["volte"])] for k, v in sorted(sk["proprieta_finestra"].items(), key=lambda x: -x[1]["volte"])[:40]]))
        blocchi.append(tabella(["Comando di Kodi nei pulsanti", "Volte"], [[k, str(v["volte"])] for k, v in list(sk["comandi"].items())[:30]]))
        blocchi.append(para("Include mancanti: %s · Variabili mancanti: %s · Caratteri definiti: %d" %
                            (", ".join(sk["include_mancanti"][:20]) or "nessuno", ", ".join(sk["variabili_mancanti"][:20]) or "nessuna", len(sk["font_definiti"]))))
        B.append(dettagli("%s: %s" % (NOMI_AREA.get(app, app), sk["nome"]), blocchi))

    # 6. ADDON
    a = R["addon"]
    B.append(titolo("6. Il nostro add-on visto dal codice", ancora="addon"))
    mod = sorted(a["moduli"].items(), key=lambda x: -x[1]["righe"])
    B.append(grafico(_barre([(k, v["righe"]) for k, v in mod[:20]], "Righe per modulo", "#00695c"), _barre_md([(k, v["righe"]) for k, v in mod[:20]])))
    B.append(tabella(["Azione del router", "Gestita in", "Collegata da"],
                     [[k, v, ", ".join(a["azioni_collegate"].get(k, [])[:3]) or "— mai collegata"] for k, v in sorted(a["azioni_gestite"].items())]))
    B.append(tabella(["Riga della home (che=)", "Gestita da widget()"], [[w, "sì"] for w in a["widget_gestiti"]]))
    if a.get("menu"):
        B.append(tabella(["Voce del menu", "Posto", "che=", "Titolo della riga"], [[r["voce"], r["posto"], r["che"], r["nome"]] for r in a["menu"]["righe"]]))
    B.append(tabella(["Immagine data (setArt)", "Dove"], [[k, ", ".join(v[:4])] for k, v in a["art_date"].items()]))
    B.append(tabella(["Dato InfoTag", "Dove"], [[k, ", ".join(v[:3])] for k, v in a["infotag"].items()]))
    B.append(tabella(["Impostazione", "Tipo", "Default", "Letta in"],
                     [[k, v["tipo"], "sì" if v["default"] else "NO", ", ".join(a["impostazioni"]["usate"].get(k, [])[:2]) or "mai"] for k, v in a["impostazioni"]["dichiarate"].items()]))
    fc = R["codice"]["funzioni_complesse"][:15]
    B.append(tabella(["Funzione più complessa", "File:riga", "Rami", "Righe"], [[f["funzione"], "%s:%d" % (f["file"], f["riga"]), str(f["rami"]), str(f["righe"])] for f in fc]))

    # 7. INCROCI
    B.append(titolo("7. Skin contro add-on, apparecchio per apparecchio", ancora="incroci"))
    for app, x in R["incroci"].items():
        if x.get("errore"):
            continue
        B.append(dettagli("%s — %s" % (NOMI_AREA.get(app, app), x["skin"]), [
            para("**Immagini che la skin legge e non diamo:** %s" % (", ".join(x["art_che_non_diamo"]) or "nessuna")),
            para("**Immagini che diamo e la skin non legge:** %s" % (", ".join(x["art_che_diamo_e_la_skin_non_legge"]) or "nessuna")),
            tabella(["Dato che la skin mostra", "Metodo che lo riempie", "Volte"], [[z["etichetta"], z["serve"], str(z["volte"])] for z in x["etichette_che_non_riempiamo"]]),
            para("**File della Videoteca diversi dal sorgente:** %s" % (", ".join(x["saghe_diversi_dal_sorgente"]) or "nessuno")),
            para("**Mancanti sull'apparecchio:** %s" % (", ".join(x["saghe_mancanti_sull_apparecchio"][:30]) or "nessuno")),
            para("**Caratteri delle nostre finestre mancanti:** %s" % (json.dumps(x["font_nostre_finestre_mancanti"], ensure_ascii=False) if x["font_nostre_finestre_mancanti"] else "nessuno")),
        ]))

    # 8. REGISTRI
    B.append(titolo("8. Cosa dicono i registri di Kodi", ancora="registri"))
    for app, k in R["apparecchi"].items():
        reg = (k or {}).get("registro") or {}
        if not reg.get("righe"):
            B.append(para("%s: nessun registro." % NOMI_AREA.get(app, app)))
            continue
        blocchi = [para("%d righe lette." % reg["righe"])]
        if reg["errori"]:
            blocchi.append(grafico(_barre([(m[:34], n) for m, n in reg["errori"][:12]], "Errori", "#c62828", larghezza=760), _barre_md([(m, n) for m, n in reg["errori"][:12]])))
            blocchi.append(tabella(["Volte", "Errore"], [[str(n), m] for m, n in reg["errori"][:40]]))
        if reg.get("errori_python"):
            blocchi.append(tabella(["Add-on", "Errore", "Dove", "Volte", "Adesso?", "Ultima"],
                                   [[t["addon"], "%s: %s" % (t["tipo"], t["contenuto"][:140]), t["dove"] or "-", str(t["volte"]),
                                     "sì (%d)" % t.get("volte_adesso", 0) if t.get("volte_adesso") else "no, storico", t["ultima"]]
                                    for t in reg["errori_python"]]))
        for t in reg.get("errori_python", [])[:20]:
            blocchi.append(dettagli("%s in %s (x%d): %s" % (t["tipo"], t["addon"], t["volte"], t["contenuto"][:90]), [codice(t["esempio"])]))
        B.append(dettagli("%s — %d errori distinti, %d errori Python" % (NOMI_AREA.get(app, app), len(reg["errori"]), len(reg.get("errori_python", []))), blocchi))

    # 9. RICHIESTE
    ch = R["chat"]
    msg = [m for m in ch["messaggi"] if m["videoteca"]]
    B.append(titolo("9. Cosa vuole Alessandro", ancora="richieste"))
    B.append(para("Estratto da **%d chat** e **%d memorie**: %d messaggi sulla Videoteca (tutti in REQUISITI.html, per argomento e sessione per sessione)."
                  % (len(ch["sessioni"]), len(ch["memorie"]), len(msg))))
    per_arg = collections.Counter(a for m in msg for a in m["argomenti"])
    B.append(grafico(_barre(per_arg.most_common(), "Messaggi per argomento", "#1565c0"), _barre_md(per_arg.most_common())))
    per_tipo = collections.Counter(m["tipo"] for m in msg)
    B.append(grafico(_barre(per_tipo.most_common(), "Messaggi per tipo", "#4527a0"), _barre_md(per_tipo.most_common())))
    per_giorno = collections.Counter(m["quando"][:10] for m in msg if m["quando"])
    B.append(grafico(_barre(sorted(per_giorno.items()), "Messaggi per giorno", "#00838f"), _barre_md(sorted(per_giorno.items()))))
    for arg, _n in per_arg.most_common():
        ultimi = [m for m in msg if arg in m["argomenti"]][-8:]
        B.append(dettagli("%s — ultime parole" % arg, [tabella(["Quando", "Tipo", "Messaggio"],
                          [[m["quando"][:16].replace("T", " "), m["tipo"], m["testo"][:400]] for m in reversed(ultimi)])]))
    aperti = []
    for mem in ch["memorie"]:
        for r in mem["testo"].splitlines():
            if re.search(r"(?i)\b(resta|da fare|da riprendere|aperto|todo|non (ancora )?fatt[oa]|manca)\b", r) and len(r.strip()) > 25:
                aperti.append([mem["nome"], r.strip()[:300]])
    B.append(titolo("Lavori aperti secondo le memorie", 3))
    B.append(dettagli("%d righe (clic per aprire)" % len(aperti), [tabella(["Memoria", "Riga"], aperti[:250])]))

    # 10. RICETTARIO
    B.append(titolo("10. Ricettario: i comandi giusti", ancora="ricettario"))
    for r in ricette:
        B.append(titolo(r["titolo"], 3))
        B.append(para(r["testo"]))
        for descr, cmd, lingua in r["comandi"]:
            B.append(para("**%s**" % descr))
            B.append(codice(cmd, lingua))
        if r["trappole"]:
            B.append(elenco(["⚠️ " + t for t in r["trappole"]]))
    return B


# ---------------------------------------------------------------- scrittori

def _md_inline(t):
    return t


def _html_inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def _md(B):
    out = []
    for b in B:
        t = b["t"]
        if t == "copertina":
            out.append("# %s\n\n_%s_\n\n**Generato:** %s\n\n%s\n" % (b["titolo"], b["sotto"], b["data"],
                       " · ".join("%s %s **%d**" % (EMOJI[l], l, n) for l, n in b["numeri"])))
            out.append("**Indice:** [Sintesi](#sintesi) · [Apparecchi](#apparecchi) · [Problemi](#problemi) · [Regole](#regole) · "
                       "[Skin](#skin) · [Add-on](#addon) · [Incroci](#incroci) · [Registri](#registri) · [Richieste](#richieste) · [Ricettario](#ricettario)\n")
        elif t == "titolo":
            out.append("\n%s %s <a id=\"%s\"></a>\n" % ("#" * b["livello"], b["testo"], b["ancora"]))
        elif t == "para":
            out.append(b["testo"] + "\n")
        elif t == "elenco":
            out.append("\n".join("- " + v for v in b["voci"]) + "\n")
        elif t == "tabella":
            if not b["righe"]:
                out.append("_(nessuna riga)_\n")
                continue
            out.append("| " + " | ".join(b["int"]) + " |")
            out.append("|" + "---|" * len(b["int"]))
            for r in b["righe"]:
                out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
            out.append("")
        elif t == "codice":
            out.append("```%s\n%s\n```\n" % (b.get("lingua", ""), b["testo"]))
        elif t == "grafico":
            out.append(b["md"] + "\n")
        elif t == "mermaid":
            out.append("```mermaid\n%s\n```\n" % b["testo"])
        elif t == "dettagli":
            out.append("<details><summary>%s</summary>\n" % html.escape(b["sommario"]))
            out.append(_md(b["blocchi"]))
            out.append("</details>\n")
    return "\n".join(out)


CSS = """
:root{--testo:#1d2733;--tenue:#5b6b7b;--bordo:#dfe5ec;--fondo:#f6f8fb;--accento:#b71c1c}
*{box-sizing:border-box}body{font-family:"Segoe UI",Inter,Roboto,Arial,sans-serif;color:var(--testo);background:#e9edf2;margin:0;line-height:1.55}
.foglio{max-width:1040px;margin:24px auto;background:#fff;padding:48px 64px;box-shadow:0 4px 30px rgba(0,0,0,.08);border-radius:6px}
.copertina{border-bottom:4px solid var(--accento);padding-bottom:28px;margin-bottom:28px}
.copertina h1{font-size:40px;margin:0 0 6px;letter-spacing:-.5px}.copertina .sotto{color:var(--tenue);font-size:17px;margin:0 0 18px}
.numeri{display:flex;gap:12px;flex-wrap:wrap}.num{flex:1;min-width:120px;border-radius:8px;padding:12px 16px;color:#fff}
.num b{display:block;font-size:30px}.indice{columns:2;font-size:14px;margin-top:18px}.indice a{color:var(--testo)}
h2{font-size:26px;margin:44px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--bordo);page-break-after:avoid}
h3{font-size:19px;margin:28px 0 8px;page-break-after:avoid}p{margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 18px;page-break-inside:auto}
th{background:#263238;color:#fff;text-align:left;padding:7px 9px;position:sticky;top:0}td{padding:6px 9px;border-bottom:1px solid var(--bordo);vertical-align:top;word-break:break-word}
tr:nth-child(even) td{background:var(--fondo)}code{background:#eef2f6;padding:1px 5px;border-radius:4px;font-size:12.5px}
pre{background:#0f1720;color:#dbe7f3;padding:14px 16px;border-radius:6px;overflow:auto;font-size:12.5px;white-space:pre-wrap}
pre code{background:none;color:inherit;padding:0}details{border:1px solid var(--bordo);border-radius:6px;margin:8px 0;padding:0 14px;background:#fff}
details[open]{padding-bottom:10px}summary{cursor:pointer;padding:9px 0;font-weight:600}
.graf{width:100%;max-width:760px;margin:8px 0 14px;font-size:12px}.graf .grande{font-size:34px;font-weight:700}.graf .piccolo{fill:#607d8b}
.graf .etic{fill:#37474f}.graf .val{fill:#263238;font-weight:600}ul{padding-left:22px}li{margin:4px 0}
.mermaid{background:var(--fondo);border-radius:6px;padding:12px;margin:10px 0}
@media print{body{background:#fff}.foglio{box-shadow:none;margin:0;padding:18mm 16mm;max-width:none}details{border:none;padding:0}
details>summary{list-style:none}details:not([open])>*:not(summary){display:block}th{position:static}h2{page-break-before:always}}
"""


def _html_blocchi(B):
    out = []
    for b in B:
        t = b["t"]
        if t == "copertina":
            nums = "".join('<div class="num" style="background:%s"><b>%d</b>%s</div>' % (COLORI[l], n, l) for l, n in b["numeri"])
            voci = [("sintesi", "1. In una pagina"), ("mappa", "A. Chi parla con chi"), ("s4me", "B. s4me visto da dentro"),
                    ("logo", "C. Il logo NOVIX"), ("correzioni", "D. Correzioni: prima e dopo"),
                    ("apparecchi", "2. Apparecchi e programmi"), ("problemi", "3. Tutti i problemi"),
                    ("regole", "4. Regole di casa"), ("skin", "5. Cosa pretende la skin"), ("addon", "6. Il nostro add-on"),
                    ("incroci", "7. Skin contro add-on"), ("registri", "8. Registri"), ("richieste", "9. Cosa vuole Alessandro"),
                    ("ricettario", "10. Ricettario")]
            out.append('<div class="copertina"><h1>%s</h1><p class="sotto">%s</p><p>Generato il %s</p><div class="numeri">%s</div>'
                       '<div class="indice">%s</div></div>' % (html.escape(b["titolo"]), html.escape(b["sotto"]), b["data"], nums,
                                                               "".join('<div><a href="#%s">%s</a></div>' % v for v in voci)))
        elif t == "titolo":
            out.append('<h%d id="%s">%s</h%d>' % (b["livello"], b["ancora"], _html_inline(b["testo"]), b["livello"]))
        elif t == "para":
            out.append("<p>%s</p>" % _html_inline(b["testo"]))
        elif t == "elenco":
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _html_inline(v) for v in b["voci"]))
        elif t == "tabella":
            if not b["righe"]:
                out.append("<p><em>(nessuna riga)</em></p>")
                continue
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
                "".join("<th>%s</th>" % html.escape(h) for h in b["int"]),
                "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % _html_inline(str(c)) for c in r) for r in b["righe"])))
        elif t == "codice":
            out.append("<pre><code>%s</code></pre>" % html.escape(b["testo"]))
        elif t == "grafico":
            out.append(b["svg"])
        elif t == "mermaid":
            out.append('<pre class="mermaid">%s</pre>' % html.escape(b["testo"]))
        elif t == "html":
            out.append(b["html"])
        elif t == "dettagli":
            out.append("<details><summary>%s</summary>%s</details>" % (_html_inline(b["sommario"]), _html_blocchi(b["blocchi"])))
    return "\n".join(out)


def _html(B):
    return ('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>Atlante della Videoteca</title><style>%s</style></head><body><div class=\"foglio\">%s</div>"
            '<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>'
            "<script>try{mermaid.initialize({startOnLoad:true,theme:'neutral'})}catch(e){}</script></body></html>" % (CSS, _html_blocchi(B)))


def _requisiti_md(ch):
    out = ["# Requisiti della Videoteca — tutte le parole di Alessandro\n",
           "Generato il %s da %d chat e %d memorie. In ordine di tempo; la colonna *Fonte* dice se il messaggio era "
           "scritto mentre Claude lavorava.\n" % (datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), len(ch["sessioni"]), len(ch["memorie"]))]
    per_arg = collections.defaultdict(list)
    for m in ch["messaggi"]:
        if m["videoteca"]:
            for a in m["argomenti"] or ["(senza argomento)"]:
                per_arg[a].append(m)
    out.append("## Indice per argomento\n")
    for a, lista in sorted(per_arg.items(), key=lambda x: -len(x[1])):
        out.append("- [%s](#%s) — %d messaggi" % (a, re.sub(r"\W+", "-", a.lower()), len(lista)))
    out.append("\n## In ordine di tempo\n")
    sessioni = ch["sessioni"]
    corrente = None
    for m in ch["messaggi"]:
        if not m["videoteca"]:
            continue
        if m["sessione"] != corrente:
            corrente = m["sessione"]
            s = sessioni.get(corrente, {})
            out.append("\n### Sessione %s — %s\n" % ((s.get("inizio") or "")[:16].replace("T", " "), s.get("titolo") or corrente[:8]))
        out.append("- **%s** · _%s_ · %s%s\n\n  > %s\n" % (m["quando"][:16].replace("T", " "), m["tipo"], ", ".join(m["argomenti"]),
                   " · ✍️ scritto mentre lavorava" if m["fonte"] != "chat" else "",
                   m["testo"].replace("\n", "\n  > ")))
    for a, lista in sorted(per_arg.items(), key=lambda x: -len(x[1])):
        out.append('\n## %s <a id="%s"></a>\n' % (a, re.sub(r"\W+", "-", a.lower())))
        for m in lista:
            out.append("- %s · _%s_ — %s" % (m["quando"][:10], m["tipo"], m["testo"][:500].replace("\n", " ")))
    out.append("\n## Memorie\n")
    for mem in ch["memorie"]:
        if mem["videoteca"]:
            out.append("- **%s** (%s) — %s" % (mem["nome"], mem["cartella"], mem["descrizione"]))
    return "\n".join(out)


def _requisiti_blocchi(ch):
    """Tutte le parole dell'utente sulla Videoteca, da leggere nel browser."""
    msg = [m for m in ch["messaggi"] if m["videoteca"]]
    B = [titolo("Le richieste di Alessandro", 1, "inizio"),
         para("Tutti i messaggi sulla Videoteca da **%d chat** e **%d memorie**: %d messaggi. "
              "✍️ = scritto mentre Claude lavorava." % (len(ch["sessioni"]), len(ch["memorie"]), len(msg)))]
    per_arg = collections.Counter(a for m in msg for a in m["argomenti"])
    B.append(grafico(_barre(per_arg.most_common(), "Messaggi per argomento", "#1565c0"), ""))
    per_tipo = collections.Counter(m["tipo"] for m in msg)
    B.append(grafico(_barre(per_tipo.most_common(), "Messaggi per tipo", "#4527a0"), ""))
    B.append(titolo("Per argomento (dal piu' recente)", 2, "argomenti"))
    for arg, n in per_arg.most_common():
        lista = [m for m in msg if arg in m["argomenti"]]
        B.append(dettagli("%s — %d messaggi" % (arg, n), [tabella(
            ["Quando", "Tipo", "Messaggio"],
            [[m["quando"][:16].replace("T", " "), m["tipo"] + (" ✍️" if m["fonte"] != "chat" else ""), m["testo"]]
             for m in reversed(lista)])]))
    B.append(titolo("Sessione per sessione", 2, "sessioni"))
    per_sessione = collections.OrderedDict()
    for m in msg:
        per_sessione.setdefault(m["sessione"], []).append(m)
    for sid, lista in per_sessione.items():
        s = ch["sessioni"].get(sid, {})
        B.append(dettagli("%s — %s (%d messaggi)" % ((s.get("inizio") or "")[:16].replace("T", " "),
                                                    s.get("titolo") or sid[:8], len(lista)), [tabella(
            ["Ora", "Tipo", "Argomenti", "Messaggio"],
            [[m["quando"][11:16], m["tipo"] + (" ✍️" if m["fonte"] != "chat" else ""), ", ".join(m["argomenti"]), m["testo"]]
             for m in lista])]))
    return B


def _fotografia(problemi, quando):
    """Il riassunto di un'analisi per il confronto con la successiva."""
    conta = collections.Counter(v["livello"] for v in problemi)
    chiavi = {}
    for v in problemi:
        chiavi["%s|%s" % (v["area"], re.sub(r"\d+", "#", v["titolo"]))] = "%s %s — %s" % (EMOJI.get(v["livello"], ""), NOMI_AREA.get(v["area"], v["area"]), v["titolo"])
    return {"quando": str(quando)[:16], "conta": dict(conta), "chiavi": chiavi}


def scrivi(R, voci, regole, salute, ricette, cartella):
    os.makedirs(cartella, exist_ok=True)
    # D. CORREZIONI: la storia delle analisi. La prima volta si parte dall'analisi
    # precedente rimasta in atlante.json (11/09/2026).
    p_storia = os.path.join(cartella, "storia.json")
    try:
        with io.open(p_storia, encoding="utf-8") as f:
            storia = json.load(f)
    except (OSError, ValueError):
        storia = []
    if not storia:
        try:
            with io.open(os.path.join(cartella, "atlante.json"), encoding="utf-8") as f:
                vecchio = json.load(f)
            storia.append(_fotografia(vecchio.get("problemi") or [], vecchio.get("generato", "prima")))
        except (OSError, ValueError):
            pass
    storia.append(_fotografia(voci, datetime.datetime.now().isoformat()))
    storia = storia[-40:]
    with io.open(p_storia, "w", encoding="utf-8") as f:
        json.dump(storia, f, ensure_ascii=False)
    R["storia"] = storia
    B = _costruisci(R, voci, regole, salute, ricette)
    # SOLO HTML (11/09/2026, l'utente: "non voglio vedere il file di testo, e' meglio
    # l'html da vedere e capire"). I vecchi .md si tolgono per non confondere.
    for vecchio in ("REPORT.md", "REQUISITI.md"):
        try:
            os.remove(os.path.join(cartella, vecchio))
        except OSError:
            pass
    with io.open(os.path.join(cartella, "REPORT.html"), "w", encoding="utf-8") as f:
        f.write(_html(B))
    with io.open(os.path.join(cartella, "REQUISITI.html"), "w", encoding="utf-8") as f:
        f.write(_html(_requisiti_blocchi(R["chat"])).replace(
            "<title>Atlante della Videoteca</title>", "<title>Le richieste di Alessandro</title>"))
    leggero = dict(R)
    leggero["chat"] = {"messaggi": R["chat"]["messaggi"], "sessioni": R["chat"]["sessioni"],
                       "memorie": [{k: v for k, v in m.items() if k != "testo"} for m in R["chat"]["memorie"]]}
    with io.open(os.path.join(cartella, "atlante.json"), "w", encoding="utf-8") as f:
        json.dump({"generato": datetime.datetime.now().isoformat(), "problemi": voci, "regole": regole,
                   "salute": salute, "dati": leggero}, f, ensure_ascii=False, indent=1, default=str)
    return os.path.join(cartella, "REPORT.html")
