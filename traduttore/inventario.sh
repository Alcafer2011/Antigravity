#!/bin/sh
echo "=== COSA E' DENTRO S4ME ADESSO ==="
ls -l /storage/.kodi/addons/plugin.video.s4me/channels/lesaghe.* \
      /storage/.kodi/addons/plugin.video.s4me/channels/abbonamenti.* 2>/dev/null | awk '{print "  ", $9, $5"b"}'
echo
echo "=== COSA E' RIMASTO SOLO NEL NOSTRO ADD-ON ==="
for f in vetrina.py taratura.py motore.py ricerca.py progresso.py sincro.py audio.py russo.py abbonamenti.py fonti.py schede.py ponte_s4me.py custode.py; do
  [ -f "/storage/.kodi/addons/plugin.video.saghe/resources/lib/$f" ] && echo "   $f"
done
echo
echo "=== la nostra icona: e' dichiarata nel canale? ==="
grep -o '"thumbnail": "[^"]*"' /storage/.kodi/addons/plugin.video.s4me/channels/lesaghe.json
grep -o '"thumbnail": "[^"]*"' /storage/.kodi/addons/plugin.video.s4me/channels/abbonamenti.json
