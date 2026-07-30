"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

/**
 * learningMemory — la memoria EVOLUTIVA di Antigravity. È ciò che rende
 * l'assistente "vivo": accumula le LEZIONI apprese (scoperte utili, correzioni
 * dell'utente, preferenze, trucchi che hanno funzionato) e le reinietta nel
 * prompt alle sessioni successive. Così migliora nel tempo invece di ripartire
 * da zero ogni volta.
 *
 * Storage: un JSON stabile in ~/.antigravity/learning.json (indipendente dal
 * progetto). Ogni lezione: { text, tags[], scope, at, uses }. Limitato e
 * deduplicato per non gonfiare all'infinito.
 */

const DIR = path.join(os.homedir(), ".antigravity");
const FILE = path.join(DIR, "learning.json");
const MAX = 300;

function _load() {
    try { const d = JSON.parse(fs.readFileSync(FILE, "utf8")); return Array.isArray(d.lessons) ? d : { lessons: [] }; }
    catch (_) { return { lessons: [] }; }
}
function _save(db) {
    try { fs.mkdirSync(DIR, { recursive: true }); fs.writeFileSync(FILE, JSON.stringify(db, null, 2), "utf8"); }
    catch (_) { /* memoria non critica: se non si salva, si prosegue */ }
}
function _norm(s) { return String(s || "").trim().replace(/\s+/g, " "); }

/**
 * Salva una lezione. scope: "global" (sempre) o una parola-chiave (es. il nome
 * del binario/progetto) per lezioni contestuali. Deduplica per testo simile.
 */
function remember(text, { tags = [], scope = "global" } = {}) {
    text = _norm(text);
    if (!text || text.length < 4) return { ok: false };
    const db = _load();
    const key = text.toLowerCase();
    const existing = db.lessons.find(l => l.text.toLowerCase() === key);
    if (existing) { existing.uses = (existing.uses || 0) + 1; existing.at = Date.now(); }
    else {
        db.lessons.push({ text, tags: Array.isArray(tags) ? tags.slice(0, 8) : [], scope: _norm(scope) || "global", at: Date.now(), uses: 0 });
        // limite: butta le più vecchie e meno usate
        if (db.lessons.length > MAX) {
            db.lessons.sort((a, b) => (b.uses - a.uses) || (b.at - a.at));
            db.lessons = db.lessons.slice(0, MAX);
        }
    }
    _save(db);
    return { ok: true, count: db.lessons.length };
}

/**
 * Richiama le lezioni rilevanti da iniettare nel prompt. Prende quelle "global"
 * più quelle il cui scope/tag compare nel contesto (prompt/percorso). Le più
 * usate e recenti per prime. Ritorna testo pronto (o "").
 */
function recall(context = "", limit = 24) {
    const db = _load();
    if (!db.lessons.length) return "";
    const ctx = String(context || "").toLowerCase();
    const scored = db.lessons.map(l => {
        let s = (l.uses || 0);
        if (l.scope && l.scope !== "global" && ctx.includes(l.scope.toLowerCase())) s += 50;
        if ((l.tags || []).some(t => ctx.includes(String(t).toLowerCase()))) s += 20;
        if (l.scope === "global") s += 5;
        return { l, s };
    }).filter(x => x.l.scope === "global" || x.s > 5);
    scored.sort((a, b) => (b.s - a.s) || (b.l.at - a.l.at));
    const chosen = scored.slice(0, limit).map(x => "• " + x.l.text);
    return chosen.length ? chosen.join("\n") : "";
}

function all() { return _load().lessons; }
function clear() { _save({ lessons: [] }); }

module.exports = { remember, recall, all, clear, FILE };
