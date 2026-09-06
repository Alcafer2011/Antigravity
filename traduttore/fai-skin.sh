#!/bin/sh
# Crea skin.saghe: una copia di Estuary con la nostra tavolozza.
# Estuary NON viene toccato: resta la rete di sicurezza se qualcosa va storto.
set -e
D=/storage/.kodi/addons/skin.saghe
rm -rf "$D"
cp -a /usr/share/kodi/addons/skin.estuary "$D"
rm -f "$D"/resources/screenshot-*.jpg
chmod -R u+w "$D"

# --- carta d'identita' -------------------------------------------------
cat > "$D/addon.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<addon id="skin.saghe" version="1.0.0" name="Le Saghe"
       provider-name="Antigravity">
  <requires>
    <import addon="xbmc.gui" version="5.16.0"/>
  </requires>
  <extension point="xbmc.gui.skin" debugging="false">
    <res width="1920" height="1440" aspect="4:3" default="false" folder="xml" />
    <res width="1920" height="1280" aspect="3:2" default="false" folder="xml" />
    <res width="1920" height="1200" aspect="16:10" default="false" folder="xml" />
    <res width="2040" height="1080" aspect="17:9" default="false" folder="xml" />
    <res width="1920" height="1080" aspect="16:9" default="true" folder="xml" />
    <res width="2560" height="1080" aspect="21:9" default="false" folder="xml" />
    <res width="2338" height="1080" aspect="19.5:9" default="false" folder="xml" />
    <res width="2160" height="1080" aspect="18:9" default="false" folder="xml" />
  </extension>
  <extension point="xbmc.addon.metadata">
    <platform>all</platform>
    <license>CC BY-SA 4.0, GNU GPL v2 - lavoro derivato da Estuary di phil65</license>
    <source>https://github.com/xbmc/skin.estuary/</source>
    <assets>
      <icon>resources/icon.png</icon>
      <fanart>resources/fanart.jpg</fanart>
    </assets>
    <summary lang="it_IT">La pelle di casa: Estuary con i colori delle Saghe</summary>
    <description lang="it_IT">Parte da Estuary, la pelle di Kodi che tutti conoscono, e ne cambia solo i colori: fondo carbone e ambra calda, pensati per una TV vista da lontano e per le locandine degli anime. Tutto il resto funziona esattamente come prima, cosi' non c'e' niente di nuovo da imparare.</description>
    <disclaimer lang="it_IT">Lavoro derivato da Estuary. Se qualcosa non va, in Impostazioni si torna a Estuary che resta installato.</disclaimer>
  </extension>
</addon>
XML

# --- la tavolozza ------------------------------------------------------
# Si scrive dentro defaults.xml e non in un tema a parte: cosi' e' il
# vestito NORMALE della pelle e non c'e' niente da scegliere a mano.
#
# Le scelte, con il perche':
#   ambra invece dell'azzurro  - l'azzurro di Estuary spegne le locandine
#     degli anime, che sono quasi tutte calde. L'ambra le accompagna.
#   fondo carbone e non nero   - il nero pieno su un pannello acceso fa
#     "sbavare" i bordi chiari; un carbone appena sollevato e' piu' riposante.
#   testo bianco caldo         - il bianco puro su fondo scuro abbaglia.
cat > "$D/colors/defaults.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<colors>
	<color name="primary_background">FF1B1410</color>
	<color name="secondary_background">33E0913A</color>
	<color name="dialog_tint">FF221A15</color>
	<color name="background">FF120E0B</color>
	<color name="bg_image">FF8C8C8C</color>
	<color name="bg_overlay">30FFFFFF</color>
	<color name="black">FF000000</color>
	<color name="white">FFF5EFE6</color>
	<color name="grey">FFA79C90</color>
	<color name="blue">FFF0A94B</color>
	<color name="red">FFCE4421</color>
	<color name="button_focus">FFE0913A</color>
	<color name="text_shadow">33000000</color>
	<color name="border_alpha">60FFFFFF</color>
	<color name="disabled">40FFFFFF</color>
	<color name="selected">FFFFC55C</color>
	<color name="invalid">FFFF5A4A</color>
</colors>
XML

# la nostra icona, se c'e'
I=/storage/.kodi/addons/plugin.video.saghe/resources/icon.png
[ -f "$I" ] && cp "$I" "$D/resources/icon.png"

echo "FATTA"
du -sh "$D"
echo "--- controllo XML ---"
for f in "$D/addon.xml" "$D/colors/defaults.xml"; do
  python3 -c "import xml.etree.ElementTree as E,sys;E.parse(sys.argv[1]);print('ok',sys.argv[1])" "$f" 2>/dev/null \
    || echo "ATTENZIONE: non ho potuto controllare $f"
done
