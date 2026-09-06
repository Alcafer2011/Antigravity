#!/system/bin/sh
# Sentinella crash di Kodi. Ogni 60 s controlla se e' comparso un tombstone
# nuovo e, in quel caso, mette al sicuro il kodi.old.log PRIMA che un secondo
# riavvio lo sovrascriva.
#   archivio completo : /sdcard/Download/kodi-crash/<data-ora>/
#   riepilogo per Kodi: addon_data/script.pannello8k/ultimo-crash.txt
# (Kodi NON puo' leggere /sdcard/Download: per questo serve il riepilogo.)
KODI=/sdcard/Android/data/org.xbmc.kodi/files/.kodi
DEST=/sdcard/Download/kodi-crash
RIEP=$KODI/userdata/addon_data/script.pannello8k
STATO=$DEST/.ultimo
mkdir -p "$DEST"
[ -f "$STATO" ] || echo "" > "$STATO"

while true; do
  ULTIMO=$(ls -t /data/tombstones/tombstone_[0-9]* 2>/dev/null | grep -v '\.pb$' | head -1)
  if [ -n "$ULTIMO" ]; then
    FIRMA="$ULTIMO $(stat -c %Y "$ULTIMO" 2>/dev/null)"
    VISTO=$(cat "$STATO" 2>/dev/null)
    if [ "$FIRMA" != "$VISTO" ]; then
      QUANDO=$(date +%Y-%m-%d_%H-%M-%S)
      CART="$DEST/$QUANDO"
      mkdir -p "$CART"
      head -120 "$ULTIMO" > "$CART/tombstone.txt" 2>/dev/null
      [ -f "$KODI/temp/kodi.old.log" ] && tail -1000 "$KODI/temp/kodi.old.log" > "$CART/prima-del-crash.log" 2>/dev/null
      [ -f "$KODI/temp/kodi.log" ]     && head -300 "$KODI/temp/kodi.log"     > "$CART/dopo-il-riavvio.log" 2>/dev/null
      # riepilogo leggibile da Kodi
      mkdir -p "$RIEP"
      DATA=$(grep -m1 Timestamp "$ULTIMO" 2>/dev/null | sed 's/Timestamp: //;s/\..*//')
      UP=$(grep -m1 'Process uptime' "$ULTIMO" 2>/dev/null | sed 's/Process uptime: //')
      TOT=$(ls -1d "$DEST"/[0-9]* 2>/dev/null | wc -l)
      echo "$DATA|$UP|$TOT" > "$RIEP/ultimo-crash.txt"
      chown 10106:10106 "$RIEP/ultimo-crash.txt" 2>/dev/null
      chmod 664 "$RIEP/ultimo-crash.txt" 2>/dev/null
      echo "$FIRMA" > "$STATO"
    fi
  fi
  sleep 60
done
