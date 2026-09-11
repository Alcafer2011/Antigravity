# -*- coding: utf-8 -*-
"""
Servizio di sottofondo: tiene la memoria della posizione.

Fa due lavori distinti.

1) Riproduzione dentro Kodi. Segue il lettore e salva il secondo esatto ogni
   pochi secondi. Se si supera la soglia, l'episodio diventa visto e la catena
   avanza da sola: alla riapertura "Continua" punta gia' al successivo.

2) Riproduzione in un'app Android. Kodi non vede nulla, quindi al rientro
   chiede una cosa sola: l'hai finito? La risposta fa avanzare la catena.
   E' l'unico modo onesto: fingere di sapere il minuto sarebbe una bugia.
"""

import os
import time

import xbmc
import xbmcgui

from resources.lib import audio, catalogo, progresso

import xbmcaddon
ADDON = xbmcaddon.Addon()

INTERVALLO = 5          # secondi fra un salvataggio e l'altro
MINIMO_PER_CHIEDERE = 60  # sotto un minuto fuori da Kodi non si chiede niente


class Lettore(xbmc.Player):
    """Sorveglia le riproduzioni per sistemare l'audio appena parte il video.

    Perche' qui e non nell'add-on: cosi' vale per QUALUNQUE cosa si guardi,
    anche i film aperti da s4me, non solo le tappe delle saghe.
    """

    def onAVStarted(self):
        # Un attimo di pazienza: le tracce audio compaiono un istante dopo
        # l'inizio, e chiederle subito darebbe una lista vuota.
        if xbmc.Monitor().waitForAbort(2):
            return
        try:
            if not ADDON.getSettingBool("audio_scelta_automatica"):
                return
        except Exception as _errore:
            xbmc.log("[Le Saghe] onAVStarted: errore ignorato: %s" % _errore, xbmc.LOGDEBUG)
        try:
            cambiata, perche = audio.scegli_traccia_migliore()
            if cambiata:
                xbmc.log("[Le Saghe] traccia audio cambiata: %s" % perche, xbmc.LOGINFO)
                if _avvisa_audio():
                    xbmcgui.Dialog().notification(
                        "Le Saghe", "Audio: %s" % perche,
                        xbmcgui.NOTIFICATION_INFO, 3000)
        except Exception as e:
            xbmc.log("[Le Saghe] scelta audio fallita: %s" % e, xbmc.LOGWARNING)


def _avvisa_audio():
    try:
        return ADDON.getSettingBool("audio_avvisa")
    except Exception:
        return False


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.lettore = xbmc.Player()
        # deve restare vivo quanto il servizio, altrimenti Python lo butta
        # via e gli avvisi di riproduzione non arrivano piu'
        self.sorvegliante = Lettore()


def _salva_se_in_riproduzione(monitor):
    sess = progresso.sessione()
    if not sess or not sess.get("dentro_kodi"):
        return

    if not monitor.lettore.isPlayingVideo():
        return

    try:
        secondi = int(monitor.lettore.getTime())
        durata = int(monitor.lettore.getTotalTime())
    except RuntimeError:
        return

    if durata <= 0:
        return

    progresso.salva_minuto(sess["percorso"], sess["idx"], secondi, durata)


def _sentinella(monitor, sess):
    """Controlla che stia andando in onda l'episodio richiesto.

    Serve perche' e' gia' capitato, con altri servizi, di scegliere un
    episodio e vederne partire un altro. Kodi lo puo' verificare solo per
    cio' che riproduce lui: il confronto e' fra il file richiesto e quello
    realmente aperto.
    """
    if sess.get("controllata"):
        return
    if not monitor.lettore.isPlayingVideo():
        return

    try:
        in_onda = monitor.lettore.getPlayingFile()
    except RuntimeError:
        return

    progresso.marca_controllata()

    atteso = sess.get("file_atteso", "")
    if not atteso:
        return

    if os.path.normcase(os.path.basename(atteso)) ==        os.path.normcase(os.path.basename(in_onda)):
        return  # tutto regolare

    progresso.registra_anomalia(sess.get("atteso", atteso), in_onda)
    xbmcgui.Dialog().notification(
        "Le Saghe - episodio sbagliato",
        "Hai chiesto %s ma è partito un altro file" % sess.get("atteso", ""),
        xbmcgui.NOTIFICATION_WARNING, 9000)
    xbmc.log("[Le Saghe] ANOMALIA atteso=%s ottenuto=%s"
             % (atteso, in_onda), xbmc.LOGWARNING)


def _impostazione(nome, difetto):
    """Un'impostazione che non esiste ancora non deve far cadere il servizio."""
    try:
        if isinstance(difetto, bool):
            return ADDON.getSettingBool(nome)
        return ADDON.getSettingInt(nome)
    except Exception:
        return difetto


