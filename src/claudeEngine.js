"use strict";

const { spawn } = require("child_process");
const http = require("http");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

/**
 * ClaudeEngine — Claude Code come PROVIDER della chat di Antigravity.
 *
 * Non è un'altra estensione né una copia: lancia la CLI `claude` già installata
 * sul PC in modalità headless (`-p --output-format stream-json`) e traduce il suo
 * flusso di eventi nel NOSTRO protocollo (streamToken / tool-card / piano TODO /
 * approvazioni). Usa l'abbonamento Claude Code esistente: nessuna chiave API.
 *
 * Cosa arriva in chat (telefono compreso, la pagina è la stessa):
 *   - testo in streaming (deltas dei messaggi parziali);
 *   - ogni strumento usato da Claude (Read/Edit/Bash/...) come tool-card;
 *   - la sua TODO list (tool TodoWrite) nel pannello Piano;
 *   - i LIMITI DI UTILIZZO (evento rate_limit_event: % usata, tipo finestra,
 *     quando si azzera) e il costo/token del turno.
 *
 * Permessi — la politica della UI viene applicata così:
 *   read-only  : Claude riceve solo gli strumenti di lettura (non può scrivere).
 *   ask-writes : tutti gli strumenti, ma un hook PreToolUse blocca scritture e
 *                comandi finché non li approvi TU dalla chat (claudeHook.js).
 *   auto-allow : nessun blocco (bypassPermissions).
 */

const READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "TodoWrite"];
// Strumenti che NON possono partire senza il tuo via libera in modalità "chiedi".
const GATED_TOOLS = "Edit|Write|MultiEdit|NotebookEdit|Bash|KillShell|WebFetch";

class ClaudeEngine {
    constructor(logger = console, opts = {}) {
        this.logger = logger;
        this.cliPath = opts.cliPath || this._findCli();
        this.hookPath = path.join(__dirname, "claudeHook.js");
        this.mcpPath = path.join(__dirname, "mcpServer.js");   // i NOSTRI strumenti, prestati a Claude
        this.sessions = new Map();   // conversationId -> session_id di Claude
        this.lastLimit = null;       // ultimo rate_limit_event visto
        this.lastResult = null;      // costo/token dell'ultimo turno
        this._proc = null;
        this._approvalServer = null;
    }

    /** La CLI c'è? Se no, il provider resta nascosto nella UI. */
    available() { return !!this.cliPath; }

    _findCli() {
        const candidates = [
            process.env.CLAUDE_CLI_PATH,
            path.join(process.env.APPDATA || "", "npm", "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe"),
            path.join(os.homedir(), "AppData", "Roaming", "npm", "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe"),
            path.join(os.homedir(), ".local", "bin", "claude"),
            "/usr/local/bin/claude"
        ].filter(Boolean);
        for (const c of candidates) {
            try { if (fs.existsSync(c)) return c; } catch (_) { /* ignora */ }
        }
        return null;
    }

    /** Modelli selezionabili dalla UI (alias della CLI: sempre l'ultimo di quella famiglia). */
    getModelChoices() {
        return [
            { value: "auto", label: "Claude: predefinito" },
            { value: "opus", label: "🧠 Opus (il più capace)" },
            { value: "sonnet", label: "⚖️ Sonnet (equilibrato)" },
            { value: "haiku", label: "⚡ Haiku (veloce, poco costoso)" }
        ];
    }

    /** Dimentica la sessione di una chat (dopo "svuota"/"nuova chat"): riparte pulita. */
    forgetSession(conversationId) { this.sessions.delete(conversationId || "default"); }

