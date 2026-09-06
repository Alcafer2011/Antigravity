#!/bin/sh
echo "=== NETFLIX: directory_search ==="
sed -n '1,60p' /storage/.kodi/addons/plugin.video.netflix/resources/lib/navigation/directory_search.py 2>/dev/null | grep -nE "def route_search_nav|pathitems|search_type|SEARCH|url" | head -12
echo "--- come costruisce gli indirizzi ---"
grep -n "def build_url" -A 22 /storage/.kodi/addons/plugin.video.netflix/resources/lib/common/kodi_ops.py 2>/dev/null | head -30
grep -rn "def build_url" /storage/.kodi/addons/plugin.video.netflix/resources/lib/common/*.py | head -3
echo
echo "=== AMAZON: da dove arrivano i parametri ==="
grep -n "searchstring\|'mode'\|args.get('mode')" /storage/.kodi/addons/plugin.video.amazon-test/default.py 2>/dev/null | head -10
ls /storage/.kodi/addons/plugin.video.amazon-test/
