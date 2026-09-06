# -*- coding: utf-8 -*-
"""Riscrive i menu di Le Saghe: meno voci, parole comprensibili."""
import io, re

P = "plugin.video.saghe/main.py"
s = io.open(P, encoding="utf-8").read()

s = s.replace(
    "from resources.lib import catalogo, fonti, progresso, schede",
    "from resources.lib import abbonamenti, catalogo, fonti, progresso, schede")

# ---------------------------------------------------------------- menu radice
inizio = s.index("def menu_principale():")
fine = s.index("# ------", inizio)
s = s[:inizio] + '''def menu_principale():
    xbmcplugin.setPluginCategory(MANIGLIA, "Le Saghe")

    for pid in catalogo.ORDINE_PERCORSI:
        p = catalogo.PERCORSI[pid]
        totale = catalogo.lunghezza(pid)
        idx = progresso.posizione(pid)
        fatto = progresso.percentuale(pid, totale)
        quanti_visti = len(progresso.visti(pid))

        if quanti_visti == 0:
            stato = "%d episodi — mai cominciata" % totale
        else:
            stato = "%d%% vista — %d episodi su %d" % (fatto, quanti_visti, totale)

        li = _voce("%s\\n[COLOR grey]%s[/COLOR]" % (p["titolo"], stato),
                   "%s\\n\\nSei arrivato a: %s" % (
                       p["sottotitolo"],
                       catalogo.descrizione_segmento(pid, idx)))
        prima = p["segmenti"][0][0]
        arte = {}
        if schede.poster(prima):
            arte["poster"] = arte["thumb"] = arte["icon"] = schede.poster(prima)
        if schede.sfondo(prima):
            arte["fanart"] = schede.sfondo(prima)
        if arte:
            li.setArt(arte)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="percorso", percorso=pid), li, True)

    cop, tot, perc = abbonamenti.copertura()
    li = _voce("I miei abbonamenti\\n[COLOR grey]con quello che hai vedi il "
               "%d%% di tutto[/COLOR]" % perc,
               "Cosa ti sblocca ogni abbonamento, in episodi veri.",
               icona="DefaultAddonService.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="abbonamenti"), li, True)

    an = progresso.anomalie()
    if an:
        li = _voce("[COLOR red]Attenzione: %d episodi sbagliati[/COLOR]" % len(an),
                   "È partito un episodio diverso da quello scelto.",
                   icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="anomalie"), li, False)

    xbmcplugin.endOfDirectory(MANIGLIA)


def pannello_abbonamenti():
    cop, tot, perc = abbonamenti.copertura()
    xbmcplugin.setPluginCategory(MANIGLIA, "I miei abbonamenti")

    li = _voce("[B]Oggi puoi vedere %d episodi su %d  (%d%%)[/B]"
               % (cop, tot, perc),
               "Conteggio su tutte le saghe, esclusa la via veloce di Dragon "
               "Ball che e' un doppione.", icona="DefaultAddonService.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="abbonamenti"), li, False)

    for v in abbonamenti.riepilogo():
        if v["posseduta"]:
            segno = "[COLOR green]HAI[/COLOR]"
            nota = "ti da %d episodi" % v["episodi"]
        elif v["esclusivi"]:
            segno = "[COLOR orange]TI MANCA[/COLOR]"
            nota = "sbloccherebbe %d episodi che oggi non puoi vedere" % v["esclusivi"]
        else:
            segno = "[COLOR grey]non serve[/COLOR]"
            nota = "i suoi %d episodi li hai gia altrove" % v["episodi"]

        li = _voce("%s  %s\\n[COLOR grey]%s — %s[/COLOR]"
                   % (segno, v["nome"], nota, v["prezzo"]),
                   "%s\\n\\n%s\\nPrezzo: %s" % (v["nome"], nota, v["prezzo"]))
        lg = fonti.logo(v["id"])
        if lg:
            li.setArt({"icon": lg, "thumb": lg})
        xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="abbonamenti"), li, False)

    li = _voce("Cambia i miei abbonamenti…",
               "Apre le impostazioni per spuntare cosa possiedi.",
               icona="DefaultAddonProgram.png")
    xbmcplugin.addDirectoryItem(MANIGLIA, url(azione="impostazioni"), li, False)
    xbmcplugin.endOfDirectory(MANIGLIA)


''' + s[fine:]

