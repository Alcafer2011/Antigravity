#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== animeworld: intestazione, mainlist e search ==="
sed -n '1,40p' "$S/channels/animeworld.py"
echo "  ---- search ----"
sed -n '101,155p' "$S/channels/animeworld.py"
echo
echo "=== come la ricerca globale chiama i canali (il modello da copiare) ==="
sed -n '340,380p' "$S/specials/globalsearch.py"
