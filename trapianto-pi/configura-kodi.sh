#!/bin/bash
# ---------------------------------------------------------------------------
# Seconda parte del trapianto: la configurazione DENTRO Kodi.
#
# Va lanciata a Kodi FERMO: Kodi tiene le impostazioni in memoria e riscrive
# guisettings.xml quando esce, quindi modificarlo da acceso non serve a niente.
# (Stessa lezione imparata sul box 8K.)
# ---------------------------------------------------------------------------
set -u
U=/storage/.kodi/userdata
G="$U/guisettings.xml"
AD="$U/addon_data/pvr.iptvsimple"
LISTA=/storage/liste/ITA_RUS.m3u
GUIDA="https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz"
UTENTE="kodi"
PASSWORD="ag1kp0yx7w"   # la stessa del box, cosi' gli strumenti gia' scritti funzionano

dire() { echo ""; echo "== $* =="; }
ok()   { echo "   ok  $*"; }
male() { echo "   !!  $*"; }

dire "Fermo Kodi"
systemctl stop kodi 2>/dev/null
for i in $(seq 1 15); do pgrep -x kodi.bin >/dev/null || break; sleep 1; done
pgrep -x kodi.bin >/dev/null && male "Kodi non si e' fermato" || ok "fermo"

dire "Webserver di Kodi (serve per comandarlo da remoto)"
if [ ! -f "$G" ]; then
    male "guisettings.xml non esiste ancora: lo creo con il minimo indispensabile"
    printf '%s\n' '<settings version="2">' '</settings>' > "$G"
fi
imposta() {   # imposta <id> <valore>
    local id="$1" val="$2"
    if grep -q "id=\"$id\"" "$G"; then
        sed -i "s#<setting id=\"$id\"[^>]*>[^<]*</setting>#<setting id=\"$id\">$val</setting>#" "$G"
    else
        sed -i "s#</settings>#    <setting id=\"$id\">$val</setting>\n</settings>#" "$G"
    fi
}
imposta services.webserver true
imposta services.webserverport 8080
imposta services.webserverusername "$UTENTE"
imposta services.webserverpassword "$PASSWORD"
imposta services.webserverauthentication true
imposta services.esallinterfaces true
imposta services.zeroconf true
ok "webserver acceso su 8080 (utente $UTENTE)"

dire "IPTV Simple: lista canali e guida TV"
mkdir -p "$AD"
# Kodi 20 usa un file di istanza per ogni lista. Ne creo UNA sola, pulita:
# sul box ce n'erano tre sovrapposte e i canali comparivano doppi.
cat > "$AD/instance-settings-1.xml" <<XML
<settings version="2">
    <setting id="kodi_addon_instance_name">Italia e Russia</setting>
    <setting id="kodi_addon_instance_enabled">true</setting>
    <setting id="m3uPathType">0</setting>
    <setting id="m3uPath">$LISTA</setting>
    <setting id="m3uCache">false</setting>
    <setting id="startNum">1</setting>
    <setting id="m3uRefreshMode">2</setting>
    <setting id="m3uRefreshHour">4</setting>
    <setting id="epgPathType">1</setting>
    <setting id="epgUrl">$GUIDA</setting>
    <setting id="epgCache">false</setting>
    <setting id="epgTimeShift">0</setting>
    <setting id="logoPathType">1</setting>
    <setting id="logoFromEpg">1</setting>
    <setting id="useFFmpegReconnect">true</setting>
    <setting id="useInputstreamAdaptiveforHls">true</setting>
</settings>
XML
ok "una sola lista: $LISTA"
ok "guida TV che si riscarica ogni notte alle 4"

dire "Riavvio Kodi"
systemctl start kodi && ok "avviato" || male "non parte"

echo ""
echo "Adesso Kodi va lasciato lavorare un paio di minuti: deve accorgersi dei"
echo "78 add-on nuovi, scaricare la guida (1,7 MB) e leggere 771 canali."
