"use strict";

const https = require("https");
const fs = require("fs");
const path = require("path");
const registry = require("./providerRegistry");

/**
 * bountyHunter — "Cacciatore di taglie" VERO.
 *
 * ★ 2026-07-24 — Prima era solo una lista scritta a mano dentro providerRegistry:
 * proponeva sempre le stesse cose e invecchiava (OpenRouter passato a pagamento,
 * Hyperbolic a credito zero, modelli Cerebras cambiati... e nessuno se ne accorgeva).
 *
 * Adesso VA A CACCIA DAVVERO: interroga fonti pubbliche che tracciano i provider
 * LLM con piano gratuito e ne ricava l'elenco aggiornato, poi lo confronta con i
 * provider che l'utente ha già e propone SOLO le novità, con il link per prendere
 * la chiave. Nessun account viene creato in automatico: la caccia è "trova e
 * proponi", la decisione resta all'utente.
 *
 * Fonti (pubbliche, leggibili a macchina, niente scraping selvaggio):
 *   1. cheahjs/free-llm-api-resources — l'elenco più aggiornato di API LLM free
 *      (sezioni "Free Providers" e "Providers with trial credits").
 *   2. OpenRouter /api/v1/models — per sapere quali modelli sono ANCORA a costo 0.
 *
 * Il risultato è messo in cache su disco: la rete si tocca al massimo una volta
 * al giorno, il resto arriva dalla cache (niente traffico inutile, niente attese).
 */

const SOURCES = [
    {
        id: "free-llm-api-resources",
        host: "raw.githubusercontent.com",
        path: "/cheahjs/free-llm-api-resources/main/README.md",
        label: "free-llm-api-resources (GitHub)"
    },
    // ★ 2026-07-24 — SECONDA FONTE, per non fidarsi di una sola ed evitare fregature.
    // Questa elenca SOLO piani gratuiti permanenti (niente crediti di prova), con i
    // limiti RPM/RPD dichiarati. Un provider visto da entrambe le fonti viene marcato
    // "confermato": è il segnale più affidabile che abbiamo senza aprire un account.
    {
        id: "awesome-free-llm-apis",
        host: "raw.githubusercontent.com",
        path: "/mnfst/awesome-free-llm-apis/main/README.md",
        label: "awesome-free-llm-apis (GitHub)"
    },
    // ★ 2026-07-27 — TERZA FONTE: il catalogo MODELLI di OpenRouter (JSON vivo).
    // Elenca i modelli a costo 0 veri (pricing.prompt==="0") e, per nome, quelli
    // senza filtri (abliterated/dolphin/magnum...). Arricchisce la caccia coi
    // modelli free realmente erogati OGGI, non solo quelli delle liste curate.
    {
        id: "openrouter-models",
        host: "openrouter.ai",
        path: "/api/v1/models",
        label: "OpenRouter /api/v1/models",
        format: "json-or"
    }
];

/** Parole che tradiscono un provider/modello SENZA filtri (uncensored). */
const UNC_RE = /abliter|dolphin|uncensor|magnum|fimbul|no.?filter|liberated|samurai|rok\/|ice-|gryphe|kunoichi|nyxn|midnight|kat-|erot|roleplay|rp-max|instruct-ablit|degold/i;

const CACHE_TTL = 24 * 60 * 60 * 1000;   // una caccia al giorno basta e avanza

