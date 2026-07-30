"use strict";

const { spawn } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");

/**
 * HermesAcpClient — pilota Hermes Agent (Nous Research) via ACP
 * (Agent Client Protocol) su subprocess stdio.
 *
 * Hermes fa da "squadra autonoma": esegue un loop di tool reale con
 * sub-agenti (delegation), memoria, skills e terminale, guidato da modelli
 * locali UNCENSORED (via Ollama). Questo client:
 *   - lancia `hermes-acp` col giusto HERMES_HOME
 *   - parla JSON-RPC 2.0 delimitato da newline (come il server ACP di Hermes)
 *   - gestisce lo streaming (session/update) e le richieste del server
 *     (session/request_permission, fs/read_text_file, fs/write_text_file)
 *
 * Politica permessi di default: AUTO-ALLOW (autonomia piena richiesta
 * dall'utente), con ogni azione notificata alla UI cosi resta visibile.
 */

const HERMES_HOME = process.env.HERMES_HOME || path.join(os.homedir(), "AppData", "Local", "hermes");
const PROTOCOL_VERSION = 1;

function findHermesAcp() {
    const scripts = path.join(HERMES_HOME, "hermes-agent", "venv", "Scripts");
    for (const name of ["hermes-acp.exe", "hermes-acp"]) {
        const p = path.join(scripts, name);
        if (fs.existsSync(p)) return { cmd: p, args: [] };
    }
    for (const name of ["python.exe", "python"]) {
        const py = path.join(scripts, name);
        if (fs.existsSync(py)) return { cmd: py, args: ["-m", "acp_adapter.entry"] };
    }
    return { cmd: "hermes-acp", args: [] };
}

class HermesAcpClient {
    /**
     * @param {object} opts
     *   cwd: cartella di lavoro dell'agente (workspace)
     *   model: nome modello Ollama da usare (uncensored + tools)
     *   logger: console-like
     *   onEvent: (evt) => void  — eventi di streaming per la UI
     *   permissionPolicy: 'auto-allow' | 'ask-writes' | 'read-only'
     *     - auto-allow : tutto senza chiedere
     *     - ask-writes : letture automatiche; modifiche/comandi chiedono OK (default)
     *     - read-only  : letture ok, modifiche/comandi negati
     *   onPermission: async ({toolCall, options, kind}) => optionId|null  (per 'ask-writes')
     *   onWriteApproval: async ({path, content}) => bool  (gate su fs/write_text_file)
     */
    constructor(opts = {}) {
        this.cwd = opts.cwd || process.cwd();
        this.model = opts.model || null;
        this.logger = opts.logger || console;
        this.onEvent = opts.onEvent || (() => {});
        this.permissionPolicy = opts.permissionPolicy || "ask-writes";
        this.onPermission = opts.onPermission || null;
        this.onWriteApproval = opts.onWriteApproval || null;

        this.proc = null;
        this.sessionId = null;
        this._buf = "";
        this._nextId = 1;
        this._pending = new Map();
        this._started = false;
        this._initResult = null;
    }

    async start() {
        if (this._started) return;
        const { cmd, args } = findHermesAcp();
        const env = Object.assign({}, process.env, { HERMES_HOME });
        if (this.model) {
            env.HERMES_MODEL = this.model;
        }
        this.logger.log && this.logger.log(`[HermesACP] avvio: ${cmd} ${args.join(" ")} (cwd=${this.cwd})`);
        this.proc = spawn(cmd, args, {
            cwd: this.cwd,
            env,
            stdio: ["pipe", "pipe", "pipe"],
            windowsHide: true
        });

        this.proc.stdout.on("data", (d) => this._onStdout(d));
        this.proc.stderr.on("data", (d) => {
            const s = d.toString("utf8");
            this.logger.log && this.logger.log("[HermesACP:stderr] " + s.trimEnd());
        });
        this.proc.on("exit", (code) => {
            this._started = false;
            for (const { reject } of this._pending.values()) reject(new Error(`hermes-acp uscito (code ${code})`));
            this._pending.clear();
            this.onEvent({ type: "exit", code });
        });
        this.proc.on("error", (err) => {
            this.onEvent({ type: "error", message: `Impossibile avviare hermes-acp: ${err.message}` });
        });

        this._started = true;

        this._initResult = await this._request("initialize", {
            protocolVersion: PROTOCOL_VERSION,
            clientCapabilities: {
                fs: { readTextFile: true, writeTextFile: true }
            }
        });

        const s = await this._request("session/new", {
            cwd: this.cwd,
            mcpServers: []
        });
        this.sessionId = s && (s.sessionId || s.session_id);
        this.onEvent({ type: "ready", sessionId: this.sessionId, agent: this._initResult });
        return this._initResult;
    }

