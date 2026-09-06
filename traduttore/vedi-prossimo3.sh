#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== come s4me trova il prossimo episodio ==="
sed -n '/^def next_ep/,/^def /p' "$S/platformcode/xbmc_videolibrary.py" | head -45
