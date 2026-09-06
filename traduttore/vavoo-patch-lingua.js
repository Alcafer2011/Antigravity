// ---------------------------------------------------------------------------
// Ridà a plugin.video.vavooto l'italiano dopo un aggiornamento.
//
// PERCHE' SERVE
//   Il plugin ha il tedesco SCRITTO FISSO nel codice, in due punti distinti:
//     1) ogni richiesta all'API Vavoo chiede {"language":"de","region":"AT"}
//        e i metadati TMDB sono chiesti in "de-DE"  -> catalogo tedesco;
//     2) vjackson.py scarta le sorgenti con  if not "de" in a['languages']
//        -> anche quando Vavoo offre l'italiano, il plugin lo butta via.
//   Un aggiornamento del plugin riscrive quei file e riporta tutto in tedesco.
//   Questo script rimette a posto entrambe le cose. E' idempotente: rilanciarlo
//   quando e' gia' a posto non fa danni, dice solo "gia' applicata".
//
// USO
//   node traduttore/vavoo-patch-lingua.js
// ---------------------------------------------------------------------------
const { UltraHD8K } = require("../src/ultrahd8k.js");

const PRIORITA = ["it", "en", "ru", "de"];   // ordine di preferenza delle lingue
const MARCA = "patch Antigravity";           // firma: se c'e', il filtro e' gia' nostro

const FILE_LINGUA = ["resources/vavoo/live_proxy.py", "resources/vavoo/utils.py",
                     "resources/vavoo/vavoo_tv.py", "resources/vavoo/vjackson.py",
                     "resources/vavoo/vjlive.py"];

const FILTRO_ORIGINALE = "\t\t\tif not \"de\" in a.get('languages', []): continue\n";
const FILTRO_NUOVO =
  "\t\t\t# --- lingua: teniamo IT/EN/RU/DE invece del solo DE (" + MARCA + ") ---\n" +
  "\t\t\t_pri = " + JSON.stringify(PRIORITA).replace(/"/g, '"') + "\n" +
  "\t\t\t_langs = [str(l).lower()[:2] for l in (a.get('languages') or [])]\n" +
  "\t\t\t_scelte = [l for l in _pri if l in _langs]\n" +
  "\t\t\tif not _scelte: continue\n" +
  "\t\t\t_lang = _scelte[0]\n" +
  "\t\t\t_bonus = (len(_pri) - _pri.index(_lang)) * 10000\n";
const APPEND = "\t\t\tnewurllist.append({\"name\":a[\"name\"]";
const ETICHETTA =
  "\t\t\ta[\"name\"] = \"[%s] %s\" % (_lang.upper(), a[\"name\"])\n" +
  "\t\t\ta[\"weight\"] = a[\"weight\"] + _bonus\n";

(async () => {
  const b = new UltraHD8K();
  await b.connetti(true);
  const H = b.cfg.kodiHome;
  const P = H + "/addons/plugin.video.vavooto";

  if (!(await b.sh("[ -d " + P + " ] && echo si || echo no", { root: true })).includes("si")) {
    console.log("plugin.video.vavooto non e' installato: niente da fare.");
    return;
  }

  console.log("Fermo Kodi (le modifiche ai file non si applicano a caldo)...");
  await b.kodiFerma();
  await new Promise(r => setTimeout(r, 5000));

  const quando = new Date().toISOString().slice(0, 10);
  await b.sh("cp -r " + P + " /data/local/tmp/vavooto-bak-" + quando + " 2>/dev/null; echo bk", { root: true });

  // ---- 1) lingua nelle richieste all'API + metadati TMDB -------------------
  let totale = 0;
  for (const rel of FILE_LINGUA) {
    const f = P + "/" + rel;
    const r = await b._leggiRemoto(f);
    if (!r.ok) { console.log("  " + rel + ": non leggibile, salto"); continue; }
    let t = r.testo, n = 0;
    const sost = (rx, val) => { const m = t.match(rx); if (m) { n += m.length; t = t.replace(rx, val); } };
    sost(/"language":(\s*)"de"/g, '"language":$1"it"');
    sost(/"region":(\s*)"AT"/g, '"region":$1"IT"');
    sost(/"de-DE"/g, '"it-IT"');
    if (!n) { console.log("  " + rel + ": gia' in italiano"); continue; }
    const w = await b._scriviRemoto(f, t);
    console.log("  " + rel + ": " + n + " sostituzioni " + (w.ok ? "OK" : "ERRORE " + w.out));
    totale += n;
  }

  // ---- 2) filtro che scartava tutto cio' che non era tedesco --------------
  const fj = P + "/resources/vavoo/vjackson.py";
  const rj = await b._leggiRemoto(fj);
  if (!rj.ok) {
    console.log("vjackson.py non leggibile: il filtro lingua NON e' stato sistemato.");
  } else if (rj.testo.includes(MARCA)) {
    console.log("  filtro sorgenti: gia' applicato");
  } else if (!rj.testo.includes(FILTRO_ORIGINALE)) {
    console.log("  ATTENZIONE: il filtro non e' nella forma attesa (il plugin e' cambiato).");
    console.log("  Controlla a mano la riga con  a.get('languages')  in vjackson.py.");
  } else {
    let t = rj.testo.replace(FILTRO_ORIGINALE, FILTRO_NUOVO);
    if (t.includes(APPEND)) t = t.replace(APPEND, ETICHETTA + APPEND);
    const w = await b._scriviRemoto(fj, t);
    console.log("  filtro sorgenti: riscritto (IT>EN>RU>DE, con etichetta) " + (w.ok ? "OK" : "ERRORE " + w.out));
    totale++;
  }

  // ---- 3) pulizia: bytecode e cache conservano la versione tedesca --------
  await b.sh("rm -rf " + P + "/resources/vavoo/__pycache__ " + P + "/resources/__pycache__; " +
             "rm -rf " + H + "/userdata/addon_data/plugin.video.vavooto/cache; " +
             "rm -f " + H + "/userdata/Database/simplecache.db; echo pulito", { root: true });
  console.log("  cache e bytecode svuotati");

  console.log(totale ? "\nPatch applicata (" + totale + " modifiche). Riapri Kodi." :
                       "\nEra gia' tutto a posto. Riapri Kodi.");
})().catch(e => console.log("ERRORE:", e.message));
