# -*- coding: utf-8 -*-
"""LA SENTINELLA: si accorge da sola quando escono episodi nuovi.

CHIESTO DALL'UTENTE (07/09/2026)
    "se escono episodi nuovi, novita' di qualsiasi cosa abbiamo noi, la vede
    in automatico e me lo dice? e me la aggiunge?"
    Si', tutte e due le cose. Questo file fa la prima; la seconda la fa
    `catalogo.applica_aggiunte`, che allunga la catena senza che nessuno
    debba toccare il catalogo a mano.

COME FUNZIONA
    Una volta alla settimana chiede a TMDb quanti episodi hanno le serie
    che nel catalogo risultano ANCORA IN CORSO. Se il numero e' cresciuto:
      - lo scrive in `aggiunte.json` (nei dati dell'utente, non nel codice)
      - avvisa a schermo, una volta sola per novita'
    Alla riapertura la saga e' gia' piu' lunga e "Continua a guardare"
    punta al posto giusto.

PERCHE' NON SI TOCCA IL CATALOGO
    `catalogo.py` e' CODICE, e viene sovrascritto a ogni aggiornamento
    dell'add-on. Le aggiunte stanno nei dati dell'utente e sopravvivono.
    E se una crescita fosse sbagliata, si cancella un file e tutto torna
    com'era: nessun danno permanente.

QUALI SERIE GUARDA, e perche' non tutte
    Solo quelle che possono davvero crescere. Dragon Ball e' finito nel
    1996: chiederlo ogni settimana sarebbe rumore. Il criterio e' l'anno di
    fine scritto nel catalogo: se manca o e' quello corrente (o il
    prossimo), la serie e' in corso.
"""

import io
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()

# Ogni quanto si controlla. Una settimana: gli episodi escono una volta a
# settimana, controllare piu' spesso e' solo traffico sprecato su 4 Mbps.
INTERVALLO = 7 * 24 * 60 * 60
CHIAVE_TMDB = "a1ab8b8669da03637a4b98fa39c39228"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _cartella_dati():
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    return c


def _file_aggiunte():
    return os.path.join(_cartella_dati(), "aggiunte.json")


def _file_stato():
    return os.path.join(_cartella_dati(), "sentinella.json")


def _radice_addon():
    return xbmcvfs.translatePath(ADDON.getAddonInfo("path"))


def leggi_aggiunte():
    """Le crescite gia' trovate. Vuoto se non c'e' niente: mai un errore."""
    try:
        with io.open(_file_aggiunte(), encoding="utf-8") as f:
            d = json.load(f)
        return {k: int(v) for k, v in d.items()}
    except Exception:
        return {}


def _scrivi_aggiunte(dati):
    try:
        with io.open(_file_aggiunte(), "w", encoding="utf-8") as f:
            f.write(json.dumps(dati, ensure_ascii=False, indent=1))
        return True
    except Exception as e:
        xbmc.log("[Le Saghe] sentinella, non ho salvato: %s" % e,
                 xbmc.LOGWARNING)
        return False


