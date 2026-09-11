# -*- coding: utf-8 -*-
"""CONSIGLIATI PER TE: guarda cosa guardi e propone, come fa TikTok.

CHIESTO DALL'UTENTE (07/09/2026)
    "uno script come quello di tiktok che analizza i miei comportamenti,
    trova e mi propone; se mi piace lo aggiungo e viene aggiunto nelle
    sezioni e nei modi giusti"

COME "ANALIZZA I COMPORTAMENTI", in concreto
    Non serve niente di misterioso: quello che guardi e' gia' scritto in
    `progresso.json` - quali saghe hai aperto, a che punto sei, quando.
    Da li' si ricavano le serie che ti interessano davvero, e si chiede a
    TMDb "chi guarda queste, cosa guarda anche".

PERCHE' NON E' UNA LISTA A CASO
    Un consiglio vale di piu' se arriva da PIU' cose che guardi: se tre
    delle tue saghe portano allo stesso titolo, quel titolo va in cima.
    E chi ha guardato di piu' pesa di piu' di chi ha aperto un episodio e
    l'ha lasciato li'.

LE REGOLE DI CASA VALGONO ANCHE QUI
    - niente che sia gia' nel catalogo (sarebbe un doppione)
    - solo roba con una scheda in italiano: se TMDb non ha nemmeno il
      titolo tradotto, in italiano non si trovera' da nessuna parte
    - si dice sempre quanti episodi ha e di che anni e', come per tutto
      il resto: mai un titolo nudo

QUANDO SI AGGIUNGE
    `aggiungi()` scrive la serie nei DATI DELL'UTENTE (non nel codice) e
    scarica la sua scheda - locandine, titoli e trame degli episodi in
    italiano. Al riavvio la trovi nel raggruppamento "Aggiunte da te", con
    la sua catena, come qualsiasi altra saga.
"""

import io
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()

from resources.lib.tmdb import CHIAVE as CHIAVE_TMDB  # la chiave sta in un posto solo
IMG = "https://image.tmdb.org/t/p/w500"
SFONDO = "https://image.tmdb.org/t/p/w1280"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Ogni quanto si rifanno i consigli. Non serve piu' spesso: i gusti non
# cambiano in un giorno, e ogni giro costa una trentina di domande a TMDb.
DURATA = 3 * 24 * 60 * 60
QUANTI = 30                 # quanti consigli tenere


def _dati():
    c = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.saghe/")
    if not xbmcvfs.exists(c):
        xbmcvfs.mkdirs(c)
    return c


def _file_consigli():
    return os.path.join(_dati(), "consigli.json")


def _file_serie_mie():
    return os.path.join(_dati(), "serie_mie.json")


def _cartella_schede_mie():
    c = os.path.join(_dati(), "schede")
    if not os.path.isdir(c):
        try:
            os.makedirs(c)
        except Exception as _errore:
            xbmc.log("[Le Saghe] _cartella_schede_mie: errore ignorato: %s" % _errore, xbmc.LOGDEBUG)
    return c


def _chiedi(url):
    import urllib.request
    for _ in range(2):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=20) as f:
                return json.loads(f.read().decode("utf-8"))
        except Exception:
            time.sleep(1.5)
    return {}


