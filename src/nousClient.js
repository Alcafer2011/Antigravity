"use strict";

/**
 * nousClient — integrazione DIRETTA con il Nous Portal (opzione B).
 *
 * Perché esiste: Antigravity voleva i modelli FREE di Nous (poolside/laguna-*,
 * tencent/hy3, stepfun/step-3.7-flash) nei suoi menu, usabili con l'agente
 * nativo, SENZA dover aprire la CLI di Hermes ogni volta. Nous però usa un
 * token OAuth che scade ~ogni ora. ★2026-07-23 — MODELLO SINGLE-WRITER (concordato
 * con Hermes stesso): il refresh_token di Nous è ROTANTE, quindi se DUE processi lo
 * ruotano si sloggano a vicenda. Perciò qui NON ruotiamo MAI: leggiamo in SOLA LETTURA
 * l'access_token da auth.json, e quando è vicino a scadere facciamo un "NUDGE" a Hermes
 * (eseguiamo la SUA funzione resolve_nous_runtime_credentials nel suo venv) che rinnova
 * con la sua logica, in modo concurrent-safe, e persiste auth.json. Poi rileggiamo.
 * Così Hermes è l'UNICO writer del refresh_token e non si slogga mai per colpa nostra.
 *
 * Non dipende da Hermes in runtime per l'inferenza: è un client HTTP locale, veloce.
 * Se il refresh_token non c'è o scade, getModels() torna [] e chat() lancia
 * un errore chiaro (così l'orchestratore può fare fallback), mai un 401 muto.
 *
 * Modelli esposti: SOLO i :free verificati (nessun credito richiesto). Gli
 * altri modelli del portale (hermes-4-405b, qwen3-coder, …) danno 404
 * "requires available credits" → esclusi di proposito.
 *
 * NOTE SUI MODELLI DI RAGIONAMENTO: le Laguna (e altri coder Nous) scrivono
 * il pensiero in `reasoning` e la RISPOSTA in `content`. Se chiedi pochi token
 * si fermano nel ragionamento e `content` arriva null → non è un errore, è che
 * servono più token. chat() gestisce entrambi i casi e usa un max_tokens alto
 * di default così la risposta vera arriva.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const https = require("https");
const http = require("http");
const { URL } = require("url");
const { spawn } = require("child_process");

const HERMES_HOME = process.env.HERMES_HOME || path.join(os.homedir(), "AppData", "Local", "hermes");

// Modelli :free verificati (rispondono senza crediti). Aggiungine altri qui.
// Mantieni la forma esatta restituita da /v1/models (org/nome:free).
const FREE_MODELS = [
    { id: "poolside/laguna-s-2.1:free", label: "🜂 Poolside Laguna-S 2.1 (free)", coder: true, reasoning: true },
    { id: "poolside/laguna-xs-2.1:free", label: "🜂 Poolside Laguna-XS 2.1 (free)", coder: true, reasoning: true },
    { id: "tencent/hy3:free", label: "🜂 Tencent HY3 (free)", coder: false, reasoning: false },
    { id: "stepfun/step-3.7-flash:free", label: "🜂 StepFun Step-3.7-Flash (free)", coder: false, reasoning: true }
];

const REFRESH_ENDPOINT_PATH = "/api/oauth/token";
// inference_base_url di Nous è già ".../v1" (OpenAI base). Il path chat è quindi
// base + "/chat/completions" = ".../v1/chat/completions".
const DEFAULT_CHAT_PATH = "/chat/completions";

// --- Persistenza token condivisa con Hermes (ANTISLOGGO) --------------------
// Il refresh_token di Nous è ROTANTE e rileva il riuso: se lo usi due volte,
// il server lo revoca ("Refresh session has been revoked") e Hermes si slogga.
// Quindi dopo ogni refresh riscriviamo il token ruotato in auth.json (lo stesso
// file che Hermes legge), così i due processi condividono lo stato e nessuno
// riusa un token già consumato. Un lock file serializza le scritture con Hermes.
const AUTH_PATH = path.join(HERMES_HOME, "auth.json");
const AUTH_LOCK = AUTH_PATH + ".nouslock";

function _withLock(fn, tries = 20) {
    // lock cooperativo basato su file (timeout ~5s)
    for (let i = 0; i < tries; i++) {
        try {
            fs.writeFileSync(AUTH_LOCK, String(process.pid), { flag: "wx" });
            try { return fn(); }
            finally { try { fs.unlinkSync(AUTH_LOCK); } catch (_) {} }
        } catch (e) {
            if (e.code === "EEXIST") { // lock occupato (da Hermes): riprova
                const age = (() => { try { return Date.now() - fs.statSync(AUTH_LOCK).mtimeMs; } catch (_) { return 9999; } })();
                if (age > 8000) { try { fs.unlinkSync(AUTH_LOCK); } catch (_) {} } // lock marcio
                const t = Date.now(); while (Date.now() - t < 250) {} // spin 250ms
                continue;
            }
            throw e;
        }
    }
    return fn(); // ultimo tentativo senza lock
}

/** Aggiorna i blocchi nous in auth.json col token ruotato (stesso formato Hermes). */
function _persistNousToken(json) {
    if (!json || !json.access_token) return;
    _withLock(() => {
        let store;
        try { store = JSON.parse(fs.readFileSync(AUTH_PATH, "utf8")); } catch (_) { return; }
        const now = new Date().toISOString();
        const exp = (json.expires_in && Number(json.expires_in)) || 3000;
        const expiresAt = new Date(Date.now() + exp * 1000).toISOString();
        const patch = (blk) => {
            if (!blk) return;
            blk.access_token = json.access_token;
            if (json.refresh_token) blk.refresh_token = json.refresh_token;
            if (json.token_type) blk.token_type = json.token_type;
            if (json.scope) blk.scope = json.scope;
            if (json.expires_in) blk.expires_in = json.expires_in;
            blk.expires_at = expiresAt;
            blk.obtained_at = now;
            if (json.agent_key) blk.agent_key = json.agent_key;
            if (json.agent_key_id !== undefined) blk.agent_key_id = json.agent_key_id;
            if (json.agent_key_expires_at) blk.agent_key_expires_at = json.agent_key_expires_at;
            if (json.agent_key_expires_in) blk.agent_key_expires_in = json.agent_key_expires_in;
            if (json.agent_key_reused !== undefined) blk.agent_key_reused = json.agent_key_reused;
        };
        if (store.providers && store.providers.nous) patch(store.providers.nous);
        if (Array.isArray(store.credential_pool && store.credential_pool.nous)) {
            store.credential_pool.nous.forEach(patch);
        }
        // scrittura atomica (tmp + rename) per non corrompere il file
        const tmp = AUTH_PATH + ".tmp";
        fs.writeFileSync(tmp, JSON.stringify(store, null, 2));
        fs.renameSync(tmp, AUTH_PATH);
    });
}

