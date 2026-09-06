#!/bin/sh
# Ordine OBBLIGATORIO: prima la password, poi accendere il webserver.
# Al contrario Kodi non riesce ad aprire la porta e si RISPEGNE da solo
# (mettendo services.webserver a false), che e' quello che era successo.
G=/storage/.kodi/userdata/guisettings.xml
P=ag1kp0yx7w
systemctl stop kodi
i=0; while pgrep -x kodi.bin >/dev/null && [ $i -lt 15 ]; do sleep 1; i=$((i+1)); done
sed -e "s#<setting id=\"services.webserverpassword\"[^>]*/>#<setting id=\"services.webserverpassword\">$P</setting>#" \
    -e "s#<setting id=\"services.webserverpassword\"[^>]*>[^<]*</setting>#<setting id=\"services.webserverpassword\">$P</setting>#" \
    -e "s#<setting id=\"services.webserver\"[^>]*/>#<setting id=\"services.webserver\">true</setting>#" \
    -e "s#<setting id=\"services.webserver\"[^>]*>[^<]*</setting>#<setting id=\"services.webserver\">true</setting>#" \
    -e "s#<setting id=\"services.webserverport\"[^>]*>[^<]*</setting>#<setting id=\"services.webserverport\">8080</setting>#" \
    -e "s#<setting id=\"services.webserverusername\"[^>]*>[^<]*</setting>#<setting id=\"services.webserverusername\">kodi</setting>#" \
    "$G" > /storage/.g.tmp && mv /storage/.g.tmp "$G"
echo "--- come e' adesso ---"
grep "services.webserver" "$G"
systemctl start kodi
echo "Kodi riavviato"
