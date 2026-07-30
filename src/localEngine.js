"use strict";

const http = require("http");

/**
 * LocalEngine — motore per modelli locali (Ollama) con:
 *  - auto-discovery dei modelli presenti su Ollama (localhost:11434)
 *  - classificazione del compito (ragionamento / coding / reverse / agente)
 *  - rotazione automatica: sceglie il miglior modello disponibile per categoria,
 *    preferendo modelli UNCENSORED e con la capability giusta (tools per l'agente)
 *  - chiamata chat diretta (OpenAI-compatible) per i compiti single-shot
 *
 * Nessuna chiave API richiesta: tutto gira in locale. I nuovi modelli scaricati
 * in Ollama vengono agganciati da soli grazie alla discovery dinamica.
 */

const OLLAMA_HOST = "127.0.0.1";
const OLLAMA_PORT = 11434;

/**
 * Converte "8.0B"/"1.5B"/"8x7B" in miliardi di parametri (per stimare il peso).
 * I modelli CLOUD dichiarano la taglia in formati che prima davano 0:
 *   "675000000000" (numero grezzo), "1T"/"1t" (tera), "" (assente).
 */
function parseSizeB(s) {
    if (!s) return 0;
    s = String(s).trim().toLowerCase();
    if (s.includes("x")) { // MoE, es. 8x7b → trattato come grande
        const parts = s.split("x");
        const n = parseFloat(parts[0]) || 1;
        const e = parseFloat(parts[1]) || 7;
        return n * e;
    }
    // Numero grezzo senza suffisso: è il conteggio parametri (675000000000 → 675B).
    if (/^\d+$/.test(s)) return parseFloat(s) / 1e9;
    const m = s.match(/([\d.]+)\s*([bt])/);
    if (!m) return 0;
    return parseFloat(m[1]) * (m[2] === "t" ? 1000 : 1);
}

/** True se il modello gira sui server Ollama (suffisso :cloud o -cloud) e non in locale. */
function isRemoteModel(name) {
    return /[:-]cloud$/i.test(String(name || ""));
}

// Categorie di compito riconosciute dal router.
const CATEGORY = {
    AGENT: "agent",        // multi-step autonomo: apri/leggi/modifica/crea file, "fai tu"
    CODING: "coding",      // refactoring, scrittura/modifica codice
    REVERSE: "reverse",    // decompiling, reverse engineering, analisi binari/malware
    REASONING: "reasoning" // ragionamento, spiegazioni, analisi logica, domande
};

/**
 * Preferenze di modello per categoria: pattern (regex sul nome) in ordine di
 * priorità. Il primo pattern che matcha un modello DAVVERO presente vince.
 * `requireTools` filtra i modelli che non espongono il function calling.
 */
const MODEL_PREFERENCES = {
    // L'agente ha bisogno di tools (function calling) + preferibilmente uncensored.
    [CATEGORY.AGENT]: {
        requireTools: true,
        requireUncensored: true, // il MOTORE della squadra deve essere uncensored (niente rifiuti a metà lavoro)
        prefer: [
            /abliterat/i,            // hermes-3 abliterated: uncensored + tools
            /dolphin.*(mixtral|mistral|qwen|coder)/i, // dolphin agentici con tools
            /hermes3?/i,             // hermes3:8b: tools
            /qwen.*coder/i,          // qwen coder: tools
            /qwen/i
        ]
    },
    // Coding: coder-tuned, tools utili ma non obbligatori.
    [CATEGORY.CODING]: {
        requireTools: false,
        prefer: [
            /qwen.*coder.*(7b|14b|32b)/i,
            /qwen.*coder/i,
            /deepseek.*coder/i,
            /codellama|starcoder/i,
            /abliterat/i,
            /hermes3?/i,
            /dolphin/i
        ]
    },
    // Reverse engineering / decompiling: UNCENSORED è essenziale (niente rifiuti).
    [CATEGORY.REVERSE]: {
        requireTools: false,
        prefer: [
            /dolphin.*(mixtral|mistral)/i,
            /abliterat/i,
            /dolphin/i,
            /hermes3?/i,
            /qwen.*coder/i
        ]
    },
    // Ragionamento generale: preferisci uncensored e capaci.
    [CATEGORY.REASONING]: {
        requireTools: false,
        prefer: [
            /dolphin.*(mixtral|mistral)/i,
            /dolphin/i,
            /abliterat/i,
            /hermes3?/i,
            /qwen/i
        ]
    }
};

