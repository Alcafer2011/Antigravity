#!/bin/sh
rm -f /storage/scatto-icona.png
kodi-send --action="ActivateWindow(Addonbrowser,addons://user/xbmc.addon.video,return)" >/dev/null 2>&1
sleep 9
kodi-send --action="TakeScreenshot(/storage/scatto-icona.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto-icona.png
