# -*- coding: utf-8 -*-
"""Scarica da TMDb le schede delle saghe post anni Ottanta.

Non riscrive il costruttore: riusa quello che c'e' gia'
([costruisci-schede.py]), cambiandogli solo l'elenco delle serie. Cosi' le
schede nuove escono identiche alle 63 gia' fatte - stesso formato, stessa
numerazione assoluta che attraversa le stagioni.

L'OFFSET serve quando due nostre serie stanno nella STESSA scheda TMDb:
Bleach e il suo seguito del 2022 sono un'unica voce da 416 episodi, quindi
il seguito parte dal 367 e il suo offset e' 366. Stesso trucco di ken2.
"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("cs", "costruisci-schede.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

cs.TMDB = {
    "yuyu":          {"id": 30669,  "offset": 0},
    "slamdunk":      {"id": 42573,  "offset": 0},
    "evangelion":    {"id": 890,    "offset": 0},
    "kenshin":       {"id": 28136,  "offset": 0},
    "berserk":       {"id": 35935,  "offset": 0},
    "cowboy":        {"id": 30991,  "offset": 0},
    "trigun":        {"id": 26453,  "offset": 0},
    "gto":           {"id": 43017,  "offset": 0},
    "hxh99":         {"id": 45952,  "offset": 0},
    "hxh":           {"id": 46298,  "offset": 0},
    "inuyasha":      {"id": 35610,  "offset": 0},
    "yashahime":     {"id": 103254, "offset": 0},
    "fma03":         {"id": 37863,  "offset": 0},
    "fmab":          {"id": 31911,  "offset": 0},
    "bleach":        {"id": 30984,  "offset": 0},
    "bleach_tybw":   {"id": 30984,  "offset": 366},
    "deathnote":     {"id": 13916,  "offset": 0},
    "codegeass":     {"id": 31724,  "offset": 0},
    "fairytail":     {"id": 46261,  "offset": 0},
    "opm":           {"id": 63926,  "offset": 0},
    "jojo":          {"id": 45790,  "offset": 0},
    "aot":           {"id": 1429,   "offset": 0},
    "mha":           {"id": 65930,  "offset": 0},
    "blackclover":   {"id": 73223,  "offset": 0},
    "demonslayer":   {"id": 85937,  "offset": 0},
    "vinland":       {"id": 88803,  "offset": 0},
    "jjk":           {"id": 95479,  "offset": 0},
    "chainsaw":      {"id": 114410, "offset": 0},
    "shamanking01":  {"id": 40143,  "offset": 0},
    "shamanking21":  {"id": 104699, "offset": 0},
    "souleater":     {"id": 37305,  "offset": 0},
    "steinsgate":    {"id": 42509,  "offset": 0},
    "digimon":       {"id": 31654,  "offset": 0},
}

sys.argv = ["costruisci-schede.py", "a1ab8b8669da03637a4b98fa39c39228"]
sys.exit(cs.main())
