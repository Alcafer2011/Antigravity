# -*- coding: utf-8 -*-
"""
LA RICERCA: una sola casella per 2.700 tappe.

IL PROBLEMA
    Il catalogo e' cresciuto oltre la soglia in cui si trova le cose
    scorrendo: 16 saghe, 17 serie turche, oltre duemilasettecento tappe,
    piu' film, capitoli e canali. Senza una ricerca, meta' di questo lavoro
    e' invisibile.

COSA SI CERCA, TUTTO INSIEME
    saghe, serie, capitoli narrativi, titoli di episodio, film, canali russi.
    Una casella sola: chi cerca non deve sapere in quale scaffale guardare.

COME SI CONFRONTANO LE PAROLE
    Non con l'uguaglianza: nessuno scrive "Il Grande Mazinga" col telecomando
    e senza errori. Si toglie tutto cio' che non e' lettera o cifra, si
    abbassano le maiuscole e si tolgono gli accenti; poi si guarda se le
    parole cercate ci sono TUTTE, in qualsiasi ordine. Cosi' "mazinga
    grande" trova "Il Grande Mazinga", e "dbz 100" trova la tappa giusta.

L'ORDINE DEI RISULTATI
    Prima le cose grosse (una saga intera), poi i capitoli, poi i singoli
    episodi. Chi cerca "Jiren" vuole il capitolo dove compare, non i
    quattrocento episodi che lo nominano di sfuggita.
"""

import re
import unicodedata

from . import catalogo, schede

# Oltre questo numero di episodi trovati si smette di cercare: una ricerca
# che restituisce ottocento righe non ha aiutato nessuno, e su un apparecchio
# da salotto costruire quella lista costa secondi veri.
MAX_EPISODI = 60


def _piatto(testo):
    """Il testo ridotto all'osso: minuscolo, senza accenti ne' segni."""
    if not testo:
        return ""
    t = unicodedata.normalize("NFKD", str(testo))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def _contiene_tutte(ago, pagliaio):
    """Tutte le parole cercate compaiono, in qualsiasi ordine."""
    if not ago:
        return False
    return all(p in pagliaio for p in ago.split())


def cerca(testo, limite_episodi=MAX_EPISODI):
    """Trova ovunque. Restituisce un elenco di risultati gia' ordinati.

    Ogni risultato:
        tipo      "saga" | "serie" | "capitolo" | "episodio" | "film" | "canale"
        titolo    da mostrare
        dettaglio riga sotto il titolo
        percorso  id del percorso, se ce n'e' uno
        idx       tappa, se e' un episodio o un capitolo
        serie     id della serie, per la locandina
    """
    ago = _piatto(testo)
    if len(ago) < 2:
        return []

    fuori = []
    visti_percorsi = set()

    # 1. Le saghe e i raggruppamenti: la roba grossa per prima.
    for pid, p in catalogo.PERCORSI.items():
        campo = _piatto("%s %s" % (p["titolo"], p.get("sottotitolo", "")))
        if _contiene_tutte(ago, campo):
            visti_percorsi.add(pid)
            fuori.append({
                "tipo": "saga",
                "titolo": p["titolo"],
                "dettaglio": "%d tappe - %s" % (catalogo.lunghezza(pid),
                                                p.get("sottotitolo", "")),
                "percorso": pid, "idx": 0,
                "serie": p["segmenti"][0][0],
            })

    # 2. Le serie dentro le saghe: "Shippuden" deve portare a Naruto.
    for pid, p in catalogo.PERCORSI.items():
        if pid in visti_percorsi:
            continue
        for sid, a, b in p["segmenti"]:
            s = catalogo.SERIE.get(sid)
            if not s:
                continue
            if _contiene_tutte(ago, _piatto(s["titolo"])):
                visti_percorsi.add(pid)
                fuori.append({
                    "tipo": "serie",
                    "titolo": s["titolo"],
                    "dettaglio": "dentro %s - %s" % (p["titolo"], s.get("anni", "")),
                    "percorso": pid, "idx": 0, "serie": sid,
                })
                break

    # 3. I capitoli narrativi: la risposta a "dove sono gli episodi con Jiren".
    for pid, archi in getattr(catalogo, "ARCHI", {}).items():
        if pid not in catalogo.PERCORSI:
            continue
        for nome, da, a in archi:
            if _contiene_tutte(ago, _piatto(nome)):
                fuori.append({
                    "tipo": "capitolo",
                    "titolo": nome,
                    "dettaglio": "%s - tappe %d-%d" % (catalogo.PERCORSI[pid]["titolo"], da, a),
                    "percorso": pid, "idx": da,
                    "serie": catalogo.PERCORSI[pid]["segmenti"][0][0],
                })

    # 4. I titoli dei singoli episodi. E' la parte cara: si scorre la catena
    #    di ogni saga, quindi si smette appena si e' raccolto abbastanza.
    quanti = 0
    for pid in catalogo.ORDINE_PERCORSI + _percorsi_nei_gruppi():
        if quanti >= limite_episodi:
            break
        for t in catalogo.catena(pid):
            if quanti >= limite_episodi:
                break
            sch = schede.episodio(t["serie"], t["ep"])
            titolo = sch["titolo"]
            if not titolo:
                continue
            if _contiene_tutte(ago, _piatto(titolo)):
                fuori.append({
                    "tipo": "episodio",
                    "titolo": titolo,
                    "dettaglio": "%s - tappa %d" % (catalogo.PERCORSI[pid]["titolo"], t["idx"]),
                    "percorso": pid, "idx": t["idx"], "serie": t["serie"],
                })
                quanti += 1

    # 5. I film.
    for pid in catalogo.PERCORSI:
        for m in schede.film(pid) or []:
            if _contiene_tutte(ago, _piatto(m.get("t", ""))):
                fuori.append({
                    "tipo": "film",
                    "titolo": m["t"],
                    "dettaglio": "film di %s%s" % (
                        catalogo.PERCORSI[pid]["titolo"],
                        (" - %s" % m["a"]) if m.get("a") else ""),
                    "percorso": pid, "idx": 0,
                    "serie": catalogo.PERCORSI[pid]["segmenti"][0][0],
                })

    # 6. I canali per imparare il russo.
    try:
        from . import russo
        for c in russo.CANALI:
            if _contiene_tutte(ago, _piatto(c["nome"])):
                fuori.append({
                    "tipo": "canale", "titolo": c["nome"],
                    "dettaglio": "canale russo - %s" % c["eta"],
                    "percorso": "", "idx": 0, "serie": "",
                })
    except Exception:
        pass

    ordine = {"saga": 0, "serie": 1, "capitolo": 2, "film": 3,
              "canale": 4, "episodio": 5}
    fuori.sort(key=lambda r: (ordine.get(r["tipo"], 9), r["titolo"]))
    return fuori


def _percorsi_nei_gruppi():
    fuori = []
    for gid in getattr(catalogo, "ORDINE_GRUPPI", []):
        fuori.extend(catalogo.GRUPPI[gid]["percorsi"])
    return fuori