class LocalEngine {
    constructor(logger = console) {
        this.logger = logger;
        this.models = [];          // [{ name, parameterSize, family, tools, contextLength }]
        this.lastDiscovery = 0;
        this.baseUrl = `http://${OLLAMA_HOST}:${OLLAMA_PORT}`;
    }

    // ---- Discovery ---------------------------------------------------------

    /** Interroga Ollama e aggiorna l'elenco dei modelli locali disponibili. */
    async discover(force = false) {
        if (!force && this.models.length && Date.now() - this.lastDiscovery < 15000) {
            return this.models;
        }
        try {
            const json = await this._get("/api/tags");
            const list = (json && json.models) || [];
            this.models = list.map(m => ({
                name: m.name,
                parameterSize: (m.details && m.details.parameter_size) || "",
                family: (m.details && m.details.family) || "",
                contextLength: (m.details && m.details.context_length) || 8192,
                tools: Array.isArray(m.capabilities) && m.capabilities.includes("tools"),
                uncensored: /abliterat|dolphin|uncensored/i.test(m.name),
                // I cloud girano sui server Ollama: non pesano sulla GPU locale, ma
                // consumano quota e richiedono rete (vedi _score e chatWithFallback).
                remote: isRemoteModel(m.name)
            }));
            // /api/tags NON popola sempre le capabilities per i modelli da registry
            // custom (es. richardyoung/…): riporta solo ["completion"] anche quando il
            // modello ha i tools. /api/show ispeziona il template ed è autorevole:
            // ri-verifichiamo lì i modelli che sembrano privi di tools.
            await Promise.all(this.models.filter(m => !m.tools).map(async (m) => {
                try {
                    const show = await this._post("/api/show", JSON.stringify({ model: m.name }));
                    if (Array.isArray(show.capabilities) && show.capabilities.includes("tools")) m.tools = true;
                } catch (_) { /* lascia tools=false */ }
            }));
            this.lastDiscovery = Date.now();
            this.logger.log && this.logger.log(`[LocalEngine] ${this.models.length} modelli locali:`, this.models.map(m => m.name).join(", "));
        } catch (err) {
            this.logger.error && this.logger.error("[LocalEngine] discovery fallita:", err.message);
            this.models = [];
        }
        return this.models;
    }

    /** True se Ollama risponde. */
    async isOnline() {
        try {
            await this._get("/api/tags");
            return true;
        } catch (_) {
            return false;
        }
    }

    getModels() {
        return this.models;
    }

    // ---- Routing -----------------------------------------------------------

