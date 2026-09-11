# -*- coding: utf-8 -*-
"""SALVARE UN FILE DI DATI SENZA ROVINARLO.

Il box 8K si riavvia da solo quando scalda (69-73 gradi a riposo). Se succede
mentre si scrive progresso.json con open(..., "w"), il file resta TRONCATO:
al riavvio il JSON non si legge e il punto di ripresa di tutte le saghe e'
perso. Trovato dall'atlante l'11/09/2026 in 8 punti.

Qui si scrive in un file provvisorio accanto e poi lo si sostituisce in un
colpo solo (os.replace): o c'e' il file vecchio intero, o quello nuovo intero.
"""

import io
import json
import os
import xbmc


def json_atomico(percorso, dati, **opzioni):
    """Come json.dump(dati, open(percorso, "w"), **opzioni), ma a prova di spegnimento."""
    provvisorio = percorso + ".tmp"
    with io.open(provvisorio, "w", encoding="utf-8") as f:
        f.write(json.dumps(dati, **opzioni))
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError as _errore:
            xbmc.log("[Le Saghe] json_atomico: errore ignorato: %s" % _errore, xbmc.LOGDEBUG)
    os.replace(provvisorio, percorso)
