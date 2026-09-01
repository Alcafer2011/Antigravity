"use strict";
// I test delle CORSIE (2026-09-01). Nascono dal riordino della scelta modello:
// la barra chiedeva provider + ricerca + modello prima ancora di poter scrivere,
// e il menu modelli poteva contenere 1635 <option> (su iPhone Safari moriva).
// Adesso si sceglie per INTENZIONE ("come vuoi che risponda") e la corsia deve
// attraversare quattro file per arrivare al motore. E' esattamente il tipo di
// filo che si stacca senza dare mai un errore: l'app risponderebbe lo stesso,
// solo ignorando quello che hai chiesto. Da qui i test di cablaggio.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const src = (f) => fs.readFileSync(path.join(__dirname, "..", "src", f), "utf8");
const radice = (f) => fs.readFileSync(path.join(__dirname, "..", f), "utf8");

test("la pagina manda la corsia al server (e non inchioda piu' il canale a 'normal')", () => {
    const p = src("mobile-page.html");
    const invii = p.match(/api\("\/send",\{[\s\S]{0,240}?\}\)/g) || [];
    assert.ok(invii.length >= 2, "non trovo le due chiamate a /send (invio e rigenera)");
    for (const inv of invii) {
        assert.match(inv, /lane:\s*LANE/, "un invio non porta la corsia: la scelta dell'utente si perde per strada");
        assert.doesNotMatch(inv, /channel:\s*"normal"\s*\}/,
            "il canale e' di nuovo fisso su 'normal': la corsia «senza filtri» non arriverebbe mai al motore");
    }
});

test("il server passa la corsia all'orchestratore", () => {
    const s = src("mobileServer.js");
    const chiamata = s.slice(s.indexOf("await this.orchestrator.handle("), s.indexOf("await this.orchestrator.handle(") + 500);
    assert.match(chiamata, /lane:\s*body\.lane/, "la corsia si ferma al server e non raggiunge l'orchestratore");
});

test("l'orchestratore normalizza la corsia e accende il canale senza filtri", () => {
    const o = src("localOrchestrator.js");
    const testa = o.slice(o.indexOf("async handle(prompt, ctx = {})"), o.indexOf("async handle(prompt, ctx = {})") + 1600);
    assert.match(testa, /ctx\.lane\s*=\s*String\(ctx\.lane\s*\|\|\s*"auto"\)/,
        "la corsia non viene piu' normalizzata all'ingresso: i percorsi sotto la vedrebbero a caso");
    assert.match(testa, /ctx\.lane === "unc".*ctx\.channel = "uncensored"/s,
        "«senza filtri» non accende piu' il canale uncensored");
});

