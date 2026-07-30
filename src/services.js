"use strict";

const http = require("http");
const { spawn } = require("child_process");

/**
 * Servizi locali che devono ACCENDERSI DA SOLI.
 *
 * L'utente non deve aprire niente a mano: se Ollama è spento quando serve, lo
 * avviamo noi. (ComfyUI fa lo stesso, ma se lo gestisce comfyClient.js, che sa
 * anche dove sta il suo venv.)
 */

const sleep = ms => new Promise(r => setTimeout(r, ms));

function ping(port, path_ = "/") {
    return new Promise(resolve => {
        const r = http.request({ host: "127.0.0.1", port, path: path_, method: "GET", timeout: 1500 },
            res => { res.resume(); resolve(true); });
        r.on("timeout", () => { r.destroy(); resolve(false); });
        r.on("error", () => resolve(false));
        r.end();
    });
}

/** True se Ollama risponde su 11434. */
async function ollamaUp() { return ping(11434, "/api/tags"); }

/**
 * Avvia `ollama serve` se è spento e aspetta che risponda.
 * @returns {Promise<boolean>} true se alla fine è su.
 */
async function ensureOllama(onStatus = () => {}) {
    if (await ollamaUp()) return true;

    onStatus("💻 Ollama è spento: lo avvio…");
    // ★ 2026-07-19 — FIX: prima chiamava spawn("ollama") dal PATH, ma su questa
    // macchina Ollama NON è nel PATH (sta in AppData\Local\Programs\Ollama) →
    // lo spawn falliva e Hermes/locale davano "non sono riuscito ad avviarlo".
    // Ora si prova il percorso REALE dell'exe, poi "ollama" nel PATH come ripiego.
    const path = require("path");
    const os = require("os");
    const candidates = [
        path.join(os.homedir(), "AppData", "Local", "Programs", "Ollama", "ollama.exe"),
        "ollama"
    ];
    let started = false;
    for (const exe of candidates) {
        try {
            // detached+unref: sopravvive alla nostra richiesta e resta acceso.
            const p = spawn(exe, ["serve"], { detached: true, stdio: "ignore", windowsHide: true });
            p.unref();
            started = true;
            break;
        } catch (_) { /* prova il prossimo candidato */ }
    }
    if (!started) return false;

    for (let i = 0; i < 20; i++) {
        await sleep(1000);
        if (await ollamaUp()) { onStatus("💻 Ollama pronto."); return true; }
    }
    return false;
}

module.exports = { ensureOllama, ollamaUp };
