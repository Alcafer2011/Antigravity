#!/bin/sh
rm -f /storage/scatto-v*.png
kodi-send --action="RunScript(plugin.video.saghe)" >/dev/null 2>&1
sleep 10
kodi-send --action="TakeScreenshot(/storage/scatto-v1.png,sync)" >/dev/null 2>&1
sleep 3
kodi-send --action="Right" >/dev/null 2>&1
sleep 1
kodi-send --action="Right" >/dev/null 2>&1
sleep 1
kodi-send --action="Down" >/dev/null 2>&1
sleep 3
kodi-send --action="TakeScreenshot(/storage/scatto-v2.png,sync)" >/dev/null 2>&1
sleep 3
ls -l /storage/scatto-v*.png
