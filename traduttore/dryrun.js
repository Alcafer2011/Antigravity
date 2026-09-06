const fs = require("fs"), path = require("path");
const ANCORE = ["addDir","addItem","ListItem(","setLabel","notification","notify(","Dialog",".ok(","yesno","select","cm.append","set_category","browse(",'"plot"',"'plot'",'"title"',"'title'","heading",'"genre"',"'genre'"];
const VIETATE = ["log(","log_debug",".replace(","xbmc.log"];
function traduciPy(t, tr){
  let c=0;
  const out=t.split("\n").map(riga=>{
    if(VIETATE.some(v=>riga.includes(v))||!ANCORE.some(a=>riga.includes(a))) return riga;
    let n=riga;
    for(const[src,dst] of Object.entries(tr)){
      for(const q of ['"',"'"]){ const ago=q+src+q; if(n.includes(ago)){ n=n.split(ago).join(q+dst+q); c++; } }
    }
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
for(const prof of ["plugin.video.vavooto","plugin.video.aguiavavoo"]){
  const p=JSON.parse(fs.readFileSync("traduttore/profili/"+prof+".json","utf8"));
  console.log("\n========== "+prof+" ==========");
  let tot=0;
  for(const rel of p.file){
    const fp=path.join("traduttore/estratti",prof,rel);
    if(!fs.existsSync(fp)){ console.log("  (manca "+rel+")"); continue; }
    const t=fs.readFileSync(fp,"utf8");
    const r=fp.endsWith(".xml")?traduciXml(t,p.traduzioni):traduciPy(t,p.traduzioni);
    tot+=r.cambi;
    if(r.cambi){
      const A=t.split("\n"), B=r.testo.split("\n"); let shown=0;
      for(let i=0;i<A.length;i++){ if(A[i]!==B[i]&&shown<5){ console.log("  "+rel+":"+(i+1)+"  "+B[i].trim().slice(0,105)); shown++; } }
      console.log("     -> "+rel+": "+r.cambi+" cambi");
    }
  }
  console.log("TOTALE "+prof+": "+tot+" sostituzioni");
}
