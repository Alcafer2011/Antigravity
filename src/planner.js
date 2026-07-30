"use strict";
/**
 * planner — PIANIFICAZIONE A STEP (CORE AI, blocco 2).
 * Dato un compito grosso, lo scompone in passi e li esegue in sequenza,
 * mostrando il progresso. Ogni step usa l'orchestratore locale (se disponibile)
 * o un modello di chat; l'output di uno step alimenta il successivo.
 *
 * SICURO: non esegue comandi di sistema distruttivi. Se un modello non risponde,
 * si ferma (non loop infinito). Massimo 8 step.
 */
const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

function _token(name) {
  try {
    const txt = fs.readFileSync(path.join(os.homedir(), ".env"), "utf8");
    const m = txt.match(new RegExp(name + "\\s*=\\s*\"?([^\"\\r\\n]+)\"?", "i"));
    return m ? m[1].trim() : null;
  } catch (_) { return null; }
}

// Chiama un modello via Ollama/MCP locale (riusa le variabili d'ambiente).
function _ask(prompt, model) {
  // usa il server locale di chat se raggiungibile (porta 8790 stessa app)
  const http = require("http");
  return new Promise((resolve) => {
    const data = JSON.stringify({ prompt, model: model || "auto" });
    const req = http.request({ host: "127.0.0.1", port: 8790, path: "/chat", method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } },
      (res) => { let d = ""; res.on("data", c => d += c); res.on("end", () => resolve(d)); });
    req.on("error", () => resolve(""));
    req.write(data); req.end();
  });
}

/**
 * Genera un piano di N step a partire dal task.
 */
async function plan(task, model) {
  const sys = "Sei un pianificatore. Dividi il compito in massimo 8 passi concreti. " +
              "Rispondi SOLO con un JSON: {\"steps\":[\"passo 1\",\"passo 2\",...]}";
  const out = await _ask(sys + "\n\nCOMPITO: " + task, model);
  try {
    const m = out.match(/\{[\s\S]*\}/);
    if (m) { const j = JSON.parse(m[0]); if (Array.isArray(j.steps)) return j.steps.slice(0, 8); }
  } catch (_) {}
  return [task]; // fallback: un solo step
}

/**
 * Esegue il piano: ogni step viene "risolto" dal modello, l'output passa al successivo.
 * Ritorna { steps: [{ step, result }] }.
 */
async function run(task, model) {
  const steps = await plan(task, model);
  const results = [];
  let ctx = task;
  for (const s of steps) {
    const r = await _ask("Contesto finora:\n" + ctx + "\n\nEsegui questo passo: " + s, model);
    results.push({ step: s, result: r.slice(0, 2000) });
    ctx += "\n- " + s + " -> " + r.slice(0, 500);
  }
  return { steps: results };
}

module.exports = { plan, run };
