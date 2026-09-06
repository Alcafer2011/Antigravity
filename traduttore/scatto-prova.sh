#!/bin/sh
# Apre davvero un episodio come farebbe il telecomando, e fotografa lo
# schermo. E' l'unico modo onesto per sapere se compare un errore: dal log
# non si distingue una riga informativa da una finestra rossa in faccia.
rm -f /storage/scatto*.png
kodi-send --action="ActivateWindow(Videos,plugin://plugin.video.saghe/?azione=sfoglia&percorso=naruto&da=1,return)" >/dev/null 2>&1
sleep 6
kodi-send --action="TakeScreenshot(/storage/scatto1.png,sync)" >/dev/null 2>&1
sleep 3
kodi-send --action="ActivateWindow(Videos,plugin://plugin.video.saghe/?azione=apri&percorso=naruto&idx=2,return)" >/dev/null 2>&1
sleep 7
kodi-send --action="TakeScreenshot(/storage/scatto2.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto*.png 2>/dev/null || echo "nessuno scatto prodotto"