    /**
     * ★ 2026-09-01 — IL PONTE COL TELEFONO. Elenca le conversazioni di Claude Code
     * salvate su disco, così dal telefono puoi RIPRENDERE il filo lasciato al PC
     * (non solo aprirne uno nuovo). Ogni conversazione è un file .jsonl dentro
     * ~/.claude/projects/<progetto>/: il nome del file È l'id da passare a --resume.
     *
     * Per non leggere file da megabyte interi, di ciascuno si legge solo la TESTA
     * (i primi ~48 KB): lì stanno già il cwd e il primo messaggio, che bastano per
     * titolo, data e progetto. Il conteggio messaggi è una stima dalla dimensione.
     * @returns {Array<{id,title,cwd,project,ts,mtime,sizeKB}>} recenti per prime
     */
    listSessions({ limit = 60 } = {}) {
        const base = path.join(os.homedir(), ".claude", "projects");
        let progetti = [];
        try { progetti = fs.readdirSync(base); } catch (_) { return []; }
        const out = [];
        for (const prog of progetti) {
            const dir = path.join(base, prog);
            let files = [];
            try { files = fs.readdirSync(dir).filter(f => f.endsWith(".jsonl")); } catch (_) { continue; }
            for (const f of files) {
                const full = path.join(dir, f);
                let st;
                try { st = fs.statSync(full); } catch (_) { continue; }
                if (!st.size) continue;   // sessione vuota: saltala
                const info = this._peekSession(full);
                out.push({
                    id: f.replace(/\.jsonl$/, ""),
                    title: info.title || "(senza titolo)",
                    cwd: info.cwd || null,
                    project: prog,
                    ts: info.ts || st.mtime.toISOString(),
                    mtime: st.mtimeMs,
                    sizeKB: Math.round(st.size / 1024)
                });
            }
        }
        out.sort((a, b) => b.mtime - a.mtime);
        return out.slice(0, limit);
    }

