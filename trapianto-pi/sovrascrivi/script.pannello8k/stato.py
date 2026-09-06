# -*- coding: utf-8 -*-
"""Legge come sta l'apparecchio. Tutto da file di sistema leggibili senza root."""
import os
import glob

ZONE = "/sys/class/thermal"

# nomi tecnici -> nomi comprensibili
NOMI = {
    # box 8K (Allwinner)
    "cpu_thermal_zone": "Processore",
    "gpu_thermal_zone": "Grafica",
    "ddr_thermal_zone": "Memoria",
    "ve_thermal_zone": "Motore video",
    # Raspberry Pi: un solo sensore, e si chiama in un altro modo
    "cpu-thermal": "Processore",
    "cpu_thermal": "Processore",
    "rp1_adc": "Scheda",
}


def _prima_esistente(*percorsi):
    """Il primo percorso che esiste davvero. Il box Android usa /sdcard,
    LibreELEC sul Raspberry usa /storage: cosi' l'add-on gira su entrambi
    senza doverne tenere due versioni."""
    for p in percorsi:
        if os.path.exists(p):
            return p
    return percorsi[-1]


def cartella_dati():
    return _prima_esistente("/storage", "/sdcard", "/")


def _leggi(percorso, default=""):
    try:
        with open(percorso, "r") as f:
            return f.read().strip()
    except Exception:
        return default


def temperature():
    """[(nome, gradi)] ordinate dalla piu' calda."""
    fuori = []
    for z in sorted(glob.glob(os.path.join(ZONE, "thermal_zone*"))):
        grezzo = _leggi(os.path.join(z, "temp"))
        if not grezzo:
            continue
        try:
            v = int(grezzo)
        except ValueError:
            continue
        # i sensori riportano millesimi di grado, ma non sempre
        gradi = v / 1000.0 if v > 1000 else float(v)
        tipo = _leggi(os.path.join(z, "type"), os.path.basename(z))
        fuori.append((NOMI.get(tipo, tipo), round(gradi, 1)))
    fuori.sort(key=lambda x: x[1], reverse=True)
    return fuori


def piu_calda():
    t = temperature()
    return t[0] if t else (None, 0.0)


def memoria():
    """(usata_mb, totale_mb, percentuale_usata)"""
    tot = disp = 0
    try:
        with open("/proc/meminfo") as f:
            for r in f:
                if r.startswith("MemTotal:"):
                    tot = int(r.split()[1])
                elif r.startswith("MemAvailable:"):
                    disp = int(r.split()[1])
    except Exception:
        return (0, 0, 0)
    if not tot:
        return (0, 0, 0)
    usata = tot - disp
    return (usata // 1024, tot // 1024, int(usata * 100 / tot))


def carico():
    p = _leggi("/proc/loadavg").split()
    return p[0] if p else "?"


def acceso_da():
    grezzo = _leggi("/proc/uptime").split()
    if not grezzo:
        return "?"
    s = int(float(grezzo[0]))
    g, s = divmod(s, 86400)
    o, s = divmod(s, 3600)
    m = s // 60
    if g:
        return "%d giorni, %d ore" % (g, o)
    if o:
        return "%d ore e %d minuti" % (o, m)
    return "%d minuti" % m


def spazio(percorso="/sdcard"):
    """(liberi_gb, totali_gb, percentuale_usata)"""
    try:
        s = os.statvfs(percorso)
    except Exception:
        return (0, 0, 0)
    tot = s.f_blocks * s.f_frsize
    lib = s.f_bavail * s.f_frsize
    if not tot:
        return (0, 0, 0)
    return (round(lib / 1073741824.0, 1), round(tot / 1073741824.0, 1),
            int((tot - lib) * 100 / tot))


def giudizio(gradi):
    """Come sta messa la temperatura, in parole."""
    if gradi >= 85:
        return "MOLTO CALDO — rischio riavvii"
    if gradi >= 75:
        return "caldo, tieni d'occhio"
    if gradi >= 65:
        return "tiepido"
    return "fresco"
