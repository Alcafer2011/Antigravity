"use strict";

const { spawn } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");
const kaggleProxy = require("./kaggleToolProxy");

/**
 * HermesClient — usa Hermes Agent come LAVORATORE autonomo, via la sua CLI.
 *
 * PERCHÉ NON ACP: il canale ACP (src/hermesAcp.js) forza lo streaming verso
 * Ollama, e in streaming il tool-calling di Ollama è inaffidabile (i tool
 * escono come testo invece di essere eseguiti). Per questo era stato aggirato
 * e non va resuscitato. La CLI in modalità one-shot (`hermes -z "…"`) non ha
 * quel problema: Hermes esegue il suo loop completo — skills, memoria,
 * sub-agenti — e stampa il risultato.
 *
 * La sessione è FISSA (--continue antigravity): così Hermes ricorda i lavori
 * precedenti da una delega all'altra invece di ripartire da zero ogni volta.
 *
 * PERMESSI: qui NON si passa --yolo. Hermes gira con le sue conferme attive.
 * Dargli esecuzione senza approvazione è una decisione dell'utente, non un
 * default che ci prendiamo noi.
 */

const HERMES_HOME = process.env.HERMES_HOME || path.join(os.homedir(), "AppData", "Local", "hermes");
const HERMES_EXE = path.join(HERMES_HOME, "hermes-agent", "venv", "Scripts", "hermes.exe");
const SESSION = "antigravity";

// Nel menu il modello viaggia come "provider::id" (es. "gemini::gemini-2.5-pro"),
// perché a Hermes vanno passati ENTRAMBI (`--provider p -m id`): lo stesso id può
// esistere su più provider e senza provider Hermes userebbe quello di config.yaml.
const SEP = "::";

// Un modello è "senza censura" se il nome lo dice (abliterated/dolphin/uncensored),
// oppure è un coder poco filtrato (deepseek/heretic/venice): così un "coder senza
// filtri" compare col 🔓 anche se non usa quelle 3 parole storiche. Coerente con
// cloudEngine, che già marca i deepseek come uncensored+coder. NB: i modelli
// openai-codex (gpt-5.6-*) restano NON uncensored — sono ospitati da OpenAI, chiusi.
// Serve per la voce "Auto — senza censura": si sceglie il primo che Hermes ha davvero.
// ★ 2026-09-01 — allineata a cloudEngine.UNCENSORED_RX ora che OpenRouter ha
// credito e porta i veri senza-filtri (hermes-4, euryale, magnum, wizardlm...).
// 'deepseek' resta dentro perche' filtra pochissimo, ma non deve piu' VINCERE:
// prima l'auto-uncensored pescava deepseek-v4-pro (a pagamento, e filtrato) al
// posto di un dolphin. L'ordine sta in UNCENSORED_PREFER, qui sotto.
const UNCENSORED_RX = /abliterat|uncensor|dolphin|venice|heretic|unfiltered|nous-?hermes|nousresearch|hermes-3|hermes-4|euryale|magnum|mythomax|lumimaid|rocinante|anubis|wizard-?lm|airoboros|sao10k|anthracite|deepseek/i;

// Ordine di preferenza per l'auto-uncensored: prima gli abliterated (uncensored E
// con tool-calling), poi i dolphin. Stessa logica di localEngine.MODEL_PREFERENCES.
const UNCENSORED_PREFER = [
    /abliterat/i,                              // uncensored E con tool-calling
    /dolphin.*(venice|mixtral|mistral|qwen|coder)/i,
    /dolphin/i,
    /hermes-4/i, /nous-?hermes|hermes-3/i,     // Nous: senza filtri e capaci
    /euryale|magnum|wizard-?lm|mythomax/i,
    /deepseek/i                                // ultima spiaggia, non prima scelta
];

const PROVIDER_ICON = { ollama: "💻", openrouter: "☁️", huggingface: "🤗", gemini: "✨", anthropic: "🤖", "openai-codex": "🧠", nous: "🜂" };

// ★ REGOLA UTENTE (2026-07-26): scegliendo Hermes si deve poter parlare SOLO con i
//   suoi modelli GRATUITI. Sono esattamente quattro — quelli con il suffisso ':free'
//   nel catalogo Nous (verificato sul proxy: /v1/models ne espone 288, 4 con ':free').
//   Prima il menu mostrava tutti i modelli dei provider di Hermes, compresi quelli a
//   pagamento, ed era facile far partire per sbaglio una richiesta che costa.
const NOUS_PROVIDER = "nous";
const NOUS_FREE = [
    "tencent/hy3:free",              // il default storico, provato
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-xs-2.1:free",
    "stepfun/step-3.7-flash:free"
];

