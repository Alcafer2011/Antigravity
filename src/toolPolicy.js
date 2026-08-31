"use strict";
/**
 * toolPolicy — PERMESSI PER SINGOLO STRUMENTO, PERSISTENTI.
 *
 * ★ 2026-08-01 — Prima esisteva UNA sola manopola globale (`permissionPolicy`:
 * ask-writes / auto-allow / read-only). Conseguenza: o approvavi ogni singola
 * cosa, oppure autorizzavi TUTTO — compreso run_command e delete. E la scelta
 * non sopravviveva al riavvio: ogni volta da capo.
 *
 * Qui la decisione diventa per STRUMENTO e resta scritta su disco:
 *   - "chiedi"  → chiede sempre conferma (default per le azioni che mutano)
 *   - "auto"    → consentito senza chiedere
 *   - "mai"     → negato senza nemmeno chiedere
 * La regola globale resta come rete: se per uno strumento non c'e' una regola
 * sua, si ricade sul comportamento di prima. Nessuna rottura all'indietro.
 *
 * Indipendente dal modello: vale per Nous free, Ollama locale, qualunque motore.
 */

const fs = require("fs");
const path = require("path");

const FILE = path.join(__dirname, ".permessi-strumenti.json");

const MODI = new Set(["chiedi", "auto", "mai"]);

/**
 * Strumenti che NON possono mai diventare "auto" da soli: toccano il sistema in
 * modo difficilmente reversibile. Possono essere messi in auto solo con
 * `forza:true`, cioe' con una scelta esplicita e consapevole dell'utente.
 */
const SENSIBILI = new Set(["run_command", "run_code", "delete_file", "patch_binary", "web_automate", "frida_hook", "mitm_capture"]);

function _leggi() {
    try {
        const j = JSON.parse(fs.readFileSync(FILE, "utf8"));
        return (j && typeof j === "object" && j.strumenti) ? j : { strumenti: {}, aggiornato: null };
    } catch (_) { return { strumenti: {}, aggiornato: null }; }
}

function _scrivi(st) {
    st.aggiornato = new Date().toISOString();
    try { fs.writeFileSync(FILE, JSON.stringify(st, null, 2), "utf8"); return true; }
    catch (_) { return false; }
}

/**
 * Decisione per uno strumento.
 * @param {string} tool
 * @returns {"chiedi"|"auto"|"mai"|null}  null = nessuna regola, decide il globale
 */
function modo(tool) {
    if (!tool) return null;
    const st = _leggi();
    const v = st.strumenti[tool];
    return (v && MODI.has(v.modo)) ? v.modo : null;
}

/**
 * Imposta la regola per uno strumento.
 * @param {string} tool
 * @param {"chiedi"|"auto"|"mai"} m
 * @param {object} o { forza, nota }
 */
function imposta(tool, m, o = {}) {
    if (!tool) return { ok: false, error: "manca il nome dello strumento" };
    if (!MODI.has(m)) return { ok: false, error: "modo non valido: " + m + " (usa chiedi|auto|mai)" };
    if (m === "auto" && SENSIBILI.has(tool) && !o.forza) {
        return {
            ok: false,
            error: "«" + tool + "» e' uno strumento sensibile: puo' toccare il sistema in modo difficile da annullare. "
                + "Per metterlo in automatico serve una conferma esplicita (forza).",
            sensibile: true
        };
    }
    const st = _leggi();
    st.strumenti[tool] = { modo: m, quando: new Date().toISOString(), nota: o.nota || "" };
    if (!_scrivi(st)) return { ok: false, error: "impossibile scrivere " + FILE };
    return { ok: true, tool, modo: m };
}

/** Toglie la regola: lo strumento torna a seguire la politica globale. */
function azzera(tool) {
    const st = _leggi();
    if (!st.strumenti[tool]) return { ok: true, tool, giaAssente: true };
    delete st.strumenti[tool];
    if (!_scrivi(st)) return { ok: false, error: "impossibile scrivere " + FILE };
    return { ok: true, tool, azzerato: true };
}

/** Tutte le regole impostate. */
function elenco() {
    const st = _leggi();
    return Object.keys(st.strumenti).sort().map(t => ({
        tool: t, modo: st.strumenti[t].modo,
        quando: st.strumenti[t].quando, nota: st.strumenti[t].nota || "",
        sensibile: SENSIBILI.has(t)
    }));
}

/** Cancella tutte le regole (torna al comportamento globale puro). */
function azzeraTutto() {
    return _scrivi({ strumenti: {} }) ? { ok: true } : { ok: false, error: "impossibile scrivere " + FILE };
}

module.exports = { modo, imposta, azzera, azzeraTutto, elenco, SENSIBILI, FILE };
