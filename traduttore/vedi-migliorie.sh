#!/bin/sh
S=/storage/.kodi/addons/plugin.video.s4me
U=/storage/.kodi/userdata/addon_data/plugin.video.s4me/settings.xml
echo "=== impostazioni di s4me che riguardano LINGUA e QUALITA' ==="
grep -nE 'id="(filter_languages|default_action|quality|preferred|lang|unify|checklinks|videolibrary_kodi|trakt)[^"]*"' "$S/resources/settings.xml" | head -20
echo
echo "=== come sono adesso da te ==="
grep -iE "filter_lang|default_action|quality|checklinks|unify|trakt|videolibrary|autoplay|next_ep|thumbnail_type|adult" "$U" 2>/dev/null | head -25
echo
echo "=== quanti canali attivi hai (piu' sono, piu' e' lenta la ricerca) ==="
ls /storage/.kodi/userdata/addon_data/plugin.video.s4me/settings_channels/*.json 2>/dev/null | wc -l
