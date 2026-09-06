#!/bin/sh
D=/storage/.kodi/userdata/addon_data/pvr.iptvsimple
echo "=== come sono impostati gli aggiornamenti nelle liste TV ==="
for f in "$D"/instance-settings-1.xml "$D"/instance-settings-2.xml "$D"/instance-settings-3.xml; do
  [ -f "$f" ] || continue
  echo "--- $(basename $f)"
  grep -E "Refresh|refresh|epgTimeShift|instance_enabled|instance_name|epgPathType|epgUrl|cacheM3U|cacheEPG" "$f" | sed 's/^/    /'
done
echo
echo "=== impostazioni comuni ==="
grep -E "Refresh|refresh|cache" "$D/settings.xml" 2>/dev/null | sed 's/^/    /'
