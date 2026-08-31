"use strict";
// I moduli portanti devono almeno CARICARSI. Sembra banale, ma qui il codice
// viene modificato anche dall'agente stesso: un errore di sintassi in uno di
// questi file si vede solo quando il server non riparte piu', cioe' tardi.
const { test } = require("node:test");
const assert = require("node:assert");

const PORTANTI = [
    "localOrchestrator.js", "nativeAgent.js", "mobileServer.js", "localEngine.js",
    "learningMemory.js", "agentCheckpoint.js", "cantiere.js", "cloudEngine.js",
    "hermesClient.js", "planner.js", "envFile.js", "liveInstructions.js"
];

for (const f of PORTANTI) {
    test("si carica: " + f, () => {
        assert.doesNotThrow(() => require("../src/" + f));
    });
}

test("il router locale classifica e sceglie un modello senza rompersi", () => {
    const LocalEngine = require("../src/localEngine.js");
    const Eng = LocalEngine.LocalEngine || LocalEngine;
    const e = new Eng({ logger: { info() {}, error() {} } });
    e.models = [
        { name: "qwen2.5-coder:7b", tools: true, uncensored: false, size: 7e9 },
        { name: "gpt-oss:120b-cloud", tools: true, remote: true, uncensored: false, size: 0 }
    ];
    const r = e.route("leggi il file src/planner.js e dimmi cosa fa", "agent");
    assert.ok(r && r.model, "il router non ha scelto nessun modello");
    assert.strictEqual(r.mode, "agent");
});
