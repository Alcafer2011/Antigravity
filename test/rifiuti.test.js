"use strict";
/**
 * rifiuti.test.js — guasto vero del 02/09/2026.
 *
 * La corsia «8K Ultra HD» rispondeva sempre «Mi dispiace, ma non posso aiutarti».
 * Non era un errore: era gpt-oss:120b-cloud (la corsia gratis di Ollama, allineata
 * alla sicurezza) che rifiutava a scatola chiusa il lavoro sul box — rootato, con
 * BusyBox e adb sulla rete. Un rifiuto è un HTTP 200, quindi la catena resiliente
 * non avanzava mai: sei motori pronti dietro, nessuno provato.
 *
 * Qui si difendono le due riparazioni:
 *   1) il rifiuto a scatola chiusa viene riconosciuto (e vale come guasto);
 *   2) le corsie specialistiche partono da un modello senza filtri.
 */
const test = require("node:test");
const assert = require("node:assert");
const LocalOrchestrator = require("../src/localOrchestrator");

test("il rifiuto secco di gpt-oss viene riconosciuto", () => {
    assert.equal(LocalOrchestrator._isRifiuto("Mi dispiace, ma non posso aiutarti con questa richiesta.", false), true);
    assert.equal(LocalOrchestrator._isRifiuto("Mi dispiace, ma non posso soddisfare questa richiesta.", false), true);
    assert.equal(LocalOrchestrator._isRifiuto("I'm sorry, but I can't help with that.", false), true);
});

test("chi ha usato gli strumenti NON viene scambiato per un rifiuto", () => {
    // Ha lavorato: un "non posso" finale è una conclusione, non un muro.
    assert.equal(LocalOrchestrator._isRifiuto("Mi dispiace, ma non posso aiutarti con questa richiesta.", true), false);
});

test("un «non posso» tecnico non fa scattare il failover", () => {
    assert.equal(LocalOrchestrator._isRifiuto("Non posso aprire quel file: il percorso non esiste.", false), false);
    assert.equal(LocalOrchestrator._isRifiuto("Ciao! Come posso aiutarti oggi?", false), false);
    assert.equal(LocalOrchestrator._isRifiuto("", false), false);
});

test("una risposta lunga è lavoro, mai un rifiuto", () => {
    const lunga = "Mi dispiace, ma non posso aiutarti. " + "x".repeat(400);
    assert.equal(LocalOrchestrator._isRifiuto(lunga, false), false);
});

test("_pickSenzaFiltri sceglie un modello uncensored CON strumenti", () => {
    const finto = Object.create(LocalOrchestrator.prototype);
    finto.getCloudChannels = () => ({ uncensored: [
        { value: "openrouter::tizio", label: "senza tool", tools: false, free: true },
        { value: "venice::caio",     label: "buono",      tools: true,  free: true },
    ]});
    assert.equal(finto._pickSenzaFiltri({ soloGratis: true }).value, "venice::caio");
});

test("se non c'è nulla di adatto ritorna null (la catena resta quella normale)", () => {
    const vuoto = Object.create(LocalOrchestrator.prototype);
    vuoto.getCloudChannels = () => ({ uncensored: [] });
    assert.equal(vuoto._pickSenzaFiltri(), null);
    const rotto = Object.create(LocalOrchestrator.prototype);
    rotto.getCloudChannels = () => { throw new Error("catalogo assente"); };
    assert.equal(rotto._pickSenzaFiltri(), null);
});
