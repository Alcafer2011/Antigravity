#!/bin/sh
# Le liste TV del Raspberry puntavano a percorsi del BOX ANDROID
# (/storage/emulated/0/Download/...), che su LibreELEC non esistono. E' un
# residuo del trapianto: i file sono stati copiati, i percorsi dentro la
# configurazione no.
#
# Effetto sullo schermo: la lista "Italia Russia Bielorussia" era accesa ma
# vuota, e il log si riempiva di "server error" a ogni richiesta di canali.
#
# Si scrive a Kodi FERMO: le impostazioni degli add-on vengono riscritte
# all'uscita, e una modifica a Kodi acceso verrebbe cancellata.
set -e
D=/storage/.kodi/userdata/addon_data/pvr.iptvsimple
systemctl stop kodi
sleep 3
for n in 2 3; do
  f="$D/instance-settings-$n.xml"
  cp "$f" "$f.bak-percorsi-android"
  sed -i 's|/storage/emulated/0/Download/preferiti_ITA_RUS_BIE.m3u|/storage/liste/preferiti.m3u|' "$f"
  sed -i 's|/storage/emulated/0/Download/ITA_RUS.m3u|/storage/liste/ITA_RUS.m3u|' "$f"
done
echo "--- com'e' rimasto ---"
for n in 1 2 3; do
  f="$D/instance-settings-$n.xml"
  printf "%s: " "$n"
  grep -o '<setting id="m3uPath">[^<]*</setting>' "$f"
done
echo "--- i file esistono? ---"
for p in /storage/liste/ITA_RUS.m3u /storage/liste/preferiti.m3u; do
  [ -s "$p" ] && echo "ok  $p" || echo "MANCA $p"
done
systemctl start kodi
echo AVVIATO
