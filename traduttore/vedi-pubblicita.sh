#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
grep -rlniE "adblock|blockads|skip_?ads|advertis|pubblicit" "$S/core" "$S/platformcode" "$S/servers" 2>/dev/null | head -10
echo "--- righe che lo dicono ---"
grep -rniE "adblock|skip_?ads|advertis|pubblicit" "$S/core" "$S/platformcode" 2>/dev/null | head -8
