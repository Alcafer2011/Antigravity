"use strict";

const vscode = require("vscode");
const fs = require("fs");
const path = require("path");

// AUTO-RIPARAZIONE: prima di caricare i moduli dell'estensione, ripristina quelli
// eventualmente corrotti da una copia sana (selfHeal usa solo moduli nativi).
try {
    const { verifyAndRepair, CRITICAL_FILES } = require("./src/selfHeal");
    verifyAndRepair({ srcDir: path.join(__dirname, "src"), files: CRITICAL_FILES, logger: console });
} catch (_) { /* selfHeal assente: si prosegue */ }

// ★ 2026-08-02 — NIENTE require di mobileServer qui. Non serviva piu' a nulla
// (MobileServer non e' mai istanziato dal 19/07: il server e' standalone), ma
// costava 1,4 s a ogni attivazione e avviava un SECONDO fileWatcher dentro
// l'extension host, duplicato di quello del server. Era il pannello "nero".
const { ServerClient } = require("./src/serverClient");

// L'estensione e il telefono usano LO STESSO server locale: il pannello di VS Code
// mostra (in un iframe) la stessa pagina web servita dal server → stessa grafica,
// stesse funzioni, stessa conversazione condivisa.

// Resta null: dal 2026-07-19 l'estensione NON avvia piu' un server proprio
// (moriva con VS Code e scollegava il telefono). Il guard in deactivate() rimane
// solo per sicurezza se qualcuno lo reintroducesse.
let inProcServer = null;
let client = null;         // ServerClient (per i comandi: modelli/stato/policy)
let cfg = { port: 8790, token: "" };
let readyPromise = null;

const consoleChannel = vscode.window.createOutputChannel("Antigravity Dev Console");
const logger = {
    log: (l, m, d) => consoleChannel.appendLine(`[${String(l).toUpperCase()}] ${m}` + (d ? " " + JSON.stringify(d) : "")),
    debug(m, d) { this.log("debug", m, d); }, info(m, d) { this.log("info", m, d); },
    warn(m, d) { this.log("warn", m, d); }, error(m, d) { this.log("error", m, d); }
};
process.on("uncaughtException", err => consoleChannel.appendLine(`[UNCAUGHT] ${err.message}\n${err.stack}`));
process.on("unhandledRejection", err => consoleChannel.appendLine(`[UNHANDLED] ${err}`));

// ---- .env (token/porta). Cerca in HOME e nella cartella estensione (quest'ultima
//      vince). Così il token sopravvive alla reinstallazione del VSIX (che non lo include).
function parseEnvFile(file) {
    const out = {};
    try {
        for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
            const s = line.trim();
            if (!s || s.startsWith("#")) continue;
            const eq = s.indexOf("="); if (eq < 0) continue;
            let v = s.slice(eq + 1).trim();
            if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
            out[s.slice(0, eq).trim()] = v;
        }
    } catch (_) {}
    return out;
}
function loadEnv(rootDir) {
    let home = ""; try { home = require("os").homedir(); } catch (_) {}
    return Object.assign(home ? parseEnvFile(path.join(home, ".env")) : {}, parseEnvFile(path.join(rootDir, ".env")));
}

function tailscaleIp() {
    try {
        for (const list of Object.values(require("os").networkInterfaces())) {
            for (const ni of list || []) if (ni.family === "IPv4" && !ni.internal && /^100\./.test(ni.address)) return ni.address;
        }
    } catch (_) {}
    return null;
}

// Garantisce che un server condiviso sia in ascolto; ritorna quando è raggiungibile.
// Legge porta/token dal .env (sincrono, pochi ms): serve PRIMA di qualunque attesa,
// così il pannello può disegnarsi subito invece di restare nero.
function loadCfg(context) {
    const env = loadEnv(context.extensionPath);
    cfg.port = parseInt(env.MOBILE_PORT || "8790", 10);
    cfg.token = env.MOBILE_TOKEN || "";
    client = new ServerClient({ port: cfg.port, token: cfg.token });
}