class HermesClient {
    /**
     * @param {object} opts
     *   cwd: cartella di lavoro
     *   model: modello di default (opzionale; altrimenti quello configurato in Hermes)
     *   logger, onEvent
     */
    constructor(opts = {}) {
        this.cwd = opts.cwd || process.cwd();
        this.model = opts.model || null;
        this.logger = opts.logger || console;
        this.onEvent = opts.onEvent || (() => {});
        this.proc = null;
        this._catalog = null;   // cache dei modelli letti dalla home di Hermes
    }

    available() { return fs.existsSync(HERMES_EXE); }

    // ---- I MODELLI DI HERMES ------------------------------------------------
    //
    // Hermes ha i SUOI provider e i SUOI modelli, già configurati nella sua home:
    //   config.yaml            → modello di default + i modelli Ollama locali
    //   provider_models_cache  → i modelli dei provider per cui HA la chiave
    // Li leggiamo da lì (niente rete, niente avvio di Hermes: sarebbe lentissimo)
    // così il menu dell'estensione mostra esattamente ciò che Hermes sa usare.

    /** Legge le due chiavi che ci servono da config.yaml, senza dipendere da un parser YAML. */
    _readConfig() {
        const out = { default: null, provider: null, ollamaModels: [] };
        let txt;
        try { txt = fs.readFileSync(path.join(HERMES_HOME, "config.yaml"), "utf8"); } catch (_) { return out; }

        // Nota: config.yaml è scritto con fine-riga Windows (CRLF), quindi i \r
        // vanno messi in conto esplicitamente, altrimenti i blocchi non matchano.
        // Blocco "model:" di primo livello → default / provider.
        const model = /^model:[ \t]*\r?\n((?:[ \t]+.*\r?\n)+)/m.exec(txt);
        if (model) {
            const d = /^[ \t]+default:[ \t]*(.+?)[ \t]*\r?$/m.exec(model[1]);
            const p = /^[ \t]+provider:[ \t]*(.+?)[ \t]*\r?$/m.exec(model[1]);
            if (d) out.default = d[1];
            if (p) out.provider = p[1];
        }
        // Elenco dei modelli Ollama (blocco providers.<qualcosa>.models con voci "- nome").
        const oll = /^[ \t]+models:[ \t]*\r?\n((?:[ \t]+-[ \t]+.+\r?\n)+)/m.exec(txt);
        if (oll) out.ollamaModels = oll[1].split(/\r?\n/).map(l => (/^[ \t]+-[ \t]+(.+?)[ \t]*$/.exec(l) || [])[1]).filter(Boolean);
        return out;
    }

    /**
     * Gli alias di modello scritti in config.yaml (blocco model.aliases).
     * ★ 2026-09-01 — serve all'auto-uncensored. La cache dei modelli di Hermes
     * (provider_models_cache.json) e' una lista POTATA e vecchia: dei veri
     * senza-filtri di OpenRouter non c'e' traccia, cosi' "auto-uncensored" finiva
     * a pescare il primo id che assomigliava a un uncensored (deepseek, o un
     * nous-hermes 13B del 2023). Gli alias invece li scrivi tu e valgono subito.
     * @returns {Array<{nome:string, provider:string, id:string}>}
     */
    _readAliases() {
        let txt;
        try { txt = fs.readFileSync(path.join(HERMES_HOME, "config.yaml"), "utf8"); } catch (_) { return []; }
        // Il blocco aliases sta dentro "model:"; prendiamo da "  aliases:" fino alla
        // prima riga con indentazione <= 2 (cioe' la chiave di primo o secondo livello
        // successiva). Fine-riga Windows messe in conto, come nel resto del file.
        const m = /^[ \t]{2,}aliases:[ \t]*\r?\n((?:[ \t]{4,}.*\r?\n|[ \t]*\r?\n)+)/m.exec(txt);
        if (!m) return [];
        const righe = m[1].split(/\r?\n/);
        const out = [];
        let corrente = null;
        for (const r of righe) {
            const capo = /^[ \t]{4}([A-Za-z0-9_.-]+):[ \t]*\r?$/.exec(r);
            if (capo) { corrente = { nome: capo[1], provider: null, id: null }; out.push(corrente); continue; }
            if (!corrente) continue;
            const campo = /^[ \t]{6,}(model|provider):[ \t]*(.+?)[ \t]*\r?$/.exec(r);
            if (!campo) continue;
            if (campo[1] === "model") corrente.id = campo[2];
            else corrente.provider = campo[2];
        }
        return out.filter(a => a.id && a.provider);
    }

