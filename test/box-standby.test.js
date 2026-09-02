"use strict";
/**
 * box-standby.test.js — il guasto che ha bruciato la giornata del 02/09/2026.
 *
 * L'utente ha provato tutto il giorno a installare un add-on su Kodi dalla corsia
 * «8K Ultra HD», senza riuscirci. Il motivo non era l'agente né l'add-on: alle
 * 17:21 IL BOX ERA ANDATO IN STANDBY (nel kodi.log «Got device sleep intent»).
 * Ma adbd risponde anche da addormentato e `pidof` continua a vedere Kodi, quindi
 * `stato` diceva «Kodi in esecuzione» e l'errore dell'API chiedeva «Kodi è acceso?
 * L'API è accesa?» — due domande sbagliate, perché entrambe le risposte erano sì.
 * L'agente ci ha girato intorno per ore.
 *
 * Scoperta verificata sul box: tenendo un wakelock del kernel, Kodi e il webserver
 * restano raggiungibili con schermo SPENTO (l'API ha risposto v13.5.0 a TV spenta).
 * Quindi un agente non deve MAI accendere la TV per lavorare — regola dell'utente.
 */
const test = require("node:test");
const assert = require("node:assert");
const { UltraHD8K } = require("../src/ultrahd8k");

/** Box finto: si comanda cosa risponde dumpsys e se l'API è viva. */
function box({ dorme, apiViva, schermoOn = false }) {
    const b = Object.create(UltraHD8K.prototype);
    b.cfg = { indirizzo: "1.2.3.4:5555", pacchettoKodi: "org.xbmc.kodi", apiPorta: 8080 };
    b.comandi = [];
    b.sh = async (cmd) => {
        b.comandi.push(cmd);
        if (/mWakefulness=/.test(cmd)) return "mWakefulness=" + (dorme ? "Asleep" : "Awake");
        if (/mScreenState/.test(cmd)) return "mScreenState=" + (schermoOn ? "ON" : "OFF");
        return "";
    };
    b._rpcGrezza = async () => { if (!apiViva) throw new Error("API_IRRAGGIUNGIBILE: ECONNREFUSED"); return { version: { major: 13 } }; };
    return b;
}

test("sveglio() distingue il box addormentato da quello sveglio", async () => {
    assert.equal((await box({ dorme: true,  apiViva: false }).sveglio()).sveglio, false);
    assert.equal((await box({ dorme: false, apiViva: true  }).sveglio()).sveglio, true);
});

test("la sveglia dell'AGENTE non accende mai la TV", async () => {
    const b = box({ dorme: true, apiViva: true });
    const r = await b.sveglia();
    assert.equal(r.ok, true);
    // Il wakelock sì; il tasto che accende schermo e TV via CEC, mai.
    assert.ok(b.comandi.some(c => /wake_lock/.test(c)), "deve prendere il wakelock");
    assert.ok(!b.comandi.some(c => /KEYCODE_WAKEUP/.test(c)), "NON deve premere WAKEUP");
    assert.ok(!b.comandi.some(c => /am start/.test(c)), "NON deve portare Kodi in primo piano");
});

test("se Kodi resta bloccato, CHIEDE il permesso invece di accendere la TV", async () => {
    const b = box({ dorme: true, apiViva: false });
    const r = await b.sveglia();
    assert.equal(r.ok, false);
    assert.equal(r.serveSchermo, true);
    assert.ok(!b.comandi.some(c => /KEYCODE_WAKEUP/.test(c)), "nemmeno qui accende da solo");
    assert.match(r.out, /schermo=true/);
});

test("schermo=true (richiesto dall'utente) accende davvero", async () => {
    const b = box({ dorme: true, apiViva: true });
    const r = await b.sveglia({ schermo: true });
    assert.ok(b.comandi.some(c => /KEYCODE_WAKEUP/.test(c)), "qui il risveglio è completo");
    assert.equal(r.schermoAcceso, true);
});

test("rpc(): box addormentato → si sveglia da solo e riprova, senza TV", async () => {
    const b = box({ dorme: true, apiViva: false });
    let tentativi = 0;
    b._rpcGrezza = async () => {
        tentativi++;
        if (tentativi === 1) throw new Error("API_IRRAGGIUNGIBILE: ECONNREFUSED");
        return { version: { major: 13 } };          // dopo il wakelock risponde
    };
    const r = await b.rpc("JSONRPC.Version", {});
    assert.deepEqual(r, { version: { major: 13 } });
    // Tre chiamate, ed è giusto così: (1) il tentativo vero che fallisce,
    // (2) la sonda di sveglia() — è quella che sa distinguere «bastava il
    // wakelock» da «Kodi è bloccato e serve lo schermo», cioè il messaggio
    // che il 02/09 è mancato, (3) il ritentativo. Una sonda in più su un
    // percorso d'errore vale una diagnosi giusta.
    assert.equal(tentativi, 3, "fallimento + sonda della sveglia + un solo ritentativo");
    assert.ok(!b.comandi.some(c => /KEYCODE_WAKEUP/.test(c)));
});

test("rpc(): se il box è SVEGLIO l'errore non viene mascherato", async () => {
    const b = box({ dorme: false, apiViva: false });
    await assert.rejects(() => b.rpc("JSONRPC.Version", {}), /API_IRRAGGIUNGIBILE/);
});

test("stato(): «dorme ma risponde» è uno stato BUONO, non un guasto", async () => {
    const b = box({ dorme: true, apiViva: true });
    b.connetti = async () => ({ ok: true });
    const s = await b.stato();
    assert.match(s, /LAVORA lo stesso/);
    assert.match(s, /schermo \/ TV  : spento/);
    assert.ok(!/bruciato una giornata/.test(s), "niente allarme se l'API risponde");
});

test("stato(): dorme e NON risponde → indica la cura giusta (sveglia, non api_accendi)", async () => {
    const b = box({ dorme: true, apiViva: false });
    b.connetti = async () => ({ ok: true });
    const s = await b.stato();
    assert.match(s, /op='sveglia'/);
    assert.match(s, /NON è «API da accendere»/);
});
