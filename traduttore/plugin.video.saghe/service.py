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
        except Exception:
            pass
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


def principale():
    # Il custode: rimette i nostri canali dentro s4me se un aggiornamento
    # se li e' portati via. Non tocca nessun file di s4me, ne aggiunge dei
    # suoi. Se fallisce non deve impedire niente, quindi sta in un try.
    try:
        from resources.lib import custode
        fatto, perche = custode.assicura()
        if fatto:
            xbmc.log("[Le Saghe] custode: %s" % perche, xbmc.LOGINFO)
    except Exception as e:
        xbmc.log("[Le Saghe] custode non riuscito: %s" % e, xbmc.LOGWARNING)

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
                _sentinella(monitor, sess)
                if contatore % INTERVALLO == 0:
                    _salva_se_in_riproduzione(monitor)
            else:
                # Il video e' finito o e' stato fermato.
                if int(time.time()) - sess.get("avviata", 0) > 3:
                    _chiudi_riproduzione_interna(sess)
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
