# -*- coding: utf-8 -*-
"""
IL QUADERNO COMUNE — gira sul Raspberry, che e' sempre acceso.

Tiene un unico registro di "dove sono arrivato" per tutte le saghe, e lo
condivide fra il Raspberry del salotto e il box della camera. Come Netflix:
cominci di la', finisci di qua.

Perche' sul Raspberry e non sul PC: il PC e' spento quasi sempre, il Raspberry
no. Consuma 3 watt e non ha bisogno di nessuno.

    GET  /progressi   -> tutto il registro
    POST /progressi   -> unisce quello che arriva e restituisce il risultato

La regola di fusione, quando i due apparecchi dicono cose diverse:
  * la POSIZIONE piu' recente vince (conta 'aggiornato', non chi parla per ultimo)
  * gli EPISODI VISTI si sommano: se l'hai visto su uno dei due, l'hai visto
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REGISTRO = "/storage/progressi.json"
PORTA = 8099
_lucchetto = threading.Lock()


def _leggi():
    try:
        with open(REGISTRO) as f:
            return json.load(f)
    except Exception:
        return {"percorsi": {}}


def _scrivi(dati):
    # Si scrive prima accanto e poi si sposta: se manca la corrente a meta',
    # il registro vecchio resta intero invece di diventare mezzo file.
    tmp = REGISTRO + ".tmp"
    with open(tmp, "w") as f:
        json.dump(dati, f, indent=1)
    os.replace(tmp, REGISTRO)


def _unisci(vecchio, nuovo):
    fuori = json.loads(json.dumps(vecchio))
    fuori.setdefault("percorsi", {})
    for pid, s_nuovo in (nuovo.get("percorsi") or {}).items():
        s_vecchio = fuori["percorsi"].get(pid)
        if not s_vecchio:
            fuori["percorsi"][pid] = s_nuovo
            continue
        # i visti si sommano sempre: sono un fatto, non un'opinione
        visti = set(s_vecchio.get("visti") or []) | set(s_nuovo.get("visti") or [])
        # la posizione: vince chi l'ha toccata per ultimo
        if int(s_nuovo.get("aggiornato", 0)) >= int(s_vecchio.get("aggiornato", 0)):
            unito = dict(s_nuovo)
        else:
            unito = dict(s_vecchio)
        unito["visti"] = sorted(visti)
        fuori["percorsi"][pid] = unito
    return fuori


class Gestore(BaseHTTPRequestHandler):
    def _rispondi(self, dati, codice=200):
        corpo = json.dumps(dati).encode("utf-8")
        self.send_response(codice)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path.startswith("/progressi"):
            with _lucchetto:
                self._rispondi(_leggi())
        elif self.path.startswith("/vivo"):
            self._rispondi({"vivo": True})
        else:
            self._rispondi({"errore": "non conosco questo indirizzo"}, 404)

    def do_POST(self):
        if not self.path.startswith("/progressi"):
            return self._rispondi({"errore": "non conosco questo indirizzo"}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            arrivato = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception as e:
            return self._rispondi({"errore": "non capisco quello che mi mandi: %s" % e}, 400)
        with _lucchetto:
            unito = _unisci(_leggi(), arrivato)
            _scrivi(unito)
        self._rispondi(unito)

    def log_message(self, formato, *args):
        pass          # niente rumore nel log di sistema


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORTA), Gestore).serve_forever()
