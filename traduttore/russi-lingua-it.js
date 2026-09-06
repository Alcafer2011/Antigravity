// ---------------------------------------------------------------------------
// Rimette in italiano gli add-on russi (Filmix, United Search) dopo un
// aggiornamento.
//
// PERCHE' SERVE
//   Filmix e United Search parlano solo inglese e russo. L'italiano l'abbiamo
//   scritto noi: sono file `resources/language/Italian/strings.po` dentro
//   ciascun add-on. Un aggiornamento dell'add-on riscrive la sua cartella e
//   **cancella la lingua italiana**: questo script la rimette.
//   I file veri stanno in `traduttore/lingue-it/<addon>/strings.po`.
//
// COSA NON PUO' FARE
//   I titoli dei film restano in russo: arrivano dal sito, non dall'add-on.
//
// USO
//   node traduttore/russi-lingua-it.js
// ---------------------------------------------------------------------------
const { UltraHD8K } = require("../src/ultrahd8k.js");
const fs = require("fs");
const path = require("path");

const ORIGINE = path.join(__dirname, "lingue-it");

(async () => {
  const b = new UltraHD8K();
  await b.connetti(true);
  const H = b.cfg.kodiHome;

  const addon = fs.existsSync(ORIGINE) ? fs.readdirSync(ORIGINE) : [];
  if (!addon.length) { console.log("Nessuna traduzione in " + ORIGINE); return; }

  // serve un riferimento per proprietario/permessi: prendo un add-on sano
  const rif = String(await b.sh("stat -c '%u:%g' " + H + "/addons/plugin.video.s4me", { root: true })).trim();
  if (!/^\d+:\d+$/.test(rif)) { console.log("Non riesco a leggere il proprietario di riferimento: " + rif); return; }

  let daFare = [];
  for (const a of addon) {
    const locale = path.join(ORIGINE, a, "strings.po");
    if (!fs.existsSync(locale)) continue;
    const dir = H + "/addons/" + a;
    const presente = String(await b.sh("[ -d " + dir + " ] && echo si || echo no", { root: true })).trim();
    if (presente !== "si") { console.log("  " + a + ": add-on non installato, salto"); continue; }

    const dest = dir + "/resources/language/Italian/strings.po";
    const attuale = await b._leggiRemoto(dest);
    const nostro = fs.readFileSync(locale, "utf8");
    if (attuale.ok && attuale.testo.trim() === nostro.trim()) { console.log("  " + a + ": gia' in italiano"); continue; }
    daFare.push([a, dir, dest, nostro]);
  }

  if (!daFare.length) { console.log("\nEra gia' tutto a posto."); return; }

  console.log("\nFermo Kodi (i file degli add-on non si cambiano a caldo)...");
  console.log("  " + await b.kodiFerma());
  await new Promise(r => setTimeout(r, 6000));

  for (const [a, dir, dest, testo] of daFare) {
    await b.sh("mkdir -p " + dir + "/resources/language/Italian", { root: true });
    const w = await b._scriviRemoto(dest, testo);
    await b.sh("chown -R " + rif + " " + dir + "/resources/language/Italian; chmod -R 750 " + dir + "/resources/language/Italian", { root: true });
    console.log("  " + a + ": " + (w.ok ? "italiano rimesso" : "ERRORE " + w.out));
  }

  console.log("\nRiavvio Kodi...");
  console.log("  " + JSON.stringify(await b.kodiAvvia({ attendi: true })));
})().catch(e => console.log("ERRORE:", e.message));
