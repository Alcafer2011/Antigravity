#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== canali di servizi ufficiali che s4me ha gia' ==="
ls "$S/channels" | grep -iE "mediaset|infinity|netflix|prime|amazon|rai|discovery|la7|now|paramount|disney" 
echo
echo "=== e quali sono attivi ==="
for c in mediasetplay raiplay la7 discoveryplus; do
  f="$S/channels/$c.json"
  [ -f "$f" ] && echo "  $c: $(grep -o '\"active\": [a-z]*' $f | head -1)  categorie: $(grep -o '\"categories\": \[[^]]*\]' $f | head -1)"
done
echo
echo "=== tutti i canali anime disponibili ==="
grep -l '"anime"' "$S/channels"/*.json 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/.json//' | tr '\n' ' '
echo
