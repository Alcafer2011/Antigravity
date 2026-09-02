"use strict";
// La sezione «8K Ultra HD» — l'apparecchio TV di casa — e i due GUASTI VERI
// trovati durante il collaudo del 02/09/2026. Come per gli altri test di questo
// progetto, ogni caso qui sotto nasce da qualcosa che si e' rotto davvero, non
// da un'ipotesi: cosi' non si ripete.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", "src");

// ── Il modulo esiste, si carica, e conosce l'apparecchio ────────────────────

test("si carica: ultrahd8k.js", () => {
    assert.doesNotThrow(() => require("../src/ultrahd8k.js"));
});

test("si carica: uncensoredAdvisor.js", () => {
    assert.doesNotThrow(() => require("../src/uncensoredAdvisor.js"));
});

test("l'apparecchio e' censito: indirizzo, ABI a 32 bit, cartella di Kodi", () => {
    const { UltraHD8K } = require("../src/ultrahd8k.js");
    const b = new UltraHD8K();
    assert.match(b.cfg.indirizzo, /^\d+\.\d+\.\d+\.\d+:\d+$/, "manca l'indirizzo ADB");
    assert.strictEqual(b.cfg.pacchettoKodi, "org.xbmc.kodi");
    assert.match(b.cfg.kodiHome, /Android\/data\/org\.xbmc\.kodi/, "la cartella di Kodi non e' quella dello scoped storage");
    // Il box e' armeabi-v7a: se qualcuno lo cambia in arm64 gli APK smettono di
    // installarsi e l'errore arriva solo mezz'ora dopo, sul dispositivo.
    assert.match(b.cfg.abi, /armeabi/, "l'ABI censita non e' a 32 bit");
});

// ── Lo strumento arriva DAVVERO ai modelli, nativi e non ────────────────────

test("ultrahd8k e' fra gli strumenti esposti al modello", () => {
    const { MODEL_TOOLS } = require("../src/nativeAgent.js");
    const t = MODEL_TOOLS.find(x => x.function.name === "ultrahd8k");
    assert.ok(t, "il tool non e' in MODEL_TOOLS: i modelli non lo vedrebbero");
    const ops = t.function.parameters.properties.op.enum;
    // Le operazioni che reggono il flusso "cerca -> installa -> configura -> guarda".
    for (const op of ["stato", "schermo", "api_accendi", "addon_cerca", "addon_installa",
        "impostazione_cerca", "impostazione_scrivi", "apk_installa", "log"]) {
        assert.ok(ops.includes(op), "manca l'operazione " + op);
    }
});

