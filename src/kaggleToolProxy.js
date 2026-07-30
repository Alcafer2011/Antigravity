"use strict";

const http = require("http");
const https = require("https");

/**
 * kaggleToolProxy — piccolo proxy OpenAI-compatibile DAVANTI all'endpoint Kaggle
 * (ngrok) che serve i modelli abliterated.
 *
 * PERCHÉ ESISTE: i modelli abliterated (Qwen2.5-Coder su Kaggle) NON riempiono il
 * campo nativo `tool_calls`: mettono la chiamata come blocco ```json (o <tools>{…})
 * dentro `content`. Antigravity ha già il fix lato client (nativeAgent), ma HERMES
 * è un pacchetto chiuso che si aspetta i `tool_calls` nativi → con quel modello non
 * esegue nulla. Questo proxy fa "la nostra ReAct" al posto suo: intercetta la
 * risposta e, se la tool-call è nel testo, la TRADUCE nel formato `tool_calls`
 * standard che Hermes sa già eseguire. Zero modifiche a Hermes, sopravvive ai suoi
 * aggiornamenti.
 *
 * Hermes punta a http://127.0.0.1:PORT/v1 (invece che direttamente a ngrok).
 * Il proxy forza le richieste con `tools` a NON-streaming verso l'upstream (serve la
 * risposta completa per tradurre) e poi risponde al client nel formato che ha chiesto
 * (SSE se stream=true, JSON altrimenti).
 */

const UPSTREAM_HOST = "paving-preschool-facelift.ngrok-free.dev";
const DEFAULT_PORT = 8791;

let _server = null;
let _port = 0;

/**
 * Estrae una tool-call da un `content` testuale. Riconosce ```json / <tools> e le
 * forme {name,arguments|args|parameters} · {action,args} · {tool,…} · {function:{…}}.
 * Ritorna {name, args} oppure null. (Gemella di nativeAgent._toolCallFromContent.)
 */
