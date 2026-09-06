# -*- coding: utf-8 -*-
"""
Aguia Vavoo - Kodi 19/20/21 Compatible Entry Point
"""

import sys
import json
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib import utils
from resources.lib import vjlive
from resources.lib import vjackson


def run():

    params = {}

    if len(sys.argv) > 2 and sys.argv[2]:
        params = dict(utils.parse_qsl(sys.argv[2][1:]))

    channel_name = params.get("name")
    action = params.pop("action", None)

    if channel_name and action == "addTvFavorit":
        vjlive.change_favorit(channel_name, group=params.get("group", ""))

    elif channel_name and action == "delTvFavorit":
        vjlive.change_favorit(channel_name, delete=True)

    elif channel_name and action == "renameTvFavorit":
        vjlive.rename_favorit_dialog(channel_name)

    elif channel_name and action == "moveTvFavoritUp":
        vjlive.move_favorit_logic(channel_name, "up")

    elif channel_name and action == "moveTvFavoritDown":
        vjlive.move_favorit_logic(channel_name, "down")

    elif channel_name:
        urls = None
        urls_param = params.get("urls")

        if urls_param:
            try:
                urls = json.loads(urls_param)
            except:
                urls = None

        vjlive.livePlay(channel_name, urls, group=params.get("group"))

    # --- 2026-09-02: svuota la cache (bottone nelle impostazioni) ---------
    # La cache conserva anche i FALLIMENTI: quando l'elenco dei paesi non si
    # scaricava, restava salvato ["Germany"] e l'add-on continuava a mostrare
    # solo quello anche dopo che il guasto era risolto. Da qui si ripulisce.
    elif action == "clearcache":
        import os as _os, shutil as _sh, xbmcvfs as _vfs
        _prof = _vfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
        _n = 0
        _d = _os.path.join(_prof, "cache")
        if _os.path.isdir(_d):
            for _f in _os.listdir(_d):
                try:
                    _p = _os.path.join(_d, _f)
                    if _os.path.isfile(_p):
                        _os.remove(_p)
                    else:
                        _sh.rmtree(_p, True)
                    _n += 1
                except Exception:
                    pass
        xbmcgui.Dialog().notification(
            "Aguia Vavoo",
            "Cache svuotata (%d voci)" % _n,
            xbmcgui.NOTIFICATION_INFO, 3000)
        # Se siamo dentro una finestra (voce di menu) ridisegniamo SUBITO
        # l'elenco aggiornato: cosi' l'effetto si vede, non va solo creduto.
        # Da RunPlugin (bottone nelle impostazioni) l'handle e' -1: si salta.
        try:
            if int(sys.argv[1]) >= 0:
                vjackson._show_countries({})
        except Exception:
            pass

    elif action is None:
        vjackson._index(params)

    elif action == "show_countries":
        vjackson._show_countries(params)

    elif action == "channels":
        vjlive.channels()

    elif action == "channelsbycategory":
        vjlive.channels_by_group(params.get("group", "Portugal"))

    elif action == "settings":
        xbmcaddon.Addon().openSettings()

    elif action == "livecategories":
        vjackson._livecategories(params)

    elif action == "favchannels":
        vjlive.favchannels()

    elif action == "makem3u":
        vjlive.makem3u(params.get("group"))

    elif action == "delallTvFavorit":
        utils.clear_all_favorites()
        utils.notify("All TV Favorites removed")
        xbmc.executebuiltin("Container.Refresh")

    else:
        handler = getattr(vjackson, f"_{action}", None)

        if handler:
            handler(params)
        else:
            utils.log(f"Unknown action: {action}", "main")


if __name__ == "__main__":
    run()
