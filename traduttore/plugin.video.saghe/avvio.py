# -*- coding: utf-8 -*-
"""
IL PUNTO DI INGRESSO FUORI DALLE CARTELLE.

PERCHE' ESISTE, ed e' la lezione piu' cara di tutta questa storia
    Quando Kodi chiede a un add-on il contenuto di una cartella, tiene
    aperta la SUA finestra di attesa. Se da li' dentro si apre un'altra
    finestra - una barra di avanzamento nostra, o peggio un altro add-on
    che apre la propria - Kodi si trova due finestre di attesa sovrapposte
    e **si spegne di proposito**:

        critical: Logic error due to two concurrent busydialogs,
                  this is a known issue. The application will exit.

    E' successo davvero il 06/09/2026, due volte in due minuti: l'utente
    apriva un episodio dal nostro add-on e LibreELEC ripartiva. Non era un
    guasto del nostro codice: era il POSTO da cui lo eseguivamo.

    Un programma lanciato con `RunScript` gira per conto suo, senza nessuna
    finestra di attesa davanti. Da qui si puo' aprire quello che si vuole.

REGOLA, da non dimenticare mai piu'
    Dentro una cartella (`main.py`) si costruiscono SOLO elenchi.
    Tutto cio' che apre finestre, chiama altri add-on o riproduce video
    passa DA QUI.

COME SI CHIAMA
    RunScript(plugin.video.saghe, vetrina)
    RunScript(plugin.video.saghe, apri, <percorso>, <tappa>)
"""

import sys

import xbmc
import xbmcgui


def _vetrina():
    from resources.lib import vetrina
    scelto = vetrina.apri("plugin://plugin.video.saghe/")
    if scelto:
        xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % scelto)


def _regola_s4me():
    """Accende in s4me le due leve che servono a guardare senza attriti.

    Sono impostazioni SUE, quindi si scrivono con la sua stessa interfaccia:
    scrivere a mano il suo settings.xml mentre Kodi gira non servirebbe a
    niente, perche' lo riscrive lui uscendo.

      autoplay  - senza, a ogni episodio chiede "scegli un'opzione" e ti
                  tocca premere. Con, sceglie da solo la fonte migliore.
      next_ep   - il passaggio automatico all'episodio dopo (era gia' su
                  "Automatico", si controlla e basta).
    """
    import xbmcaddon
    try:
        s4 = xbmcaddon.Addon("plugin.video.s4me")
    except Exception:
        xbmcgui.Dialog().ok("Le Saghe", "s4me non e' installato.")
        return

    prima_autoplay = s4.getSetting("autoplay")
    prima_next = s4.getSetting("next_ep")
    s4.setSetting("autoplay", "true")
    if prima_next in ("", "0"):
        s4.setSetting("next_ep", "1")     # 1 = Automatico

    xbmcgui.Dialog().ok(
        "Le Saghe - s4me regolato",
        "[B]Scelta automatica della fonte:[/B] accesa "
        "(prima era '%s')\n"
        "Non ti chiedera' piu' 'scegli un'opzione' a ogni episodio.\n\n"
        "[B]Prossimo episodio:[/B] automatico\n"
        "Funziona per le saghe messe nella videoteca di s4me: apri una "
        "saga, tasto destro (o Menu) sul titolo, [B]Aggiungi alla "
        "videoteca[/B]. Da quel momento gli episodi si concatenano da soli, "
        "seguendo il nostro ordine cronologico."
        % ("acceso" if prima_autoplay == "true" else "spento"))


