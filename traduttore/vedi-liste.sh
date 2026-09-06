#!/bin/sh
for f in /storage/liste/ITA_RUS.m3u /storage/liste/preferiti.m3u; do
  echo "=== $f"
  echo "canali: $(grep -c '^#EXTINF' "$f")"
  echo "gruppi:"
  grep -o 'group-title="[^"]*"' "$f" | sort | uniq -c | sort -rn | head -8
done
