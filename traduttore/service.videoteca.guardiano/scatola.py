# -*- coding: utf-8 -*-
"""LA SCATOLA NERA: cosa succede sull'apparecchio mentre lo usi.

PERCHE' (chiesto dall'utente l'11/09/2026)
    "ci vuole uno script che raccolga le informazioni mentre li sto
    utilizzando nel caso ci siano errori nel funzionamento, perche' io non
    saprei descrivertele". Un guasto raccontato a voce ("non partiva", "si e'
    bloccato") non dice DOVE ne' PERCHE'. Qui si scrive, con l'ora:
      - ogni schermata e cartella aperta, e da quale voce ci si arrivava
      - i video: chiesto, partito davvero (o no), fermato, quanto e' durato
      - le finestre di messaggio e le notifiche, col loro testo
      - le attese lunghe (la rotellina) e gli errori del registro di Kodi
      - se Kodi si era chiuso da solo
    e nei momenti brutti si fotografa lo schermo. Sul PC,
    `traduttore/registratore.py box|pi|pc` scarica tutto e ne fa un rapporto.

QUANTO PESA
    Poche etichette lette una volta al secondo (ogni 3 s mentre va un video),
    una riga di testo solo quando qualcosa CAMBIA, al massimo 40 fotografie
    tenute. I giorni piu' vecchi di una settimana si cancellano da soli.
    Ogni pezzo sta in un try: la scatola nera non deve MAI essere lei il guasto.
"""

import io
import json
import os
import re
import time

import xbmc
import xbmcgui
import xbmcvfs

ID = "service.videoteca.guardiano"
GIORNI = 7
MAX_GIORNO = 8 * 1024 * 1024
MAX_SCATTI = 40
PAUSA_SCATTI = 20
ATTESA_LUNGA = 15
VIDEO_NON_PARTITO = 25
BATTITO = 30

ATTESE = (10138, 10160)                 # busydialog, busydialognocancel
FINESTRE_MESSAGGIO = {12002: "messaggio", 10100: "domanda", 12000: "elenco", 10147: "testo",
                      10103: "tastiera", 10107: "notifica", 10101: "avanzamento", 10106: "menu"}
PAROLE_BRUTTE = re.compile(r"(?i)errore|error|impossibil|fallit|non riuscit|non trovat|nessun[ao]? fonte|"
                           r"failed|unable|not found|scadut|timeout|non disponibil")
RIGA_REGISTRO = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+ T:\d+\s+(\w+)\s+<([^>]*)>:\s?(.*)$")
IMPORTANTI = re.compile(r"(?i)playback failed|two concurrent busydialogs|openfile|failed to open|"
                        r"inputstream|http error|curl|no stream|could not|unable to")
NOSTRI = ("plugin.video.saghe", ID)


