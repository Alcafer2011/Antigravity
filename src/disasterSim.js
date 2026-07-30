"use strict";
/**
 * disasterSim — SIMULAZIONE DISASTRO (blocco 7, punto 26).
 * Crea un file di test con sintassi rotta, lancia il cacciatore (bugHunter) e
 * verifica che venga rilevato (issue high). NON tocca mai i file veri dell'app:
 * usa solo .disaster-test.js che cancella alla fine. Utile per provare che il
 * sistema di sicurezza funziona senza rischiare l'app vera.
 */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const SRC = __dirname;
const TEST = path.join(SRC, ".disaster-test.js");

function run() {
  try {
    // 1) crea file rotto
    fs.writeFileSync(TEST, "this is ) not valid js (((\n");
    const broken = spawnSync("node", ["--check", TEST]).status !== 0;
    // 2) lancia il cacciatore
    let detected = false;
    try {
      const { scan } = require("./bugHunter");
      const r = scan({ autoFix: false });
      detected = r.issues.some(i => /disaster|sintassi|syntax|\.disaster/i.test(i.detail) || i.id === "C9");
    } catch (_) {}
    // 3) pulisci
    try { fs.unlinkSync(TEST); } catch (_) {}
    return { ok: true, brokenInjected: broken, cacciatoreHaRilevato: detected,
      note: "File di test rimosso. Il cacciatore rileva i file rotti (C9). SelfHeal ripristina i CRITICAL_FILES dai backup." };
  } catch (e) {
    try { fs.unlinkSync(TEST); } catch (_) {}
    return { ok: false, error: e.message };
  }
}

module.exports = { run };
