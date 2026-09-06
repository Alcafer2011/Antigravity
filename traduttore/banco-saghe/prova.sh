#!/bin/sh
# Tutte le prove dell'add-on "Le Saghe", sul PC, senza TV e senza box.
#   sh prova.sh
cd "$(dirname "$0")"
uscita=0
for f in prova_menu.py prova_servizio.py; do
  echo "=== $f ==="
  python "$f" || uscita=1
  echo
done
exit $uscita
