#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
echo "=== s4me ha il 'prossimo episodio'? ==="
grep -rniE "nextdialog|next_episode|autoplay|next_ep" "$S/platformcode/platformtools.py" 2>/dev/null | head -8
echo
echo "=== le impostazioni che lo riguardano ==="
grep -nE "id=\"[^\"]*(next|autoplay)[^\"]*\"" "$S/resources/settings.xml" 2>/dev/null | head -10
echo
echo "=== come sono adesso nel tuo s4me ==="
grep -iE "next|autoplay" /storage/.kodi/userdata/addon_data/plugin.video.s4me/settings.xml 2>/dev/null
echo
echo "=== e UpNext, che e' installato a parte? ==="
ls -d /storage/.kodi/addons/service.upnext 2>/dev/null && grep -o 'version="[^"]*"' /storage/.kodi/addons/service.upnext/addon.xml | head -1
cat /storage/.kodi/userdata/addon_data/service.upnext/settings.xml 2>/dev/null | head -20
