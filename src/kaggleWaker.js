"use strict";

const https = require("https");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

let registry = null;
try { registry = require("./providerRegistry"); } catch (_) {}

/**
 * kaggleWaker — accende il notebook Kaggle ON-DEMAND.
 *
 * Il notebook (alcafer2011/notebook39aa15083b) gira su GPU Kaggle e serve i modelli
 * abliterated via Ollama + tunnel ngrok (dominio fisso). Tenerlo sempre acceso brucia
 * la quota GPU (30h/settimana), quindi lo si vuole avviare SOLO quando serve.
 *
 * ensureUp(): se l'endpoint è già su → ok. Altrimenti fa `kaggle kernels push` (avvia
 * un nuovo run del kernel) e ASPETTA che l'endpoint risponda (il boot + il download dei
 * modelli richiede qualche minuto). Una sola accensione alla volta (guardia _waking).
 *
 * Il token API sta nel .env dell'app (KAGGLE_API_TOKEN, gitignored). La CLI kaggle è
 * installata nell'ambiente Python del sistema.
 */

const KAGGLE_HOST = (registry && registry.byId && registry.byId("kaggle") && registry.byId("kaggle").host)
    || "paving-preschool-facelift.ngrok-free.dev";
// Due notebook: 14B (Qwen2.5-Coder-14B) e big (Qwen3-Coder-30B-MoE). Stessa slug
// su Kaggle, cartella sorgente diversa su disco.
const NB_SLUG = "alcafer2011/notebook39aa15083b";
const SIZE_DIR = { 14: path.join(__dirname, "kaggle-notebook"), 30: path.join(__dirname, "kaggle-notebook-big") };

function sizeDir(size) {
    const s = String(size || "14") === "30" ? 30 : 14;
    return { dir: SIZE_DIR[s], slug: NB_SLUG, size: s };
}

/** True se l'endpoint Kaggle risponde con la lista modelli. */
const PY_CANDIDATES = ["C:\\Program Files\\Python312\\python.exe", "python", "python3"];
function pythonExe() {
    for (const p of PY_CANDIDATES) { try { if (p === "python" || p === "python3" || fs.existsSync(p)) return p; } catch (_) {} }
    return "python";
}

/** True se l'endpoint Kaggle risponde con la lista modelli. */
function isUp(timeoutMs = 8000) {
    return new Promise((resolve) => {
        const req = https.get({ host: KAGGLE_HOST, path: "/v1/models", timeout: timeoutMs, headers: { "ngrok-skip-browser-warning": "true" } }, (res) => {
            let d = ""; res.on("data", c => d += c);
            res.on("end", () => resolve(res.statusCode === 200 && /"data"\s*:/.test(d)));
        });
        req.on("timeout", () => { req.destroy(); resolve(false); });
        req.on("error", () => resolve(false));
    });
}

