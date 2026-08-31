"use strict";
// I test della MEMORIA. Nascono dal guasto del 31/08: 103 lezioni su 109 erano
// lo stesso pezzo di prompt di sistema rientrato dalla finestra, e finivano
// dentro OGNI richiesta. La memoria "funzionava" e nessuno se ne accorgeva.
const { test } = require("node:test");
const assert = require("node:assert");
const mem = require("../src/learningMemory.js");

test("un pezzo del prompt di sistema NON viene salvato come lezione", () => {
    const r = mem.remember("CORREZIONE UTENTE: «═══ CONOSCENZA OPERATIVA (regole) ═══ # REGOLE GHIDRA»");
    assert.strictEqual(r.ok, false, "ha accettato spazzatura: torneremmo a 103 lezioni finte");
});

test("l'archivio non e' pieno di quel blocco", () => {
    const sporche = mem.all().filter(l => /═══|CONOSCENZA OPERATIVA/.test(l.text));
    assert.strictEqual(sporche.length, 0, "in archivio ci sono " + sporche.length + " lezioni di rumore");
});

test("l'archivio non e' cresciuto a dismisura", () => {
    assert.ok(mem.all().length <= 300, "troppe lezioni: " + mem.all().length);
});

test("il richiamo a parole risponde senza esplodere", () => {
    const out = mem.recall("licenza", 5);
    assert.strictEqual(typeof out, "string");
});

test("il richiamo semantico non si rompe se Ollama non c'e'", async () => {
    // Punta a una porta morta: deve ricadere sul richiamo a parole, non alzare errore.
    const prima = process.env.OLLAMA_HOST;
    process.env.OLLAMA_HOST = "http://127.0.0.1:9";
    try {
        delete require.cache[require.resolve("../src/learningMemory.js")];
        const spento = require("../src/learningMemory.js");
        const out = await spento.recallSemantic("licenza del programma", 5);
        assert.strictEqual(typeof out, "string", "con Ollama spento la memoria deve degradare, non fallire");
    } finally {
        if (prima === undefined) delete process.env.OLLAMA_HOST; else process.env.OLLAMA_HOST = prima;
        delete require.cache[require.resolve("../src/learningMemory.js")];
    }
});
