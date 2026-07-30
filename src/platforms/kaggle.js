"use strict";

/**
 * platforms/kaggle — Kaggle vestito con lo stesso contratto degli altri driver.
 *
 * ★ 2026-07-30 — Kaggle funzionava già (kaggleWaker), ma parlava una lingua sua:
 * la pagina del telefono aveva pulsanti dedicati solo a lei. Qui la si adatta al
 * contratto comune, così un solo pannello comanda tutte le piattaforme e
 * aggiungerne una è aggiungere un file, non rifare l'interfaccia.
 *
 * Non duplica niente: delega a kaggleWaker, che resta l'unico posto in cui si
 * parla con Kaggle.
 */

const b = require("./base");
const kw = require("../kaggleWaker");

const ID = "kaggle";

const CAMPI = [
    { chiave: "KAGGLE_API_TOKEN", etichetta: "Token API Kaggle", segreto: true,
      dove: "https://www.kaggle.com/settings/api → «Create New Token»: scarica kaggle.json, il valore è il campo \"key\"." },
    { chiave: "KAGGLE_SHUTDOWN_URL", etichetta: "URL del worker di spegnimento", opzionale: true,
      dove: "Kaggle non ha un'API di stop: serve il worker Cloudflare. Senza questo campo lo spegnimento è un tap sulla pagina del notebook." }
];

function configurato() {
    const mancanti = CAMPI.filter(c => !c.opzionale && !b.env(c.chiave)).map(c => c.chiave);
    return { ok: mancanti.length === 0, mancanti, campi: CAMPI };
}

function endpoint() { return "https://" + kw.KAGGLE_HOST; }
function isUp(t) { return kw.isUp(t); }

async function accendi(o = {}) {
    const ok = await kw.ensureUp({ onStatus: o.onStato || (() => {}), size: o.size || 14, maxWaitMs: o.maxWaitMs });
    return { ok, url: endpoint(), messaggio: ok ? "✅ Kaggle acceso." : "⚠️ Kaggle non è salito (vedi i messaggi di stato)." };
}

async function spegni() {
    const r = await kw.shutdown();
    return { ok: !!r.ok, messaggio: r.message, url: r.url || null };
}

async function quota() {
    const q = await kw.quota();
    // Qui la quota è REALE: Kaggle la espone via API. È l'unica piattaforma di cui
    // possiamo dire "ti restano tot ore" senza fidarci di quello che scrive il sito.
    return Object.assign({ fonte: "api", dove: "https://www.kaggle.com/settings" }, q);
}

async function stato() {
    const cfg = configurato();
    return {
        id: ID, nome: "Kaggle Notebooks", configurato: cfg.ok, mancanti: cfg.mancanti,
        up: await isUp(), url: endpoint(), modello: "Qwen2.5-Coder-14B / Qwen3-Coder-30B abliterated",
        remoto: true, alwaysOn: false, uncensoredOk: true, gratis: true,
        nota: "30 h GPU/settimana, quota leggibile davvero (API)."
    };
}

const COME = "Già cablata: i pulsanti accendono e spengono il notebook e la quota è quella VERA letta dall'API. "
    + "Lo spegnimento automatico richiede il worker Cloudflare (KAGGLE_SHUTDOWN_URL); senza, si spegne con un tap sulla pagina.";

module.exports = { id: ID, nome: "Kaggle Notebooks", campi: CAMPI, come: COME, configurato, isUp, accendi, spegni, quota, stato, endpoint };
