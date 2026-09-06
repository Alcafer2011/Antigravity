// Ripristina i file bersaglio di aguiavavoo dagli originali locali (estratti/),
// poi ri-applica la traduzione col motore corretto, pulisce pycache, riavvia.
const { UltraHD8K } = require("../src/ultrahd8k.js");
const fs = require("fs"), path = require("path");

const ANCORE = ["addDir","addItem","ListItem(","setLabel","notification","notify(","Dialog",".ok(","yesno","select","cm.append","set_category","browse(",'"plot"',"'plot'",'"title"',"'title'","heading",'"genre"',"'genre'"];
const VIETATE = ["log(","log_debug",".replace(","xbmc.log"];
function traduciPy(t, tr){ let c=0; const out=t.split("\n").map(riga=>{
  if(VIETATE.some(v=>riga.includes(v))||!ANCORE.some(a=>riga.includes(a))) return riga;
  let n=riga; for(const[src,dst] of Object.entries(tr)) for(const q of ['"',"'"]){ const ago=q+src+q; if(n.includes(ago)){ const s=dst.split(q).join("\\"+q); n=n.split(ago).join(q+s+q); c++; } }
  return n; }); return {testo:out.join("\n"), cambi:c}; }
function traduciXml(t, tr){ let c=0;
  t=t.replace(/(label=")([^"]*)(")/g,(m,a,val,b)=>{ if(tr[val]){c++;return a+tr[val]+b;} return m; });
  t=t.replace(/(values=")([^"]*)(")/g,(m,a,val,b)=>{ const seg=val.split("|").map(p=>tr[p]?(c++,tr[p]):p); return a+seg.join("|")+b; });
  return {testo:t, cambi:c}; }

(async () => {
  const b = new UltraHD8K(); await b.connetti(true);
  const prof = "plugin.video.aguiavavoo";
  const home = b.cfg.kodiHome + "/addons";
  const p = JSON.parse(fs.readFileSync(path.join(__dirname, "profili", prof + ".json"), "utf8"));

  // 1) ripristino originali
  for (const rel of p.file) {
    const orig = path.join(__dirname, "estratti", prof, rel);
    if (!fs.existsSync(orig)) { console.log("manca originale " + rel); continue; }
    const w = await b._scriviRemoto(home + "/" + prof + "/" + rel, fs.readFileSync(orig, "utf8"));
    console.log("ripristino " + (w.ok ? "OK  " : "ERR ") + rel);
  }

  // 2) ri-applico
  let tot = 0;
  for (const rel of p.file) {
    const r = await b._leggiRemoto(home + "/" + prof + "/" + rel);
    if (!r.ok) continue;
    const res = rel.endsWith(".xml") ? traduciXml(r.testo, p.traduzioni) : traduciPy(r.testo, p.traduzioni);
    if (!res.cambi) continue;
    const w = await b._scriviRemoto(home + "/" + prof + "/" + rel, res.testo);
    console.log("applico " + (w.ok ? "OK  " : "ERR ") + rel + " (" + res.cambi + ")");
    tot += res.cambi;
  }
  await b.sh("find " + home + "/" + prof + " -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo done", { root: true });
  console.log("totale " + tot + " sostituzioni, pycache pulita");

  console.log(await b.kodiRiavvia());
  // 3) verifica funzionale
  try {
    const d = await b.rpc("Files.GetDirectory", { directory: "plugin://" + prof + "/" }, { timeout: 60000 });
    console.log("MENU aguiavavoo: " + (d.files || []).map(f => f.label).join("  |  "));
  } catch (e) { console.log("verifica err: " + e.message); }
})().catch(e => console.log("FATAL:", e.message));
