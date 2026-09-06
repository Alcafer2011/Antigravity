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
    RunScript(plugin.video.saghe, regola_s4me)

NOTA STORICA, perche' il file resti comprensibile
    Qui dentro c'era anche l'apertura degli episodi, con tutto il motore
    delle fonti. Non c'e' piu': dal 06/09/2026 gli episodi li trova s4me,
    che ha 55 fonti e le aggiorna da solo. Quel codice e' stato tolto, non
    lasciato a marcire: sta nella storia del deposito se dovesse servire.
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


def main():
    comando = sys.argv[1] if len(sys.argv) > 1 else "vetrina"
    try:
        if comando == "vetrina":
            _vetrina()
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
