#!/bin/sh
echo "=== c'e' un advancedsettings.xml? ==="
for f in /storage/.kodi/userdata/advancedsettings.xml; do
  if [ -f "$f" ]; then echo "--- $f"; cat "$f"; else echo "  NESSUNO: Kodi usa i valori di fabbrica"; fi
done
echo
echo "=== memoria libera (il buffer sta in RAM) ==="
free -m | head -2
echo
echo "=== velocita' vera della linea, dal Raspberry ==="
for i in 1 2 3; do
  curl -o /dev/null -s -w "  %{speed_download} byte/s\n" --max-time 8 \
    "https://speed.cloudflare.com/__down?bytes=8000000"
done