/** Legge una variabile dal .env dell'app (../.env rispetto a src) o dall'ambiente. */
function envVar(name) {
    try {
        const env = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
        const m = env.match(new RegExp("^\\s*" + name + "\\s*=\\s*(.+?)\\s*$", "m"));
        if (m) return m[1].replace(/^["']|["']$/g, "").trim();
    } catch (_) {}
    return (process.env[name] || "").trim();
}
function token() { return envVar("KAGGLE_API_TOKEN"); }

/**
 * ★ 2026-07-30 — Il token Kaggle può essere PRESENTE ma RIFIUTATO (scaduto o
 * revocato). In quel caso la CLI stampa il suo "auth help" ed esce: prima non lo
 * distinguevamo da un avvio lento, così i pulsanti di accensione aspettavano 15
 * minuti e poi dicevano "riprova tra poco" — un messaggio falso che mandava in
 * circolo. Ora lo riconosciamo e lo diciamo subito, con il link per rifare il token.
 */
function isAuthFailure(out) {
    return /Authentication required to call the Kaggle API|401|Unauthorized|invalid.*token|token.*expired/i.test(out || "");
}
const AUTH_MSG = "⛔ Il token Kaggle non è più valido (scaduto o revocato): Antigravity non può accendere né interrogare il notebook. "
    + "Rigeneralo su https://www.kaggle.com/settings/api → «Generate New Token», poi incolla il valore in KAGGLE_API_TOKEN nel .env e riavvia.";

/**
 * Lancia `kaggle kernels push` per avviare un nuovo run del notebook.
 * @returns {Promise<{ok:boolean, authFailed:boolean, out:string}>}
 */
function pushKernel(tok, logger, dir) {
    return new Promise((resolve) => {
        const p = spawn(pythonExe(), ["-m", "kaggle", "kernels", "push", "-p", dir], {
            env: Object.assign({}, process.env, { KAGGLE_API_TOKEN: tok }),
            windowsHide: true
        });
        let out = "";
        p.stdout.on("data", d => out += d);
        p.stderr.on("data", d => out += d);
        p.on("close", () => {
            (logger.log || console.log).call(logger, "[kaggleWaker] push: " + out.trim().slice(0, 200));
            resolve({ ok: /successfully pushed/i.test(out), authFailed: isAuthFailure(out), out });
        });
        p.on("error", e => {
            (logger.error || console.error).call(logger, "[kaggleWaker] push errore: " + e.message);
            resolve({ ok: false, authFailed: false, out: e.message });
        });
    });
}

let _waking = null;

/**
 * Assicura che il notebook Kaggle sia acceso. Ritorna Promise<boolean>.
 * @param {object} o  onStatus(fn), maxWaitMs (default 15min), logger, size (14|30)
 */
function ensureUp(o = {}) {
    const onStatus = o.onStatus || (() => {});
    const maxWaitMs = o.maxWaitMs || 15 * 60 * 1000;
    const logger = o.logger || console;
    const { dir, size } = sizeDir(o.size);

    if (_waking) { onStatus("🟡 Notebook Kaggle: accensione già in corso…"); return _waking; }

    _waking = (async () => {
        if (await isUp()) { onStatus("✅ Notebook Kaggle (" + size + "B) già acceso."); return true; }
        const tok = token();
        if (!tok) { onStatus("⚠️ Manca KAGGLE_API_TOKEN nel .env: non posso accendere il notebook Kaggle."); return false; }
        if (!fs.existsSync(path.join(dir, "kernel-metadata.json"))) { onStatus("⚠️ Notebook Kaggle non incluso nell'app (src/kaggle-notebook" + (size === 30 ? "-big" : "") + ")."); return false; }

        onStatus("🟡 Accendo il notebook Kaggle " + size + "B su GPU… (scarica i modelli: può volerci qualche minuto)");
        const pushed = await pushKernel(tok, logger, dir);
        // Token rifiutato: inutile attendere l'endpoint, non partirà mai. Fallisci
        // SUBITO dicendo la cosa vera e azionabile, invece di 15 minuti di attesa.
        if (pushed.authFailed) { onStatus(AUTH_MSG); return false; }
        if (!pushed.ok) onStatus("🟡 Push inviato (esito incerto): attendo comunque l'endpoint…");

        const t0 = Date.now();
        let ticks = 0;
        while (Date.now() - t0 < maxWaitMs) {
            await new Promise(r => setTimeout(r, 10000));
            if (await isUp()) { onStatus("✅ Notebook Kaggle " + size + "B pronto."); return true; }
            if (++ticks % 3 === 0) onStatus("🟡 Notebook " + size + "B in avvio… (" + Math.round((Date.now() - t0) / 1000) + "s)");
        }
        onStatus("⚠️ Il notebook Kaggle " + size + "B non è salito entro il tempo massimo. Riprova tra poco.");
        return false;
    })().finally(() => { _waking = null; });

    return _waking;
}

/** Stato corrente: su/giù + quale dimensione è configurata. */
async function status() {
    const up = await isUp();
    return { up, host: KAGGLE_HOST, slug: NB_SLUG };
}

/**
 * Spegnimento. Kaggle NON espone API di stop: se nel .env c'è KAGGLE_SHUTDOWN_URL
 * (worker Cloudflare) lo usiamo; altrimenti restituiamo il link alla pagina del
 * notebook dove spegnere a mano (un tap sul telefono).
 */
async function shutdown() {
    const url = envVar("KAGGLE_SHUTDOWN_URL");
    if (url) {
        try {
            await new Promise((resolve, reject) => {
                const req = https.request(url, { method: "POST", timeout: 15000 }, r => { let d = ""; r.on("data", c => d += c); r.on("end", () => resolve(d)); });
                req.on("error", reject); req.setTimeout(15000, () => req.destroy(new Error("timeout"))); req.end();
            });
            return { ok: true, via: "worker", message: "🔴 Spegnimento Kaggle richiesto via worker Cloudflare." };
        } catch (e) {
            return { ok: false, via: "worker", message: "⚠️ Worker di shutdown non raggiungibile: " + e.message };
        }
    }
    // ★ 2026-07-30 — Nessun KAGGLE_SHUTDOWN_URL nel .env: lo spegnimento "via
    // Cloudflare" NON è mai stato configurato (non si è rotto). Diciamolo, così è
    // chiaro che serve creare il worker e incollarne l'URL, non riparare del codice.
    return {
        ok: false, via: "manual", workerConfigured: false,
        message: "Spegnimento automatico non configurato (manca KAGGLE_SHUTDOWN_URL nel .env: è l'URL del worker Cloudflare). "
            + "Kaggle non ha un'API di stop, quindi per ora si spegne con un tap dalla pagina del notebook: apro io la pagina.",
        url: "https://www.kaggle.com/code/" + NB_SLUG
    };
}

// --- Ore quota GPU (usate/rimanenti/reset) via API kaggle quota_view ---------
let _quotaCache = null, _quotaAt = 0;
/** Ritorna { usedH, totalH, remainingH, reset } delle ore GPU Kaggle. Cache 5 min. */
function quota() {
    if (_quotaCache && Date.now() - _quotaAt < 5 * 60 * 1000) return Promise.resolve(_quotaCache);
    const tok = token();
    if (!tok) return Promise.resolve({ error: "manca KAGGLE_API_TOKEN" });
    const py = [
        "import json,re",
        "from kaggle.api.kaggle_api_extended import KaggleApi",
        "a=KaggleApi(); a.authenticate()",
        "q=a.quota_view()",
        "g=getattr(q,'gpu_quota',None) or getattr(q,'gpuQuota',None)",
        "def attr(o,*names):",
        " for n in names:",
        "  v=getattr(o,n,None)",
        "  if v is None and isinstance(o,dict): v=o.get(n)",
        "  if v is not None: return v",
        " return None",
        "def sec(v):",
        " if hasattr(v,'total_seconds'): return v.total_seconds()",
        " m=re.match(r'(\\d+(?:\\.\\d+)?)',str(v or ''))",
        " return float(m.group(1)) if m else 0.0",
        "used=sec(attr(g,'time_used','timeUsed'))/3600.0",
        "total=sec(attr(g,'total_time_allowed','totalTimeAllowed'))/3600.0",
        "reset=attr(q,'quota_refresh_time','quotaRefreshTime')",
        "print(json.dumps({'usedH':round(used,1),'totalH':round(total,1),'remainingH':round(max(0,total-used),1),'reset':str(reset)[:10]}))"
    ].join("\n");
    return new Promise((resolve) => {
        const p = spawn(pythonExe(), ["-c", py], { env: Object.assign({}, process.env, { KAGGLE_API_TOKEN: tok }), windowsHide: true });
        let out = "", err = "";
        p.stdout.on("data", d => out += d); p.stderr.on("data", d => err += d);
        const t = setTimeout(() => { try { p.kill(); } catch (_) {} }, 20000);
        p.on("close", () => {
            clearTimeout(t);
            try { const j = JSON.parse(out.trim().split("\n").pop()); _quotaCache = j; _quotaAt = Date.now(); resolve(j); }
            catch (_) {
                // Distingui "token rifiutato" da "output inatteso": il primo si risolve
                // solo rigenerando il token, e va detto invece di un generico errore.
                if (isAuthFailure(err + "\n" + out)) return resolve({ error: "token Kaggle scaduto", authFailed: true, hint: AUTH_MSG });
                resolve({ error: "quota non leggibile", detail: (err || out).slice(0, 120) });
            }
        });
        p.on("error", (e) => { clearTimeout(t); resolve({ error: e.message }); });
    });
}

module.exports = { isUp, ensureUp, ensureUpSize: (size, o) => ensureUp(Object.assign({}, o, { size })), status, shutdown, quota, KAGGLE_HOST, NB_SLUG, NB_DIR: SIZE_DIR[14] };
