#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== s4me prevede canali aggiunti dall utente? ==="
grep -nE "^def |custom|community|user_channel|userdata|special://" "$S/specials/community.py" 2>/dev/null | head -25
echo
echo "=== dove li mette ==="
grep -nE "get_data_path|addon_data|makedirs|join\(" "$S/specials/community.py" 2>/dev/null | head -12
echo
echo "=== e la cartella dati di s4me, quella che sopravvive agli aggiornamenti ==="
ls /storage/.kodi/userdata/addon_data/plugin.video.s4me/ 2>/dev/null
