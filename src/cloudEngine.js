"use strict";

const https = require("https");
const fs = require("fs");
const path = require("path");
const registry = require("./providerRegistry");

/**
 * CloudEngine — potenza extra opzionale, MULTI-PROVIDER (tutti OpenAI-compat).
 *
 * Il motore LOCALE (Ollama) resta il default e l'unico per l'uncensored offline.
 * Questo motore aggiunge modelli cloud gratuiti, su DUE CANALI:
 *   - "uncensored": modelli senza filtri (via OpenRouter :free → dolphin-venice,
 *     hermes-405b, ecc.). Su HuggingFace free NON esistono (tutti su featherless,
 *     disattivato), quindi l'uncensored cloud arriva da OpenRouter.
 *   - "normale": modelli allineati potenti/veloci (HuggingFace, Groq, OpenRouter).
 *
 * Provider attivi = quelli con chiave nel .env. Catalogo DINAMICO (si aggiorna da
 * solo interrogando le API). Ogni voce porta con sé il suo provider ("prov::id"),
 * così la chat sa dove instradare. Barra di UTILIZZO: token/richieste/costo stimato
 * (persistiti, azzerati a inizio mese) verso un budget mensile.
 */

const CATALOG_TTL = 10 * 60 * 1000;
const DEFAULT_PRICE_PER_MTOK = 0.20;
const SEP = "::"; // separatore provider::modelId nel value

const UNCENSORED_RX = /abliterat|uncensor|dolphin|lumimaid|mythomax|nous-?hermes|nousresearch|hermes-3|hermes-4|venice|heretic|unfiltered|neuraldaredevil|tiger.?gemma|wizard-?lm|airoboros|magnum|euryale|rocinante|anubis|weaver|sao10k|anthracite/i;

// Provider HF: raggiungibili dal free (featherless escluso, ospita gli uncensored).
const HF_REACHABLE = [
    "novita", "nscale", "deepinfra", "together", "hyperbolic",
    "sambanova", "fireworks-ai", "nebius", "cohere", "hf-inference", "cerebras", "groq"
];

class CloudEngine {
    constructor(logger = console, opts = {}) {
        this.logger = logger;
        this.rootDir = opts.rootDir || process.cwd();
        this.storageDir = opts.storageDir || this.rootDir;
        this.env = this._loadEnv();
        this.budgetUsd = parseFloat(this.env.HF_MONTHLY_BUDGET_USD || "0.10") || 0.10;
        this.pricePerMtok = parseFloat(this.env.HF_PRICE_PER_MTOK || "") || DEFAULT_PRICE_PER_MTOK;

        this.hfReachable = new Set(HF_REACHABLE);
        if (this.env.HF_PROVIDERS) {
            for (const p of this.env.HF_PROVIDERS.split(",").map(s => s.trim().toLowerCase()).filter(Boolean)) {
                this.hfReachable.add(p);
            }
        }

        // Registro provider: solo quelli con chiave presente.
        this.providers = this._buildProviders();

        this.channels = { uncensored: [], normal: [] };
        this.lastDiscovery = 0;
        this._usageFile = path.join(this.storageDir, "cloud-usage.json");
        this._catalogFile = path.join(this.storageDir, "cloud-catalog.json");
        this.usage = this._loadUsage();
        this._loadCatalogCache();

        // ---- Budget richieste per provider (letto dagli header di risposta) ----
        // ★ 2026-07-24 — Quasi tutti i free tier NON limitano il totale giornaliero
        // ma le richieste al MINUTO. Cerebras: 5/min con 2400/giorno. L'agente ne
        // spara 6-8 di fila (tool call → risposta → altro tool) e prende 429 pur
        // avendo 2399 richieste ancora disponibili: sembra "chiave esaurita" e non
        // lo è. Qui teniamo il conto VERO, letto dagli header x-ratelimit-*, e il
        // router SALTA il provider saturo per i pochi secondi che servono, invece
        // di bruciarlo con un cooldown da mezz'ora.
        this._rateFile = path.join(this.storageDir, "cloud-rate.json");
        this._rate = this._loadRate();      // provId -> { limMin, remMin, remDay, until, at }
        this._recent = {};                  // provId -> [timestamp] finestra 60s
        this._refreshTimer = null;
    }

    _buildProviders() {
        // Ogni provider del registro con la sua chiave in .env (o env di processo)
        // diventa ATTIVO automaticamente. Così basta incollare una nuova chiave:
        // host/endpoint sono già nel registro, nessuna configurazione manuale.
        const p = [];
        for (const def of registry.PROVIDERS) {
            const key = this.env[def.env] || process.env[def.env]
                || (def.id === "google" ? (this.env.GEMINI_API_KEY || process.env.GEMINI_API_KEY) : null);
            if (!key) continue;
            // ★ 2026-07-24 — provider che oltre alla chiave vogliono un secondo dato
            // nell'INDIRIZZO (Cloudflare: l'ID account sta dentro l'URL). Se manca,
            // il provider resta spento invece di fallire a ogni chiamata.
            let host = def.host, chatPath = def.chatPath, modelsPath = def.modelsPath || null;
            if (def.needsEnv) {
                const extra = this.env[def.needsEnv] || process.env[def.needsEnv];
                if (!extra) {
                    this.logger.log && this.logger.log(`[CloudEngine] ${def.id}: chiave presente ma manca ${def.needsEnv} nel .env → provider non attivato`);
                    continue;
                }
                const sub = s => String(s || "").replace(/\{ACCOUNT\}/g, extra);
                chatPath = sub(chatPath); modelsPath = modelsPath ? sub(modelsPath) : null;
            }
            p.push({
                id: def.id, label: def.label.replace(/ \(.*\)$/, ""), key,
                host, chatPath, modelsPath,
                billed: !!def.billed
            });
        }
        return p;
    }

    configured() { return this.providers.length > 0; }
    getProviderIds() { return this.providers.map(p => p.id); }
    _provider(id) { return this.providers.find(p => p.id === id); }

    // ---- Gestione chiavi facilitata --------------------------------------

    /** Elenco di TUTTI i provider noti con: se è configurato, se è gratis, link. */
    listKnownProviders() {
        const active = new Set(this.getProviderIds());
        return registry.all().map(p => Object.assign({}, p, { configured: active.has(p.id) }));
    }
    /** Solo i provider gratis NON ancora configurati → suggerimenti utili. */
    freeSuggestions() {
        const active = new Set(this.getProviderIds());
        return registry.freeSuggestions().filter(p => !active.has(p.id));
    }
    /** Rileva il provider da una chiave incollata (per l'auto-compilazione). */
    detectKey(key) { return registry.detectProvider(key); }

    /**
     * Salva una chiave nel .env (aggiorna se esiste, altrimenti la aggiunge) e
     * RICARICA i provider a caldo. Se providerId è dato, usa la sua variabile;
     * altrimenti la rileva dalla chiave. Ritorna { ok, provider, env } o { ok:false }.
     */
    saveKey(key, providerId, opts = {}) {
        key = registry.normalizeKey(key);            // ★ toglie spazi/virgolette/Bearer/"NOME="
        if (!key) return { ok: false, error: "chiave vuota" };
        // ★ 2026-07-31 — un provider scelto/rilevato dev'essere ESPLICITO. Il fallback
        //   "indovina dalla forma" resta solo quando manca del tutto una scelta, MA
        //   non deve poter finire su un provider a caso: se non c'è un best chiaro,
        //   meglio fermarsi e chiedere che sovrascrivere la variabile sbagliata.
        let def = providerId ? registry.byId(providerId) : (registry.detectProvider(key).best || null);
        if (def && !def.env) def = registry.byId(def.id); // publicView → voce piena
        if (!def) return { ok: false, error: "provider non riconosciuto: specifica quale" };
        const envName = def.env;
        const envPath = path.join(this.rootDir, ".env");
        let txt = "";
        try { txt = fs.readFileSync(envPath, "utf8"); } catch (_) { txt = ""; }
        // ★ 2026-07-31 — RETE DI SICUREZZA: non toccare mai il .env senza un backup.
        //   Se una risoluzione sbagliata sovrascrive la chiave di un altro provider
        //   (è quello che è successo con groq), la copia .env.bak permette di
        //   recuperarla. Teniamo l'ultima copia buona prima di ogni scrittura.
        if (txt) { try { fs.writeFileSync(envPath + ".bak", txt, "utf8"); } catch (_) {} }
        // ★ 2026-07-31 — SALVAGUARDIA ANTI-CORRUZIONE: se questa variabile contiene
        //   GIÀ una chiave DIVERSA e la risoluzione è solo AUTOMATICA (nessuna
        //   conferma esplicita dell'utente), NON la sovrascriviamo alla cieca:
        //   segnaliamo il conflitto così il chiamante può chiedere conferma. Con
        //   opts.confirmOverwrite (l'utente ha scelto quel provider) si procede.
        {
            const prev = this._loadEnv()[envName];
            if (prev && prev !== key && !opts.confirmOverwrite) {
                return { ok: false, conflict: true, provider: def.id, env: envName, label: def.label,
                         error: "«" + envName + "» contiene già una chiave diversa (" + def.label + "). Conferma per sovrascriverla." };
            }
        }
        // ★ 2026-07-30 — NORMALIZZA I FINE-RIGA prima di cercare/sostituire. Un .env
        // con un \r solitario (vecchio stile Mac, o incollato da certi editor) teneva
        // la riga della chiave "incollata" a un commento: non veniva né trovata qui
        // (→ chiave duplicata) né letta da _loadEnv (→ "salvata ma non attiva"). È
        // esattamente il bug ArliAI. Ora ogni riga è separata da un \n vero.
        txt = txt.replace(/\r\n?/g, "\n");
        const line = envName + "=" + key;
        // [ \t] invece di \s: non deve mai attraversare più righe.
        const rx = new RegExp("^[ \\t]*#?[ \\t]*" + envName + "[ \\t]*=.*$", "m");
        if (rx.test(txt)) txt = txt.replace(rx, line);
        else txt = txt.replace(/\n*$/, "") + "\n" + line + "\n";
        try { fs.writeFileSync(envPath, txt, "utf8"); }
        catch (e) { return { ok: false, error: "scrittura .env fallita: " + e.message }; }
        // ricarica a caldo
        this.env = this._loadEnv();
        this.providers = this._buildProviders();
        this.lastDiscovery = 0; // forza un nuovo catalogo alla prossima discover()
        return { ok: true, provider: def.id, env: envName, label: def.label };
    }

