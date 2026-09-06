#!/bin/sh
# Il percorso VERO: si entra nell'elenco degli episodi e si preme invio su
# uno, come farebbe il telecomando. La prova di prima saltava dentro
# l'indirizzo dell'episodio, e quindi non aveva un elenco in cui restare.
rm -f /storage/scatto*.png
kodi-send --action="ActivateWindow(Videos,plugin://plugin.video.saghe/?azione=sfoglia&percorso=naruto&da=1,return)" >/dev/null 2>&1
sleep 7
kodi-send --action="Down" >/dev/null 2>&1
sleep 1
kodi-send --action="Select" >/dev/null 2>&1
sleep 8
kodi-send --action="TakeScreenshot(/storage/scatto3.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto3.png
