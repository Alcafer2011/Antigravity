// Riduce IPTV Simple a Italia+Russia senza rompere niente:
// 1) scarica MONDIALE_completo.m3u dal box
// 2) filtra i blocchi con group-title Italy o Russia -> ITA_RUS.m3u
// 3) lo carica sul box in Download
// 4) punta instance-1 e instance-3 al nuovo file, refreshMode=0 su tutte (backup)
// 5) riavvia Kodi e verifica il conteggio canali
const { UltraHD8K } = require("../src/ultrahd8k.js");
const fs = require("fs"), path = require("path"), os = require("os");

(async () => {
  const b = new UltraHD8K(); await b.connetti(true);
  const dl = "/storage/emulated/0/Download";
  const dir = b.cfg.kodiHome + "/userdata/addon_data/pvr.iptvsimple";

  // 1) pull mondiale
  const r = await b._leggiRemoto(dl + "/MONDIALE_completo.m3u");
  if (!r.ok) { console.log("no m3u:", r.out); return; }
  const righe = r.testo.split(/\r?\n/);
  console.log("righe mondiale:", righe.length);

  // 2) filtro blocchi Italy/Russia
  const tieni = /group-title="(Italy|Russia)"/i;
  const out = ["#EXTM3U"];
  let n = 0;
  for (let i = 0; i < righe.length; i++) {
    const l = righe[i];
    if (l.startsWith("#EXTINF")) {
      if (tieni.test(l)) {
        out.push(l);
        // righe successive del blocco fino al prossimo #EXTINF o EOF
        let j = i + 1;
        while (j < righe.length && !righe[j].startsWith("#EXTINF")) {
          if (righe[j].trim() !== "" && !righe[j].startsWith("#EXTM3U")) out.push(righe[j]);
          j++;
        }
        n++;
        i = j - 1;
      }
    }
  }
  console.log("canali tenuti (Italia+Russia):", n);
  const locale = path.join(os.tmpdir(), "ITA_RUS.m3u");
  fs.writeFileSync(locale, out.join("\n") + "\n", "utf8");
  console.log("dimensione filtrato:", (fs.statSync(locale).size / 1024).toFixed(0), "KB");

  // 3) push sul box
  const dest = dl + "/ITA_RUS.m3u";
  const p = await b._adb(["-s", b.cfg.indirizzo, "push", locale, dest], { timeout: 120000 });
  console.log("push:", p.ok ? "OK" : p.out);
  await b.sh("chmod 664 " + dest + " 2>/dev/null; echo ok", { root: true });

  // 4) patch instances (backup + m3uPath -> ITA_RUS per 1 e 3; refresh 0 su tutte)
  for (const [fn, cambiaPath] of [["instance-settings-1.xml", true], ["instance-settings-2.xml", false], ["instance-settings-3.xml", true]]) {
    const f = dir + "/" + fn;
    const cur = await b._leggiRemoto(f);
    if (!cur.ok) { console.log(fn, "no read"); continue; }
    await b.sh("cp " + f + " " + f + ".bak-itarus 2>/dev/null; echo bk", { root: true });
    let x = cur.testo;
    const set = (id, val) => {
      const rx = new RegExp('(<setting id="' + id + '"[^>]*>)[^<]*(</setting>)');
      if (rx.test(x)) x = x.replace(rx, "$1" + val + "$2");
    };
    if (cambiaPath) set("m3uPath", dest);
    set("m3uRefreshMode", "0");
    const w = await b._scriviRemoto(f, x);
    console.log(fn, w.ok ? ("OK" + (cambiaPath ? " -> ITA_RUS" : "") + " refresh=0") : ("ERR " + w.out));
  }

  console.log("riavvio Kodi...");
  console.log(await b.kodiRiavvia());
})().catch(e => console.log("FATAL:", e.message));