def _identificativi():
    try:
        with io.open(os.path.join(
                xbmcvfs.translatePath(ADDON.getAddonInfo("path")),
                "resources", "tmdb.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# --------------------------------------------------------------------------
# Cosa guardi
# --------------------------------------------------------------------------

def _gusti(catalogo, progresso):
    """Le serie che ti interessano, col loro peso.

    Il peso e' quanti episodi hai visto: chi ne ha visti cento conta piu'
    di chi ne ha aperto uno. Cosi' i consigli seguono quello che guardi
    davvero, non quello che hai sfiorato una volta.
    """
    pesi = {}
    try:
        tutte = progresso.tutte()
    except Exception:
        tutte = {}
    for pid, stato in (tutte or {}).items():
        p = catalogo.PERCORSI.get(pid)
        if not p:
            continue
        visti = len(stato.get("visti") or []) or 1
        for sid, _a, _b in p["segmenti"]:
            pesi[sid] = pesi.get(sid, 0) + visti
    return pesi


# Quanti voti su TMDb deve avere un titolo per valere un consiglio.
# Misurato sui consigliati di Naruto: con 100 restano 10 titoli su 16,
# e spariscono proprio quelli che l'utente non riconosceva.
SOGLIA_VOTI = 100


def _titolo_leggibile(titolo):
    """Vero se il titolo e' scritto nel nostro alfabeto.

    Non e' snobismo verso il giapponese: e' che TMDb ci restituisce il
    titolo originale proprio QUANDO la traduzione italiana non esiste. Un
    titolo in kanji e' il segnale che quella serie, in italiano, non c'e'.
    Si accetta qualche carattere strano (accenti, punteggiatura): il
    criterio e' che la maggior parte delle lettere sia latina.
    """
    t = (titolo or "").strip()
    if not t:
        return False
    lettere = [c for c in t if c.isalpha()]
    if not lettere:
        return False
    latine = sum(1 for c in lettere if ord(c) < 0x250)
    return latine >= len(lettere) * 0.6


def _tmdb_gia_nostri(catalogo):
    """Gli identificativi TMDb delle serie che ABBIAMO GIA'.

    IL DIFETTO DEL 07/09/2026: i primi consigli proponevano Naruto, Naruto
    Shippuden e Dragon Ball Z - roba che sta gia' in catalogo da mesi. Il
    controllo dei doppioni confrontava le CHIAVI NOSTRE ("naruto", "dbz")
    con quelle di TMDb ("tmdb_31910"): due alfabeti diversi, non
    combaciavano mai. Il confronto giusto e' sull'identificativo TMDb, che
    e' l'unica cosa che le due parti hanno in comune.
    """
    fuori = set()
    for sid, conf in _identificativi().items():
        if sid not in catalogo.SERIE:
            continue
        tid = conf.get("id") if isinstance(conf, dict) else conf
        if tid:
            fuori.add(str(tid))
    # e quelle aggiunte da te, che hanno l'identificativo nel nome
    for sid in catalogo.SERIE:
        if sid.startswith("tmdb_"):
            fuori.add(sid[5:])
    return fuori


# --------------------------------------------------------------------------
# I consigli
# --------------------------------------------------------------------------

def leggi():
    """I consigli gia' calcolati. Non va mai in rete."""
    try:
        with io.open(_file_consigli(), encoding="utf-8") as f:
            return (json.load(f) or {}).get("voci") or []
    except Exception:
        return []


def scaduti():
    try:
        with io.open(_file_consigli(), encoding="utf-8") as f:
            return (time.time() - (json.load(f) or {}).get("quando", 0)) > DURATA
    except Exception:
        return True


def calcola(catalogo, progresso, avvisa=False):
    """Chiede a TMDb cosa somiglia a quello che guardi. Lento: filo a parte."""
    ids = _identificativi()
    pesi = _gusti(catalogo, progresso)
    if not pesi:
        # Mai guardato niente: si parte dalle saghe piu' rappresentative,
        # se no la riga resterebbe vuota per sempre.
        pesi = {s: 1 for s in ("db", "naruto", "one_piece", "ss")
                if s in catalogo.SERIE}

    nostre = _tmdb_gia_nostri(catalogo)
    gia_mie = set(k[5:] for k in _leggi_serie_mie() if k.startswith("tmdb_"))
    # Quelle a cui hai messo il pollice GIU'. Lette una volta sola, non a
    # ogni titolo: il file e' piccolo ma il giro e' di ~200 confronti.
    # Se il modulo manca (add-on vecchio), i consigli funzionano lo stesso.
    try:
        from resources.lib import miolista
        bocciate = miolista.bocciate_tmdb()
    except Exception:
        bocciate = set()
    punteggi = {}

    for sid, peso in sorted(pesi.items(), key=lambda x: -x[1])[:12]:
        conf = ids.get(sid)
        tid = conf.get("id") if isinstance(conf, dict) else conf
        if not tid:
            continue
        for cosa in ("recommendations", "similar"):
            d = _chiedi("https://api.themoviedb.org/3/tv/%s/%s"
                        "?api_key=%s&language=it-IT" % (tid, cosa, CHIAVE_TMDB))
            for r in (d.get("results") or [])[:12]:
                rid = str(r.get("id"))
                # niente doppioni: ne' col catalogo ne' con quello che hai
                # gia' aggiunto tu. Il confronto e' sull'identificativo
                # TMDb, non sulle nostre chiavi: vedi _tmdb_gia_nostri.
                if rid in nostre or rid in gia_mie:
                    continue
                # IL POLLICE GIU' VALE DAVVERO. Senza questa riga sarebbe un
                # giochino: continuare a riproporre una cosa che l'utente ha
                # rifiutato e' peggio che non consigliare niente.
                if rid in bocciate:
                    continue
                # SENZA TITOLO IN ITALIANO NON SI TROVA IN ITALIANO.
                # TMDb, quando la traduzione non c'e', restituisce il titolo
                # ORIGINALE: fra i primi consigli sono usciti "星の海のアムリ"
                # e "真夜中ぱんチ". Proporre una cosa che l'utente non potra'
                # mai guardare in italiano e' peggio che non proporla.
                if not _titolo_leggibile(r.get("name")):
                    continue
                # TROPPO OSCURO PER ESSERE UN CONSIGLIO.
                # L'utente (10/09/2026), guardando la riga: sono titoli che
                # non riconosce. La prima diagnosi - "sono in inglese, quindi
                # in italiano non esistono" - era SBAGLIATA: TMDb dice che
                # "Kill Blue" e "True Beauty" IL titolo italiano ce l'hanno,
                # ed e' quello (in Italia molti anime escono col nome
                # inglese). Verificato anche con /translations.
                # Il vero segno e' un altro, e si misura: i titoli oscuri
                # hanno 40-50 voti su TMDb, quelli che uno riconosce ne
                # hanno migliaia (Boruto 2522, Dragon Ball Z 4996, Young
                # Justice 1249; Marriage Toxin 47, Black Cat 40).
                # Sotto la soglia non e' un consiglio: e' rumore.
                if (r.get("vote_count") or 0) < SOGLIA_VOTI:
                    continue
                v = punteggi.setdefault(rid, {
                    "id": rid,
                    "titolo": r.get("name"),
                    "originale": r.get("original_name"),
                    "trama": (r.get("overview") or "").strip(),
                    "immagine": (IMG + r["poster_path"]) if r.get("poster_path") else "",
                    "sfondo": (SFONDO + r["backdrop_path"]) if r.get("backdrop_path") else "",
                    "anno": (r.get("first_air_date") or "")[:4],
                    "voto": r.get("vote_average") or 0,
                    "punti": 0,
                    "perche": [],
                })
                v["punti"] += peso
                nome_nostro = catalogo.SERIE.get(sid, {}).get("titolo", sid)
                if nome_nostro not in v["perche"]:
                    v["perche"].append(nome_nostro)
        if xbmc.Monitor().waitForAbort(0.2):
            break

    voci = sorted(punteggi.values(),
                  key=lambda v: (-v["punti"], -(v["voto"] or 0)))[:QUANTI]
    for v in voci:
        # La riga che spiega il consiglio. E' la differenza fra "guarda
        # questo" e "te lo propongo perche' guardi Dragon Ball e Naruto".
        v["motivo"] = "Perche' guardi " + ", ".join(v["perche"][:3])

    try:
        with io.open(_file_consigli(), "w", encoding="utf-8") as f:
            f.write(json.dumps({"quando": int(time.time()), "voci": voci},
                               ensure_ascii=False))
    except Exception as e:
        xbmc.log("[Le Saghe] consigli non salvati: %s" % e, xbmc.LOGWARNING)

    xbmc.log("[Le Saghe] consigli aggiornati: %d proposte" % len(voci),
             xbmc.LOGINFO)
    return voci


def calcola_se_serve(catalogo, progresso):
    """Rifa' i consigli in un filo a parte. Torna subito."""
    if not scaduti():
        return False
    import threading

    def _lavora():
        try:
            calcola(catalogo, progresso)
        except Exception as e:
            xbmc.log("[Le Saghe] consigli caduti: %s" % e, xbmc.LOGWARNING)

    t = threading.Thread(target=_lavora, daemon=True)
    t.daemon = True
    t.start()
    return True


# --------------------------------------------------------------------------
# Aggiungere una serie proposta
# --------------------------------------------------------------------------

def _leggi_serie_mie():
    try:
        with io.open(_file_serie_mie(), encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def serie_mie():
    return _leggi_serie_mie()


def aggiungi(tmdb_id, tipo="anime"):
    """Aggiunge la serie al catalogo e ne scarica la scheda.

    `tipo` decide la sezione: "anime" -> Cartoni animati, "serietv" ->
    Serie TV. Torna (fatto, messaggio). Il messaggio si mostra a schermo,
    quindi e' scritto per essere letto da tre metri di distanza.
    """
    tid = str(tmdb_id)
    testa = _chiedi("https://api.themoviedb.org/3/tv/%s?api_key=%s&language=it-IT"
                    % (tid, CHIAVE_TMDB))
    if not testa or not testa.get("name"):
        return False, "Non sono riuscito a leggere la scheda: riprova."

    quanti = int(testa.get("number_of_episodes") or 0)
    if quanti < 1:
        return False, "Questa serie non ha episodi elencati: non la aggiungo."

    sid = "tmdb_%s" % tid
    inizio = (testa.get("first_air_date") or "")[:4]
    fine = (testa.get("last_air_date") or "")[:4]

    # Il doppiaggio italiano non lo sa nessuno con certezza: si dice quello
    # che si sa, cioe' se esiste almeno la scheda in italiano. La regola di
    # casa e' non promettere l'italiano se non si e' sicuri.
    trad = _chiedi("https://api.themoviedb.org/3/tv/%s/translations?api_key=%s"
                   % (tid, CHIAVE_TMDB))
    ha_italiano = any(t.get("iso_639_1") == "it"
                      for t in (trad.get("translations") or []))

    tipo = "serietv" if str(tipo).lower() in (
        "serietv", "serie", "live", "liveaction", "attori") else "anime"

    mie = _leggi_serie_mie()
    mie[sid] = {
        "titolo": testa.get("name"),
        "anni": ("%s-%s" % (inizio, fine)) if inizio and fine else inizio,
        "episodi": quanti,
        "audio_ita": bool(ha_italiano),
        "sottotitoli_ita": not ha_italiano,
        "nota": (testa.get("overview") or "").strip()[:400],
        "tmdb": int(tid),
        "tipo": tipo,
        "aggiunta": int(time.time()),
    }
    try:
        with io.open(_file_serie_mie(), "w", encoding="utf-8") as f:
            f.write(json.dumps(mie, ensure_ascii=False, indent=1))
    except Exception as e:
        return False, "Non sono riuscito a salvarla: %s" % e

    quante_schede = _scarica_scheda(tid, sid, testa)

    dove = ("Serie TV > Aggiunte da te" if tipo == "serietv"
            else "Cartoni animati > Aggiunte da te")
    return True, ("[B]%s[/B] aggiunta.\n\n%d episodi, %s.\n%s\n\n"
                  "La trovi in %s."
                  % (testa.get("name"), quanti,
                     mie[sid]["anni"] or "anno sconosciuto",
                     "Scheda scaricata: %d episodi con titolo e trama."
                     % quante_schede if quante_schede else
                     "La scheda dettagliata non era disponibile.", dove))


def _scarica_scheda(tid, sid, testa):
    """Titoli, trame e immagini degli episodi, in italiano. Quanti ne ha presi."""
    scheda = {
        "serie": testa.get("name") or "",
        "poster": (IMG + testa["poster_path"]) if testa.get("poster_path") else "",
        "sfondo": (SFONDO + testa["backdrop_path"]) if testa.get("backdrop_path") else "",
        "episodi": {},
    }
    assoluto = 0
    stagioni = sorted([s for s in (testa.get("seasons") or [])
                       if (s.get("season_number") or 0) > 0],
                      key=lambda s: s["season_number"])
    for st in stagioni:
        d = _chiedi("https://api.themoviedb.org/3/tv/%s/season/%s"
                    "?api_key=%s&language=it-IT"
                    % (tid, st["season_number"], CHIAVE_TMDB))
        for ep in (d.get("episodes") or []):
            assoluto += 1
            scheda["episodi"][str(assoluto)] = {
                "t": (ep.get("name") or "").strip(),
                "p": (ep.get("overview") or "").strip(),
                "i": (IMG + ep["still_path"]) if ep.get("still_path") else "",
                "d": (ep.get("air_date") or "")[:10],
            }
        if xbmc.Monitor().waitForAbort(0.2):
            break

    try:
        with io.open(os.path.join(_cartella_schede_mie(), sid + ".json"),
                     "w", encoding="utf-8") as f:
            f.write(json.dumps(scheda, ensure_ascii=False,
                               separators=(",", ":")))
    except Exception as e:
        xbmc.log("[Le Saghe] scheda di %s non salvata: %s" % (sid, e),
                 xbmc.LOGWARNING)
        return 0
    return len(scheda["episodi"])


def togli(sid):
    """Toglie una serie aggiunta da te. Torna (fatto, messaggio)."""
    mie = _leggi_serie_mie()
    if sid not in mie:
        return False, "Non e' fra quelle che hai aggiunto."
    titolo = mie[sid].get("titolo", sid)
    del mie[sid]
    try:
        with io.open(_file_serie_mie(), "w", encoding="utf-8") as f:
            f.write(json.dumps(mie, ensure_ascii=False, indent=1))
    except Exception as e:
        return False, "Non sono riuscito a toglierla: %s" % e
    try:
        os.remove(os.path.join(_cartella_schede_mie(), sid + ".json"))
    except Exception as _errore:
        xbmc.log("[Le Saghe] togli: errore ignorato: %s" % _errore, xbmc.LOGDEBUG)
    return True, "%s tolta. Sparisce al prossimo avvio." % titolo
