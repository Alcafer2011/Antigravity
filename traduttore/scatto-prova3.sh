#!/bin/sh
rm -f /storage/scatto4.png
kodi-send --action="ActivateWindow(Videos,plugin://plugin.video.saghe/?azione=sfoglia&percorso=naruto&da=1,return)" >/dev/null 2>&1
sleep 7
kodi-send --action="Down" >/dev/null 2>&1
sleep 1
kodi-send --action="Select" >/dev/null 2>&1
sleep 9
kodi-send --action="TakeScreenshot(/storage/scatto4.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto4.png
