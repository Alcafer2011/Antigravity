# -*- coding: utf-8 -*-
"""Completa resources/tmdb.json cercando su TMDb le serie che non ce l'hanno.

Serve alla sentinella: per chiedere "sono usciti episodi nuovi?" bisogna
sapere QUALE scheda guardare. Cercare per nome ogni volta sbaglierebbe
serie (fra i risultati di "One Piece" esce di tutto), quindi si cerca una
volta sola e si salva l'identificativo.

CONTROLLO: si accetta solo un risultato il cui numero di episodi somigli a
quello che abbiamo noi (entro il 20%) oppure il cui anno di inizio combaci.
Un identificativo sbagliato e' peggio di uno mancante.
"""
import importlib.util as u
import io, json, time, urllib.parse, urllib.request

K = "a1ab8b8669da03637a4b98fa39c39228"
UA = {"User-Agent": "Mozilla/5.0"}
MAPPA = "plugin.video.saghe/resources/tmdb.json"


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=25) as f:
                return json.loads(f.read().decode())
        except Exception:
            time.sleep(2)
    return {}


s = u.spec_from_file_location("cat", "plugin.video.saghe/resources/lib/catalogo.py")
c = u.module_from_spec(s); s.loader.exec_module(c)
mappa = json.load(io.open(MAPPA, encoding="utf-8"))

nuovi, dubbi = 0, []
for sid, serie in c.SERIE.items():
    if sid in mappa:
        continue
    titolo = serie["titolo"]
    anno = (serie.get("anni") or "")[:4]
    d = get("https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s"
            % (K, urllib.parse.quote_plus(titolo)))
    scelto = None
    for r in d.get("results", [])[:6]:
        det = get("https://api.themoviedb.org/3/tv/%d?api_key=%s" % (r["id"], K))
        ep = det.get("number_of_episodes") or 0
        a = (det.get("first_air_date") or "")[:4]
        nostri = serie.get("episodi") or 0
        vicino = nostri and abs(ep - nostri) <= max(3, nostri * 0.2)
        stesso_anno = anno and a == anno
        if vicino or stesso_anno:
            scelto = (r["id"], ep, a, vicino, stesso_anno)
            break
        time.sleep(0.1)
    if scelto:
        mappa[sid] = scelto[0]
        nuovi += 1
        print("  %-20s id=%-7d %s ep, %s  (%s)" % (
            sid, scelto[0], scelto[1], scelto[2],
            "episodi simili" if scelto[3] else "stesso anno"))
    else:
        dubbi.append("%s (%s)" % (sid, titolo))
    time.sleep(0.2)

io.open(MAPPA, "w", encoding="utf-8").write(json.dumps(mappa, indent=1, sort_keys=True))
print("\naggiunti %d, totale %d" % (nuovi, len(mappa)))
print("NON identificate con sicurezza (%d): %s" % (len(dubbi), ", ".join(dubbi)))