/** Estrae un messaggio d'errore leggibile dalla risposta (gestisce {error:{message}}). */
function _readNousCreds() {
    try {
        const p = path.join(HERMES_HOME, "auth.json");
        const j = JSON.parse(fs.readFileSync(p, "utf8"));
        const n = j && j.providers && j.providers.nous;
        if (!n || !n.refresh_token) return null;
        return {
            portal: (n.portal_base_url || "https://portal.nousresearch.com").replace(/\/+$/, ""),
            base: (n.inference_base_url || "https://inference-api.nousresearch.com").replace(/\/+$/, ""),
            refresh_token: n.refresh_token,
            client_id: n.client_id || "hermes-cli"
        };
    } catch (_) { return null; }
}

/** HTTP(S) POST JSON, ritorna {status, json, text}. */
function _postJson(urlStr, payload, headers, timeoutMs) {
    return new Promise((resolve, reject) => {
        let u;
        try { u = new URL(urlStr); } catch (e) { return reject(e); }
        const body = Buffer.from(JSON.stringify(payload));
        const lib = u.protocol === "http:" ? http : https;
        const req = lib.request({
            hostname: u.hostname,
            port: u.port || (u.protocol === "https:" ? 443 : 80),
            path: u.pathname + u.search,
            method: "POST",
            headers: Object.assign({
                "Content-Type": "application/json",
                "Content-Length": body.length,
                "Accept": "application/json"
            }, headers || {})
        }, (res) => {
            let data = "";
            res.on("data", (c) => { data += c; });
            res.on("end", () => {
                let json = null;
                try { json = JSON.parse(data); } catch (_) {}
                resolve({ status: res.statusCode, json, text: data });
            });
        });
        req.on("error", reject);
        if (timeoutMs) req.setTimeout(timeoutMs, () => req.destroy(new Error("timeout")));
        req.write(body);
        req.end();
    });
}

