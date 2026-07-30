#!/usr/bin/env node
"use strict";

/**
 * Hook PreToolUse per il provider Claude Code di Antigravity.
 *
 * Claude Code, in modalità headless, non può fermarsi a chiedere: allora chiede a
 * NOI. Prima di ogni scrittura/comando la CLI lancia questo script, che gira la
 * domanda al motore (ClaudeEngine) via HTTP locale; il motore la mostra come
 * approvazione inline nella chat (VS Code e telefono) e attende il tuo Approva/Nega.
 *
 * Sicurezza: FAIL-CLOSED. Se il motore non risponde, se manca il segreto, se va
 * storto qualsiasi cosa → si NEGA. Non si autorizza mai per errore.
 */

const http = require("http");

const URL_ = process.env.ANTIGRAVITY_APPROVAL_URL || "";
const SECRET = process.env.ANTIGRAVITY_APPROVAL_SECRET || "";

function decide(allow, reason) {
    process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: allow ? "allow" : "deny",
            permissionDecisionReason: reason
        }
    }));
    process.exit(0);
}

function ask(payload) {
    return new Promise((resolve) => {
        let u;
        try { u = new URL(URL_); } catch (_) { return resolve(false); }
        const body = JSON.stringify(payload);
        const req = http.request({
            host: u.hostname, port: u.port, path: u.pathname, method: "POST",
            headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
            timeout: 290000   // l'utente ha tempo di decidere (il timeout dell'hook è 300s)
        }, (res) => {
            let data = "";
            res.on("data", c => { data += c; });
            res.on("end", () => {
                try { resolve(!!JSON.parse(data).allow); } catch (_) { resolve(false); }
            });
        });
        req.on("timeout", () => { req.destroy(); resolve(false); });
        req.on("error", () => resolve(false));
        req.write(body);
        req.end();
    });
}

let input = "";
process.stdin.on("data", c => { input += c; });
process.stdin.on("end", async () => {
    if (!URL_ || !SECRET) return decide(false, "Antigravity: canale di approvazione assente → nego per sicurezza.");
    let ev = {};
    try { ev = JSON.parse(input || "{}"); } catch (_) { return decide(false, "Antigravity: evento hook illeggibile → nego."); }

    const allow = await ask({
        secret: SECRET,
        tool_name: ev.tool_name || "",
        tool_input: ev.tool_input || {},
        session_id: ev.session_id || ""
    });

    decide(allow, allow
        ? "Approvato dall'utente nella chat Antigravity."
        : "Negato dall'utente (o nessuna risposta) nella chat Antigravity.");
});
