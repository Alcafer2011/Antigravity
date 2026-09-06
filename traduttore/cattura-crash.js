// ---------------------------------------------------------------------------
// Crash di Kodi: controlla la sentinella e porta sul PC quello che ha raccolto.
//
// COME FUNZIONA
//   Sul box gira `/data/local/tmp/kodi-guardia.sh`: ogni 60 secondi guarda se
//   e' comparso un tombstone nuovo e, in quel caso, salva SUBITO in
//   `/sdcard/Download/kodi-crash/<data-ora>/` il tombstone e il
//   `kodi.old.log` — cioe' cosa stava facendo Kodi un istante prima di morire.
//   Senza la sentinella quel log sparisce al riavvio successivo: e' cosi' che
//   sono andati persi tutti i crash del 02-03/09/2026.
//
//   Questo script fa tre cose: verifica che la sentinella sia viva (e la
//   riavvia se serve, per esempio dopo un riavvio del box), scarica gli
//   archivi nuovi in `traduttore/crash/`, e riassume cosa c'e' dentro.
//
// USO
//   node traduttore/cattura-crash.js
// ---------------------------------------------------------------------------
const { UltraHD8K } = require("../src/ultrahd8k.js");
const fs = require("fs");
const path = require("path");

const ARCHIVIO = path.join(__dirname, "crash");
const REMOTO = "/sdcard/Download/kodi-crash";
const GUARDIA = "/data/local/tmp/kodi-guardia.sh";

(async () => {
  const b = new UltraHD8K();
  await b.connetti(true);
  fs.mkdirSync(ARCHIVIO, { recursive: true });

  // 1) la sentinella e' viva?
  const viva = String(await b.sh("ps -A -o PID,ARGS | grep '[k]odi-guardia' | head -1", { root: true })).trim();
  if (viva) {
    console.log("Sentinella attiva  (" + viva.split(/\s+/)[0] + ")");
  } else {
    const presente = String(await b.sh("[ -f " + GUARDIA + " ] && echo si || echo no", { root: true })).trim();
    if (presente !== "si") { console.log("ATTENZIONE: lo script della sentinella non c'e' piu' sul box. Va reinstallato."); }
    else {
      await b.sh("setsid " + GUARDIA + " </dev/null >/dev/null 2>&1 &", { root: true });
      await new Promise(r => setTimeout(r, 4000));
      const ora = String(await b.sh("ps -A -o PID,ARGS | grep '[k]odi-guardia' | head -1", { root: true })).trim();
      console.log(ora ? "Sentinella NON era attiva (probabile riavvio del box): riavviata." : "Sentinella NON riparte: da controllare a mano.");
    }
  }

  // 2) archivi nuovi sul box
  const cartelle = String(await b.sh("ls -1 " + REMOTO + " 2>/dev/null | grep -E '^[0-9]{4}-' || true", { root: true }))
    .split("\n").map(s => s.trim()).filter(Boolean);
  if (!cartelle.length) { console.log("\nNessun crash registrato. (E' una buona notizia.)"); return; }

  console.log("\nCrash registrati sul box: " + cartelle.length);
  let nuovi = 0;
  for (const c of cartelle) {
    const dove = path.join(ARCHIVIO, c);
    if (fs.existsSync(dove)) { console.log("  " + c + "  (gia' sul PC)"); continue; }
    fs.mkdirSync(dove, { recursive: true });
    for (const f of ["tombstone.txt", "prima-del-crash.log", "dopo-il-riavvio.log"]) {
      const r = await b._leggiRemoto(REMOTO + "/" + c + "/" + f);
      if (r.ok) fs.writeFileSync(path.join(dove, f), r.testo, "utf8");
    }
    nuovi++;
    // riassunto immediato
    const t = path.join(dove, "tombstone.txt");
    const testo = fs.existsSync(t) ? fs.readFileSync(t, "utf8") : "";
    const quando = (testo.match(/Timestamp: (.*)/) || [])[1] || "?";
    const uptime = (testo.match(/Process uptime: (.*)/) || [])[1] || "?";
    const dove_crash = (testo.match(/#0[0-9] pc [0-9a-f]+ .*libkodi\.so \(([^)]+)\)/) || [])[1] || "(non identificato)";
    console.log("  " + c + "  SCARICATO");
    console.log("      quando: " + quando);
    console.log("      Kodi girava da: " + uptime);
    console.log("      punto del crash: " + dove_crash);
  }
  console.log(nuovi ? "\nScaricati " + nuovi + " crash in traduttore/crash/ — leggi 'prima-del-crash.log'." : "\nNiente di nuovo.");
})().catch(e => console.log("ERRORE:", e.message));