test("la corsia arriva al motore: chat cloud e agente coi tool", () => {
    const o = src("localOrchestrator.js");
    assert.match(o, /resilientCandidates\(\{[\s\S]{0,200}?lane:\s*ctx\.lane/,
        "la chat cloud ordina di nuovo i candidati senza tener conto della corsia");
    const n = src("nativeAgent.js");
    assert.match(n, /chatToolsResilient\(messages, tools, \{[\s\S]{0,160}?lane:\s*this\.lane/,
        "l'agente coi tool ha perso la corsia: il failover tornerebbe all'ordine di sempre");
    assert.match(o, /new NativeAgent\(\{[\s\S]{0,260}?lane:\s*ctx\.lane/,
        "l'agente viene creato senza corsia");
});

test("ogni corsia sposta DAVVERO la classifica (non sono etichette)", () => {
    const CE = require("../src/cloudEngine.js");
    const Engine = CE.CloudEngine || CE;
    const e = new Engine({ root: path.join(__dirname, ".."), logger: { log() {}, error() {} } });
    // Catalogo finto: niente rete, risultati ripetibili. Un piccolo veloce, un
    // gigante gratis, un uncensored a pagamento.
    // OpenRouter acceso: e' l'unica corsia a pagamento del failover, e senza di
    // essa i modelli senza filtri e quelli a pagamento non entrerebbero proprio nel
    // pool (li' il test non misurerebbe piu' l'ordinamento ma l'esclusione).
    e.env = { OPENROUTER_ENABLE: "1" };
    // Niente provider configurati: cosi' i SEMI di sicurezza (SEED_MODELS, che sono
    // filtrati per "provider con chiave") restano fuori e il test vede solo il
    // catalogo finto. Senza questo il primo classificato arrivava dalle chiavi VERE
    // del .env: il test misurava la macchina di chi lo esegue, non il codice.
    e.providers = [];
    e.channels = {
        uncensored: [
            { value: "openrouter::nousresearch/hermes-4-70b", id: "nousresearch/hermes-4-70b", provider: "openrouter", label: "hermes-4-70b", uncensored: true, tools: true, free: false }
        ],
        normal: [
            { value: "groq::llama-3.3-70b-versatile", id: "llama-3.3-70b-versatile", provider: "groq", label: "llama 70B", uncensored: false, tools: true, free: true },
            { value: "sambanova::DeepSeek-V3-671B", id: "DeepSeek-V3-671B", provider: "sambanova", label: "DeepSeek 671B", uncensored: false, tools: true, free: true }
        ]
    };
    e._cd = {};   // nessun cooldown in mezzo
    const primo = (lane) => {
        const c = e.resilientCandidates({ lane, needTools: false, minB: 0 });
        return c.length ? c[0].value : "(vuoto)";
    };
    const veloce = primo("fast"), grosso = primo("big"), senzaFiltri = primo("unc");
    assert.notStrictEqual(veloce, grosso, "«veloce» e «grosso» danno lo stesso primo modello: una delle due non fa nulla");
    assert.match(senzaFiltri, /hermes-4/, "«senza filtri» non mette davanti il modello senza filtri");
    assert.match(veloce, /groq/, "«veloce» non parte dal provider verificato piu' rapido");
    assert.match(grosso, /671B|sambanova/, "«grosso» non mette davanti il modello piu' grande");
});

test("a parita' di tutto vince il GRATIS: il credito si spende solo se lo chiedi", () => {
    const CE = require("../src/cloudEngine.js");
    const Engine = CE.CloudEngine || CE;
    const e = new Engine({ root: path.join(__dirname, ".."), logger: { log() {}, error() {} } });
    // OpenRouter acceso: e' l'unica corsia a pagamento del failover, e senza di
    // essa i modelli senza filtri e quelli a pagamento non entrerebbero proprio nel
    // pool (li' il test non misurerebbe piu' l'ordinamento ma l'esclusione).
    e.env = { OPENROUTER_ENABLE: "1" };
    // Niente provider configurati: cosi' i SEMI di sicurezza (SEED_MODELS, che sono
    // filtrati per "provider con chiave") restano fuori e il test vede solo il
    // catalogo finto. Senza questo il primo classificato arrivava dalle chiavi VERE
    // del .env: il test misurava la macchina di chi lo esegue, non il codice.
    e.providers = [];
    e._cd = {};
    e.channels = {
        uncensored: [],
        normal: [
            { value: "openrouter::qwen/qwen-a-pagamento", id: "qwen/qwen-a-pagamento", provider: "openrouter", label: "qwen 70B", uncensored: false, tools: true, free: false },
            { value: "openrouter::qwen/qwen-gratis:free", id: "qwen/qwen-gratis:free", provider: "openrouter", label: "qwen 70B", uncensored: false, tools: true, free: true }
        ]
    };
    const c = e.resilientCandidates({ lane: "big", needTools: false, minB: 0 });
    assert.match(c[0].value, /:free/,
        "la corsia «grosso» apre il portafoglio da sola: a parita' di taglia deve vincere il gratis");
    const pagato = e.resilientCandidates({ lane: "paid", needTools: false, minB: 0 });
    assert.doesNotMatch(pagato[0].value, /:free/,
        "la corsia «col credito» non mette davanti i modelli a pagamento: allora non serve a niente");
});

test("la scelta modello non e' piu' una tendina da 1635 voci", () => {
    const p = src("mobile-page.html");
    const barra = p.slice(p.indexOf('<div class="opts">'), p.indexOf("</div>", p.indexOf('<div class="opts">')));
    assert.doesNotMatch(barra, /<select[^>]*id="llmProvider"/,
        "il selettore provider e' tornato in barra: due tendine affiancate che si chiamano tutte e due «provider»");
    assert.match(p, /<select id="model" hidden>/,
        "il <select> dei modelli non e' piu' nascosto: torna la ruota nativa che uccideva Safari");
    assert.match(p, /class="mrow"/, "l'elenco modelli non e' piu' fatto di bottoni");
});

test("in VS Code l'iframe si misura sul pannello, non sul viewport", () => {
    const h = radice("interface.html");
    assert.doesNotMatch(h, /iframe\{[^}]*height:100vh/,
        "l'iframe e' tornato alto 100vh: dentro la webview sborda sotto e con overflow:hidden si porta via la barra della chat");
    assert.match(h, /iframe\{[^}]*flex:1 1 auto/, "l'iframe non riempie piu' il contenitore");
});