/** Estrae un messaggio d'errore leggibile dalla risposta (gestisce {error:{message}}). */
function _errText(r) {
    if (r.json && r.json.error && r.json.error.message) return String(r.json.error.message);
    if (r.json && r.json.message) return String(r.json.message);
    if (r.json && r.json.error_description) return String(r.json.error_description);
    if (r.text) return r.text.slice(0, 200);
    return "HTTP " + (r.status || "?");
}

class NousClient {
    /** opts.logger opzionale. */
    constructor(opts = {}) {
        this.logger = opts.logger || console;
        this._creds = _readNousCreds();
        this._token = null;
        this._tokenExpiry = 0; // epoch ms; rinnova se < now + 60s
        this._tokenPromise = null; // deduplica refresh concorrenti
    }

    /** true se abbiamo le credenziali Nous (refresh_token) in auth.json. */
    available() { return !!this._creds; }

    /**
     * ★ 2026-07-23 — SINGLE-WRITER (concordato con Hermes stesso). NON ruotiamo il
     * refresh_token: leggiamo l'access_token da auth.json (read-only). Se è entro lo
     * skew (~120s) o scaduto, facciamo un NUDGE a Hermes — eseguiamo la SUA funzione
     * resolve_nous_runtime_credentials nel suo venv, che rinnova (concurrent-safe) e
     * persiste auth.json — poi RILEGGIAMO il token fresco. Antigravity non scrive MAI
     * auth.json né usa il refresh_token: così Hermes non si slogga. NON reintrodurre
     * un refresh OAuth diretto qui: era la causa del logout di Hermes.
     */
    async _ensureToken() {
        const SKEW_MS = 120_000;
        const read = () => { try { return JSON.parse(fs.readFileSync(AUTH_PATH, "utf8")).providers.nous; } catch (_) { return null; } };
        const stale = (n) => !n || !n.access_token || (n.expires_at && !isNaN(Date.parse(n.expires_at)) && Date.now() > Date.parse(n.expires_at) - SKEW_MS);
        let nous = read();
        if (!stale(nous)) return nous.access_token;
        // NUDGE: chiedi a HERMES di rinnovare (è lui l'unico writer). Al massimo una
        // volta ogni 15s, per non tempestarlo se arrivano molte richieste ravvicinate.
        if (!this._lastNudge || Date.now() - this._lastNudge > 15_000) {
            this._lastNudge = Date.now();
            await this._nudgeHermesRefresh();
            nous = read();
        }
        if (!stale(nous)) return nous.access_token;
        throw new Error("Nous non disponibile: access_token scaduto e refresh via Hermes non riuscito. Usa Hermes una volta, o verifica il login Nous (hermes portal login).");
    }