def _stato():
    try:
        with io.open(_file_stato(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"quando": 0, "trovate": []}


def _scrivi_stato(s):
    try:
        with io.open(_file_stato(), "w", encoding="utf-8") as f:
            f.write(json.dumps(s, ensure_ascii=False, indent=1))
    except Exception:
        pass


def scaduta():
    return (time.time() - _stato().get("quando", 0)) > INTERVALLO


def _identificativi():
    """serie_id -> identificativo TMDb, dal file preparato sul computer."""
    try:
        with io.open(os.path.join(_radice_addon(), "resources", "tmdb.json"),
                     encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _chiedi(url):
    import urllib.request
    for _ in range(2):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=20) as f:
                return json.loads(f.read().decode("utf-8"))
        except Exception:
            time.sleep(2)
    return {}


def _in_corso(serie, anno_ora):
    """Vero se la serie puo' ancora crescere.

    Il criterio e' l'anno di fine scritto nel catalogo: se non c'e', o e'
    quello corrente o il prossimo, la serie e' viva. Chiedere a TMDb di
    Dragon Ball, finito nel 1996, sarebbe rumore ogni settimana.
    """
    anni = str(serie.get("anni") or "")
    if "-" not in anni:
        return True
    fine = anni.split("-")[-1].strip()
    if not fine.isdigit():
        return True
    return int(fine) >= anno_ora


def controlla(catalogo, avvisa=True):
    """Chiede a TMDb chi e' cresciuto. Torna la lista delle novita'.

    `catalogo` e' il modulo gia' caricato: cosi' questo file non lo importa
    e resta usabile anche dal banco di prova.
    """
    ids = _identificativi()
    if not ids:
        xbmc.log("[Le Saghe] sentinella: manca resources/tmdb.json",
                 xbmc.LOGWARNING)
        return []

    anno_ora = int(time.strftime("%Y"))
    aggiunte = leggi_aggiunte()
    novita = []

    for sid, serie in catalogo.SERIE.items():
        conf = ids.get(sid)
        if not conf or not _in_corso(serie, anno_ora):
            continue
        # Lo SCOSTAMENTO: quante puntate della stessa scheda TMDb
        # appartengono alla serie precedente.
        #
        # IL FALSO ALLARME DEL 07/09/2026: la sentinella ha annunciato
        # "Bleach TYBW: da 50 a 416 (+366)". Falso. `bleach` e `bleach_tybw`
        # sono UNA scheda sola su TMDb (416 puntate) che noi teniamo
        # spezzata in due; la seconda comincia dalla 367. Senza sottrarre
        # lo scostamento, la seconda meta' sembra lunga quanto tutto.
        if isinstance(conf, dict):
            tid, scostamento = conf.get("id"), int(conf.get("offset") or 0)
        else:
            tid, scostamento = conf, 0
        if not tid:
            continue
        nostri = int(aggiunte.get(sid) or serie.get("episodi") or 0)
        d = _chiedi("https://api.themoviedb.org/3/tv/%s?api_key=%s"
                    % (tid, CHIAVE_TMDB))
        loro = int(d.get("number_of_episodes") or 0) - scostamento
        if loro > nostri:
            aggiunte[sid] = loro
            novita.append({
                "serie": sid,
                "titolo": serie.get("titolo", sid),
                "prima": nostri,
                "adesso": loro,
                "nuovi": loro - nostri,
            })
        # Un respiro fra una domanda e l'altra: e' un servizio gratuito.
        if xbmc.Monitor().waitForAbort(0.3):
            break

    if novita:
        _scrivi_aggiunte(aggiunte)

    s = _stato()
    s["quando"] = int(time.time())
    s["trovate"] = novita + (s.get("trovate") or [])
    s["trovate"] = s["trovate"][:40]
    _scrivi_stato(s)

    if novita and avvisa:
        _avvisa(novita)
    return novita


def _avvisa(novita):
    """Un avviso solo, che dice la cosa piu' utile: quanti e dove."""
    quante = sum(n["nuovi"] for n in novita)
    if len(novita) == 1:
        n = novita[0]
        testo = "%d nuovi di %s" % (n["nuovi"], n["titolo"])
    else:
        testo = "%d episodi nuovi in %d saghe" % (quante, len(novita))
    xbmcgui.Dialog().notification("Le Saghe - novita'", testo,
                                  xbmcgui.NOTIFICATION_INFO, 9000)
    for n in novita:
        xbmc.log("[Le Saghe] %s: da %d a %d episodi (+%d)"
                 % (n["titolo"], n["prima"], n["adesso"], n["nuovi"]),
                 xbmc.LOGINFO)


def ultime_novita():
    """Le novita' trovate finora, per mostrarle in un elenco."""
    return _stato().get("trovate") or []


def controlla_se_serve(catalogo):
    """Fa il giro solo se e' passata una settimana. Non blocca: filo a parte."""
    if not scaduta():
        return False
    import threading

    def _lavora():
        try:
            controlla(catalogo)
        except Exception as e:
            xbmc.log("[Le Saghe] sentinella caduta: %s" % e, xbmc.LOGWARNING)

    t = threading.Thread(target=_lavora)
    t.daemon = True
    t.start()
    return True
