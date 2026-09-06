#!/bin/sh
# Dice a inputstreamhelper che il Widevine c'e' gia', cosi' non prova a
# riscaricare 1,2 GB dalla linea 4G di casa a ogni riproduzione.
set -e
D=/storage/.kodi/userdata/addon_data/script.module.inputstreamhelper
mkdir -p "$D"
cat > "$D/settings.xml" <<'XML'
<settings version="2">
    <setting id="last_modified">0</setting>
    <setting id="disabled">false</setting>
</settings>
XML
# la versione installata, dove l'aiutante la cerca
echo '{"last_modified": 0, "version": "4.10.2662.3"}' > /storage/.kodi/cdm/manifest.json 2>/dev/null || true
ls -l /storage/.kodi/cdm/
echo "--- impostazioni di inputstream.adaptive ---"
cat /storage/.kodi/userdata/addon_data/inputstream.adaptive/settings.xml 2>/dev/null || echo "(nessuna: usa i valori predefiniti, cioe' special://home/cdm - giusto)"
