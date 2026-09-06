#!/bin/sh
echo "=== NETFLIX: come si costruisce una ricerca ==="
grep -rn "search" /storage/.kodi/addons/plugin.video.netflix/resources/lib/navigation/directory.py 2>/dev/null | head -5
grep -rn "def search\|'search'\|search_query\|build_url" /storage/.kodi/addons/plugin.video.netflix/resources/lib/utils/api_paths.py 2>/dev/null | head -5
grep -rn "SEARCH" /storage/.kodi/addons/plugin.video.netflix/resources/lib/common/pathops.py 2>/dev/null | head -3
echo "--- rotte dichiarate ---"
grep -rn "g.MODE_DIRECTORY\|MODE_SEARCH\|'search'" /storage/.kodi/addons/plugin.video.netflix/addon.py 2>/dev/null | head -10
echo
echo "=== AMAZON: modalita' di ricerca ==="
grep -rn "mode=Search\|searchString\|def Search" /storage/.kodi/addons/plugin.video.amazon-test/resources/lib/*.py 2>/dev/null | head -8
