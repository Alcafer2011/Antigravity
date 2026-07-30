"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

/**
 * ghidraHeadless — analisi Ghidra COMPLETAMENTE AUTOMATICA, senza GUI.
 *
 * Dai un percorso di binario: importa + analizza in un progetto temporaneo con
 * analyzeHeadless, esegue lo script decompile_dump.py e restituisce l'output
 * (elenco funzioni, oppure la decompilazione di una funzione richiesta).
 * A fine lavoro il progetto temporaneo viene eliminato (-deleteProject).
 *
 * È l'alternativa "a un solo path" al flusso GUI di GhidraMCP: nessun click,
 * ma più lenta (rifà l'analisi ogni volta). Utile per file al volo.
 */

const HEADLESS_CANDIDATES = [
    "C:\\ProgramData\\chocolatey\\lib\\ghidra\\tools\\ghidra_12.1.2_PUBLIC\\support\\analyzeHeadless.bat",
    "C:\\Program Files\\ghidra_12.1.2_PUBLIC\\support\\analyzeHeadless.bat"
];
// Cartella script di Ghidra dell'utente (già scansionata da Ghidra headless).
const SCRIPT_DIR = path.join(os.homedir(), "ghidra_scripts");

function findHeadless() {
    for (const p of HEADLESS_CANDIDATES) if (fs.existsSync(p)) return p;
    return null;
}

/**
 * @param {string} binaryPath  file da analizzare
 * @param {object} o  { functionName, timeoutMs, onStatus }
 * @returns {string} output testuale (o messaggio d'errore)
 */
function analyzeFile(binaryPath, o = {}) {
    const onStatus = o.onStatus || (() => {});
    if (!binaryPath || !fs.existsSync(binaryPath)) return "ERRORE: file non trovato: " + binaryPath;
    const headless = findHeadless();
    if (!headless) return "ERRORE: analyzeHeadless.bat non trovato (Ghidra non installato?).";

    const projDir = fs.mkdtempSync(path.join(os.tmpdir(), "agHeadless_"));
    const projName = "ag_" + Date.now().toString(36);
    const target = o.functionName ? String(o.functionName) : "__list__";
    const args = [
        projDir, projName,
        "-import", binaryPath,
        "-scriptPath", SCRIPT_DIR,
        "-postScript", "decompile_dump.java", target,
        "-deleteProject"
    ];
    onStatus("🐉 Analisi headless di " + path.basename(binaryPath) + " (può volerci un po')…");
    // Su Windows i .bat vanno eseguiti con shell:true; quotiamo noi ogni argomento.
    const cmdLine = ['"' + headless + '"'].concat(args.map(a => '"' + String(a) + '"')).join(" ");
    let out;
    try {
        out = spawnSync(cmdLine, {
            shell: true,
            encoding: "utf8",
            timeout: o.timeoutMs || 300000,           // 5 min max
            maxBuffer: 32 * 1024 * 1024,
            windowsHide: true
        });
    } catch (e) {
        try { fs.rmSync(projDir, { recursive: true, force: true }); } catch (_) {}
        return "ERRORE analyzeHeadless: " + e.message;
    }
    try { fs.rmSync(projDir, { recursive: true, force: true }); } catch (_) {}

    const stdout = (out.stdout || "") + (out.stderr || "");
    if (out.error && out.error.code === "ETIMEDOUT") return "TIMEOUT: analisi troppo lunga. Usa un binario più piccolo o la GUI (🐉 Ghidra RE).";
    // Estrae solo la parte utile prodotta dallo script (dopo i marcatori ===).
    const idx = stdout.search(/=== (FUNZIONI|DECOMPILE)/);
    if (idx >= 0) return stdout.slice(idx).trim().slice(0, 40000);
    // Lo scripting headless di Ghidra 12 può fallire (PyGhidra assente / conflitto OSGi
    // con estensioni). In tal caso indirizza al flusso GUI che è affidabile.
    if (/PyGhidra|BundleException|SCRIPT ERROR|not available/i.test(stdout)) {
        return "L'analisi HEADLESS non è disponibile su questa installazione di Ghidra 12 " +
            "(lo scripting headless è in conflitto con le estensioni). " +
            "USA IL FLUSSO GUI, che funziona: apri il binario in Ghidra (File→Import File) " +
            "e usa gli strumenti ghidra_decompile / ghidra_list_functions sul programma aperto.";
    }
    return stdout.trim().slice(-4000) || "(nessun output dall'analisi)";
}

module.exports = { analyzeFile, findHeadless };