    /**
     * Classifica il prompt in una categoria di compito.
     * `forcedMode` (dalla UI) ha priorità: 'agent' | 'coding' | 'reverse' | 'reasoning'.
     */
    classify(prompt, forcedMode = "auto") {
        if (forcedMode && forcedMode !== "auto" && CATEGORY[forcedMode.toUpperCase()]) {
            return CATEGORY[forcedMode.toUpperCase()];
        }
        const p = (prompt || "").toLowerCase();

        // Segnali di compito AGENTE autonomo (tocca file / esegue / multi-step).
        const agentSignals = [
            "apri", "leggi il file", "leggi i file", "modifica", "crea un file", "crea il file",
            "scrivi il file", "scrivi su", "refactor", "refactoring", "implementa", "esegui",
            "lancia", "installa", "fai tu", "da solo", "in autonomia", "studia il progetto",
            "analizza il progetto", "analizza la cartella", "correggi il", "sistema il codice",
            "apri e", "copia il file", "sposta il file", "cerca nei file", "trova nel progetto",
            "run ", "open ", "read file", "write file", "edit ", "fix the", "create file"
        ];
        if (agentSignals.some(s => p.includes(s))) return CATEGORY.AGENT;

        // Reverse engineering / decompiling.
        const reverseSignals = [
            "decompil", "reverse engineer", "reverse-engineer", "reversing", "disassembl",
            "disasm", "binario", "binary", "malware", "shellcode", "unpack", "deobfusc",
            "offuscat", "obfuscat", "crack", "patch il binario", "ida ", "ghidra",
            "hex", "assembly", "asm ", "firmware", ".exe", ".dll", "bytecode"
        ];
        if (reverseSignals.some(s => p.includes(s))) return CATEGORY.REVERSE;

        // Coding.
        const codingSignals = [
            "funzione", "function", "classe", "class ", "bug", "debug", "errore nel codice",
            "scrivi codice", "genera codice", "ottimizza", "optimize", "unit test", "test ",
            "algoritmo", "regex", "sql", "api ", "endpoint", "```", "component", "typescript",
            "javascript", "python", "c++", "rust", "converti in", "traduci il codice"
        ];
        if (codingSignals.some(s => p.includes(s))) return CATEGORY.CODING;

        return CATEGORY.REASONING;
    }

    /**
     * Sceglie il miglior modello locale per una categoria, tra quelli presenti.
     * Ritorna il nome del modello o null se nessuno è adatto.
     */
    pickModel(category, { toolsOnly = false } = {}) {
        const pref = MODEL_PREFERENCES[category] || MODEL_PREFERENCES[CATEGORY.REASONING];
        let pool = this.models;
        if (pref.requireTools || toolsOnly) {
            const withTools = pool.filter(m => m.tools);
            if (withTools.length) pool = withTools;
        }
        // Il motore-agente deve restare uncensored se ne esiste almeno uno adatto,
        // così non parti uncensored dalla chat e poi l'agente ti blocca a metà.
        if (pref.requireUncensored) {
            const unc = pool.filter(m => m.uncensored);
            if (unc.length) pool = unc;
        }
        if (!pool.length) return this.models.length ? this.models[0].name : null;
        // Punteggio trasparente: fra più candidati (es. 3 dolphin) vince quello
        // col miglior punteggio per la categoria, non "il primo che capita".
        let best = null, bestScore = -Infinity;
        for (const m of pool) {
            const s = this._score(m, category, pref);
            if (s > bestScore) { bestScore = s; best = m; }
        }
        return best ? best.name : pool[0].name;
    }

    /**
     * Punteggio di un modello per una categoria. Fattori (in ordine di peso):
     *  - aderenza al tipo di compito (posizione nella lista di preferenze)
     *  - uncensored (fondamentale per reverse; importante per agente/ragionamento)
     *  - taglia adatta all'hardware (premia 3-9B, penalizza >14B perché lenti)
     *  - bonus coder per il coding
     */
    _score(m, category, pref) {
        let score = 0;
        // Tier di aderenza al compito.
        const tierIdx = pref.prefer.findIndex(rx => rx.test(m.name));
        score += (tierIdx >= 0) ? (pref.prefer.length - tierIdx) * 100 : 0;
        // Tools (necessari per l'agente, utili altrove).
        if (m.tools) score += (category === CATEGORY.AGENT ? 60 : 8);
        // Uncensored.
        if (m.uncensored) score += (category === CATEGORY.REVERSE ? 70 : (category === CATEGORY.AGENT || category === CATEGORY.REASONING ? 30 : 10));
        // Coder-tuned per il coding.
        if (category === CATEGORY.CODING && /coder|code/i.test(m.name)) score += 40;
        // Ma per il RUOLO AGENTE i "coder" vanno penalizzati: dichiarano i tools
        // ma in pratica NON li invocano in nativo (li scrivono come testo).
        if (category === CATEGORY.AGENT && /coder/i.test(m.name)) score -= 60;
        // I modelli CLOUD non girano sulla GPU di casa, quindi la penalità taglia
        // non li riguarda: esce prima di applicarla.
        //
        // SCELTA DELIBERATA: nessun bonus: in automatico NON vincono mai contro un
        // abliterated locale, perché nessuno di loro è uncensored e un rifiuto a
        // metà lavoro (reverse, Ghidra, agente) costa più della potenza in più.
        // Restano selezionabili A MANO dal menu modelli, ed è lì che si usano.
        if (m.remote) return score;

        // Taglia vs hardware (default: sweet spot 3-9B).
        const b = parseSizeB(m.parameterSize);
        if (b > 0) {
            // L'utente ha 32GB RAM e preferisce la potenza: comfort fino a ~15B.
            if (b >= 3 && b <= 15) score += 25;
            else if (b > 15 && b <= 35) score += 3;   // grande ma gira (lento) in RAM
            else if (b > 35) score -= 60;             // troppo grande per la GPU/velocità
            else if (b < 2) score -= 12;              // troppo piccolo = debole
            // A parità, il modello più grande (entro il comfort) vince: 14B > 8B > 3B.
            score += Math.min(b, 15);
        }
        return score;
    }

