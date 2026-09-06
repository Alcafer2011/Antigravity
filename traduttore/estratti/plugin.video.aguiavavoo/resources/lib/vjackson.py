# -*- coding: utf-8 -*-

import sys
import os
from urllib.parse import quote_plus 
import xbmc
import xbmcplugin
from xbmcgui import ListItem
import xbmcaddon

try:
    import utils
except ImportError:
    try:
        from . import utils
    except ImportError:
        from resources.lib import utils

try:
    from infotagger.listitem import ListItemInfoTag
    TAGGER_AVAILABLE = True
except ImportError:
    TAGGER_AVAILABLE = False


ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')


def _set_listitem_info(listitem, info_labels):
    if TAGGER_AVAILABLE:
        info_tag = ListItemInfoTag(listitem, 'video')
        info_tag.set_info(info_labels)
    else:
        listitem.setInfo("Video", info_labels)


def _index(params):
    _show_countries(params)


def _show_countries(params):
    """
    Display the list of available countries/regions.
    """
    utils.set_content("files")

    try:
        import vjlive
    except ImportError:
        from . import vjlive

    LIVE_GROUP_ALIASES = (

        (u'Portugal', u'Portugal', 'resources/lib/flags/country/pt.png', None),

        (u'Germany', u'Deutschland', 'resources/lib/flags/country/de.png', None),
        (u'Germany/Sky', u'SKY Deutschland', 'resources/lib/flags/country/de.png', None),
        (u'DE2', u'Deutschland#2', 'resources/lib/flags/country/de.png', None),
        (u'Netherlands', u'Niederlande', 'resources/lib/flags/country/nl.png', None),
        (u'Italy', u'Italien', 'resources/lib/flags/country/it.png', None),
        (u'France', u'Frankreich', 'resources/lib/flags/country/fr.png', None),
        (u'United Kingdom', u'England', 'resources/lib/flags/country/gb.png', None),
        (u'Spain', u'Spanien', 'resources/lib/flags/country/es.png', None),
        (u'Balkans', u'Balkan', 'resources/lib/flags/country/yu.png', None),
        (u'Switzerland', u'Schweiz', 'resources/lib/flags/country/ch.png', None),
        (u'Austria', u'Austria', 'resources/lib/flags/country/at.png', None),
        (u'Poland', u'Polen', 'resources/lib/flags/country/pl.png', None),
        (u'Ukraine', u'Ukraine', 'resources/lib/flags/country/ua.png', None),
        (u'Belgium', u'Belgien', 'resources/lib/flags/country/be.png', None),
        (u'Finland', u'Finland', 'resources/lib/flags/country/fi.png', None),
        (u'Sweden', u'Schweden', 'resources/lib/flags/country/se.png', None),
        (u'Denmark', u'Danemark', 'resources/lib/flags/country/dk.png', None),
        (u'Norway', u'Norwegen', 'resources/lib/flags/country/no.png', None),
        (u'Scandinavia', u'Skandinavien', 'resources/lib/flags/country/scd.jpg', None),
        (u'Czech Republic', u'Tschechien', 'resources/lib/flags/country/cz.png', None),
        (u'Serbia', u'Serbien', 'resources/lib/flags/country/rs.png', None),
        (u'Slovenia', u'Slowenien', 'resources/lib/flags/country/si.png', None),
        (u'Bulgaria', u'Bulgarien', 'resources/lib/flags/country/bg.png', None),
        (u'Romania', u'Rumanien', 'resources/lib/flags/country/ro.png', None),
        (u'Greece', u'Griechenland', 'resources/lib/flags/country/gr.png', None),
        (u'Macedonia', u'Makedonien', 'resources/lib/flags/country/mk.png', None),
        (u'Estonia', u'Estland', 'resources/lib/flags/country/ee.png', None),
        (u'Hungary', u'Ungarn', 'resources/lib/flags/country/hu.png', None),
        (u'Lithuania', u'Litauen', 'resources/lib/flags/country/lt.png', None),
        (u'Lithunia', u'Litauen', 'resources/lib/flags/country/li.png', None),
        (u'Malta', u'Malta', 'resources/lib/flags/country/mt.png', None),
        (u'Albania', u'Albanien', 'resources/lib/flags/country/al.png', None),
        (u'Russia', u'Russland', 'resources/lib/flags/country/ru.png', None),
        (u'Israel', u'Israel', 'resources/lib/flags/country/il.png', None),
        (u'USA', u'USA', 'resources/lib/flags/country/us.png', None),
        (u'Canada', u'Kanada', 'resources/lib/flags/country/ca.png', None),
        (u'Brazil', u'Brasilien', 'resources/lib/flags/country/br.png', None),
        (u'Columbia', u'Kolumbien', 'resources/lib/flags/country/co.png', None),
        (u'Latin', u'Lateinamerika', 'resources/lib/flags/country/latin.jpg', None),
        (u'Armenia', u'Armenien', 'resources/lib/flags/country/am.png', None),
        (u'Armenian', u'Armenien#2', 'resources/lib/flags/country/am.png', None),
        (u'Arabia', u'Arabisch', 'resources/lib/flags/country/ae.png', None),
        (u'Azerbaijan', u'Azerbaijan', 'resources/lib/flags/country/az.png', None),
        (u'Iran', u'Iran', 'resources/lib/flags/country/ir.png', None),
        (u'Afganisthan', u'Afghanistan', 'resources/lib/flags/country/af.png', None),
        (u'Afghanistan', u'Afghanistan#2', 'resources/lib/flags/country/af.png', None),
        (u'Kurdish', u'Kurdistan', 'resources/lib/flags/country/kur.png', None),
        (u'India', u'Indien', 'resources/lib/flags/country/in.png', None),
        (u'Pakistan', u'Pakistan', 'resources/lib/flags/country/pk.png', None),
        (u'Africa', u'Afrika', 'resources/lib/flags/country/afr.png', None),
        (u'Afrika', u'Afrika#2', 'resources/lib/flags/country/afr.png', None),
        (u'Seychelles', u'Seychellen', 'resources/lib/flags/country/sc.png', None),
        (u'Suriname', u'Suriname', 'resources/lib/flags/country/sr.png', None),
        (u'China', u'China', 'resources/lib/flags/country/cn.png', None),
        (u'Korea', u'Korea', 'resources/lib/flags/country/kr.png', None),
        (u'Japan', u'Japan', 'resources/lib/flags/country/jp.png', None),
        (u'Thailand', u'Thailand', 'resources/lib/flags/country/th.png', None),
        (u'Malaysia', u'Malaysia', 'resources/lib/flags/country/my.png', None),
        (u'Nauru', u'Nauru', 'resources/lib/flags/country/nr.png', None),
        (u'Philippines', u'Philippinen', 'resources/lib/flags/country/ph.png', None),
        (u'Turkey', u'Turkei', 'resources/lib/flags/country/tr.png', None),
        (u'Singapore', u'Singapur', 'resources/lib/flags/country/sg.png', None),
        (u'Viet Nam', u'Vietnam', 'resources/lib/flags/country/vn.png', None),
        (u'SKAI DIGITAL', u'SKAI DIGITAL', 'resources/lib/flags/country/skai.png', None),
        (u'SPORTS', u'SPORTS', 'resources/lib/flags/country/wsp.jpg', None),
        (u'SPORTS 2', u'SPORTS 2', 'resources/lib/flags/country/wsp.jpg', None),
        (u'Indonesia', u'Indonesia', 'resources/lib/flags/country/Indonesia.png', None),
        (u'XXX', u'XXX', 'resources/lib/flags/country/skai.png', None),
    )

    countries = vjlive.get_available_countries()
    country_set = set(countries)

    # --- 2026-09-02: voce VISIBILE per svuotare la cache -------------------
    # La cache dell'add-on conserva anche i FALLIMENTI: se l'elenco dei paesi
    # non si scarica resta salvato ["Germany"] e si continua a vedere solo
    # quello anche dopo che il guasto e' passato. Da qui si ripulisce in un
    # clic, senza entrare nelle impostazioni.
    _ico = os.path.join(ADDON_PATH, "icon.png")
    _li = ListItem(u"[COLOR orange]🧹  Svuota la cache / Aggiorna elenco[/COLOR]")
    _li.setArt({"icon": _ico, "thumb": _ico, "fanart": _ico})
    utils.add({"action": "clearcache"}, _li, True)

    for alias, name, icon, _ in LIVE_GROUP_ALIASES:
        if alias in country_set:

            icon_path = os.path.join(ADDON_PATH, icon)

            listitem = ListItem(name)

            listitem.setArt({
                "icon": icon_path,
                "thumb": icon_path,
                "fanart": icon_path
            })

            params = {"action": "channelsbycategory", "group": alias}

            utils.add(params, listitem, True)

    utils.end(cacheToDisc=False)


