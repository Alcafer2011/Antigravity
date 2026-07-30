"use strict";
/**
 * ghidraAgent — sotto-agente RE che ESEGUE davvero (non solo testo).
 * - decompile(bin): lancia Ghidra headless + estrae stringhe/report (blocco 3).
 * - strings(bin): stringhe grezze.
 * - secrets(bin): estrae URL, chiavi, percorsi sospetti (blocco 3, punto 18).
 * - diff(a,b): confronta due binary per vedere cosa e' cambiato (blocco 3, punto 17).
 * SICURO: solo analisi, mai modifica i file.
 */
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

let DC = null;
try { DC = require("../ghidraDecompile"); } catch (_) {}

function decompile(binaryPath) {
  if (!DC) return { ok: false, error: "ghidraDecompile non disponibile" };
  return DC.analyze(binaryPath);
}
function strings(binaryPath) {
  try {
    const out = execSync("strings \"" + binaryPath + "\"", { encoding: "utf8", timeout: 60000 });
    return { ok: true, output: out };
  } catch (e) { return { ok: false, error: e.message }; }
}
// punto 18: estrazione config/segreto (URL, chiavi, percorsi)
function secrets(binaryPath) {
  try {
    const out = execSync("strings \"" + binaryPath + "\"", { encoding: "utf8", timeout: 60000 });
    const lines = out.split("\n");
    const url = lines.filter(l => /https?:\/\//i.test(l)).slice(0, 30);
    const keys = lines.filter(l => /(api[_-]?key|token|secret|password|passwd)=?/i.test(l)).slice(0, 20);
    const paths = lines.filter(l => new RegExp("c:\\|%appdata%|/etc/|\\.exe|\\.dll", "i").test(l)).slice(0, 30);
    return { ok: true, url, keys, paths };
  } catch (e) { return { ok: false, error: e.message }; }
}
// punto 17: diff tra due binary
function diff(a, b) {
  try {
    const sa = execSync("strings \"" + a + "\"", { encoding: "utf8", timeout: 60000 }).split("\n");
    const sb = execSync("strings \"" + b + "\"", { encoding: "utf8", timeout: 60000 }).split("\n");
    const setB = new Set(sb);
    const onlyA = sa.filter(x => !setB.has(x) && x.trim().length > 3).slice(0, 50);
    const setA = new Set(sa);
    const onlyB = sb.filter(x => !setA.has(x) && x.trim().length > 3).slice(0, 50);
    return { ok: true, onlyInA: onlyA, onlyInB: onlyB };
  } catch (e) { return { ok: false, error: e.message }; }
}
// punto 19: script Ghidra pronti (restituisce il sorgente di script utili)
const SCRIPTS = {
  renameFunctions: "/* Rinomina le funzioni per indirizzo */\nfunction run() { var f = getGlobalFunctions(); for (var i=0;i<f.length;i++){ if (f[i].getName().startsWith(\"FUN_\")) f[i].setName(\"fn_\"+i); } }\n",
  findLicenseChecks: "/* Cerca funzioni con nome contenente 'licen'/'auth' */\nfunction run() { var f = getGlobalFunctions(); for (var i=0;i<f.length;i++){ if (/licen|auth|valid/i.test(f[i].getName())) println(f[i].getName()); } }\n"
};

module.exports = { decompile, strings, secrets, diff, SCRIPTS, kind: "ghidra" };