    /** Il prompt fa riferimento a un file/percorso concreto? (serve l'agente coi tool) */
    _mentionsFile(prompt) {
        const p = prompt || "";
        return /\.[a-z0-9]{1,5}\b/i.test(p)                 // estensione file (.exe .js .py …)
            || /[\\/][\w.\-]+[\\/]/.test(p)                 // percorso con separatori
            || /\b(il|questo|nel|del|questa)\s+(file|progetto|cartella|binario|codice)\b/i.test(p)
            || /\bfile\s+[\w.\-]+/i.test(p);
    }

    /**
     * Assegnazione RUOLI → modello: la mappa trasparente "chi fa cosa".
     * L'utente (e la UI) può vederla per capire quale modello è il motore,
     * quale il ragionatore, quale il coder, quale per il reverse.
     */
    getRoleAssignments() {
        return {
            agente:      this.pickModel(CATEGORY.AGENT),      // motore squadra Hermes (tools)
            ragionamento: this.pickModel(CATEGORY.REASONING),
            coding:      this.pickModel(CATEGORY.CODING),
            reverse:     this.pickModel(CATEGORY.REVERSE)
        };
    }

    /**
     * Router completo: dal prompt → { category, mode, model }.
     *  - mode 'agent'  → gestito da Hermes (ACP): ha i TOOL per aprire/leggere/
     *    modificare file ed eseguire strumenti esterni (strings, objdump, …).
     *  - mode 'direct' → chat diretta al modello locale (nessun tool: solo testo).
     *
     * Regola chiave: se il compito TOCCA un file/percorso concreto, serve l'agente
     * (coi tool), anche per reverse/coding. Solo le domande concettuali restano dirette.
     */
    route(prompt, forcedMode = "auto") {
        const category = this.classify(prompt, forcedMode);
        const touchesFile = this._mentionsFile(prompt);
        // Percorso concreto = c'è un file reale su cui lavorare (separatori o estensione binaria).
        const hasConcretePath = /[a-z]:[\\/]|[\\/][\w.\-]+[\\/]|\.(dll|exe|sys|bin|so|js|ts|py|c|cpp|h|rs|go|java|cs|json|md|txt|xml|html|css)\b/i.test(prompt || "");

        // AGENTE esplicito, reverse/coding su file, o QUALSIASI percorso concreto → serve l'agente
        // (con i tool: se c'è un file vero, si lavora, non si chiacchiera).
        const needsAgent = category === CATEGORY.AGENT
            || hasConcretePath
            || ((category === CATEGORY.REVERSE || category === CATEGORY.CODING) && touchesFile);

        if (needsAgent) {
            // L'agente ha bisogno di un modello con TOOLS; scegli il migliore per
            // il TIPO di compito reale (coding→coder, reverse→uncensored) ma solo
            // fra i modelli tools-capable. Se la categoria è già "agente", usa le
            // preferenze dell'agente.
            const agentCat = category === CATEGORY.AGENT ? CATEGORY.AGENT : category;
            return { category, mode: "agent", model: this.pickModel(agentCat, { toolsOnly: true }) };
        }
        return { category, mode: "direct", model: this.pickModel(category) };
    }

