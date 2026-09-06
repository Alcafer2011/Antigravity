# -*- coding: utf-8 -*-
"""
Risoluzione delle fonti: da "serie + episodio" a "qualcosa che parte".

Ordine di preferenza, sempre:
  1. LOCALE - i tuoi file. Nessuno te li puo' togliere, e Kodi sa il minuto.
  2. GRATIS - YouTube/Yamato, Pluto TV, Mediaset Infinity.
  3. ABBONAMENTO che possiedi.
  4. ABBONAMENTO che non possiedi: mostrato ma marcato, cosi' sai cosa manca.
"""

import os
import re

import xbmc
import xbmcaddon
import xbmcvfs

from . import catalogo

ADDON = xbmcaddon.Addon()

ESTENSIONI = (".mkv", ".mp4", ".avi", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv", ".mov")


# --------------------------------------------------------------------------
# Fonte locale
# --------------------------------------------------------------------------

def cartella_locale(serie_id):
    """Cartella impostata dall'utente per questa serie, o '' se non c'e'."""
    radice = ADDON.getSetting("cartella_serie") or ""
    if not radice:
        return ""
    percorso = os.path.join(xbmcvfs.translatePath(radice), serie_id)
    return percorso if xbmcvfs.exists(percorso) else ""


def file_locale(serie_id, ep):
    """Cerca il file dell'episodio nella cartella della serie.

    Riconosce i modi in cui la gente numera davvero i file:
    '137', 'E137', 'Ep137', '1x137', 'S01E137' - con o senza zeri davanti.
    """
    cartella = cartella_locale(serie_id)
    if not cartella:
        return ""

    try:
        _, files = xbmcvfs.listdir(cartella)
    except Exception:
        return ""

    schemi = [
        r"(?:^|[^0-9])0*%d(?:[^0-9]|$)" % ep,
        r"[eE][pP]?0*%d(?:[^0-9]|$)" % ep,
        r"[sS]\d+[eE]0*%d(?:[^0-9]|$)" % ep,
        r"\d+[xX]0*%d(?:[^0-9]|$)" % ep,
    ]

    for nome in sorted(files):
        if not nome.lower().endswith(ESTENSIONI):
            continue
        for schema in schemi:
            if re.search(schema, nome):
                return os.path.join(cartella, nome)
    return ""


# --------------------------------------------------------------------------
# Abbonamenti posseduti
# --------------------------------------------------------------------------

def giorni_alla_scadenza(fonte_id):
    """Quanti giorni mancano alla scadenza di questo abbonamento.

    None = nessuna scadenza impostata (abbonamento normale, si rinnova da se').
    Numero negativo = e' gia' scaduto.
    """
    # NON si usa datetime.strptime: dentro Kodi vale None e solleva
    # "TypeError: NoneType object is not callable" (il modulo _strptime non
    # viene caricato nei thread). Guasto vero: ha buttato giu' tutto il menu.
    # Si legge la data a mano, che tanto sono tre numeri.
    import datetime
    try:
        testo = (ADDON.getSetting("scadenza_" + fonte_id) or "").strip()
    except Exception:
        return None
    if not testo:
        return None
    for separatore in ("/", "-"):
        pezzi = testo.split(separatore)
        if len(pezzi) != 3:
            continue
        try:
            a, b, c = (int(x) for x in pezzi)
        except ValueError:
            continue
        # gg/mm/aaaa oppure aaaa-mm-gg: si distingue da dove sta l'anno
        giorno, mese, anno = (a, b, c) if c > 31 else (c, b, a)
        try:
            d = datetime.date(anno, mese, giorno)
        except ValueError:
            continue
        return (d - datetime.date.today()).days
    return None


def possiede(fonte_id):
    """Ce l'ho DAVVERO adesso?

    Non basta la casella spuntata: una prova gratuita scaduta e' come non
    averlo. Se e' scaduto si risponde no, cosi' l'add-on smette di proporlo e
    passa direttamente a s4me invece di mandarti su una schermata di pagamento.
    """
    fonte = catalogo.FONTI.get(fonte_id, {})
    chiave = fonte.get("chiave_abbonamento")
    if not chiave:
        return True  # gratis
    if not ADDON.getSettingBool(chiave):
        return False
    # Se il calcolo della scadenza fallisce per qualunque motivo, si considera
    # l'abbonamento valido: meglio proporre una fonte in piu' che rompere
    # l'add-on. Una comodita' non deve poter buttare giu' il menu.
    try:
        giorni = giorni_alla_scadenza(fonte_id)
    except Exception:
        return True
    if giorni is not None and giorni < 0:
        return False
    return True


# --------------------------------------------------------------------------

def fonti_disponibili(serie_id, ep):
    """Elenco ordinato di fonti utilizzabili per questo episodio.

    Ogni voce:
        id, etichetta, tipo, dentro_kodi, posseduta, percorso
    """
    serie = catalogo.SERIE[serie_id]
    risultato = []

    # 1. Locale
    locale = file_locale(serie_id, ep)
    if locale:
        risultato.append({
            "id": "locale",
            "etichetta": "I tuoi file",
            "tipo": "locale",
            "dentro_kodi": True,
            "posseduta": True,
            "percorso": locale,
        })

    # 2-4. Fonti dichiarate nel catalogo
    for fonte_id in serie.get("fonti", []):
        fonte = catalogo.FONTI.get(fonte_id)
        if not fonte:
            continue
        risultato.append({
            "id": fonte_id,
            "etichetta": fonte["etichetta"],
            "tipo": fonte["tipo"],
            "dentro_kodi": fonte["tipo"] in ("plugin",),
            "posseduta": possiede(fonte_id),
            "percorso": "",
        })

    # Prima il locale, poi il gratis posseduto, poi il resto.
    def peso(f):
        if f["tipo"] == "locale":
            return 0
        gratis = catalogo.FONTI.get(f["id"], {}).get("gratis", False)
        if gratis:
            return 1
        return 2 if f["posseduta"] else 3

    risultato.sort(key=peso)
    return risultato


def fonte_migliore(serie_id, ep):
    """La fonte che si userebbe premendo Play. None se non ce n'e' nessuna usabile."""
    for f in fonti_disponibili(serie_id, ep):
        if f["posseduta"]:
            return f
    return None


# --------------------------------------------------------------------------
# Avvio
# --------------------------------------------------------------------------

_LOGHI = os.path.join(
    xbmcvfs.translatePath(ADDON.getAddonInfo("path")), "resources", "loghi")


def logo(fonte_id):
    """Percorso del logo del distributore, o '' se non ce l'ha."""
    nome = catalogo.FONTI.get(fonte_id, {}).get("logo", "")
    if not nome:
        return ""
    percorso = os.path.join(_LOGHI, nome + ".jpg")
    return percorso if os.path.exists(percorso) else ""


def sigla(fonte_id):
    return catalogo.FONTI.get(fonte_id, {}).get("sigla", "")


def link_diretto(fonte_id, serie_id):
    """URL che apre l'app gia' posizionata sulla serie.

    Verificato sul box il 04/09/2026: funziona su Netflix, NON su Prime Video
    (l'intento viene accettato ma l'app non si apre). Dove non funziona si
    restituisce '' e ci si limita ad aprire l'applicazione.
    """
    modello = catalogo.FONTI.get(fonte_id, {}).get("deeplink", "")
    ident = catalogo.SERIE.get(serie_id, {}).get("id_" + fonte_id, "")
    if not modello or not ident:
        return ""
    return modello % ident


def comando_app(pacchetto):
    """Builtin di Kodi per aprire un'app Android."""
    return 'StartAndroidActivity("%s")' % pacchetto


def avvia_app(pacchetto, url=""):
    """Apre l'app. Con url, tenta di posizionarla sulla serie."""
    if url:
        xbmc.executebuiltin(
            'StartAndroidActivity("%s","android.intent.action.VIEW","","%s")'
            % (pacchetto, url))
    else:
        xbmc.executebuiltin(comando_app(pacchetto))


def su_android():
    """Vero solo sul box: e' l'unico apparecchio dove esistono le app.

    Serve perche' `avvia_app` usa StartAndroidActivity, che su LibreELEC non
    fa assolutamente NIENTE - e senza errori. Sul Raspberry l'utente vedeva
    l'avviso "cerca l'episodio 2" e poi non succedeva piu' nulla: sembrava un
    guasto dell'add-on, era solo un'app che li' non esiste.
    """
    try:
        return bool(xbmc.getCondVisibility("System.Platform.Android"))
    except Exception:
        return False
