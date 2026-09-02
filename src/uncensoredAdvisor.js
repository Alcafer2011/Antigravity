"use strict";
/**
 * uncensoredAdvisor — «quale modello senza filtri conviene usare?», col conto.
 *
 * ★ 2026-09-02 — Prima c'era solo `modelAdvisor`, che risponde a un'ALTRA
 * domanda: quale GGUF ci sta nella VRAM di una GPU. Per i modelli CLOUD senza
 * filtri non c'era niente, e la scelta si faceva a naso — che è il modo migliore
 * per pagare 6 volte tanto un modello che lavora peggio.
 *
 * Qui i modelli si ordinano su QUATTRO assi, con i prezzi veri presi dal
 * catalogo live di OpenRouter (non da una tabella scritta a mano che invecchia):
 *
 *   1. CAPACITÀ D'AGENTE — sa usare gli strumenti? È l'asse che pesa di più,
 *      perché un modello che non sa chiamare uno strumento non ti serve a
 *      comandare il box, per quanto sia "intelligente". Tre livelli:
 *        nativo    = dichiara `tools` fra i supported_parameters
 *        corazza+  = niente tool nativi MA famiglia addestrata a produrre JSON
 *                    strutturato (Hermes su tutti): con runReact va benissimo
 *        corazza   = ci va solo col protocollo testuale, e ogni tanto sbaglia
 *        no        = da chat, non da agente (contesto minuscolo o roleplay puro)
 *   2. POTENZA — parametri dedotti dal nome (405B, 70B, 24B…).
 *   3. CONTESTO — quanto lavoro ci sta dentro senza tagliare.
 *   4. COSTO — prezzo di UN GIRO D'AGENTE realistico, non il $/Mtok astratto:
 *      un giro consuma molto input (la trascrizione ricresce a ogni passo) e
 *      poco output. Vedi GIRO_IN / GIRO_OUT.
 *
 * Il punteggio finale è potenza+capacità+contesto DIVISO il costo: è il
 * "rapporto" che l'utente chiede. Chi non sa fare l'agente viene escluso dalla
 * classifica per uso="agente", perché per quel mestiere vale zero.
 */

const fs = require("fs");
const path = require("path");
const https = require("https");

/**
 * La chiave, cercata dove c'è davvero.
 * ★ Il chiamante può non averla: `mobileServer` non tiene un `this.env`, e il
 * processo dell'estensione non sempre ha le variabili caricate. Quindi qui si
 * ripiega sul .env di Antigravity, che è la fonte vera (vedi envFile.js).
 */