function extractToolCall(content) {
    let s = String(content || "").trim();
    if (!s) return null;
    // togli i wrapper ```json … ``` e <tools> … </tools>
    let m = s.match(/```(?:json)?\s*([\s\S]*?)```/i) || s.match(/```(?:json)?\s*([\s\S]*)$/i);
    if (m) s = m[1];
    m = s.match(/<tools?>\s*([\s\S]*?)<\/tools?>/i) || s.match(/<tools?>\s*([\s\S]*)$/i);
    if (m) s = m[1];
    s = s.trim();
    const start = s.indexOf("{");
    if (start < 0) return null;
    // primo oggetto JSON bilanciato
    let depth = 0, inStr = false, esc = false, obj = null;
    for (let i = start; i < s.length; i++) {
        const c = s[i];
        if (inStr) { if (esc) esc = false; else if (c === "\\") esc = true; else if (c === '"') inStr = false; }
        else if (c === '"') inStr = true;
        else if (c === "{") depth++;
        else if (c === "}") { depth--; if (depth === 0) { try { obj = JSON.parse(s.slice(start, i + 1)); } catch (_) { obj = null; } break; } }
    }
    if (!obj || typeof obj !== "object") return null;
    if (obj.final != null || obj.answer != null) return null; // è una risposta, non una call
    let name = obj.name || obj.action || obj.tool || obj.tool_name;
    let args = obj.arguments != null ? obj.arguments : (obj.args != null ? obj.args : obj.parameters);
    if (!name && obj.function && typeof obj.function === "object") { name = obj.function.name; args = obj.function.arguments; }
    if (!name) return null;
    if (typeof args === "string") { try { args = JSON.parse(args); } catch (_) { args = {}; } }
    if (args == null || typeof args !== "object") args = {};
    return { name: String(name), args };
}

/** Traduce una risposta OpenAI non-streaming: tool-call nel testo → tool_calls nativi. */
function translate(json) {
    try {
        const choice = json && json.choices && json.choices[0];
        if (!choice) return json;
        const msg = choice.message || {};
        if (msg.tool_calls && msg.tool_calls.length) return json; // già nativa: non toccare
        const tc = extractToolCall(msg.content || "");
        if (tc && tc.name) {
            msg.tool_calls = [{
                id: "call_" + Math.random().toString(36).slice(2, 10),
                type: "function",
                function: { name: tc.name, arguments: JSON.stringify(tc.args || {}) }
            }];
            msg.content = null;                 // il contenuto è ora nella tool_call
            choice.message = msg;
            choice.finish_reason = "tool_calls";
        }
    } catch (_) { /* in caso di dubbio: risposta invariata */ }
    return json;
}

/** Rimanda una risposta (eventualmente tradotta) come stream SSE con un solo delta. */
function emitSSE(res, json) {
    res.writeHead(200, { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-cache", "Connection": "keep-alive" });
    const choice = (json.choices && json.choices[0]) || { message: {}, finish_reason: "stop" };
    const msg = choice.message || {};
    const delta = {};
    if (msg.role) delta.role = msg.role;
    if (msg.content != null) delta.content = msg.content;
    if (msg.tool_calls) delta.tool_calls = msg.tool_calls.map((t, i) => Object.assign({ index: i }, t));
    const chunk = { id: json.id || "chatcmpl-proxy", object: "chat.completion.chunk", created: json.created || Math.floor(Date.now() / 1000), model: json.model, choices: [{ index: 0, delta, finish_reason: choice.finish_reason || "stop" }] };
    res.write("data: " + JSON.stringify(chunk) + "\n\n");
    if (json.usage) res.write("data: " + JSON.stringify({ id: chunk.id, object: "chat.completion.chunk", choices: [], usage: json.usage }) + "\n\n");
    res.write("data: [DONE]\n\n");
    res.end();
}

function forward(req, res, bodyBuf) {
    let payload = null;
    try { payload = JSON.parse(bodyBuf.toString("utf8") || "null"); } catch (_) { payload = null; }
    const isChat = /\/chat\/completions\b/.test(req.url || "");
    const wantsTools = !!(payload && Array.isArray(payload.tools) && payload.tools.length);
    const clientWantsStream = !!(payload && payload.stream);

    // Per tradurre serve la risposta COMPLETA: con i tool forziamo non-stream upstream.
    if (payload && wantsTools && payload.stream) payload.stream = false;
    const outBody = payload != null ? Buffer.from(JSON.stringify(payload)) : bodyBuf;

    const headers = Object.assign({}, req.headers, {
        host: UPSTREAM_HOST,
        "content-length": Buffer.byteLength(outBody),
        "ngrok-skip-browser-warning": "true"
    });
    delete headers["accept-encoding"]; // niente gzip da decomprimere

    const up = https.request({ host: UPSTREAM_HOST, path: req.url, method: req.method, headers, timeout: 120000 }, (r) => {
        const data = [];
        r.on("data", c => data.push(c));
        r.on("end", () => {
            const raw = Buffer.concat(data).toString("utf8");
            const ct = r.headers["content-type"] || "";
            // Solo le chat CON tool vanno tradotte; il resto passa invariato.
            if (isChat && wantsTools && (r.statusCode || 200) < 400 && /json/i.test(ct)) {
                let json = null;
                try { json = JSON.parse(raw); } catch (_) {}
                if (json) {
                    const out = translate(json);
                    if (clientWantsStream) return emitSSE(res, out);
                    const s = JSON.stringify(out);
                    res.writeHead(r.statusCode || 200, { "Content-Type": "application/json; charset=utf-8", "Content-Length": Buffer.byteLength(s) });
                    return res.end(s);
                }
            }
            res.writeHead(r.statusCode || 200, { "Content-Type": ct || "application/json" });
            res.end(raw);
        });
    });
    up.on("timeout", () => up.destroy(new Error("timeout upstream")));
    up.on("error", (e) => { try { res.writeHead(502, { "Content-Type": "application/json" }); } catch (_) {} res.end(JSON.stringify({ error: { message: "kaggleToolProxy upstream: " + e.message } })); });
    up.end(outBody);
}

/**
 * Avvia il proxy in-process (una sola volta). Ritorna la porta.
 * Idempotente: se già avviato, o se la porta è occupata (già su), non fa nulla.
 */
function ensureRunning(port, logger) {
    port = port || DEFAULT_PORT;
    logger = logger || console;
    if (_server) return _port || port;
    _server = http.createServer((req, res) => {
        const chunks = [];
        req.on("data", c => chunks.push(c));
        req.on("end", () => { try { forward(req, res, Buffer.concat(chunks)); } catch (e) { try { res.writeHead(500); } catch (_) {} res.end("proxy error"); } });
    });
    _server.on("error", (e) => {
        if (e.code === "EADDRINUSE") { _port = port; (logger.log || console.log).call(logger, "[kaggleToolProxy] porta " + port + " già in uso: assumo sia già attivo"); }
        else { _server = null; (logger.error || console.error).call(logger, "[kaggleToolProxy] " + e.message); }
    });
    _server.listen(port, "127.0.0.1", () => { _port = port; (logger.log || console.log).call(logger, "[kaggleToolProxy] traduzione tool-call attiva su http://127.0.0.1:" + port + "/v1"); });
    return port;
}

module.exports = { ensureRunning, translate, extractToolCall, DEFAULT_PORT };