    /** Il miglior alias senza filtri scritto in config.yaml, o null. */
    _pickAliasUncensored() {
        const alias = this._readAliases().filter(a => UNCENSORED_RX.test(a.id) || UNCENSORED_RX.test(a.nome));
        if (!alias.length) return null;
        for (const rx of UNCENSORED_PREFER) {
            const hit = alias.find(a => rx.test(a.id) || rx.test(a.nome));
            if (hit) return { provider: hit.provider, id: hit.id };
        }
        return { provider: alias[0].provider, id: alias[0].id };
    }

    /** I provider per cui Hermes ha davvero una chiave (li ha già interrogati almeno una volta). */
    _readProviderCache() {
        try {
            const d = JSON.parse(fs.readFileSync(path.join(HERMES_HOME, "provider_models_cache.json"), "utf8"));
            const out = {};
            for (const [prov, v] of Object.entries(d)) if (v && Array.isArray(v.models) && v.models.length) out[prov] = v.models;
            return out;
        } catch (_) { return {}; }
    }

    /**
     * Le voci del menu modelli per il provider "hermes".
     * @returns {Array<{value:string,label:string}>} value = "auto" | "auto-uncensored" | "provider::id"
     */
    getModelChoices() {
        if (!this.available()) return [];
        if (this._catalog) return this._catalog;

        // ★ TUTTI e SOLI i modelli GRATUITI (suffisso ':free'). Quelli a pagamento
        //   restano fuori: prima il menu li mostrava tutti e bastava un tocco per far
        //   partire una richiesta che costa.
        // ★ 2026-07-30 — Ogni voce ora porta il SUO provider vero. Prima ogni modello
        //   veniva etichettato "nous::<id>" anche quando nella cache stava sotto un
        //   altro provider: Hermes riceveva `--provider nous` per un modello che nous
        //   non ha, e rispondeva 404. In questa installazione un provider "nous" non
        //   esiste proprio (la cache ha openrouter, novita, gemini, nvidia, …).
        const liberi = this._freeDisponibili();
        const list = liberi.length
            ? [{ value: "auto", label: "🜂 Auto (free: " + short(liberi[0].id) + ")" }]
            : [{ value: "auto", label: "🜂 Auto (predefinito di Hermes)" }];
        for (const m of liberi) {
            const senzaFiltri = UNCENSORED_RX.test(m.id) ? " 🔓" : "";
            list.push({ value: m.provider + SEP + m.id, label: "🜂 " + short(m.id) + " · gratis" + senzaFiltri });
        }
        this._catalog = list;
        return list;
    }

    /** ★ 2026-07-30 — QUESTI DUE METODI NON ESISTEVANO.
     *  _modelArgs() li chiamava (righe 169 e 178) ma non erano scritti da nessuna
     *  parte — nemmeno nello snapshot "sano" di selfHeal. Risultato: OGNI delega
     *  con model "auto" (cioè il default di localOrchestrator e nativeAgent)
     *  moriva con "this._pickNousFree is not a function". Il canale verso Hermes
     *  era rotto in partenza, non solo scollegato dal cacciatore di bug.
     *
     *  I gratis si leggono dalla cache di Hermes SU TUTTI i provider, tenendo per
     *  ciascuno il provider vero. NOUS_FREE resta solo come ultima spiaggia se la
     *  cache è vuota — e oggi è una lista scaduta: `tencent/hy3:free` risponde
     *  404, e un provider "nous" in questa installazione non c'è. Coerente con la
     *  regola: "auto" non apre MAI il portafoglio.
     *  @returns {Array<{provider:string,id:string}>}
     */
    _freeDisponibili() {
        const out = [], visti = new Set();
        for (const [prov, ids] of Object.entries(this._readProviderCache()))
            for (const id of ids)
                if (/:free$/i.test(id) && !visti.has(id)) { visti.add(id); out.push({ provider: prov, id }); }
        if (out.length) return out;
        return NOUS_FREE.map(id => ({ provider: NOUS_PROVIDER, id }));   // ultima spiaggia
    }

    /** Il primo modello gratuito utilizzabile. → {provider, id} | null */
    _pickNousFree() {
        return this._freeDisponibili()[0] || null;
    }

    /** Il miglior gratuito SENZA censura. → {provider, id} | null */
    _pickNousFreeUncensored() {
        const liberi = this._freeDisponibili().filter(m => UNCENSORED_RX.test(m.id));
        if (!liberi.length) return null;
        for (const rx of UNCENSORED_PREFER) {
            const hit = liberi.find(m => rx.test(m.id));
            if (hit) return hit;
        }
        return liberi[0];
    }

