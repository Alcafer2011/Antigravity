#!/bin/sh
echo "=== bit dello spazio utente (conta per il Widevine) ==="
file /usr/lib/libcrypto.so.* 2>/dev/null | head -1
readelf -h /usr/lib/kodi/kodi.bin 2>/dev/null | grep -i "Class\|Machine"
echo "=== versioni ==="
grep -o 'id="inputstream.adaptive" version="[^"]*"' /storage/.kodi/addons/inputstream.adaptive/addon.xml
grep -o 'id="script.module.inputstreamhelper" version="[^"]*"' /storage/.kodi/addons/script.module.inputstreamhelper/addon.xml
echo "=== cosa scaricherebbe l'aiutante ==="
grep -rn "CHROMEOS_RECOVERY_URL\|chromeos\|dl.google.com" /storage/.kodi/addons/script.module.inputstreamhelper/lib/inputstreamhelper/config.py 2>/dev/null | head -8
echo "=== immagini ChromeOS previste per arm ==="
grep -n "hana\|kevin\|elm\|ARM" /storage/.kodi/addons/script.module.inputstreamhelper/lib/inputstreamhelper/config.py 2>/dev/null | head -12
