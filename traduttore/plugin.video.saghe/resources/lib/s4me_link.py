# -*- coding: utf-8 -*-
"""GLI INDIRIZZI VERSO s4me, scritti come li scrive s4me.

PERCHE' (registro del Raspberry, 11/09/2026)
    s4me legge la prima parte dell'indirizzo come un Item codificato: JSON in
    base64, quello che produce `Item.tourl()`. Noi gli passavamo
    `?channel=lesaghe&action=findvideos&...` in chiaro. Funzionava lo stesso,
    perche' s4me ripiega sui parametri, ma a OGNI episodio scriveva nel
    registro "**NOT** able to load the JSON" con un Traceback intero: rumore
    che copriva i guasti veri e che la scatola nera contava come errore.
    E un nome d'azione sbagliato non lo notava nessuno: `action=Search` (con
    la S maiuscola) non esiste, e la ricerca semplicemente non partiva.

COME
    La TESTA (canale e azione) codificata come fa s4me; i DATI in coda, in
    chiaro, `&chiave=valore`. s4me li legge uno per uno (`launcher.makeItem`
    fa `item.chiave = unquote(valore)`), e noi - nelle prove, nel registratore,
    nell'atlante - li vediamo senza dover decodificare niente.
    Provato sul Kodi del PC l'11/09/2026: risposta in 0,5 s, registro pulito.

    Ogni valore passa da quote(safe=""): una & o un = dentro un titolo
    ("Terra amara & co") non puo' spezzare l'indirizzo.
    Nessuna importazione di Kodi: lo usano anche gli strumenti sul PC.
"""

import base64
import json
from urllib.parse import quote, unquote

BASE = "plugin://plugin.video.s4me/?"


def indirizzo(testa, **dati):
    """`testa` = {"channel": ..., "action": ...}; `dati` in coda, in chiaro."""
    corpo = json.dumps(testa, separators=(",", ":"), sort_keys=True).encode("utf-8")
    capo = quote(base64.b64encode(corpo).decode("ascii"), safe="")
    coda = "".join("&%s=%s" % (k, quote(str(v), safe=""))
                   for k, v in dati.items() if v is not None and str(v) != "")
    return BASE + capo + coda


def leggi(testo):
    """Da un indirizzo di s4me ai suoi campi: la testa decodificata piu' la coda.

    Legge anche gli indirizzi vecchi, tutti in chiaro."""
    if not testo or "?" not in testo:
        return {}
    pezzi = testo.split("?", 1)[1].split("&")
    campi = {}
    try:
        campi.update(json.loads(base64.b64decode(unquote(pezzi[0])).decode("utf-8")))
    except (ValueError, TypeError):
        if "=" in pezzi[0]:
            k, v = pezzi[0].split("=", 1)
            campi[k] = unquote(v)
    for p in pezzi[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            campi[k] = unquote(v)
    return campi
