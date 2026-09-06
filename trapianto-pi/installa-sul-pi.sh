#!/bin/bash
# ---------------------------------------------------------------------------
# TRAPIANTO: rende il Raspberry (LibreELEC) uguale al box 8K della camera.
#
# Gira SUL RASPBERRY, via SSH. Si porta dietro tutto quello che serve e non
# chiede niente a nessuno.
#
#   scp -r trapianto-pi root@<indirizzo>:/storage/
#   ssh root@<indirizzo> "bash /storage/trapianto-pi/installa-sul-pi.sh"
#
# COSA FA E COSA NON FA
#   Copia i 78 add-on in PYTHON presi dal box: quelli girano ovunque.
#   I binari del box (inputstream, pvr.iptvsimple, vfs...) NON si copiano:
#   sono compilati per Android a 32 bit. Al loro posto lo script installa le
#   versioni per QUESTO processore, gia' scaricate in binari-armv8/.
# ---------------------------------------------------------------------------
set -u

QUI="$(cd "$(dirname "$0")" && pwd)"
KODI="/storage/.kodi"
ADDONS="$KODI/addons"
UDATA="$KODI/userdata"
LISTE="/storage/liste"
MARCA="$(date +%Y%m%d-%H%M%S)"
BACKUP="/storage/backup-prima-del-trapianto-$MARCA"

dire() { echo ""; echo "== $* =="; }
ok()   { echo "   ok  $*"; }
male() { echo "   !!  $*"; }

# --- controlli preliminari: meglio fermarsi che fare mezzo lavoro ----------
dire "Controlli"
[ -d "$KODI" ] || { male "Non trovo $KODI. Kodi e' mai stato avviato su questo Raspberry?"; exit 1; }
for f in addons.tgz userdata.tgz; do
    [ -f "$QUI/$f" ] || { male "Manca $QUI/$f"; exit 1; }
done
LIBERI_MB=$(df -m /storage | awk 'NR==2{print $4}')
ok "spazio libero: ${LIBERI_MB} MB"
[ "${LIBERI_MB:-0}" -lt 300 ] && { male "Servono almeno 300 MB liberi."; exit 1; }
ok "archivi presenti"

# --- Kodi va fermato, altrimenti riscrive tutto quando esce ---------------
dire "Fermo Kodi"
systemctl stop kodi 2>/dev/null && ok "fermato" || male "non l'ho fermato (forse non gira: va bene lo stesso)"
sleep 3

# --- backup di quello che c'e' adesso ------------------------------------
dire "Backup di quello che c'e' ora"
mkdir -p "$BACKUP"
[ -d "$ADDONS" ] && cp -a "$ADDONS" "$BACKUP/addons" && ok "addons salvati"
[ -d "$UDATA" ]  && cp -a "$UDATA"  "$BACKUP/userdata" && ok "userdata salvato"
echo "Se qualcosa va storto: systemctl stop kodi; rm -rf $ADDONS $UDATA; cp -a $BACKUP/addons $ADDONS; cp -a $BACKUP/userdata $UDATA; systemctl start kodi" > "$BACKUP/COME-TORNARE-INDIETRO.txt"
ok "istruzioni per tornare indietro in $BACKUP"

# --- gli add-on in Python -------------------------------------------------
dire "Trapianto degli add-on"
mkdir -p "$ADDONS"
if tar -xzf "$QUI/addons.tgz" -C "$ADDONS"; then
    ok "$(tar -tzf "$QUI/addons.tgz" | grep -c '^[^/]*/$') add-on estratti"
else
    male "estrazione fallita"; exit 1
fi