    async prompt(text) {
        if (!this._started) await this.start();
        return this._request("session/prompt", {
            sessionId: this.sessionId,
            prompt: [{ type: "text", text }]
        });
    }

    async cancel() {
        if (this._started && this.sessionId) {
            try { await this._notify("session/cancel", { sessionId: this.sessionId }); } catch (_) {}
        }
    }

    stop() {
        if (this.proc) {
            try { this.proc.kill(); } catch (_) {}
            this.proc = null;
        }
        this._started = false;
    }

    _send(obj) {
        if (!this.proc || !this.proc.stdin.writable) return;
        this.proc.stdin.write(JSON.stringify(obj) + "\n");
    }

    _request(method, params) {
        const id = this._nextId++;
        this._send({ jsonrpc: "2.0", id, method, params });
        return new Promise((resolve, reject) => {
            this._pending.set(id, { resolve, reject });
        });
    }

    _notify(method, params) {
        this._send({ jsonrpc: "2.0", method, params });
    }

    _respond(id, result) {
        this._send({ jsonrpc: "2.0", id, result });
    }

    _onStdout(data) {
        this._buf += data.toString("utf8");
        let idx;
        while ((idx = this._buf.indexOf("\n")) >= 0) {
            const line = this._buf.slice(0, idx).trim();
            this._buf = this._buf.slice(idx + 1);
            if (!line) continue;
            let msg;
            try { msg = JSON.parse(line); }
            catch (_) { continue; }
            this._dispatch(msg);
        }
    }

    async _dispatch(msg) {
        if (msg.id !== undefined && (msg.result !== undefined || msg.error !== undefined)) {
            const p = this._pending.get(msg.id);
            if (p) {
                this._pending.delete(msg.id);
                if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
                else p.resolve(msg.result);
            }
            return;
        }

        const method = msg.method;
        if (!method) return;

        if (method === "session/update") {
            this._handleSessionUpdate(msg.params || {});
            return;
        }

        if (msg.id !== undefined) {
            try {
                const result = await this._handleServerRequest(method, msg.params || {});
                this._respond(msg.id, result);
            } catch (err) {
                this._send({ jsonrpc: "2.0", id: msg.id, error: { code: -32000, message: err.message } });
            }
        }
    }

    _handleSessionUpdate(params) {
        const u = params.update || params;
        const kind = u.sessionUpdate || u.type;
        switch (kind) {
            case "agent_message_chunk":
                this.onEvent({ type: "message", text: this._textOf(u.content) });
                break;
            case "agent_thought_chunk":
                this.onEvent({ type: "thought", text: this._textOf(u.content) });
                break;
            case "tool_call":
                this.onEvent({ type: "tool", status: "start", title: u.title || (u.rawInput && u.rawInput.name) || "tool", kind: u.kind, id: u.toolCallId });
                break;
            case "tool_call_update":
                this.onEvent({ type: "tool", status: u.status || "update", title: u.title, id: u.toolCallId, content: u.content });
                break;
            case "plan":
                this.onEvent({ type: "plan", entries: u.entries || [] });
                break;
            case "user_message_chunk":
                break;
            default:
                this.onEvent({ type: "update", kind, raw: u });
        }
    }