async function ensureServer(context) {
    if (!client) loadCfg(context);

    if (await client.ping()) return true;

    // ★ 2026-07-19 — NIENTE PIU' SERVER IN-PROCESS.
    //
    // PERCHE': il server in-process VIVE E MUORE con VS Code. Bastava chiudere
    // l'editor, fare "Reload Window" o un riavvio dell'extension host perche' il
    // server sparisse e il telefono restasse scollegato ("offline / irraggiungibile
    // da cellulare, molto spesso"). Peggio: mentre VS Code teneva la porta, il
    // watchdog di Startup non riusciva mai a subentrare e girava a vuoto —
    // 13.008 EADDRINUSE contro 112 avvii riusciti nel log. Quei 112 avvii sono
    // 112 cadute di connessione per il telefono. Il processo non e' MAI andato in
    // crash (zero eccezioni non gestite nel log): spariva e basta.
    //
    // ORA: il padrone della porta e' UNO SOLO, il server STANDALONE, che
    // sopravvive alla chiusura di VS Code e gira sempre dai sorgenti freschi di
    // ~/src. Se non risponde, lo si avvia STACCATO (detached) da qui e poi lo si
    // aspetta; l'estensione resta un semplice client con l'iframe.
    try {
        const { spawn } = require("child_process");
        const home = require("os").homedir();
        // ★ 2026-08-01 — PERCORSO CORRETTO. Puntava a ~/src/heal-and-run.js, cartella
        // che il riordino del 30/07 ha eliminato (tutto sta in ~/Antigravity). Il
        // fallback quindi non partiva MAI: a server spento il pannello restava vuoto
        // e "non rispondeva", con un solo warning nella Dev Console.
        // Ora si parte dalla cartella dell'estensione (che E' ~/Antigravity via junction).
        const candidati = [
            path.join(context.extensionPath, "src", "heal-and-run.js"),
            path.join(home, "Antigravity", "src", "heal-and-run.js"),
            path.join(home, "src", "heal-and-run.js")   // storico, pre-riordino
        ];
        const runner = candidati.find(p => fs.existsSync(p)) || candidati[0];
        if (fs.existsSync(runner)) {
            const child = spawn(process.execPath, [runner], {
                // radice del progetto (la cartella che contiene src/), non la home:
                // il server legge .env e node_modules da li'.
                cwd: path.dirname(path.dirname(runner)),
                detached: true,          // sopravvive alla morte dell'extension host
                stdio: "ignore",
                windowsHide: true
            });
            child.unref();
            logger.info("server standalone avviato (detached)");
        } else {
            logger.warn("heal-and-run.js non trovato in " + runner);
        }
    } catch (err) { logger.warn("avvio standalone fallito: " + err.message); }

    // attendi che risponda (~8s: lo standalone parte piu' lentamente dell'in-process)
    for (let i = 0; i < 16; i++) { if (await client.ping()) return true; await new Promise(r => setTimeout(r, 500)); }
    return false;
}

