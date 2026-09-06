#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== animeworld: le funzioni che ci servono ==="
grep -nE "^def (search|episodios|findvideos|mainlist|list_all|newest)" "$S/channels/animeworld.py"
echo
echo "=== come si costruisce un Item ==="
grep -nE "^class Item|def __init__" "$S/core/item.py" | head -5
echo
echo "=== come si risolve un video ==="
grep -nE "^def (resolve_video_urls_for_playing|get_servers_itemlist|find_video_items)" "$S/core/servertools.py"
echo
echo "=== la ricerca globale (cerca su TUTTI i canali) ==="
ls "$S/specials" 2>/dev/null
grep -nE "^def " "$S/specials/search.py" 2>/dev/null | head -12
