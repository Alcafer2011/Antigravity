#!/bin/sh
echo "=== quante volte Kodi e ripartito, e perche ==="
journalctl -u kodi --no-pager 2>/dev/null | grep -iE "Started|Stopped|Main process exited|Failed|signal|core-dump|scheduled restart" | tail -30
echo
echo "=== ci sono file di crash? ==="
ls -lt /storage/.kodi/temp/*crash* /storage/*crash* 2>/dev/null | head -10 || echo "  nessuno"
echo
echo "=== il registro di ieri finisce bene o di colpo? ==="
tail -3 /storage/.kodi/temp/kodi.old.log 2>/dev/null