# ------------------------------------------------------------- menu di saga
inizio = s.index("def menu_percorso(pid):")
fine = s.index("def _mmss(", inizio)
s = s[:inizio] + '''def menu_percorso(pid):
    p = catalogo.PERCORSI[pid]
    totale = catalogo.lunghezza(pid)
    idx = progresso.posizione(pid)
    secondi, durata = progresso.ripresa(pid)
    mai = len(progresso.visti(pid)) == 0

    xbmcplugin.setPluginCategory(MANIGLIA, p["titolo"])

    # 1. La voce che serve nel 90% dei casi.
    dove = catalogo.descrizione_segmento(pid, idx).split(" — ")[0]
    if mai:
        testo = "Comincia dal primo episodio"
    else:
        testo = "Riprendi da: %s" % dove
        if secondi > 60:
            testo += "  (al minuto %s)" % _mmss(secondi)
    li = _voce("[B]%s[/B]" % testo,
               "Parte subito l'episodio giusto, senza cercare nulla.",
               riproducibile=True, icona="DefaultInProgressShows.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="riproduci", percorso=pid, idx=idx), li, False)

    # 2. Tutti gli episodi.
    li = _voce("Tutti gli episodi in ordine\\n[COLOR grey]%d, dal primo "
               "all'ultimo[/COLOR]" % totale,
               "L'ordine corretto per capire la storia, anche quando salta da "
               "una serie all'altra.", icona="DefaultTVShows.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="sfoglia", percorso=pid, da=1), li, True)

    # 3. I film.
    fl = schede.film(pid)
    if fl:
        disp = sum(1 for m in fl
                   if any(fonti.possiede(f) for f in m.get("f", [])))
        li = _voce("I film\\n[COLOR grey]%d, di cui %d guardabili adesso[/COLOR]"
                   % (len(fl), disp),
                   "Lungometraggi e special. Stanno fuori dall'ordine: "
                   "raccontano storie a se'.", icona="DefaultMovies.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="film", percorso=pid), li, True)

    # 4. I tagli italiani.
    quanti = len(catalogo.tutti_i_tagli(pid))
    if quanti:
        li = _voce("Dove la TV italiana ti ha interrotto\\n[COLOR grey]%d punti"
                   "[/COLOR]" % quanti,
                   "Gli episodi esatti in cui hanno tagliato o smesso di "
                   "trasmettere.", icona="DefaultAddonNone.png")
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione="tagli", percorso=pid), li, True)

    # 5. Tutto il resto, raccolto.
    li = _voce("[COLOR grey]Altro…[/COLOR]",
               "Com'e' fatto questo ordine, riparti da un punto preciso, "
               "ricomincia da capo.", icona="DefaultAddonHelper.png")
    xbmcplugin.addDirectoryItem(
        MANIGLIA, url(azione="altro", percorso=pid), li, True)

    xbmcplugin.endOfDirectory(MANIGLIA)


def menu_altro(pid):
    xbmcplugin.setPluginCategory(MANIGLIA, "Altro")
    voci = [
        ("Com'e' fatto questo ordine", "spiega",
         "Perche' gli episodi sono in quest'ordine e non un altro.",
         "DefaultAddonHelper.png", False),
        ("Riparti da un episodio preciso…", "salta",
         "Scegli tu il punto da cui ricominciare.",
         "DefaultAddonsSearch.png", False),
        ("Ricomincia da capo", "azzera",
         "Riporta la saga al primo episodio e cancella cosa hai visto.",
         "DefaultAddonNone.png", False),
    ]
    for etichetta, azione, desc, icona, cartella in voci:
        li = _voce(etichetta, desc, icona=icona)
        xbmcplugin.addDirectoryItem(
            MANIGLIA, url(azione=azione, percorso=pid), li, cartella)
    xbmcplugin.endOfDirectory(MANIGLIA)


''' + s[fine:]

# ------------------------------------------------------------------- rotte
s = s.replace('    elif azione == "film":',
              '''    elif azione == "abbonamenti":
        pannello_abbonamenti()
    elif azione == "altro":
        menu_altro(pid)
    elif azione == "film":''')

io.open(P, "w", encoding="utf-8").write(s)
print("menu riscritti")