function _chiave(esplicita) {
    if (esplicita) return String(esplicita).trim();
    if (process.env.OPENROUTER_API_KEY) return String(process.env.OPENROUTER_API_KEY).trim();
    const posti = [];
    try { posti.push(require("./envFile").envFilePath()); } catch (_) {}
    posti.push(path.join(__dirname, "..", ".env"));
    for (const p of posti) {
        try {
            const m = fs.readFileSync(p, "utf8").match(/^\s*OPENROUTER_API_KEY\s*=\s*(.+)$/m);
            if (m && m[1]) return m[1].trim().replace(/^["']|["']$/g, "");
        } catch (_) { /* file assente: prova il prossimo */ }
    }
    return null;
}

/** Stessa regola di riconoscimento usata da cloudEngine: un solo posto da cambiare. */
const UNCENSORED_RX = /abliterat|uncensor|dolphin|lumimaid|mythomax|nous-?hermes|nousresearch|hermes-3|hermes-4|venice|heretic|unfiltered|neuraldaredevil|tiger.?gemma|wizard-?lm|airoboros|magnum|euryale|rocinante|anubis|weaver|sao10k|anthracite/i;

/**
 * Un giro d'agente tipico misurato sul lavoro col box: la trascrizione cresce
 * a ogni passo, quindi l'INPUT domina. Chi guarda solo il prezzo di output
 * sbaglia la stima di un ordine di grandezza.
 */
const GIRO_IN = 20000;   // token di input per giro (system + storia + osservazioni)
const GIRO_OUT = 700;    // token di output per giro (una tool-call, non un tema)
const GIRI_TIPICI = 12;  // giri per portare a casa un lavoro tipo "installa e configura"

/**
 * Famiglie addestrate a emettere JSON/tool-call strutturati anche senza il
 * supporto `tools` dell'API: con la corazza ReAct rendono quasi come i nativi.
 * NON è un giudizio a naso: Hermes e' addestrato esplicitamente al function
 * calling, e nel nostro loop e' la differenza fra "obbedisce" e "chiacchiera".
 */
const BRAVI_CON_LA_CORAZZA = /hermes|nousresearch|dolphin|wizard-?lm/i;

/** Modelli da roleplay: scrivono bene ma non eseguono compiti. */
const SOLO_ROLEPLAY = /lumimaid|mythomax|weaver|magnum|rocinante|anubis|euryale|lunaris/i;

let _cache = { quando: 0, dati: null };

function _scarica(url, chiave) {
    return new Promise((risolvi, rifiuta) => {
        const req = https.get(url, {
            timeout: 45000,
            headers: { "Authorization": "Bearer " + chiave, "User-Agent": "Antigravity/advisor" }
        }, res => {
            if (res.statusCode !== 200) { res.resume(); return rifiuta(new Error("HTTP " + res.statusCode)); }
            const pezzi = [];
            res.on("data", d => pezzi.push(d));
            res.on("end", () => {
                try { risolvi(JSON.parse(Buffer.concat(pezzi).toString("utf8"))); }
                catch (e) { rifiuta(new Error("risposta non-JSON da OpenRouter")); }
            });
        });
        req.on("error", rifiuta);
        req.on("timeout", () => { req.destroy(); rifiuta(new Error("timeout su OpenRouter")); });
    });
}

/** Parametri dedotti dal nome: "70b" → 70, "8x22b" → 176 (MoE: totali). */
function _miliardi(id) {
    const moe = /(\d+)\s*x\s*(\d+)\s*b/i.exec(id);
    if (moe) return Number(moe[1]) * Number(moe[2]);
    const m = /(\d+(?:\.\d+)?)\s*b\b/i.exec(id);
    return m ? Number(m[1]) : 0;
}

/** Livello di capacità d'agente, con la spiegazione in chiaro. */
function _capacita(m) {
    const nativi = (m.supported_parameters || []).includes("tools");
    const ctx = Number(m.context_length || 0);
    const roleplay = SOLO_ROLEPLAY.test(m.id);
    // ★ Il tool-calling nativo NON riscatta un modello da roleplay: sa emettere
    // la chiamata, ma è addestrato a raccontare, non a portare a termine compiti.
    // Senza questo, l3.1-euryale finiva primo per "capacità" mentre il gemello
    // l3.3 era scartato — stessa famiglia, giudizi opposti.
    if (nativi && roleplay) return { livello: "nativo (roleplay)", punti: 55, perche: "chiama gli strumenti in modo nativo, ma è una famiglia da roleplay: tende a raccontare invece di eseguire" };
    if (nativi) return { livello: "nativo", punti: 100, perche: "chiama gli strumenti in modo nativo" };
    if (ctx < 16000) return { livello: "no", punti: 0, perche: "contesto troppo piccolo (" + ctx + "): un agente lo riempie subito" };
    if (roleplay) return { livello: "no", punti: 5, perche: "modello da roleplay: scrive bene ma non esegue compiti" };
    if (BRAVI_CON_LA_CORAZZA.test(m.id)) return { livello: "corazza+", punti: 75, perche: "niente tool nativi, ma è addestrato a produrre JSON strutturato: con la corazza ReAct rende quasi come un nativo" };
    return { livello: "corazza", punti: 35, perche: "solo col protocollo testuale della corazza: ogni tanto sbaglia la chiamata" };
}

/**
 * Classifica i modelli senza filtri.
 * @param {object} o
 *   chiave: OPENROUTER_API_KEY
 *   uso: "agente" (default) — comandare il box, servono gli strumenti
 *        "chat"            — solo conversazione, la capacità d'agente non conta
 *   budget: euro/dollari disponibili (default 10) — per stimare quanti lavori ci stanno
 */
async function consiglia(o = {}) {
    const chiave = _chiave(o.chiave);
    if (!chiave) return { ok: false, error: "manca OPENROUTER_API_KEY (né passata, né in process.env, né nel .env di Antigravity)" };
    const uso = String(o.uso || "agente").toLowerCase();
    const budget = Number(o.budget != null ? o.budget : 10);

    let cat;
    if (_cache.dati && Date.now() - _cache.quando < 6 * 3600 * 1000) cat = _cache.dati;
    else {
        try { cat = await _scarica("https://openrouter.ai/api/v1/models", chiave); }
        catch (e) { return { ok: false, error: "catalogo OpenRouter non raggiungibile: " + e.message }; }
        _cache = { quando: Date.now(), dati: cat };
    }

    const grezzi = (cat.data || []).filter(m => UNCENSORED_RX.test(m.id));
    if (!grezzi.length) return { ok: false, error: "nessun modello senza filtri nel catalogo" };

    const voci = grezzi.map(m => {
        const pin = Number(m.pricing && m.pricing.prompt || 0) * 1e6;
        const pout = Number(m.pricing && m.pricing.completion || 0) * 1e6;
        const ctx = Number(m.context_length || 0);
        const b = _miliardi(m.id);
        const cap = _capacita(m);

        // Costo di UN giro e di un lavoro intero: il numero che conta davvero.
        const giro = (GIRO_IN * pin + GIRO_OUT * pout) / 1e6;
        const lavoro = giro * GIRI_TIPICI;

        // Potenza: scala compressa (da 70B a 405B non si guadagna 6 volte).
        const pPotenza = b > 0 ? Math.min(100, 26 * Math.log2(1 + b / 7)) : 40;
        const pContesto = Math.min(100, (ctx / 131072) * 100);
        // La capacità d'agente pesa il doppio della potenza: e' il collo di bottiglia.
        const qualita = uso === "chat"
            ? (pPotenza * 0.7 + pContesto * 0.3)
            : (cap.punti * 0.5 + pPotenza * 0.35 + pContesto * 0.15);

        // Rapporto qualità/prezzo. Il +0.002 evita di dividere per ~zero sui
        // modelli quasi gratis, che altrimenti dominerebbero comunque vadano.
        const rapporto = qualita / (giro + 0.002);

        return {
            id: m.id,
            parametriB: b || null,
            contesto: ctx,
            prezzoIn: Math.round(pin * 100) / 100,
            prezzoOut: Math.round(pout * 100) / 100,
            costoGiro: Math.round(giro * 10000) / 10000,
            costoLavoro: Math.round(lavoro * 1000) / 1000,
            lavoriColBudget: giro > 0 ? Math.floor(budget / lavoro) : null,
            agente: cap.livello,
            perche: cap.perche,
            qualita: Math.round(qualita),
            rapporto: Math.round(rapporto)
        };
    });

    // Per l'uso "agente" chi non sa eseguire è fuori classifica: non è severità,
    // è che per quel mestiere vale zero.
    const utili = uso === "chat" ? voci : voci.filter(v => v.agente !== "no");
    const scartati = uso === "chat" ? [] : voci.filter(v => v.agente === "no");

    utili.sort((a, b) => b.rapporto - a.rapporto);
    const migliore = utili[0] || null;
    const piuCapace = utili.slice().sort((a, b) => b.qualita - a.qualita)[0] || null;
    const piuEconomico = utili.slice().sort((a, b) => a.costoGiro - b.costoGiro)[0] || null;

    return {
        ok: true,
        uso, budget,
        ipotesi: { tokenInPerGiro: GIRO_IN, tokenOutPerGiro: GIRO_OUT, giriPerLavoro: GIRI_TIPICI },
        consiglio: migliore ? {
            modello: migliore.id,
            perche: "miglior rapporto fra capacità e costo: " + migliore.perche
                + "; un lavoro tipico costa circa $" + migliore.costoLavoro
                + ", quindi col budget ci stanno ~" + migliore.lavoriColBudget + " lavori.",
            alternative: {
                seServeIlMassimo: piuCapace && piuCapace.id !== migliore.id ? piuCapace.id : null,
                seServeRisparmiare: piuEconomico && piuEconomico.id !== migliore.id ? piuEconomico.id : null
            }
        } : null,
        classifica: utili,
        scartati: scartati.map(v => ({ id: v.id, perche: v.perche }))
    };
}

/** Versione leggibile a schermo (per la chat e per il terminale). */
function testo(r) {
    if (!r || !r.ok) return "Consigliere non disponibile: " + ((r && r.error) || "?");
    const righe = [];
    righe.push("MODELLI SENZA FILTRI — classifica per uso «" + r.uso + "» (budget $" + r.budget + ")");
    righe.push("Ipotesi di calcolo: " + r.ipotesi.tokenInPerGiro + " token in / "
        + r.ipotesi.tokenOutPerGiro + " out per giro, " + r.ipotesi.giriPerLavoro + " giri per lavoro.");
    righe.push("");
    for (const v of r.classifica) {
        righe.push("  " + v.id);
        righe.push("      agente: " + v.agente + "   qualità " + v.qualita + "/100   rapporto " + v.rapporto
            + (v.parametriB ? "   " + v.parametriB + "B" : "") + "   ctx " + v.contesto);
        righe.push("      $" + v.prezzoIn + "/" + v.prezzoOut + " per Mtok  →  $" + v.costoGiro
            + " a giro, $" + v.costoLavoro + " a lavoro  (~" + v.lavoriColBudget + " lavori col budget)");
        righe.push("      " + v.perche);
    }
    if (r.scartati.length) {
        righe.push("");
        righe.push("Fuori classifica per questo uso:");
        for (const s of r.scartati) righe.push("  " + s.id + " — " + s.perche);
    }
    if (r.consiglio) {
        righe.push("");
        righe.push("CONSIGLIO: " + r.consiglio.modello);
        righe.push("  " + r.consiglio.perche);
        if (r.consiglio.alternative.seServeIlMassimo) righe.push("  Se serve il massimo: " + r.consiglio.alternative.seServeIlMassimo);
        if (r.consiglio.alternative.seServeRisparmiare) righe.push("  Se serve risparmiare: " + r.consiglio.alternative.seServeRisparmiare);
    }
    return righe.join("\n");
}

module.exports = { consiglia, testo, UNCENSORED_RX };