    /** Il miglior modello senza censura fra quelli che Hermes ha. → {provider, id} | null */
    _pickUncensored(byProvider) {
        const all = [];
        for (const [prov, ids] of Object.entries(byProvider)) for (const id of ids) if (UNCENSORED_RX.test(id)) all.push({ provider: prov, id });
        if (!all.length) return null;
        for (const rx of UNCENSORED_PREFER) { const hit = all.find(m => rx.test(m.id)); if (hit) return hit; }
        return all[0];
    }

    /**
     * Traduce la scelta del menu negli argomenti della CLI.
     * "auto" → nessun override (vale il default di Hermes).
     * @returns {{args:string[], label:string|null}}
     */
    _modelArgs(choice) {
        const c = String(choice || "auto").trim();
        // ★ REGOLA NOS: "auto" non apre MAI il portafoglio. Prima prova i free Nous
        //   uno a uno, poi al limite l'uncensored fra i Nous free noti.
        if (!c || c === "auto") {
            // ★ 2026-07-30 — PRIMA IL CANALE DEL CONFIG, non OpenRouter.
            //   Il default di Hermes (config.yaml → stepfun/step-3.7-flash:free su
            //   provider "nous") è un canale DIVERSO da OpenRouter, con una quota
            //   giornaliera separata. Prima "auto" scavalcava quel default e pescava
            //   il primo :free della cache, che qui è sempre un modello OpenRouter:
            //   così ogni delega sbatteva sul tetto giornaliero gratuito di OpenRouter
            //   ("HTTP 429: free-models-per-day"). Se il default di Hermes è già un
            //   :free lo usiamo com'è — args vuoti = default puro di Hermes, così
            //   provider/modello/base_url restano coerenti e OpenRouter resta la
            //   riserva (raggiungibile scegliendo il modello esplicitamente dal menu).
            const cfg = this._readConfig();
            if (cfg.default && /:free$/i.test(cfg.default))
                return { args: [], label: cfg.default };
            const fallback = this._pickNousFree();
            // ★ 2026-07-30 — il provider è quello del modello scelto, non "nous" fisso:
            // passare `--provider nous` per un modello che sta sotto openrouter faceva
            // rispondere 404 a ogni delega "auto".
            if (fallback) return { args: ["--provider", fallback.provider, "-m", fallback.id], label: fallback.id };
            return { args: [], label: null };   // niente free noto: vale il default di Hermes
        }

        if (c === "auto-uncensored") {
            const byProvider = this._readProviderCache();
            const cfg = this._readConfig();
            if (cfg.ollamaModels.length) byProvider.ollama = cfg.ollamaModels;
            // Prima gli alias di config.yaml (scelta esplicita), poi la cache di Hermes.
            const pick = this._pickAliasUncensored() || this._pickUncensored(byProvider) || this._pickNousFreeUncensored();
            if (!pick) return { args: [], label: null };
            return { args: ["--provider", pick.provider, "-m", pick.id], label: pick.id };
        }

        const i = c.indexOf(SEP);
        if (i < 0) return { args: ["-m", c], label: c };   // id nudo: lo passiamo com'è
        const provider = c.slice(0, i), id = c.slice(i + SEP.length);
        return { args: ["--provider", provider, "-m", id], label: id };
    }

