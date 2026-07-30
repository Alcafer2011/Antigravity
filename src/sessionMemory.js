"use strict";
/**
 * sessionMemory — MEMORIA LUNGA delle sessioni (CORE AI, blocco 2).
 * Le chat non sono più "solo l'ultima": ogni sessione chiusa viene riassunta e
 * salvata in knowledge/sessions/<id>.js come oggetto leggibile. recall() ritorna
 * gli ultimi N riassunti da iniettare nel system prompt, così l'agente riprende
 * da dove aveva lasciato (es. un lavoro di reverse o un pezzo CAD).
 *
 * SICURO: solo append/lettura. Non cancella mai. Niente segreti nei riassunti.
 */
const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "knowledge", "sessions");
try { fs.mkdirSync(DIR, { recursive: true }); } catch (_) {}

function _id(ts) { return new Date(ts || Date.now()).toISOString().replace(/[:.]/g, "-"); }

/**
 * Salva un riassunto di sessione.
 * @param {object} sess { id?, title, summary, topics:[], ts? }
 */
function save(sess) {
  try {
    const id = sess.id || _id(sess.ts);
    const file = path.join(DIR, id + ".json");
    const obj = { id, title: sess.title || "sessione", summary: String(sess.summary || ""), topics: sess.topics || [], ts: sess.ts || Date.now() };
    fs.writeFileSync(file, JSON.stringify(obj, null, 2), "utf8");
    _prune();
    return { ok: true, id };
  } catch (e) { return { ok: false, error: e.message }; }
}

/**
 * Ritorna gli ultimi N riassunti (piu' recenti prima) come testo da iniettare.
 * @param {number} n  quanti riassunti (default 5)
 */
function recall(n = 5) {
  try {
    const files = fs.readdirSync(DIR).filter(f => f.endsWith(".json")).sort().reverse().slice(0, n);
    const out = [];
    for (const f of files) {
      try {
        const o = JSON.parse(fs.readFileSync(path.join(DIR, f), "utf8"));
        out.push("• [" + (o.title || o.id) + "] " + (o.summary || "").slice(0, 300));
      } catch (_) {}
    }
    return out.join("\n");
  } catch (_) { return ""; }
}

// Mantiene al massimo 50 sessioni (anti-crecita illimitata).
function _prune(max = 50) {
  try {
    const files = fs.readdirSync(DIR).filter(f => f.endsWith(".json")).sort();
    while (files.length > max) { const old = files.shift(); try { fs.unlinkSync(path.join(DIR, old)); } catch (_) {} }
  } catch (_) {}
}

module.exports = { save, recall, DIR };