def _attacca_il_prossimo(pid, idx):
    """Parte da solo con la tappa successiva, dando il tempo di fermarsi.

    Il conto alla rovescia non e' un vezzo: senza, chi ha finito di guardare
    si ritrova un altro episodio addosso mentre si alza dal divano. Con il
    conto alla rovescia il comportamento e' quello di Netflix - va avanti da
    solo, ma basta un tasto per dire di no.

    Se la tappa non ha una fonte, riproduci() lo spiega e si ferma li': non
    serve controllarlo qui, e sarebbe un doppione della stessa logica.
    """
    t = catalogo.tappa(pid, idx)
    if not t:
        return False

    attesa = int(_impostazione("prossimo_attesa", 10) or 10)
    dialogo = xbmcgui.DialogProgress()
    dialogo.create("Le Saghe",
                   "Fra poco: [B]%s[/B]" % catalogo.descrizione_segmento(pid, idx))
    monitor = xbmc.Monitor()
    for rimasti in range(attesa, 0, -1):
        if dialogo.iscanceled():
            dialogo.close()
            return False
        dialogo.update(int(100.0 * (attesa - rimasti) / attesa),
                       "Fra poco: [B]%s[/B]\n\nParte fra %d secondi - "
                       "premi Indietro per fermarti."
                       % (catalogo.descrizione_segmento(pid, idx), rimasti))
        if monitor.waitForAbort(1):
            dialogo.close()
            return False
    dialogo.close()

    xbmc.Player().play("plugin://plugin.video.saghe/?azione=riproduci"
                       "&percorso=%s&idx=%d" % (pid, idx))
    return True


def _chiudi_riproduzione_interna(sess):
    """Chiamata quando il video dentro Kodi si e' fermato."""
    pid = sess["percorso"]
    idx = int(sess["idx"])
    secondi, durata = progresso.ripresa(pid)

    finito = durata > 0 and secondi >= durata * progresso.SOGLIA_COMPLETATO
    if finito:
        progresso.segna_visto(pid, idx, avanza=True,
                              massimo=catalogo.lunghezza(pid))

    progresso.chiudi_sessione()

    if not finito:
        return

    prossima = progresso.posizione(pid)
    # Se avanza() non ha potuto muoversi siamo in fondo alla catena.
    if prossima == idx or prossima > catalogo.lunghezza(pid):
        xbmcgui.Dialog().notification(
            "Le Saghe", "Saga finita. Complimenti.",
            xbmcgui.NOTIFICATION_INFO, 6000)
        return

    if _impostazione("prossimo_automatico", True):
        if _attacca_il_prossimo(pid, prossima):
            return

    xbmcgui.Dialog().notification(
        "Le Saghe",
        "Prossimo: %s" % catalogo.descrizione_segmento(pid, prossima),
        xbmcgui.NOTIFICATION_INFO, 5000)


def _chiudi_riproduzione_esterna(sess):
    """Chiamata al rientro in Kodi dopo un'app Android."""
    pid = sess["percorso"]
    idx = int(sess["idx"])
    t = catalogo.tappa(pid, idx)
    if not t:
        progresso.chiudi_sessione()
        return

    serie = catalogo.SERIE[t["serie"]]
    scelta = xbmcgui.Dialog().yesnocustom(
        "Le Saghe",
        "Hai finito [B]%s - episodio %d[/B]?\n\n"
        "Kodi non può saperlo da solo: il video è passato dall'app, non da lui."
        % (serie["titolo"], t["ep"]),
        customlabel="Chiedimelo dopo",
        nolabel="No, devo finirlo",
        yeslabel="Sì, vai al prossimo")

    # 0 = no, 1 = si, 2 = personalizzato, -1 = annullato
    if scelta == 1:
        progresso.segna_visto(pid, idx, avanza=True,
                              massimo=catalogo.lunghezza(pid))
        prossima = progresso.posizione(pid)
        xbmcgui.Dialog().notification(
            "Le Saghe",
            "Prossimo: %s" % catalogo.descrizione_segmento(pid, prossima),
            xbmcgui.NOTIFICATION_INFO, 5000)
        progresso.chiudi_sessione()
    elif scelta == 0:
        progresso.chiudi_sessione()
    # "Chiedimelo dopo" e annullamento lasciano la sessione aperta.


def _avvio_custode():
    # Il custode: rimette i nostri canali dentro s4me se un aggiornamento
    # se li e' portati via. Non tocca nessun file di s4me, ne aggiunge dei
    # suoi. Se fallisce non deve impedire niente, quindi sta in un try.
    try:
        from resources.lib import custode
        fatto, perche = custode.assicura()
        if fatto:
            xbmc.log("[Le Saghe] custode: %s" % perche, xbmc.LOGINFO)
        # E riaccende i canali di s4me che arrivano spenti (VVVVID,
        # Eurostreaming e compagnia): un suo aggiornamento li rispegne, noi
        # li riaccendiamo qui, a ogni avvio.
        custode.assicura_canali()
    except Exception as e:
        xbmc.log("[Le Saghe] custode non riuscito: %s" % e, xbmc.LOGWARNING)