/** Nomi/alias dei provider che conosciamo già, per riconoscere i doppioni. */
function knownAliases() {
    const map = new Map();   // alias normalizzato -> id nostro
    const add = (alias, id) => { const k = norm(alias); if (k) map.set(k, id); };
    for (const p of registry.PROVIDERS) {
        add(p.id, p.id);
        add(p.label, p.id);
        add(String(p.label).replace(/\(.*\)/, ""), p.id);
        if (p.host) add(String(p.host).replace(/^(api|router|integrate|llm|cloud|models)\./, "").split(".")[0], p.id);
        // ★ 2026-07-30 — alias del catalogo preconfigurato: sono i nomi con cui le
        // liste online chiamano il provider ("io.net", "kimi", "command r", "sn19"...).
        // Senza questi il cacciatore trovava il provider ma non sapeva agganciarlo a
        // una voce del registro, quindi niente "Incolla qui" e niente auto-rilevamento.
        for (const a of (p.aliases || [])) add(a, p.id);
    }
    // alias manuali per come li scrivono le liste online
    add("google ai studio", "google"); add("gemini", "google");
    add("mistral la plateforme", "mistral"); add("mistral codestral", "mistral"); add("mistral ai", "mistral");
    add("huggingface inference providers", "hf"); add("hugging face", "hf");
    add("sambanova cloud", "sambanova"); add("nvidia nim", "nvidia");
    add("github models", "github"); add("ollama cloud", "ollama-cloud");
    add("alibaba cloud international model studio", "alibaba");
    return map;
}
function norm(s) {
    return String(s || "").toLowerCase()
        .replace(/[’']/g, "").replace(/[^a-z0-9]+/g, " ").trim();
}

class BountyHunter {
    constructor(logger = console, opts = {}) {
        this.logger = logger;
        this.storageDir = opts.storageDir || process.cwd();
        this.cacheFile = path.join(this.storageDir, "bounty-hunt.json");
    }

    _load() { try { return JSON.parse(fs.readFileSync(this.cacheFile, "utf8")); } catch (_) { return null; } }
    _save(d) { try { fs.mkdirSync(this.storageDir, { recursive: true }); fs.writeFileSync(this.cacheFile, JSON.stringify(d), "utf8"); } catch (_) {} }

    _getText(host, pathname) {
        return new Promise((resolve, reject) => {
            const req = https.get({
                host, path: pathname, timeout: 15000,
                headers: { "User-Agent": "Antigravity-BountyHunter/1.0", "Accept": "text/plain,*/*" }
            }, (res) => {
                if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                    // un solo salto di redirect, per sicurezza
                    try {
                        const u = new URL(res.headers.location, `https://${host}${pathname}`);
                        return this._getText(u.host, u.pathname + u.search).then(resolve, reject);
                    } catch (e) { return reject(e); }
                }
                if (res.statusCode >= 400) return reject(new Error(`${host} HTTP ${res.statusCode}`));
                let d = ""; res.setEncoding("utf8");
                res.on("data", c => d += c);
                res.on("end", () => resolve(d));
            });
            req.on("timeout", () => req.destroy(new Error("timeout " + host)));
            req.on("error", reject);
        });
    }

    /**
     * Estrae i provider dal README della lista. Struttura del documento:
     *   ## Free Providers            → piano gratuito vero
     *   ### [Nome](url)              → un provider
     *   | modello | limiti |         → tabella dei modelli sotto ogni provider
     *   ## Providers with trial credits → credito di prova (gratis ma a scadenza)
     */
    _parseList(md) {
        const out = [];
        let section = null;         // "free" | "trial" | null
        let cur = null;
        const push = () => { if (cur) { out.push(cur); cur = null; } };

        for (const raw of String(md).split(/\r?\n/)) {
            const line = raw.trim();
            const h2 = line.match(/^##\s+(.+)$/);
            if (h2 && !/^###/.test(line)) {
                push();
                const t = norm(h2[1]);
                // "Free Providers" (cheahjs) e "Provider APIs" (mnfst, che elenca solo
                // piani gratuiti permanenti) = roba buona. "Trial credits" = crediti a
                // scadenza: li teniamo da parte ma NON li proponiamo.
                if (/free provider|provider apis/.test(t)) section = "free";
                else if (/trial credit/.test(t)) section = "trial";
                else section = null;
                continue;
            }
            if (!section) continue;
            const h3 = line.match(/^###\s+\[([^\]]+)\]\(([^)]+)\)/);
            if (h3) {
                push();
                cur = { name: h3[1].trim(), url: h3[2].trim(), kind: section, models: [], notes: [] };
                continue;
            }
            if (!cur) continue;
            // Le tabelle dei modelli sono in HTML dentro il markdown:
            //   <tr><td>gpt-oss-120b</td><td>30 requests/minute<br>...</td></tr>
            // I limiti sono la parte più preziosa: dicono le richieste/minuto, che è
            // il vero muro dei piani free (non la quota giornaliera).
            const tr = line.match(/<tr>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>/i);
            if (tr) {
                const name = tr[1].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
                const lim = tr[2].replace(/<br\s*\/?>/gi, " · ").replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
                if (name && cur.models.length < 10) cur.models.push(lim ? `${name} (${lim})` : name);
                continue;
            }
            // righe di tabella markdown classiche: | modello | qualcosa |
            const row = line.match(/^\|\s*([^|]+?)\s*\|/);
            if (row && !/^\|\s*-+/.test(line) && !/^\|\s*model\b/i.test(line)) {
                const m = row[1].replace(/\[|\]|##/g, "").replace(/\(.*?\)/g, "").trim();
                if (m && m.length < 80 && cur.models.length < 10 && !/^model$/i.test(m)) cur.models.push(m);
            } else if (line.startsWith("*") || line.startsWith("-")) {
                const n = line.replace(/^[*-]\s*/, "").trim();
                if (n && n.length < 200 && cur.notes.length < 3) cur.notes.push(n);
            }
        }
        push();
        return out;
    }

    /**
     * Parser JSON di OpenRouter /api/v1/models: estrae i modelli a costo 0
     * (pricing.prompt==="0" && pricing.completion==="0") e li tratta come
     * provider "openrouter" (conosciuto dal registro). Marca uncensored per nome.
     */
    _parseOrModels(raw) {
        try {
            const j = JSON.parse(raw);
            const data = Array.isArray(j) ? j : (j.data || []);
            const free = data.filter(m => m && m.pricing &&
                String(m.pricing.prompt) === "0" && String(m.pricing.completion) === "0");
            const out = [];
            for (const m of free.slice(0, 80)) {
                const name = m.id || m.name || "";
                if (!name) continue;
                const unc = UNC_RE.test(name);
                out.push({
                    name,
                    url: "https://openrouter.ai/" + encodeURIComponent(name),
                    kind: "free",
                    models: [name],
                    notes: [],
                    uncensored: unc
                });
            }
            return out;
        } catch (_) { return []; }
    }

    /**
     * Va a caccia. Ritorna:
     *   { at, sources, total, nuovi:[...], gia:[...], error }
     * "nuovi" = provider gratuiti che NON hai ancora (con link per la chiave).
     * @param {object} o  force:true ignora la cache · configuredIds: id già attivi
     */
    async hunt(o = {}) {
        const cached = this._load();
        if (!o.force && cached && Date.now() - (cached.at || 0) < CACHE_TTL) {
            return this._decorate(cached, o.configuredIds || [], o);
        }
        let found = [];
        const sourcesOk = [];
        for (const s of SOURCES) {
            try {
                const raw = await this._getText(s.host, s.path);
                const list = (s.format === "json-or") ? this._parseOrModels(raw) : this._parseList(raw);
                if (list.length) {
                    for (const p of list) p.source = s.id;
                    found = found.concat(list);
                    sourcesOk.push(s.label);
                }
            } catch (e) {
                this.logger.error && this.logger.error("[BountyHunter] fonte " + s.id + ":", e.message);
            }
        }
        if (!found.length) {
            // rete giù o fonte cambiata: meglio la cache vecchia che niente
            if (cached) return this._decorate(Object.assign({}, cached, { stale: true }), o.configuredIds || [], o);
            return { at: Date.now(), sources: [], total: 0, nuovi: [], gia: [], error: "nessuna fonte raggiungibile" };
        }
        // FUSIONE per nome: se lo stesso provider compare in più fonti non lo si
        // duplica, si tiene traccia di QUANTE fonti lo citano. Due fonti indipendenti
        // che dicono "questo è gratis" valgono molto più di una.
        const byName = new Map();
        for (const p of found) {
            const k = norm(p.name);
            if (!k) continue;
            const prev = byName.get(k);
            if (!prev) { byName.set(k, Object.assign({ sources: [p.source] }, p)); continue; }
            if (prev.sources.indexOf(p.source) < 0) prev.sources.push(p.source);
            // tieni il record più ricco (quello con i modelli/limiti)
            if ((p.models || []).length > (prev.models || []).length) { prev.models = p.models; prev.url = p.url || prev.url; }
            // se una fonte lo dà come piano gratuito permanente, vince su "trial"
            if (p.kind === "free") prev.kind = "free";
        }
        const uniq = Array.from(byName.values());
        const data = { at: Date.now(), sources: sourcesOk, providers: uniq };
        this._save(data);
        return this._decorate(data, o.configuredIds || [], o);
    }

    /**
     * Riconosce se un provider cacciato è "senza filtri" (uncensored/abliterated/RP).
     * Lo capisce dal nome (online capita spesso "X Uncensored", "abliterated",
     * "dolphin", "roleplay") e dagli alias che conosciamo già nel registro.
     */
    _isUnc(name, knownId) {
        const n = norm(name || "");
        if (/uncensor|abliterat|abliterated|dolphin|unfilter|no[ -]?filter|nsfw|roleplay|\brp\b|free[ -]?filter|without[ -]?filter/.test(n)) return true;
        const uncIds = new Set(["venice", "arliai", "featherless", "hf", "nvidia", "kaggle", "ollama", "ollama-cloud"]);
        if (knownId && uncIds.has(knownId)) return true;
        return false;
    }

    /** Divide fra "ce l'hai già" e "nuovi da provare", con il match sugli alias.
     * ★ 2026-07-24 — Di default vengono proposti SOLO i piani gratuiti PERMANENTI:
     * i "crediti di prova" (che finiscono, e spesso chiedono la carta) restano fuori,
     * su richiesta esplicita dell'utente. Si possono chiedere con includeTrial:true.
     * ★ 2026-07-27 — se o.uncensored è true, ritorna SOLO i provider senza filtri
     * (terza "categoria" del cacciatore di taglie). Ogni riga porta anche il flag
     * `uncensored` così la UI può mostrarlo distintamente.
     */
    _decorate(data, configuredIds, o = {}) {
        const aliases = knownAliases();
        const configured = new Set(configuredIds);
        const nuovi = [], gia = [], trial = [];
        for (const p of (data.providers || [])) {
            const id = aliases.get(norm(p.name)) || null;
            const nFonti = (p.sources || []).length || 1;
            // ★ 2026-07-27 — flag uncensored: dal nome online, dal campo della fonte,
            // o dal registro (se il provider è noto e marcato uncensored).
            const regUnc = id ? (registry.byId(id) || {}).uncensored : false;
            const uncensored = !!(p.uncensored || regUnc || UNC_RE.test(p.name));
            const row = {
                name: p.name, url: p.url, kind: p.kind,
                models: (p.models || []).slice(0, 6), note: (p.notes && p.notes[0]) || "",
                knownId: id, configured: id ? configured.has(id) : false,
                fonti: nFonti,
                uncensored,
                // "confermato" = citato come gratuito da PIÙ fonti indipendenti.
                confermato: nFonti >= 2
            };
            if (row.configured) { gia.push(row); continue; }
            if (row.kind === "trial") { trial.push(row); continue; }
            // categoria "senza filtri": se richiesto, tieni SOLO quelli uncensored
            if (o.uncensored && !uncensored) continue;
            nuovi.push(row);
        }
        // in cima i confermati da più fonti, poi quelli con i modelli dichiarati
        const rank = r => (r.confermato ? 0 : 1) * 10 + ((r.models || []).length ? 0 : 2) + (r.knownId ? 1 : 0);
        nuovi.sort((a, b) => rank(a) - rank(b));
        return {
            at: data.at, stale: !!data.stale, sources: data.sources || [],
            total: (data.providers || []).length,
            nuovi: o.includeTrial ? nuovi.concat(trial) : nuovi,
            trialEsclusi: trial.length,
            gia
        };
    }
}

module.exports = { BountyHunter };
