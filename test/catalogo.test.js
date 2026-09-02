"use strict";
/**
 * catalogo.test.js — guasto vero del 02/09/2026, ore 14:01.
 *
 * Il catalogo cloud passò da 1594 a 1036 modelli: aimlapi (571 voci) ebbe un
 * intoppo di rete e `discover()` sostituiva il catalogo IN BLOCCO appena tornava
 * anche un solo modello. Risultato: 558 modelli spariti dal menù in silenzio —
 * e nel log nemmeno una riga, perché `logger.error` non veniva scritto sul file.
 *
 * Qui si difende il recupero: chi cade si tiene i modelli del giro precedente.
 */
const test = require("node:test");
const assert = require("node:assert");
const { CloudEngine } = require("../src/cloudEngine");

/** Motore finto: due provider, di cui uno può "cadere" a comando. */
function motore({ aimlapiCade }) {
    const e = Object.create(CloudEngine.prototype);
    e.logger = { log() {}, error() {} };
    e.providers = [{ id: "venice" }, { id: "aimlapi" }];
    e.lastDiscovery = 0;
    e.channels = {
        uncensored: [{ value: "venice::a", provider: "venice", uncensored: true, rank: 1 }],
        normal: [
            { value: "aimlapi::x", provider: "aimlapi", rank: 1 },
            { value: "aimlapi::y", provider: "aimlapi", rank: 1 },
        ],
    };
    e.configured = () => true;
    e.refreshOpenRouterCredit = async () => null;
    e.isFreeModel = () => true;
    e.getProviderIds = () => ["venice", "aimlapi"];
    e._saveCatalogCache = () => {};
    e._discoverProvider = async (p) => {
        if (p.id === "aimlapi") {
            if (aimlapiCade) throw new Error("timeout api.aimlapi.com");
            return [{ value: "aimlapi::x", provider: "aimlapi", rank: 1 },
                    { value: "aimlapi::y", provider: "aimlapi", rank: 1 }];
        }
        return [{ value: "venice::a", provider: "venice", uncensored: true, rank: 1 }];
    };
    return e;
}

test("giro sano: il catalogo contiene tutti i provider", async () => {
    const ch = await motore({ aimlapiCade: false }).discover(true);
    const tutti = ch.uncensored.concat(ch.normal);
    assert.equal(tutti.length, 3);
    assert.equal(tutti.filter(m => m.stale).length, 0);
});

test("provider caduto: i suoi modelli NON spariscono dal catalogo", async () => {
    const ch = await motore({ aimlapiCade: true }).discover(true);
    const tutti = ch.uncensored.concat(ch.normal);
    // Il guasto vero: qui prima ne restava 1 solo (venice), i 2 di aimlapi persi.
    assert.equal(tutti.length, 3, "i modelli del provider caduto vanno recuperati");
    assert.deepEqual(tutti.filter(m => m.provider === "aimlapi").map(m => m.value).sort(),
                     ["aimlapi::x", "aimlapi::y"]);
});

test("i modelli recuperati sono marcati stale (si sa che sono di ieri)", async () => {
    const ch = await motore({ aimlapiCade: true }).discover(true);
    const tutti = ch.uncensored.concat(ch.normal);
    assert.equal(tutti.filter(m => m.stale).length, 2);
    assert.equal(tutti.find(m => m.provider === "venice").stale, undefined);
});

test("niente doppioni: chi risponde vince sulla copia vecchia", async () => {
    const ch = await motore({ aimlapiCade: false }).discover(true);
    const valori = ch.uncensored.concat(ch.normal).map(m => m.value);
    assert.equal(new Set(valori).size, valori.length);
});
