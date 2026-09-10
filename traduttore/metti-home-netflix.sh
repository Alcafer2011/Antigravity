#!/bin/sh
# Mette la home e la vista in stile Netflix dentro skin.saghe.
#
# COSA TOCCA, e cosa no
#   Di skin.saghe tocca TRE file: Home.xml, Includes.xml e MyVideoNav.xml
#   (agli ultimi due aggiunge solo delle righe). Ne aggiunge quattro nuovi:
#   Includes_Videoteca.xml, View_56_Videoteca.xml, bianco.png, sfumatura.png.
#   Estuary NON viene toccato: resta la rete di sicurezza.
#
# COME SI TORNA INDIETRO
#   sh metti-home-netflix.sh indietro
#   Rimette Home.xml e MyVideoNav.xml dalle copie .prima-netflix.
#   E se non bastasse, dalle impostazioni di Kodi si sceglie Estuary.
#
# ATTENZIONE AI FINE-RIGA: se questo file arriva da Windows ha i CRLF e su
# LibreELEC "set -e" diventa "illegal option". Passarlo con: tr -d '\r'
set -e

D=/storage/.kodi/addons/skin.saghe
S=/storage/videoteca-skin

if [ "$1" = "indietro" ]; then
    for f in Home.xml MyVideoNav.xml; do
        if [ -f "$D/xml/$f.prima-netflix" ]; then
            mv "$D/xml/$f.prima-netflix" "$D/xml/$f"
            echo "$f rimesso com'era"
        fi
    done
    exit 0
fi

[ -d "$D" ] || { echo "skin.saghe non c'e'"; exit 1; }
[ -f "$S/Home.xml" ] || { echo "manca $S/Home.xml"; exit 1; }

# Copie di sicurezza, una volta sola: se si rilancia lo script non si
# sovrascrive l'originale con quella gia' modificata.
for f in Home.xml MyVideoNav.xml; do
    [ -f "$D/xml/$f.prima-netflix" ] || cp "$D/xml/$f" "$D/xml/$f.prima-netflix"
done

cp "$S/Home.xml"               "$D/xml/Home.xml"
cp "$S/Includes_Videoteca.xml" "$D/xml/Includes_Videoteca.xml"
cp "$S/View_56_Videoteca.xml"  "$D/xml/View_56_Videoteca.xml"
cp "$S/View_57_VideotecaEpisodi.xml" "$D/xml/View_57_VideotecaEpisodi.xml"
cp "$S/bianco.png"             "$D/media/bianco.png"
cp "$S/sfumatura.png"          "$D/media/sfumatura.png"

# Kodi carica gli altri file di include solo se Includes.xml li nomina.
for f in Includes_Videoteca View_56_Videoteca View_57_VideotecaEpisodi; do
    if ! grep -q "$f.xml" "$D/xml/Includes.xml"; then
        sed -i "s|</includes>|\t<include file=\"$f.xml\" />\n</includes>|" "$D/xml/Includes.xml"
    fi
done

# La vista nuova va dichiarata in MyVideoNav.xml in DUE punti:
#   - nell'elenco <views>, altrimenti il tasto di cambio vista non la propone
#   - fra gli <include>, altrimenti non viene disegnata
if ! grep -q "<views>56,57," "$D/xml/MyVideoNav.xml"; then
    sed -i "s|<views>56,|<views>56,57,|" "$D/xml/MyVideoNav.xml"
fi
# Una alla volta e con la sua guardia: se si controllasse solo la 56, su un
# file gia' modificato la 57 non verrebbe mai aggiunta.
if ! grep -q "View_56_Videoteca" "$D/xml/MyVideoNav.xml"; then
    sed -i "s|<include>View_50_List</include>|<include>View_56_Videoteca</include>\n\t\t\t<include>View_50_List</include>|" "$D/xml/MyVideoNav.xml"
fi
if ! grep -q "View_57_VideotecaEpisodi" "$D/xml/MyVideoNav.xml"; then
    sed -i "s|<include>View_50_List</include>|<include>View_57_VideotecaEpisodi</include>\n\t\t\t<include>View_50_List</include>|" "$D/xml/MyVideoNav.xml"
fi

echo "fatto:"
echo "  include:  $(grep -c 'Videoteca.xml' "$D/xml/Includes.xml")"
echo "  viste:    $(grep -o '<views>[^<]*' "$D/xml/MyVideoNav.xml")"
echo "  vista 56: $(grep -c 'View_56_Videoteca' "$D/xml/MyVideoNav.xml")"
