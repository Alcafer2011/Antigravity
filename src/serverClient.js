"use strict";

/**
 * serverClient.js — client Node verso il server mobile (mobileServer.js).
 *
 * Serve a far diventare l'ESTENSIONE VS CODE un client dello STESSO server che
 * usa il telefono: così VS Code e telefono condividono la STESSA conversazione.
 * L'estensione gira nell'host Node (nessun vincolo CSP), quindi può aprire una
 * connessione SSE e fare POST verso http://localhost:8790 senza problemi.
 *
 * Eventi ricevuti (via onEvent): gli stessi che il server manda ai client —
 * history, userMessage, cleared, updateStatus, streamStart/Token/End,
 * addResponse, agentEvent, requestApproval, cloudUsage.
 */

const http = require("http");

class ServerClient {
    constructor({ host = "127.0.0.1", port = 8790, token = "" } = {}) {
        this.host = host;
        this.port = port;
        this.token = token;
        this._sse = null;
        this._onEvent = null;
        this._closed = false;
        this._reconnectTimer = null;
    }

    /** Il server risponde? (ping leggero su /models) */
    async ping() {
        try { await this._get("/models"); return true; } catch (_) { return false; }
    }

    /** Apre lo stream SSE e inoltra ogni messaggio a onEvent. Si riconnette da solo. */
    connect(onEvent) {
        this._onEvent = onEvent;
        this._closed = false;
        this._openSse();
    }

    _openSse() {
        if (this._closed) return;
        const req = http.request({
            host: this.host, port: this.port,
            path: "/events?t=" + encodeURIComponent(this.token),
            method: "GET", headers: { "Accept": "text/event-stream" }
        }, (res) => {
            if (res.statusCode !== 200) { res.resume(); return this._scheduleReconnect(); }
            res.setEncoding("utf8");
            let buf = "";
            res.on("data", chunk => {
                buf += chunk;
                let idx;
                while ((idx = buf.indexOf("\n\n")) >= 0) {
                    const block = buf.slice(0, idx);
                    buf = buf.slice(idx + 2);
                    for (const line of block.split("\n")) {
                        const s = line.trim();
                        if (!s.startsWith("data:")) continue;
                        const payload = s.slice(5).trim();
                        if (!payload) continue;
                        try { this._onEvent && this._onEvent(JSON.parse(payload)); } catch (_) {}
                    }
                }
            });
            res.on("end", () => this._scheduleReconnect());
            res.on("error", () => this._scheduleReconnect());
        });
        req.on("error", () => this._scheduleReconnect());
        req.end();
        this._sse = req;
    }

    _scheduleReconnect() {
        if (this._closed || this._reconnectTimer) return;
        this._reconnectTimer = setTimeout(() => { this._reconnectTimer = null; this._openSse(); }, 1500);
    }

    close() {
        this._closed = true;
        if (this._reconnectTimer) { clearTimeout(this._reconnectTimer); this._reconnectTimer = null; }
        if (this._sse) { try { this._sse.destroy(); } catch (_) {} this._sse = null; }
    }

    // ---- Azioni (POST) -----------------------------------------------------
    send(payload) { return this._post("/send", payload); }
    stop() { return this._post("/stop", {}); }
    approve(id, approved) { return this._post("/approve", { id, approved }); }
    policy(policy) { return this._post("/policy", { policy }); }
    clear() { return this._post("/clear", {}); }
    models() { return this._get("/models"); }

    // ---- HTTP helpers ------------------------------------------------------
    _get(pathname) {
        return new Promise((resolve, reject) => {
            const req = http.get({
                host: this.host, port: this.port,
                path: pathname + (pathname.includes("?") ? "&" : "?") + "t=" + encodeURIComponent(this.token),
                timeout: 8000
            }, (res) => {
                let d = "";
                res.on("data", c => d += c);
                res.on("end", () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } });
            });
            req.on("timeout", () => req.destroy(new Error("timeout")));
            req.on("error", reject);
        });
    }

    _post(pathname, obj) {
        const body = JSON.stringify(obj || {});
        return new Promise((resolve, reject) => {
            const req = http.request({
                host: this.host, port: this.port,
                path: pathname + "?t=" + encodeURIComponent(this.token),
                method: "POST",
                headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
                timeout: 8000
            }, (res) => {
                let d = "";
                res.on("data", c => d += c);
                res.on("end", () => { try { resolve(d ? JSON.parse(d) : {}); } catch (_) { resolve({}); } });
            });
            req.on("timeout", () => req.destroy(new Error("timeout")));
            req.on("error", reject);
            req.write(body);
            req.end();
        });
    }
}

module.exports = { ServerClient };
