"use strict";
/**
 * specialists.js — dispatcher dei sotto-agenti specializzati (Opzione B dell'utente).
 *
 * Il "direttore" (nativeAgent) riceve la richiesta; questo modulo capisce di che
 * mestiere è e ritorna il blocco del sotto-agente giusto da appendere al system prompt.
 * Priorità: ghidra > zw3d > immagini > web (il primo che riconosce vince).
 *
 * SICUREZZA: se un file manca, quel sotto-agente ritorna "" e si passa al successivo.
 * Se nessuno calza, ritorna "" (l'agente resta col MANIFESTO + istruzioni vive).
 * Nessun file viene mai scritto qui: solo lettura.
 */

const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "knowledge", "specialisti");
const FILES = {
  ghidra:   path.join(DIR, "ghidra.md"),
  zw3d:     path.join(DIR, "zw3d.md"),
  immagini: path.join(DIR, "immagini.md"),
  web:      path.join(DIR, "web.md"),
};

// Agenti ESEGUIBILI (sotto-cartella agents/). Se il file manca, quel sotto-agente
// resta solo "testuale" (istruzioni nel prompt) e non esegue codice.
const AGENTS = {
  ghidra:   path.join(__dirname, "agents", "ghidraAgent.js"),
  zw3d:     path.join(__dirname, "agents", "zw3dAgent.js"),
  immagini: path.join(__dirname, "agents", "imageAgent.js"),
  web:      path.join(__dirname, "agents", "webAgent.js"),
};

// Parole-chiave per riconoscere il mestiere (semplici, robuste).
const SIGNALS = {
  ghidra: /(reverse|decompil|ghidra|disassembl|\.dll|\.exe|\.sys|binary|binario|pe header|import table|unpack|packer|offusc|hook|frida|radare|diec|license check|controllo licenz)/i,
  zw3d:   /(zw3d|cad|solidworks|taglio|lamiera|fresat|alesat|file z3|api zw|modello 3d|disegno tecnico|quotatura|feature tree|entity)/i,
  immagini: /(immagin|genera un'immagine|crea un'immagine|logo|illustraz|disegna|foto|png|render|comfy|stable diffusion|sd1\.5)/i,
  web:    /(cerca|ricerca|google|web|tor|\.onion|sito|url|documentazione|docs|github|stackoverflow|fonte|link|naviga)/i,
};

function _read(p) {
  try { return fs.readFileSync(p, "utf8").trim(); } catch (_) { return ""; }
}

/**
 * Ritorna { key, block } del sotto-agente rilevante, o { key:null, block:"" }.
 * @param {string} text  il testo della richiesta dell'utente
 */
function pickSpecialist(text) {
  const t = String(text || "");
  // Ordine di priorità: RE prima di tutto (spesso i .exe/.dll sono anche "web").
  for (const key of ["ghidra", "zw3d", "immagini", "web"]) {
    if (!SIGNALS[key].test(t)) continue;
    const block = _read(FILES[key]);
    if (!block) continue; // file mancante: salta al prossimo
    return { key, block: "\n\n=== SOTTO-AGENTE: " + key.toUpperCase() + " ===\n" + block + "\n=== FINE SOTTO-AGENTE ===" };
  }
  return { key: null, block: "" };
}

/** Solo il blocco (per comodità). */
function specialistBlock(text) {
  return pickSpecialist(text).block;
}

/**
 * ★ 2026-07-27 — ESECUZIONE REALE: se la richiesta è un "comando esegui" per un
 * sotto-agente, chiama l'agente eseguibile corrispondente e ritorna il suo output.
 * Se l'agente non esiste o fallisce, ritorna { ok:false } (il direttore decide).
 *   key: "ghidra"|"zw3d"|"immagini"|"web"
 *   input: dipende dall'agente (es. per ghidra: { action:"analyze", path:"./x.exe" })
 */
function runSpecialist(key, input) {
  const agentPath = AGENTS[key];
  if (!agentPath || !fs.existsSync(agentPath)) return { ok: false, error: "agente non disponibile: " + key };
  try {
    const agent = require(agentPath);
    switch (key) {
      case "ghidra":
        if (input && input.action === "strings") return agent.strings(input.path);
        if (input && input.action === "decompile") return agent.decompile(input.path);
        if (input && input.action === "secrets") return agent.secrets(input.path);
        if (input && input.action === "diff") return agent.diff(input.a, input.b);
        return agent.analyze(input && input.path);
      case "zw3d":
        return agent.runZw(input && input.cmd);
      case "immagini":
        return agent.generate(input && input.prompt, input || {});
      case "web":
        if (input && input.onion) return agent.onion(input.url);
        return agent.search(input && input.query, input || {});
      default:
        return { ok: false, error: "chiave sconosciuta: " + key };
    }
  } catch (e) { return { ok: false, error: e.message }; }
}

module.exports = { pickSpecialist, specialistBlock, runSpecialist, FILES, AGENTS };
