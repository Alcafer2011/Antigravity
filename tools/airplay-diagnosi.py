# -*- coding: utf-8 -*-
"""
Diagnosi: quali comandi AirPlay accetta DAVVERO questa TV?

Si autentica come farebbe un iPhone (pair-verify con le credenziali salvate) e
poi bussa a una porta per volta, stampando il codice di risposta. Serve a
smettere di tirare a indovinare su quale dialetto di AirPlay parli la Hisense.
"""
import asyncio
import json
import os
import plistlib
import sys

from pyatv.protocols.airplay.auth import pair_verify
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.support.http import http_connect

QUI = os.path.dirname(os.path.abspath(__file__))
INDIRIZZO = "192.168.1.109"
PORTA = 7000
URL = "https://rainews1-live.akamaized.net/hls/live/598326/rainews1/rainews1/playlist.m3u8"


def credenziali():
    with open(os.path.join(QUI, "airplay-credenziali.json")) as f:
        return json.load(f)["airplay"]


async def prova(conn, descrizione, metodo, percorso, corpo=None, tipo=None):
    intestazioni = {"User-Agent": "AirPlay/377.40.00", "X-Apple-ProtocolVersion": "1"}
    if tipo:
        intestazioni["Content-Type"] = tipo
    try:
        if metodo == "GET":
            r = await conn.get(percorso, allow_error=True)
        else:
            r = await conn.post(percorso, headers=intestazioni, body=corpo, allow_error=True)
        corpo_r = (r.body or b"")
        if isinstance(corpo_r, bytes):
            corpo_r = corpo_r[:120]
        print("  %-42s -> %s   %s" % (descrizione, r.code, corpo_r if r.code < 300 else ""))
        return r.code
    except Exception as e:
        print("  %-42s -> ECCEZIONE %s" % (descrizione, type(e).__name__))
        return None


async def main():
    conn = await http_connect(INDIRIZZO, PORTA)
    try:
        print("Mi autentico come farebbe un iPhone...")
        verifier = pair_verify(parse_credentials(credenziali()), conn)
        await verifier.verify_credentials()
        print("Autenticato.\n")

        print("Cosa risponde la TV, comando per comando:")
        await prova(conn, "GET /server-info", "GET", "/server-info")
        await prova(conn, "GET /playback-info", "GET", "/playback-info")

        testo = "Content-Location: %s\nStart-Position: 0\n" % URL
        await prova(conn, "POST /play (testo, stile AirPlay 1)", "POST", "/play",
                    testo, "text/parameters")

        plist = plistlib.dumps({"Content-Location": URL, "Start-Position": 0.0},
                               fmt=plistlib.FMT_BINARY)
        await prova(conn, "POST /play (plist binario, stile 2)", "POST", "/play",
                    plist, "application/x-apple-binary-plist")

        # Alcuni ricevitori di terze parti espongono il video sotto un altro nome
        for alt in ("/video", "/playvideo", "/start"):
            await prova(conn, "POST %s (tentativo alternativo)" % alt, "POST", alt,
                        testo, "text/parameters")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
