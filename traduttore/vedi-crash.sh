#!/bin/sh
echo "=== da quanto e acceso ==="
uptime
echo
echo "=== il kernel ha registrato un panico o un blocco? ==="
dmesg 2>/dev/null | grep -iE "panic|oops|BUG:|watchdog|reboot|under-voltage|undervoltage|throttl|Out of memory|oom-killer" | tail -20
echo "  (vuoto = niente)"
echo
echo "=== temperatura e alimentazione ==="
vcgencmd measure_temp 2>/dev/null
vcgencmd get_throttled 2>/dev/null
echo "  0x0 = nessun problema; bit 0 = sotto tensione ORA; bit 16 = c'e' stato"
echo
echo "=== memoria ==="
free -m | head -2
echo
echo "=== l ultima cosa scritta prima del riavvio (kodi.old.log) ==="
tail -25 /storage/.kodi/temp/kodi.old.log 2>/dev/null
