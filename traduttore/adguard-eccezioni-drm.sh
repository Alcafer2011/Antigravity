#!/bin/sh
# Aggiunge le eccezioni per Netflix e Prime Video al filtro DNS di casa.
#
# Non e' che oggi siano bloccati: e' che una lista di blocco che si aggiorna
# male puo' bloccarli domani, e il sintomo sarebbe "il video non parte",
# indistinguibile da un guasto dell'add-on. Le altre 21 eccezioni esistono
# per lo stesso motivo.
set -e
Y=/storage/AdGuardHome/AdGuardHome.yaml
cp "$Y" "$Y.bak-prima-drm"

python3 - "$Y" <<'PY'
import io, sys
p = sys.argv[1]
righe = io.open(p, encoding="utf-8").read().split("\n")
nuove = [
    "netflix.com", "nflxvideo.net", "nflximg.net", "nflxext.com",
    "nflxso.net", "netflix.net",
    "primevideo.com", "amazon.com", "media-amazon.com",
    "aiv-cdn.net", "aiv-delivery.net", "amazonvideo.com",
]
# si inserisce in fondo al blocco user_rules, prima della chiave successiva
dentro = False
fine = None
for i, r in enumerate(righe):
    if r.startswith("user_rules:"):
        dentro = True
        continue
    if dentro and not r.startswith("  - "):
        fine = i
        break
if fine is None:
    raise SystemExit("blocco user_rules non trovato: non tocco niente")

gia = "\n".join(righe)
da_mettere = ["  - '@@||%s^'" % d for d in nuove if ("||%s^" % d) not in gia]
righe[fine:fine] = da_mettere
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(righe))
print("eccezioni aggiunte: %d" % len(da_mettere))
PY

systemctl restart adguard
sleep 4
systemctl is-active adguard
grep -c "@@||" "$Y"
