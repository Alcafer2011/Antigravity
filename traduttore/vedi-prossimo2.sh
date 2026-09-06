#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== chi usa next_ep, e cosa gli serve per funzionare ==="
grep -rn "next_ep" "$S/platformcode"/*.py "$S/core"/*.py 2>/dev/null | grep -v "next_ep_type\|next_ep_seconds" | head -10
echo
echo "=== il file che gestisce il prossimo episodio ==="
ls "$S/platformcode" | head -20
