#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== il modello ufficiale di un canale in JSON ==="
head -c 2600 "$S/channels/0example.json.txt" 2>/dev/null
echo
echo "..."
echo
echo "=== esiste gia' un canale community installato? ==="
cat /storage/.kodi/userdata/addon_data/plugin.video.s4me/community_channels.json 2>/dev/null | head -c 600 || echo "  nessuno"