    // ---- Identificazione DAL VIVO (autorevole) ----------------------------
    //
    // ★ 2026-07-30 — Il rilevamento per FORMA sbaglia quando più provider usano
    // lo stesso formato (sk-, hex-32, JWT, UUID…) o quando una chiave nuova non
    // matcha nessuna regex. La verità la sa solo l'endpoint: qui PROVIAMO la
    // chiave contro i provider plausibili e vediamo chi risponde 200. Così
    // "incolla e basta" diventa preciso: la chiave finisce sul provider giusto
    // anche se la forma è ambigua o l'utente ha scelto quello sbagliato.

    /** Prova una chiave (non ancora salvata) contro UN provider.
     *  @returns {Promise<'live'|'quota'|'dead'|'unreachable'|'maybe'>}
     *   live = autentica e usabile · quota = autentica ma senza credito ·
     *   dead = 401/403 (non è di questo provider) · maybe = passa ma endpoint/
     *   modello non combacia (404) · unreachable = rete/timeout/5xx. */
    _probeKeyAgainst(def, key, timeoutMs = 12000) {
        return new Promise((resolve) => {
            const https = require("https");
            if (!def || !def.host) return resolve("unreachable");
            const ngrok = /ngrok/i.test(def.host) ? { "ngrok-skip-browser-warning": "true" } : {};
            const usaModels = !!def.modelsPath;
            const p = usaModels ? def.modelsPath : def.chatPath;
            if (!p) return resolve("unreachable");
            const method = usaModels ? "GET" : "POST";
            const body = usaModels ? null : JSON.stringify({
                model: (def.models && def.models[0]) || "gpt-4o-mini",
                messages: [{ role: "user", content: "ok" }], max_tokens: 1
            });
            const headers = Object.assign({ "Authorization": "Bearer " + key, "User-Agent": "Antigravity/1.0" }, ngrok);
            if (body) { headers["Content-Type"] = "application/json"; headers["Content-Length"] = Buffer.byteLength(body); }
            let done = false;
            const finish = (v) => { if (!done) { done = true; resolve(v); } };
            const req = https.request({ host: def.host, path: p, method, timeout: timeoutMs, headers }, (rs) => {
                let d = ""; rs.on("data", c => { if (d.length < 4000) d += c; });
                rs.on("end", () => {
                    const code = rs.statusCode || 0;
                    if (code === 401 || code === 403) return finish("dead");
                    if (code === 402 || code === 429 || /insufficient|not enough|balance|quota|payment required|out of funds/i.test(d)) return finish("quota");
                    if (code >= 200 && code < 300) return finish("live");
                    // 410 / messaggi di manutenzione = SERVIZIO giù (non colpa della
                    // chiave): es. GitHub Models "retirement_brownout".
                    if (code === 0 || code >= 500 || code === 410 || /unavailable|retirement|brownout|maintenance|temporarily/i.test(d)) return finish("unreachable");
                    return finish("maybe"); // 404 & co: la chiave è PASSATA (non 401), ma endpoint/modello non combacia
                });
            });
            req.on("error", () => finish("unreachable"));
            req.on("timeout", () => { req.destroy(); finish("unreachable"); });
            if (body) req.write(body); req.end();
        });
    }

    /** Identifica dal vivo a chi appartiene una chiave incollata.
     *  Prova i provider PLAUSIBILI (per forma) e restituisce quello che autentica.
     *  @returns {Promise<{key, best, tested:[{id,label,status}], candidates}>}
     *   best = provider vincente (con liveStatus) o null se nessuno autentica. */
    async identifyKeyLive(rawKey, opts = {}) {
        const key = registry.normalizeKey(rawKey);
        if (!key) return { key: "", best: null, tested: [], candidates: [] };
        const det = registry.detectProvider(key);
        // Ordine di prova: prima la scelta ESPLICITA dell'utente (se c'è), poi il
        // rilevato, poi gli altri candidati per forma. Così se l'utente ha scelto
        // un provider e la chiave lì funziona, NON gliela spostiamo altrove.
        let ids = [];
        if (opts.prefer) ids.push(opts.prefer);
        if (det.best && ids.indexOf(det.best.id) < 0) ids.push(det.best.id);
        for (const c of det.candidates) if (ids.indexOf(c.id) < 0) ids.push(c.id);
        // Aggiungi SEMPRE ogni provider la cui regex accetta la chiave, anche quando
        // il rilevamento si era fermato a un prefisso "forte". Es.: un UUID matcha sia
        // Scaleway sia ArliAI → vanno provati entrambi, decide il test dal vivo. Senza
        // questo, la short-circuit di detectProvider ne provava uno solo (quello
        // sbagliato) e si arrendeva.
        for (const p of registry.PROVIDERS)
            if (p.detect && p.detect.test(key) && ids.indexOf(p.id) < 0) ids.push(p.id);
        ids = ids.slice(0, opts.max || 6);
        const tested = [];
        for (const id of ids) {
            const def = registry.byId(id);
            if (!def || def.needsEnv) continue;   // needsEnv (es. Cloudflare) non è testabile senza l'ID account
            const status = await this._probeKeyAgainst(def, key);
            tested.push({ id, label: def.label, status });
            // ★ 2026-07-31 — LA SCELTA ESPLICITA È AUTOREVOLE. Se l'utente ha
            //   indicato un provider e la chiave lì AUTENTICA (live OPPURE quota:
            //   quota = chiave valida, manca solo il credito), ci fermiamo SUBITO.
            //   Prima il ciclo proseguiva e poteva "preferire" un altro provider
            //   che rispondeva live, spostando la chiave altrove e sovrascrivendo
            //   la chiave già presente lì (è così che spariva la chiave di groq).
            if (id === opts.prefer && (status === "live" || status === "quota")) break;
            if (status === "live") break;         // vinto: risposta autorevole, ci fermiamo
        }
        // Vincitore: se c'è una scelta esplicita che ha autenticato, vince LEI.
        // Altrimenti il primo live, altrimenti il primo quota.
        const preferOk = opts.prefer && tested.find(t => t.id === opts.prefer && (t.status === "live" || t.status === "quota"));
        const live = tested.find(t => t.status === "live");
        const quota = tested.find(t => t.status === "quota");
        const win = preferOk || live || quota || null;
        return {
            key,
            best: win ? Object.assign(registry.publicView(registry.byId(win.id)), { liveStatus: win.status }) : null,
            tested,
            candidates: det.candidates,
            // stato del provider ESPLICITamente scelto (se c'è): serve al chiamante
            // per decidere se una "correzione" è lecita (solo se lì è morto).
            preferStatus: opts.prefer ? ((tested.find(t => t.id === opts.prefer) || {}).status || "untested") : null
        };
    }

    // ---- .env -------------------------------------------------------------

    _loadEnv() {
        const out = {};
        try {
            const txt = fs.readFileSync(path.join(this.rootDir, ".env"), "utf8");
            // ★ split anche sul \r SOLITARIO (vecchio stile Mac): senza, una riga
            // "commento\rNOME=chiave" resterebbe un unico commento e la chiave non
            // verrebbe mai letta (bug ArliAI).
            for (const line of txt.split(/\r\n|\r|\n/)) {
                const s = line.trim();
                if (!s || s.startsWith("#")) continue;
                const eq = s.indexOf("=");
                if (eq < 0) continue;
                const k = s.slice(0, eq).trim();
                let v = s.slice(eq + 1).trim();
                if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
                out[k] = v;
            }
        } catch (_) { /* nessun .env */ }
        return out;
    }

    // ---- Catalogo dinamico (unione dei provider) --------------------------

    async discover(force = false) {
        if (!this.configured()) return this.channels;
        if (!force && (this.channels.normal.length || this.channels.uncensored.length)
            && Date.now() - this.lastDiscovery < CATALOG_TTL) {
            return this.channels;
        }
        // Credito OpenRouter prima di tutto: serve a _discoverOpenRouter (che
        // decide se pescare anche i modelli a pagamento) e al router resiliente.
        await this.refreshOpenRouterCredit();
        const seen = new Set();
        const uncensored = [];
        const normal = [];
        const caduti = [];
        for (const prov of this.providers) {
            try {
                const list = await this._discoverProvider(prov);
                for (const e of list) {
                    if (seen.has(e.value)) continue;
                    seen.add(e.value);
                    (e.uncensored ? uncensored : normal).push(e);
                }
                if (!list.length) caduti.push(prov.id); // ha risposto, ma a vuoto
            } catch (err) {
                caduti.push(prov.id);
                this.logger.error && this.logger.error(`[CloudEngine] discovery ${prov.id} fallita:`, err.message);
            }
        }

        // ★ 2026-09-02 — UN PROVIDER CHE INCIAMPA NON CANCELLA I SUOI MODELLI.
        // Il catalogo veniva SOSTITUITO in blocco appena tornava anche un solo
        // modello: bastava che un provider andasse in timeout perché i suoi
        // sparissero dall'elenco fino alla discovery successiva. Il 02/09 aimlapi
        // ha avuto un intoppo e il catalogo è passato da 1594 a 1036 modelli —
        // 558 spariti in silenzio, con l'utente che se li vedeva mancare dal menù.
        // Ora i modelli di chi è caduto vengono RIPORTATI dal catalogo precedente e
        // marcati `stale`: meglio una voce di ieri che un buco.
        if (caduti.length) {
            const vecchi = [].concat(this.channels.uncensored || [], this.channels.normal || []);
            let recuperati = 0;
            for (const e of vecchi) {
                if (!caduti.includes(e.provider) || seen.has(e.value)) continue;
                seen.add(e.value);
                const copia = Object.assign({}, e, { stale: true });
                (copia.uncensored ? uncensored : normal).push(copia);
                recuperati++;
            }
            this.logger.error && this.logger.error(
                `[CloudEngine] provider a vuoto: ${caduti.join(",")} — ` +
                (recuperati ? `tengo i ${recuperati} modelli del giro precedente (marcati stale).`
                            : "nessun modello da recuperare dal catalogo precedente."));
        }
        // ★ 2026-07-24 — UNICA FONTE DI VERITÀ su gratis/a pagamento. Prima la UI se
        // lo calcolava da sola con un elenco scritto a mano, e ogni provider nuovo
        // (GitHub, Cloudflare) finiva marcato "a pagamento" pur essendo gratis.
        for (const e of uncensored.concat(normal)) e.free = this.isFreeModel(e.provider, e.id);
        uncensored.sort((a, b) => b.rank - a.rank);
        normal.sort((a, b) => b.rank - a.rank);
        if (uncensored.length || normal.length) {
            this.channels = { uncensored, normal };
            this.lastDiscovery = Date.now();
            this._saveCatalogCache();
        }
        this.logger.log && this.logger.log(`[CloudEngine] catalogo: ${uncensored.length} uncensored, ${normal.length} normali (provider: ${this.getProviderIds().join(",")})`);
        return this.channels;
    }

