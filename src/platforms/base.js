"use strict";

/**
 * platforms/base — le cose che ogni driver di piattaforma rifà uguali:
 * leggere/scrivere il .env, sondare un endpoint OpenAI-compatibile, lanciare un
 * comando, ricordare lo stato (URL dell'endpoint, ultimo avvio) su disco.
 *
 * ★ 2026-07-30 — Nasce estraendo il pattern già collaudato di kaggleWaker
 * (isUp / ensureUp / shutdown / quota). Il primo driver costa, i successivi no:
 * qui sta la parte che NON si riscrive ogni volta.
 *
 * CONTRATTO DI UN DRIVER (vedi modal.js come esempio completo):
 *   id, nome, campiRichiesti[]   -> il wizard chiede solo questi
 *   configurato()  -> {ok, mancanti[]}
 *   isUp()         -> Promise<boolean>
 *   accendi(o)     -> Promise<{ok, url?, messaggio}>       o.onStato(testo)
 *   spegni()       -> Promise<{ok, messaggio}>
 *   quota()        -> Promise<{fonte:"api"|"dichiarato", ...}>
 *   endpoint()     -> string|null  (base URL OpenAI-compatibile)
 */

const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");
const { spawn } = require("child_process");

const SRC = path.join(__dirname, "..");

// ---- .env --------------------------------------------------------------------

function envPath() {
    try { return require("../envFile").envFilePath(); }
    catch (_) { return path.join(SRC, "..", ".env"); }
}

/** Legge una chiave dal .env del progetto (o dall'ambiente). */
function env(nome) {
    try {
        const txt = fs.readFileSync(envPath(), "utf8");
        const m = txt.match(new RegExp("^\\s*" + nome + "\\s*=\\s*(.+?)\\s*$", "m"));
        if (m) return m[1].replace(/^["']|["']$/g, "").trim();
    } catch (_) {}
    return (process.env[nome] || "").trim() || null;
}

/**
 * Scrive/aggiorna una chiave nel .env, conservando tutto il resto e facendo
 * prima una copia (il .env contiene chiavi che non si rigenerano in un click).
 */
function setEnv(nome, valore) {
    const f = envPath();
    let txt = "";
    try { txt = fs.readFileSync(f, "utf8"); } catch (_) {}
    try { if (txt) fs.writeFileSync(f + ".bak", txt, "utf8"); } catch (_) {}
    const riga = nome + "=" + String(valore);
    const re = new RegExp("^\\s*" + nome + "\\s*=.*$", "m");
    txt = re.test(txt) ? txt.replace(re, riga) : (txt.replace(/\s*$/, "") + "\n" + riga + "\n");
    fs.writeFileSync(f, txt, "utf8");
    return { ok: true, file: f, chiave: nome };
}

// ---- stato persistente per piattaforma ---------------------------------------

function statoFile(id) { return path.join(SRC, ".platform-" + id + ".json"); }

function leggiStato(id) {
    try { return JSON.parse(fs.readFileSync(statoFile(id), "utf8")); } catch (_) { return {}; }
}
function salvaStato(id, patch) {
    const s = Object.assign(leggiStato(id), patch, { aggiornato: new Date().toISOString() });
    try { fs.writeFileSync(statoFile(id), JSON.stringify(s, null, 2), "utf8"); } catch (_) {}
    return s;
}

// ---- sonda endpoint -----------------------------------------------------------

/**
 * True se l'endpoint risponde da server OpenAI-compatibile (/v1/models con "data").
 * Stesso criterio di kaggleWaker: "risponde" non basta, deve rispondere da modello.
 */
function sonda(url, timeoutMs = 8000) {
    return new Promise((resolve) => {
        let u;
        try { u = new URL(url.replace(/\/+$/, "") + "/v1/models"); } catch (_) { return resolve(false); }
        const mod = u.protocol === "http:" ? http : https;
        const req = mod.get({
            host: u.hostname, port: u.port || undefined, path: u.pathname,
            timeout: timeoutMs, headers: { "ngrok-skip-browser-warning": "true" }
        }, (res) => {
            let d = "";
            res.on("data", c => { if (d.length < 65536) d += c; });
            res.on("end", () => resolve(res.statusCode === 200 && /"data"\s*:/.test(d)));
        });
        req.on("timeout", () => { req.destroy(); resolve(false); });
        req.on("error", () => resolve(false));
    });
}

/** Aspetta che l'endpoint salga, riferendo ogni tanto. */
async function attendi(url, o = {}) {
    const max = o.maxWaitMs || 12 * 60 * 1000;
    const onStato = o.onStato || (() => {});
    const t0 = Date.now();
    let tick = 0;
    while (Date.now() - t0 < max) {
        if (await sonda(url)) return true;
        await new Promise(r => setTimeout(r, 10000));
        if (++tick % 3 === 0) onStato("🟡 In avvio… (" + Math.round((Date.now() - t0) / 1000) + "s)");
    }
    return false;
}

// ---- comandi -----------------------------------------------------------------

const PY_CANDIDATI = ["C:\\Program Files\\Python312\\python.exe", "python", "python3"];
function python() {
    for (const p of PY_CANDIDATI) { try { if (p === "python" || p === "python3" || fs.existsSync(p)) return p; } catch (_) {} }
    return "python";
}

/** Esegue un comando raccogliendo stdout+stderr. Non lancia mai: ritorna l'esito. */
function esegui(cmd, args, o = {}) {
    return new Promise((resolve) => {
        let p;
        try {
            p = spawn(cmd, args, {
                env: Object.assign({}, process.env, o.env || {}),
                cwd: o.cwd, windowsHide: true
            });
        } catch (e) { return resolve({ ok: false, out: e.message, code: -1 }); }
        let out = "";
        const acc = d => { out += d; if (out.length > 200000) out = out.slice(-100000); if (o.onRiga) o.onRiga(String(d)); };
        p.stdout.on("data", acc); p.stderr.on("data", acc);
        const t = setTimeout(() => { try { p.kill(); } catch (_) {} }, o.timeoutMs || 15 * 60 * 1000);
        p.on("close", (code) => { clearTimeout(t); resolve({ ok: code === 0, code, out }); });
        p.on("error", (e) => { clearTimeout(t); resolve({ ok: false, code: -1, out: e.message }); });
    });
}

/** Una accensione alla volta per piattaforma (come la guardia _waking di Kaggle). */
const _inCorso = {};
function unaAllaVolta(id, fn) {
    if (_inCorso[id]) return _inCorso[id];
    _inCorso[id] = Promise.resolve().then(fn).finally(() => { delete _inCorso[id]; });
    return _inCorso[id];
}

module.exports = { env, setEnv, envPath, leggiStato, salvaStato, sonda, attendi, esegui, python, unaAllaVolta, SRC };