function activate(context) {
    loadCfg(context);
    readyPromise = ensureServer(context).catch(err => { logger.error("ensureServer", { message: err.message }); return false; });

    const provider = {
        async resolveWebviewView(webviewView) {
            const wv = webviewView.webview;
            wv.options = { enableScripts: true, localResourceRoots: [vscode.Uri.file(context.extensionPath)] };
            // ★ 2026-08-02 — SI DISEGNA SUBITO. Prima si aspettava readyPromise PRIMA
            // di scrivere l'HTML: finché il server non rispondeva il pannello restava
            // nero e indistinguibile da un guasto. Ora la pagina appare all'istante con
            // "collegamento in corso", e l'iframe viene agganciato quando il server c'è.
            // ★ 2026-07-19 — ANTI-CACHE. Il server manda già no-store, ma la webview
            // di VS Code riusava la pagina vecchia in memoria (URL identico = stessa
            // risorsa). Aggiungendo un parametro che cambia a ogni apertura, la
            // webview è COSTRETTA a riscaricare: si vede sempre la versione nuova.
            const serverUrl = `http://127.0.0.1:${cfg.port}/?t=${encodeURIComponent(cfg.token)}&v=${Date.now()}`;
            const nonce = require("crypto").randomBytes(16).toString("base64");
            const htmlPath = path.join(context.extensionPath, "interface.html");
            let html = fs.existsSync(htmlPath) ? fs.readFileSync(htmlPath, "utf8") : '<iframe src="${serverUrl}" style="border:0;width:100%;height:100vh"></iframe>';
            html = html.replace(/\$\{serverUrl\}/g, serverUrl).replace(/\$\{nonce\}/g, nonce);
            wv.html = html;

            // Il server è pronto? Allora aggancia l'iframe. Altrimenti mostra il perché.
            const ok = await readyPromise;
            try {
                wv.postMessage(ok
                    ? { tipo: "pronto", url: serverUrl }
                    : { tipo: "errore", porta: cfg.port, testo: "Il server Antigravity non risponde sulla porta " + cfg.port + "." });
            } catch (_) { /* pannello già chiuso */ }
        }
    };
    context.subscriptions.push(vscode.window.registerWebviewViewProvider("antigravityUnifiedChat", provider, {
        webviewOptions: { retainContextWhenHidden: true }
    }));

    context.subscriptions.push(vscode.commands.registerCommand("antigravity.discoverModels", async () => {
        try { const m = await client.models(); vscode.window.showInformationMessage(`Modelli locali: ${(m.models || []).length}`); }
        catch (_) { vscode.window.showWarningMessage("Server non raggiungibile."); }
    }));
    context.subscriptions.push(vscode.commands.registerCommand("antigravity.showStatus", async () => {
        try { const m = await client.models(); const r = m.roles || {}; vscode.window.showInformationMessage(`Agente: ${r.agente || "—"} | Coding: ${r.coding || "—"} | Reverse: ${r.reverse || "—"}`); }
        catch (_) { vscode.window.showWarningMessage("Server non raggiungibile."); }
    }));
    context.subscriptions.push(vscode.commands.registerCommand("antigravity.setPermissionPolicy", async () => {
        const pick = await vscode.window.showQuickPick([
            { label: "Chiedi prima di scrivere/eseguire", value: "ask-writes" },
            { label: "Totale autonomia (auto-allow)", value: "auto-allow" },
            { label: "Solo lettura", value: "read-only" }
        ], { placeHolder: "Autonomia della squadra" });
        if (pick && client) { await client.policy(pick.value); vscode.window.showInformationMessage("Politica permessi: " + pick.label); }
    }));
    context.subscriptions.push(vscode.commands.registerCommand("antigravity.toggleMobileServer", async () => {
        const ip = tailscaleIp() || "localhost";
        const url = `http://${ip}:${cfg.port}/?t=${cfg.token}`;
        const ok = client && await client.ping();
        const choice = await vscode.window.showInformationMessage(
            (ok ? "Server attivo. " : "⚠️ Server non raggiungibile. ") + "Apri sul telefono:\n" + url, "Copia URL");
        if (choice === "Copia URL") vscode.env.clipboard.writeText(url);
    }));

    // Tasto destro su un file in Explorer → analisi diretta nella chat.
    context.subscriptions.push(vscode.commands.registerCommand("antigravity.analyzeFile", async (uri) => {
        const fp = (uri && uri.fsPath) || (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri.fsPath);
        if (!fp) { vscode.window.showWarningMessage("Nessun file selezionato."); return; }
        await readyPromise;
        if (!client || !(await client.ping())) { vscode.window.showWarningMessage("Server Antigravity non raggiungibile."); return; }
        // Apre il pannello Antigravity e invia la richiesta di analisi.
        try { await vscode.commands.executeCommand("workbench.view.extension.antigravity-unified-container"); } catch (_) {}
        const p = fp.replace(/\\/g, "/");
        await client.send({ prompt: `Analizza il file ${p} e dimmi cos'è, cosa fa e cosa contiene di rilevante.`, mode: "reverse", provider: "local", channel: "normal" });
        vscode.window.showInformationMessage("Antigravity: analisi avviata su " + path.basename(fp));
    }));

    // Spegne i motori pesanti (ComfyUI, Ollama) per liberare la VRAM/RAM.
    context.subscriptions.push(vscode.commands.registerCommand("antigravity.stopEngines", async () => {
        const { exec } = require("child_process");
        // ComfyUI = python che serve la porta 8188; Ollama = ollama.exe (serve + runner).
        const ps = "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*8188*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; " +
            "Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue";
        exec("powershell -NoProfile -Command \"" + ps + "\"", () => {});
        vscode.window.showInformationMessage("Antigravity: motori spenti (ComfyUI + Ollama). Si riaccenderanno da soli al bisogno.");
    }));
}

async function deactivate() {
    if (client) { try { client.close(); } catch (_) {} client = null; }
    if (inProcServer) { try { inProcServer.stop(); } catch (_) {} inProcServer = null; }
}

module.exports = { activate, deactivate };
