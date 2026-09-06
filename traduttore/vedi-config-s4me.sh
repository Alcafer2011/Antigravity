#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== s4me si aggancia al SUO add-on o a chi lo chiama? ==="
grep -nE "xbmcaddon.Addon\(" "$S/platformcode/config.py" | head -8
echo
echo "=== come si importa: c e un __init__ alla radice? ==="
ls "$S/__init__.py" 2>/dev/null && echo "  si"
head -20 "$S/default.py"
echo
echo "=== la firma di findvideos e di episodios in animeworld ==="
sed -n '155,200p' "$S/channels/animeworld.py"
