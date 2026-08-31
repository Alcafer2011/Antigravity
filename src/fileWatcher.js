"use strict";
/**
 * fileWatcher — ALLARME SE FILE TOCCATI DA ESTRANEO (blocco 7, punto 27).
 * Monitora src\ e, se un file cambia mentre NON siamo in fase di riavvio/apply-change
 * (che sono modifiche legittime di Hermes), scrive un avviso in .bugHunter/alerts.json.
 * Se il bridge WhatsApp è pronto, invia la notifica.
 *
 * SICURO: solo lettura/alert. Non modifica mai i file monitorati.
 */
const fs = require("fs");
const path = require("path");
const os = require("os");

const SRC = __dirname;
const ALERTS = path.join(SRC, ".bugHunter", "alerts.json");
const LOCK = path.join(os.tmpdir(), "antigravity_applychange.lock"); // apply-change scrive qui durante il riavvio

// firme dei file all'avvio
let _baseline = {};
function _snapshot() {
  try {
    for (const f of fs.readdirSync(SRC)) {
      if (!f.endsWith(".js")) continue;
      try { _baseline[f] = fs.statSync(path.join(SRC, f)).mtimeMs; } catch (_) {}
    }
  } catch (_) {}
}

// apply-change sta girando? (lock file recente)
function _applyRunning() {
  try { return (Date.now() - fs.statSync(LOCK).mtimeMs) < 60000; } catch (_) { return false; }
}

function _alert(msg) {
  try {
    fs.mkdirSync(path.dirname(ALERTS), { recursive: true });
    let arr = [];
    try { arr = JSON.parse(fs.readFileSync(ALERTS, "utf8")); } catch (_) {}
    arr.push({ at: new Date().toISOString(), msg });
    if (arr.length > 50) arr = arr.slice(-50);
    fs.writeFileSync(ALERTS, JSON.stringify(arr, null, 2), "utf8");
  } catch (_) {}
  // ★ 2026-08-01 — notifica WhatsApp rimossa insieme al bridge (non usato).
}

function start(intervalMs = 15000) {
  _snapshot();
  setInterval(() => {
    if (_applyRunning()) return; // modifiche legittime in corso, ignora
    try {
      for (const f of fs.readdirSync(SRC)) {
        if (!f.endsWith(".js")) continue;
        const m = fs.statSync(path.join(SRC, f)).mtimeMs;
        if (_baseline[f] !== undefined && m !== _baseline[f]) {
          _baseline[f] = m;
          _alert("File modificato da processo sconosciuto: " + f);
        }
      }
    } catch (_) {}
  }, intervalMs);
}

module.exports = { start, LOCK };
