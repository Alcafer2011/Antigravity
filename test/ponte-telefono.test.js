"use strict";
// I test del PONTE COL TELEFONO (2026-09-01). Nascono da un bisogno concreto:
// dal letto, col solo Antigravity sul telefono, riprendere il filo di una
// conversazione di Claude Code lasciata al PC — non solo aprirne una nuova.
// Il ponte attraversa tre pezzi (motore → rotte del server → pagina) e ognuno
// è un filo che può staccarsi senza dare errore: da qui i test di cablaggio.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const src = (f) => fs.readFileSync(path.join(__dirname, "..", "src", f), "utf8");

test("claudeEngine espone listSessions e primeResume", () => {
    const CE = require("../src/claudeEngine.js");
    const E = CE.ClaudeEngine || CE;
    const e = new E({ log() {}, error() {} });
    assert.strictEqual(typeof e.listSessions, "function", "manca listSessions");
    assert.strictEqual(typeof e.primeResume, "function", "manca primeResume");
});

test("listSessions legge le sessioni dal disco con titolo, cwd e data", () => {
    const CE = require("../src/claudeEngine.js");
    const E = CE.ClaudeEngine || CE;
    const e = new E({ log() {}, error() {} });
    const list = e.listSessions({ limit: 5 });
    assert.ok(Array.isArray(list), "listSessions non torna un array");
    // Se sul PC c'è almeno una sessione, deve avere i campi che servono al telefono.
    if (list.length) {
        const s = list[0];
        for (const k of ["id", "title", "mtime"]) assert.ok(k in s, "manca il campo " + k + " nelle sessioni");
        assert.ok(String(s.id).length > 8, "l'id sessione non è plausibile");
    }
});

test("primeResume aggancia la sessione alla conversazione (--resume la userà)", () => {
    const CE = require("../src/claudeEngine.js");
    const E = CE.ClaudeEngine || CE;
    const e = new E({ log() {}, error() {} });
    e.primeResume("chatX", "sess-123");
    assert.strictEqual(e.sessions.get("chatX"), "sess-123",
        "primeResume non ha registrato la sessione: la ripresa non partirebbe");
});

test("il server pubblica le rotte del ponte", () => {
    const s = src("mobileServer.js");
    assert.match(s, /p === "\/claude\/sessions"/, "manca la rotta /claude/sessions");
    assert.match(s, /p === "\/claude\/resume"/, "manca la rotta /claude/resume");
    assert.match(s, /_claudeSessions\s*\(/, "manca l'handler _claudeSessions");
    assert.match(s, /_claudeResume\s*\(/, "manca l'handler _claudeResume");
});

test("la ripresa arriva fino a Claude: prime + cwd della sessione originale", () => {
    const s = src("mobileServer.js");
    // Al momento dell'invio, se la chat ha un aggancio, si prepara la ripresa…
    assert.match(s, /claude\.primeResume\(this\.activeId,\s*ripresa\.sessionId\)/,
        "l'invio non prepara più la ripresa: Claude ripartirebbe da zero");
    // …e si usa il cwd della sessione originale (le sessioni sono legate alla cartella).
    assert.match(s, /ripresa && ripresa\.cwd\)\s*\|\|\s*body\.workspaceRoot/,
        "la ripresa non usa più il cwd d'origine: --resume non troverebbe il filo");
});

test("la pagina ha il pulsante e il pannello di ripresa, e chiama le rotte", () => {
    const p = src("mobile-page.html");
    assert.match(p, /id="resumeBtn"/, "manca il pulsante ↩️ nell'header");
    assert.match(p, /id="resumeDrawer"/, "manca il pannello di ripresa");
    assert.match(p, /\/claude\/sessions/, "la pagina non chiede l'elenco delle sessioni");
    assert.match(p, /\/claude\/resume/, "la pagina non aggancia la sessione scelta");
    // Scegliendo una sessione, la chat deve passare al provider Claude.
    assert.match(p, /\$\("#provider"\)\.value\s*=\s*"claude"/,
        "riprendendo un filo, la chat non passa a Claude Code: il messaggio andrebbe altrove");
});
