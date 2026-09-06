#!/bin/sh
rm -f /storage/scatto-vetrina*.png
kodi-send --action="ActivateWindow(Videos,plugin://plugin.video.saghe/?azione=vetrina,return)" >/dev/null 2>&1
sleep 12
kodi-send --action="TakeScreenshot(/storage/scatto-vetrina1.png,sync)" >/dev/null 2>&1
sleep 3
kodi-send --action="Right" >/dev/null 2>&1
sleep 1
kodi-send --action="Right" >/dev/null 2>&1
sleep 2
kodi-send --action="TakeScreenshot(/storage/scatto-vetrina2.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto-vetrina*.png