    async _handleServerRequest(method, params) {
        switch (method) {
            case "session/request_permission": {
                const optionId = await this._decidePermission(params);
                if (!optionId) return { outcome: { outcome: "cancelled" } };
                return { outcome: { outcome: "selected", optionId } };
            }
            case "fs/read_text_file": {
                const content = fs.readFileSync(params.path, "utf8");
                if (params.line || params.limit) {
                    const lines = content.split("\n");
                    const start = (params.line || 1) - 1;
                    const end = params.limit ? start + params.limit : lines.length;
                    return { content: lines.slice(start, end).join("\n") };
                }
                return { content };
            }
            case "fs/write_text_file": {
                // Gate di scrittura (azione mutante).
                if (this.permissionPolicy === "read-only") {
                    throw new Error("scrittura negata: modalità sola lettura");
                }
                if (this.permissionPolicy === "ask-writes" && this.onWriteApproval) {
                    const ok = await this.onWriteApproval({ path: params.path, content: params.content });
                    if (!ok) throw new Error("scrittura rifiutata dall'utente");
                }
                fs.mkdirSync(path.dirname(params.path), { recursive: true });
                fs.writeFileSync(params.path, params.content, "utf8");
                this.onEvent({ type: "tool", status: "completed", title: `scrittura ${params.path}`, kind: "edit" });
                return null;
            }
            default:
                throw new Error("metodo non supportato: " + method);
        }
    }

    // Classifica un tool_call come sola-lettura o mutante (modifica/comando).
    _isReadOnly(toolCall) {
        const kind = (toolCall && toolCall.kind || "").toLowerCase();
        if (["read", "search", "think", "fetch"].includes(kind)) return true;
        if (["edit", "delete", "move", "execute"].includes(kind)) return false;
        // Euristica sul titolo se il kind manca.
        const title = (toolCall && toolCall.title || "").toLowerCase();
        if (/write|edit|modif|delete|rimuov|remove|exec|run|comando|command|install|crea|create|sposta|move/.test(title)) return false;
        return true; // in dubbio, trattalo come lettura (le scritture reali passano comunque da fs/write o request_permission mutante)
    }

    async _decidePermission(params) {
        const options = params.options || [];
        const toolCall = params.toolCall || {};
        const readOnly = this._isReadOnly(toolCall);
        this.onEvent({ type: "permission", title: toolCall.title || "azione", options, readOnly });

        const pickAllow = () => {
            const allow = options.find(o => /allow|yes|approve|once/i.test((o.optionId || "") + " " + (o.name || "") + " " + (o.kind || "")))
                || options.find(o => o.kind === "allow_once" || o.kind === "allow_always")
                || options[0];
            return allow && (allow.optionId || allow.id);
        };
        const pickReject = () => {
            const rej = options.find(o => /reject|deny|no|cancel/i.test((o.optionId || "") + " " + (o.name || "") + " " + (o.kind || "")))
                || options.find(o => o.kind === "reject_once" || o.kind === "reject_always");
            return rej ? (rej.optionId || rej.id) : null;
        };

        // read-only: consenti letture, nega mutazioni.
        if (this.permissionPolicy === "read-only") {
            return readOnly ? pickAllow() : (pickReject() || null);
        }
        // auto-allow: sempre.
        if (this.permissionPolicy === "auto-allow") {
            return pickAllow();
        }
        // ask-writes (default): letture automatiche, mutazioni chiedono.
        if (readOnly) return pickAllow();
        if (this.onPermission) {
            const chosen = await this.onPermission({ toolCall, options, kind: toolCall.kind });
            if (chosen === false || chosen === null) return pickReject() || null; // negato
            if (typeof chosen === "string") return chosen;
        }
        return pickAllow();
    }

    _textOf(content) {
        if (!content) return "";
        if (typeof content === "string") return content;
        if (Array.isArray(content)) return content.map(c => this._textOf(c)).join("");
        if (content.type === "text") return content.text || "";
        if (content.text) return content.text;
        return "";
    }
}

module.exports = { HermesAcpClient, findHermesAcp, HERMES_HOME };
