#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== la seconda chiave e dove salva il permesso ==="
grep -nE "client_secret =|set_setting\(.token|set_setting\(.refresh" "$S/core/trakt_tools.py" | head -8
echo
echo "--- la funzione che scambia il codice col permesso ---"
sed -n '/^def token_trakt/,/^def /p' "$S/core/trakt_tools.py" | head -30
