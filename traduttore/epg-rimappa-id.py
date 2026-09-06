# -*- coding: utf-8 -*-
"""
Riscrive i tvg-id della lista IPTV (formato iptv-org, es. "Rai1.it@SD") con gli
id usati dalla guida TV di epgshare01 (es. "Rai.1.it"), abbinando per NOME.

Cosi' la guida si aggiorna da sola dal box, senza dipendere dal PC.

Uso:
    python epg-rimappa-id.py lista.m3u guida.xml uscita.m3u [--report report.txt]
"""
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

# rumore nei nomi della lista: "(1080p)", "[Geo-blocked]", "[Not 24/7]"
RUMORE = re.compile(r"\((?:\d{3,4}[pi]|[^)]*\d{3,4}[pi][^)]*)\)|\[[^\]]*\]", re.I)
# parole che non aiutano a distinguere un canale
CODA = ("hd", "sd", "fhd", "uhd", "4k", "italia", "italy", "it", "tv", "channel", "canale")


def normalizza(nome: str) -> str:
    s = RUMORE.sub(" ", nome or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("&", " e ").replace("+", " plus ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"\s+", "", s)


def varianti(nome: str):
    """chiave piena e chiave senza le parole-coda inutili"""
    base = normalizza(nome)
    if not base:
        return []
    chiavi = [base]
    ridotto = base
    cambiato = True
    while cambiato:
        cambiato = False
        for c in CODA:
            if ridotto.endswith(c) and len(ridotto) > len(c) + 1:
                ridotto = ridotto[: -len(c)]
                cambiato = True
    if ridotto and ridotto != base:
        chiavi.append(ridotto)
    return chiavi


def leggi_guida(percorso):
    """{chiave-normalizzata: id-guida}; il primo che arriva vince (l'ordine
    della guida mette per primi i canali principali)"""
    indice = {}
    dettaglio = {}
    for _, el in ET.iterparse(percorso, events=("end",)):
        if not el.tag.endswith("channel"):
            el.clear()
            continue
        cid = el.get("id")
        nomi = [d.text for d in el if d.tag.endswith("display-name") and d.text]
        dettaglio[cid] = nomi
        for n in nomi:
            for k in varianti(n):
                indice.setdefault(k, cid)
        # l'id stesso e' spesso il nome puntato: "Sky.Uno.it" -> "skyuno"
        if cid:
            for k in varianti(re.sub(r"\.(it|eu)$", "", cid).replace(".", " ")):
                indice.setdefault(k, cid)
        el.clear()
    return indice, dettaglio


def e_italiano(riga, tvg_id):
    """Si guarda il PAESE nel tvg-id, non il gruppo: la lista dei preferiti usa
    gruppi tematici (General, Movies...) e mescola Italia, Russia e Bielorussia.
    Cosi' i canali russi non rischiano di prendersi la guida di un canale
    italiano che si chiama quasi uguale."""
    if tvg_id:
        m = re.match(r"^(?P<base>[^@]*)(?:@(?P<feed>.*))?$", tvg_id)
        base, feed = m.group("base") or "", m.group("feed") or ""
        paese = base.rsplit(".", 1)[-1].lower() if "." in base else ""
        if paese in ("it", "sm", "va"):
            return True
        return feed.lower() in ("it", "italy", "ita")
    g = re.search(r'group-title="([^"]*)"', riga)
    return bool(g) and g.group(1).lower() == "italy"


def nome_da_extinf(riga):
    """Il nome sta dopo l'ULTIMO attributo fra virgolette: alcune righe hanno un
    http-user-agent che contiene virgole (es. Rai 2) e spezzarle sulla prima
    virgola dava un nome fasullo."""
    if '",' in riga:
        return riga.rsplit('",', 1)[1].strip()
    return riga.split(",", 1)[1].strip() if "," in riga else ""


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    lista, guida, uscita = sys.argv[1:4]
    report = None
    if "--report" in sys.argv:
        report = sys.argv[sys.argv.index("--report") + 1]

    indice, _ = leggi_guida(guida)
    print(f"guida: {len(indice)} chiavi di ricerca")

    with open(lista, encoding="utf-8", errors="replace") as f:
        righe = f.read().split("\n")

    abbinati, mancanti, fuori = [], [], 0
    for i, riga in enumerate(righe):
        if not riga.startswith("#EXTINF"):
            continue
        nome = nome_da_extinf(riga)
        vecchio = re.search(r'tvg-id="([^"]*)"', riga)
        vecchio = vecchio.group(1) if vecchio else ""
        if not e_italiano(riga, vecchio):
            fuori += 1
            continue
        chiavi = varianti(nome)
        if vecchio:
            base = re.sub(r"@.*$", "", vecchio)
            base = re.sub(r"\.(it|eu|de|us|sm|va)$", "", base, flags=re.I)
            for k in varianti(base):
                if k not in chiavi:
                    chiavi.append(k)
        nuovo = None
        for k in chiavi:
            if k in indice:
                nuovo = indice[k]
                break
        if nuovo:
            if vecchio:
                righe[i] = riga.replace(f'tvg-id="{vecchio}"', f'tvg-id="{nuovo}"', 1)
            else:
                righe[i] = riga.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-id="{nuovo}"', 1)
            abbinati.append((nome, vecchio, nuovo))
        else:
            mancanti.append((nome, vecchio))

    with open(uscita, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(righe))

    tot = len(abbinati) + len(mancanti)
    print(f"canali italiani: {tot} | abbinati: {len(abbinati)} | senza guida: {len(mancanti)}")
    print(f"non italiani, lasciati intatti: {fuori}")
    if report:
        with open(report, "w", encoding="utf-8", newline="\n") as f:
            f.write("=== ABBINATI ===\n")
            for n, v, x in abbinati:
                f.write(f"{n}\n    {v}  ->  {x}\n")
            f.write("\n=== SENZA GUIDA ===\n")
            for n, v in mancanti:
                f.write(f"{n}   ({v})\n")
        print(f"report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
