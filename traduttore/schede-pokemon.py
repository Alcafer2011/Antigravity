# -*- coding: utf-8 -*-
"""Schede (locandine, titoli, trame) di Pokemon, Doraemon e Yu-Gi-Oh."""
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cs", "costruisci-schede.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)
cs.TMDB = {
    "pokemon":        {"id": 60572, "offset": 0},
    "doraemon2005":   {"id": 65733, "offset": 0},
    "doraemon1979":   {"id": 57911, "offset": 0},
    "yugioh_dm":      {"id": 902,   "offset": 0},
    "yugioh_gx":      {"id": 12536, "offset": 0},
    "yugioh_5ds":     {"id": 20695, "offset": 0},
    "yugioh_zexal":   {"id": 45854, "offset": 0},
    "yugioh_arcv":    {"id": 67460, "offset": 0},
    "yugioh_vrains":  {"id": 71360, "offset": 0},
}
sys.argv = ["costruisci-schede.py", "a1ab8b8669da03637a4b98fa39c39228"]
sys.exit(cs.main())
