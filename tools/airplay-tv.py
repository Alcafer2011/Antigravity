# -*- coding: utf-8 -*-
"""
Manda un video alla TV Hisense del salotto via AirPlay, senza cavi ne' telecomandi.

L'accoppiamento va fatto UNA VOLTA SOLA: la TV mostra un codice sullo schermo,
tu me lo dai, e da quel momento le credenziali restano salvate qui accanto.

    python airplay-tv.py accoppia          -> avvia, la TV mostra il codice
    python airplay-tv.py codice 1234       -> completa con il codice letto
    python airplay-tv.py manda <indirizzo> -> riproduce un video/flusso sulla TV
    python airplay-tv.py stato             -> cosa sta facendo la TV adesso
    python airplay-tv.py ferma             -> interrompe la riproduzione

Va lanciato con il Python dell'ambiente isolato:
    tools\\airplay-venv\\Scripts\\python.exe tools\\airplay-tv.py ...
"""
import asyncio
import json
import os
import sys

import pyatv
from pyatv.const import Protocol
from pyatv.storage.memory_storage import MemoryStorage
from pyatv.support import rtsp as _rtsp
from pyatv import exceptions as _exc


# ── LA TOPPA CHE FA FUNZIONARE QUESTA TV ────────────────────────────────────
#
# Verificato sul campo il 05/09/2026. La sequenza AirPlay 2 di pyatv e' questa:
#   1) POST /play          <- la Hisense lo ACCETTA: il video parte
#   2) PUT  /setProperty?... <- la Hisense risponde 501 Not Implemented
#   3) POST /rate?value=1  <- serve a far partire davvero (altrimenti in pausa)
# Al punto 2 pyatv solleva un errore e non arriva mai al punto 3, quindi il
# video parte e resta fermo. Qui i 501 vengono ignorati: sono comandi
# facoltativi (proprieta' di riproduzione), non il flusso.
#
# Il protocollo v1 NON e' l'alternativa: la TV pretende l'autenticazione
# AirPlay 2, e col v1 chiude la connessione a meta' del POST /play.

_scambio_originale = _rtsp.RtspSession.exchange


# I comandi FACOLTATIVI che seguono il /play: regolano proprieta' di
# riproduzione. Se la TV non li conosce (501) o non li espone (404), il flusso
# sta gia' andando e non ha senso far fallire tutto. Elencati apposta: un
# errore su /play o sull'autenticazione deve continuare a fallire, forte.
_FACOLTATIVI = ("/setProperty", "/rate", "/scrub", "/getProperty")


async def _scambio_tollerante(self, method, uri=None, *args, **kwargs):
    try:
        return await _scambio_originale(self, method, uri, *args, **kwargs)
    except _exc.HttpError as e:
        testo = str(e)
        facoltativo = uri and any(uri.startswith(x) for x in _FACOLTATIVI)
        if facoltativo and ("501" in testo or "404" in testo or "400" in testo):
            print("  (la TV non conosce %s %s - lo salto)" % (method, uri))
            return None
        raise


_rtsp.RtspSession.exchange = _scambio_tollerante


QUI = os.path.dirname(os.path.abspath(__file__))
CREDENZIALI = os.path.join(QUI, "airplay-credenziali.json")
IN_CORSO = os.path.join(QUI, ".accoppiamento-in-corso.json")
INDIRIZZO = "192.168.1.109"


async def _trova(loop):
    """La TV, cercata per indirizzo. Se non risponde non ha senso proseguire."""
    trovati = await pyatv.scan(loop, hosts=[INDIRIZZO], timeout=8)
    if not trovati:
        trovati = await pyatv.scan(loop, timeout=8)
        trovati = [d for d in trovati if str(d.address) == INDIRIZZO]
    if not trovati:
        raise SystemExit("La TV non risponde su %s. E' accesa? E' in rete?" % INDIRIZZO)
    return trovati[0]


def _leggi_credenziali():
    try:
        with open(CREDENZIALI) as f:
            return json.load(f).get("airplay")
    except Exception:
        return None


