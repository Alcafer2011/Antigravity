#!/bin/sh
# Sceglie skin.saghe scrivendo direttamente in guisettings.xml.
#
# PERCHE' COSI' E NON DALL'API: cambiando pelle da remoto Kodi apre una
# finestra "la tengo?" che scade in pochi secondi e torna indietro se non
# c'e' nessuno davanti alla TV. Provato due volte, tornato indietro due volte.
# A Kodi fermo il file si scrive e basta, e all'avvio la pelle e' quella.
#
# La copia di sicurezza NON e' un vezzo: guisettings.xml contiene TUTTE le
# impostazioni di Kodi. Se si rompe, si perde la configurazione intera.
set -e
G=/storage/.kodi/userdata/guisettings.xml
systemctl stop kodi
sleep 3
cp "$G" "/storage/guisettings-prima-$(date +%Y%m%d-%H%M).xml"
# Attenzione: la riga ha anche default="true" quando non e' mai stata
# cambiata. Il modello deve accettare gli attributi, o non trova niente.
sed -i 's|<setting id="lookandfeel.skin"[^>]*>[^<]*</setting>|<setting id="lookandfeel.skin">skin.saghe</setting>|' "$G"
echo "--- come e' rimasto ---"
grep -o '<setting id="lookandfeel.skin"[^/]*</setting>' "$G"
python3 -c "import xml.etree.ElementTree as E;E.parse('$G');print('il file e ancora valido')"
systemctl start kodi
echo AVVIATO
