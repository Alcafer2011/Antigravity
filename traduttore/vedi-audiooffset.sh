#!/bin/sh
echo "=== add-on di scostamento audio presenti ==="
for d in /storage/.kodi/addons/*audiooffset* /storage/.kodi/addons/*AudioOffset* \
         /storage/.kodi/addons/service.audio* /usr/share/kodi/addons/*audiooffset*; do
  [ -d "$d" ] || continue
  echo "--- $d"
  head -3 "$d/addon.xml" 2>/dev/null | tail -2
done
echo
echo "=== tutti i servizi installati (per non perderne uno) ==="
for d in /storage/.kodi/addons/*/; do
  if grep -q "xbmc.service" "$d/addon.xml" 2>/dev/null; then
    n=$(basename "$d")
    echo "  $n"
  fi
done
