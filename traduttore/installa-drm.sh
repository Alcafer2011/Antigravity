#!/bin/sh
# Installa Netflix e Prime Video sul Raspberry scompattando gli archivi
# direttamente nella cartella degli add-on.
#
# PERCHE' A MANO E NON DAL DEPOSITO: installare dal deposito richiede
# qualcuno davanti alla TV che confermi le finestre. Scompattare fa la
# stessa identica cosa: un add-on di Kodi E' una cartella.
set -e
A=/storage/.kodi/addons
cd /storage/drm-zip
for z in *.zip; do
  echo "--- $z"
  unzip -oq "$z" -d "$A" && echo "    scompattato"
done
echo
echo "=== cosa c'e' adesso ==="
for a in plugin.video.netflix plugin.video.amazon-test script.module.addon.signals \
         script.module.myconnpy script.module.amazoncaptcha script.module.mechanicalsoup \
         script.module.pyautogui; do
  [ -d "$A/$a" ] && echo "  ok    $a" || echo "  MANCA $a"
done
