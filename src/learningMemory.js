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
// 2026-08-31 — FILTRO ANTI-SPAZZATURA. Trovato dal vivo: su 109 "lezioni" in
// archivio, 103 erano lo STESSO blocco («CORREZIONE UTENTE: «═══ CONOSCENZA
// OPERATIVA …»»). Nasceva così: nei percorsi guidati (Ghidra/ZW3D/manutenzione)
// il prompt passato all'agente ha in testa il file di conoscenza; se dentro
// c'era la parola "errore", nativeAgent lo scambiava per una correzione
// dell'utente e ne salvava una fetta come lezione. La deduplica non lo fermava
// perché ogni fetta era leggermente diversa. Risultato: ~10.000 caratteri di
// rumore iniettati nel prompt a OGNI turno — una delle voci che facevano
// sbattere l'agente contro il muro TPM dei provider.
const _SPAZZATURA = /═══|CONOSCENZA OPERATIVA|REGOLE GHIDRA|STRUMENTI DELL'AGENTE/;
/** Prefisso usato per riconoscere una lezione "praticamente uguale" a una già presente. */
function _prefisso(t) { return _norm(t).toLowerCase().slice(0, 80); }

function remember(text, { tags = [], scope = "global" } = {}) {
    text = _norm(text);
    if (!text || text.length < 4) return { ok: false };
    // Non è una lezione: è un pezzo di prompt di sistema rientrato dalla finestra.
    if (_SPAZZATURA.test(text)) return { ok: false, motivo: "sembra un pezzo del prompt di sistema, non una lezione" };
    const db = _load();
    const key = text.toLowerCase();
    const existing = db.lessons.find(l => l.text.toLowerCase() === key)
        || db.lessons.find(l => _prefisso(l.text) === _prefisso(text));
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

// ===========================================================================
// MEMORIA SEMANTICA  (2026-08-31)
// ---------------------------------------------------------------------------
// recall() qui sopra confronta PAROLE: una lezione viene ripescata solo se il
// suo scope o un suo tag compare LETTERALMENTE nel prompt. Con 109 lezioni in
// archivio questo significa due difetti opposti allo stesso tempo:
//   - la lezione giusta non salta fuori se l'utente la chiama con altre parole
//     ("scheda video piccola" non incrocia mai il tag "gpu");
//   - per compensare venivano iniettate 24 lezioni a ogni turno, quasi tutte
//     fuori tema: e' una delle voci che gonfiano il system prompt e fanno
//     sbattere l'agente contro il muro TPM dei provider.
// Qui sotto le lezioni vengono confrontate per SIGNIFICATO, con gli embedding
// di Ollama (nomic-embed-text, gira in locale, gratis, ~270 MB). I vettori
// stanno in un file a parte (learning.json resta leggibile) e si calcolano una
// volta sola per lezione. Se Ollama e' spento o il modello manca, si ricade in
// silenzio su recall() a parole: la memoria non si rompe mai.
// ===========================================================================

const VEC_FILE = path.join(DIR, "learning-vectors.json");
const EMBED_MODEL = process.env.ANTIGRAVITY_EMBED_MODEL || "nomic-embed-text";
const OLLAMA = (process.env.OLLAMA_HOST || "http://127.0.0.1:11434").replace(/\/$/, "");
// Soglia di somiglianza: sotto questa una lezione e' rumore e NON entra nel
// prompt. Meglio 6 lezioni giuste che 24 a caso.
const MIN_SIM = 0.45;

function _loadVecs() {
    try { const d = JSON.parse(fs.readFileSync(VEC_FILE, "utf8")); return (d && d.model === EMBED_MODEL && d.vecs) ? d.vecs : {}; }
    catch (_) { return {}; }
}
function _saveVecs(vecs) {
    try { fs.mkdirSync(DIR, { recursive: true }); fs.writeFileSync(VEC_FILE, JSON.stringify({ model: EMBED_MODEL, vecs }), "utf8"); }
    catch (_) { /* la cache non e' critica */ }
}
/** Chiave stabile di una lezione (il testo normalizzato). */
function _key(text) { return _norm(text).toLowerCase().slice(0, 400); }

/** Embedding di uno o piu' testi via Ollama. Ritorna null se non e' disponibile. */
async function _embed(inputs, timeoutMs = 8000) {
    if (!inputs.length) return [];
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
        const r = await fetch(OLLAMA + "/api/embed", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: EMBED_MODEL, input: inputs }),
            signal: ctrl.signal
        });
        if (!r.ok) return null;
        const j = await r.json();
        return Array.isArray(j.embeddings) ? j.embeddings : null;
    } catch (_) { return null; }
    finally { clearTimeout(t); }
}