    /** Legge la testa di un .jsonl e ne ricava cwd, primo messaggio utente, data. */
    _peekSession(full) {
        let testa = "";
        try {
            const fd = fs.openSync(full, "r");
            const buf = Buffer.alloc(49152);           // ~48 KB bastano per la testa
            const n = fs.readSync(fd, buf, 0, buf.length, 0);
            fs.closeSync(fd);
            testa = buf.slice(0, n).toString("utf8");
        } catch (_) { return {}; }
        let cwd = null, title = null, ts = null;
        for (const riga of testa.split("\n")) {
            if (!riga.trim()) continue;
            let j; try { j = JSON.parse(riga); } catch (_) { continue; }   // ultima riga tronca: ignorala
            if (!cwd && j.cwd) cwd = j.cwd;
            if (!ts && j.timestamp) ts = j.timestamp;
            if (!title && j.type === "user" && j.message) {
                const c = j.message.content;
                let t = typeof c === "string" ? c : (Array.isArray(c) ? ((c.find(x => x && x.type === "text") || {}).text || "") : "");
                t = String(t).replace(/\s+/g, " ").trim();
                // Salta i messaggi-strumento (tool_result) e le note di sistema.
                if (t && !/^<[a-z-]+>/i.test(t) && !/^Caveat:|^\[Request interrupted/.test(t)) title = t.slice(0, 80);
            }
            if (cwd && title && ts) break;
        }
        return { cwd, title, ts };
    }

    /**
     * Prepara la ripresa di una conversazione salvata: al prossimo messaggio di
     * questa chat, Claude riparte da QUEL filo (--resume) invece che da zero.
     * Il cwd va abbinato: le sessioni sono legate alla cartella in cui sono nate,
     * e --resume le cerca lì. Chi chiama passa quel cwd al prossimo chat().
     */
    primeResume(conversationId, sessionId) {
        if (sessionId) this.sessions.set(conversationId || "default", sessionId);
    }

    /** Ultimo stato dei limiti d'uso, pronto per la barra della UI. */
    getLimit() { return this.lastLimit; }

    stop() {
        if (this._proc) { try { this._proc.kill(); } catch (_) { /* già morto */ } }
    }

    /**
     * Un turno di conversazione.
     * @param {string} prompt
     * @param {object} o { cwd, model, policy, conversationId, onToken, onEvent, onLimit, askApproval, signal }
     * @returns {Promise<{text:string, sessionId:string, cost:number, usage:object}>}
     */
    async chat(prompt, o = {}) {
        if (!this.cliPath) throw new Error("CLI di Claude Code non trovata. Installa: npm i -g @anthropic-ai/claude-code");

        const convId = o.conversationId || "default";
        const policy = o.policy || "ask-writes";
        const onToken = o.onToken || (() => {});
        const onEvent = o.onEvent || (() => {});
        const onLimit = o.onLimit || (() => {});

        const args = ["-p", prompt, "--output-format", "stream-json", "--verbose", "--include-partial-messages"];

        const prev = this.sessions.get(convId);
        if (prev) args.push("--resume", prev);
        if (o.model && o.model !== "auto") args.push("--model", o.model);

        // La cassetta degli attrezzi di Antigravity, prestata a Claude via MCP:
        // generate_image (ComfyUI locale) e analyze_binary (toolchain reverse).
        // Così Claude lavora con gli STESSI strumenti della squadra locale.
        if (fs.existsSync(this.mcpPath)) {
            args.push("--mcp-config", JSON.stringify({
                mcpServers: { antigravity: { command: process.execPath, args: [this.mcpPath] } }
            }));
        }

        // --- permessi ---------------------------------------------------------
        const env = Object.assign({}, process.env);
        if (policy === "read-only") {
            args.push("--tools", READ_ONLY_TOOLS.join(","));
            args.push("--permission-mode", "bypassPermissions"); // niente da chiedere: non può scrivere
        } else if (policy === "auto-allow") {
            args.push("--permission-mode", "bypassPermissions");
        } else {
            // "chiedi prima di scrivere": il cancello è il NOSTRO hook, che chiede
            // a te dalla chat. Claude non deve bloccare per conto suo (non potrebbe
            // fare domande in headless), quindi la decisione passa tutta di lì.
            args.push("--permission-mode", "bypassPermissions");
            const gate = await this._startApprovalServer(o.askApproval);
            env.ANTIGRAVITY_APPROVAL_URL = gate.url;
            env.ANTIGRAVITY_APPROVAL_SECRET = gate.secret;
            args.push("--settings", JSON.stringify({
                hooks: {
                    PreToolUse: [{
                        matcher: GATED_TOOLS,
                        hooks: [{ type: "command", command: `node "${this.hookPath}"`, timeout: 300 }]
                    }]
                }
            }));
        }

        const cwd = o.cwd && fs.existsSync(o.cwd) ? o.cwd : os.homedir();

        return new Promise((resolve, reject) => {
            const proc = spawn(this.cliPath, args, { cwd, env, windowsHide: true });
            this._proc = proc;

            const tools = new Map();   // tool_use_id -> {title, kind}
            let text = "";             // testo composto dai delta in streaming
            let finalText = "";        // rete di sicurezza: il testo intero nel "result"
            let sessionId = prev || "";
            let result = null;
            let stderr = "";
            let buf = "";

            const finish = (err) => {
                this._proc = null;
                this._stopApprovalServer();
                if (err) return reject(err);
                // Se i delta non sono arrivati (CLI vecchia / streaming assente),
                // il testo c'è comunque nel messaggio finale: mandalo tutto insieme.
                if (!text && finalText) { text = finalText; onToken(finalText); }
                resolve({
                    text,
                    sessionId,
                    cost: (result && result.total_cost_usd) || 0,
                    usage: (result && result.usage) || null,
                    limit: this.lastLimit
                });
            };

            proc.stdout.on("data", (chunk) => {
                buf += chunk.toString("utf8");
                let i;
                while ((i = buf.indexOf("\n")) >= 0) {
                    const line = buf.slice(0, i).trim();
                    buf = buf.slice(i + 1);
                    if (!line) continue;
                    let ev;
                    try { ev = JSON.parse(line); } catch (_) { continue; } // riga parziale/rumore
                    try {
                        const t = this._onEvent(ev, { tools, onToken, onEvent, onLimit });
                        if (t.text) text += t.text;
                        if (t.finalText) finalText = t.finalText;
                        if (t.sessionId) { sessionId = t.sessionId; this.sessions.set(convId, sessionId); }
                        if (t.result) result = t.result;
                    } catch (e) {
                        this.logger.error && this.logger.error("[ClaudeEngine] evento:", e.message);
                    }
                }
            });

            proc.stderr.on("data", c => { stderr += c.toString("utf8"); });

            proc.on("error", (e) => finish(new Error("Avvio CLI Claude fallito: " + e.message)));
            proc.on("close", (code) => {
                if (code !== 0 && !text) {
                    // Sessione non più riprendibile → riparti pulito al prossimo turno.
                    if (/No conversation found|session/i.test(stderr)) this.sessions.delete(convId);
                    return finish(new Error(`Claude CLI uscita ${code}: ${(stderr || "").slice(0, 400) || "nessun dettaglio"}`));
                }
                finish(null);
            });

            if (o.signal) {
                o.signal.addEventListener("abort", () => { try { proc.kill(); } catch (_) {} });
            }
        });
    }

    /** Traduce UN evento stream-json della CLI nel nostro protocollo. */
    _onEvent(ev, { tools, onToken, onEvent, onLimit }) {
        const out = {};

        if (ev.type === "system" && ev.subtype === "init") {
            out.sessionId = ev.session_id;
            onEvent({ type: "status", text: `🤖 Claude ${this._modelLabel(ev.model)} · ${(ev.tools || []).length} strumenti` });
            return out;
        }

        // Testo token-per-token (arriva solo con --include-partial-messages).
        if (ev.type === "stream_event") {
            const e = ev.event || {};
            if (e.type === "content_block_delta") {
                const d = e.delta || {};
                if (d.type === "text_delta" && d.text) { onToken(d.text); out.text = d.text; }
                else if (d.type === "thinking_delta" && d.thinking) onEvent({ type: "status", text: "💭 ragiona…" });
            }
            return out;
        }

        // Messaggio dell'assistente: qui prendiamo SOLO i tool_use (il testo è già
        // arrivato come delta: prenderlo di nuovo lo duplicherebbe).
        if (ev.type === "assistant") {
            for (const b of ((ev.message && ev.message.content) || [])) {
                if (b.type !== "tool_use") continue;
                if (b.name === "TodoWrite") {                       // la sua TODO list → pannello Piano
                    const entries = ((b.input && b.input.todos) || []).map(t => ({
                        text: t.content || t.activeForm || "",
                        status: t.status === "completed" ? "done" : (t.status === "in_progress" ? "doing" : "todo")
                    }));
                    onEvent({ type: "plan", entries });
                    continue;
                }
                const meta = { title: this._toolTitle(b.name, b.input), kind: this._toolKind(b.name) };
                tools.set(b.id, meta);
                onEvent({ type: "tool", id: b.id, status: "running", title: meta.title, kind: meta.kind });
            }
            return out;
        }

        // Risultato di uno strumento → chiude la tool-card.
        if (ev.type === "user") {
            for (const b of ((ev.message && ev.message.content) || [])) {
                if (b.type !== "tool_result") continue;
                const meta = tools.get(b.tool_use_id) || { title: "strumento", kind: "read" };
                onEvent({
                    type: "tool", id: b.tool_use_id,
                    status: b.is_error ? "error" : "completed",
                    title: meta.title, kind: meta.kind,
                    content: this._resultText(b.content)
                });
                tools.delete(b.tool_use_id);
            }
            return out;
        }

        // ★ Limiti di utilizzo dell'abbonamento (come li mostra Claude Code).
        if (ev.type === "rate_limit_event" && ev.rate_limit_info) {
            this.lastLimit = this._limit(ev.rate_limit_info);
            onLimit(this.lastLimit);
            return out;
        }

        if (ev.type === "result") {
            out.result = ev;
            this.lastResult = { cost: ev.total_cost_usd || 0, usage: ev.usage || null, ms: ev.duration_ms || 0 };
            // Se lo streaming dei deltas non fosse disponibile, il testo finale è qui.
            if (!ev.is_error && ev.result && typeof ev.result === "string") out.finalText = ev.result;
            if (ev.is_error) onEvent({ type: "status", text: "⚠️ Claude ha chiuso con errore: " + (ev.subtype || "") });
            return out;
        }

        return out;
    }

    /** rate_limit_info grezzo → oggetto pronto per la barra della UI. */
    _limit(i) {
        const tipo = i.rateLimitType === "seven_day" ? "settimanale"
            : i.rateLimitType === "five_hour" ? "5 ore"
                : (i.rateLimitType || "utilizzo");
        const pct = Math.round((i.utilization || 0) * 100);
        return {
            type: i.rateLimitType || "",
            label: tipo,
            percent: pct,
            status: i.status || "",                       // allowed | allowed_warning | rejected
            overage: !!i.isUsingOverage,
            resetsAt: (i.resetsAt || 0) * 1000,           // epoch ms
            resetsHuman: i.resetsAt ? new Date(i.resetsAt * 1000).toLocaleString("it-IT", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : ""
        };
    }

    _modelLabel(m) { return String(m || "").replace(/^claude-/, "").replace(/-\d+$/, ""); }

    _toolKind(name) {
        if (/^(Edit|Write|MultiEdit|NotebookEdit)$/.test(name)) return "edit";
        if (/^(Bash|KillShell|BashOutput)$/.test(name)) return "execute";
        return "read";
    }

    _toolTitle(name, input) {
        const i = input || {};
        if (i.file_path) return `${name} ${this._short(i.file_path)}`;
        if (i.command) return `${name}: ${String(i.command).slice(0, 80)}`;
        if (i.pattern) return `${name} "${String(i.pattern).slice(0, 50)}"`;
        if (i.url) return `${name} ${String(i.url).slice(0, 60)}`;
        if (i.prompt) return `${name}: ${String(i.prompt).slice(0, 60)}`;
        return name;
    }
    _short(p) { return String(p).split(/[\\/]/).slice(-2).join("/"); }

    _resultText(content) {
        if (typeof content === "string") return content.slice(0, 4000);
        if (Array.isArray(content)) {
            return content.map(c => (c && c.type === "text" ? c.text : "")).join("\n").slice(0, 4000);
        }
        return "";
    }

    // ---- Cancello dei permessi (usato dall'hook PreToolUse) -------------------
    //
    // Server HTTP effimero su 127.0.0.1: l'hook ci scrive "Claude vuole fare X",
    // noi chiediamo a TE dalla chat e rispondiamo allow/deny. Vive quanto il turno.

    _startApprovalServer(askApproval) {
        if (this._approvalServer) return Promise.resolve(this._approvalServer.info);
        const secret = crypto.randomBytes(16).toString("hex");

        return new Promise((resolve, reject) => {
            const srv = http.createServer((req, res) => {
                let body = "";
                req.on("data", c => { body += c; });
                req.on("end", async () => {
                    let j = {};
                    try { j = JSON.parse(body || "{}"); } catch (_) { /* corpo illeggibile */ }
                    if (j.secret !== secret) { res.writeHead(403).end("{}"); return; }
                    let allow = false;
                    try {
                        if (typeof askApproval === "function") {
                            const title = this._toolTitle(j.tool_name || "strumento", j.tool_input);
                            allow = await askApproval(`Claude vuole eseguire: ${title}`, this._detail(j.tool_input));
                        }
                    } catch (_) { allow = false; }   // in dubbio: si nega
                    res.writeHead(200, { "Content-Type": "application/json" });
                    res.end(JSON.stringify({ allow: !!allow }));
                });
            });
            srv.on("error", reject);
            srv.listen(0, "127.0.0.1", () => {
                const info = { url: `http://127.0.0.1:${srv.address().port}/ask`, secret };
                this._approvalServer = { srv, info };
                resolve(info);
            });
        });
    }

    _stopApprovalServer() {
        if (!this._approvalServer) return;
        try { this._approvalServer.srv.close(); } catch (_) { /* già chiuso */ }
        this._approvalServer = null;
    }

    _detail(input) {
        try {
            const s = JSON.stringify(input || {}, null, 2);
            return s.length > 1500 ? s.slice(0, 1500) + "\n…" : s;
        } catch (_) { return ""; }
    }
}

module.exports = { ClaudeEngine };