def _livecategories(params):
    _show_countries(params)


def _channelsbycategory(params):
    group = params.get("group", "Portugal")
    utils.set_content("files")
    try:
        import vjlive
    except ImportError:
        from . import vjlive
    vjlive.channels_by_group(group)


def _refresh(params):
    try:
        import vjlive
    except ImportError:
        from . import vjlive
    vjlive.refresh_channels()
    
    xbmc.executebuiltin("Container.Refresh")

def _favchannels(params):
    try:
        import vjlive
    except ImportError:
        from . import vjlive
    vjlive.favchannels()


def _addTvFavorit(params):
    name = params.get("name", "")
    group = params.get("group", "")
    if name and group:
        try:
            import vjlive
        except ImportError:
            from . import vjlive
        vjlive.change_favorit(name, group=group)

def _delTvFavorit(params):
    name = params.get("name", "")
    if name:
        try:
            import vjlive
        except ImportError:
            from . import vjlive
        vjlive.change_favorit(name, delete=True)

def _delallTvFavorit(params):
    utils.clear_all_favorites()
    utils.notify("All TV Favorites removed")
    xbmc.executebuiltin("Container.Refresh")

def _renameTvFavorit(params):
    name = params.get("name", "")
    if name:
        try:
            import vjlive
        except ImportError:
            from . import vjlive
        vjlive.rename_favorit_dialog(name)

def _moveTvFavoritUp(params):
    name = params.get("name", "")
    if name:
        try:
            import vjlive
        except ImportError:
            from . import vjlive
        vjlive.move_favorit_logic(name, "up")

def _moveTvFavoritDown(params):
    name = params.get("name", "")
    if name:
        try:
            import vjlive
        except ImportError:
            from . import vjlive
        vjlive.move_favorit_logic(name, "down")

def addDir(name, params, isFolder=True, context=None):
    listitem = ListItem(name)
    if context is None:
        context = []
    listitem.addContextMenuItems(context)
    info_labels = {"title": name, "plot": " "}
    _set_listitem_info(listitem, info_labels)
    utils.add(params, listitem, isFolder)

def addDir2(name, action, context=None, isFolder=True, **params):
    params["action"] = action
    addDir(name, params, isFolder, context or [])
