# -*- coding: utf-8 -*-
"""Mette le serie nuove dentro i percorsi, al punto giusto della cronologia.

Lavora sulle RIGHE dei segmenti, non con espressioni regolari sull'intero
file: i segmenti sono righe semplici e prevedibili, e cosi' si vede subito
se un innesto non ha trovato il suo posto invece di scoprirlo davanti alla
TV.
"""
import io
import os
import sys

CAT = r"C:\Users\infoa\Antigravity\traduttore\plugin.video.saghe\resources\lib\catalogo.py"

# (percorso, serie nuova, quanti episodi, dopo quale serie; None = in testa)
INNESTI = [
    ("gundam",  "gundam_08th",       12, "gundam0079"),
    ("gundam",  "gundam_0080",        6, "gundam_08th"),
    ("gundam",  "gundam_0083",       13, "gundam_0080"),
    ("lupin",   "lupin_fujiko",      13, None),
    ("lupin",   "lupin4",            24, "lupin3"),
    ("lupin",   "lupin5",            24, "lupin4"),
    ("lupin",   "lupin6",            24, "lupin5"),
    ("zodiaco", "ss_soul_of_gold",   13, "ss_hades"),
    ("zodiaco", "ss_omega",          97, "ss_soul_of_gold"),
    ("zodiaco", "ss_lost_canvas",    26, "ss_omega"),
    ("holly",   "holly_road2002",    52, "holly2"),
    ("ken",     "ken_blue_sky",      46, "ken2"),
    ("lamu",    "lamu2022",          46, "lamu"),
    ("mazinga", "grendizer_u",       13, "mazinga_edition_z"),
    ("gonagai", "devilman_crybaby",  10, "jeeg"),
]


def confini(righe, percorso):
    """(prima riga, ultima riga) del blocco segmenti di un percorso."""
    dentro = False
    inizio = fine = None
    for i, r in enumerate(righe):
        if r.strip().startswith('"%s": {' % percorso):
            dentro = True
        elif dentro and r.strip() == '"segmenti": [':
            inizio = i + 1
        elif dentro and inizio is not None and r.strip() == "],":
            fine = i - 1
            return inizio, fine
    return None, None


def main():
    testo = io.open(CAT, encoding="utf-8").read()
    righe = testo.split("\n")
    fatti, mancati = 0, []

    for percorso, serie, quanti, dopo in INNESTI:
        a, b = confini(righe, percorso)
        if a is None:
            mancati.append("%s: percorso non trovato" % percorso)
            continue
        nuova = '            ("%s",%s 1, %3d),' % (
            serie, " " * max(1, 17 - len(serie)), quanti)

        if dopo is None:
            righe.insert(a, nuova)
            fatti += 1
            continue

        posto = None
        for i in range(a, b + 1):
            if '"%s"' % dopo in righe[i]:
                posto = i + 1        # dopo l'ULTIMO pezzo di quella serie
        if posto is None:
            mancati.append("%s: non trovo %s dentro %s" % (serie, dopo, percorso))
            continue
        righe.insert(posto, nuova)
        fatti += 1

    io.open(CAT, "w", encoding="utf-8", newline="\n").write("\n".join(righe))
    import ast
    ast.parse(io.open(CAT, encoding="utf-8").read())

    print("innesti riusciti: %d su %d" % (fatti, len(INNESTI)))
    for m in mancati:
        print("   NON FATTO: %s" % m)
    return 1 if mancati else 0


if __name__ == "__main__":
    sys.exit(main())
