"use strict";

const http = require("http");
const fs = require("fs");
const { spawn } = require("child_process");

/**
 * ghidraLauncher — rende l'uso di Ghidra "a un bottone": controlla se il server
 * GhidraMCP è già attivo (porta 8080); se Ghidra è spento, lo AVVIA da solo e
 * aspetta che il plugin risponda. Così l'utente non deve avviare Ghidra a mano.
 *
 * Nota: l'IMPORT del binario nel CodeBrowser resta un gesto GUI di Ghidra (il
 * plugin GhidraMCP vive nella GUI). Il launcher automatizza tutto il resto:
 * avvio, attesa, verifica "programma caricato".
 */

const GHIDRA_RUN_CANDIDATES = [
    "C:\\ProgramData\\chocolatey\\lib\\ghidra\\tools\\ghidra_12.1.2_PUBLIC\\ghidraRun.bat",
    "C:\\Program Files\\ghidra_12.1.2_PUBLIC\\ghidraRun.bat"
];

function httpGet(path, timeout = 4000) {
    return new Promise((resolve) => {
        const req = http.request({ host: "127.0.0.1", port: 8080, path, method: "GET", timeout }, (res) => {
            let d = ""; res.setEncoding("utf8"); res.on("data", c => d += c);
            res.on("end", () => resolve({ status: res.statusCode, body: d.trim() }));
        });
        req.on("timeout", () => req.destroy());
        req.on("error", () => resolve(null));
        req.end();
    });
}

/** Il server GhidraMCP risponde? */
async function isServerUp() {
    const r = await httpGet("/methods?offset=0&limit=1");
    return !!(r && r.status === 200);
}

/** C'è un programma caricato? (il server risponde ma potrebbe dire "No program loaded") */
async function programLoaded() {
    const r = await httpGet("/methods?offset=0&limit=1");
    if (!r || r.status !== 200) return false;
    return !/no program loaded/i.test(r.body) && r.body.length > 0;
}

function findGhidraRun() {
    for (const p of GHIDRA_RUN_CANDIDATES) if (fs.existsSync(p)) return p;
    return null;
}

/** Avvia Ghidra (GUI) in background, senza finestra di console. */
function launchGhidra() {
    const bat = findGhidraRun();
    if (!bat) throw new Error("ghidraRun.bat non trovato. Installa Ghidra o correggi il percorso.");
    // ★ 2026-07-24 — FIX FINESTRA NERA "findstr.exe". `windowsHide:true` nasconde
    // SOLO il cmd che lanciamo noi: ghidraRun.bat al suo interno chiama altri
    // programmi (findstr/wmic per cercare la JVM) e QUELLI, non avendo una console
    // da ereditare (stdio:"ignore"), se ne allocano una NUOVA e visibile — la
    // finestra che restava aperta a metà schermo.
    // Soluzione: lo stesso trucco già usato per il server mobile — un VBS che fa
    // Run(..., 0, False). Il cmd nasce con una console GIÀ nascosta e tutti i suoi
    // figli la ereditano: zero finestre, per sempre.
    const os = require("os"), pathMod = require("path");
    const vbsPath = pathMod.join(os.tmpdir(), "antigravity-ghidra-launch.vbs");
    const vbs = 'Set sh = CreateObject("WScript.Shell")\r\n'
        + 'sh.Run "cmd /c ""' + bat.replace(/"/g, '""') + '""", 0, False\r\n';
    try {
        fs.writeFileSync(vbsPath, vbs, "utf8");
        const p = spawn("wscript.exe", ["//B", "//Nologo", vbsPath], { detached: true, stdio: "ignore", windowsHide: true });
        p.unref();
        return true;
    } catch (_) {
        // Se per qualche motivo il VBS non è scrivibile, si torna al metodo vecchio.
        const p = spawn("cmd.exe", ["/c", bat], { detached: true, stdio: "ignore", windowsHide: true });
        p.unref();
        return true;
    }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

/**
 * Garantisce che il server GhidraMCP sia RAGGIUNGIBILE. Se serve, avvia Ghidra e
 * aspetta (fino a ~90s: il primo avvio carica la JVM). Ritorna:
 *   { up:true, loaded:bool }  oppure  { up:false, error }
 * onStatus riceve messaggi di avanzamento da mostrare in chat.
 */
async function ensureReady(onStatus = () => {}) {
    if (await isServerUp()) {
        return { up: true, loaded: await programLoaded() };
    }
    onStatus("🐉 Ghidra è spento: lo avvio…");
    try { launchGhidra(); } catch (e) { return { up: false, error: e.message }; }
    for (let i = 0; i < 45; i++) {         // ~90s
        await sleep(2000);
        if (await isServerUp()) {
            onStatus("🐉 GhidraMCP pronto (porta 8080).");
            return { up: true, loaded: await programLoaded() };
        }
        if (i === 6) onStatus("🐉 Ghidra sta caricando la JVM…");
    }
    return { up: false, error: "Ghidra avviato ma il server GhidraMCP non risponde entro 90s. Verifica che il plugin GhidraMCPPlugin sia spuntato (File→Configure→Developer)." };
}

module.exports = { isServerUp, programLoaded, ensureReady, launchGhidra, findGhidraRun };
