"use strict";
/**
 * gpuFailover — INFRA/GPU (blocco 4): failover automatico, accensione programmata,
 * pre-caricamento modello, monitor quota.
 *
 * ★ 2026-07-30 (due correzioni):
 *  1. Il .env veniva letto da os.homedir() invece che dalla radice del progetto.
 *     Con il consolidamento in C:\Users\infoa\Antigravity il file buono è
 *     ..\.env: MODAL_TOKEN_ID & co. risultavano "non configurati" pur essendoci.
 *     Ora si usa envFile.envFilePath() come tutti gli altri moduli.
 *  2. Il failover non cambia più corsia MENTRE stai costruendo: se c'è un
 *     cantiere aperto con una piattaforma "appuntata", quella resta l'attiva
 *     finché è viva. Cambiare modello/endpoint a metà lavoro è uno dei modi in
 *     cui il lavoro dal telefono si rompeva da solo.
 *
 * Lo stato "up" reale viene dai driver in platforms/ (Kaggle e Modal sono reali).
 */
const fs = require("fs");
const path = require("path");

function _envPath() {
    try { return require("./envFile").envFilePath(); }
    catch (_) { return path.join(__dirname, "..", ".env"); }
}
function _token(name) {
    try {
        const txt = fs.readFileSync(_envPath(), "utf8");
        const m = txt.match(new RegExp("^\\s*" + name + "\\s*=\\s*\"?([^\"\\r\\n]+)\"?", "im"));
        if (m) return m[1].trim();
    } catch (_) {}
    return (process.env[name] || "").trim() || null;
}

// Stato di ogni piattaforma (configurata = hai il token).
function platforms() {
    const defs = [
        { id: "kaggle",     token: "KAGGLE_API_TOKEN", alwaysOn: false },
        { id: "modal",      token: "MODAL_TOKEN_ID",   alwaysOn: true },
        { id: "lightning",  token: "LIGHTNING_TOKEN",  alwaysOn: false },
        { id: "paperspace", token: "PAPERSPACE_API_KEY", alwaysOn: false },
    ];
    return defs.map(d => ({ id: d.id, configured: !!_token(d.token), alwaysOn: d.alwaysOn }));
}

/**
 * Failover: quale corsia usare adesso.
 * Ordine: piattaforma appuntata dal cantiere → alwaysOn configurata → prima configurata.
 */
function pickActive() {
    // ★ Cantiere aperto con pin: non si cambia cavallo a metà guado.
    try {
        const st = require("./cantiere").stato();
        if (st.aperto && st.pinPiattaforma) {
            return { active: st.pinPiattaforma, appuntata: true,
                note: "Corsia bloccata su «" + st.pinPiattaforma + "» dal cantiere «" + st.titolo + "»: il failover non cambia piattaforma mentre stai costruendo." };
        }
    } catch (_) {}

    const ps = platforms();
    const up = ps.filter(p => p.configured);
    if (!up.length) return { active: "kaggle", note: "Nessun token: solo Kaggle manuale disponibile." };
    const always = up.find(p => p.alwaysOn);
    return { active: always ? always.id : up[0].id, available: up.map(p => p.id) };
}

// Accensione programmata: salva un orario di accensione/spegnimento.
function setSchedule(on, off) {
    try {
        const f = path.join(__dirname, ".gpu-schedule.json");
        fs.writeFileSync(f, JSON.stringify({ on, off, updated: Date.now() }), "utf8");
        return { ok: true, on, off };
    } catch (e) { return { ok: false, error: e.message }; }
}
function getSchedule() {
    try { return JSON.parse(fs.readFileSync(path.join(__dirname, ".gpu-schedule.json"), "utf8")); }
    catch (_) { return { on: null, off: null }; }
}

// Pre-caricamento modello: segna quale modello abliterated caricare al boot della piattaforma.
function setPreload(repo) {
    try {
        const f = path.join(__dirname, ".gpu-preload.json");
        fs.writeFileSync(f, JSON.stringify({ repo, updated: Date.now() }), "utf8");
        return { ok: true, repo };
    } catch (e) { return { ok: false, error: e.message }; }
}
function getPreload() {
    try { return JSON.parse(fs.readFileSync(path.join(__dirname, ".gpu-preload.json"), "utf8")); }
    catch (_) { return { repo: null }; }
}

// Monitor quota: legge quota Kaggle se kaggleWaker disponibile.
async function quota() {
    try {
        const kw = require("./kaggleWaker");
        if (typeof kw.quota === "function") return { ok: true, kaggle: await kw.quota() };
    } catch (_) {}
    return { ok: false, note: "kaggleWaker non disponibile" };
}

module.exports = { platforms, pickActive, setSchedule, getSchedule, setPreload, getPreload, quota };