    /**
     * NUDGE a Hermes: esegue la SUA funzione di refresh nel suo venv Python. Con
     * force_refresh=False rinnova SOLO se serve (rispetta lo skew), in modo
     * concurrent-safe, e persiste auth.json. Noi NON ruotiamo nulla: è Hermes l'unico
     * writer del refresh_token. Timeout 30s; se il venv non c'è, no-op.
     */
    _nudgeHermesRefresh() {
        return new Promise((resolve) => {
            const py = path.join(HERMES_HOME, "hermes-agent", "venv", "Scripts", "python.exe");
            if (!fs.existsSync(py)) return resolve(false);
            const code = "from hermes_cli.auth import resolve_nous_runtime_credentials as f; f()";
            let done = false;
            let p;
            try { p = spawn(py, ["-c", code], { env: Object.assign({}, process.env, { HERMES_HOME }), windowsHide: true }); }
            catch (_) { return resolve(false); }
            let err = "";
            if (p.stderr) p.stderr.on("data", d => err += d);
            const t = setTimeout(() => { if (!done) { try { p.kill(); } catch (_) {} } }, 30_000);
            p.on("close", (c) => { done = true; clearTimeout(t); if (c !== 0 && this.logger && this.logger.log) this.logger.log("[NousClient] nudge Hermes refresh exit " + c + " " + err.slice(0, 120)); resolve(c === 0); });
            p.on("error", () => { done = true; clearTimeout(t); resolve(false); });
        });
    }

    /** Voci per il menu modelli del provider "nous". */
    getModelChoices() {
        if (!this.available()) return [];
        return FREE_MODELS.map((m) => ({ value: "nous::" + m.id, label: m.label, coder: !!m.coder, reasoning: !!m.reasoning }));
    }

    /** Lista modelli per la catalogazione API (stesso formato di Hermes/cloud). */
    getModels() { return this.getModelChoices(); }

    /** Risolve "nous::id" → id pulito. */
    _modelId(value) {
        const s = String(value || "");
        return s.startsWith("nous::") ? s.slice("nous::".length) : s;
    }

    /**
     * Chat semplice (no tool). Ritorna il testo (string).
     * @param value  "nous::<id>" o "<id>"
     * @param messages  array OpenAI [{role,content}]
     * @param o { temperature, maxTokens, signal }
     */
    async chat(value, messages, { temperature = 0.7, maxTokens = 2048, signal = null } = {}) {
        const token = await this._ensureToken();
        const model = this._modelId(value);
        const base = this._creds.base;
        const r = await _postJson(base + DEFAULT_CHAT_PATH, {
            model,
            messages,
            temperature,
            max_tokens: maxTokens,
            stream: false
        }, { "Authorization": "Bearer " + token }, 90_000);
        if (r.status !== 200 || !r.json || !r.json.choices) {
            throw new Error("Nous chat " + model + " fallita: " + _errText(r).slice(0, 200));
        }
        const msg = (r.json.choices[0] && r.json.choices[0].message) || {};
        // I modelli di ragionamento mettono la risposta in content; se è null
        // (ancora in reasoning) usiamo il reasoning come fallback leggibile.
        let content = msg.content;
        if (content == null) content = (msg.reasoning_content || msg.reasoning || "");
        // Se anche così è vuoto ma c'è reasoning, segnaliamo che servono più token.
        if (!String(content).trim() && (msg.reasoning_content || msg.reasoning)) {
            content = "(modello di ragionamento: aumenta max_tokens per la risposta completa)";
        }
        return String(content || "");
    }

    /**
     * Chat con tool-calling (stile OpenAI). Ritorna { content, tool_calls }.
     * Se il modello NON emette tool_calls nativi, tool_calls = [] (l'agente
     * nativo di Antigravity gestisce il caso via _toolCallFromContent).
     */
    async chatTools(value, messages, tools, { temperature = 0.2, maxTokens = 2048, signal = null } = {}) {
        const token = await this._ensureToken();
        const model = this._modelId(value);
        const base = this._creds.base;
        const r = await _postJson(base + DEFAULT_CHAT_PATH, {
            model,
            messages,
            temperature,
            max_tokens: maxTokens,
            tools,
            tool_choice: "auto",
            stream: false
        }, { "Authorization": "Bearer " + token }, 90_000);
        if (r.status !== 200 || !r.json || !r.json.choices) {
            throw new Error("Nous chatTools " + model + " fallita: " + _errText(r).slice(0, 200));
        }
        const msg = (r.json.choices[0] && r.json.choices[0].message) || {};
        let content = msg.content;
        if (content == null) content = (msg.reasoning_content || msg.reasoning || "");
        return { content: String(content || ""), tool_calls: msg.tool_calls || [] };
    }
}

module.exports = { NousClient, FREE_MODELS, HERMES_HOME };
