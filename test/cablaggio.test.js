"use strict";
// I test del CABLAGGIO. Questi sono i piu' importanti di tutti, perche'
// riguardano l'unico guasto che non da' MAI un errore: un pezzo di lavoro
// scollegato. Il 06/08 sono state costruite la catena resiliente (Ollama cloud
// gratis in testa) e la ripresa da checkpoint; per 25 giorni non sono mai
// entrate in funzione perche' il percorso agente normale non le chiamava.
// L'app rispondeva lo stesso, solo peggio. Nessun test tradizionale lo vede:
// serve controllare che i fili siano attaccati dove devono.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const src = (f) => fs.readFileSync(path.join(__dirname, "..", "src", f), "utf8");

test("il percorso AGENTE passa dalla catena resiliente, non da _runAgent nudo", () => {
    const o = src("localOrchestrator.js");
    const ramo = o.slice(o.indexOf("async handle(prompt, ctx = {})"));
    const decisione = ramo.slice(ramo.indexOf('if (route.mode === "agent")'), ramo.indexOf("_runDirect(prompt, route, ctx)"));
    assert.match(decisione, /_runAgentResilient/,
        "il bottone «Agente» e' tornato su un motore solo: niente cloud gratis, niente ripiego, niente ripresa");
});

test("la catena resiliente mette Ollama cloud gratis davanti al locale", () => {
    const o = src("localOrchestrator.js");
    const catena = o.slice(o.indexOf("async _runAgentResilient"), o.indexOf("async handle(prompt"));
    const cloud = catena.indexOf("pickFreeCloud");
    const locale = catena.indexOf('label: "locale"');
    assert.ok(cloud > 0 && locale > 0 && cloud < locale, "l'ordine dei motori e' cambiato: il locale e' finito davanti al cloud gratis");
});

test("la catena resiliente passa il checkpoint all'agente (la ripresa)", () => {
    const catena = src("localOrchestrator.js");
    assert.match(catena, /agentCheckpoint/, "la ripresa da checkpoint e' stata scollegata");
});

test("anche la chat DIRETTA prova il cloud gratis prima del locale", () => {
    const o = src("localOrchestrator.js");
    const diretta = o.slice(o.indexOf("async _runDirect"), o.indexOf("_isAbort(err) {"));
    assert.match(diretta, /pickFreeCloud/, "la chat diretta e' tornata inchiodata al modello locale (90 s per una parola)");
});

test("la memoria delle lezioni viene richiamata per SIGNIFICATO", () => {
    assert.match(src("nativeAgent.js"), /recallSemantic/, "si e' tornati al richiamo a parole uguali");
});

test("nessuna rotta del server distrugge qualcosa su una GET nuda", () => {
    const m = src("mobileServer.js");
    const f = m.slice(m.indexOf("async _serverEngines"), m.indexOf("async _serverEngines") + 1200);
    assert.doesNotMatch(f, /\?\s*"start"\s*:\s*"stop"/,
        "/server/engines e' tornato a spegnere Ollama a ogni apertura dell'indirizzo");
    assert.match(f, /action === "status"/, "manca la risposta in sola lettura");
});

test("ogni giro di renderMd consuma almeno una riga (la rete contro i cicli infiniti)", () => {
    const pagina = fs.readFileSync(path.join(__dirname, "..", "src", "mobile-page.html"), "utf8");
    assert.match(pagina, /if\(!para\.length\)\{ para\.push\(lines\[i\]\); i\+\+; \}/,
        "tolta la garanzia di avanzamento: le tabelle possono di nuovo bloccare il telefono");
});
