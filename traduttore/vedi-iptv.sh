#!/bin/sh
for f in /storage/.kodi/userdata/addon_data/pvr.iptvsimple/instance-settings-1.xml \
         /storage/.kodi/userdata/addon_data/pvr.iptvsimple/instance-settings-2.xml \
         /storage/.kodi/userdata/addon_data/pvr.iptvsimple/instance-settings-3.xml; do
  echo "--- $f"
  grep -E 'm3uPath|epgPath|instance_enabled|instance_name' "$f"
done
echo "--- liste ---"
ls -l /storage/liste/ /storage/trapianto-pi/ITA_RUS.m3u /storage/trapianto-pi/preferiti.m3u