    // ---- Chat diretta ------------------------------------------------------

    /**
     * Chat completion diretta su Ollama (OpenAI-compatible /v1/chat/completions).
     * messages: [{role, content}]. onToken(chunk) opzionale per lo streaming.
     */
    async chat(model, messages, { temperature = 0.7, onToken = null, signal = null } = {}) {
        const wantStream = typeof onToken === "function";
        const body = JSON.stringify({
            model,
            messages: LocalEngine._toMultiModal(messages),
            temperature,
            stream: wantStream,
            // Tiene il modello caricato in memoria per 30 min tra un turno e l'altro:
            // senza questo, un 14B viene scaricato dopo 5 min e ricaricato (lento) al
            // turno dopo, causando timeout e attese enormi.
            keep_alive: "30m"
        });

        if (!wantStream) {
            const json = await this._post("/v1/chat/completions", body);
            return (json.choices && json.choices[0] && json.choices[0].message && json.choices[0].message.content) || "";
        }

        // Streaming SSE.
        return new Promise((resolve, reject) => {
            const req = http.request({
                host: OLLAMA_HOST,
                port: OLLAMA_PORT,
                path: "/v1/chat/completions",
                method: "POST",
                headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) }
            }, (res) => {
                if (res.statusCode >= 400) {
                    let e = "";
                    res.on("data", c => e += c);
                    res.on("end", () => reject(new Error(`Ollama HTTP ${res.statusCode}: ${e}`)));
                    return;
                }
                let full = "";
                let buf = "";
                res.on("data", chunk => {
                    buf += chunk.toString("utf8");
                    let idx;
                    while ((idx = buf.indexOf("\n")) >= 0) {
                        const line = buf.slice(0, idx).trim();
                        buf = buf.slice(idx + 1);
                        if (!line.startsWith("data:")) continue;
                        const payload = line.slice(5).trim();
                        if (payload === "[DONE]") continue;
                        try {
                            const j = JSON.parse(payload);
                            const delta = j.choices && j.choices[0] && j.choices[0].delta && j.choices[0].delta.content;
                            if (delta) { full += delta; onToken(delta); }
                        } catch (_) { /* riga parziale: ignora */ }
                    }
                });
                res.on("end", () => resolve(full));
            });
            req.on("error", reject);
            if (signal) signal.addEventListener("abort", () => req.destroy(new Error("aborted")));
            req.write(body);
            req.end();
        });
    }

    /**
     * Chat NON-streaming con tool nativi (function calling di Ollama).
     * Ritorna { content, tool_calls } dove tool_calls è l'array OpenAI-style.
     * Lo streaming è volutamente OFF: il tool-calling nativo di Ollama è
     * affidabile solo in non-streaming.
     */
    async chatTools(model, messages, tools, { temperature = 0.3 } = {}) {
        const body = JSON.stringify({ model, messages: LocalEngine._toMultiModal(messages), tools, stream: false, temperature, keep_alive: "30m" });
        const json = await this._post("/v1/chat/completions", body);
        const msg = (json.choices && json.choices[0] && json.choices[0].message) || {};
        return { content: msg.content || "", tool_calls: msg.tool_calls || [] };
    }

    // ---- Retrocessione cloud → locale --------------------------------------

    /** Il miglior modello NON-remoto per la categoria (riserva offline). */
    pickLocalFallback(category, { toolsOnly = false } = {}) {
        const remoteNames = new Set(this.models.filter(m => m.remote).map(m => m.name));
        const saved = this.models;
        try {
            this.models = saved.filter(m => !remoteNames.has(m.name));
            return this.models.length ? this.pickModel(category, { toolsOnly }) : null;
        } finally {
            this.models = saved;
        }
    }

    /**
     * Come chat(), ma se il modello è CLOUD e la chiamata fallisce (rete assente,
     * quota Ollama esaurita, server giù) ripiega sul miglior modello locale invece
     * di bloccare il lavoro. `onFallback(from, to, motivo)` per avvisare in chat.
     */
    async chatWithFallback(model, messages, opts = {}) {
        const { category = CATEGORY.REASONING, onFallback = null, ...rest } = opts;
        try {
            return await this.chat(model, messages, rest);
        } catch (err) {
            if (!isRemoteModel(model)) throw err;
            const local = this.pickLocalFallback(category);
            if (!local) throw err;
            onFallback && onFallback(model, local, err.message);
            // Lo streaming già iniziato va riavviato dal modello locale: il chiamante
            // riceve la risposta completa del ripiego.
            return await this.chat(local, messages, rest);
        }
    }

    /** Variante con tool nativi della retrocessione cloud → locale. */
    async chatToolsWithFallback(model, messages, tools, opts = {}) {
        const { category = CATEGORY.AGENT, onFallback = null, ...rest } = opts;
        try {
            return await this.chatTools(model, messages, tools, rest);
        } catch (err) {
            if (!isRemoteModel(model)) throw err;
            const local = this.pickLocalFallback(category, { toolsOnly: true });
            if (!local) throw err;
            onFallback && onFallback(model, local, err.message);
            return await this.chatTools(local, messages, tools, rest);
        }
    }

    // ---- HTTP helpers ------------------------------------------------------

    _get(path) {
        return new Promise((resolve, reject) => {
            // 20s (non 5s): quando Ollama sta caricando un modello grande, anche
            // /api/tags può rispondere lento; con 5s lo scambiavamo per "offline".
            const req = http.get({ host: OLLAMA_HOST, port: OLLAMA_PORT, path, timeout: 20000 }, (res) => {
                let data = "";
                res.on("data", c => data += c);
                res.on("end", () => {
                    try { resolve(JSON.parse(data)); }
                    catch (e) { reject(new Error("JSON non valido da Ollama: " + e.message)); }
                });
            });
            req.on("timeout", () => req.destroy(new Error("timeout Ollama")));
            req.on("error", reject);
        });
    }

    _post(path, body) {
        return new Promise((resolve, reject) => {
            const req = http.request({
                host: OLLAMA_HOST, port: OLLAMA_PORT, path, method: "POST",
                headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
                // I modelli grandi (es. 14B) girano in RAM su questo hardware: una singola
                // risposta può richiedere minuti, e la PRIMA include il caricamento del
                // modello. 2 minuti erano troppo pochi → "timeout Ollama" a raffica.
                timeout: 600000
            }, (res) => {
                let data = "";
                res.on("data", c => data += c);
                res.on("end", () => {
                    if (res.statusCode >= 400) return reject(new Error(`Ollama HTTP ${res.statusCode}: ${data}`));
                    try { resolve(JSON.parse(data)); }
                    catch (e) { reject(new Error("JSON non valido da Ollama: " + e.message)); }
                });
            });
            req.on("timeout", () => req.destroy(new Error("timeout Ollama")));
            req.on("error", reject);
            req.write(body);
            req.end();
        });
    }

    /**
     * Converte i messaggi in formato multimodale OpenAI-compatible se contengono
     * immagini: un messaggio con `.images` (array di base64) diventa
     * { role, content: [ {type:"text",text}, {type:"image_url", url:"data:..."} ] }.
     * I messaggi senza immagini restano invariati. Serve ai modelli VISIONE (llava).
     */
    static _toMultiModal(messages) {
        if (!Array.isArray(messages)) return messages;
        return messages.map(m => {
            if (m && Array.isArray(m.images) && m.images.length) {
                const text = (typeof m.content === "string") ? m.content : (m.content && m.content.text) || "";
                const content = [{ type: "text", text: text || "Descrivi l'immagine." }];
                for (const b64 of m.images) {
                    const mime = (typeof b64 === "object" && b64.mime) ? b64.mime : "image/png";
                    const data = (typeof b64 === "object" && b64.data) ? b64.data : String(b64);
                    content.push({ type: "image_url", url: "data:" + mime + ";base64," + data });
                }
                return { role: m.role, content };
            }
            return m;
        });
    }
}

module.exports = { LocalEngine, CATEGORY, parseSizeB, isRemoteModel };