def _ora(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


class Scatola(object):

    def __init__(self):
        self.cartella = xbmcvfs.translatePath("special://profile/addon_data/%s/scatola_nera/" % ID)
        self.scatti = os.path.join(self.cartella, "scatti")
        if not os.path.isdir(self.scatti):
            os.makedirs(self.scatti)
        self.prima = {}
        self.ultima_voce = ""
        self.attesa_da = 0
        self.attesa_segnalata = False
        self.voci_in_arrivo = False
        self.video = None
        self.ultimo_scatto = 0
        self.ultimo_controllo = 0
        self.ultimo_battito = 0
        self.ultimo_registro = 0
        self.pos_registro = None
        self.blocco_python = None
        self.gia_visti = {}
        self._pulisci()
        self._sessione_precedente()

    # ---------------------------------------------------------------- scrittura

    def evento(self, tipo, **dati):
        adesso = time.time()
        riga = dict(dati, t=_ora(adesso), ts=round(adesso, 2), tipo=tipo)
        p = os.path.join(self.cartella, time.strftime("%Y-%m-%d", time.localtime(adesso)) + ".jsonl")
        try:
            if tipo in ("schermata", "registro") and os.path.exists(p) and os.path.getsize(p) > MAX_GIORNO:
                return riga           # giornata gia' piena: si tengono solo anomalie e video
            with io.open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(riga, ensure_ascii=False) + "\n")
        except OSError as errore:
            xbmc.log("[Guardiano] scatola nera non scritta: %s" % errore, xbmc.LOGDEBUG)
        return riga

    def anomalia(self, genere, testo, fotografa=True, **dati):
        scatto = self.fotografa(genere) if fotografa else ""
        return self.evento("anomalia", genere=genere, testo=testo[:600], scatto=scatto,
                           cartella=xbmc.getInfoLabel("Container.FolderPath"),
                           voce=self.ultima_voce, **dati)

    def fotografa(self, motivo):
        adesso = time.time()
        if adesso - self.ultimo_scatto < PAUSA_SCATTI:
            return ""
        self.ultimo_scatto = adesso
        nome = "%s-%s.png" % (time.strftime("%Y%m%d-%H%M%S", time.localtime(adesso)), re.sub(r"\W+", "", motivo)[:20])
        xbmc.executebuiltin("TakeScreenshot(%s,sync)" % os.path.join(self.scatti, nome))
        try:
            vecchi = sorted(f for f in os.listdir(self.scatti) if f.endswith(".png"))
            for f in vecchi[:-MAX_SCATTI]:
                os.remove(os.path.join(self.scatti, f))
        except OSError as errore:
            xbmc.log("[Guardiano] scatti non puliti: %s" % errore, xbmc.LOGDEBUG)
        return nome

    def _pulisci(self):
        limite = time.strftime("%Y-%m-%d", time.localtime(time.time() - GIORNI * 86400))
        for f in os.listdir(self.cartella):
            if f.endswith(".jsonl") and f[:10] < limite:
                try:
                    os.remove(os.path.join(self.cartella, f))
                except OSError as errore:
                    xbmc.log("[Guardiano] giorno vecchio non tolto: %s" % errore, xbmc.LOGDEBUG)

    # ---------------------------------------------------------------- sessione

    def _file_sessione(self):
        return os.path.join(self.cartella, "sessione.json")

    def _sessione_precedente(self):
        try:
            with io.open(self._file_sessione(), encoding="utf-8") as f:
                prima = json.load(f)
        except (OSError, ValueError):
            prima = {}
        if prima.get("aperta"):
            self.anomalia("kodi_chiuso_da_solo",
                          "Kodi si era chiuso senza salutare (crollo o corrente staccata): ultimo segno di vita alle %s"
                          % _ora(prima.get("battito", 0)), fotografa=False, ultimo_battito=prima.get("battito"))
        self.evento("kodi_avviato", versione=xbmc.getInfoLabel("System.BuildVersion"),
                    skin=xbmc.getSkinDir())
        self._battito(time.time(), aperta=True)

    def _battito(self, adesso, aperta=True):
        self.ultimo_battito = adesso
        try:
            tmp = self._file_sessione() + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as f:
                json.dump({"aperta": aperta, "battito": adesso}, f)
            os.replace(tmp, self._file_sessione())
        except OSError as errore:
            xbmc.log("[Guardiano] battito non scritto: %s" % errore, xbmc.LOGDEBUG)

    def chiudi(self):
        self.evento("kodi_chiuso")
        self._battito(time.time(), aperta=False)

    # ---------------------------------------------------------------- il giro di ogni secondo

    def tick(self):
        try:
            self._tick()
        except Exception as errore:
            xbmc.log("[Guardiano] scatola nera: %s" % errore, xbmc.LOGDEBUG)

    def _tick(self):
        adesso = time.time()
        if adesso - self.ultimo_battito > BATTITO:
            self._battito(adesso)
        if adesso - self.ultimo_registro >= 2:
            self.ultimo_registro = adesso
            self._registro()
        in_video = xbmc.getCondVisibility("Player.HasVideo")
        if in_video and adesso - self.ultimo_controllo < 3:
            return
        self.ultimo_controllo = adesso
        self._schermo(adesso, in_video)
        self._video_che_non_parte(adesso)

    def _nome_finestra(self, numero):
        return (xbmc.getInfoLabel("Window(%d).Property(xmlfile)" % numero) or str(numero)).replace(".xml", "")

    def _testi(self, dialogo):
        titolo, testo = "", ""
        coppie = {10107: (401, 402), 12002: (1, 9), 10100: (1, 9), 10147: (1, 5), 12000: (1, None)}
        a, b = coppie.get(dialogo, (1, None))
        try:
            finestra = xbmcgui.Window(dialogo)
            titolo = finestra.getControl(a).getLabel()
            if b:
                testo = finestra.getControl(b).getLabel()
        except Exception:
            titolo = xbmc.getInfoLabel("Control.GetLabel(%d)" % a)
            testo = xbmc.getInfoLabel("Control.GetLabel(%d)" % b) if b else ""
        return titolo or "", testo or ""

    def _schermo(self, adesso, in_video):
        finestra = xbmcgui.getCurrentWindowId()
        dialogo = xbmcgui.getCurrentWindowDialogId()
        cartella = xbmc.getInfoLabel("Container.FolderPath")
        # Mentre la pagina carica, Kodi ha gia' il nuovo indirizzo ma zero voci:
        # "Chernobyl 0 voci" dell'11/09 aveva in realta' 36 risultati arrivati
        # otto secondi dopo. Le voci si contano quando la rotellina si ferma.
        in_arrivo = xbmc.getCondVisibility("Container.IsUpdating") or dialogo in ATTESE
        if finestra != self.prima.get("finestra") or cartella != self.prima.get("cartella"):
            self.evento("schermata", finestra=finestra, nome=self._nome_finestra(finestra), cartella=cartella,
                        da_voce=self.ultima_voce, voci="" if in_arrivo else xbmc.getInfoLabel("Container.NumItems"))
            self.voci_in_arrivo = in_arrivo
        elif self.voci_in_arrivo and not in_arrivo:
            self.voci_in_arrivo = False
            self.evento("cartella_pronta", cartella=cartella, voci=xbmc.getInfoLabel("Container.NumItems"))
        if dialogo != self.prima.get("dialogo"):
            self._dialogo_cambiato(adesso, dialogo)
        if dialogo in ATTESE and not self.attesa_segnalata and adesso - self.attesa_da > ATTESA_LUNGA:
            self.attesa_segnalata = True
            self.anomalia("attesa_lunga", "La rotellina gira da %d secondi" % (adesso - self.attesa_da))
        if not in_video:
            voce = xbmc.getInfoLabel("ListItem.Label")
            if voce:
                self.ultima_voce = voce
        self.prima = {"finestra": finestra, "dialogo": dialogo, "cartella": cartella}

    def _dialogo_cambiato(self, adesso, dialogo):
        prima = self.prima.get("dialogo")
        if prima in ATTESE and adesso - self.attesa_da > 5:
            self.evento("attesa_finita", secondi=round(adesso - self.attesa_da, 1))
        if dialogo in ATTESE:
            self.attesa_da = adesso
            self.attesa_segnalata = False
            return
        if dialogo in FINESTRE_MESSAGGIO:
            titolo, testo = self._testi(dialogo)
            self.evento("finestra", dialogo=dialogo, genere=FINESTRE_MESSAGGIO[dialogo], titolo=titolo, testo=testo[:600])
            if dialogo == 12002 or (dialogo == 10107 and PAROLE_BRUTTE.search("%s %s" % (titolo, testo))):
                self.anomalia("messaggio", "%s: %s" % (titolo, testo))
        elif dialogo not in (9999, 0):
            self.evento("finestra", dialogo=dialogo, genere=self._nome_finestra(dialogo))

    # ---------------------------------------------------------------- video

    def notifica(self, mittente, metodo, dati):
        try:
            self._notifica(mittente, metodo, dati)
        except Exception as errore:
            xbmc.log("[Guardiano] scatola nera, notifica: %s" % errore, xbmc.LOGDEBUG)

    def _notifica(self, mittente, metodo, dati):
        adesso = time.time()
        if metodo == "Player.OnPlay":
            self.video = {"chiesto": adesso, "partito": 0, "segnalato": False,
                          "titolo": xbmc.getInfoLabel("Player.Title") or self.ultima_voce,
                          "file": xbmc.getInfoLabel("Player.Filenameandpath")[:300]}
            self.evento("video_chiesto", titolo=self.video["titolo"], file=self.video["file"], da_voce=self.ultima_voce)
        elif metodo == "Player.OnAVStart":
            if self.video and not self.video["partito"]:
                self.video["partito"] = adesso
                self.evento("video_partito", titolo=self.video["titolo"], attesa=round(adesso - self.video["chiesto"], 1))
        elif metodo == "Player.OnStop":
            fine = False
            try:
                fine = bool(json.loads(dati or "{}").get("end"))
            except ValueError:
                pass
            v = self.video or {}
            self.video = None
            if v and not v.get("partito"):
                if not v.get("segnalato"):
                    self.anomalia("video_non_partito", "Il video '%s' si e' fermato senza mai partire" % v.get("titolo", ""),
                                  fotografa=False, file=v.get("file", ""))
            elif v:
                durata = adesso - v["partito"]
                self.evento("video_fermato", titolo=v.get("titolo", ""), durata=round(durata), finito=fine,
                            sospetto=(not fine and durata < 60))
        elif metodo in ("Player.OnPause", "Player.OnResume", "System.OnSleep", "System.OnWake", "System.OnQuit",
                        "GUI.OnScreensaverActivated", "GUI.OnScreensaverDeactivated"):
            self.evento("kodi", metodo=metodo)
        elif mittente not in ("xbmc", ""):
            self.evento("messaggio_addon", mittente=mittente, metodo=metodo, dati=(dati or "")[:500])

    def _video_che_non_parte(self, adesso):
        v = self.video
        if v and not v["partito"] and not v["segnalato"] and adesso - v["chiesto"] > VIDEO_NON_PARTITO:
            v["segnalato"] = True
            self.anomalia("video_non_partito", "Il video '%s' e' chiesto da %d secondi e non parte"
                          % (v["titolo"], adesso - v["chiesto"]), file=v["file"])

    # ---------------------------------------------------------------- registro di Kodi

    def _registro(self):
        p = os.path.join(xbmcvfs.translatePath("special://logpath"), "kodi.log")
        try:
            misura = os.path.getsize(p)
        except OSError:
            return
        if self.pos_registro is None or misura < self.pos_registro:
            self.pos_registro = misura if self.pos_registro is None else 0
            return
        if misura == self.pos_registro:
            return
        with io.open(p, encoding="utf-8", errors="replace") as f:
            f.seek(max(self.pos_registro, misura - 512 * 1024))
            testo = f.read()
        self.pos_registro = misura
        for riga in testo.splitlines():
            self._riga_registro(riga)

    def _riga_registro(self, riga):
        m = RIGA_REGISTRO.match(riga)
        if not m:
            if self.blocco_python is not None:
                self.blocco_python.append(riga)
            return
        _quando, livello, _dove, messaggio = m.groups()
        livello = livello.lower()
        if "EXCEPTION Thrown" in messaggio or messaggio.startswith("Traceback"):
            self.blocco_python = [messaggio]
            return
        if self.blocco_python is not None:
            self.blocco_python.append(messaggio)
            if "End of Python script error report" in messaggio:
                self._errore_python("\n".join(self.blocco_python))
                self.blocco_python = None
            return
        if livello in ("error", "fatal") or IMPORTANTI.search(messaggio):
            chiave = re.sub(r"\d+", "#", messaggio)[:160]
            adesso = time.time()
            if adesso - self.gia_visti.get(chiave, 0) < 60:
                return
            self.gia_visti[chiave] = adesso
            if len(self.gia_visti) > 500:
                self.gia_visti = {}
            self.evento("registro", livello=livello, testo=messaggio[:600])
            # "LoadTimers: ... Failed to open file" e' la skin senza Timers.xml
            # (facoltativo): ogni avvio del Raspberry, e non e' un guasto.
            if re.search(r"(?i)playback failed|two concurrent busydialogs|failed to open", messaggio) \
                    and not messaggio.startswith("LoadTimers"):
                self.anomalia("registro", messaggio)

    def _errore_python(self, blocco):
        contenuto = re.search(r"Error Contents:\s*(.+)", blocco)
        addon = re.findall(r"addons[\\/]+([^\\/]+)[\\/]", blocco)
        di_chi = addon[-1] if addon else "?"
        testo = "%s: %s" % (di_chi, contenuto.group(1).strip() if contenuto else "errore Python")
        self.anomalia("errore_python", testo, fotografa=di_chi in NOSTRI, addon=di_chi, traccia=blocco[-3000:])

    # ---------------------------------------------------------------- per stato.json

    def riassunto(self, ore=24):
        """Le anomalie delle ultime `ore`, per il giro del guardiano e l'atlante."""
        limite = time.time() - ore * 3600
        fuori = []
        for giorno in sorted(os.listdir(self.cartella))[-2:]:
            if not giorno.endswith(".jsonl"):
                continue
            with io.open(os.path.join(self.cartella, giorno), encoding="utf-8", errors="replace") as f:
                for riga in f:
                    if '"anomalia"' not in riga:
                        continue
                    try:
                        e = json.loads(riga)
                    except ValueError:
                        continue
                    if e.get("ts", 0) >= limite:
                        fuori.append({k: e.get(k) for k in ("t", "genere", "testo", "addon")})
        conti = {}
        for e in fuori:
            conti[e["genere"]] = conti.get(e["genere"], 0) + 1
        return {"ore": ore, "conti": conti, "ultime": fuori[-20:]}
