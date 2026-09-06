#!/bin/sh
# Toglie la ri-lettura automatica delle liste TV all'avvio.
#
# PERCHE'
#   Le liste stanno in /storage/liste/, sono file LOCALI: non cambiano da
#   sole. Rileggerle ogni giorno (e quindi al primo avvio utile, se
#   l'apparecchio era spento alle 4) costa secondi di attesa a ogni
#   accensione per non guadagnare niente.
#
#   La guida TV invece continua ad aggiornarsi: quella viene da internet e
#   cambia davvero. Si e' solo allargato l'intervallo da 2 ore a 12.
#
# Va fatto a Kodi FERMO: le impostazioni degli add-on vengono riscritte
# all'uscita, e una modifica a Kodi acceso sparirebbe.
set -e
D=/storage/.kodi/userdata/addon_data/pvr.iptvsimple
systemctl stop kodi
sleep 3
for n in 1 2 3; do
  f="$D/instance-settings-$n.xml"
  [ -f "$f" ] || continue
  cp "$f" "$f.bak-prima-scansione"
  sed -i 's|<setting id="m3uRefreshMode">2</setting>|<setting id="m3uRefreshMode">0</setting>|' "$f"
  printf "  istanza %s: " "$n"
  grep -o '<setting id="m3uRefreshMode">[0-9]*</setting>' "$f"
done
systemctl start kodi
echo AVVIATO
