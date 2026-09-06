#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== 1. come il lanciatore chiama un canale ==="
grep -nE "getattr|import_module|__import__|channel\." "$S/platformcode/launcher.py" 2>/dev/null | head -20
echo
echo "=== 2. cosa deve avere un Item ==="
sed -n '132,175p' "$S/core/item.py"
echo
echo "=== 3. il canale piu' piccolo che c'e', da usare come modello ==="
for f in "$S"/channels/*.py; do
  n=$(wc -l < "$f")
  echo "$n $(basename $f)"
done | sort -n | head -8
