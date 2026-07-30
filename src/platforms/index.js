"use strict";

/**
 * platforms — il registro dei driver di piattaforma GPU.
 *
 * ★ 2026-07-30 — Due categorie, e la differenza è dichiarata invece che
 * lasciata capire dai commenti:
 *
 *  CABLATE  (driver reale: pulsanti accendi/spegni/stato che fanno davvero
 *           qualcosa)  → kaggle, modal
 *  DA CABLARE (sappiamo cosa serve e come si accende, ma il driver non c'è
 *           ancora) → tutte le altre. Per queste il wizard chiede comunque i
 *           campi giusti e li salva: il giorno che si scrive il driver, la
 *           configurazione è già lì.
 *
 * Aggiungere una piattaforma cablata = un file in questa cartella che esporta il
 * contratto (vedi modal.js) + una riga qui. Nient'altro: la pagina del telefono
 * e le rotte sono generiche.
 */

const CABLATE = {};
for (const nome of ["kaggle", "modal"]) {
    try { CABLATE[nome] = require("./" + nome); }
    catch (e) { console.error("[platforms] driver " + nome + " non caricato: " + e.message); }
}

/**
 * Piattaforme non ancora cablate: campi che servirebbero (2-3, veri, non un
 * modulo generico) e come si accendono. Serve al wizard e alla scelta.
 */
const DA_CABLARE = [
    { id: "beam", nome: "Beam Cloud", gratis: true, uncensoredOk: true, alwaysOn: true,
      campi: [{ chiave: "BEAM_TOKEN", etichetta: "Token Beam", dove: "https://platform.beam.cloud → Settings → API Keys" }],
      come: "Container tuoi con GPU serverless, free tier a crediti. Deploy da CLI `beam deploy`: stessa forma del driver Modal." },
    { id: "cerebrium", nome: "Cerebrium", gratis: true, uncensoredOk: true, alwaysOn: true,
      campi: [{ chiave: "CEREBRIUM_API_KEY", etichetta: "API key Cerebrium", dove: "https://dashboard.cerebrium.ai → API Keys" }],
      come: "Serverless GPU con crediti gratuiti iniziali; deploy da cortex CLI." },
    { id: "runpod", nome: "RunPod", gratis: false, uncensoredOk: true, alwaysOn: true,
      campi: [{ chiave: "RUNPOD_API_KEY", etichetta: "API key RunPod", dove: "https://www.runpod.io/console/user/settings" }],
      come: "A pagamento a ore (~0,15 €/h per una 4090). API REST completa: avvio/spegnimento pod da remoto." },
    { id: "lightning", nome: "Lightning AI Studios", gratis: true, uncensoredOk: true, alwaysOn: false,
      campi: [{ chiave: "LIGHTNING_TOKEN", etichetta: "Token Lightning", dove: "https://lightning.ai → Settings → API keys" },
              { chiave: "LIGHTNING_USER", etichetta: "Username Lightning", dove: "Il tuo nome utente sulla piattaforma" }],
      come: "~22 h GPU/mese gratis su Studio persistente. Il notebook generato da Antigravity gira senza modifiche." },
    { id: "paperspace", nome: "Paperspace Gradient", gratis: true, uncensoredOk: true, alwaysOn: false,
      campi: [{ chiave: "PAPERSPACE_API_KEY", etichetta: "API key Paperspace", dove: "https://console.paperspace.com → Team Settings → API Keys" }],
      come: "GPU gratis quando disponibili; il notebook generato è lo stesso di Kaggle." },
    { id: "colab", nome: "Google Colab", gratis: true, uncensoredOk: false, alwaysOn: false,
      campi: [],
      come: "Nessuna API di avvio: il notebook si genera e si apre a mano. ⚠️ I modelli abliterated violano i termini Google: sconsigliata per la tua corsia." },
    { id: "saturn", nome: "Saturn Cloud", gratis: true, uncensoredOk: true, alwaysOn: false,
      campi: [{ chiave: "SATURN_TOKEN", etichetta: "Token Saturn", dove: "https://app.community.saturnenterprise.io → Settings → API token" }],
      come: "30 h GPU/mese gratis. Notebook generato compatibile." },
    { id: "sagemaker-lab", nome: "SageMaker Studio Lab", gratis: true, uncensoredOk: true, alwaysOn: false,
      campi: [],
      come: "4 h GPU per sessione, gratis senza carta. Nessuna API: notebook generato, avvio a mano." },
    { id: "flyio", nome: "Fly.io", gratis: false, uncensoredOk: true, alwaysOn: true,
      campi: [{ chiave: "FLY_API_TOKEN", etichetta: "Token Fly", dove: "`fly auth token` oppure https://fly.io/user/personal_access_tokens" }],
      come: "GPU a consumo, container tuoi. Antigravity genera Dockerfile + avvio.sh già pronti." },
    { id: "koyeb", nome: "Koyeb", gratis: true, uncensoredOk: true, alwaysOn: true,
      campi: [{ chiave: "KOYEB_API_KEY", etichetta: "API key Koyeb", dove: "https://app.koyeb.com → Settings → API" }],
      come: "Free tier (CPU) + GPU a consumo. Dockerfile generato." },
    { id: "vastai", nome: "Vast.ai", gratis: false, uncensoredOk: true, alwaysOn: true,
      campi: [{ chiave: "VAST_API_KEY", etichetta: "API key Vast.ai", dove: "https://cloud.vast.ai/account/" }],
      come: "Marketplace di GPU tra privati, da ~0,10 €/h. API completa per affittare/spegnere." }
];

