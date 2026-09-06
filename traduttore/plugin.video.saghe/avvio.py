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


# Le leve di s4me che valgono la pena, con il valore giusto per questa casa.
#
# Sono impostazioni SUE: si scrivono con la sua stessa interfaccia, perche'
# modificargli il settings.xml a mano mentre Kodi gira non servirebbe a
# niente - lo riscrive lui uscendo.
LEVE_S4ME = [
    ("autoplay", "true",
     "Scelta automatica della fonte",
     "Senza, a ogni singolo episodio compare 'scegli un'opzione' e devi "
     "premere. Con, sceglie da solo e parte."),
    ("default_action", "1",
     "Qualita' video: Bassa",
     "Era su 'Chiedi'. Con 4 Mbps la qualita' alta non regge: scegliendo "
     "bassa in automatico il video parte e non si ferma. E' la stessa "
     "logica del tetto gia' messo su Netflix e Prime."),
    ("videolibrary_kodi", "true",
     "Videoteca di s4me dentro la libreria di Kodi",
     "Le saghe che aggiungi alla videoteca finiscono nella libreria Serie "
     "TV di Kodi: ripresa vera, prossimo episodio nativo, locandine "
     "ovunque. Da sola non fa niente finche' non aggiungi una saga."),
    ("next_ep", "1",
     "Prossimo episodio: automatico",
     "Funziona per le saghe messe nella videoteca."),
    ("trakt_sync", "true",
     "Sincronia con Trakt",
     "Tiene il segno di dove sei arrivato su TUTTI gli apparecchi, e anche "
     "fuori casa - cosa che il nostro quaderno non sa fare. Attenzione: "
     "accendere l'interruttore non basta, serve autorizzare l'account "
     "dalla TV (vedi sotto)."),
]


def _regola_s4me():
    """Mette in s4me i valori giusti per questa casa, e racconta cosa ha fatto."""
    import xbmcaddon
    try:
        s4 = xbmcaddon.Addon("plugin.video.s4me")
    except Exception:
        xbmcgui.Dialog().ok("Le Saghe", "s4me non e' installato.")
        return

    righe = []
    for chiave, valore, nome, perche in LEVE_S4ME:
        prima = s4.getSetting(chiave)
        if prima == valore:
            righe.append("[COLOR grey]gia' a posto[/COLOR]  %s" % nome)
            continue
        try:
            s4.setSetting(chiave, valore)
            righe.append("[B]cambiato[/B]  %s\n   %s" % (nome, perche))
        except Exception as e:
            righe.append("[COLOR red]non riuscito[/COLOR]  %s (%s)" % (nome, e))

    xbmcgui.Dialog().textviewer(
        "s4me regolato per questa casa",
        "\n\n".join(righe) +
        "\n\n\n[B]Cosa fare adesso[/B]\n"
        "Per avere il passaggio automatico all'episodio dopo, apri una saga "
        "dentro s4me (canale 'Le Saghe'), premi Menu sul titolo e scegli "
        "[B]Aggiungi alla videoteca[/B].\n\n"
        "Falla UNA saga per volta, quella che stai guardando: ogni saga "
        "crea un file per episodio, e con tutte insieme sarebbero migliaia "
        "di file da scansionare su un Raspberry.\n\n"
        "[B]Per Trakt serve un passaggio in piu'[/B]\n"
        "L'interruttore e' acceso, ma finche' non autorizzi l'account non "
        "sincronizza niente. Si fa da: Impostazioni di s4me > Preferenze > "
        "Trakt. Compare un codice da scrivere su [B]trakt.tv/activate[/B] "
        "dal telefono o dal computer. L'account e' gratuito.\n"
        "Finche' non lo fai, il segno resta quello che teniamo noi: non si "
        "perde niente.")


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
