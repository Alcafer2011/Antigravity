"use strict";
/**
 * collaudo — il controllo che gira DA SOLO a ogni avvio del server.
 *
 * Perche' esiste. Il 31/08/2026 un giro di verifica ha trovato sei guasti che
 * erano li' da settimane e che NON davano nessun errore: la catena di motori
 * scollegata dal percorso agente (25 giorni), la ripresa da checkpoint mai
 * scattata, 103 lezioni su 109 fatte di rumore, le tabelle che bloccavano il
 * telefono, il cron morto da un mese, una rotta che spegneva Ollama a ogni
 * apertura. L'app rispondeva lo stesso — solo peggio, piu' lenta, o inventando.
 *
 * E' questo il modo in cui un sistema smette di essere professionale: non si
 * rompe, degrada in silenzio. I test in test/ servono a chi modifica il codice;
 * questo file serve a TE: parla all'avvio e ti avvisa in chat se qualcosa si e'
 * scollegato, senza che tu debba andarlo a cercare.
 *
 * Regole: non alza MAI un'eccezione, non modifica niente, dura pochi secondi.
 * Si puo' lanciare anche a mano:  npm run collaudo
 */

const fs = require("fs");
const path = require("path");

const SRC = __dirname;
const leggi = (f) => { try { return fs.readFileSync(path.join(SRC, f), "utf8"); } catch (_) { return ""; } };

/** Una prova sola: nome, esito, e cosa vuol dire se e' andata male. */
async function prova(nome, fn, seFallisce) {
    try {
        const r = await fn();
        if (r === true) return { nome, ok: true };
        return { nome, ok: false, dettaglio: (typeof r === "string" ? r : seFallisce) };
    } catch (e) {
        return { nome, ok: false, dettaglio: seFallisce + " (" + e.message + ")" };
    }
}

/**
 * @param {object} opt
 * @param {object} [opt.engine]  motore locale (per provare Ollama davvero)
 * @param {number} [opt.timeoutMs]
 */