def _avvio_regolazioni_s4me():
    # Le regolazioni di s4me, in silenzio, a ogni avvio.
    #
    # PERCHE' QUI: il 06/09/2026 il salotto era regolato e la camera no, e la
    # differenza si vedeva - in camera compariva "scegli un'opzione" a ogni
    # episodio e la qualita' partiva alta su una linea da 4 Mbps. Applicarle
    # a mano su ogni apparecchio vuol dire dimenticarsene su uno.
    # In modo muto non apre NIENTE, quindi e' sicuro anche se l'avvio del
    # servizio capita mentre c'e' gia' qualcosa sullo schermo.
    try:
        import avvio
        avvio._regola_s4me(muto=True)
    except Exception as e:
        xbmc.log("[Le Saghe] regolazioni s4me non riuscite: %s" % e,
                 xbmc.LOGWARNING)


def _avvio_novita():
    # Le novita' di s4me per la Vetrina.
    #
    # SI FANNO QUI, NON NELLA VETRINA. Interrogare s4me gli fa aprire una
    # sua finestra di avanzamento; se succede mentre la Vetrina e' a
    # schermo si ritrovano due finestre sovrapposte, ed e' cosi' che Kodi
    # si chiude (successo il 06/09 con il ponte). Qui non c'e' niente a
    # schermo, quindi e' innocuo - e quando l'utente apre la Vetrina le
    # locandine sono gia' pronte, senza aspettare.
    try:
        from resources.lib import novita
        novita.aggiorna_se_serve()
    except Exception as e:
        xbmc.log("[Le Saghe] novita' non aggiornate: %s" % e, xbmc.LOGWARNING)


def _avvio_cinema():
    # IL CARTELLONE DEL CINEMA.
    #
    # Chiede a TMDB quali film sono nelle sale ITALIANE, una volta al
    # giorno, e scrive l'elenco su file. Qui si scarica solo CHI c'e' al
    # cinema: DOVE guardarlo lo cerca il nostro canale dentro s4me, e solo
    # quando apri un film - cercare quaranta titoli su otto siti a ogni
    # avvio vorrebbe dire minuti di rete per niente.
    # Se la rete e' giu' non tocca il file: meglio il cartellone di ieri
    # che una sezione vuota.
    try:
        from resources.lib import cinema
        quanti = cinema.aggiorna_se_serve()
        if quanti:
            xbmc.log("[Le Saghe] cartellone aggiornato: %d film in sala"
                     % quanti, xbmc.LOGINFO)
    except Exception as e:
        xbmc.log("[Le Saghe] cartellone non aggiornato: %s" % e,
                 xbmc.LOGWARNING)


def _avvio_copertine():
    # LE LOCANDINE DI DOCUMENTARI, CUCINA E YOUTUBE.
    #
    # Prima quelle righe mettevano l'icona della videoteca su ogni voce:
    # 129 quadratini identici, che e' come non avere locandine (segnalato
    # dall'utente il 07/09). Qui si cercano i poster veri su TMDB e le
    # immagini dei canali YouTube, una volta al mese, in sottofondo.
    # Chi non ha una corrispondenza sicura tiene l'icona: non si mette
    # una locandina a caso, che sembrerebbe giusta ed e' peggio.
    try:
        from resources.lib import copertine
        from resources.lib import scoperte as _sc
        quante = copertine.calcola_se_serve(_sc.scaffale)
        if quante:
            xbmc.log("[Le Saghe] copertine trovate: %d" % quante,
                     xbmc.LOGINFO)
    except Exception as e:
        xbmc.log("[Le Saghe] copertine non aggiornate: %s" % e,
                 xbmc.LOGWARNING)


def _avvio_sentinella():
    # LA SENTINELLA DEGLI EPISODI NUOVI.
    #
    # ATTENZIONE AL NOME: in questo file c'e' gia' una funzione `_sentinella`,
    # ed e' un'altra cosa (controlla che parta l'episodio giusto). Questa e'
    # `resources/lib/sentinella.py`: una volta alla settimana chiede a TMDb
    # se le serie ancora in corso sono cresciute, allunga le catene e
    # avvisa. Gira in un filo a parte: se la rete non risponde non blocca
    # l'avvio.
    try:
        from resources.lib import sentinella as guardia_episodi
        cambiati = catalogo.applica_aggiunte(guardia_episodi.leggi_aggiunte())
        if cambiati:
            xbmc.log("[Le Saghe] saghe allungate: %s"
                     % ", ".join("%s %d->%d" % c for c in cambiati),
                     xbmc.LOGINFO)
        if guardia_episodi.controlla_se_serve(catalogo):
            xbmc.log("[Le Saghe] sentinella: controllo episodi nuovi avviato",
                     xbmc.LOGINFO)
    except Exception as e:
        xbmc.log("[Le Saghe] sentinella non avviata: %s" % e, xbmc.LOGWARNING)


