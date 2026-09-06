#!/system/bin/sh
D=/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi/userdata/addon_data/pvr.iptvsimple
am force-stop org.xbmc.kodi
sleep 4
for n in 1 2 3; do
  f="$D/instance-settings-$n.xml"
  [ -f "$f" ] || continue
  cp "$f" "$f.bak-prima-scansione"
  sed -i 's|<setting id="m3uRefreshMode">2</setting>|<setting id="m3uRefreshMode">0</setting>|' "$f"
  printf "  istanza %s: " "$n"
  grep -o '<setting id="m3uRefreshMode">[0-9]*</setting>' "$f"
done
monkey -p org.xbmc.kodi -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
echo RILANCIATO
