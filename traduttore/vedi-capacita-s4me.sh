#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== 1. GRAFICA: s4me ha finestre proprie o pelli? ==="
find "$S" -name "*.xml" -path "*skin*" 2>/dev/null | head -20
ls "$S/resources" 2>/dev/null
echo "--- finestre XML in giro ---"
find "$S" -name "*.xml" 2>/dev/null | grep -viE "addon.xml|settings.xml|strings" | head -15
echo
echo "=== 2. IMPOSTAZIONI per canale ==="
ls "$S/resources/settings"* 2>/dev/null | head
ls /storage/.kodi/userdata/addon_data/plugin.video.s4me/settings_channels/ 2>/dev/null | head -10
echo
echo "=== 3. MEMORIA: cosa tiene s4me ==="
echo "--- la sua base dati ---"
ls -l /storage/.kodi/userdata/addon_data/plugin.video.s4me/db.sqlite 2>/dev/null
echo "--- videoteca e trakt ---"
grep -nE "^def " "$S/core/videolibrarytools.py" 2>/dev/null | head -12
grep -nE "^def " "$S/core/trakt_tools.py" 2>/dev/null | head -12
