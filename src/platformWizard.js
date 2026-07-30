"use strict";

/**
 * platformWizard — «scegli la piattaforma», e poi ti chiedo SOLO quello che
 * serve a quella piattaforma.
 *
 * ★ 2026-07-30 — Prima c'era un modulo generico uguale per tutti: chiedeva campi
 * che per metà delle piattaforme non esistono, e non chiedeva quelli veri. Qui
 * ogni piattaforma dichiara i suoi 2-3 campi (li tiene il suo driver, o la voce
 * "da cablare" nel registro) e il wizard li chiede uno per volta, dicendo DOVE
 * si prendono.
 *
 * Cosa il wizard NON fa, e non può fare nessuno: creare l'account, accettare i
 * termini, mettere la carta, risolvere il CAPTCHA. Quelli sono tuoi. Dal token
 * in poi è tutto mio.
 */

const p = require("./platforms");
const b = require("./platforms/base");

/**
 * Passo 1 — le piattaforme tra cui scegliere, con l'unica cosa che conta per
 * decidere: è gratis? i tuoi modelli senza filtri sono ammessi? resta accesa?
 * la comando da qui?
 */
async function scelte() {
    const st = await p.stato();
    const righe = st.cablate.map(c => ({
        id: c.id, nome: c.nome, cablata: true, configurato: c.configurato,
        gratis: c.gratis !== false, uncensoredOk: c.uncensoredOk !== false, alwaysOn: !!c.alwaysOn,
        stato: c.up ? "acceso" : (c.configurato ? "spento" : "da configurare"),
        campiMancanti: c.mancanti || []
    })).concat(st.daCablare.map(d => ({
        id: d.id, nome: d.nome, cablata: false,
        configurato: (d.campi || []).length ? (d.campi || []).every(c => !!b.env(c.chiave)) : null,
        gratis: !!d.gratis, uncensoredOk: !!d.uncensoredOk, alwaysOn: !!d.alwaysOn,
        stato: "driver non ancora scritto", come: d.come
    })));

    // Ordine: prima quelle che puoi davvero accendere da qui e che ammettono i
    // tuoi modelli, poi il resto.
    righe.sort((a, b2) => (b2.cablata - a.cablata) || (b2.uncensoredOk - a.uncensoredOk) || (b2.gratis - a.gratis));
    return {
        piattaforme: righe,
        consigliata: righe.find(r => r.cablata && r.uncensoredOk && r.gratis && r.alwaysOn)
                  || righe.find(r => r.cablata) || null,
        nota: "«uncensoredOk: false» vuol dire che i modelli abliterated violano i termini di quella piattaforma: non è un giudizio mio, è il loro regolamento."
    };
}

/** Passo 2 — cosa devo chiederti per questa piattaforma (e dove lo prendi). */
function domande(id) {
    const campi = p.campi(id);
    if (campi === null) return { ok: false, error: "Piattaforma sconosciuta: " + id };
    const d = p.descrizione(id);
    const drv = p.driver(id);
    return {
        ok: true, id,
        cablata: !!drv,
        come: (drv && drv.come) || (d ? d.come : null),
        campi: campi.map(c => Object.assign({}, c, { giaPresente: !!b.env(c.chiave) })),
        nonAutomatizzabile: campi.length
            ? "Account, termini, eventuale carta e CAPTCHA li fai tu sul sito. Poi incolli qui i valori e non tocchi più niente."
            : "Questa piattaforma non ha token da incollare: si apre a mano, ma il notebook te lo genero io già configurato."
    };
}

/**
 * Passo 3 — salva le risposte nel .env (con copia di sicurezza) e verifica.
 * @param {string} id
 * @param {object} valori  { CHIAVE: "valore", ... }
 */
async function salva(id, valori = {}) {
    const campi = p.campi(id);
    if (campi === null) return { ok: false, error: "Piattaforma sconosciuta: " + id };

    const scritti = [], ignorati = [];
    for (const c of campi) {
        const v = valori[c.chiave];
        if (v === undefined || v === null || String(v).trim() === "") { ignorati.push(c.chiave); continue; }
        b.setEnv(c.chiave, String(v).trim());
        scritti.push(c.chiave);
    }

    // Verifica vera: il driver ricontrolla se ora è configurato.
    const d = p.driver(id);
    const cfg = d ? d.configurato() : { ok: campi.every(c => !!b.env(c.chiave)), mancanti: campi.filter(c => !b.env(c.chiave)).map(c => c.chiave) };

    return {
        ok: true, scritti, ignorati,
        configurato: cfg.ok, mancanti: cfg.mancanti || [],
        file: b.envPath(),
        prossimo: cfg.ok
            ? (d ? "Puoi accendere «" + id + "» dal pannello: il modello lo scelgo io dalla VRAM della GPU."
                 : "Configurazione salvata. Il driver di «" + id + "» non c'è ancora: intanto posso generarti il notebook già pronto.")
            : "Mancano ancora: " + (cfg.mancanti || []).join(", ")
    };
}

/**
 * «È davvero gratis?» — risposta onesta: dove c'è un'API di quota la leggo
 * davvero (Kaggle), altrove riporto quello che dichiara la piattaforma e da
 * quale pagina, senza garantirlo io.
 */
async function costi(id) {
    const q = await p.quota(id);
    return {
        id,
        verificato: q.fonte === "api",
        quota: q,
        avvertenza: q.fonte === "api"
            ? "Dato letto dall'API della piattaforma: è reale."
            : "Dato DICHIARATO dalla piattaforma, non verificato da Antigravity: i free tier cambiano senza preavviso. Controlla la pagina indicata prima di contarci."
    };
}

module.exports = { scelte, domande, salva, costi };
