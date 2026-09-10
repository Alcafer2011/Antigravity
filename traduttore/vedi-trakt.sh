#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== come s4me si autorizza su Trakt ==="
sed -n '/^def auth_trakt/,/^def /p' "$S/core/trakt_tools.py" | head -50
echo
echo "=== la chiave del programma ==="
grep -rnE "client_id|CLIENT_ID|apikey" "$S/core/trakt_tools.py" | head -6