function _cos(a, b) {
    let d = 0, na = 0, nb = 0;
    for (let i = 0; i < a.length && i < b.length; i++) { d += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
    return (na && nb) ? d / (Math.sqrt(na) * Math.sqrt(nb)) : 0;
}

/**
 * Richiamo per SIGNIFICATO. Stessa firma di recall() ma asincrono.
 * Il punteggio unisce le due cose che contano davvero:
 *   somiglianza semantica (peso 100) + i bonus di scope/tag/uso gia' collaudati,
 * cosi' una lezione fissata su un progetto continua ad avere la precedenza
 * quando si lavora su quel progetto.
 */
async function recallSemantic(context = "", limit = 12) {
    try {
        const db = _load();
        if (!db.lessons.length) return "";
        const ctx = String(context || "").trim();
        if (!ctx) return recall(context, limit);

        // 1) vettori delle lezioni: dalla cache, e calcolo solo quelli mancanti.
        const vecs = _loadVecs();
        const mancanti = db.lessons.filter(l => !vecs[_key(l.text)]);
        if (mancanti.length) {
            const nuovi = await _embed(mancanti.map(l => l.text).slice(0, 200), 30000);
            if (!nuovi) return recall(context, limit);      // Ollama giu' -> a parole
            mancanti.slice(0, 200).forEach((l, i) => { if (nuovi[i]) vecs[_key(l.text)] = nuovi[i]; });
            _saveVecs(vecs);
        }

        // 2) vettore della domanda (solo la parte utile: prompt + percorso).
        const q = await _embed([ctx.slice(0, 2000)]);
        if (!q || !q[0]) return recall(context, limit);
        const qv = q[0];

        const low = ctx.toLowerCase();
        const scored = db.lessons.map(l => {
            const v = vecs[_key(l.text)];
            const sim = v ? _cos(qv, v) : 0;
            let s = sim * 100;
            if (l.scope && l.scope !== "global" && low.includes(l.scope.toLowerCase())) s += 50;
            if ((l.tags || []).some(t => low.includes(String(t).toLowerCase()))) s += 20;
            s += Math.min(l.uses || 0, 10);
            return { l, s, sim };
        }).filter(x => x.sim >= MIN_SIM || x.s >= 55);   // rumore fuori dal prompt

        scored.sort((a, b) => (b.s - a.s) || (b.l.at - a.l.at));
        const chosen = scored.slice(0, limit).map(x => "• " + x.l.text);
        return chosen.length ? chosen.join("\n") : "";
    } catch (_) {
        return recall(context, limit);
    }
}

/** Ricostruisce da zero la cache dei vettori (dopo un cambio di modello). */
async function reindex() {
    const db = _load();
    const vecs = {};
    const testi = db.lessons.map(l => l.text).slice(0, 200);
    const nuovi = await _embed(testi, 60000);
    if (!nuovi) return { ok: false, error: "Ollama non risponde o manca il modello " + EMBED_MODEL };
    testi.forEach((t, i) => { if (nuovi[i]) vecs[_key(t)] = nuovi[i]; });
    _saveVecs(vecs);
    return { ok: true, count: Object.keys(vecs).length, model: EMBED_MODEL };
}

module.exports = { remember, recall, recallSemantic, reindex, all, clear, FILE, VEC_FILE, EMBED_MODEL };
