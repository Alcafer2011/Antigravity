# -*- coding: utf-8 -*-
"""
Serve le liste TV alla rete di casa, per le TV che non hanno Kodi.

Nasce come prova sul PC, ma e' scritto per essere spostato su un Raspberry
senza cambiare una riga: e' Python puro, senza dipendenze.

    python servi.py            (porta 8088)
    python servi.py 8080

Poi sulla TV (SS IPTV o simili) si mette l'indirizzo che stampa all'avvio.
"""
import http.server
import os
import socket
import socketserver
import sys

CARTELLA = os.path.dirname(os.path.abspath(__file__))
PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 8088


def indirizzo_in_rete():
    """L'indirizzo che vedono gli ALTRI apparecchi: non 127.0.0.1."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 80))   # non manda niente, serve solo a scegliere la scheda
        return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


class Gestore(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=CARTELLA, **k)

    def end_headers(self):
        # Le TV sono schizzinose: senza questi due la lista a volte non parte.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato, *args):
        # Si vede CHI chiede cosa: e' l'unico modo per capire se la TV arriva davvero.
        print("  %s -> %s" % (self.client_address[0], formato % args))


if __name__ == "__main__":
    ip = indirizzo_in_rete()
    print("Liste servite dalla cartella:\n  %s\n" % CARTELLA)
    print("Indirizzi da mettere nella TV:")
    for f in sorted(os.listdir(CARTELLA)):
        if f.endswith((".m3u", ".m3u8", ".xml", ".gz")):
            print("  http://%s:%d/%s" % (ip, PORTA, f))
    print("\nGuida TV (arriva da internet, non da qui):")
    print("  https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz")
    print("\nCtrl+C per fermare. Sotto compaiono le richieste che arrivano:\n")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORTA), Gestore) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nfermato.")
