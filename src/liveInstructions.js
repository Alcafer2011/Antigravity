"use strict";
/**
 * liveInstructions.js — "Istruzioni vive" dell'agente.
 *
 * Obiettivo (idea dell'utente, 2026-07-27): un agente super-istruito che si
 * AGGIORNA DA SOLO a ogni modifica dei file di Antigravity. Invece di incollare
 * tutto nel system prompt (che lo farebbe impazzire e rallentare), teniamo un
 * unico file `knowledge/ISTRUZIONI_VIVE.md` che è il riassunto SEMPRE AGGIORNATO
 * di: regole tassative, mappa dei moduli, come si comporta l'agente.
 *
 * REGOLA ANTI-GONFIAMENTO (richiesta dell'utente): il blocco ha un TETTO MASSIMO.
 * Se il file supera il tetto, viene troncato mantenendo in testa la versione e le
 * regole più importanti. Così "salendo di versione" si alleggerisce, non si appesantisce.
 *
 * Aggiornamento: apply-change.ps1 (lo script anti-danno) ricompila questo file a
 * ogni modifica di src\ o knowledge\, alzando il numero di versione. L'agente alla
 * prossima risposta ricarica le istruzioni (legge il file ogni volta, niente cache).
 *
 * SICUREZZA: se il file non c'è, ritorna "" — NON rompe mai l'agente.
 */

const fs = require("fs");
const path = require("path");

const FILE = path.join(__dirname, "knowledge", "ISTRUZIONI_VIVE.md");
const CAP = 6000; // tetto massimo caratteri iniettati nel prompt

function _read() {
  try {
    return fs.readFileSync(FILE, "utf8");
  } catch (_) {
    return "";
  }
}

/** Numero di versione (dal primo rigo tipo "VERSION: 1.2.3"). 0 se assente. */
function version() {
  const t = _read();
  const m = /VERSION:\s*([0-9]+\.[0-9]+\.[0-9]+)/i.exec(t);
  return m ? m[1] : "0.0.0";
}

/**
 * Ritorna il blocco di istruzioni da iniettare nel system prompt.
 * Se il file è vuoto → "". Se supera il CAP → tronca tenendo testa+corpo.
 */
function liveBlock() {
  const raw = _read().trim();
  if (!raw) return "";

  // Se entro il tetto, ritorna tutto.
  if (raw.length <= CAP) {
    return (
      "\n\n=== ISTRUZIONI VIVE (auto-aggiornate, v" + version() + ") ===\n" +
      raw +
      "\n=== FINE ISTRUZIONI VIVE ==="
    );
  }

  // OLTRE IL TETTO: tieni la prima riga (VERSION) + le prime CAP-200 char del corpo,
  // e chiudi con un avviso. Così l'agente ha sempre le regole in cima, mai un mattone.
  const head = raw.slice(0, raw.indexOf("\n") + 1);
  const body = raw.slice(raw.indexOf("\n") + 1, CAP - 200);
  return (
    "\n\n=== ISTRUZIONI VIVE (v" + version() + ", COMPATTATE per tetto) ===\n" +
    head + body +
    "\n[... troncato per tetto " + CAP + " char: vedi knowledge/ISTRUZIONI_VIVE.md per il testo completo ]\n" +
    "=== FINE ISTRUZIONI VIVE ==="
  );
}

/**
 * Budget della finestra storica in funzione della VERSIONE.
 * Idea dell'utente: "salendo di versione si può limitare lo storico, alleggerire".
 * Ogni bump delle istruzioni vive (patch z) riduce di 1 i messaggi tenuti, fino a
 * un minimo di 8. Così l'agente resta leggero man mano che impara di più (le
 * istruzioni vive contengono già il contesto, non serve tutta la cronaca).
 */
function historyBudget() {
  const v = version().split(".").map(Number);
  const patch = v[2] || 0;
  return Math.max(8, 30 - patch);
}

module.exports = { liveBlock, version, historyBudget, FILE, CAP };
