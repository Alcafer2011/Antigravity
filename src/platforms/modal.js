"use strict";

/**
 * platforms/modal — PRIMO DRIVER NUOVO dopo Kaggle, e quello che detta il
 * modello per tutti gli altri.
 *
 * ★ 2026-07-30 — Perché Modal per primo: free tier vero (crediti mensili), API
 * pulita via CLI, e soprattutto i CONTAINER SONO TUOI → i modelli abliterated
 * non violano niente, che è il problema di Colab e HuggingFace Spaces. In più
 * `@modal.web_server` dà un URL https stabile: niente ngrok, niente dominio da
 * rinnovare, niente tunnel che cade.
 *
 * Cosa serve da te (il wizard chiede solo questo):
 *   MODAL_TOKEN_ID + MODAL_TOKEN_SECRET  → https://modal.com/settings/tokens
 * Il resto (app, volume, endpoint, modello) lo costruisce e lo ricorda Antigravity.
 *
 * Quello che NESSUNO può automatizzare, e non fingiamo di poterlo fare: creare
 * l'account, accettare i termini, il CAPTCHA. Il token lo prendi tu e lo incolli.
 */

const path = require("path");
const fs = require("fs");
const b = require("./base");

const ID = "modal";
const NOME_APP = "antigravity-ollama";
const CARTELLA = path.join(b.SRC, "modal-app");

const CAMPI = [
    { chiave: "MODAL_TOKEN_ID", etichetta: "Token ID Modal", esempio: "ak-xxxxxxxxxxxx",
      dove: "https://modal.com/settings/tokens → «New token»: ti dà due valori, questo è il primo." },
    { chiave: "MODAL_TOKEN_SECRET", etichetta: "Token Secret Modal", esempio: "as-xxxxxxxxxxxx", segreto: true,
      dove: "Stessa pagina, è il secondo valore. Si vede una volta sola: copialo subito." }
];

function configurato() {
    const mancanti = CAMPI.filter(c => !b.env(c.chiave)).map(c => c.chiave);
    return { ok: mancanti.length === 0, mancanti, campi: CAMPI };
}

function ambiente() {
    return {
        MODAL_TOKEN_ID: b.env("MODAL_TOKEN_ID") || "",
        MODAL_TOKEN_SECRET: b.env("MODAL_TOKEN_SECRET") || ""
    };
}

/** L'URL dell'endpoint, imparato al primo deploy e ricordato. */
function endpoint() {
    return b.leggiStato(ID).url || null;
}

async function isUp(timeoutMs) {
    const u = endpoint();
    if (!u) return false;
    return b.sonda(u, timeoutMs || 8000);
}

/** Modal è installato? (`pip install modal`) */
async function cliPronta() {
    const r = await b.esegui(b.python(), ["-m", "modal", "--version"], { timeoutMs: 60000 });
    return { ok: r.ok, versione: (r.out || "").trim().split("\n").pop(), out: r.out };
}

async function installaCli(onStato) {
    onStato("🟡 Installo la CLI Modal (pip install modal)…");
    const r = await b.esegui(b.python(), ["-m", "pip", "install", "-q", "modal"], { timeoutMs: 10 * 60 * 1000 });
    return r.ok;
}

/**
 * Genera l'app Modal dal template parametrico. Il modello non lo scegli tu a
 * mano: esce dalla VRAM della GPU richiesta (modelAdvisor).
 */
function preparaSorgente(o = {}) {
    const { scrivi } = require("../notebookTemplate");
    const gpu = o.gpu || "T4";
    return scrivi(CARTELLA, {
        piattaforma: "modal",
        gpu,
        gpuModal: gpu,
        contesto: o.contesto || 32768,
        modello: o.modello || null,
        mirror: o.mirror || b.env("HF_MIRROR_REPO") || null,
        nomeApp: NOME_APP,
        idleSeconds: o.idleSeconds || 300,
        tunnel: "nativo"
    });
}

/** Dall'output di `modal deploy` estrae l'URL dell'endpoint web. */
function urlDaOutput(out) {
    const m = String(out || "").match(/https:\/\/[a-z0-9][a-z0-9._-]*\.modal\.run/i);
    return m ? m[0] : null;
}

/**
 * Accende (deploy) l'app Ollama su Modal e aspetta che risponda.
 * Stessa forma di kaggleWaker.ensureUp: una accensione alla volta, stati
 * raccontati mentre succedono, e un esito onesto se non sale.
 */
