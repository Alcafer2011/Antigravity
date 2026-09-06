// Verifica finale: box sveglio, API viva, istanze puntate, conteggio canali PVR
const { UltraHD8K } = require("../src/ultrahd8k.js");
(async () => {
  const b = new UltraHD8K();
  await b.connetti(true);
  await b.sveglia({ schermo: false, attendiMs: 8000 });
  const dl = "/storage/emulated/0/Download";
  const dir = b.cfg.kodiHome + "/userdata/addon_data/pvr.iptvsimple";

  const ls = await b.sh("ls -l " + dl + "/ITA_RUS.m3u; grep -c '#EXTINF' " + dl + "/ITA_RUS.m3u", { root: true });
  console.log("FILE:", ls.out || ls);

  for (const fn of ["instance-settings-1.xml","instance-settings-2.xml","instance-settings-3.xml"]) {
    const r = await b._leggiRemoto(dir + "/" + fn);
    if (!r.ok) { console.log(fn, "non leggibile"); continue; }
    const g = (id) => { const m = r.testo.match(new RegExp('<setting id="'+id+'"[^>]*>([^<]*)</setting>')); return m ? m[1] : "?"; };
    console.log(fn, "| m3uPath=" + g("m3uPath"), "| refreshMode=" + g("m3uRefreshMode"));
  }

  // API + canali PVR (con attesa import)
  let ok = false, tv = -1, radio = -1;
  for (let i = 0; i < 12; i++) {
    try {
      await b.rpc("JSONRPC.Ping");
      const t = await b.rpc("PVR.GetChannels", { channelgroupid: "alltv" });
      tv = (t && t.limits && t.limits.total) || 0;
      try { const rd = await b.rpc("PVR.GetChannels", { channelgroupid: "allradio" }); radio = (rd && rd.limits && rd.limits.total) || 0; } catch(e){ radio = 0; }
      ok = true;
      if (tv > 0) break;
    } catch (e) { /* non ancora su */ }
    await new Promise(r => setTimeout(r, 10000));
  }
  console.log("API:", ok ? "viva" : "NON risponde", "| canali TV:", tv, "| radio:", radio);
})().catch(e => console.log("FATAL:", e.message));