async function esegui(opt = {}) {
    const { engine = null, timeoutMs = 6000 } = opt;
    const esiti = [];

    // --- 1. I FILI SONO ATTACCATI ------------------------------------------
    // Il guasto piu' pericoloso di tutti, perche' e' invisibile: un pezzo di
    // lavoro costruito e mai collegato. Si controlla sul sorgente, non a runtime.
    const orch = leggi("localOrchestrator.js");
    esiti.push(await prova("percorso agente collegato alla catena di motori", () => {
        const h = orch.slice(orch.indexOf("async handle(prompt, ctx = {})"));
        const ramo = h.slice(h.indexOf('if (route.mode === "agent")'), h.indexOf("_runDirect(prompt, route, ctx)"));
        return /_runAgentResilient/.test(ramo);
    }, "il bottone «Agente» e' tornato su un motore solo: niente cloud gratis, niente ripiego, niente ripresa"));

    esiti.push(await prova("ripresa da checkpoint collegata", () => /agentCheckpoint/.test(orch),
        "un lavoro interrotto ricomincera' da zero (e ribrucera' il budget)"));

    esiti.push(await prova("chat diretta collegata al cloud gratis", () => {
        const d = orch.slice(orch.indexOf("async _runDirect"), orch.indexOf("_isAbort(err) {"));
        return /pickFreeCloud/.test(d);
    }, "la chat torna inchiodata al modello locale: ~90 secondi per una risposta breve"));

    esiti.push(await prova("memoria richiamata per significato", () => /recallSemantic/.test(leggi("nativeAgent.js")),
        "si e' tornati al richiamo a parole uguali: le lezioni giuste non escono"));

    // --- 2. LA PAGINA NON SI PUO' BLOCCARE ---------------------------------
    esiti.push(await prova("pagina: rete contro i cicli infiniti", () => {
        const p = (() => { try { return fs.readFileSync(path.join(SRC, "mobile-page.html"), "utf8"); } catch (_) { return ""; } })();
        return /if\(!para\.length\)\{ para\.push\(lines\[i\]\); i\+\+; \}/.test(p);
    }, "una tabella nella risposta puo' di nuovo bloccare il telefono (schermo fermo, pulsanti morti)"));

    // --- 3. NESSUNA ROTTA DISTRUGGE SU UNA GET NUDA ------------------------
    esiti.push(await prova("nessuna rotta distruttiva su GET", () => {
        const m = leggi("mobileServer.js");
        const f = m.slice(m.indexOf("async _serverEngines"), m.indexOf("async _serverEngines") + 1500);
        return /action === "status"/.test(f) && !/\?\s*"start"\s*:\s*"stop"/.test(f);
    }, "/server/engines torna a spegnere Ollama a ogni apertura dell'indirizzo"));

    // --- 4. LA MEMORIA E' PULITA -------------------------------------------
    esiti.push(await prova("memoria senza rumore", () => {
        const mem = require("./learningMemory.js");
        const tutte = mem.all();
        const sporche = tutte.filter(l => /═══|CONOSCENZA OPERATIVA/.test(l.text));
        if (sporche.length) return sporche.length + " lezioni su " + tutte.length + " sono pezzi di prompt di sistema: vanno tolte";
        return true;
    }, "l'archivio delle lezioni si e' risporcato"));

    // --- 5. I MOTORI RISPONDONO DAVVERO ------------------------------------
    if (engine) {
        esiti.push(await prova("Ollama e' vivo e ha modelli", async () => {
            const su = await Promise.race([
                engine.isOnline().catch(() => false),
                new Promise(r => setTimeout(() => r(false), timeoutMs))
            ]);
            if (!su) return "Ollama non risponde: senza di lui restano solo i provider cloud a rate-limit";
            try { await engine.discover(); } catch (_) { }
            const n = (engine.getModels && engine.getModels().length) || 0;
            return n > 0 ? true : "Ollama e' acceso ma non ha modelli installati";
        }, "Ollama non raggiungibile"));

        esiti.push(await prova("corsia Ollama cloud gratis disponibile", async () => {
            if (!engine.pickFreeCloud) return "questa versione del motore non conosce la corsia gratis";
            const m = await Promise.race([
                engine.pickFreeCloud().catch(() => null),
                new Promise(r => setTimeout(() => r(null), timeoutMs))
            ]);
            return m ? true : "nessun modello :cloud gratis trovato: si lavorera' col modello locale, molto piu' lento";
        }, "corsia gratis non verificabile"));
    }

    const falliti = esiti.filter(e => !e.ok);
    return { ok: falliti.length === 0, esiti, falliti };
}

/** Una riga sola, adatta al log e alla chat. */
function riassunto(res) {
    if (res.ok) return "✅ Collaudo all'avvio: " + res.esiti.length + " controlli, tutto a posto.";
    return "⚠️ Collaudo all'avvio: " + res.falliti.length + " controlli su " + res.esiti.length + " NON passano.\n"
        + res.falliti.map(f => "• **" + f.nome + "** — " + (f.dettaglio || "non superato")).join("\n");
}

module.exports = { esegui, riassunto };

// Lanciato a mano: npm run collaudo
if (require.main === module) {
    (async () => {
        let engine = null;
        try {
            const LE = require("./localEngine.js");
            const Eng = LE.LocalEngine || LE;
            engine = new Eng({ logger: { info() { }, error() { } } });
        } catch (_) { }
        const res = await esegui({ engine });
        for (const e of res.esiti) console.log((e.ok ? "  ok    " : "  NO    ") + e.nome + (e.ok ? "" : "\n          -> " + e.dettaglio));
        console.log("\n" + riassunto(res).split("\n")[0]);
        process.exit(res.ok ? 0 : 1);
    })();
}
