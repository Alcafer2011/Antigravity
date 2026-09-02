"use strict";
/**
 * passi-esauriti.test.js — «Antigravity continua a fermarsi sulla mia richiesta
 * esplicita» (segnalato dall'utente il 02/09/2026).
 *
 * Non si fermava per un errore: ESAURIVA I PASSI a metà lavoro. La rete di
 * sicurezza in fondo a run() chiedeva al modello di «riassumere ciò che gli
 * strumenti hanno trovato», e arrivava una tabella indistinguibile da un lavoro
 * concluso. Peggio: quel riassunto riempiva finalText, quindi il checkpoint
 * veniva AZZERATO — e «riprendi da dove ti sei fermato» ripartiva da zero,
 * ribruciava tutti i passi e produceva un'altra tabella. Un cerchio chiuso.
 *
 * Qui si difende: il limite raggiunto si DICE, e il checkpoint SOPRAVVIVE.
 */
const test = require("node:test");
const assert = require("node:assert");
const { NativeAgent } = require("../src/nativeAgent");

/**
 * Agente finto con un motore che non chiude MAI il lavoro: chiama sempre uno
 * strumento, così il ciclo arriva in fondo ai passi. È il caso dell'utente.
 */
function agente({ chiudeAlPasso = null } = {}) {
    const eventi = [];
    const ckpt = { azzerato: false };
    const a = new NativeAgent({
        engine: {
            chat: async () => "STATO DEI LAVORI: fatto A, manca B, riparto da C.",
            chatTools: async () => ({ content: "", tool_calls: [] })
        },
        workspaceRoot: process.cwd(),
        model: "finto",
        onEvent: (e) => eventi.push(e),
        checkpoint: {
            load: () => null,
            save: () => {},
            clear: () => { ckpt.azzerato = true; }
        }
    });
    let n = 0;
    // Ogni giro chiede uno strumento => il ciclo non finisce mai da solo.
    a._chatToolsAuto = async () => {
        n++;
        if (chiudeAlPasso && n >= chiudeAlPasso) return { content: "Fatto davvero.", tool_calls: [] };
        return { content: "", tool_calls: [{ id: "t" + n, function: { name: "read_file", arguments: '{"path":"x"}' } }] };
    };
    a._exec = async () => "contenuto finto";
    return { a, eventi, ckpt, passi: () => n };
}

test("passi esauriti: l'utente viene AVVISATO che il lavoro non e finito", async () => {
    const { a, eventi } = agente();
    const out = await a.run("installa l'add-on e togli la repo vecchia", []);
    assert.match(String(out), /NON HO FINITO/);
    assert.ok(eventi.some(e => e.type === "message" && /NON HO FINITO/.test(e.text)),
        "l'avviso deve arrivare anche come evento in chat");
});

test("passi esauriti: il checkpoint NON viene azzerato (si puo riprendere)", async () => {
    const { a, ckpt } = agente();
    await a.run("un lavoro lungo", []);
    assert.equal(ckpt.azzerato, false, "azzerarlo qui distrugge la ripresa: era il guasto");
});

test("lavoro CONCLUSO davvero: nessun falso allarme, e il checkpoint si azzera", async () => {
    const { a, eventi, ckpt } = agente({ chiudeAlPasso: 3 });
    const out = await a.run("un lavoro corto", []);
    assert.ok(!/NON HO FINITO/.test(String(out)), "non deve allarmare se ha finito");
    assert.ok(!eventi.some(e => e.type === "message" && /NON HO FINITO/.test(e.text)));
    assert.equal(ckpt.azzerato, true, "finito davvero: il checkpoint va pulito");
});

test("il tetto dei passi e configurabile e non e piu 24", () => {
    // 24 erano pochi per «installa, rimuovi, cerca in rete, poi la VPN».
    const sorgente = require("fs").readFileSync(require("path").join(__dirname, "..", "src", "nativeAgent.js"), "utf8");
    const m = sorgente.match(/const MAX_STEPS = ([^;]+);/);
    assert.ok(m, "MAX_STEPS deve esistere");
    assert.match(m[1], /ANTIGRAVITY_MAX_STEPS/, "deve essere regolabile senza toccare il codice");
    assert.match(m[1], /\|\|\s*40/, "il valore di riposo deve essere 40");
});
