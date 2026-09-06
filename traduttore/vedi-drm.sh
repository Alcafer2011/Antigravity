#!/bin/sh
echo "=== inputstream.adaptive ==="
ls -d /usr/share/kodi/addons/inputstream.adaptive /storage/.kodi/addons/inputstream.adaptive 2>/dev/null
grep -o 'version="[^"]*"' /usr/share/kodi/addons/inputstream.adaptive/addon.xml 2>/dev/null | head -1
echo "=== widevine gia' installato? ==="
find /storage -name "libwidevinecdm.so" 2>/dev/null
ls -l /storage/.kodi/cdm/ 2>/dev/null || echo "nessuna cartella cdm"
echo "=== inputstreamhelper ==="
ls -d /storage/.kodi/addons/script.module.inputstreamhelper /usr/share/kodi/addons/script.module.inputstreamhelper 2>/dev/null || echo "assente"
echo "=== architettura ==="
uname -m
echo "userspace: $(readelf -h /usr/bin/kodi.bin 2>/dev/null | grep -i class | awk '{print $2}')"
file /usr/lib/libc.so* 2>/dev/null | head -2
echo "=== versione LibreELEC / Kodi ==="
cat /etc/os-release | grep -E "^VERSION|^NAME"
echo "=== spazio ==="
df -h /storage | tail -1
