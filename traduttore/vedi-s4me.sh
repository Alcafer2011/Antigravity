#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== com e fatto s4me ==="
ls "$S"
echo
echo "=== quanti canali (fonti) ha ==="
ls "$S/channels"/*.py 2>/dev/null | wc -l
echo "--- alcuni ---"
ls "$S/channels" 2>/dev/null | head -20
echo
echo "=== il nucleo ==="
ls "$S/core" 2>/dev/null | head -25
echo
echo "=== versione e aggiornamenti ==="
grep -o 'version="[^"]*"' "$S/addon.xml" 2>/dev/null | head -2