    // ---- Credito OpenRouter (il solo provider a consumo che teniamo acceso) ----
    // ★ 2026-09-01 — GUARDIANO DEL PORTAFOGLIO. OpenRouter è l'unica corsia a
    // pagamento nel failover: se il credito finisce, ogni tentativo diventa un 402 e
    // un buco di secondi prima di ripiegare. Qui leggiamo quanto resta (una volta
    // ogni 10 minuti, gratis: /api/v1/credits non costa token) e `openrouterVivo()`
    // dice al router se vale ancora la pena provarci. Se la lettura fallisce NON
    // spegniamo nulla: meglio un tentativo di troppo che una corsia persa per un
    // errore di rete.
    async refreshOpenRouterCredit(force = false) {
        const prov = this._provider("openrouter");
        if (!prov) return null;
        const c = this._orCredit;
        if (!force && c && Date.now() - c.ts < 10 * 60 * 1000) return c;
        try {
            const json = await this._get(prov.host, "/api/v1/credits", prov.key);
            const d = (json && json.data) || {};
            const tot = parseFloat(d.total_credits) || 0;
            const uso = parseFloat(d.total_usage) || 0;
            this._orCredit = { ts: Date.now(), total: tot, usage: uso, remaining: tot - uso, ok: true };
            this.logger.log && this.logger.log(`[CloudEngine] OpenRouter: restano ${(tot - uso).toFixed(2)}$ di ${tot.toFixed(2)}$`);
        } catch (err) {
            this._orCredit = { ts: Date.now(), remaining: null, ok: false, error: err.message };
        }
        return this._orCredit;
    }

    /** Quanto resta sul conto OpenRouter, o null se non l'abbiamo (mai) letto. */
    openrouterCredito() { return this._orCredit || null; }

    /**
     * true se OpenRouter va ancora usato: acceso nel .env e con credito sopra la
     * soglia OPENROUTER_MIN_CREDIT (default 0.20 $). Credito ignoto = sì.
     */
    openrouterVivo() {
        if (!/^(1|true|si|yes)$/i.test(String(this.env.OPENROUTER_ENABLE || ""))) return false;
        const c = this._orCredit;
        if (!c || !c.ok || c.remaining == null) return true;   // ignoto → si prova
        const soglia = parseFloat(this.env.OPENROUTER_MIN_CREDIT || "0.20");
        return c.remaining > (isNaN(soglia) ? 0.20 : soglia);
    }

    _discoverProvider(prov) {
        if (prov.id === "hf") return this._discoverHF(prov);
        if (prov.id === "openrouter") return this._discoverOpenRouter(prov);
        if (prov.id === "groq") return this._discoverGroq(prov);
        if (prov.id === "google") return this._discoverGoogle(prov);
        if (prov.id === "cloudflare") return this._discoverCloudflare(prov);
        return this._discoverGeneric(prov);   // cerebras, nvidia, sambanova, mistral, github, ...
    }