async def accoppia(loop):
    """Passo 1: chiede l'accoppiamento. La TV mostra un codice di 4 cifre."""
    conf = await _trova(loop)
    coppia = await pyatv.pair(conf, Protocol.AirPlay, loop)
    await coppia.begin()
    if not coppia.device_provides_pin:
        # Alcune TV non chiedono il codice: in quel caso e' gia' finita qui.
        await coppia.finish()
        _salva(coppia)
        await coppia.close()
        print("Accoppiato senza codice: la TV non lo chiedeva.")
        return
    print("Guarda la TV: sta mostrando un codice di 4 cifre.")
    print("Poi lancia:  python airplay-tv.py codice <le 4 cifre>")
    # Il processo NON puo' restare aperto ad aspettare: si salva lo stato e si
    # riprende dopo. E' il motivo per cui l'accoppiamento e' in due comandi.
    with open(IN_CORSO, "w") as f:
        json.dump({"nota": "accoppiamento avviato"}, f)


def _salva(coppia):
    dati = {}
    if os.path.exists(CREDENZIALI):
        try:
            with open(CREDENZIALI) as f:
                dati = json.load(f)
        except Exception:
            pass
    dati["airplay"] = coppia.service.credentials
    with open(CREDENZIALI, "w") as f:
        json.dump(dati, f, indent=2)
    print("Credenziali salvate in", CREDENZIALI)


async def accoppia_con_codice(loop, pin):
    """Passo 1 e 2 insieme: il codice compare e resta sullo schermo qualche
    minuto, quindi si puo' rifare begin() e chiudere subito con il pin."""
    conf = await _trova(loop)
    coppia = await pyatv.pair(conf, Protocol.AirPlay, loop)
    await coppia.begin()
    coppia.pin(pin)
    await coppia.finish()
    _salva(coppia)
    await coppia.close()
    try:
        os.remove(IN_CORSO)
    except OSError:
        pass
    print("Accoppiamento riuscito.")


async def _collega(loop):
    """
    ATTENZIONE — la Hisense vuole il protocollo AirPlay v1.

    Di suo pyatv sceglie il v2 perche' la TV annuncia le funzioni giuste, ma poi
    il v2 manda dei `PUT /setProperty` che questa TV non implementa e risponde
    501: il video parte e viene subito buttato via. Il v1 fa solo il
    `POST /play` con Content-Location, che invece la TV capisce.
    Verificato sul campo il 05/09/2026.
    """
    conf = await _trova(loop)
    cred = _leggi_credenziali()
    if cred:
        conf.set_credentials(Protocol.AirPlay, cred)
    # Le impostazioni non si passano a connect(): vivono dentro uno "storage"
    # che connect() rilegge e applica sopra la configurazione. Le credenziali
    # vanno messe LI', altrimenti l'apply() le cancella.
    deposito = MemoryStorage()
    impostazioni = await deposito.get_settings(conf)
    if cred:
        impostazioni.protocols.airplay.credentials = cred
    return await pyatv.connect(conf, loop, storage=deposito)


async def manda(loop, url):
    tv = await _collega(loop)
    try:
        print("Mando alla TV:", url)
        await tv.stream.play_url(url)
        print("Inviato.")
    finally:
        tv.close()


async def stato(loop):
    tv = await _collega(loop)
    try:
        print(await tv.metadata.playing())
    finally:
        tv.close()


async def ferma(loop):
    tv = await _collega(loop)
    try:
        await tv.remote_control.stop()
        print("Fermato.")
    finally:
        tv.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if cmd == "accoppia":
            loop.run_until_complete(accoppia(loop))
        elif cmd == "codice":
            loop.run_until_complete(accoppia_con_codice(loop, sys.argv[2]))
        elif cmd == "manda":
            loop.run_until_complete(manda(loop, sys.argv[2]))
        elif cmd == "stato":
            loop.run_until_complete(stato(loop))
        elif cmd == "ferma":
            loop.run_until_complete(ferma(loop))
        else:
            print(__doc__)
            return 2
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