def _apri(percorso, idx):
    """Apre una tappa provando le strade del piano, una dopo l'altra.

    E' lo stesso lavoro che prima stava dentro main.apri(), spostato qui:
    li' faceva crollare Kodi, qui e' al sicuro.
    """
    import time

    from resources.lib import catalogo, fonti, motore, progresso, ponte_s4me

    idx = int(idx)
    t = catalogo.tappa(percorso, idx)
    if not t:
        xbmcgui.Dialog().notification("Le Saghe", "Tappa inesistente",
                                      xbmcgui.NOTIFICATION_ERROR)
        return

    serie = catalogo.SERIE[t["serie"]]
    strade = motore.piano(t["serie"], t["ep"])
    if not strade:
        xbmcgui.Dialog().ok(
            "Le Saghe",
            "Per [B]%s - episodio %d[/B] non c'e' nessuna strada da provare.\n\n"
            "Non hai fonti per questa serie e il ponte verso s4me non "
            "risulta installato." % (serie["titolo"], t["ep"]))
        return

    saltate = []
    for n, strada in enumerate(strade):
        ultima = (n == len(strade) - 1)

        ok, perche = motore.previsione(strada)
        if not ok and not ultima:
            motore.annota(t["serie"], t["ep"], strada["id"], "saltata", perche)
            saltate.append("%s (%s)" % (strada["etichetta"], perche))
            continue

        partenza = time.time()
        riuscita = _prova(percorso, idx, t, serie, strada, saltate,
                          catalogo, fonti, progresso, ponte_s4me)
        motore.ricorda(t["serie"], strada["id"], riuscita, time.time() - partenza)
        motore.annota(t["serie"], t["ep"], strada["id"],
                      "riuscita" if riuscita else "fallita", "")
        if riuscita:
            return
        if not ultima:
            saltate.append("%s (non ha aperto niente)" % strada["etichetta"])

    # Nessuna strada ha aperto niente: si dice cosa e' stato provato, invece
    # di lasciare l'utente davanti a un menu che non reagisce.
    xbmcgui.Dialog().ok(
        "Le Saghe",
        "[B]%s - episodio %d[/B]\n\nHo provato tutte le strade e nessuna ha "
        "aperto niente:\n\n%s\n\nIn 'Altro > Perche' non e' partito?' trovi "
        "il dettaglio." % (serie["titolo"], t["ep"],
                           "\n".join("- " + s for s in saltate) or "-"))


def _prova(percorso, idx, t, serie, strada, saltate,
           catalogo, fonti, progresso, ponte_s4me):
    """Prova UNA strada. Vero se ha aperto qualcosa."""
    if strada["tipo"] == "app":
        progresso.vai_a(percorso, idx)
        pacchetto = catalogo.FONTI[strada["id"]]["pacchetto"]
        link = fonti.link_diretto(strada["id"], t["serie"])
        progresso.apri_sessione(percorso, idx, dentro_kodi=False,
                                atteso="%s ep %d" % (serie["titolo"], t["ep"]))
        xbmcgui.Dialog().notification(
            "Le Saghe",
            "%s - cerca l'episodio %d" % (serie["titolo"], t["ep"]),
            xbmcgui.NOTIFICATION_INFO, 7000)
        fonti.avvia_app(pacchetto, link)
        return True

    if strada["tipo"] == "ponte":
        titolo = ponte_s4me.titolo_per_ricerca(serie, t)
        if not titolo:
            return False
        if saltate:
            xbmcgui.Dialog().notification(
                "Le Saghe",
                ("Provato senza esito: %s. Cerco su s4me."
                 % "; ".join(saltate[:2]))[:110],
                xbmcgui.NOTIFICATION_INFO, 5000)
        # La tappa si segna PRIMA: se il video parte, il servizio deve gia'
        # sapere dove siamo per registrare il minuto.
        progresso.vai_a(percorso, idx)
        esito = ponte_s4me.apri_automatico(titolo, t["ep"])
        if esito == "niente":
            ponte_s4me.cerca(titolo)
        elif esito == "avvicinato":
            xbmcgui.Dialog().notification(
                "Le Saghe",
                "Non ho individuato l'episodio %d: eccoti al punto piu' vicino"
                % t["ep"], xbmcgui.NOTIFICATION_INFO, 5000)
        return True

    return False


def main():
    comando = sys.argv[1] if len(sys.argv) > 1 else "vetrina"
    try:
        if comando == "vetrina":
            _vetrina()
        elif comando == "apri":
            _apri(sys.argv[2], sys.argv[3])
        elif comando == "regola_s4me":
            _regola_s4me()
        else:
            xbmc.log("[Le Saghe] comando sconosciuto: %s" % comando,
                     xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log("[Le Saghe] avvio.py: %s" % e, xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Le Saghe", "Qualcosa e' andato storto",
                                      xbmcgui.NOTIFICATION_ERROR, 5000)


if __name__ == "__main__":
    main()
