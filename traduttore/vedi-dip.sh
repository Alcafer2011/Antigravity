#!/bin/sh
for a in script.module.addon.signals script.module.inputstreamhelper \
         script.module.pycryptodome script.module.requests script.module.myconnpy \
         script.module.six script.module.urllib3 script.module.certifi \
         script.module.idna script.module.chardet script.module.dateutil; do
  if [ -d "/storage/.kodi/addons/$a" ]; then
    v=$(grep -o 'version="[^"]*"' "/storage/.kodi/addons/$a/addon.xml" 2>/dev/null | head -1)
    echo "HA(utente)  $a  $v"
  elif [ -d "/usr/share/kodi/addons/$a" ]; then
    echo "HA(sistema) $a"
  else
    echo "MANCA       $a"
  fi
done
