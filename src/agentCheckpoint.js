"use strict";
/**
 * agentCheckpoint.js — RIPRESA del lavoro dell'agente.
 *
 * Problema (segnalato dall'utente 2026-08-06): quando un motore si interrompe e
 * si preme "↻ Rigenera", oppure quando il failover passa a un altro motore,
 * l'agente RICOMINCIA DA ZERO — rilegge tutti i file, rifà i grep, e ri-brucia
 * il budget dei provider free. Le osservazioni degli strumenti vivevano solo
 * dentro l'array `messages` di quella singola run e venivano buttate.
 *
 * Soluzione: persistiamo su disco le OSSERVAZIONI degli strumenti (cosa ha letto,
 * cercato, trovato) legate a (conversazione + testo della richiesta). Alla ripresa
 * — stessa richiesta, stessa conversazione — l'agente ritrova quei risultati e
 * CONTINUA da dove era, invece di rifare tutto.
 *
 * Chiave = conversationId + hash(prompt): così "Rigenera" (rispedisce lo stesso
 * `lastUser`) e il failover (stesso `guided`) ricadono sullo stesso checkpoint,
 * mentre una domanda NUOVA parte pulita. Si azzera al completamento (successo) e
 * scade da solo dopo 1 ora (niente ripresa di roba vecchia).
 *
 * SICUREZZA: tutto è avvolto in try/catch e ritorna sempre valori neutri — se il
 * disco non è scrivibile o il file è corrotto, l'agente lavora come prima, senza
 * ripresa, ma NON si rompe mai.
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DIR = path.join(__dirname, ".checkpoints");
const TTL = 60 * 60 * 1000;   // 1 ora: oltre, il checkpoint è considerato scaduto
const MAX_OBS = 40;           // quante osservazioni tenere (le più recenti)

function _key(convId, prompt) {
    const h = crypto.createHash("sha1").update(String(prompt || "")).digest("hex").slice(0, 12);
    const safe = String(convId || "default").replace(/[^\w.-]/g, "_").slice(0, 60);
    return safe + "_" + h;
}

function _file(convId, prompt) {
    return path.join(DIR, _key(convId, prompt) + ".json");
}

/** Ritorna le osservazioni salvate per (conversazione+richiesta), o [] se assenti/scadute. */
function load(convId, prompt) {
    try {
        const f = _file(convId, prompt);
        const j = JSON.parse(fs.readFileSync(f, "utf8"));
        if (!j || (Date.now() - (j.at || 0)) > TTL) { try { fs.unlinkSync(f); } catch (_) {} return []; }
        return Array.isArray(j.observations) ? j.observations : [];
    } catch (_) {
        return [];
    }
}

/** Salva (sovrascrive) le osservazioni per (conversazione+richiesta). */
function save(convId, prompt, observations) {
    try {
        fs.mkdirSync(DIR, { recursive: true });
        const obs = Array.isArray(observations) ? observations.slice(-MAX_OBS) : [];
        fs.writeFileSync(_file(convId, prompt), JSON.stringify({ at: Date.now(), observations: obs }), "utf8");
    } catch (_) { /* best-effort: se non si può scrivere, niente ripresa ma nessun danno */ }
}

/** Cancella il checkpoint (chiamato al completamento con successo). */
function clear(convId, prompt) {
    try { fs.unlinkSync(_file(convId, prompt)); } catch (_) {}
}

/** Pulizia opportunistica dei checkpoint scaduti (chiamabile ogni tanto). */
function sweep() {
    try {
        for (const name of fs.readdirSync(DIR)) {
            const p = path.join(DIR, name);
            try {
                const j = JSON.parse(fs.readFileSync(p, "utf8"));
                if (Date.now() - (j.at || 0) > TTL) fs.unlinkSync(p);
            } catch (_) { try { fs.unlinkSync(p); } catch (_) {} }
        }
    } catch (_) {}
}

module.exports = { load, save, clear, sweep };
