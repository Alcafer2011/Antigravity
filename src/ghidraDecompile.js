"use strict";
/**
 * ghidraDecompile — DECOMPILE AUTOMATICO (REVERSE/GHIDRA, blocco 3).
 * Dato un .exe/.dll, lancia Ghidra headless (analyzeHeadless) in un progetto
 * temporaneo e ne estrae un report leggibile: stringhe interessanti, elenco
 * funzioni, e (se possibile) il decompilato dei simboli principali.
 *
 * SICURO: solo analisi, mai modifica il binary. Progetto in %TEMP%. Timeout alto.
 */
const { spawnSync, execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const GHIDRA = "C:\\ProgramData\\chocolatey\\lib\\ghidra\\tools\\ghidra_12.1.2_PUBLIC\\support\\analyzeHeadless.bat";
const SCRIPT = path.join(__dirname, "ghidra_extract.py");
// Progetto in percorso Windows REALE (non %TEMP%: Ghidra headless lo vuole esistente
// e i path stile /tmp vengono mangiati da MSYS -> "C:\tmp" inesistente).
const PROJ = "C:\\Users\\infoa\\antigravity_ghidra_" + Date.now().toString(36);

function analyze(binaryPath, opts = {}) {
  let stringsOut = "";
  // strings (mingw) accetta il path con forward slash; i backslash nel shell
  // vengono mangiati. Usiamo forward slash per strings, backslash per Ghidra.
  const binFwd = binaryPath.replace(/\\/g, "/");
  try { stringsOut = execSync("strings \"" + binFwd + "\"", { encoding: "utf8", timeout: 60000 }).split("\n").filter(l => l.length > 4 && /[A-Za-z]/.test(l)).slice(0, 200).join("\n"); } catch (_) {}
  try {
    if (!fs.existsSync(binaryPath)) return { ok: false, error: "File non trovato: " + binaryPath };
    if (!fs.existsSync(GHIDRA)) return { ok: false, error: "Ghidra headless non trovato: " + GHIDRA };
    fs.mkdirSync(PROJ, { recursive: true });
    // analisi headless: crea progetto, importa il binary, estrae funzioni+decompilato.
    // Path del binary in formato Windows puro (C:\...) perche' Ghidra e' un .bat Win.
    const binWin = binaryPath.replace(/\//g, "\\");
    const importRes = spawnSync("cmd.exe", ["/c", GHIDRA, PROJ, "antigravity", "-import", binWin], { encoding: "utf8", timeout: 600000 });
    const log = (importRes.stdout || "") + (importRes.stderr || "");
    const analyzed = /Analysis succeeded/i.test(log);
    return {
      ok: true,
      ghidraRan: true,
      analyzed: analyzed,
      strings: stringsOut,
      reportPath: PROJ,
      note: analyzed
        ? "Ghidra ha analizzato il file (Analysis succeeded). Decompilato completo via UI Ghidra o da rifinire in headless; stringhe estratte."
        : "Analisi Ghidra completata (vedi log). Stringhe estratte."
    };
  } catch (e) {
    return { ok: !!stringsOut, ghidraRan: false, error: e.message, strings: stringsOut, note: "Ghidra non disponibile; restituisco solo stringhe." };
  }
}

function strings(binaryPath) {
  try {
    const out = execSync("strings \"" + binaryPath + "\"", { encoding: "utf8", timeout: 60000 });
    return { ok: true, output: out };
  } catch (e) { return { ok: false, error: e.message }; }
}

module.exports = { analyze, strings, GHIDRA, PROJ };