    // Discovery GENERICA per qualsiasi provider OpenAI-compat con /models: elenca i
    // modelli di chat, stima taglia e uncensored dal nome. tools:true ottimistico
    // (il router failover gestisce da sé i modelli che poi rifiutano i tool).
    async _discoverGeneric(prov) {
        if (!prov.modelsPath) return [];
        let json;
        try { json = await this._get(prov.host, prov.modelsPath, prov.key); }
        catch (_) { return []; }
        // ★ 2026-07-24 — alcuni cataloghi rispondono con una LISTA pura invece che
        // { data: [...] } (GitHub Models: /catalog/models). Prima venivano scartati
        // in silenzio e il provider restava senza modelli.
        const data = Array.isArray(json) ? json : ((json && (json.data || json.models || json.result)) || []);
        const out = [];
        for (const m of data) {
            const id = String(m.id || m.name || m.model || "").replace(/^models\//, "");
            if (!id) continue;
            if (/embed|whisper|tts|rerank|guard|moderation|image|vision|audio|video|bge|nomic/i.test(id)) continue;
            const unc = UNCENSORED_RX.test(id);
            out.push({
                value: prov.id + SEP + id,
                id, provider: prov.id,
                label: this._short(id) + " · " + prov.label,
                uncensored: unc, rank: (this._sizeB(id) || 1), tools: true
            });
        }
        return out;
    }

    // Cloudflare Workers AI: il catalogo NON è OpenAI-compat (risponde
    // { result: [ { name: "@cf/openai/gpt-oss-120b", task: {...} } ] }), mentre la
    // chat lo è. Teniamo solo i modelli di testo veri: fuori guard/lora/embedding,
    // che non sono assistenti e farebbero fallire le chiamate.
    async _discoverCloudflare(prov) {
        if (!prov.modelsPath) return [];
        let json;
        try { json = await this._get(prov.host, prov.modelsPath, prov.key); }
        catch (_) { return []; }
        const data = (json && (json.result || json.data)) || [];
        const out = [];
        for (const m of data) {
            const id = String(m.name || m.id || "");
            if (!id.startsWith("@cf/")) continue;
            if (/guard|lora|embed|bge|whisper|tts|resnet|detr|sd-|stable-diffusion|reranker|melotts|m2m100|distil/i.test(id)) continue;
            out.push({
                value: "cloudflare" + SEP + id,
                id, provider: "cloudflare",
                label: this._short(id) + " · Cloudflare",
                uncensored: UNCENSORED_RX.test(id),
                rank: (this._sizeB(id) || 1), tools: true
            });
        }
        return out;
    }

    // Google Gemini: endpoint OpenAI-compat. Modelli chat "gemini-*" (no embedding/
    // imagen/veo/aqa). Filtrati (non uncensored). Chiave API gratuita.
    async _discoverGoogle(prov) {
        const json = await this._get(prov.host, "/v1beta/openai/models", prov.key);
        const data = (json && json.data) || [];
        const out = [];
        for (const m of data) {
            const id = String(m.id || "").replace(/^models\//, "");
            if (!/gemini/i.test(id)) continue;
            // solo modelli di CHAT testuale: escludi embedding/immagini/audio/video/live
            if (/embedding|aqa|imagen|veo|vision|tts|image|audio|live|realtime|native/i.test(id)) continue;
            // Preferenze pensate per il piano GRATIS: i "flash" hanno quota free
            // molto più alta dei "pro" (che sul free si esauriscono subito, 429).
            let rank = 40;
            if (/flash/i.test(id)) rank += 25;      // flash = default pratico sul free
            if (/2\.5|flash-latest/i.test(id)) rank += 12;
            if (/2\.0/i.test(id)) rank += 6;
            if (/pro/i.test(id)) rank -= 20;        // pro: qualità top ma quota free minima
            if (/lite|8b/i.test(id)) rank -= 6;
            if (/exp|preview/i.test(id)) rank -= 4;
            out.push({
                value: "google" + SEP + id,
                id, provider: "google",
                label: this._short(id) + " · Gemini",
                uncensored: false, rank, tools: true
            });
        }
        return out;
    }

    // HuggingFace: text-generation servibili (provider live E raggiungibili).
    async _discoverHF(prov) {
        const out = [];
        const seen = new Set();
        const add = (m) => {
            if (!m || !m.id || seen.has(m.id)) return;
            const live = this._hfLiveProviders(m);
            if (!live.length) return;               // non servibile sul nostro account
            seen.add(m.id);
            const unc = UNCENSORED_RX.test(m.id) || this._tagsUncensored(m);
            const size = this._sizeFrom(m.id + " " + (m.tags || []).join(" "));
            out.push({
                value: "hf" + SEP + m.id,
                id: m.id, provider: "hf",
                label: this._short(m.id) + (size ? ` (${size})` : "") + " · HF",
                uncensored: unc, rank: m.trendingScore || 0,
                tools: (m.tags || []).some(t => /tool|function.?call|agent/i.test(t))
            });
        };
        const normal = await this._hfApi({ inference_provider: "all", pipeline_tag: "text-generation", sort: "trendingScore", limit: "80" }, prov.key);
        for (const term of ["abliterated", "uncensored", "dolphin"]) {
            const r = await this._hfApi({ inference_provider: "all", search: term, limit: "40" }, prov.key);
            r.forEach(add);
        }
        normal.forEach(add);
        return out;
    }

    // OpenRouter: i modelli :free SEMPRE; quelli A PAGAMENTO solo se nel .env c'è
    // OPENROUTER_ENABLE=1 (cioè c'è credito sul conto).
    // ★ 2026-09-01 — prima qui passavano SOLO i :free, e dal 2026-07-24 i :free grossi
    // erano spariti: OpenRouter era di fatto un provider morto. Con credito caricato
    // riapriamo la corsia, ma con tre paletti perché i 10 $ non evaporino:
    //   • tetto di prezzo: OPENROUTER_MAX_USD_PER_M (default 3 $ per milione in uscita)
    //   • solo modelli che servono davvero: uncensored (la corsia senza filtri) oppure
    //     le famiglie utili a codice/RE; il resto del listino (400+ voci) resta fuori
    //   • tetto al numero di voci a pagamento non-uncensored (OPENROUTER_MAX_PAID, 40)
    // tools: NON più ottimistico. Lo leggiamo da supported_parameters, perché molti
    // uncensored non fanno tool-calling e l'agente ci sbatteva contro a vuoto.
    async _discoverOpenRouter(prov) {
        const json = await this._get(prov.host, "/api/v1/models", prov.key);
        const data = (json && json.data) || [];
        const paidOn = /^(1|true|si|yes)$/i.test(String(this.env.OPENROUTER_ENABLE || ""));
        const maxOut = parseFloat(this.env.OPENROUTER_MAX_USD_PER_M || "3") || 3;
        const maxPaid = parseInt(this.env.OPENROUTER_MAX_PAID || "40", 10) || 40;
        // Famiglie che vale la pena pagare: coding, reverse engineering, contesti lunghi.
        const UTILI_RX = /qwen|deepseek|kimi|glm|minimax|codestral|devstral|llama-3\.3|mistral|gpt-oss|command-a|grok-code/i;
        const gratuiti = [], paidUnc = [], paidUtil = [];
        for (const m of data) {
            const pr = m.pricing || {};
            const inM = (parseFloat(pr.prompt) || 0) * 1e6;
            const outM = (parseFloat(pr.completion) || 0) * 1e6;
            const gratis = String(m.id).endsWith(":free") || (inM === 0 && outM === 0);
            const testo = m.id + " " + (m.name || "");
            const unc = UNCENSORED_RX.test(testo);
            if (!gratis) {
                if (!paidOn) continue;                       // niente credito → solo i :free
                if (!outM || outM > maxOut) continue;        // troppo caro per il budget
                if (!unc && !UTILI_RX.test(testo)) continue; // fuori tema → fuori catalogo
            }
            const ctx = m.context_length ? " " + Math.round(m.context_length / 1000) + "k" : "";
            const prezzo = gratis ? "" : " · " + outM.toFixed(2) + "$/M";
            const e = {
                value: "openrouter" + SEP + m.id,
                id: m.id, provider: "openrouter",
                label: this._short(m.id).replace(/:free$/, "") + " · OpenRouter" + ctx + prezzo,
                uncensored: unc, rank: (m.context_length || 0) / 1000,
                tools: (m.supported_parameters || []).includes("tools"),
                priceInPerM: inM, priceOutPerM: outM
            };
            if (gratis) gratuiti.push(e); else if (unc) paidUnc.push(e); else paidUtil.push(e);
        }
        paidUtil.sort((a, b) => b.rank - a.rank);
        return gratuiti.concat(paidUnc, paidUtil.slice(0, maxPaid));
    }

    // Groq: tutti gratis, tutti "normali" (filtrati). Velocissimi.
    async _discoverGroq(prov) {
        const json = await this._get(prov.host, "/openai/v1/models", prov.key);
        const data = (json && json.data) || [];
        const out = [];
        for (const m of data) {
            const id = m.id;
            if (/whisper|tts|guard|prompt-guard|orpheus|playai|distil|embed/i.test(id)) continue; // non-chat
            out.push({
                value: "groq" + SEP + id,
                id, provider: "groq",
                label: this._short(id) + " · Groq ⚡",
                uncensored: false, rank: 50, tools: true
            });
        }
        return out;
    }

    _hfLiveProviders(m) {
        const ipm = m.inferenceProviderMapping;
        const out = [];
        const push = (name, status) => { if (status === "live" && this.hfReachable.has(String(name).toLowerCase())) out.push(name); };
        if (Array.isArray(ipm)) for (const p of ipm) { if (p) push(p.provider, p.status); }
        else if (ipm && typeof ipm === "object") for (const [n, v] of Object.entries(ipm)) { if (v) push(n, v.status); }
        return out;
    }
    _tagsUncensored(m) { return (m.tags || []).some(t => /uncensored|abliterated|not-for-all-audiences/i.test(t)); }
    _sizeFrom(hay) {
        const mt = hay.match(/(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*b\b/i);
        if (mt) return `${Math.round(parseFloat(mt[1]) * parseFloat(mt[2]))}B`;
        const m1 = hay.match(/(\d+(?:\.\d+)?)\s*b\b/i);
        return m1 ? `${m1[1]}B` : "";
    }
    _short(id) { return String(id).replace(/^.*\//, ""); }

    /**
     * Il modello è utilizzabile GRATIS? Regola unica, valida per tutta l'app:
     *   • il provider ha un piano gratuito e non è a consumo → gratis;
     *   • eccezione OpenRouter: solo i modelli che finiscono in ":free";
     *   • HuggingFace e i provider a consumo (OpenAI, DeepSeek, Anthropic…) → a pagamento.
     */
    isFreeModel(provId, modelId) {
        const id = String(modelId || "");
        if (provId === "openrouter") return /:free$/i.test(id);
        if (provId === "nous") return true;   // dal portale Nous prendiamo solo i :free
        const def = registry.byId(provId);
        if (!def) return false;
        return !!def.free && !def.billed;
    }

    /** Elenco provider presenti nel catalogo, con nome leggibile e se sono gratis. */
    providerMeta() {
        const out = {};
        for (const e of [].concat(this.channels.uncensored || [], this.channels.normal || [])) {
            if (out[e.provider]) continue;
            const def = registry.byId(e.provider);
            out[e.provider] = {
                id: e.provider,
                name: (def && def.label) || e.provider,
                free: !!(def && def.free && !def.billed)
            };
        }
        return out;
    }

    getChannels() {
        const map = arr => arr.map(m => ({
            value: m.value, label: (m.tools ? "" : "") + m.label,
            provider: m.provider,
            // gratis/a pagamento deciso QUI, non nella UI (vedi isFreeModel)
            free: (m.free != null) ? !!m.free : this.isFreeModel(m.provider, m.id)
        }));
        return { uncensored: map(this.channels.uncensored), normal: map(this.channels.normal), providers: this.providerMeta() };
    }

    // ---- Inferenza --------------------------------------------------------

    /**
     * chat(value, ...) dove value = "provider::modelId" (o solo modelId → hf).
     * Streaming SSE se onToken è funzione. Registra l'uso a fine risposta.
     */
    async chat(value, messages, { temperature = 0.7, onToken = null, maxTokens = 2048, signal = null } = {}) {
        const { prov, model } = this._resolve(value);
        if (!prov) throw new Error("Nessun provider cloud configurato per: " + value);
        const wantStream = typeof onToken === "function";
        const payload = { model, messages, temperature, max_tokens: maxTokens, stream: wantStream };
        if (wantStream) payload.stream_options = { include_usage: true };
        const body = JSON.stringify(payload);
        const headers = {
            "Authorization": "Bearer " + prov.key,
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body)
        };
        if (prov.id === "openrouter") { headers["HTTP-Referer"] = "https://localhost/antigravity"; headers["X-Title"] = "Antigravity"; }
        if (prov.id === "kaggle") { headers["ngrok-skip-browser-warning"] = "true"; }

        if (!wantStream) {
            this._noteRequest(prov.id);
            const json = await this._post(prov.host, prov.chatPath, body, headers, prov.id);
            const content = (json.choices && json.choices[0] && json.choices[0].message && json.choices[0].message.content) || "";
            this._record(value, prov, json.usage || this._estimateUsage(messages, content));
            return content;
        }

        this._noteRequest(prov.id);
        return new Promise((resolve, reject) => {
            const req = https.request({ host: prov.host, path: prov.chatPath, method: "POST", headers }, (res) => {
                this._noteRate(prov.id, res.headers);
                if (res.statusCode >= 400) {
                    let e = ""; res.on("data", c => e += c);
                    res.on("end", () => reject(new Error(`${prov.label} HTTP ${res.statusCode}: ${e.slice(0, 400)}`)));
                    return;
                }
                let full = "", buf = "", usage = null;
                res.on("data", chunk => {
                    buf += chunk.toString("utf8");
                    let idx;
                    while ((idx = buf.indexOf("\n")) >= 0) {
                        const line = buf.slice(0, idx).trim();
                        buf = buf.slice(idx + 1);
                        if (!line.startsWith("data:")) continue;
                        const p = line.slice(5).trim();
                        if (p === "[DONE]") continue;
                        try {
                            const j = JSON.parse(p);
                            if (j.usage) usage = j.usage;
                            const delta = j.choices && j.choices[0] && j.choices[0].delta && j.choices[0].delta.content;
                            if (delta) { full += delta; onToken(delta); }
                        } catch (_) { /* riga parziale */ }
                    }
                });
                res.on("end", () => { this._record(value, prov, usage || this._estimateUsage(messages, full)); resolve(full); });
            });
            req.on("error", reject);
            if (signal) signal.addEventListener("abort", () => req.destroy(new Error("aborted")));
            req.write(body); req.end();
        });
    }

    /**
     * chatTools — come chat(), ma con STRUMENTI (tool-calling in stile OpenAI).
     * Serve a far guidare l'agente da un modello CLOUD (es. Hermes-405B uncensored)
     * invece che dal 14B locale. Non è in streaming: il tool-calling affidabile
     * vuole la risposta completa. Ritorna { content, tool_calls } come il locale.
     */
    async chatTools(value, messages, tools, { temperature = 0.2, maxTokens = 2048, signal = null } = {}) {
        const { prov, model } = this._resolve(value);
        if (!prov) throw new Error("Nessun provider cloud configurato per: " + value);
        const payload = { model, messages, temperature, max_tokens: maxTokens, tools, tool_choice: "auto", stream: false };
        const body = JSON.stringify(payload);
        const headers = {
            "Authorization": "Bearer " + prov.key,
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body)
        };
        if (prov.id === "openrouter") { headers["HTTP-Referer"] = "https://localhost/antigravity"; headers["X-Title"] = "Antigravity"; }
        if (prov.id === "kaggle") { headers["ngrok-skip-browser-warning"] = "true"; }
        this._noteRequest(prov.id);
        const json = await this._post(prov.host, prov.chatPath, body, headers, prov.id);
        const msg = (json.choices && json.choices[0] && json.choices[0].message) || {};
        this._record(value, prov, json.usage || this._estimateUsage(messages, msg.content || ""));
        return { content: msg.content || "", tool_calls: msg.tool_calls || [] };
    }

    _resolve(value) {
        const s = String(value || "");
        const i = s.indexOf(SEP);
        if (i >= 0) return { prov: this._provider(s.slice(0, i)), model: s.slice(i + SEP.length) };
        // Retro-compat: nessun prefisso → HF.
        return { prov: this._provider("hf"), model: s };
    }

    // ---- Barra di utilizzo ------------------------------------------------

    _emptyUsage() { return { month: this._monthKey(), requests: 0, promptTokens: 0, completionTokens: 0, totalTokens: 0, estCostUsd: 0, perModel: {} }; }
    _monthKey() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; }
    _loadUsage() { try { const u = JSON.parse(fs.readFileSync(this._usageFile, "utf8")); if (u && u.month === this._monthKey()) return u; } catch (_) {} return this._emptyUsage(); }
    _saveUsage() { try { fs.mkdirSync(this.storageDir, { recursive: true }); fs.writeFileSync(this._usageFile, JSON.stringify(this.usage, null, 2), "utf8"); } catch (e) { this.logger.error && this.logger.error("[CloudEngine] save uso:", e.message); } }
    _estimateUsage(messages, output) {
        const inChars = messages.reduce((n, m) => n + (m.content ? m.content.length : 0), 0);
        const prompt = Math.ceil(inChars / 4), completion = Math.ceil((output || "").length / 4);
        return { prompt_tokens: prompt, completion_tokens: completion, total_tokens: prompt + completion };
    }
    _record(value, prov, usage) {
        if (this.usage.month !== this._monthKey()) this.usage = this._emptyUsage();
        const pt = usage.prompt_tokens || 0, ct = usage.completion_tokens || 0, tt = usage.total_tokens || (pt + ct);
        this.usage.requests += 1; this.usage.promptTokens += pt; this.usage.completionTokens += ct; this.usage.totalTokens += tt;
        // Costo stimato solo per provider a consumo (HF). Groq/OpenRouter free = 0.
        if (prov && prov.billed) this.usage.estCostUsd += (tt / 1e6) * this.pricePerMtok;
        const pm = this.usage.perModel[value] || { requests: 0, totalTokens: 0 };
        pm.requests += 1; pm.totalTokens += tt; this.usage.perModel[value] = pm;
        this._saveUsage();
    }
    getUsage() {
        const u = this.usage;
        const pct = this.budgetUsd > 0 ? Math.min(100, (u.estCostUsd / this.budgetUsd) * 100) : 0;
        // Aggregazione per PROVIDER (dal prefisso "provider::model" delle perModel):
        // alimenta la barra token per-provider della UI.
        const perProvider = {};
        for (const [value, m] of Object.entries(u.perModel || {})) {
            const prov = String(value).split(SEP)[0] || "?";
            const p = perProvider[prov] || { requests: 0, totalTokens: 0 };
            p.requests += m.requests || 0; p.totalTokens += m.totalTokens || 0;
            perProvider[prov] = p;
        }
        return {
            month: u.month, requests: u.requests, totalTokens: u.totalTokens,
            promptTokens: u.promptTokens, completionTokens: u.completionTokens,
            estCostUsd: Math.round(u.estCostUsd * 1e6) / 1e6, budgetUsd: this.budgetUsd,
            percent: Math.round(pct * 10) / 10, perModel: u.perModel,
            perProvider, resetsHuman: this._nextResetHuman()
        };
    }
    /** Quando si azzera il conteggio mensile, in forma leggibile (es. "il 1° ago"). */
    _nextResetHuman() {
        const d = new Date();
        const next = new Date(d.getFullYear(), d.getMonth() + 1, 1);
        const mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
        return "il 1° " + mesi[next.getMonth()];
    }
    exhausted() { return this.budgetUsd > 0 && this.usage.estCostUsd >= this.budgetUsd; }
    static isQuotaError(err) {
        const m = String((err && err.message) || err || "");
        return /HTTP 402|HTTP 429|quota|credit|insufficient|payment required|rate.?limit|too many requests/i.test(m);
    }
    resetUsage() { this.usage = this._emptyUsage(); this._saveUsage(); return this.getUsage(); }

    // ---- Catalogo persistito ---------------------------------------------

    _saveCatalogCache() { try { fs.mkdirSync(this.storageDir, { recursive: true }); fs.writeFileSync(this._catalogFile, JSON.stringify({ at: this.lastDiscovery, channels: this.channels }), "utf8"); } catch (_) {} }
    _loadCatalogCache() { try { const c = JSON.parse(fs.readFileSync(this._catalogFile, "utf8")); if (c && c.channels) { this.channels = c.channels; this.lastDiscovery = c.at || 0; } } catch (_) {} }

    // ---- Budget richieste al minuto (anti "rate limit" fantasma) ----------

    _loadRate() { try { return JSON.parse(fs.readFileSync(this._rateFile, "utf8")) || {}; } catch (_) { return {}; } }
    _saveRate() { try { fs.mkdirSync(this.storageDir, { recursive: true }); fs.writeFileSync(this._rateFile, JSON.stringify(this._rate), "utf8"); } catch (_) {} }

    /** Registra una richiesta appena partita (finestra locale di 60s per provider). */
    _noteRequest(provId) {
        const now = Date.now();
        const arr = (this._recent[provId] || []).filter(t => now - t < 60000);
        arr.push(now);
        this._recent[provId] = arr;
    }

    /**
     * Legge gli header di rate-limit della risposta (standard OpenAI-compat, usati
     * da Cerebras/Groq/Mistral/OpenRouter) e aggiorna il budget del provider.
     * È l'unica fonte ATTENDIBILE: niente stime, niente liste hardcoded che invecchiano.
     */
    _noteRate(provId, h) {
        if (!provId || !h) return;
        const num = (k) => { const v = h[k]; if (v == null) return null; const n = parseFloat(String(v)); return isFinite(n) ? n : null; };
        const st = this._rate[provId] || {};
        const limMin = num("x-ratelimit-limit-requests-minute") ?? num("x-ratelimit-limit-requests") ?? st.limMin ?? null;
        const remMin = num("x-ratelimit-remaining-requests-minute") ?? num("x-ratelimit-remaining-requests");
        const remDay = num("x-ratelimit-remaining-requests-day") ?? num("x-ratelimit-remaining-tokens-day");
        const retry = num("retry-after");
        const next = { at: Date.now() };
        if (limMin != null) next.limMin = limMin;
        if (remMin != null) next.remMin = remMin;
        if (remDay != null) next.remDay = remDay;
        // Se il provider dice esplicitamente "riprova tra N secondi", lo rispettiamo.
        if (retry != null && retry > 0) next.until = Date.now() + Math.min(retry, 300) * 1000;
        // Finite le richieste del minuto: pausa fino al minuto successivo, non di più.
        else if (remMin != null && remMin <= 0) next.until = Date.now() + 62 * 1000;
        this._rate[provId] = Object.assign({}, st, next);
        this._saveRate();
    }

    /**
     * Il provider è saturo ADESSO? (non è un guasto: fra pochi secondi torna).
     * Due segnali: (1) quello che ha dichiarato lui negli header; (2) il nostro
     * conteggio locale, che protegge anche alla PRIMA raffica, prima che arrivi
     * un 429 (se conosciamo il limite al minuto dichiarato in precedenza).
     */
    _providerBusy(provId) {
        const st = this._rate[provId];
        if (st && st.until && st.until > Date.now()) return true;
        if (st && st.limMin) {
            const now = Date.now();
            const used = (this._recent[provId] || []).filter(t => now - t < 60000).length;
            if (used >= st.limMin) return true;
        }
        return false;
    }

    /** Fra quanti ms il provider torna libero (0 = libero ora). */
    _busyForMs(provId) {
        const st = this._rate[provId];
        let ms = 0;
        if (st && st.until && st.until > Date.now()) ms = st.until - Date.now();
        if (st && st.limMin) {
            const now = Date.now();
            const times = (this._recent[provId] || []).filter(t => now - t < 60000);
            if (times.length >= st.limMin) ms = Math.max(ms, 60000 - (now - times[0]) + 500);
        }
        return ms;
    }

    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    /** Il tempo più breve dopo il quale ALMENO un candidato torna utilizzabile. */
    _shortestWait(cands) {
        let best = Infinity;
        for (const c of cands) {
            const ms = this._busyForMs(c.provider);
            if (ms < best) best = ms;
        }
        return isFinite(best) ? best : 0;
    }

    /**
     * AUTO-AGGIORNAMENTO del catalogo: ogni provider viene ri-interrogato da solo
     * (GET /models) a intervalli regolari, così gli ID che il provider ritira
     * spariscono e quelli nuovi entrano SENZA che nessuno tocchi il codice.
     * È la cura definitiva alle "liste obsolete": i semi scritti a mano restano
     * solo come rete di sicurezza per il primo avvio.
     */
    startAutoRefresh(intervalMs = 6 * 60 * 60 * 1000) {
        this.stopAutoRefresh();
        const tick = () => {
            this.discover(true)
                .then(() => this.logger.log && this.logger.log("[CloudEngine] catalogo aggiornato in automatico"))
                .catch(e => this.logger.error && this.logger.error("[CloudEngine] auto-refresh:", e.message));
        };
        // primo giro dopo 30s (non rallenta l'avvio), poi a intervalli
        const first = setTimeout(tick, 30 * 1000);
        if (first.unref) first.unref();
        this._refreshTimer = setInterval(tick, intervalMs);
        if (this._refreshTimer.unref) this._refreshTimer.unref();
        return this;
    }
    stopAutoRefresh() { if (this._refreshTimer) { clearInterval(this._refreshTimer); this._refreshTimer = null; } }

    /**
     * "Cacciatore di taglie" VERO: unisce la lista curata con i dati LIVE.
     * Per ogni provider con chiave dice i modelli che esistono DAVVERO adesso
     * (dal catalogo auto-aggiornato) e quanto budget resta; per quelli senza
     * chiave resta il suggerimento con il link per prenderla.
     */
    liveFreeProviders() {
        const curated = registry.freeProviders();
        const active = new Set(this.getProviderIds());
        const rate = this.rateSnapshot();
        const byProv = {};
        for (const e of [].concat(this.channels.uncensored || [], this.channels.normal || [])) {
            (byProv[e.provider] = byProv[e.provider] || []).push({ id: e.id, uncensored: !!e.uncensored, size: this._sizeB(e.value) || null });
        }
        const cd = this._cd_();
        const out = curated.map(p => {
            const live = byProv[p.id];
            const st = rate[p.id] || {};
            const provCd = cd["prov:" + p.id];
            return Object.assign({}, p, {
                configured: active.has(p.id),
                live: !!live,
                // i modelli veri, ordinati per taglia; se la discovery non ha ancora
                // girato per questo provider si mostra la lista curata (fallback)
                freeModels: live ? live.sort((a, b) => (b.size || 0) - (a.size || 0)).slice(0, 12).map(m => m.id) : p.freeModels,
                modelsLive: !!live,
                lastCheck: this.lastDiscovery || null,
                budget: active.has(p.id) ? {
                    perMinute: st.limitPerMinute, remainingMinute: st.remainingMinute,
                    remainingDay: st.remainingDay, busyForSec: st.busyForSec || 0
                } : null,
                health: !active.has(p.id) ? "no-key"
                    : (provCd && provCd.until > Date.now()) ? String(provCd.reason || "in pausa")
                    : (st.busyForSec > 0) ? "occupato (limite al minuto)"
                    : "ok"
            });
        });
        // provider con chiave ma non presenti nella lista curata → aggiungili
        for (const id of active) {
            if (out.some(p => p.id === id)) continue;
            const def = registry.byId(id);
            const live = byProv[id];
            out.push({
                id, name: (def && def.label) || id, keyUrl: (def && def.signup) || "",
                freeModels: live ? live.slice(0, 12).map(m => m.id) : [],
                note: (def && def.note) || "", configured: true, live: !!live,
                modelsLive: !!live, lastCheck: this.lastDiscovery || null,
                budget: null, health: "ok"
            });
        }
        return out;
    }

    /** Fotografia leggibile del budget per la UI (pannello chiavi / cacciatore). */
    rateSnapshot() {
        const out = {};
        for (const p of this.providers) {
            const st = this._rate[p.id] || {};
            const now = Date.now();
            out[p.id] = {
                limitPerMinute: st.limMin ?? null,
                remainingMinute: st.remMin ?? null,
                remainingDay: st.remDay ?? null,
                busyForSec: Math.ceil(this._busyForMs(p.id) / 1000),
                usedLastMinute: (this._recent[p.id] || []).filter(t => now - t < 60000).length
            };
        }
        return out;
    }

    // ---- HTTP helpers -----------------------------------------------------

    _hfApi(params, key) {
        const qs = Object.entries(params).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
        return this._get("huggingface.co", `/api/models?${qs}&expand[]=inferenceProviderMapping`, key);
    }
    _get(host, pathname, key) {
        return new Promise((resolve, reject) => {
            const req = https.get({ host, path: pathname, timeout: 12000, headers: key ? { "Authorization": "Bearer " + key } : {} }, (res) => {
                let data = ""; res.on("data", c => data += c);
                res.on("end", () => {
                    if (res.statusCode >= 400) return reject(new Error(`${host} ${res.statusCode}: ${data.slice(0, 200)}`));
                    try { resolve(JSON.parse(data)); } catch (e) { reject(new Error("JSON non valido da " + host + ": " + e.message)); }
                });
            });
            req.on("timeout", () => req.destroy(new Error("timeout " + host)));
            req.on("error", reject);
        });
    }
    _post(host, pathname, body, headers, provId = null) {
        return new Promise((resolve, reject) => {
            // ★ 2026-07-19 — timeout 120s → 30s. A 2 MINUTI per tentativo, un
            // provider che si pianta (NVIDIA verificato: timeout secco) bloccava
            // tutta la catena e l'app "non rispondeva". A 30s un provider morto
            // viene abbandonato in fretta e la rotazione passa subito al
            // successivo: uno che funziona (Groq/SambaNova ~400-950ms) risponde
            // ben prima della soglia; solo i pantani vengono tagliati.
            const req = https.request({ host, path: pathname, method: "POST", headers, timeout: 30000 }, (res) => {
                // Header di rate-limit: valgono ANCHE (anzi soprattutto) sul 429.
                if (provId) this._noteRate(provId, res.headers);
                let data = ""; res.on("data", c => data += c);
                res.on("end", () => {
                    if (res.statusCode >= 400) return reject(new Error(`${host} HTTP ${res.statusCode}: ${data.slice(0, 400)}`));
                    try { resolve(JSON.parse(data)); } catch (e) { reject(new Error("JSON non valido da " + host + ": " + e.message)); }
                });
            });
            req.on("timeout", () => req.destroy(new Error("timeout " + host)));
            req.on("error", reject);
            req.write(body); req.end();
        });
    }

    // =======================================================================
    // ROUTER FAILOVER INTELLIGENTE
    // -----------------------------------------------------------------------
    // Garantisce un agente SEMPRE disponibile: prova i modelli GRATIS ≥ minB
    // in ordine di preferenza; se uno è esaurito (429/quota), in errore o giù,
    // lo mette in "cooldown" e passa AUTOMATICAMENTE al successivo, su un altro
    // provider. Solo provider gratuiti (OpenRouter/Groq/Google); HF è a consumo
    // ed è escluso. Lo stato di cooldown è persistito, così un modello bruciato
    // resta saltato per un po' anche tra un avvio e l'altro.
    // =======================================================================

    // Modelli-seme noti come gratuiti, grossi (≥32B) e con tool-calling. Usati
    // se la discovery live non ha (ancora) popolato il catalogo. La discovery
    // resta la fonte primaria; questi sono la rete di sicurezza.
    static SEED_MODELS() {
        return [
            // provider::id, sizeB, uncensored, coder — AGGIORNATO da discovery live 2026-07-18
            // (verificato con le chiavi reali; rimossi gli ID :free morti su OpenRouter/Groq).
            // ★ CORSIA PRIORITARIA dell'utente: abliterated coder su Kaggle. Il 14B è il
            // default (veloce ~19 t/s). Il 32B resta selezionabile a mano per i casi tosti.
            { value: "kaggle::hf.co/bartowski/Qwen2.5-Coder-14B-Instruct-abliterated-GGUF:Q4_K_M", b: 14, unc: true, coder: true },
            // ★ 2026-07-24 — CEREBRAS mancava del tutto tra i semi (aveva rank 9 ma
            // nessun modello): entrava solo se la discovery aveva già girato. Questi
            // sono gli ID VERIFICATI oggi sulla chiave reale (HTTP 200).
            { value: "cerebras::gpt-oss-120b", b: 120, unc: false, coder: true },
            { value: "cerebras::zai-glm-4.7", b: 100, unc: false, coder: true },
            { value: "cerebras::gemma-4-31b", b: 31, unc: false, coder: false },
            // ★ 2026-07-24 — CLOUDFLARE WORKERS AI e GITHUB MODELS: nuove corsie gratis
            // (ID verificati con le chiavi reali dell'utente, HTTP 200).
            { value: "cloudflare::@cf/openai/gpt-oss-120b", b: 120, unc: false, coder: true },
            { value: "cloudflare::@cf/moonshotai/kimi-k2.7-code", b: 0, unc: false, coder: true },
            { value: "cloudflare::@cf/deepseek-ai/deepseek-r1-distill-qwen-32b", b: 32, unc: false, coder: true },
            { value: "github::openai/gpt-4.1-mini", b: 0, unc: false, coder: true },
            { value: "github::openai/gpt-4o-mini", b: 0, unc: false, coder: false },
            // Generalisti gratis stabili (rete di sicurezza del failover)
            { value: "groq::llama-3.3-70b-versatile", b: 70, unc: false, coder: false },
            { value: "google::gemini-2.0-flash", b: 100, unc: false, coder: false },
            { value: "nvidia::nvidia/llama-3.1-nemotron-ultra-253b-v1", b: 253, unc: false, coder: false },
            { value: "nvidia::nvidia/nemotron-3-super-120b-a12b", b: 120, unc: false, coder: false },
            // CODER potenti gratis
            // (i semi OpenRouter/Hyperbolic sono stati RIMOSSI il 2026-07-24: i :free
            //  grossi sono passati a pagamento e Hyperbolic è a credito zero → erano
            //  solo tentativi a vuoto. Tornano da soli via discovery se riattivati.)
            { value: "mistral::codestral-latest", b: 22, unc: false, coder: true },
            { value: "mistral::devstral-medium-latest", b: 24, unc: false, coder: true },
            { value: "nvidia::mistralai/codestral-22b-instruct-v0.1", b: 22, unc: false, coder: true },
            // CODER + poco filtrati (deepseek), grossi e raggiungibili
            { value: "sambanova::DeepSeek-V3.2", b: 671, unc: true, coder: true },
            { value: "nvidia::deepseek-ai/deepseek-v4-pro", b: 236, unc: true, coder: true }
        ];
    }

    // Nome leggibile del provider + modello, es. "OpenRouter · qwen3-coder".
    _friendlyLabel(value) {
        const NAMES = { openrouter: "OpenRouter", groq: "Groq ⚡", google: "Gemini", hf: "HuggingFace" };
        const i = String(value).indexOf(SEP);
        const provId = i >= 0 ? value.slice(0, i) : "hf";
        const model = i >= 0 ? value.slice(i + SEP.length) : value;
        return (NAMES[provId] || provId) + " · " + this._short(model).replace(/:free$/, "");
    }

    _cooldownPath() { return path.join(this.storageDir, "cloud-cooldown.json"); }
    _loadCooldown() {
        let cd = {};
        try { cd = JSON.parse(fs.readFileSync(this._cooldownPath(), "utf8")) || {}; } catch (_) { return {}; }
        // AUTO-PULIZIA all'avvio: butta le voci già SCADUTE (il file non cresce e i
        // provider tornano subito disponibili quando il loro cooldown è passato).
        const now = Date.now();
        for (const k of Object.keys(cd)) { if (!cd[k] || !(cd[k].until > now)) delete cd[k]; }
        return cd;
    }
    _saveCooldown() { try { fs.writeFileSync(this._cooldownPath(), JSON.stringify(this._cd || {}), "utf8"); } catch (_) {} }
    _cd_() { if (!this._cd) this._cd = this._loadCooldown(); return this._cd; }
    _inCooldown(value) { const c = this._cd_()[value]; return c && c.until > Date.now(); }
    _setCooldown(value, ms, reason) { this._cd_()[value] = { until: Date.now() + ms, reason }; this._saveCooldown(); }
    clearCooldown() { this._cd = {}; this._saveCooldown(); }
    /**
     * AUTO-AZZERAMENTO: cancella i cooldown TRANSITORI (quota/saturo/errore/modello
     * non valido) MA tiene le chiavi morte (auth) — inutile ritentare un provider con
     * chiave revocata. Ritorna quanti ne ha rimossi. Chiamato da solo quando il
     * failover si esaurisce, così alla richiesta dopo riparti pulito senza fare nulla.
     */
    _resetTransientCooldowns() {
        const cd = this._cd_();
        let n = 0;
        for (const k of Object.keys(cd)) {
            if (cd[k] && /auth/i.test(cd[k].reason || "")) continue; // chiave morta → rispettala
            delete cd[k]; n++;
        }
        if (n) this._saveCooldown();
        return n;
    }

    /** Dimensione in miliardi di parametri stimata da un value/id. 0 = ignota. */
    _sizeB(value) {
        const s = this._sizeFrom(String(value)); // es. "70B"
        const m = s.match(/([\d.]+)\s*B/i);
        return m ? parseFloat(m[1]) : 0;
    }

    /**
     * Costruisce la lista ordinata di candidati "provider::model" per il failover.
     * @param {object} o  minB (default 32), uncensored (bias), coder (bias), needTools (default true)
     */
    resilientCandidates(o = {}) {
        // * 2026-09-01 - CORSIE PER INTENZIONE (o.lane). La pagina non chiede piu'
        // "quale provider / quale modello" (1635 voci: nessuno sceglie davvero fra
        // 1635 voci) ma "come vuoi che risponda". Le corsie non sono etichette
        // decorative: ognuna sposta per davvero questa classifica.
        //   fast  - i free tier verificati veloci, senza giganti lenti
        //   big   - i modelli grossi, anche se ci mettono di piu'
        //   unc   - senza filtri (equivale a o.uncensored)
        //   paid  - usa il credito: prima i modelli a pagamento
        //   auto  - la classifica di sempre
        const lane = String(o.lane || "auto");
        const laneUnc = lane === "unc" || !!o.uncensored;
        // "Grosso" alza la soglia, "veloce" la toglie: chiedendo velocita' un 8B che
        // risponde in mezzo secondo e' una risposta giusta, non un ripiego.
        const minB = o.minB != null ? o.minB : (lane === "big" ? 70 : lane === "fast" ? 0 : 32);
        const needTools = o.needTools !== false;
        // Tutti i provider GRATUITI configurabili (con tool-calling). Prima erano
        // solo 3 → il failover ignorava NVIDIA/SambaNova/Hyperbolic/Cerebras/Mistral
        // e insisteva su OpenRouter. Ora li usa TUTTI. (HF/OpenAI/DeepSeek = a consumo → fuori.)
        // ★ 2026-07-24 — FUORI i provider che NON sono più gratis: erano una FALLA.
        //   • OpenRouter: i modelli :free grossi sono passati a pagamento (404 "use
        //     the paid slug") → il router li provava, falliva, e intanto tu aspettavi.
        //   • Hyperbolic: 402 "insufficient funds", credito finito.
        // Non li cancello (restano nel registro e nel menù a mano): li riaccendi con
        // OPENROUTER_ENABLE=1 / HYPERBOLIC_ENABLE=1 nel .env il giorno che li paghi.
        const FREE = new Set(["kaggle", "groq", "google", "nvidia", "sambanova", "cerebras", "mistral", "alibaba", "cloudflare", "github", "kilo", "opencode"]);
        // ★ 2026-09-01 — OpenRouter entra nel failover solo se e acceso E ha ancora
        // credito: senza il controllo, a portafoglio vuoto ogni richiesta perdeva
        // secondi in 402 prima di ripiegare sulle corsie gratis.
        if (this.openrouterVivo()) FREE.add("openrouter");
        if (/^(1|true|si|yes)$/i.test(String(this.env.HYPERBOLIC_ENABLE || ""))) FREE.add("hyperbolic");
        // Rank = affidabilità/velocità del free tier (più alto = provato prima).
        // ★ 2026-07-19 — ricalibrato su test reali con le chiavi vere:
        //   Groq 344-405ms ✅ · Cerebras ✅ · SambaNova 954ms ✅ (DeepSeek-V3.2 671B uncensored!)
        //   NVIDIA = TIMEOUT secco · Hyperbolic = 402 fondi finiti · OpenRouter :free → a pagamento.
        // I tre verificati veloci vanno provati PER PRIMI; i pantani in fondo (e
        // comunque il cooldown-al-fallimento li salta da solo dopo il primo buco).
        // ★ 2026-07-24 — entrano cloudflare (verificato 200 su gpt-oss-120b/kimi-k2.7)
        // e github models (verificato 200): due corsie gratis in più = meno buchi.
        const provRank = { kaggle: 20, groq: 10, cerebras: 9, sambanova: 8, cloudflare: 7, github: 6, alibaba: 3, openrouter: 3, kilo: 4, opencode: 4, mistral: 2, google: 1, nvidia: 1, hyperbolic: 0 };

        // Modelli VIVI per provider, dal catalogo aggiornato in automatico da /models.
        // Serve a scartare gli ID che il provider ha ritirato (è la causa dei 404
        // "model does not exist" che spegnevano le corsie per 6 ore).
        const liveByProv = {};
        for (const e of [].concat(this.channels.uncensored || [], this.channels.normal || [])) {
            (liveByProv[e.provider] = liveByProv[e.provider] || new Set()).add(e.value);
        }

        // 1) dal catalogo live (se popolato)
        const fromCatalog = [].concat(this.channels.uncensored || [], this.channels.normal || [])
            .filter(e => FREE.has(e.provider))
            .filter(e => needTools ? e.tools !== false : true)
            .map(e => ({
                value: e.value, provider: e.provider,
                b: this._sizeB(e.value) || this._sizeB(e.label) || 0,
                unc: !!e.uncensored, coder: /coder|code|deepseek/i.test(e.value),
                // Serve alla corsia "col credito": senza il campo free non c'e' modo
                // di distinguere un modello pagato da uno gratuito a parita' di nome.
                free: e.free != null ? !!e.free : this.isFreeModel(e.provider, e.id)
            }));

        // 2) semi noti (rete di sicurezza)
        const seed = CloudEngine.SEED_MODELS()
            .filter(s => FREE.has(String(s.value).split(SEP)[0]))
            .filter(s => this._provider(String(s.value).split(SEP)[0])) // solo provider con chiave
            // Se per quel provider abbiamo un catalogo LIVE, il seme vale solo se il
            // modello esiste ancora davvero: niente più tentativi su ID ritirati.
            .filter(s => {
                const p = String(s.value).split(SEP)[0];
                const live = liveByProv[p];
                return !live || live.has(s.value);
            })
            .map(s => ({ value: s.value, provider: String(s.value).split(SEP)[0], b: s.b, unc: s.unc, coder: s.coder,
                free: this.isFreeModel(String(s.value).split(SEP)[0], String(s.value).split(SEP)[1] || "") }));

        // unione (catalogo prima), dedup per value
        const seen = new Set();
        let all = [];
        for (const it of fromCatalog.concat(seed)) {
            if (seen.has(it.value)) continue;
            if (this._inCooldown("prov:" + it.provider)) continue;   // provider con auth morta → saltato in blocco
            // filtro taglia: se la taglia è nota dev'essere ≥ minB; se ignota, la teniamo (deprioritata)
            // ECCEZIONE: la corsia Kaggle (priorità utente) non è soggetta al filtro taglia,
            // così il 14B abliterated resta il default veloce anche con minB=32.
            if (it.provider !== "kaggle" && it.b && it.b < minB) continue;
            seen.add(it.value);
            all.push(it);
        }

        // punteggio: fuori-cooldown ▸ bias uncensored/coder ▸ taglia ▸ provider
        const isReasoning = (v) => /(-r1\b|:r1|\bqwq\b|reason|thinking|distill-r1|deepseek-r1)/i.test(v);
        // CORSIA PREFERENZIALE: famiglie migliori per RE/decompiler (scelta utente).
        const isPreferred = (v) => /qwen|deepseek|hermes/i.test(v);
        const score = (it) => {
            let sc = 0;
            if (this._inCooldown(it.value)) sc -= 1000;
            // I modelli "solo ragionamento" (R1/QwQ) spesso NON supportano il
            // tool-calling: se servono i tool, deprioritizzali (restano comunque
            // in coda, come ultima risorsa).
            if (needTools && isReasoning(it.value)) sc -= 60;
            if (isPreferred(it.value)) sc += 45;      // qwen / deepseek / hermes in cima
            // ★ 2026-09-01 — il bonus uncensored passa da +40 a +120. A +40 non
            // vinceva mai: bastava la differenza di affidabilità fra due provider
            // (×10) a rimetterlo dietro, e chi chiedeva "senza filtri" si ritrovava
            // gpt-oss-120b, che filtrato lo è eccome. Se lo chiedi esplicitamente,
            // ora i modelli senza filtri vanno davvero in testa.
            if (laneUnc && it.unc) sc += 120;
            if (o.coder && it.coder) sc += 40;
            // VELOCE: contano i provider verificati rapidi, non la taglia. I giganti
            // vengono spinti indietro: ai 400 ms di Groq non ci arrivano comunque.
            if (lane === "fast") { sc -= Math.min(it.b, 140) / 4; sc += (provRank[it.provider] || 0) * 6; if (it.b > 200) sc -= 80; }
            // GROSSO: qui la taglia torna a pesare e la fretta conta meno.
            if (lane === "big") { sc += Math.min(it.b, 400) / 4; sc -= (provRank[it.provider] || 0) * 4; }
            // COL CREDITO: hai caricato dei soldi e vuoi usarli. Sopra ai gratis, ma
            // solo per questa richiesta: non cambia il default di nessun'altra.
            if (lane === "paid") { if (!it.free) sc += 150; else sc -= 40; }
            // GRATIS PRIMA, a parita' di tutto il resto. Senza questo la corsia
            // "grosso" apriva il portafoglio da sola: metteva hermes-4-405b (3 $/M)
            // davanti a qwen3-coder-480b, che e' piu' grande ED e' gratis. Il credito
            // si spende quando lo chiedi tu (corsia "col credito"), non per inerzia.
            if (lane !== "paid" && !it.free) sc -= 25;
            // ★ 2026-07-19 — TETTO ALLA TAGLIA. Prima era "b/4 senza tetto": un
            // modello da 480B prendeva +120 e vinceva sempre, così il failover
            // provava PRIMA i giganti da 405-671B (lenti o MORTI, tipo i :free di
            // OpenRouter passati a pagamento) e solo dopo ~15s di tentativi a vuoto
            // ripiegava sul locale lento — l'app sembrava "bloccata". Ora la taglia
            // conta fino a ~140B: oltre, la differenza non giustifica la lentezza.
            sc += Math.min(it.b, 140) / 4;            // taglia con tetto (max +35)
            // ★ AFFIDABILITÀ pesata di più (×10 invece di ×5): i free tier VELOCI e
            // stabili (Groq, Cerebras, ~400ms verificati) devono essere provati per
            // primi nella chat di tutti i giorni. I giganti restano in coda per
            // quando servono davvero (coder/uncensored li ripescano coi loro bonus).
            sc += (provRank[it.provider] || 0) * 10;
            return sc;
        };
        all.sort((a, b) => score(b) - score(a));
        return all;
    }

    // Toglie un modello morto dal catalogo in memoria + dalla cache su disco, così la
    // lista riflette la realtà senza aspettare il prossimo giro di discovery.
    _purgeModel(value) {
        let changed = false;
        for (const ch of ["uncensored", "normal"]) {
            const arr = this.channels[ch];
            if (!Array.isArray(arr)) continue;
            const i = arr.findIndex(e => e.value === value);
            if (i >= 0) { arr.splice(i, 1); changed = true; }
        }
        if (changed) { try { this._saveCatalogCache(); } catch (_) {} }
        return changed;
    }

    _classifyAndCooldown(value, err) {
        const msg = String((err && err.message) || err);
        const provId = String(value).split(SEP)[0];
        // Kaggle: un fallimento = quasi sempre "notebook non acceso ora". Cooldown BREVE
        // (90s), così la corsia torna disponibile appena riavvii il notebook e NON finisce
        // nel ramo "modello non valido" (che la bloccherebbe 6 ore).
        if (provId === "kaggle") { this._setCooldown(value, 90 * 1000, "kaggle: notebook non attivo"); return "kaggle-off"; }
        // AUTH morta (chiave errata/revocata/account inesistente) → scarta l'INTERO
        // provider per un po': inutile provare i suoi altri modelli, falliscono tutti.
        if (/HTTP 401|HTTP 403|user not found|invalid.*api.?key|unauthor|no auth|authentication/i.test(msg)) {
            this._setCooldown("prov:" + provId, 6 * 60 * 60 * 1000, "auth non valida (chiave morta)");
            return "auth";
        }
        // ★ 2026-07-24 — RATE-LIMIT ≠ QUOTA FINITA. Erano trattati uguale (30 min di
        // stop) e bastava una raffica di tool-call per spegnere una corsia sana per
        // mezz'ora: da fuori sembrava "tutte le chiavi esaurite". Ora si distingue:
        //   • 429 al MINUTO  → il provider è solo occupato: pausa di ~1 minuto (o il
        //     Retry-After che ha dichiarato lui). Vale per TUTTO il provider, perché
        //     il limite è della chiave, non del singolo modello.
        //   • credito/quota giornaliera finita (402, "insufficient", "per day") →
        //     quello sì è esaurito davvero: provider da parte per 45 minuti.
        const st429 = this._rate[provId] || {};
        const isMinuteLimit = /HTTP 429|too many requests|rate.?limit|requests per minute|rpm/i.test(msg)
            && !/per day|daily|day limit|quota exceeded for the day/i.test(msg);
        if (isMinuteLimit) {
            const wait = (st429.until && st429.until > Date.now()) ? (st429.until - Date.now()) : 62 * 1000;
            this._rate[provId] = Object.assign({}, st429, { until: Date.now() + wait, at: Date.now() });
            this._saveRate();
            this._setCooldown("prov:" + provId, wait, "limite al minuto (torna subito)");
            return "rate-minute";
        }
        if (CloudEngine.isQuotaError(err)) { this._setCooldown("prov:" + provId, 45 * 60 * 1000, "credito/quota esaurita"); return "quota"; }
        // "No endpoints" = il :free è momentaneamente saturo (nessun provider gratis
        // libero ora): NON è un modello invalido, torna disponibile → cooldown breve.
        if (/no endpoints|no allowed providers|temporarily|503|502|overloaded/i.test(msg)) { this._setCooldown(value, 20 * 60 * 1000, "saturo (no endpoints)"); return "busy"; }
        // Modello davvero inesistente/non abilitato o input non valido → salta a lungo.
        if (/HTTP 40[0-4]|not found|unsupported|invalid model|does not exist|no such model|decommission|deprecated|retired/i.test(msg)) {
            this._purgeModel(value);
            this._setCooldown(value, 6 * 60 * 60 * 1000, "modello non valido (rimosso dal catalogo)");
            return "invalid";
        }
        // Rete/timeout/altro → riprova presto.
        this._setCooldown(value, 3 * 60 * 1000, "errore/timeout"); return "error";
    }

    /**
     * chatTools con FAILOVER automatico su più modelli/provider gratuiti.
     * @returns { content, tool_calls, model, label }
     */
    async chatToolsResilient(messages, tools, o = {}) {
        const cands = this.resilientCandidates(o);
        if (!cands.length) throw new Error("Nessun modello cloud gratuito disponibile (verifica le chiavi in .env).");
        const onFailover = typeof o.onFailover === "function" ? o.onFailover : () => {};
        let lastErr = null;
        const tried = [];
        const attempt = async (c) => {
            tried.push(c.value);
            const r = await this.chatTools(c.value, messages, tools, { temperature: o.temperature, maxTokens: o.maxTokens, signal: o.signal });
            return Object.assign({}, r, { model: c.value, label: this._friendlyLabel(c.value) });
        };
        // Passo 1 — solo corsie sane E non sature al minuto.
        for (const c of cands) {
            if (this._inCooldown(c.value) || this._providerBusy(c.provider)) continue;
            try { return await attempt(c); }
            catch (err) {
                lastErr = err;
                const kind = this._classifyAndCooldown(c.value, err);
                onFailover({ from: c.value, reason: kind, message: String(err.message || err).slice(0, 200) });
            }
        }
        // Passo 2 — ignora il cooldown (magari è vecchio), ma non sprecare tempo sui
        // provider che sappiamo saturi in questo momento.
        for (const c of cands) {
            if (this._providerBusy(c.provider)) continue;
            try { return await attempt(c); }
            catch (err) { lastErr = err; this._classifyAndCooldown(c.value, err); }
        }
        // ★ Passo 3 — ANTI "restare a piedi". Se siamo qui è quasi sempre perché i
        // provider buoni sono saturi AL MINUTO: non sono guasti, tornano fra pochi
        // secondi. Invece di arrendersi, aspetta il primo che si libera (max 70s) e
        // riprova. Meglio una risposta fra 20 secondi che un errore in faccia.
        const wait = this._shortestWait(cands);
        if (wait > 0 && wait <= 70000) {
            onFailover({ from: "(tutti saturi)", reason: "attesa", message: `provider al limite del minuto: riprovo fra ${Math.ceil(wait / 1000)}s` });
            await this._sleep(wait);
            for (const c of cands) {
                if (this._providerBusy(c.provider)) continue;
                try { return await attempt(c); }
                catch (err) { lastErr = err; this._classifyAndCooldown(c.value, err); }
            }
        }
        // AUTO-AZZERAMENTO: esaurito tutto → ripulisci i cooldown transitori così la
        // PROSSIMA richiesta riparte pulita (non serve azzerare a mano).
        this._resetTransientCooldowns();
        throw new Error("Failover esaurito: nessun provider gratuito disponibile ora (provati " + tried.length + "). Ultimo errore: " + String(lastErr && lastErr.message || lastErr).slice(0, 200));
    }

    /** chat() semplice con failover (per la chat del telefono, non-tool). */
    async chatResilient(messages, o = {}) {
        const cands = this.resilientCandidates(Object.assign({ needTools: false }, o));
        if (!cands.length) throw new Error("Nessun modello cloud gratuito disponibile (verifica le chiavi in .env).");
        const onFailover = typeof o.onFailover === "function" ? o.onFailover : () => {};
        let lastErr = null;
        for (const pass of [0, 1]) {
            for (const c of cands) {
                if (pass === 0 && this._inCooldown(c.value)) continue;
                if (this._providerBusy(c.provider)) continue;   // saturo al minuto: torna fra poco
                try {
                    const content = await this.chat(c.value, messages, { temperature: o.temperature, maxTokens: o.maxTokens, onToken: o.onToken, signal: o.signal });
                    return { content, model: c.value, label: this._friendlyLabel(c.value) };
                } catch (err) { lastErr = err; const kind = this._classifyAndCooldown(c.value, err); onFailover({ from: c.value, reason: kind, message: String(err.message || err).slice(0, 200) }); }
            }
        }
        // ANTI "restare a piedi" (come sopra): aspetta il primo che si libera.
        const wait = this._shortestWait(cands);
        if (wait > 0 && wait <= 70000) {
            onFailover({ from: "(tutti saturi)", reason: "attesa", message: `provider al limite del minuto: riprovo fra ${Math.ceil(wait / 1000)}s` });
            await this._sleep(wait);
            for (const c of cands) {
                if (this._providerBusy(c.provider)) continue;
                try {
                    const content = await this.chat(c.value, messages, { temperature: o.temperature, maxTokens: o.maxTokens, onToken: o.onToken, signal: o.signal });
                    return { content, model: c.value, label: this._friendlyLabel(c.value) };
                } catch (err) { lastErr = err; this._classifyAndCooldown(c.value, err); }
            }
        }
        this._resetTransientCooldowns(); // auto-azzeramento: prossima volta riparti pulito
        throw new Error("Failover esaurito (chat). Ultimo errore: " + String(lastErr && lastErr.message || lastErr).slice(0, 200));
    }
}

module.exports = { CloudEngine };