def _avvio_consigli():
    # I CONSIGLI: si rifanno ogni tre giorni, guardando cosa hai guardato.
    # Anche questi in un filo a parte, e anche questi qui e non a schermo:
    # interrogare TMDb trenta volte mentre l'utente aspetta e' inaccettabile.
    try:
        from resources.lib import consigli, progresso as _prog
        catalogo.applica_serie_nuove(consigli.serie_mie())
        if consigli.calcola_se_serve(catalogo, _prog):
            xbmc.log("[Le Saghe] consigli: ricalcolo avviato", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log("[Le Saghe] consigli non calcolati: %s" % e, xbmc.LOGWARNING)


def _avvio_netflix():
    # LA RIGA "SU NETFLIX ORA": la cache la riempie QUI, in un filo a parte.
    # La riga della home legge solo il file (netflix.riga()) e non aspetta
    # mai la rete: sono 29 righe che partono insieme all'apertura della
    # schermata iniziale, e una sola che va a TMDb le blocca tutte.
    def _scalda_netflix():
        try:
            from resources.lib import netflix as _nf
            esito = _nf.aggiorna_righe()
            xbmc.log("[Le Saghe] Su Netflix ora: " + ", ".join(
                "%s %d" % (k, v) for k, v in sorted(esito.items())),
                xbmc.LOGINFO)
        except Exception as e:
            xbmc.log("[Le Saghe] Su Netflix ora non aggiornata: %s" % e,
                     xbmc.LOGWARNING)
        # I LOGHI DEL TITOLO delle righe che arrivano da TMDb (Netflix,
        # Consigliati, Cinema, serie aggiunte da te). Dopo Netflix, cosi' la
        # sua cache e' gia' fresca; le righe poi li leggono dal file.
        try:
            from resources.lib import loghi
            chiesti = loghi.riempi()
            if chiesti:
                xbmc.log("[Le Saghe] loghi del titolo chiesti a TMDb: %d"
                         % chiesti, xbmc.LOGINFO)
        except Exception as e:
            xbmc.log("[Le Saghe] loghi non aggiornati: %s" % e, xbmc.LOGWARNING)

    try:
        import threading
        threading.Thread(target=_scalda_netflix, daemon=True).start()
    except Exception as e:
        xbmc.log("[Le Saghe] filo Netflix non avviato: %s" % e, xbmc.LOGWARNING)


# All'avvio, uno dopo l'altro. Ogni passo ha il suo try: se uno fallisce gli altri
# partono lo stesso. (Era una funzione sola da 188 righe: divisa l'11/09/2026.)
PASSI_ALL_AVVIO = (_avvio_custode, _avvio_regolazioni_s4me, _avvio_novita, _avvio_cinema,
                   _avvio_copertine, _avvio_sentinella, _avvio_consigli, _avvio_netflix)


def principale():
    for passo in PASSI_ALL_AVVIO:
        passo()

    monitor = Monitor()
    kodi_era_in_primo_piano = True
    contatore = 0

    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

        contatore += 1
        sess = progresso.sessione()

        if not sess:
            continue

        if sess.get("dentro_kodi"):
            if monitor.lettore.isPlayingVideo():
                if not sess.get("visto_play"):
                    progresso.marca_visto_play()
                _sentinella(monitor, sess)
                if contatore % INTERVALLO == 0:
                    _salva_se_in_riproduzione(monitor)
            else:
                eta = int(time.time()) - sess.get("avviata", 0)
                if sess.get("visto_play"):
                    # E' partito e ora non c'e' piu': e' finito o fermato.
                    if eta > 3:
                        _chiudi_riproduzione_interna(sess)
                elif eta > 90:
                    # Non e' MAI partito in 90 secondi: s4me non ce l'ha
                    # fatta. Si chiude la sessione senza avanzare.
                    progresso.chiudi_sessione()
        else:
            # Sessione su app esterna: si aspetta il rientro in Kodi.
            in_primo_piano = not xbmc.getCondVisibility("System.IdleTime(1)") \
                or xbmc.getCondVisibility("Window.IsActive(home)") \
                or xbmc.getCondVisibility("Window.IsMedia")
            trascorso = int(time.time()) - sess.get("avviata", 0)
            if trascorso > MINIMO_PER_CHIEDERE and in_primo_piano \
                    and not kodi_era_in_primo_piano:
                _chiudi_riproduzione_esterna(sess)
            kodi_era_in_primo_piano = in_primo_piano


if __name__ == "__main__":
    principale()
