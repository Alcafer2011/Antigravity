const { UltraHD8K } = require("../src/ultrahd8k.js");
const path = require("path");

(async () => {
  const b = new UltraHD8K();
  const c = await b.connetti(true);
  if (!c.ok) { console.log("STOP:", c.out); return; }

  const localDir = path.join(__dirname, "script.traduttore.it");
  const id = "script.traduttore.it";
  const home = b.cfg.kodiHome + "/addons";
  const ponte = "/data/local/tmp/.ag_addon_" + id;

  // 1) push cartella add-on sul box
  await b.sh("rm -rf " + ponte, { root: true });
  const push = await b._adb(["-s", b.cfg.indirizzo, "push", localDir, ponte], { timeout: 180000 });
  console.log("push:", push.ok ? "OK" : push.out);
  if (!push.ok) return;

  // 2) copia in addons con owner/permessi giusti
  const own = String(await b.sh("stat -c '%U:%G' " + home + " 2>/dev/null || echo ''", { root: true })).trim();
  const dest = home + "/" + id;
  let cmd = "rm -rf '" + dest + "' && cp -r " + ponte + " '" + dest + "'";
  if (own && own !== ":") cmd += " && chown -R " + own + " '" + dest + "'";
  cmd += " && chmod -R 770 '" + dest + "' && rm -rf " + ponte + " && echo OK";
  const esito = await b.sh(cmd, { root: true });
  console.log("copia:", /OK/.test(esito) ? "OK" : esito);

  // 3) riavvio perche' Kodi scopra l'add-on
  console.log("riavvio Kodi per la scoperta...");
  console.log(await b.kodiRiavvia());

  // 4) abilita l'add-on
  try { await b.rpc("Addons.SetAddonEnabled", { addonid: id, enabled: true }); console.log("abilitato"); }
  catch (e) { console.log("abilita:", e.message); }

  // 5) esegui headless: apply all
  try {
    await b.rpc("Addons.ExecuteAddon", { addonid: id, params: ["apply", "all"] });
    console.log("ExecuteAddon lanciato");
  } catch (e) { console.log("ExecuteAddon:", e.message); }

  // 6) attesa che finisca il lavoro sui file
  await new Promise(r => setTimeout(r, 12000));

  // 7) leggi lo stato prodotto dall'add-on
  const stato = await b.sh("cat " + b.cfg.kodiHome + "/userdata/addon_data/" + id + "/stato.json 2>/dev/null || echo VUOTO", { root: true });
  console.log("--- stato.json ---\n" + stato);

  // 8) verifica: righe tradotte nei file bersaglio
  const v1 = await b._leggiRemoto(home + "/plugin.video.vavooto/resources/vavoo/vjackson.py");
  if (v1.ok) {
    const righe = v1.testo.split("\n").slice(8, 12).map(s => s.trim());
    console.log("--- vavooto vjackson.py righe 9-12 ---\n" + righe.join("\n"));
  }
  const v2 = await b._leggiRemoto(home + "/plugin.video.vavooto/resources/settings.xml");
  if (v2.ok) console.log("--- vavooto settings riga 4 ---\n" + v2.testo.split("\n")[3].trim());

  console.log("\nriavvio finale per caricare le traduzioni...");
  console.log(await b.kodiRiavvia());
})().catch(e => console.log("FATAL:", e.message));
