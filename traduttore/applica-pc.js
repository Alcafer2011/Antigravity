// Applica la traduzione direttamente dal PC (stesso motore del dry-run), con
// backup gia' presente in traduttore/estratti/. Scrive i file via root-safe,
// pulisce __pycache__, riavvia Kodi.
const { UltraHD8K } = require("../src/ultrahd8k.js");
const fs = require("fs"), path = require("path");

const ANCORE = ["addDir","addItem","ListItem(","setLabel","notification","notify(","Dialog",".ok(","yesno","select","cm.append","set_category","browse(",'"plot"',"'plot'",'"title"',"'title'","heading",'"genre"',"'genre'"];
const VIETATE = ["log(","log_debug",".replace(","xbmc.log"];
function traduciPy(t, tr){
  let c=0;
  const out=t.split("\n").map(riga=>{
    if(VIETATE.some(v=>riga.includes(v))||!ANCORE.some(a=>riga.includes(a))) return riga;
    let n=riga;
    for(const[src,dst] of Object.entries(tr)) for(const q of ['"',"'"]){ const ago=q+src+q; if(n.includes(ago)){ const dstSafe=dst.split(q).join("\\"+q); n=n.split(ago).join(q+dstSafe+q); c++; } }
    return n;
  });
  return {testo:out.join("\n"), cambi:c};
}
function traduciXml(t, tr){
  let c=0;
  t=t.replace(/(label=")([^"]*)(")/g,(m,a,val,b)=>{ if(tr[val]){c++;return a+tr[val]+b;} return m; });
  t=t.replace(/(values=")([^"]*)(")/g,(m,a,val,b)=>{ const seg=val.split("|").map(p=>{ if(tr[p]){c++;return tr[p];} return p; }); return a+seg.join("|")+b; });
  return {testo:t, cambi:c};
}

(async () => {
  const b = new UltraHD8K();
  const c = await b.connetti(true);
  if (!c.ok) { console.log("STOP:", c.out); return; }
  const home = b.cfg.kodiHome + "/addons";

  for (const prof of ["plugin.video.vavooto", "plugin.video.aguiavavoo"]) {
    const p = JSON.parse(fs.readFileSync(path.join(__dirname, "profili", prof + ".json"), "utf8"));
    console.log("\n===== " + prof + " =====");
    let tot = 0;
    for (const rel of p.file) {
      const remoto = home + "/" + prof + "/" + rel;
      const r = await b._leggiRemoto(remoto);
      if (!r.ok) { console.log("  salto " + rel + " (" + r.out + ")"); continue; }
      const res = rel.endsWith(".xml") ? traduciXml(r.testo, p.traduzioni) : traduciPy(r.testo, p.traduzioni);
      if (!res.cambi) { continue; }
      const w = await b._scriviRemoto(remoto, res.testo);
      console.log("  " + (w.ok ? "OK  " : "ERR ") + rel + "  (" + res.cambi + " cambi)" + (w.ok ? "" : " " + w.out));
      tot += res.cambi;
    }
    // pulizia __pycache__
    await b.sh("find " + home + "/" + prof + " -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo done", { root: true });
    console.log("  totale " + prof + ": " + tot + " sostituzioni, __pycache__ pulita");
  }

  console.log("\nriavvio Kodi...");
  console.log(await b.kodiRiavvia());
})().catch(e => console.log("FATAL:", e.message));