    /**
     * Delega un compito a Hermes e ritorna il suo risultato (testo).
     * @param {string} task
     * @param {object} o { model:string, onStatus:fn, timeoutMs:number, extraArgs:string[] }
     *   model: voce scelta nel menu ("auto" | "auto-uncensored" | "provider::id").
     *   extraArgs: ★ 2026-07-30 — flag CLI aggiuntivi per questa singola chiamata
     *     (es. ["--yolo"]). Serve al cacciatore di bug: la delega gira headless,
     *     dove una richiesta di conferma di Hermes non ha nessuno che risponda e
     *     manda tutto in timeout. Chi passa --yolo si prende la responsabilità di
     *     aver già fatto approvare il lavoro all'utente: NON è un default.
     */
    async delegate(task, o = {}) {
        const onStatus = o.onStatus || (() => {});
        const timeoutMs = o.timeoutMs || 10 * 60 * 1000;
        const extraArgs = Array.isArray(o.extraArgs) ? o.extraArgs : [];

        const { args: mArgs0, label } = this._modelArgs(o.model || this.model);
        const mArgs = mArgs0.concat(extraArgs);

        // ★ 2026-07-26 — KAGGLE NON SI ACCENDE PIÙ DA SOLO.
        //   Prima qui c'era un ensureUp() INCONDIZIONATO: bastava scegliere Hermes e
        //   partiva il notebook Kaggle (10-15 minuti di avvio e quota GPU bruciata),
        //   anche quando il modello scelto non aveva niente a che fare con Kaggle.
        //   Era il motivo per cui Kaggle "si accendeva da solo". Ora si accende SOLO
        //   se il modello chiesto è davvero un modello Kaggle.
        const usaKaggle = /kaggle/i.test(String(o.model || this.model || "")) || /kaggle/i.test(String(label || ""));
        if (usaKaggle) {
            try {
                const waker = require("./kaggleWaker");
                if (!(await waker.isUp())) { onStatus("🟡 Accendo il notebook Kaggle…"); await waker.ensureUp({ onStatus, logger: this.logger }); }
            } catch (_) {}
            // Il proxy traduce le tool-call TESTUALI dei modelli abliterated di Kaggle
            // nel formato nativo che Hermes sa eseguire: serve solo con Kaggle.
            try { kaggleProxy.ensureRunning(kaggleProxy.DEFAULT_PORT, this.logger); } catch (_) {}
        }
        onStatus("🜂 Hermes sta lavorando…" + (label ? " (" + short(label) + ")" : ""));

        // 1° tentativo: col modello scelto nel menu.
        let r = await this._spawnOnce(String(task), mArgs, { onStatus, timeoutMs });

        // RIPIEGO AUTOMATICO: se il modello scelto è MUTO (stdout vuoto) ma non era il
        // default, riprovo col modello predefinito di Hermes (nous/hy3), che è la corsia
        // più affidabile. È la causa reale del "Hermes non ha fornito nessun output":
        // un modello del menu non disponibile/rotto usciva vuoto e nessuno ripiegava.
        if (!r.text && !r.timedOut && mArgs0.length) {
            onStatus("↩︎ Il modello «" + short(label) + "» non ha risposto: ripiego sul predefinito di Hermes…");
            // ★ 2026-07-30 — il ripiego lascia cadere la scelta del MODELLO, non i
            // permessi: senza extraArgs qui, un secondo tentativo con --yolo si
            // sarebbe bloccato di nuovo sulle conferme.
            r = await this._spawnOnce(String(task), extraArgs, { onStatus, timeoutMs });
        }

        if (r.timedOut) {
            return "Hermes ha superato il tempo massimo (" + Math.round(timeoutMs / 60000) +
                " min) ed è stato fermato. Può essere rimasto in attesa di una conferma.\n\nOutput parziale:\n" + (r.text || "").slice(-4000);
        }
        if (!r.text) {
            return "Hermes non ha prodotto output" + (mArgs.length ? " (né col modello scelto né col predefinito)" : "") + "."
                + (r.err ? "\nstderr: " + r.err.slice(0, 1000) : "");
        }
        return r.text.slice(0, 30000);
    }

    /** Un singolo run di hermes.exe. Ritorna {text, err, timedOut} — niente eccezioni. */
    _spawnOnce(task, mArgs, { onStatus = () => {}, timeoutMs = 10 * 60 * 1000 } = {}) {
        return new Promise((resolve) => {
            const exe = this.available() ? HERMES_EXE : "hermes";
            const args = ["-z", task, "--continue", SESSION, ...mArgs];
            const p = spawn(exe, args, {
                cwd: this.cwd,
                env: Object.assign({}, process.env, { HERMES_HOME }),
                windowsHide: true
            });
            this.proc = p;
            let out = "", err = "", timedOut = false;
            const timer = setTimeout(() => { timedOut = true; try { p.kill(); } catch (_) {} }, timeoutMs);
            p.stdout.on("data", d => {
                const s = d.toString();
                out += s;
                for (const line of s.split("\n")) {
                    const t = line.trim();
                    if (t) this.onEvent({ type: "hermes", line: t.slice(0, 300) });
                }
            });
            p.stderr.on("data", d => { err += d.toString(); });
            p.on("error", e => { clearTimeout(timer); this.proc = null; resolve({ text: "", err: "impossibile avviare Hermes: " + e.message, timedOut: false }); });
            p.on("close", () => { clearTimeout(timer); this.proc = null; resolve({ text: out.trim(), err: err.trim(), timedOut }); });
        });
    }

    stop() { if (this.proc) { try { this.proc.kill(); } catch (_) {} this.proc = null; } }
}

/** Nome leggibile: via il prefisso utente/organizzazione, che nel menu è solo rumore. */
function short(id) {
    const s = String(id);
    const base = s.includes("/") ? s.slice(s.lastIndexOf("/") + 1) : s;
    return base.length > 38 ? base.slice(0, 38) + "…" : base;
}

module.exports = { HermesClient, HERMES_HOME, HERMES_EXE };