test("la corazza ReAct descrive anche ultrahd8k (modelli senza tool nativi)", () => {
    // _toolsText() e' cio' che i modelli uncensored leggono al posto dell'API
    // tools. Se il nuovo strumento non finisce li', per loro non esiste.
    const src = fs.readFileSync(path.join(SRC, "nativeAgent.js"), "utf8");
    assert.match(src, /_toolsText\(\)\s*\{[\s\S]*?MODEL_TOOLS\.map/, "_toolsText non parte da MODEL_TOOLS");
    assert.match(src, /MODEL_TOOLS\.push\(ULTRAHD_TOOL\)/, "ULTRAHD_TOOL non entra in MODEL_TOOLS");
    // Serve anche a riconoscere una tool-call scritta come TESTO.
    assert.match(src, /ALL_TOOL_NAMES[\s\S]{0,120}"ultrahd8k"/, "ultrahd8k non e' fra i nomi riconosciuti nel testo");
});

// ── La voce nel menu: senza quella, la sezione non esiste per l'utente ──────
//
// Il modulo, il tool e gli specialisti possono essere perfetti: se «8K Ultra HD»
// non e' selezionabile nella tendina accanto a Ghidra/ZW3D/Manutenzione, per chi
// usa l'app la sezione NON C'E'. Dimenticanza vera del 02/09/2026.

test("«8K Ultra HD» e' selezionabile nella tendina, accanto a Ghidra e ZW3D", () => {
    const pagina = fs.readFileSync(path.join(SRC, "mobile-page.html"), "utf8");
    const sel = /<select[^>]*id="provider"[\s\S]*?<\/select>/.exec(pagina);
    assert.ok(sel, "la tendina dei provider non c'e' piu'");
    assert.match(sel[0], /value="ultrahd8k"/, "manca la voce 8K Ultra HD nella tendina");
    assert.match(sel[0], /8K Ultra HD/, "la voce non ha il nome giusto");
    // Le compagne devono restare: la tendina e' un punto in cui e' facile
    // cancellare qualcosa mentre si aggiunge.
    for (const v of ["local", "cloud", "ghidra", "zw3d", "maintenance"]) {
        assert.match(sel[0], new RegExp('value="' + v + '"'), "sparita la voce " + v);
    }
});

test("la voce in tendina e' collegata a un agente vero, non a nulla", () => {
    const orc = fs.readFileSync(path.join(SRC, "localOrchestrator.js"), "utf8");
    assert.match(orc, /ctx\.provider === "ultrahd8k"/, "il provider non e' instradato");
    assert.match(orc, /_run8k\s*\(prompt, ctx\)/, "manca l'agente _run8k");
    // Deve portarsi dietro la conoscenza e passare dalla catena resiliente,
    // altrimenti funziona solo col motore del momento.
    const inizio = orc.indexOf("async _run8k");
    const blocco = orc.slice(inizio, inizio + 3000);
    assert.match(blocco, /kodi[\s\S]*android|android[\s\S]*kodi/, "non carica i due specialisti");
    assert.match(blocco, /_runAgentResilient\(guided, ctx, "8k"\)/, "non passa dalla catena resiliente");
    assert.match(blocco, /web_search/, "non dice all'agente che puo' cercare su internet");
});

// ── GUASTO VERO n.1 — «su» e' una preposizione italiana ─────────────────────
//
// Il primo instradamento dello specialista Android usava \bsu\b per intercettare
// il comando `su`. Risultato: "cerca SU google una notizia" finiva all'esperto di
// root invece che a quello web. Il test tiene ferme entrambe le direzioni.

test("lo specialista giusto per ogni mestiere", () => {
    const s = require("../src/specialists.js");
    const casi = [
        ["installami un add-on per i sottotitoli su kodi", "kodi"],
        ["cerca un apk per il box", "kodi"],
        ["dammi i permessi di root e fai un setprop", "android"],
        ["perche adb non riesce a scrivere in /sdcard/Android/data", "android"],
        ["disinstalla un pacchetto con pm list packages", "android"],
        ["decompila questo .exe", "ghidra"],
        ["scrivimi una macro zw3d", "zw3d"],
        ["genera un logo", "immagini"]
    ];
    for (const [domanda, atteso] of casi) {
        assert.strictEqual(s.pickSpecialist(domanda).key, atteso,
            "instradamento sbagliato per: " + domanda);
    }
});

test("«su» preposizione NON tira dentro lo specialista root — guasto del 02/09", () => {
    const s = require("../src/specialists.js");
    // Queste frasi non parlano di root: se ci finiscono, la regex e' tornata larga.
    for (const frase of ["cerca su google una notizia", "cerca su internet chi ha vinto",
        "scrivi su un file la risposta"]) {
        assert.notStrictEqual(s.pickSpecialist(frase).key, "android",
            "«su» preposizione ha attivato lo specialista android: " + frase);
    }
    const src = fs.readFileSync(path.join(SRC, "specialists.js"), "utf8");
    assert.ok(!/android:.*\\bsu\\b/.test(src), "e' tornato il segnale \\bsu\\b, che intercetta la preposizione");
});

test("i due specialisti nuovi hanno il loro testo, e dicono i vincoli che contano", () => {
    const s = require("../src/specialists.js");
    const kodi = s.pickSpecialist("installa un add-on kodi").block;
    const android = s.pickSpecialist("permessi di root e setprop").block;
    assert.ok(kodi.length > 1000, "il blocco kodi e' vuoto o troppo corto");
    assert.ok(android.length > 1000, "il blocco android e' vuoto o troppo corto");
    // I vincoli che, se dimenticati, fanno fallire il lavoro sul campo.
    assert.match(kodi, /api_accendi/, "kodi.md non dice come accendere il JSON-RPC");
    assert.match(kodi, /riavvi/i, "kodi.md non dice che Kodi rilegge gli add-on solo all'avvio");
    assert.match(android, /armeabi/, "android.md non avverte dell'ABI a 32 bit");
    assert.match(android, /chown/, "android.md non ricorda il chown dopo il push (rompe tutto in silenzio)");
});

// ── GUASTO VERO n.2 — la rotta leggeva un `this.env` inesistente ────────────
//
// La rotta /modelli/uncensored passava `this.env.OPENROUTER_API_KEY`, ma
// mobileServer NON ha un `this.env`: la chiave arrivava undefined e il
// consigliere rispondeva "manca la chiave" pur essendoci nel .env.

test("il consigliere trova la chiave da solo, senza che il chiamante gliela passi", () => {
    const src = fs.readFileSync(path.join(SRC, "uncensoredAdvisor.js"), "utf8");
    assert.match(src, /function _chiave/, "manca il ripiego per trovare la chiave");
    assert.match(src, /OPENROUTER_API_KEY\\s\*=/, "non legge la chiave dal .env");
    // Senza chiave da nessuna parte deve dirlo in chiaro, non esplodere.
    const adv = require("../src/uncensoredAdvisor.js");
    assert.strictEqual(typeof adv.consiglia, "function");
    assert.strictEqual(typeof adv.testo, "function");
    assert.match(adv.testo({ ok: false, error: "prova" }), /prova/);
});

test("il server pubblica la rotta del consigliere senza filtri", () => {
    const src = fs.readFileSync(path.join(SRC, "mobileServer.js"), "utf8");
    assert.match(src, /"\/modelli\/uncensored"/, "la rotta non e' registrata");
    assert.match(src, /_modelliUncensored\s*\(req, res\)/, "manca il gestore della rotta");
});

// ── Il giudizio del consigliere: le regole che non devono sbiadire ──────────

test("un modello da roleplay non diventa un buon agente solo perche' ha i tool nativi", () => {
    // Prima della correzione l3.1-euryale (roleplay CON tool nativi) finiva primo
    // per capacita', mentre il gemello l3.3 era scartato: stessa famiglia, giudizi
    // opposti. Ora esiste il livello "nativo (roleplay)" col punteggio abbassato.
    const src = fs.readFileSync(path.join(SRC, "uncensoredAdvisor.js"), "utf8");
    assert.match(src, /nativo \(roleplay\)/, "manca il livello che declassa i roleplay con tool nativi");
    assert.match(src, /SOLO_ROLEPLAY/, "manca l'elenco delle famiglie da roleplay");
    assert.match(src, /BRAVI_CON_LA_CORAZZA/, "manca l'elenco di chi rende bene con la corazza");
});

test("il costo e' calcolato su un giro d'agente, non sul prezzo per milione", () => {
    // Guardare solo il $/Mtok sbaglia la stima di un ordine di grandezza: in un
    // giro d'agente l'input domina, perche' la trascrizione ricresce a ogni passo.
    const src = fs.readFileSync(path.join(SRC, "uncensoredAdvisor.js"), "utf8");
    assert.match(src, /GIRO_IN\s*=\s*\d+/, "manca l'ipotesi sui token di input per giro");
    assert.match(src, /GIRO_OUT\s*=\s*\d+/, "manca l'ipotesi sui token di output per giro");
    const adv = require("../src/uncensoredAdvisor.js");
    assert.match(adv.testo({ ok: false, error: "x" }), /non disponibile/);
});

// ── Il permesso dello strumento resta una scelta dell'utente ────────────────

test("le operazioni che toccano il box passano dal permesso, non lo scavalcano", () => {
    const src = fs.readFileSync(path.join(SRC, "nativeAgent.js"), "utf8");
    const inizio = src.indexOf('if (name === "ultrahd8k")');
    assert.ok(inizio > 0, "il dispatch di ultrahd8k non c'e' piu'");
    // Fino all'inizio del blocco successivo (ZW3D), non a un numero di caratteri
    // a caso: il dispatch cresce, e un taglio fisso fa fallire il test per finta.
    const fine = src.indexOf("---- ZW3D", inizio);
    const blocco = src.slice(inizio, fine > 0 ? fine : inizio + 12000);
    assert.match(blocco, /_needApproval/, "nessuna richiesta di approvazione: il tool scavalcherebbe i permessi");
    // Le operazioni distruttive devono chiedere; quelle di sola lettura no.
    for (const op of ["apk_installa", "addon_rimuovi", "impostazione_scrivi", "comando"]) {
        assert.ok(blocco.includes('case "' + op + '"'), "manca l'operazione " + op);
    }
});
