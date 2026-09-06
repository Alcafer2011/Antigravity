#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== il blocco delle impostazioni intorno a lingua e qualita' ==="
sed -n '105,120p' "$S/resources/settings.xml"
echo
echo "=== cosa vogliono dire ==="
L="$S/resources/language/resource.language.it_it/strings.po"
for n in 70246 70240 70241 70763 70764 70765 30020 70120 70109 30005 30006 30007 30008; do
  printf "  %s = " "$n"
  grep -A 2 "msgctxt \"#$n\"" "$L" 2>/dev/null | grep -m1 "msgstr" | sed 's/msgstr //' | tr -d '"'
done
