#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
L="$S/resources/language/resource.language.it_it/strings.po"
[ -f "$L" ] || L="$S/resources/language/resource.language.en_gb/strings.po"
echo "  (file: $L)"
for n in 70562 70748 70832 70833 70732 70834 70754 70755 70756 70757 70749; do
  printf "  %s = " "$n"
  grep -A 2 "msgctxt \"#$n\"" "$L" 2>/dev/null | grep -m1 "msgstr" | sed 's/msgstr //' | tr -d '"'
  grep -A 1 "msgctxt \"#$n\"" "$L" 2>/dev/null | grep -m1 "msgid" | sed 's/msgid /      (en) /' | tr -d '"'
done
