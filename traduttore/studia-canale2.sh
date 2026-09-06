#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== un canale di serie, per intero (guardaserieicu.py) ==="
cat "$S/channels/guardaserieicu.py"
echo
echo "=== la sua scheda json ==="
cat "$S/channels/guardaserieicu.json" 2>/dev/null | head -30
