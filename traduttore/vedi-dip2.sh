#!/bin/sh
for a in script.module.beautifulsoup4 script.module.pyxbmct script.module.pyautogui; do
  if [ -d "/storage/.kodi/addons/$a" ]; then echo "HA(utente)  $a"
  elif [ -d "/usr/share/kodi/addons/$a" ]; then echo "HA(sistema) $a"
  else echo "MANCA       $a"; fi
done
