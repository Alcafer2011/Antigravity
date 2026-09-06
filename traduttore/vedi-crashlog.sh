#!/bin/sh
F=/storage/.kodi/temp/kodi_crashlog_20260906131615.log
echo "=== le ultime righe del registro prima del crollo ==="
sed -n '/Log:/,$p' "$F" 2>/dev/null | tail -30
echo
echo "=== traccia della chiamata (chi ha fatto crollare) ==="
grep -A 30 -iE "Stack trace|backtrace|Thread 1" "$F" 2>/dev/null | head -40