/** Tutti gli id conosciuti. */
function elenco() {
    return Object.keys(CABLATE).concat(DA_CABLARE.map(p => p.id));
}

function driver(id) { return CABLATE[id] || null; }
function descrizione(id) { return DA_CABLARE.find(p => p.id === id) || null; }

/** I campi che il wizard deve chiedere per questa piattaforma (2-3, non un modulo). */
function campi(id) {
    const d = driver(id);
    if (d) return d.campi || [];
    const x = descrizione(id);
    return x ? x.campi : null;
}

/** Stato di TUTTE le piattaforme: quelle cablate lo dicono davvero. */
async function stato() {
    const cablate = [];
    for (const id of Object.keys(CABLATE)) {
        try { cablate.push(Object.assign({ cablata: true }, await CABLATE[id].stato())); }
        catch (e) { cablate.push({ id, cablata: true, errore: e.message }); }
    }
    const altre = DA_CABLARE.map(p => Object.assign({ cablata: false, configurato: null }, p));
    return { cablate, daCablare: altre };
}

/** Accende una piattaforma. Se non è cablata lo dice, invece di far finta. */
async function accendi(id, o = {}) {
    const d = driver(id);
    if (!d) {
        const x = descrizione(id);
        return { ok: false, cablata: false,
            messaggio: x ? ("«" + x.nome + "» non ha ancora un driver: " + x.come)
                         : ("Piattaforma sconosciuta: " + id) };
    }
    // ★ Cantiere aperto: appunta la corsia, così il failover non la cambia a metà lavoro.
    try {
        const cant = require("../cantiere");
        const st = cant.stato();
        if (st.aperto && !st.pinPiattaforma) cant.appunta(id);
    } catch (_) {}
    return d.accendi(o);
}

async function spegni(id) {
    const d = driver(id);
    if (!d) return { ok: false, cablata: false, messaggio: "Piattaforma non cablata: " + id };
    return d.spegni();
}

async function quota(id) {
    const d = driver(id);
    if (!d) return { fonte: "nessuna", testo: "Piattaforma non cablata: nessun dato di quota verificabile." };
    return d.quota();
}

/**
 * La corsia da usare ADESSO: la prima cablata che risponde davvero.
 * Rispetta il pin del cantiere (vedi gpuFailover.pickActive).
 */
async function attiva() {
    let pin = null;
    try { const st = require("../cantiere").stato(); if (st.aperto) pin = st.pinPiattaforma; } catch (_) {}
    const ordine = pin ? [pin].concat(Object.keys(CABLATE).filter(k => k !== pin)) : Object.keys(CABLATE);
    for (const id of ordine) {
        const d = driver(id);
        if (!d) continue;
        try { if (await d.isUp()) return { id, url: d.endpoint(), appuntata: id === pin }; } catch (_) {}
    }
    return { id: null, url: null, nota: "Nessuna piattaforma accesa." };
}

module.exports = { elenco, driver, descrizione, campi, stato, accendi, spegni, quota, attiva, CABLATE, DA_CABLARE };
