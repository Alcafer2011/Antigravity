"use strict";
/**
 * zw3dAgent — sotto-agente CAD che ESEGUE comandi ZW3D via API/CLI già cablati.
 * Per ora espone helper di costruzione (non distruttivi). Se ZW3D è aperto e
 * raggiungibile sull'emulatore interno (localhost:8888), inoltra il comando.
 */
const http = require("http");

// Esegue un comando sul server ZW3D interno (porta 8888, emulatore).
function runZw(cmd) {
  return new Promise((resolve) => {
    const data = JSON.stringify({ cmd });
    const req = http.request({ host: "127.0.0.1", port: 8888, path: "/run", method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } },
      (res) => { let d = ""; res.on("data", c => d += c); res.on("end", () => resolve({ ok: true, output: d })); });
    req.on("error", e => resolve({ ok: false, error: e.message }));
    req.write(data); req.end();
  });
}

module.exports = { runZw, kind: "zw3d" };
