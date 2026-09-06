#!/bin/sh
# Kodi NON deve piu' accendere la TV quando parte.
#
# Due impostazioni, e servono tutte e due:
#   activate_source = 0   non chiede piu' alla TV di passare al suo ingresso
#   wake_devices    = ""  non accende piu' nessun apparecchio all'avvio
#
# COSA RESTA ACCESO, e va bene cosi':
#   enabled        = 1        il telecomando della TV continua a comandare Kodi
#   standby_devices = 36037   spegnendo Kodi si spegne anche la TV
#
# Va fatto a Kodi FERMO: il file viene riscritto all'uscita.
set -e
F=/storage/.kodi/userdata/peripheral_data/cec_CEC_Adapter.xml
systemctl stop kodi
sleep 3
cp "$F" "$F.bak-prima-cec"
sed -i 's|<setting id="activate_source" value="1" />|<setting id="activate_source" value="0" />|' "$F"
sed -i 's|<setting id="wake_devices" value="36037" />|<setting id="wake_devices" value="" />|' "$F"
echo "--- come e rimasto ---"
grep -E "activate_source|wake_devices\"|standby_devices\"|enabled" "$F" | sed 's/^/    /'
systemctl start kodi
echo AVVIATO
