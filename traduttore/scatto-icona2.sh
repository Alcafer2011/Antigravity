#!/bin/sh
rm -f /storage/scatto-icona2.png
for i in 1 2 3 4; do kodi-send --action="Down" >/dev/null 2>&1; sleep 1; done
sleep 4
kodi-send --action="TakeScreenshot(/storage/scatto-icona2.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto-icona2.png