# le versioni aggiornate, adattate al Raspberry (sensori e percorsi diversi)
if [ -d "$QUI/sovrascrivi" ]; then
    for a in "$QUI"/sovrascrivi/*/; do
        n="$(basename "$a")"
        rm -rf "${ADDONS:?}/$n"
        cp -a "$a" "$ADDONS/$n" && ok "aggiornato $n (versione adattata al Raspberry)"
    done
fi

# i __pycache__ vengono da un'altra macchina: vanno buttati o Python si confonde
find "$ADDONS" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null
ok "cache di Python ripulita"

# --- impostazioni e dati degli add-on ------------------------------------
dire "Impostazioni degli add-on"
mkdir -p "$UDATA"
TMP="$(mktemp -d)"
tar -xzf "$QUI/userdata.tgz" -C "$TMP"
# addon_data: le impostazioni di s4me, Filmix, i sottotitoli... si portano
cp -a "$TMP/addon_data" "$UDATA/" 2>/dev/null && ok "addon_data copiato"
# questi si portano tali e quali
# NB: advancedsettings.xml NON e' in questa lista — piu' sotto viene
# riscritto su misura per la memoria del Raspberry.
for f in sources.xml favourites.xml mediasources.xml; do
    [ -f "$TMP/$f" ] && cp -a "$TMP/$f" "$UDATA/$f" && ok "$f"
done
# guisettings.xml NO: viene da Android e contiene scelte di quella macchina
# (uscita audio, risoluzione, percorsi). Lo lascio a disposizione da leggere.
[ -f "$TMP/guisettings.xml" ] && cp -a "$TMP/guisettings.xml" "$QUI/guisettings-del-box.xml" \
    && ok "guisettings del box messo da parte (NON applicato: e' roba di Android)"
rm -rf "$TMP"

# --- le liste dei canali --------------------------------------------------
dire "Liste TV"
mkdir -p "$LISTE"
for m in ITA_RUS.m3u preferiti.m3u; do
    [ -f "$QUI/$m" ] && cp -f "$QUI/$m" "$LISTE/$m" && ok "$m -> $LISTE/$m"
done


# --- gli add-on BINARI, quelli che non si potevano copiare ----------------
dire "Add-on binari (compilati per QUESTO processore)"
# Presi da https://addons.libreelec.tv/11.0.0/ARMv8/arm — l'indirizzo NON e'
# indovinato: e' quello scritto dentro l'immagine stessa
# (/usr/share/kodi/addons/repository.libreelec.tv/addon.xml). ARMv7 sarebbe
# stato sbagliato. Verificati: ELF 32 bit, macchina 0x28 = ARM.
if [ -d "$QUI/binari-armv8" ]; then
    for z in "$QUI"/binari-armv8/*.zip; do
        [ -f "$z" ] || continue
        n="$(basename "$z")"
        if unzip -o -q "$z" -d "$ADDONS" 2>/dev/null; then
            ok "installato $n"
        else
            male "non sono riuscito a scompattare $n"
        fi
    done
else
    male "cartella binari-armv8 assente: gli add-on binari vanno installati a mano"
fi

# --- impostazioni di riproduzione, tarate sul Raspberry -------------------
dire "Impostazioni di riproduzione"
# Il box in camera aveva 100 MB di buffer perche' e' un apparecchio modesto.
# Il Pi 4 ha piu' memoria e una rete vera: si puo' bufferizzare di piu', il che
# sulla linea 4G di casa (che ha alti e bassi) conta piu' della potenza.
RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
ok "memoria del Raspberry: ${RAM_MB} MB"
if   [ "${RAM_MB:-0}" -ge 3500 ]; then BUF=350
elif [ "${RAM_MB:-0}" -ge 1800 ]; then BUF=200
else                                   BUF=100
fi
cat > "$UDATA/advancedsettings.xml" <<XML
<advancedsettings>
  <cache>
    <!-- buffermode 1 = bufferizza ANCHE la diretta: di fabbrica non lo fa,
         ed e' quello che salva i canali IPTV quando la linea singhiozza -->
    <buffermode>1</buffermode>
    <memorysize>$((BUF * 1024 * 1024))</memorysize>
    <readfactor>20</readfactor>
  </cache>
  <network>
    <!-- i canali morti mollano in 10 secondi invece di ~30: sullo zapping
         di 771 canali la differenza e' enorme -->
    <curlclienttimeout>10</curlclienttimeout>
    <curllowspeedtime>10</curllowspeedtime>
  </network>
</advancedsettings>
XML
ok "buffer impostato a ${BUF} MB (il box in camera ne aveva 100)"

# --- e adesso? -----------------------------------------------------------
dire "Riavvio Kodi"
systemctl start kodi 2>/dev/null && ok "Kodi riavviato" || male "avvialo a mano: systemctl start kodi"

cat <<FINE

============================================================
FATTO. Cosa e' stato fatto e cosa manca ancora:

 FATTO   78 add-on in Python trapiantati dal box
 FATTO   impostazioni degli add-on (s4me, Filmix, sottotitoli...)
 FATTO   liste canali in $LISTE
 FATTO   backup completo in $BACKUP

 FATTO   add-on binari per ARMv8/arm (IPTV Simple, inputstream, vfs)
 FATTO   buffer di riproduzione alzato secondo la memoria del Raspberry

 MANCA   configurare IPTV Simple: lista $LISTE/ITA_RUS.m3u e guida TV
         https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz

 MANCA   accendere il webserver di Kodi per poterlo comandare da remoto.
============================================================
FINE