function accendi(o = {}) {
    const onStato = o.onStato || (() => {});
    return b.unaAllaVolta(ID, async () => {
        const cfg = configurato();
        if (!cfg.ok) {
            return { ok: false, configurato: false, mancanti: cfg.mancanti,
                messaggio: "⚠️ Manca " + cfg.mancanti.join(" e ") + " nel .env. Prendi i due valori da https://modal.com/settings/tokens e incollali nella procedura guidata: il resto lo faccio io." };
        }

        if (await isUp()) {
            onStato("✅ Modal già acceso.");
            return { ok: true, url: endpoint(), messaggio: "✅ Modal era già acceso.", gia: true };
        }

        let cli = await cliPronta();
        if (!cli.ok) {
            if (!await installaCli(onStato)) {
                return { ok: false, messaggio: "⚠️ Non riesco a installare la CLI Modal (pip install modal). Controlla che Python abbia rete." };
            }
            cli = await cliPronta();
            if (!cli.ok) return { ok: false, messaggio: "⚠️ CLI Modal installata ma non funzionante: " + (cli.out || "").slice(0, 200) };
        }

        onStato("🟡 Preparo l'app Modal (modello scelto in base alla GPU)…");
        let prep;
        try { prep = preparaSorgente(o); }
        catch (e) { return { ok: false, messaggio: "⚠️ " + e.message }; }
        onStato("🟡 Modello scelto: " + prep.cfg.tag);

        onStato("🟡 Deploy su Modal… (la prima volta costruisce l'immagine: qualche minuto)");
        const dep = await b.esegui(b.python(), ["-m", "modal", "deploy", "modal_app.py"], {
            cwd: CARTELLA, env: ambiente(), timeoutMs: 20 * 60 * 1000,
            onRiga: (r) => { const u = urlDaOutput(r); if (u) onStato("🟡 Endpoint: " + u); }
        });

        if (/token|auth|unauthor/i.test(dep.out) && !dep.ok) {
            return { ok: false, authFallita: true,
                messaggio: "⛔ Modal rifiuta i token: rigenerali su https://modal.com/settings/tokens e reincollali. (Non è un problema di rete: la CLI risponde, l'autenticazione no.)" };
        }

        const url = urlDaOutput(dep.out);
        if (!url) {
            return { ok: false, messaggio: "⚠️ Deploy senza URL. Uscita di Modal: " + (dep.out || "").trim().slice(-400) };
        }
        b.salvaStato(ID, { url, app: NOME_APP, modello: prep.cfg.tag, gpu: o.gpu || "T4", ultimoDeploy: new Date().toISOString() });

        onStato("🟡 App pubblicata. Aspetto che il modello sia caricato… (il primo avvio scarica i pesi)");
        const su = await b.attendi(url, { maxWaitMs: o.maxWaitMs || 15 * 60 * 1000, onStato });
        if (!su) {
            return { ok: false, url,
                messaggio: "⚠️ Modal ha pubblicato " + url + " ma l'endpoint non risponde ancora. Il primo scaricamento del modello può superare i 15 minuti: riprova tra poco, il volume conserva i pesi e la seconda accensione è in decine di secondi." };
        }
        return { ok: true, url, modello: prep.cfg.tag, messaggio: "✅ Modal acceso: " + url + " (" + prep.cfg.tag + ")" };
    });
}

/** Spegne l'app (i container si fermano; il volume con i pesi resta). */
async function spegni() {
    const cfg = configurato();
    if (!cfg.ok) return { ok: false, messaggio: "⚠️ Token Modal non configurati." };
    const r = await b.esegui(b.python(), ["-m", "modal", "app", "stop", NOME_APP], { env: ambiente(), timeoutMs: 3 * 60 * 1000 });
    if (r.ok) {
        b.salvaStato(ID, { spentoIl: new Date().toISOString() });
        return { ok: true, messaggio: "🔴 App Modal fermata. I pesi restano nel volume: la prossima accensione è veloce." };
    }
    return { ok: false, messaggio: "⚠️ Stop non riuscito: " + (r.out || "").trim().slice(-300) };
}

/**
 * Quota. Modal NON espone un'API di credito residuo: non lo invento.
 * Dico quello che dichiara Modal e da dove viene, e il resto lo leggi tu.
 */
async function quota() {
    const s = b.leggiStato(ID);
    return {
        fonte: "dichiarato",
        testo: "Modal dichiara crediti gratuiti mensili sul piano Starter (GPU a consumo scalata da quei crediti). Non esiste un'API pubblica del credito residuo: questo dato NON è verificato da Antigravity.",
        dove: "https://modal.com/settings/usage",
        ultimoDeploy: s.ultimoDeploy || null,
        nota: "Il consumo si taglia da solo: l'app si spegne dopo " + ((s.idleSeconds || 300) / 60) + " minuti di inattività e si riaccende alla prima richiesta."
    };
}

async function stato() {
    const cfg = configurato();
    const s = b.leggiStato(ID);
    return {
        id: ID, nome: "Modal", configurato: cfg.ok, mancanti: cfg.mancanti,
        up: cfg.ok ? await isUp() : false,
        url: s.url || null, modello: s.modello || null, gpu: s.gpu || null,
        ultimoDeploy: s.ultimoDeploy || null,
        remoto: true, alwaysOn: true, uncensoredOk: true, gratis: true
    };
}

module.exports = {
    id: ID, nome: "Modal", campi: CAMPI,
    come: "Con i due token incollati qui, Antigravity genera l'app, la pubblica su Modal e ti dà l'endpoint. "
        + "I pesi restano in un volume: la prima accensione scarica il modello (minuti), le successive sono decine di secondi. "
        + "Si spegne da sola dopo 5 minuti di inattività e si riaccende alla prima richiesta.",
    configurato, isUp, accendi, spegni, quota, stato, endpoint,
    preparaSorgente, CARTELLA, NOME_APP
};
