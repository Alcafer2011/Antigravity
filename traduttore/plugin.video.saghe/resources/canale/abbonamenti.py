# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# I MIEI ABBONAMENTI - canale per s4me
#
# COSA FA
#     Partecipa alla ricerca di s4me come se fosse un sito, ma non cerca in
#     rete: offre di aprire la stessa ricerca dentro gli abbonamenti che
#     possiedi - Netflix, Prime Video, Mediaset Infinity, RaiPlay.
#
# PERCHE' SERVE
#     s4me e' fortissimo sui siti, ma quei siti non hanno tutto. Capita di
#     cercare qualcosa e non trovarlo, mentre sta tranquillamente su Netflix
#     o su Prime. Con questo canale la ricerca di s4me risponde comunque:
#     "in rete non c'e', ma ce l'hai su Prime".
#
#     Vale per QUALSIASI cosa si cerchi in s4me, non solo per il nostro
#     catalogo: film, serie, documentari.
#
# COSA NON PUO' FARE, e va detto
#     Netflix e Prime non si lasciano comandare da fuori: si puo' aprire la
#     loro ricerca col titolo gia' scritto, ma l'episodio va scelto a mano.
#     E' un limite loro, non nostro.
#
# NON MOSTRA MAI QUELLO CHE NON HAI
#     Una voce compare solo se l'add-on corrispondente e' davvero installato
#     su questo apparecchio. Meglio nessuna riga che una riga che non apre
#     niente.
# ---------------------------------------------------------------------------

from core import support
from core.item import Item
from platformcode import logger

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

import xbmcvfs


# (nome mostrato, add-on che serve, come si chiede la ricerca)
SERVIZI = [
    ("Netflix", "plugin.video.netflix",
     "plugin://plugin.video.netflix/directory/search/search/%s/"),
    ("Prime Video", "plugin.video.amazon-test",
     "plugin://plugin.video.amazon-test/?mode=search&searchstring=%s"),
]


def _installato(addon):
    try:
        return bool(xbmcvfs.exists("special://home/addons/%s/addon.xml" % addon))
    except Exception:
        return False


def _voci(testo):
    fuori = []
    for nome, addon, modello in SERVIZI:
        if not _installato(addon):
            continue
        fuori.append(Item(
            channel="abbonamenti",
            action="",
            folder=True,
            url=modello % quote_plus(testo),
            title=support.typo("Cerca '%s' su %s" % (testo, nome), "bold"),
            fulltitle=testo,
            contentTitle=testo,
            plot="Apre %s con la ricerca gia' scritta.\n\n"
                 "Nota: Netflix e Prime non si lasciano comandare da fuori, "
                 "quindi l'episodio va scelto a mano una volta dentro."
                 % nome,
        ))
    return fuori


def mainlist(item):
    """Da menu: si chiede cosa cercare e si offrono gli abbonamenti."""
    from platformcode import platformtools
    testo = platformtools.dialog_input("", "Cosa cerchi nei tuoi abbonamenti?")
    if not testo:
        return []
    return _voci(testo)


def search(item, text):
    """Chiamata dalla ricerca globale di s4me, per ogni ricerca."""
    logger.info("abbonamenti: %s" % text)
    try:
        return _voci(text)
    except Exception as e:
        logger.error("abbonamenti: %s" % e)
        return []
