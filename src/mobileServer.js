"use strict";

/**
 * mobileServer.js — piccolo web-server locale che serve la chat dell'estensione
 * al BROWSER del telefono, attraverso l'interfaccia Tailscale.
 *
 * Idea: l'intero motore (LocalOrchestrator) parla col mondo SOLO via
 * `webview.postMessage(msg)`. Qui creiamo un "finto webview" che, invece di
 * postare alla webview di VS Code, inoltra i messaggi al telefono via SSE
 * (Server-Sent Events). Le azioni del telefono (invia/stop/approva) tornano
 * indietro con semplici POST e vengono instradate all'orchestratore.
 *
 * NON dipende da VS Code: gira anche a editor chiuso (serve solo Ollama).
 * Avvio standalone:  node src/mobileServer.js
 * Oppure dall'estensione via il comando "Antigravity: Avvia server mobile".
 *
 * Sicurezza: sulla tailnet il server è già privato ai tuoi dispositivi; in più
 * richiediamo un TOKEN (MOBILE_TOKEN nel .env, o generato e stampato all'avvio).
 * Apri sul telefono:  http://<IP-PC-tailscale>:<porta>/?t=<TOKEN>
 */

const http = require("http");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");

// AUTO-RIPARAZIONE: prima di caricare i moduli del motore, ripara quelli
// eventualmente corrotti (mancanti/troncati/sintassi rotta) da una copia sana.
// selfHeal dipende solo da moduli nativi, quindi è sicuro caricarlo per primo.
try {
    const { verifyAndRepair, CRITICAL_FILES } = require("./selfHeal");
    verifyAndRepair({ srcDir: __dirname, files: CRITICAL_FILES, logger: console });
} catch (_) { /* selfHeal assente/rotto: si prosegue comunque */ }

// ★ 2026-07-27 — Cacciatore di bug: disattivato all'avvio per non bloccare il server.
// Resta disponibile on-demand tramite l'interfaccia (chiama /bugHunter/scan).
// try { ... } catch (_) {}

// ★ 2026-07-27 — FileWatcher: disattivato all'avvio. Si attiva solo se richiesto.
// try { ... } catch (_) {}

const LocalOrchestrator = require("./localOrchestrator");
let TorBrowser = null;
try { ({ TorBrowser } = require("./torBrowser")); } catch (_) { /* tor opzionale */ }
let kaggleWaker = null;
let isUp, ensureUpSize, status, shutdown, quota, KAGGLE_HOST;
try { ({ isUp, ensureUpSize, status, shutdown, quota, KAGGLE_HOST } = require("./kaggleWaker")); } catch (_) { /* kaggle opzionale */ }

const DEFAULT_PORT = 8790;

class MobileServer {
    /**
     * @param {object} opts
     *   rootDir     dove sta il .env (default: cartella padre di src/)
     *   storageDir  cartella scrivibile (uso/catalogo cloud)
     *   orchestrator (opzionale) LocalOrchestrator già esistente da riusare
     *   host, port, token, workspaceRoot
     */
    constructor(opts = {}) {
        this.rootDir = opts.rootDir || path.join(__dirname, "..");
        this.storageDir = opts.storageDir || this.rootDir;
        this.logger = opts.logger || console;
        this.orchestrator = opts.orchestrator ||
            new LocalOrchestrator(this.logger, { rootDir: this.rootDir, storageDir: this.storageDir });
        const env = this._loadEnv();
        this.host = opts.host || env.MOBILE_HOST || "0.0.0.0";
        this.port = parseInt(opts.port || env.MOBILE_PORT || DEFAULT_PORT, 10);
        this.token = opts.token || env.MOBILE_TOKEN || crypto.randomBytes(9).toString("base64url");
        this.workspaceRoot = opts.workspaceRoot || env.MOBILE_WORKSPACE || this.rootDir;
        this.clients = new Set();  // risposte SSE aperte (telefono + VS Code)
        this.server = null;
        this.busy = false;         // un turno per volta (utente singolo)
        this.tor = TorBrowser ? new TorBrowser(this.logger) : null;  // lettore Tor (opzionale)
        this._startedAt = Date.now();   // uptime del server (gestione lato server)

        // ★ 2026-07-27 — LOGGER SU FILE: ogni riga di log finisce anche su disco
        // (antigravity-server.log in storageDir) così /server/logs può mostrare cosa
        // ha fatto il server anche senza tenera aperta la console. Nessun segreto:
        // gli errori client (CLIENT-ERROR) sono già loggati altrove; qui solo runtime.
        this._logFile = path.join(this.storageDir, "antigravity-server.log");
        this._components = {
            discovery: false,
            fileWatcher: false,
            bugHunter: false
        };
        this._fileWatcherInstance = null;
        this._bugHunterInstance = null;
        const _origLog = this.logger.log ? this.logger.log.bind(this.logger) : (...a) => console.log(...a);
        const _self = this;
        this.logger.log = function (...args) {
            try { fs.appendFileSync(_self._logFile, "[" + new Date().toISOString() + "] " + args.map(a => typeof a === "string" ? a : JSON.stringify(a)).join(" ") + "\n"); } catch (_) {}
            return _origLog(...args);
        };

        // CONVERSAZIONE CONDIVISA: unica fonte di verità. Telefono e VS Code leggono
        // e scrivono QUESTA, così vedono la STESSA chat. Persistita su disco.
        // CONVERSAZIONI MULTIPLE (stile Claude): elenco di chat salvate, una attiva.
        // `this.conversation` punta SEMPRE ai messaggi della chat attiva, così il
        // resto del codice (history/send) resta invariato. Tutto condiviso fra i device.
        this.convsFile = path.join(this.storageDir, "mobile-conversations.json");
        this._loadConversations();
        this._streamAcc = "";   // accumulo del testo assistant del turno corrente

        // Ponte: quello che l'orchestratore crede una "webview". Oltre a inoltrare
        // ai client, CATTURA la risposta dell'assistente per salvarla nella conversazione.
        this.webview = { postMessage: (msg) => this._onEnginePost(msg) };
    }

    _newId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

    _loadConversations() {
        this.convs = [];       // [{id, title, messages:[], updatedAt}]
        this.activeId = null;
        try {
            const data = JSON.parse(fs.readFileSync(this.convsFile, "utf8"));
            if (data && Array.isArray(data.convs)) { this.convs = data.convs; this.activeId = data.activeId; }
        } catch (_) {
            // Migra la vecchia singola conversazione, se presente.
            try {
                const old = JSON.parse(fs.readFileSync(path.join(this.storageDir, "mobile-conversation.json"), "utf8"));
                if (Array.isArray(old) && old.length) this.convs = [{ id: this._newId(), title: this._titleOf(old), messages: old.slice(-300), updatedAt: Date.now() }];
            } catch (_) {}
        }
        if (!this.convs.length) this.convs = [{ id: this._newId(), title: "Nuova chat", messages: [], updatedAt: Date.now() }];
        if (!this.activeId || !this.convs.some(c => c.id === this.activeId)) this.activeId = this.convs[0].id;
        this.conversation = this._active().messages;
    }

    _active() { return this.convs.find(c => c.id === this.activeId) || this.convs[0]; }
    /** Messaggi VISIBILI della chat attiva: quelli dopo l'ultimo "pulisci schermo".
     *  La memoria (this.conversation) resta intera; qui filtriamo solo la vista. */
    _visibleMessages(c) { const a = c || this._active(); const i = a.clearedIndex || 0; return a.messages.slice(i); }

    /**
     * ★ 2026-08-06 — CRONOLOGIA ALLEGGERITA **SOLO PER LA VISTA**.
     *
     * Misurato oggi su questa chat: 194 messaggi, 359.513 caratteri (~351 KB), di cui
     * DUE messaggi da 101.814 caratteri l'uno. Il client li riceve tutti insieme
     * all'apertura del canale e `renderHistory` li costruisce in un ciclo SINCRONO,
     * con parsing markdown a regex su stringhe da 100 KB. Su iPhone il thread
     * principale resta inchiodato: la pagina si vede (lo scheletro è già disegnato)
     * ma non risponde più a niente, e poi Safari uccide la scheda. Nel log si vede
     * come un silenzio totale dopo `canaleAperto` — nessun errore, perché quando il
     * thread muore non resta nessuno che possa segnalarlo.
     *
     * ATTENZIONE: questo tocca SOLO cosa viene DISEGNATO. La memoria della
     * conversazione (`a.messages`) resta intatta: il contesto dell'agente, /history
     * e l'esportazione continuano a vedere tutto.
     *
     * L'ULTIMO messaggio utente non viene mai troncato: `regenerate()` nel client
     * rispedisce `lastUser` preso da qui, e un prompt tagliato sarebbe una corruzione
     * silenziosa (rigenereresti una domanda diversa da quella che avevi fatto).
     */
    _historyForView(c) {
        const MAX_MSG = 40;        // quanti messaggi disegnare
        const MAX_CHARS = 6000;    // tetto per singolo messaggio disegnato
        const tutti = this._visibleMessages(c);
        const tagliati = Math.max(0, tutti.length - MAX_MSG);
        const ultimi = tagliati ? tutti.slice(-MAX_MSG) : tutti.slice();

        // indice dell'ultimo messaggio utente: intoccabile (lo usa "rigenera")
        let ultimoUtente = -1;
        for (let k = ultimi.length - 1; k >= 0; k--) { if (ultimi[k] && ultimi[k].role === "user") { ultimoUtente = k; break; } }

        const out = ultimi.map((m, k) => {
            const testo = String((m && m.content) || "");
            if (k === ultimoUtente || testo.length <= MAX_CHARS) return m;
            return Object.assign({}, m, {
                content: testo.slice(0, MAX_CHARS) +
                    "\n\n*[… messaggio lungo: mostrati i primi " + MAX_CHARS.toLocaleString("it-IT") +
                    " caratteri su " + testo.length.toLocaleString("it-IT") +
                    ". Il testo completo è intatto nella memoria della chat.]*"
            });
        });

        if (tagliati) out.unshift({
            role: "assistant",
            content: "*[Cronologia lunga: disegnati gli ultimi " + MAX_MSG + " messaggi su " +
                     tutti.length + ". I " + tagliati + " precedenti restano in memoria e l'agente li vede.]*"
        });
        return out;
    }
    _titleOf(msgs) {
        const u = (msgs || []).find(m => m.role === "user");
        const t = (u && u.content ? u.content : "Nuova chat").replace(/\s+/g, " ").trim();
        return t.length > 44 ? t.slice(0, 44) + "…" : t;
    }
    _saveConversations() {
        try {
            // ordina per recente, limita a 50 chat, 300 messaggi ciascuna
            this.convs.sort((a, b) => b.updatedAt - a.updatedAt);
            this.convs = this.convs.slice(0, 50);
            for (const c of this.convs) if (c.messages.length > 300) {
                const removed = c.messages.length - 300;
                c.messages = c.messages.slice(-300);
                if (c.clearedIndex) c.clearedIndex = Math.max(0, c.clearedIndex - removed);
            }
            fs.writeFileSync(this.convsFile, JSON.stringify({ activeId: this.activeId, convs: this.convs }));
        } catch (_) {}
    }
    /** Elenco leggero per la UI. */
    _convList() { return this.convs.slice().sort((a, b) => b.updatedAt - a.updatedAt).map(c => ({ id: c.id, title: c.title || "Nuova chat", active: c.id === this.activeId })); }
    _broadcastList() { this._broadcast({ type: "conversations", list: this._convList() }); }

    _onEnginePost(msg) {
        if (msg.type === "streamToken") this._streamAcc += (msg.value || "");
        else if (msg.type === "streamStart") this._streamAcc = "";
        else if (msg.type === "streamEnd") {
            const text = (msg.value && msg.value.length >= this._streamAcc.length) ? msg.value : this._streamAcc;
            if (text) this._appendMessage({ role: "assistant", content: text, model: msg.model });
            this._streamAcc = "";
        } else if (msg.type === "addResponse") {
            if (msg.value) this._appendMessage({ role: "assistant", content: msg.value });
        }
        this._broadcast(msg);
    }

    _appendMessage(m) {
        const active = this._active();
        active.messages.push(m);
        active.updatedAt = Date.now();
        const hadTitle = active.title && active.title !== "Nuova chat";
        if (m.role === "user" && !hadTitle) { active.title = this._titleOf(active.messages); this._broadcastList(); }
        this.conversation = active.messages;
        this._saveConversations();
    }

    // Crea una nuova chat vuota e la rende attiva (broadcast a tutti i device).
    _newChat() {
        const c = { id: this._newId(), title: "Nuova chat", messages: [], updatedAt: Date.now() };
        this.convs.unshift(c);
        this.activeId = c.id;
        this.conversation = c.messages;
        this._saveConversations();
        this._broadcast({ type: "history", messages: [] });
        this._broadcastList();
    }
    // Passa a una chat esistente.
    _switchChat(id) {
        const c = this.convs.find(x => x.id === id);
        if (!c) return;
        this.activeId = id;
        this.conversation = c.messages;
        this._saveConversations();
        this._broadcast({ type: "history", messages: this._historyForView(c) });
        this._broadcastList();
    }
    // Elimina una chat; se era attiva, passa alla più recente (o ne crea una vuota).
    _deleteChat(id) {
        this.convs = this.convs.filter(c => c.id !== id);
        if (!this.convs.length) return this._newChat();
        if (this.activeId === id) { this.activeId = this.convs[0].id; this.conversation = this._active().messages; this._broadcast({ type: "history", messages: this._historyForView() }); }
        this._saveConversations();
        this._broadcastList();
    }

    _loadEnv() {
        const out = {};
        try {
            const txt = fs.readFileSync(path.join(this.rootDir, ".env"), "utf8");
            for (const line of txt.split(/\r?\n/)) {
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

    // ---- SSE verso il telefono --------------------------------------------

    _broadcast(msg) {
        const data = "data: " + JSON.stringify(msg) + "\n\n";
        for (const res of this.clients) {
            try { res.write(data); } catch (_) { this.clients.delete(res); }
        }
    }

    // ---- Avvio / stop ------------------------------------------------------

    // ★ 2026-07-31 — RETE ANTI-CRASH. Prima non c'era NESSUN gestore globale: una
    // Promise di background rifiutata (discovery cloud, kaggle, tor…) o un errore di
    // socket bastavano a uccidere il processo. Sul telefono la connessione SSE cadeva
    // e la pagina si "riavviava"; peggio, il motivo restava invisibile. Ora:
    //   • unhandledRejection → si logga e si TIENE VIVO il server (background non critico);
    //   • errori di rete benigni (telefono che chiude) → ignorati, sono normali;
    //   • errore davvero grave → si logga la causa e si esce pulito, così il supervisor
    //     (VBS) riavvia — ma stavolta il perché è scritto nel log.
    _installCrashGuards() {
        if (global.__antigravityGuards) return;   // una sola volta per processo
        global.__antigravityGuards = true;
        const log = (...a) => { try { this.logger.log("[CRASH-GUARD] " + a.join(" ")); } catch (_) { try { console.error("[CRASH-GUARD]", ...a); } catch (_) {} } };
        const BENIGN = /EPIPE|ECONNRESET|ECANCELED|ERR_STREAM_WRITE_AFTER_END|write after end/i;
        process.on("unhandledRejection", (reason) => {
            log("unhandledRejection (ignorata, server vivo):", reason && reason.stack ? reason.stack : String(reason));
        });
        process.on("uncaughtException", (err) => {
            const msg = err && err.stack ? err.stack : String(err);
            if (BENIGN.test(msg)) { log("errore di rete non fatale (ignorato):", msg); return; }
            log("uncaughtException FATALE — esco per riavvio pulito:", msg);   // append sincrono su file: flush garantito prima di exit
            process.exit(1);
        });
    }

    async start() {
        this._installCrashGuards();   // ★ installa la rete anti-crash prima di tutto
        // ★ 2026-08-04 — DISCOVERY LAZY: non blocca l'avvio.
        // LeDiscovery verranno avviate alla prima richiesta /models o quando
        // l'utente interagisce, così il server risponde subito e la pagina non
        // resta nera/bloccata su PC e telefono.
        this._discoveryStarted = false;

        this.server = http.createServer((req, res) => this._route(req, res));
        await new Promise((resolve, reject) => {
            this.server.once("error", reject);
            this.server.listen(this.port, this.host, resolve);
        });
        const urls = this._urls();
        this.logger.log && this.logger.log("[MobileServer] in ascolto su " + this.host + ":" + this.port);
        this.logger.log && this.logger.log("[MobileServer] TOKEN = " + this.token);
        for (const u of urls) this.logger.log && this.logger.log("[MobileServer] apri sul telefono: " + u);

        // ★ 2026-08-31 — COLLAUDO AUTOMATICO. Non blocca l'avvio: parte subito
        // dopo che la porta e' aperta e scrive l'esito nel log. Se qualcosa non
        // passa, l'esito resta qui e viene DETTO in chat al primo client che si
        // collega (vedi _sse). Serve contro l'unico guasto che non da' mai un
        // errore: un pezzo di lavoro che si scollega e l'app che continua a
        // rispondere, solo peggio. Vedi src/collaudo.js per la storia.
        this._collaudo = null;
        setTimeout(async () => {
            try {
                const c = require("./collaudo");
                const res = await c.esegui({ engine: this.orchestrator && this.orchestrator.engine });
                this._collaudo = res;
                const riga = c.riassunto(res);
                this.logger.log && this.logger.log("[collaudo] " + riga.replace(/\n/g, " | "));
                if (!res.ok) this._broadcast({ type: "status", value: riga });
            } catch (e) {
                this.logger.log && this.logger.log("[collaudo] non eseguito: " + e.message);
            }
        }, 1500);

        // ★ 2026-07-30 — Lo snapshot "sano" NON si fa più appena la porta si apre.
        // "Il file compila" e "il server si avvia" non significano "funziona": un file
        // guasto ma sintatticamente valido diventava subito il nuovo riferimento di
        // backup, cancellando quello buono. Ora servono DUE prove reali:
        //   1) il server è ancora in piedi dopo SNAPSHOT_DELAY_MS (se è rotto, il
        //      riavvio in loop del VBS lo abbatte prima e lo snapshot non avviene);
        //   2) ha servito almeno una richiesta andata a buon fine.
        // Finché le prove mancano, il backup precedente resta intatto.
        const SNAPSHOT_DELAY_MS = 3 * 60 * 1000;
        const t = setTimeout(() => {
            if (!this.server || !this.server.listening) return;
            if (!this._servedOk) {
                this.logger.log && this.logger.log("[selfHeal] snapshot rimandato: nessuna richiesta servita, non posso dire che funziona.");
                return;
            }
            try {
                const { snapshotHealthy, CRITICAL_FILES } = require("./selfHeal");
                snapshotHealthy({ srcDir: __dirname, files: CRITICAL_FILES, logger: this.logger });
            } catch (_) { /* non critico */ }
        }, SNAPSHOT_DELAY_MS);
        // Non trattenere il processo in vita solo per lo snapshot.
        if (t.unref) t.unref();
        this._snapshotTimer = t;

        return { port: this.port, host: this.host, token: this.token, urls };
    }

    stop() {
        for (const res of this.clients) { try { res.end(); } catch (_) {} }
        this.clients.clear();
        // Uno stop volontario non è una prova di buona salute: annulla lo snapshot.
        if (this._snapshotTimer) { try { clearTimeout(this._snapshotTimer); } catch (_) {} this._snapshotTimer = null; }
        if (this.server) { try { this.server.close(); } catch (_) {} this.server = null; }
    }

    /** URL utili (localhost + eventuale IP Tailscale 100.x rilevato). */
    _urls() {
        const out = [`http://localhost:${this.port}/?t=${this.token}`];
        try {
            const os = require("os");
            for (const list of Object.values(os.networkInterfaces())) {
                for (const ni of list || []) {
                    if (ni.family === "IPv4" && !ni.internal && /^100\./.test(ni.address)) {
                        out.push(`http://${ni.address}:${this.port}/?t=${this.token}`);
                    }
                }
            }
        } catch (_) {}
        return out;
    }

    // ---- Routing -----------------------------------------------------------

    // ★ 2026-08-31 — IL TOKEN NON DEVE PIU' VIVERE NELL'INDIRIZZO.
    // Finche' viaggia come "?t=…" finisce nella cronologia del browser (e da li'
    // in iCloud), nei log, e in qualunque schermata condivisa. Ora ci sono tre
    // strade, in ordine: il cookie (la normale, invisibile), l'intestazione
    // x-token (per gli script), e la query — che RESTA valida perche' e' quella
    // dei collegamenti gia' salvati sul telefono. Alla prima apertura con "?t="
    // il server posa il cookie e la pagina cancella il token dalla barra degli
    // indirizzi: da li' in avanti l'indirizzo e' pulito e continua a funzionare.
    _leggiCookie(req, nome) {
        const raw = req.headers.cookie || "";
        for (const pezzo of raw.split(";")) {
            const i = pezzo.indexOf("=");
            if (i > 0 && pezzo.slice(0, i).trim() === nome) return decodeURIComponent(pezzo.slice(i + 1).trim());
        }
        return null;
    }

    _authOk(req, url) {
        const t = url.searchParams.get("t") || req.headers["x-token"] || this._leggiCookie(req, "ag_t");
        return t && t === this.token;
    }

    /** Intestazione che posa il cookie del token (un anno, non leggibile da JS). */
    _cookieToken() {
        return "ag_t=" + encodeURIComponent(this.token) + "; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax";
    }

    /** Serve un PNG generato da ComfyUI (solo dalla cartella output, per basename). */
    _serveImage(name, res) {
        try {
            const { COMFY_OUTPUT } = require("./comfyClient");
            const base = path.basename(String(name)); // taglia qualsiasi "../"
            const fp = path.join(COMFY_OUTPUT, base);
            if (!fp.startsWith(COMFY_OUTPUT) || !fs.existsSync(fp)) { res.writeHead(404).end(); return; }
            const ext = path.extname(fp).toLowerCase();
            const ct = ext === ".png" ? "image/png" : ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : ext === ".webp" ? "image/webp" : "application/octet-stream";
            res.writeHead(200, { "Content-Type": ct, "Cache-Control": "public, max-age=86400" });
            fs.createReadStream(fp).pipe(res);
        } catch (_) { res.writeHead(500).end(); }
    }

    /** La pagina web (stile Claude), letta da src/mobile-page.html. */
    _page() {
        try {
            const fp = path.join(__dirname, "mobile-page.html");
            let html = fs.readFileSync(fp, "utf8");
            // ★ VERSIONE VISIBILE (richiesta utente): inietto la data/ora del file
            // della pagina, così sullo schermo si VEDE quando è stata caricata una
            // versione nuova. Cambia da sola a ogni modifica del file: niente da
            // aggiornare a mano.
            let ver = "?";
            try {
                const t = fs.statSync(fp).mtime;
                const p2 = n => String(n).padStart(2, "0");
                ver = `${p2(t.getDate())}/${p2(t.getMonth() + 1)} ${p2(t.getHours())}:${p2(t.getMinutes())}`;
            } catch (_) {}
            return html.replace(/\{\{VER\}\}/g, ver);
        }
        catch (e) { return "<!doctype html><meta charset=utf-8><body style='font-family:sans-serif;padding:24px'>Pagina non trovata: " + e.message + "</body>"; }
    }

    async _route(req, res) {
        let url;
        try { url = new URL(req.url, "http://x"); } catch (_) { res.writeHead(400).end(); return; }
        const p = url.pathname;
        // Prova che il server non solo è partito, ma sta davvero servendo: la usa il
        // gate dello snapshot selfHeal (vedi start()). Una risposta completata senza
        // errore di codice basta come segnale di "vivo e funzionante".
        if (!this._servedOk) res.once("finish", () => { if (res.statusCode < 500) this._servedOk = true; });

        if (p === "/" || p === "/index.html") {
            // La pagina è pubblica; le API richiedono il token. Il token viaggia
            // nella query (?t=) e la pagina lo propaga a fetch/EventSource.
            // no-store: la pagina è riletta dal disco a ogni richiesta, così il
            // telefono non resta con una versione vecchia dopo una modifica.
            // ★ 2026-07-19 — anti-cache RINFORZATO: no-store da solo non bastava con
            // Safari/webview testardi. Aggiunti no-cache/must-revalidate + Pragma +
            // Expires (per i client vecchi) → la pagina nuova arriva SEMPRE.
            const intestazioni = {
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            };
            // Se sei arrivato col token nell'indirizzo (il collegamento salvato sul
            // telefono), posiamo il cookie: le aperture successive funzionano con un
            // indirizzo pulito. NON si fa una redirezione: se il cookie non
            // attecchisse (Safari in navigazione privata) resteresti chiuso fuori.
            // Cosi' invece il peggio che puo' succedere e' restare come prima.
            if (url.searchParams.get("t") === this.token) intestazioni["Set-Cookie"] = this._cookieToken();
            res.writeHead(200, intestazioni);
            res.end(this._page());
            return;
        }

        // Immagini generate da ComfyUI: servite dalla cartella output, solo per
        // basename (niente path traversal). Pubbliche come la pagina.
        if (p.startsWith("/img/")) return this._serveImage(decodeURIComponent(p.slice(5)), res);

        // ★ 2026-08-06 — PROVA DI VITA, pubblica e cortissima da digitare.
        // Serve a separare due guasti che l'utente non puo' distinguere dal telefono:
        // "la rete non arriva al PC" e "la rete arriva ma la pagina non si disegna".
        // Nessun token (il token e' lungo e sbagliarlo a mano e' facilissimo), nessun
        // JavaScript, nessuna dipendenza: se sul telefono compare la scritta, il
        // tragitto telefono→server FUNZIONA e il guasto e' nella pagina.
        // Logga chi ha chiamato, cosi' lo vedo anche se il telefono non mostra nulla.
        if (p === "/vivo") {
            this.logger.log && this.logger.log(`[VIVO] richiesta da ${req.socket.remoteAddress} — UA: ${req.headers["user-agent"] || "?"}`);
            res.writeHead(200, {
                "Content-Type": "text/plain; charset=utf-8",
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
            });
            res.end("SERVER VIVO — " + new Date().toLocaleTimeString("it-IT") + "\nIl telefono raggiunge il PC.\n");
            return;
        }

        if (!this._authOk(req, url)) { res.writeHead(401, { "Content-Type": "text/plain" }).end("token mancante o errato"); return; }

        // DIAGNOSTICA CLIENT: la pagina manda qui i propri errori JavaScript.
        // Serve perche' gli errori dentro Safari sull'iPhone non sono ispezionabili
        // dal PC: senza, sul "si è verificato ripetutamente un errore" si puo' solo
        // tirare a indovinare. Finiscono nel log del server, dove li leggo.
        if (p === "/clientError") {
            let body = "";
            req.on("data", d => { body += d; if (body.length > 20000) req.destroy(); });
            req.on("end", () => {
                try {
                    const e = JSON.parse(body || "{}");
                    this.logger.log("[CLIENT-ERROR] " + JSON.stringify(e).slice(0, 2000));
                } catch (_) { this.logger.log("[CLIENT-ERROR] illeggibile: " + body.slice(0, 500)); }
                this._json(res, { ok: true });
            });
            return;
        }
        // ---- LETTORE TOR ------------------------------------------------------
        // /tor/page → scarica una pagina via Tor, la ripulisce, la restituisce.
        // /tor/raw  → riproxa una risorsa (immagine) via Tor come bytes grezzi.
        if (p === "/tor/page") return this._torPage(req, res, url);
        if (p === "/tor/raw")  return this._torRaw(req, res, url);
        if (p === "/tor/status") {
            const up = this.tor ? this.tor.isUp() : false;
            return this._json(res, { available: !!(this.tor && this.tor.available()), up });
        }

        if (p === "/events") return this._sse(req, res);
        if (p === "/history") return this._json(res, { messages: this._visibleMessages() });
        if (p === "/conversations") return this._json(res, { list: this._convList() });
        if (p === "/models") return this._models(req, res);
        // ★ 2026-09-01 — PONTE COL TELEFONO: elenca e riprende le conversazioni di
        // Claude Code salvate sul PC, così dal letto continui il filo lasciato qui.
        if (p === "/claude/sessions") return this._claudeSessions(res);
        if (p === "/claude/resume")   return this._claudeResume(req, res);
        if (p === "/send")   return this._send(req, res);
        if (p === "/stop")   { this.orchestrator.stop(); this.busy = false; this._queue = []; this._broadcast({ type: "status", value: "⏹️ Fermato (coda svuotata) — puoi scrivere un nuovo messaggio." }); return this._json(res, { ok: true }); }
        if (p === "/approve") return this._approve(req, res);
        if (p === "/policy")  return this._policy(req, res);
        if (p === "/clear")   return this._clear(res);
        if (p === "/clearView") return this._clearView(res);
        if (p === "/newChat") { this._newChat(); return this._json(res, { ok: true }); }
        if (p === "/switch")  return this._switchReq(req, res);
        if (p === "/delete")  return this._deleteReq(req, res);
        if (p === "/keys")     return this._keys(req, res);
        if (p === "/keys/check") return this._checkKey(req, res);
        if (p === "/detectKey") return this._detectKey(req, res);
        if (p === "/addKey")   return this._addKey(req, res);
        if (p === "/bugHunter") return this._bugHunter(req, res);
        if (p === "/bugHunter/scan") return this._bugHunterScan(req, res);
        if (p === "/bugHunter/queue") return this._bugHunterQueue(req, res);
        if (p === "/bugHunter/delegate") return this._bugHunterDelegate(req, res);
        if (p === "/bugHunter/apply") return this._bugHunterApply(req, res);
        if (p === "/bugHunter/close") return this._bugHunterClose(req, res);
        if (p === "/agents/run") return this._agentsRun(req, res);
        if (p === "/gpu/pull") return this._gpuPull(req, res);
        if (p === "/gpu/status") return this._gpuStatus(req, res);
        if (p === "/plan") return this._plan(req, res);
        if (p === "/models/compare") return this._modelsCompare(req, res);
        if (p === "/ghidra/decompile") return this._ghidra(req, res, "decompile");
        if (p === "/ghidra/diff") return this._ghidra(req, res, "diff");
        if (p === "/ghidra/secrets") return this._ghidra(req, res, "secrets");
        if (p === "/ghidra/scripts") return this._ghidra(req, res, "scripts");
        if (p === "/gpu/failover") return this._gpuFailover(req, res);
        if (p === "/gpu/schedule") return this._gpuSchedule(req, res);
        if (p === "/gpu/preload") return this._gpuPreload(req, res);
        if (p === "/gpu/quota") return this._gpuQuota(req, res);
        if (p === "/rollback") return this._rollback(req, res);
        if (p === "/simulate-disaster") return this._simulateDisaster(req, res);
        if (p === "/alerts") return this._alerts(req, res);
        if (p === "/platform/guide") return this._platformGuide(req, res);
        if (p === "/freeProviders") return this._freeProviders(req, res);
        if (p === "/freeProviders/hunt") return this._huntProviders(req, res);
        if (p === "/gpuPlatforms") return this._gpuPlatforms(req, res);
        if (p === "/translate") return this._translate(req, res);
        if (p === "/music/search") return this._musicSearch(req, res);
        if (p === "/music/lyrics") return this._musicLyrics(req, res);
        if (p === "/music/spotify") return this._musicSpotifyEmbed(req, res);
        if (p === "/music/youtube") return this._musicYouTube(req, res);
        if (p === "/upload")   return this._upload(req, res);

        // ---- Comandi GPU Kaggle (4 pulsanti UI) ----
        if (p === "/kaggle/up") {
            if (!ensureUpSize) return this._json(res, { error: "kaggleWaker non disponibile" }, 503);
            const size = (url.searchParams.get("size") === "30") ? 30 : 14;
            ensureUpSize(size, { onStatus: (t) => this._broadcast({ type: "status", value: t }), logger: console })
                .then(ok => this._json(res, { ok: !!ok, size }))
                .catch(e => this._json(res, { ok: false, error: e.message }, 500));
            return;
        }
        if (p === "/kaggle/status") {
            if (!status) return this._json(res, { up: false });
            return status().then(s => this._json(res, s)).catch(() => this._json(res, { up: false }));
        }
        if (p === "/kaggle/shutdown") {
            if (!shutdown) return this._json(res, { ok: false, message: "kaggleWaker non disponibile" }, 503);
            return shutdown().then(r => this._json(res, r)).catch(e => this._json(res, { ok: false, message: e.message }, 500));
        }
        if (p === "/kaggle/quota") {
            if (!quota) return this._json(res, { error: "kaggleWaker non disponibile" }, 503);
            return quota().then(q => this._json(res, q)).catch(e => this._json(res, { error: e.message }, 500));
        }

        // ---- CANTIERE: il lavoro che stai costruendo dal telefono, protetto ----
        // ★ 2026-07-30 — Vedi cantiere.js. /cantiere/ripresa è quella che conta
        // quando l'app si interrompe: restituisce il mandato per ripartire da dove
        // eri, senza doverlo raccontare di nuovo.
        if (p === "/cantiere")          return this._cantiere(req, res);
        if (p === "/cantiere/apri")     return this._cantiereApri(req, res);
        if (p === "/cantiere/passo")    return this._cantierePasso(req, res);
        if (p === "/cantiere/proteggi") return this._cantiereProteggi(req, res);
        if (p === "/cantiere/ripresa")  return this._cantiereRipresa(req, res);
        if (p === "/cantiere/chiudi")   return this._cantiereChiudi(req, res);
        if (p === "/cantiere/diario")   return this._cantiereDiario(req, res);

        // ---- PIATTAFORME GPU: wizard, accensione, modello consigliato, mirror ----
        if (p === "/piattaforme")          return this._piattaformeStato(req, res);
        if (p === "/piattaforme/scelte")   return this._piattaformeScelte(req, res);
        if (p === "/piattaforme/domande")  return this._piattaformeDomande(req, res);
        if (p === "/piattaforme/salva")    return this._piattaformeSalva(req, res);
        if (p === "/piattaforme/accendi")  return this._piattaformeAccendi(req, res);
        if (p === "/piattaforme/spegni")   return this._piattaformeSpegni(req, res);
        if (p === "/piattaforme/costi")    return this._piattaformeCosti(req, res);
        if (p === "/piattaforme/genera")   return this._piattaformeGenera(req, res);
        if (p === "/modelli/consiglia")    return this._modelliConsiglia(req, res);
        if (p === "/modelli/uncensored")   return this._modelliUncensored(req, res);
        if (p === "/mirror")               return this._mirrorStato(req, res);
        if (p === "/mirror/crea")          return this._mirrorCrea(req, res);

        // Stato generale (dashboard): cosa è vivo e pronto. NESSUN segreto.
        if (p === "/status") {
            return this._statusDashboard(req, res);
        }

        // ---- GESTIONE SERVER (lato server) ----
        if (p === "/server/status")  return this._serverStatus(req, res);
        if (p === "/server/health")  return this._serverHealth(req, res);
        if (p === "/server/logs")    return this._serverLogs(req, res);
        if (p === "/server/restart") return this._serverRestart(req, res);
        if (p === "/server/engines") return this._serverEngines(req, res);
        if (p === "/system/toggle")  return this._systemToggle(req, res);

        res.writeHead(404).end();
    }

    // ================= CANTIERE (il lavoro dal telefono, protetto) =============
    // ★ 2026-07-30 — Vedi cantiere.js per il perché. Qui solo le porte.

    async _cantiere(req, res) {
        try { return this._json(res, { ok: true, cantiere: require("./cantiere").stato() }); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** Apre il cantiere: da qui in poi quei file non li tocca nessun automatismo. */
    async _cantiereApri(req, res) {
        try {
            const b = await this._body(req);
            if (!b.titolo) return this._json(res, { ok: false, error: "manca 'titolo': serve per ritrovare il lavoro quando riprendi" }, 400);
            const r = require("./cantiere").apri({
                titolo: b.titolo, obiettivo: b.obiettivo, prossimo: b.prossimo,
                files: b.files || [], origine: b.origine || "mobile", pinPiattaforma: b.pinPiattaforma
            });
            this._broadcast({ type: "status", value: "🔒 Cantiere aperto: «" + r.cantiere.titolo + "» — " + r.cantiere.files.length + " file protetti da selfHeal, rollback, Hermes e sync." });
            return this._json(res, r);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** Segna un passo fatto + qual è il prossimo: è quello che rende possibile riprendere. */
    async _cantierePasso(req, res) {
        try {
            const b = await this._body(req);
            if (!b.testo) return this._json(res, { ok: false, error: "manca 'testo' (cosa hai appena fatto)" }, 400);
            const r = require("./cantiere").passo(b.testo, { prossimo: b.prossimo });
            return this._json(res, r, r.ok ? 200 : 409);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    async _cantiereProteggi(req, res) {
        try {
            const b = await this._body(req);
            const r = require("./cantiere").proteggi(b.files || b.file || []);
            return this._json(res, r, r.ok ? 200 : 409);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /**
     * «Riprendi da dove ti sei interrotto» — senza doverlo raccontare di nuovo.
     * Restituisce il mandato pronto; con ?invia=1 lo manda direttamente al
     * modello come messaggio, così dal telefono è un pulsante solo.
     */
    async _cantiereRipresa(req, res) {
        try {
            const url = new URL(req.url, "http://x");
            const r = require("./cantiere").ripresa();
            if (!r.ok) return this._json(res, r, 404);
            if (url.searchParams.get("invia") === "1") {
                // Stessa strada di /send: in coda, eco immediato, e parte appena
                // il turno in corso finisce. Dal telefono è un pulsante solo.
                this._queue = this._queue || [];
                this._queue.push({ prompt: r.testo });
                this._broadcast({ type: "userMessage", value: r.testo });
                if (!this.busy) this._drainQueue();
                return this._json(res, Object.assign({ inviato: true }, r));
            }
            return this._json(res, r);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    async _cantiereChiudi(req, res) {
        try {
            const b = await this._body(req);
            const r = require("./cantiere").chiudi(b.esito || "chiuso dal telefono");
            if (r.ok) this._broadcast({ type: "status", value: "🔓 Cantiere «" + r.cantiere.titolo + "» chiuso: le manutenzioni automatiche riprendono." });
            return this._json(res, r, r.ok ? 200 : 409);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    async _cantiereDiario(req, res) {
        try { return this._json(res, { ok: true, voci: require("./cantiere").diario(null, 200), storico: require("./cantiere").storico(10) }); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    // ================= PIATTAFORME GPU ========================================

    async _piattaformeStato(req, res) {
        try { return this._json(res, Object.assign({ ok: true }, await require("./platforms").stato())); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _piattaformeScelte(req, res) {
        try { return this._json(res, Object.assign({ ok: true }, await require("./platformWizard").scelte())); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _piattaformeDomande(req, res) {
        try {
            const id = new URL(req.url, "http://x").searchParams.get("id");
            const r = require("./platformWizard").domande(id);
            return this._json(res, r, r.ok ? 200 : 404);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _piattaformeSalva(req, res) {
        try {
            const b = await this._body(req);
            if (!b.id) return this._json(res, { ok: false, error: "manca id piattaforma" }, 400);
            return this._json(res, await require("./platformWizard").salva(b.id, b.valori || {}));
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** Accende una piattaforma qualsiasi: stessi pulsanti di Kaggle, per tutte. */
    async _piattaformeAccendi(req, res) {
        try {
            const b = await this._body(req);
            const url = new URL(req.url, "http://x");
            const id = b.id || url.searchParams.get("id");
            if (!id) return this._json(res, { ok: false, error: "manca id piattaforma" }, 400);
            const r = await require("./platforms").accendi(id, {
                gpu: b.gpu || url.searchParams.get("gpu") || undefined,
                contesto: b.contesto ? Number(b.contesto) : undefined,
                size: b.size,
                onStato: (t) => this._broadcast({ type: "status", value: "[" + id + "] " + t })
            });
            if (r.messaggio) this._broadcast({ type: "status", value: r.messaggio });
            return this._json(res, Object.assign({ id }, r));
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _piattaformeSpegni(req, res) {
        try {
            const url = new URL(req.url, "http://x");
            const b = await this._body(req);
            const id = b.id || url.searchParams.get("id");
            if (!id) return this._json(res, { ok: false, error: "manca id piattaforma" }, 400);
            const r = await require("./platforms").spegni(id);
            if (r.messaggio) this._broadcast({ type: "status", value: r.messaggio });
            return this._json(res, Object.assign({ id }, r));
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** «È davvero gratis?»: letto dall'API dove esiste, dichiarato altrove — e lo dice. */
    async _piattaformeCosti(req, res) {
        try {
            const id = new URL(req.url, "http://x").searchParams.get("id");
            return this._json(res, Object.assign({ ok: true }, await require("./platformWizard").costi(id)));
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** Genera notebook/script di deploy per una piattaforma (senza accenderla). */
    async _piattaformeGenera(req, res) {
        try {
            const b = await this._body(req);
            const path2 = require("path");
            const id = b.id || "kaggle";
            const cartella = b.cartella || path2.join(__dirname, "generati", id);
            const r = require("./notebookTemplate").scrivi(cartella, {
                piattaforma: id, gpu: b.gpu || "T4", contesto: b.contesto || 32768,
                mirror: b.mirror, tunnel: b.tunnel, dominio: b.dominio,
                ngrokToken: b.ngrokToken, shutdownUrl: b.shutdownUrl, uso: b.uso
            });
            return this._json(res, { ok: true, piattaforma: id, modello: r.cfg.tag, scritti: r.scritti, consiglio: r.cfg.consiglio || null });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 400); }
    }
    /** Che modello ci sta su questa GPU: con il conto, non a naso. */
    async _modelliConsiglia(req, res) {
        try {
            const url = new URL(req.url, "http://x");
            const b = await this._body(req);
            const gpu = b.gpu || url.searchParams.get("gpu") || "T4";
            const contesto = Number(b.contesto || url.searchParams.get("contesto") || 32768);
            return this._json(res, require("./modelAdvisor").consiglia({ gpu: isNaN(Number(gpu)) ? gpu : Number(gpu), contesto, uso: b.uso || url.searchParams.get("uso") || "coder" }));
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /**
     * ★ 2026-09-02 — «quale modello senza filtri conviene?», col conto e coi
     * prezzi veri presi dal catalogo live. Diverso da /modelli/consiglia, che
     * risponde all'altra domanda (quale GGUF ci sta nella VRAM di una GPU).
     * ?uso=agente|chat  ?budget=10  ?formato=testo
     */
    async _modelliUncensored(req, res) {
        try {
            const url = new URL(req.url, "http://x");
            const b = await this._body(req).catch(() => ({}));
            const adv = require("./uncensoredAdvisor");
            const r = await adv.consiglia({
                chiave: this.env && this.env.OPENROUTER_API_KEY,
                uso: b.uso || url.searchParams.get("uso") || "agente",
                budget: Number(b.budget || url.searchParams.get("budget") || 10)
            });
            const formato = b.formato || url.searchParams.get("formato");
            if (formato === "testo") {
                res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
                return res.end(adv.testo(r));
            }
            return this._json(res, r);
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _mirrorStato(req, res) {
        try { return this._json(res, Object.assign({ ok: true }, await require("./modelMirror").stato())); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _mirrorCrea(req, res) {
        try {
            const b = await this._body(req);
            return this._json(res, await require("./modelMirror").creaRepo(b.repo));
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** Dashboard stato: cosa è vivo e pronto. NESSUN segreto esposto. */
    async _statusDashboard(req, res) {
        const o = this.orchestrator || {};
        const out = {
            server: true,
            time: new Date().toISOString(),
            engines: {},
            kaggle: null,
            tor: null,
            keys_configured: 0,
            models_local: 0,
            nous: false
        };
        try { out.engines.local = !!(await o.engine.isOnline().catch(() => false)); } catch (_) { out.engines.local = false; }
        try { out.engines.cloud = !!(o.cloudConfigured && o.cloudConfigured()); } catch (_) { out.engines.cloud = false; }
        try {
            const ms = o.engine && o.engine.getModels ? o.engine.getModels() : [];
            out.models_local = Array.isArray(ms) ? ms.length : 0;
        } catch (_) { out.models_local = 0; }
        try { out.nous = !!(o.nous && o.nous.available && o.nous.available()); } catch (_) { out.nous = false; }
        try { out.kaggle = status ? (await status()) : null; } catch (_) { out.kaggle = null; }
        try { out.tor = (this.tor && this.tor.available && this.tor.available()) ? "installed" : (TorBrowser ? "missing" : "n/a"); } catch (_) { out.tor = null; }
        // Chiavi configurate: contiamo i provider con env key, senza esporre i valori.
        try {
            const cloud = o.cloud;
            if (cloud && cloud.listKnownProviders) {
                const provs = cloud.listKnownProviders();
                out.keys_configured = Array.isArray(provs) ? provs.filter(p => p.configured).length : 0;
            }
        } catch (_) {}
        // Pronto/non pronto per ogni provider: vedi _statoProvider.
        try { out.providers = this._statoProvider(out); } catch (_) { out.providers = null; }
        return this._json(res, out);
    }

    _sse(req, res) {
        res.writeHead(200, {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        });
        res.write(": connesso\n\n");
        // Manda SUBITO la conversazione attiva + l'elenco delle chat: il client
        // (telefono o VS Code) ridisegna la STESSA chat e la stessa lista.
        res.write("data: " + JSON.stringify({ type: "history", messages: this._historyForView() }) + "\n\n");
        res.write("data: " + JSON.stringify({ type: "conversations", list: this._convList() }) + "\n\n");
        // Se il collaudo all'avvio ha trovato qualcosa fuori posto, lo dice QUI:
        // al primo sguardo, senza doverlo andare a cercare nel log.
        if (this._collaudo && !this._collaudo.ok) {
            try {
                const riga = require("./collaudo").riassunto(this._collaudo);
                res.write("data: " + JSON.stringify({ type: "status", value: riga }) + "\n\n");
            } catch (_) { }
        }
        this.clients.add(res);
        // ★ 2026-08-06 — IL PING DEVE ESSERE UN DATO, NON UN COMMENTO.
        // ": ping" è un commento SSE: per specifica NON fa scattare onmessage, quindi
        // il client non aggiornava mai `lastBeat` a chat ferma. Il suo watchdog (9 s)
        // dichiarava morto un canale sanissimo e riconnetteva ogni ~11 s; ogni
        // riconnessione rimanda la history, che fa clearThread() e cancella la
        // risposta in corso lasciando #send inchiodato su "■". Era questo il
        // "sul telefono clicco un pulsante e poi non va più niente".
        // Ora è un evento vero (onmessage scatta) e più fitto del timeout del client.
        const ping = setInterval(() => {
            try { res.write("data: " + JSON.stringify({ type: "ping" }) + "\n\n"); } catch (_) {}
        }, 5000);
        req.on("close", () => { clearInterval(ping); this.clients.delete(res); });
    }

    // ---- LETTORE TOR ------------------------------------------------------
    // Scarica una pagina attraverso Tor, la ripulisce e la restituisce come JSON
    // { url, title, html }. L'app la mostra in un pannello-browser.
    async _torPage(req, res, url) {
        if (!this.tor || !this.tor.available()) {
            return this._json(res, { error: "Tor non è installato sul PC." }, 503);
        }
        let target = String(url.searchParams.get("u") || "").trim();
        if (!target) return this._json(res, { error: "URL mancante." }, 400);
        if (!/^https?:\/\//i.test(target)) target = "http://" + target;   // aiuto: aggiunge lo schema
        if (!/^https?:\/\//i.test(target)) return this._json(res, { error: "URL non valido." }, 400);
        try {
            await this.tor.ensureRunning((t) => this._broadcast({ type: "status", value: t }));
            const r = await this.tor.fetch(target, { maxTime: 45 });
            if (!r.ok) return this._json(res, { error: `Pagina non raggiungibile (stato ${r.status}). Il sito .onion potrebbe essere offline.`, url: target }, 200);
            const ct = r.contentType || "";
            if (!/text\/html|text\/plain|application\/xhtml/i.test(ct)) {
                // non è una pagina: rimanda l'utente al proxy raw (es. un PDF/immagine)
                return this._json(res, { url: target, title: target, html: `<p>Contenuto non testuale (${this._esc(ct)}). <a data-tor-url="${this._esc(target)}" href="#">Riprova</a></p>` });
            }
            const html = r.body.toString("utf8");
            const title = (/<title[^>]*>([\s\S]*?)<\/title>/i.exec(html) || [])[1] || target;
            // ★ PRE-ANALISI RISCHIO sull'HTML GREZZO (prima di ripulirlo), così
            //   l'utente è avvisato PRIMA di guardare la pagina.
            const risk = TorBrowser.analyzeRisk(html, target);
            const clean = TorBrowser.sanitize(html, target, this.token);
            // estrai solo il <body> se c'è, per non incollare <head> pesante
            const bodyM = /<body[^>]*>([\s\S]*?)<\/body>/i.exec(clean);
            const out = bodyM ? bodyM[1] : clean;
            return this._json(res, { url: target, title: String(title).trim().slice(0, 200), html: out, risk });
        } catch (e) {
            return this._json(res, { error: "Tor: " + e.message, url: target }, 200);
        }
    }

    // Riproxa una risorsa (immagine) attraverso Tor: il telefono non contatta
    // mai direttamente il server remoto → nessuna fuga dell'IP reale.
    async _torRaw(req, res, url) {
        if (!this.tor || !this.tor.available()) { res.writeHead(503).end(); return; }
        const target = String(url.searchParams.get("u") || "").trim();
        if (!/^https?:\/\//i.test(target)) { res.writeHead(400).end(); return; }
        try {
            await this.tor.ensureRunning(() => {});
            const r = await this.tor.fetch(target, { maxTime: 30, binary: true });
            if (!r.ok) { res.writeHead(502).end(); return; }
            const ct = r.contentType || "application/octet-stream";
            // solo immagini, per sicurezza (niente html/eseguibili serviti come risorsa)
            if (!/^image\//i.test(ct)) { res.writeHead(415).end(); return; }
            res.writeHead(200, { "Content-Type": ct, "Cache-Control": "no-store" });
            res.end(r.body);
        } catch (_) { res.writeHead(500).end(); }
    }

    _esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

    // ---- Chiavi API (aggiunta facilitata) --------------------------------
    // cache stato chiavi (evita 19 check live a ogni apertura pannello)
    _keysCache = { at: 0, data: null };
    // Probe LIVE di una chiave: ritorna { status:'live'|'dead'|'quota', detail }.
    // Riutilizzato da /keys e /keys/check.
    async probeKey(id) {
        const cloud = this.orchestrator && this.orchestrator.cloud;
        if (!cloud) return { provider: id, status: "dead", detail: "motore cloud non disponibile" };
        const def = cloud._provider(id);
        if (!def) return { provider: id, status: "dead", detail: "provider non configurato" };
        const https = require("https");
        const ngrok = /ngrok/i.test(def.host) ? { "ngrok-skip-browser-warning": "true" } : {};
        const doReq = (method, pathX, body) => new Promise((resolve) => {
            const headers = Object.assign({ "Authorization": "Bearer " + def.key, "User-Agent": "Antigravity/1.0" }, ngrok);
            if (body) { headers["Content-Type"] = "application/json"; headers["Content-Length"] = Buffer.byteLength(body); }
            const r = https.request({ host: def.host, path: pathX, method, timeout: 15000, headers }, (rs) => {
                let d = ""; rs.on("data", c => d += c); rs.on("end", () => resolve({ code: rs.statusCode || 0, body: d }));
            });
            r.on("error", () => resolve({ code: 0, body: "" })); r.on("timeout", () => { r.destroy(); resolve({ code: 0, body: "" }); });
            if (body) r.write(body); r.end();
        });
        try {
            const mp = def.modelsPath ? def.modelsPath : "/v1/models";
            const m = await doReq("GET", mp);
            if (m.code === 401 || m.code === 403) return { provider: id, status: "dead", detail: "chiave non valida (HTTP " + m.code + ")" };
            if (m.code === 0 || m.code >= 500) return { provider: id, status: "dead", detail: "non raggiungibile (HTTP " + m.code + ")" };
            if (def.chatPath) {
                const cm = await doReq("POST", def.chatPath, JSON.stringify({ model: (def.models && def.models[0]) || "x", messages: [{ role: "user", content: "hi" }], max_tokens: 4 }));
                if (cm.code === 402 || /not enough|quota|balance/i.test(cm.body)) return { provider: id, status: "quota", detail: "live ma senza credito/quota" };
                if (cm.code === 200) return { provider: id, status: "live", detail: "ok" };
                return { provider: id, status: "quota", detail: "modelli ok, chat:" + cm.code };
            }
            return { provider: id, status: "live", detail: "ok" };
        } catch (e) { return { provider: id, status: "dead", detail: e.message }; }
    }
    async _keys(req, res) {
        const cloud = this.orchestrator && this.orchestrator.cloud;
        if (!cloud) return this._json(res, { providers: [], suggestions: [] });
        const now = Date.now();
        let cache = this._keysCache;
        if (!cache.data || now - cache.at > 60000) {
            const all = cloud.listKnownProviders();
            const out = [];
            for (const p of all) {
                let status = "unknown";
                if (p.configured) {
                    try { const r = await this.probeKey(p.id); status = r.status; } catch (_) {}
                } else {
                    status = "no-key";
                }
                out.push(Object.assign({}, p, { status }));
            }
            cache = { at: now, data: out };
            this._keysCache = cache;
        }
        this._json(res, {
            providers: cache.data,
            dead: cache.data.filter(p => p.status === "dead").map(p => p.id),
            suggestions: cloud.freeSuggestions()
        });
    }
    async _detectKey(req, res) {
        const b = await this._body(req);
        const cloud = this.orchestrator && this.orchestrator.cloud;
        if (!cloud) return this._json(res, { best: null, candidates: [] });
        this._json(res, cloud.detectKey(String(b.key || "")));
    }
    async _addKey(req, res) {
        const b = await this._body(req);
        const cloud = this.orchestrator && this.orchestrator.cloud;
        if (!cloud) return this._json(res, { ok: false, error: "motore cloud non disponibile" }, 500);
        const rawKey = String(b.key || "");
        const chosen = b.provider || null;   // provider scelto a mano dall'utente (può mancare)
        const confirmOverwrite = !!b.confirmOverwrite; // l'utente ha confermato la sovrascrittura
        let provider = chosen, corrected = null, liveStatus = null;

        // ★ 2026-07-31 — AUTO-IDENTIFICAZIONE DAL VIVO, ma la SCELTA MANUALE VINCE.
        //   Proviamo la chiave contro gli endpoint per capire dove autentica, però:
        //   - se l'utente NON ha scelto → salviamo sul provider che autentica dal vivo;
        //   - se l'utente HA scelto e lì la chiave AUTENTICA (live/quota) o il
        //     servizio è giù/non testabile → RISPETTIAMO la sua scelta, non la spostiamo;
        //   - la "correzione" automatica scatta SOLO se il provider scelto è
        //     davvero MORTO (401/403) e un altro autentica: e anche allora avvisiamo.
        try {
            const ident = await cloud.identifyKeyLive(rawKey, { prefer: chosen });
            if (!chosen) {
                // nessuna scelta: prendi il provider vivo (se c'è)
                if (ident.best) { provider = ident.best.id; liveStatus = ident.best.liveStatus; }
            } else if (ident.preferStatus === "live" || ident.preferStatus === "quota") {
                // il provider scelto autentica: è quello giusto, punto.
                provider = chosen; liveStatus = ident.preferStatus;
            } else if (ident.preferStatus === "dead" && ident.best && ident.best.id !== chosen) {
                // scelto = morto, ma la chiave autentica ALTROVE → correzione motivata
                corrected = { from: chosen, to: ident.best.id, toLabel: ident.best.label };
                provider = ident.best.id; liveStatus = ident.best.liveStatus;
            } else {
                // servizio giù / non testabile / esito incerto: rispetta la scelta
                provider = chosen; liveStatus = null;
            }
        } catch (_) { /* test live non riuscito: si prosegue col provider scelto/rilevato */ }

        // La conferma di sovrascrittura vale quando l'utente ha scelto lui il provider
        // (o ha esplicitamente confermato): in quel caso può sovrascrivere la variabile.
        const r = cloud.saveKey(rawKey, provider, { confirmOverwrite: confirmOverwrite || (!!chosen && provider === chosen) });
        if (r.ok) {
            this.orchestrator.discoverCloud(true).catch(() => {}); // aggiorna il catalogo
            r.liveStatus = liveStatus;            // 'live' | 'quota' | null (servizio giù/non testato)
            if (corrected) r.corrected = corrected;
        }
        // conflict = la variabile ha già una chiave diversa e la risoluzione è automatica:
        // 409 così il frontend può chiedere conferma senza distruggere nulla.
        this._json(res, r, r.ok ? 200 : (r.conflict ? 409 : 400));
    }

    /**
     * Probe LIVE di una chiave provider: fa una richiesta leggera all'endpoint
     * del provider usando la CHIAVE REALE letta dal .env (mai esposta al client).
     * Ritorna { provider, status:'live'|'dead'|'quota', detail }.
     * Usa i path nota del provider dal registro; per i provider senza modelsPath
     * (es. perplexity) fa un ping su chatPath con un body minimo.
     */
    async _checkKey(req, res) {
        const providerId = String(req.url ? new URL(req.url, "http://x").searchParams.get("provider") || "" : "");
        const cloud = this.orchestrator && this.orchestrator.cloud;
        if (!cloud) return this._json(res, { provider: providerId, status: "dead", detail: "motore cloud non disponibile" }, 503);
        const def = providerId ? cloud._provider(providerId) : null;
        if (!def) return this._json(res, { provider: providerId, status: "dead", detail: "provider non configurato" }, 400);

        // ★ 2026-07-23 — VERIFICA REALE: prima /models (riconosce la chiave), POI una
        // mini-chat col primo modello → rivela quota/saldo/blocchi (chutes/novita danno
        // 200 su /models ma 402/403 "not enough balance" sulla chat). Così "valida"
        // significa DAVVERO usabile, non solo "chiave riconosciuta".
        const https = require("https");
        const ngrok = /ngrok/i.test(def.host) ? { "ngrok-skip-browser-warning": "true" } : {};
        const doReq = (method, pathX, body) => new Promise((resolve) => {
            const headers = Object.assign({ "Authorization": "Bearer " + def.key, "User-Agent": "Antigravity/1.0" }, ngrok);
            if (body) { headers["Content-Type"] = "application/json"; headers["Content-Length"] = Buffer.byteLength(body); }
            const r = https.request({ host: def.host, path: pathX, method, timeout: 15000, headers }, (rs) => {
                let d = ""; rs.on("data", c => d += c); rs.on("end", () => resolve({ code: rs.statusCode || 0, body: d }));
            });
            r.on("timeout", () => { r.destroy(); resolve({ code: 0, body: "timeout" }); });
            r.on("error", (e) => resolve({ code: 0, body: e.message }));
            if (body) r.write(body); r.end();
        });
        const classify = (code, body) => {
            if (code === 401 || code === 403 && !/balance|quota|insufficient|payment/i.test(body)) return { status: "dead", detail: "chiave non valida (HTTP " + code + ")" };
            if (code === 402 || code === 429 || /not enough balance|insufficient|out of funds|quota exceed|balance is \$0|payment required|requires.*credit/i.test(body)) return { status: "quota", detail: "credito/quota esaurito — non usabile ora (HTTP " + code + ")" };
            return null;
        };
        let result;
        try {
            // 1) /models → riconoscimento chiave + un id modello da testare
            let model = "";
            if (def.modelsPath) {
                const m = await doReq("GET", def.modelsPath, null);
                const c = classify(m.code, m.body);
                if (c) { this._json(res, Object.assign({ provider: providerId }, c)); return; }
                if (m.code < 200 || m.code >= 300) { this._json(res, { provider: providerId, status: "dead", detail: "HTTP " + m.code + " " + (m.body || "").slice(0, 120) }); return; }
                try { const j = JSON.parse(m.body); const arr = Array.isArray(j) ? j : (j.data || j.models || []); const pick = arr.find(x => /chat|instruct|llama|qwen|deepseek|mistral|gemini|gpt|coder|hermes/i.test(x.id || x.name || "")) || arr[0]; model = pick && String(pick.id || pick.name || "").replace(/^models\//, ""); } catch (_) {}
            }
            if (!model) { this._json(res, { provider: providerId, status: "live", detail: "chiave riconosciuta (nessun modello da testare)" }); return; }
            // 2) mini-chat reale col modello → stato d'uso EFFETTIVO
            const body = JSON.stringify({ model, messages: [{ role: "user", content: "ok" }], max_tokens: 1, stream: false });
            const chat = await doReq("POST", def.chatPath, body);
            const cc = classify(chat.code, chat.body);
            if (cc) result = Object.assign({ provider: providerId }, cc);
            else if (chat.code >= 200 && chat.code < 300) result = { provider: providerId, status: "live", detail: "funziona ✓ (testato " + model.slice(0, 40) + ")" };
            else result = { provider: providerId, status: "quota", detail: "non usabile ora: HTTP " + chat.code + " " + (chat.body || "").slice(0, 90) };
        } catch (e) { result = { provider: providerId, status: "dead", detail: "errore: " + (e.message || e) }; }
        this._json(res, result, 200);
    }

    /** Cacciatore di taglie. ★ 2026-07-24 — non più una lista scritta a mano che
     *  invecchia: se il motore cloud c'è, i modelli mostrati sono quelli VIVI ora
     *  (catalogo auto-aggiornato da /models di ogni provider) con salute e budget
     *  residuo. La lista curata resta come fallback e per i provider senza chiave.
     *  MAI chiavi/segreti nella risposta.
     *  ★ 2026-07-27 — accetta ?uncensored=1 per restituire SOLO i provider senza
     *  filtri (terza "categoria" del cacciatore di taglie). */
    _freeProviders(req, res) {
        try {
            const un = /(\?|&)uncensored=1/.test(req.url || "");
            const cloud = this.orchestrator && this.orchestrator.cloud;
            if (cloud && typeof cloud.liveFreeProviders === "function") {
                const all = cloud.liveFreeProviders();
                return this._json(res, { providers: un ? all.filter(p => p.uncensored) : all, live: true });
            }
            const reg = require("./providerRegistry");
            return this._json(res, { providers: reg.freeProviders(un ? "uncensored" : undefined), live: false });
        } catch (_) { return this._json(res, { providers: [] }); }
    }

    /** ★ 2026-07-27 — Traduttore: dato un URL esterno (keyUrl dei provider, pagine
     *  GPU), restituisce l'URL del traduttore Google in italiano, così l'utente
     *  apre SEMPRE la pagina tradotta (anche se il sito è cinese/russo/inglese).
     *  NESSUN segreto: solo il link, passato dal client. */
    _translate(req, res) {
        try {
            const u = new URL(req.url, "http://localhost");
            const target = u.searchParams.get("u");
            if (!target) return this._json(res, { error: "manca u" }, 400);
            const tUrl = "https://translate.google.com/translate?sl=auto&tl=it&u=" + encodeURIComponent(target);
            return this._json(res, { url: tUrl });
        } catch (e) { return this._json(res, { error: e.message }, 400); }
    }

    // ---- 🎵 MUSICA (ricerca brano + testo + anteprima 30s) ------------------
    //
    // ★ 2026-07-30 — "Spotify che funziona davvero" senza uscire dalla pagina, nella
    // parte che NON richiede né login né Premium: cerca il brano, mostra il testo,
    // suona l'anteprima di 30s (mp3), e offre "Apri in Spotify" per il brano intero.
    // Fonti gratuite senza chiave (lyrics.ovh / Deezer). Il telefono non contatta i
    // siti: il PC fa da tramite, come per Tor. La riproduzione INTERA nel tuo Spotify
    // (Premium, controllo via Web API) è un secondo passo che si attiva quando metti
    // le credenziali della tua app developer.

    /** GET esterno → JSON (nessuna chiave). Ritorna null se fallisce, mai eccezioni. */
    _musicHttpJson(target, timeoutMs = 15000) {
        return new Promise((resolve) => {
            let done = false; const fin = v => { if (!done) { done = true; resolve(v); } };
            try {
                const https = require("https");
                const r = https.get(target, { timeout: timeoutMs, headers: { "User-Agent": "Antigravity/1.0" } }, (rs) => {
                    let d = ""; rs.on("data", c => { if (d.length < 500000) d += c; });
                    rs.on("end", () => { try { fin(JSON.parse(d)); } catch (_) { fin(null); } });
                });
                r.on("error", () => fin(null));
                r.on("timeout", () => { r.destroy(); fin(null); });
            } catch (_) { fin(null); }
        });
    }

    /** /music/search?q=… → { results:[{title,artist,album,cover,preview,spotify}] } */
    async _musicSearch(req, res) {
        try {
            const u = new URL(req.url, "http://localhost");
            const q = (u.searchParams.get("q") || "").trim();
            if (!q) return this._json(res, { results: [] });
            const j = await this._musicHttpJson("https://api.lyrics.ovh/suggest/" + encodeURIComponent(q));
            const results = ((j && j.data) || []).slice(0, 12).map(x => {
                const artist = (x.artist && x.artist.name) || "";
                return {
                    title: x.title || "", artist,
                    album: (x.album && x.album.title) || "",
                    cover: (x.album && (x.album.cover_medium || x.album.cover)) || "",
                    preview: x.preview || "",   // mp3 30s: suonabile in-pagina, niente login
                    spotify: "https://open.spotify.com/search/" + encodeURIComponent((artist + " " + (x.title || "")).trim())
                };
            });
            return this._json(res, { results });
        } catch (e) { return this._json(res, { results: [], error: e.message }, 500); }
    }

    /** /music/spotify?q=… → { ok, embed, url } — trova l'ID del brano su Spotify
     *  (keyless, via ricerca web: site:open.spotify.com/track) e ritorna l'URL del
     *  PLAYER EMBED ufficiale. È l'approccio di EfestoAI: niente OAuth/Client-ID,
     *  l'iframe suona l'anteprima per tutti e il brano intero se sei loggato in
     *  Spotify nel browser/webview. */
    async _musicSpotifyEmbed(req, res) {
        try {
            const u = new URL(req.url, "http://localhost");
            const q = (u.searchParams.get("q") || "").trim();
            if (!q) return this._json(res, { ok: false, error: "manca q" }, 400);
            let web; try { web = require("./webSearch"); } catch (_) { return this._json(res, { ok: false, error: "ricerca web non disponibile" }, 500); }
            const tentativi = ["site:open.spotify.com/track " + q, "site:open.spotify.com " + q + " song", q + " spotify track"];
            for (const query of tentativi) {
                let ris = [];
                try { ris = await web.search(query, 8); } catch (_) { continue; }
                for (const r of ris || []) {
                    const m = String(r.url || "").match(/open\.spotify\.com\/(?:intl-\w+\/)?(track|album|playlist|episode)\/([A-Za-z0-9]+)/);
                    if (m) return this._json(res, { ok: true, embed: "https://open.spotify.com/embed/" + m[1] + "/" + m[2], url: r.url });
                }
            }
            return this._json(res, { ok: false, error: "brano non trovato su Spotify" });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** GET pagina (HTML) con User-Agent da browser. Per lo scraping keyless di YouTube. */
    _musicPageHtml(target, timeoutMs = 15000) {
        return new Promise((resolve) => {
            let done = false; const fin = v => { if (!done) { done = true; resolve(v); } };
            try {
                const https = require("https");
                const r = https.get(target, { timeout: timeoutMs, headers: {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8"
                } }, (rs) => {
                    let d = ""; rs.on("data", c => { if (d.length < 3000000) d += c; });
                    rs.on("end", () => fin(d));
                });
                r.on("error", () => fin(""));
                r.on("timeout", () => { r.destroy(); fin(""); });
            } catch (_) { fin(""); }
        });
    }

    /** /music/youtube?q=… → { ok, videoId, embed, title } — trova il video del brano
     *  su YouTube (keyless: interroga la pagina risultati ed estrae il primo videoId)
     *  e ritorna l'URL dell'iframe player. YouTube ha il BRANO INTERO, gratis: è la
     *  riproduzione completa per chi non ha Spotify Premium. */
    async _musicYouTube(req, res) {
        try {
            const u = new URL(req.url, "http://localhost");
            const q = (u.searchParams.get("q") || "").trim();
            if (!q) return this._json(res, { ok: false, error: "manca q" }, 400);
            const html = await this._musicPageHtml("https://www.youtube.com/results?search_query=" + encodeURIComponent(q) + "&hl=it");
            const m = html.match(/"videoId":"([A-Za-z0-9_-]{11})"/);
            if (!m) return this._json(res, { ok: false, error: "nessun video trovato su YouTube" });
            const t = html.match(/"title":\{"runs":\[\{"text":"([^"]{1,90})"/);
            return this._json(res, { ok: true, videoId: m[1], title: t ? t[1] : "", embed: "https://www.youtube.com/embed/" + m[1] });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** /music/lyrics?artist=…&title=… → { lyrics, found } */
    async _musicLyrics(req, res) {
        try {
            const u = new URL(req.url, "http://localhost");
            const artist = (u.searchParams.get("artist") || "").trim();
            const title = (u.searchParams.get("title") || "").trim();
            if (!artist || !title) return this._json(res, { error: "servono artist e title", found: false }, 400);
            const j = await this._musicHttpJson("https://api.lyrics.ovh/v1/" + encodeURIComponent(artist) + "/" + encodeURIComponent(title));
            return this._json(res, { lyrics: (j && j.lyrics) || "", found: !!(j && j.lyrics) });
        } catch (e) { return this._json(res, { error: e.message, found: false }, 500); }
    }

    /** ★ 2026-07-24 — CACCIA VERA: interroga online l'elenco aggiornato dei provider
     *  con piano gratuito e propone quelli che NON hai (con il link per la chiave).
     *  Non crea account e non tocca niente: trova e propone. Cache di 24h. */
    async _huntProviders(req, res) {
        try {
            const { BountyHunter } = require("./bountyHunter");
            if (!this._hunter) this._hunter = new BountyHunter(console, { storageDir: this.storageDir || process.cwd() });
            const force = /(\?|&)force=1/.test(req.url || "");
            // ★ 2026-07-27 — la UI del cacciatore ha 3 schede: la scheda "Senza
            // filtri" passa ?uncensored=1 così proponiamo SOLO i provider abliterated.
            const uncensored = /(\?|&)uncensored=1/.test(req.url || "");
            const cloud = this.orchestrator && this.orchestrator.cloud;
            const ids = cloud && cloud.getProviderIds ? cloud.getProviderIds() : [];
            const r = await this._hunter.hunt({ force, configuredIds: ids, uncensored });
            return this._json(res, r);
        } catch (e) {
            return this._json(res, { error: e.message, nuovi: [], gia: [] }, 500);
        }
    }

    /** ★ 2026-07-27 — Cacciatore di piattaforme GPU (tipo Kaggle): confronto
     *  Kaggle/Colab/Modal/RunPod/HF + stato live di Kaggle (via kaggleWaker). */
    async _gpuPlatforms(req, res) {
        try {
            const { summary } = require("./gpuPlatforms");
            const r = await summary();
            return this._json(res, r);
        } catch (e) {
            return this._json(res, { error: e.message, platforms: [] }, 500);
        }
    }

    /** ★ 2026-07-27 — CACCIATORE DI BUG INTERNO: report dello stato dell'app.
     *  Se ?fix=1 (o force) esegue anche le auto-riparazioni (whitelist chiusa).
     *  Mai espone segreti: i dettagli citano solo nomi file / id provider. */
    async _bugHunter(req, res) {
        try {
            const { scan } = require("./bugHunter");
            const fix = /(\?|&)(fix|force)=1/.test(req.url || "");
            const r = scan({ autoFix: fix });
            const high = r.issues.filter(i => i.severity === "high").length;
            return this._json(res, {
                ok: true,
                scannedAt: r.scannedAt,
                issues: r.issues,
                fixed: r.fixed,
                fixes: r.fixes,
                healthy: r.issues.length === 0,
                highIssues: high,
                note: "Auto-riparazione su whitelist chiusa. Per riparare manualmente: GET /bugHunter/scan?fix=1"
            });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** Forza una scansione + riparazione completa. */
    async _bugHunterScan(req, res) {
        try {
            const { scan } = require("./bugHunter");
            const r = scan({ autoFix: true });
            return this._json(res, { ok: true, fixed: r.fixed, fixes: r.fixes, issues: r.issues, tickets: r.tickets, scannedAt: r.scannedAt });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** ★ 2026-07-27 — CODA TICKET: gli errori che il cacciatore non ha potuto
     *  auto-riparare. ★ 2026-07-30 — ora la lettura passa da bugHunter.listTickets
     *  (una sola implementazione invece di due copie che leggevano la stessa
     *  cartella con criteri diversi). */
    async _bugHunterQueue(req, res) {
        try {
            const { listTickets } = require("./bugHunter");
            const tickets = listTickets();
            return this._json(res, {
                ok: true,
                open: tickets.filter(t => t.status === "open").length,
                inProgress: tickets.filter(t => t.status === "in-progress").length,
                tickets
            });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-30 — DELEGA A HERMES, SU RICHIESTA ESPLICITA.
     *  Prima la coda era una buca delle lettere senza postino: i ticket venivano
     *  scritti e nessuno li leggeva (uno è rimasto aperto 3 giorni). Qui il
     *  passaggio esiste davvero, ma parte solo quando l'utente preme il bottone:
     *  nessun agente riscrive codice mentre non stai guardando.
     *
     *  Hermes può metterci minuti, quindi NON teniamo appesa la richiesta HTTP
     *  (sul telefono andrebbe in timeout): il ticket passa a "in-progress", la
     *  risposta torna subito, e la risoluzione viene scritta nel ticket a lavoro
     *  finito. La UI la vede al successivo aggiornamento della coda. */
    async _preparaHermes(req, statiAmmessi) {
        const body = await this._body(req);
        const file = body && body.file;
        if (!file) return { errore: "manca il campo 'file' del ticket", codice: 400 };

        // ★ 2026-07-30 — CANTIERE: Hermes gira con --yolo, quindi può riscrivere
        // qualsiasi file mentre tu stai costruendo dal telefono. Finché un cantiere
        // è aperto la delega è RINVIATA (non annullata: il ticket resta lì). Si può
        // forzare con force:true nel corpo, ma dev'essere una tua scelta esplicita.
        if (!(body && body.force)) {
            try {
                const cant = require("./cantiere");
                const g = cant.manutenzioneAmmessa("la manutenzione con Hermes");
                if (!g.ammessa) return { errore: g.motivo, codice: 409, cantiere: g.cantiere };
            } catch (_) { /* cantiere assente: si prosegue come prima */ }
        }

        const { listTickets } = require("./bugHunter");
        const t = listTickets().find(x => x.file === file);
        if (!t) return { errore: "ticket inesistente: " + file, codice: 404 };
        if (statiAmmessi.indexOf(t.status) < 0)
            return { errore: "il ticket è in stato '" + t.status + "': qui serve " + statiAmmessi.join(" o "), codice: 409 };

        const { HermesClient } = require("./hermesClient");
        const hermes = new HermesClient({ cwd: path.join(__dirname, ".."), logger: console });
        if (!hermes.available())
            return { errore: "hermes.exe non trovato: controlla HERMES_HOME nel .env", codice: 503 };
        return { t, hermes };
    }

    /** FASE 1 — ANALISI. Hermes studia il problema e PROPONE, non tocca niente.
     *  Il piano finisce nel ticket, che passa in attesa della tua approvazione:
     *  quando approvi sai esattamente cosa stai approvando (causa, file, modifica,
     *  rischi) invece di dare un --yolo al buio.
     *
     *  Hermes gira comunque con --yolo perché headless una sua richiesta di
     *  conferma non ha nessuno che risponda e manda tutto in timeout (successo
     *  davvero: 4 minuti, output vuoto). Quindi il "non modificare" NON è affidato
     *  alla sua buona volontà: fotografiamo tutti i file prima e dopo e, se ne ha
     *  toccato uno, il ticket lo segnala PRIMA che tu approvi. */
    async _bugHunterDelegate(req, res) {
        try {
            const p = await this._preparaHermes(req, ["open"]);
            if (p.errore) return this._json(res, { ok: false, error: p.errore }, p.codice);
            const { t, hermes } = p;
            const { updateTicket, promptAnalisi, fotografiaAlbero, confrontaAlbero } = require("./bugHunter");

            updateTicket(t.file, { status: "analyzing", analyzedAt: new Date().toISOString(), plan: null, resolution: null, warnings: null });
            const prima = fotografiaAlbero();

            // Sganciato dalla risposta HTTP: gli errori finiscono nel ticket, non in
            // un'eccezione che nessuno raccoglie.
            hermes.delegate(promptAnalisi(t), {
                onStatus: (s) => console.log("[bugHunter→hermes/analisi] " + s),
                timeoutMs: 6 * 60 * 1000,
                extraArgs: ["--yolo"]
            }).then(out => {
                const tocchi = confrontaAlbero(prima, fotografiaAlbero());
                updateTicket(t.file, {
                    status: "awaiting-approval",
                    plan: String(out || "").slice(0, 20000),
                    warnings: tocchi.length ? tocchi : null
                });
                console.log("[bugHunter→hermes/analisi] ticket " + t.id + ": piano pronto" + (tocchi.length ? " ⚠️ ha toccato " + tocchi.length + " file" : ""));
            }).catch(err => {
                updateTicket(t.file, { status: "open", resolution: "❌ Analisi fallita: " + err.message });
                console.error("[bugHunter→hermes/analisi] ticket " + t.id + " fallito: " + err.message);
            });

            return this._json(res, { ok: true, status: "analyzing", id: t.id, file: t.file });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** FASE 2 — ESECUZIONE. Parte SOLO su un ticket che ha già un piano e che tu
     *  hai approvato premendo. Hermes riceve il piano come mandato, con l'obbligo
     *  di non allargarsi ad altri file. A fine lavoro il ticket elenca i file
     *  davvero cambiati (per confronto, non per fiducia) e viene rifatta una
     *  scansione: se la modifica ha rotto qualcosa, si vede subito. */
    async _bugHunterApply(req, res) {
        try {
            const p = await this._preparaHermes(req, ["awaiting-approval"]);
            if (p.errore) return this._json(res, { ok: false, error: p.errore }, p.codice);
            const { t, hermes } = p;
            const { updateTicket, promptEsecuzione, fotografiaAlbero, confrontaAlbero, scan } = require("./bugHunter");
            if (!t.plan) return this._json(res, { ok: false, error: "il ticket non ha un piano da approvare" }, 409);

            updateTicket(t.file, { status: "applying", approvedAt: new Date().toISOString() });
            const prima = fotografiaAlbero();

            hermes.delegate(promptEsecuzione(t), {
                onStatus: (s) => console.log("[bugHunter→hermes/esecuzione] " + s),
                timeoutMs: 8 * 60 * 1000,
                extraArgs: ["--yolo"]
            }).then(out => {
                const cambiati = confrontaAlbero(prima, fotografiaAlbero());
                let rotti = [];
                try { rotti = scan({ autoFix: false }).issues.filter(i => i.severity === "high").map(i => "[" + i.id + "] " + i.detail); } catch (_) {}
                updateTicket(t.file, {
                    status: "resolved",
                    resolution: String(out || "").slice(0, 20000),
                    changedFiles: cambiati,
                    afterCheck: rotti.length ? rotti : "nessun errore grave dopo la modifica",
                    resolvedAt: new Date().toISOString()
                });
                console.log("[bugHunter→hermes/esecuzione] ticket " + t.id + " chiuso. File cambiati: " + cambiati.length);
            }).catch(err => {
                updateTicket(t.file, { status: "awaiting-approval", resolution: "❌ Esecuzione fallita: " + err.message });
                console.error("[bugHunter→hermes/esecuzione] ticket " + t.id + " fallito: " + err.message);
            });

            return this._json(res, { ok: true, status: "applying", id: t.id, file: t.file });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-30 — Chiude un ticket a mano (falso allarme, o già sistemato). */
    async _bugHunterClose(req, res) {
        try {
            const body = await this._body(req);
            if (!body || !body.file) return this._json(res, { ok: false, error: "manca il campo 'file' del ticket" }, 400);
            const { updateTicket } = require("./bugHunter");
            const t = updateTicket(body.file, {
                status: "resolved",
                resolution: body.resolution || "Chiuso a mano dall'utente.",
                resolvedAt: new Date().toISOString()
            });
            return this._json(res, { ok: true, ticket: t });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 400); }
    }

    /** ★ 2026-07-27 — ESEGUE un sotto-agente reale (ghidra/zw3d/immagini/web). */
    async _agentsRun(req, res) {
        try {
            const body = await this._body(req);
            const { key, input } = body || {};
            if (!key) return this._json(res, { ok: false, error: "manca key" }, 400);
            const { runSpecialist } = require("./specialists");
            const r = runSpecialist(key, input || {});
            return this._json(res, { ok: true, key, result: r });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** ★ 2026-07-27 — Prepara/invia download modello UNCENSORED da HF SULLA PIATTAFORMA. */
    async _gpuPull(req, res) {
        try {
            const body = await this._body(req);
            const { repo, pattern, target } = body || {};
            if (!repo) return this._json(res, { ok: false, error: "manca repo HF" }, 400);
            const { pull } = require("./modelPuller");
            const r = await pull(repo, { pattern, target });
            return this._json(res, { ok: true, pulled: r });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** ★ 2026-07-27 — Stato piattaforme GPU gratis cablate. */
    async _gpuStatus(req, res) {
        try { const { status } = require("./gpuWaker"); return this._json(res, { ok: true, free: status() }); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** ★ 2026-07-27 — PIANIFICAZIONE A STEP (CORE AI): scompone ed esegue un task. */
    async _plan(req, res) {
        try {
            const body = await this._body(req);
            const { task, model } = body || {};
            if (!task) return this._json(res, { ok: false, error: "manca task" }, 400);
            const { run } = require("./planner");
            const r = await run(task, model);
            return this._json(res, { ok: true, plan: r });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** ★ 2026-07-27 — CONFRONTO MODELLI: stessa richiesta su piu' modelli. */
    async _modelsCompare(req, res) {
        try {
            const body = await this._body(req);
            const { prompt, models } = body || {};
            if (!prompt) return this._json(res, { ok: false, error: "manca prompt" }, 400);
            const list = (models && Array.isArray(models)) ? models.slice(0, 3) : ["auto"];
            const out = [];
            for (const m of list) {
                try {
                    const r = await new Promise((resolve) => {
                        const httpm = require("http");
                        const data = JSON.stringify({ prompt, model: m });
                        const rq = httpm.request({ host: "127.0.0.1", port: 8790, path: "/chat", method: "POST",
                            headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } },
                            (rs) => { let d = ""; rs.on("data", c => d += c); rs.on("end", () => resolve(d)); });
                        rq.on("error", () => resolve("")); rq.write(data); rq.end();
                    });
                    out.push({ model: m, reply: String(r).slice(0, 600) });
                } catch (e) { out.push({ model: m, error: e.message }); }
            }
            return this._json(res, { ok: true, compared: out });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-27 — GHIDRA: decompile / diff / secrets / scripts (REVERSE, blocco 3). */
    async _ghidra(req, res, action) {
        try {
            const body = await this._body(req);
            // legge path/a/b dal body (POST) O dalla query (GET)
            const q = require("url").parse(req.url, true).query || {};
            const dec = (s) => { try { return s ? decodeURIComponent(s) : s; } catch (_) { return s; } };
            const bin = dec((body && body.path) || q.path || q.file || null);
            const a = dec((body && body.a) || q.a || null);
            const b = dec((body && body.b) || q.b || null);
            const { runSpecialist } = require("./specialists");
            let r;
            if (action === "decompile") r = runSpecialist("ghidra", { action: "decompile", path: bin });
            else if (action === "secrets") r = runSpecialist("ghidra", { action: "secrets", path: bin });
            else if (action === "diff") r = runSpecialist("ghidra", { action: "diff", a, b });
            else if (action === "scripts") { const ag = require("./agents/ghidraAgent"); r = { ok: true, scripts: ag.SCRIPTS }; }
            else r = { ok: false, error: "azione sconosciuta" };
            return this._json(res, { ok: true, action, result: r });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-27 — GPU FAILOVER / SCHEDULE / PRELOAD / QUOTA (INFRA, blocco 4). */
    async _gpuFailover(req, res) {
        try { const { pickActive, platforms } = require("./gpuFailover"); return this._json(res, { ok: true, active: pickActive(), platforms: platforms() }); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _gpuSchedule(req, res) {
        try {
            const body = await this._body(req);
            const { on, off } = body || {};
            const FO = require("./gpuFailover");
            if (on || off) { const s = FO.setSchedule(on, off); return this._json(res, { ok: true, set: s }); }
            return this._json(res, { ok: true, schedule: FO.getSchedule() });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _gpuPreload(req, res) {
        try {
            const body = await this._body(req);
            const { repo } = body || {};
            const FO = require("./gpuFailover");
            if (repo) { const p = FO.setPreload(repo); return this._json(res, { ok: true, set: p }); }
            return this._json(res, { ok: true, preload: FO.getPreload() });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    async _gpuQuota(req, res) {
        try { const { quota } = require("./gpuFailover"); const q = await quota(); return this._json(res, { ok: true, quota: q }); }
        catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-27 — ROLLBACK: ripristina l'ultimo backup buono di un file (blocco 5). */
    async _rollback(req, res) {
        try {
            const body = await this._body(req);
            const { name, force } = body || {};
            if (!name) return this._json(res, { ok: false, error: "manca name (es. mobileServer.js)" }, 400);
            const { rollback } = require("./rollback");
            const r = rollback(name, { force: !!force });
            // ★ 2026-07-30 — Bloccato dal cantiere: non è un errore, è la protezione
            // che funziona. Va risposto 409 (non 200 "ok") o dal telefono sembra fatto.
            if (r.bloccato) return this._json(res, { ok: false, bloccato: true, rollback: r }, 409);
            if (r.ok) {
                // riavvia il server per rendere effettivo il rollback
                try { require("child_process").spawn("powershell.exe", ["-ExecutionPolicy","Bypass","-File", path.join(__dirname, "apply-change.ps1")], { detached: true }); } catch (_) {}
            }
            return this._json(res, { ok: true, rollback: r });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-27 — SIMULAZIONE DISASTRO (blocco 7, punto 26). */
    async _simulateDisaster(req, res) {
        try {
            const { run } = require("./disasterSim");
            const r = run();
            return this._json(res, { ok: true, sim: r });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }
    /** ★ 2026-07-27 — ALLARMI file toccati da estraneo (blocco 7, punto 27). */
    async _alerts(req, res) {
        try {
            const fs = require("fs"); const path = require("path");
            const f = path.join(__dirname, ".bugHunter", "alerts.json");
            const alerts = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : [];
            return this._json(res, { ok: true, count: alerts.length, alerts: alerts.slice(-20) });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    /** ★ 2026-07-27 — GUIDA CONFIGURAZIONE PIATTAFORMA (assistente guidato, come Claude Code ma in Antigravity). */
    async _platformGuide(req, res) {
        try {
            const url = require("url").parse(req.url, true);
            const name = (url.query.name || (req.body && req.body.name) || "").toString();
            const { guide } = require("./platformGuide");
            const g = guide(name);
            return this._json(res, { ok: true, guide: g });
        } catch (e) { return this._json(res, { ok: false, error: e.message }, 500); }
    }

    // ---- Allega file (qualsiasi tipo/dimensione): salva in streaming su disco ----
    _upload(req, res) {
        try {
            let name = decodeURIComponent(req.headers["x-filename"] || "allegato.bin");
            name = name.replace(/[\\/:*?"<>|]+/g, "_").replace(/^\.+/, "").slice(0, 180) || "allegato.bin";
            const dir = path.join(this.storageDir, "uploads");
            fs.mkdirSync(dir, { recursive: true });
            // Nome univoco (timestamp) per non sovrascrivere allegati diversi.
            const fp = path.join(dir, Date.now().toString(36) + "_" + name);
            const ws = fs.createWriteStream(fp);
            let size = 0;
            req.on("data", (c) => { size += c.length; });
            req.pipe(ws);
            ws.on("finish", () => {
                this.logger && this.logger.log && this.logger.log("[upload] " + fp + " (" + size + " byte)");
                this._json(res, { ok: true, path: fp.replace(/\\/g, "/"), name, size });
            });
            ws.on("error", (e) => this._json(res, { ok: false, error: e.message }, 500));
            req.on("error", () => { try { ws.destroy(); } catch (_) {} });
        } catch (e) { this._json(res, { ok: false, error: e.message }, 500); }
    }

    async _switchReq(req, res) { const b = await this._body(req); this._switchChat(b.id); this._json(res, { ok: true }); }
    async _deleteReq(req, res) { const b = await this._body(req); this._deleteChat(b.id); this._json(res, { ok: true }); }

    /** Se Ollama è spento, prova ad avviarlo (ollama serve) e attende che risponda. */
    async _ensureOllama() {
        try { if (await this.orchestrator.isOnline()) return true; } catch (_) {}
        this._broadcast({ type: "updateStatus", value: "⏳ Avvio Ollama..." });
        try {
            const { spawn } = require("child_process");
            const path = require("path"), os = require("os");
            // ★ 2026-07-19 FIX: "ollama" NON è nel PATH su questa macchina → prima
            // falliva. Prova prima l'exe REALE, poi il PATH come ripiego.
            const exe = path.join(os.homedir(), "AppData", "Local", "Programs", "Ollama", "ollama.exe");
            const fs = require("fs");
            if (fs.existsSync(exe)) spawn(exe, ["serve"], { detached: true, stdio: "ignore", windowsHide: true }).unref();
            else spawn("ollama serve", { detached: true, stdio: "ignore", windowsHide: true, shell: true }).unref();
        } catch (_) { /* ollama non trovato */ }
        for (let i = 0; i < 20; i++) {                       // fino a ~10s
            await new Promise(r => setTimeout(r, 500));
            try { if (await this.orchestrator.isOnline()) return true; } catch (_) {}
        }
        return false;
    }

    async _models(req, res) {
        try {
            this._startDiscoveryIfNeeded();
            const payload = {
                models: this.orchestrator.getModelChoices(),
                roles: this.orchestrator.getRoleAssignments(),
                cloud: {
                    configured: this.orchestrator.cloudConfigured(),
                    channels: this.orchestrator.cloudConfigured() ? this.orchestrator.getCloudChannels() : { normal: [], uncensored: [] }
                },
                claude: {
                    available: !!(this.orchestrator.claudeAvailable && this.orchestrator.claudeAvailable()),
                    models: this.orchestrator.getClaudeModelChoices ? this.orchestrator.getClaudeModelChoices() : [],
                    limit: this.orchestrator.getClaudeLimit ? this.orchestrator.getClaudeLimit() : null
                },
                hermes: {
                    available: !!(this.orchestrator.hermesAvailable && this.orchestrator.hermesAvailable()),
                    models: this.orchestrator.getHermesModelChoices ? this.orchestrator.getHermesModelChoices() : []
                },
                nous: {
                    available: !!(this.orchestrator.nousAvailable && this.orchestrator.nousAvailable()),
                    models: this.orchestrator.getNousModelChoices ? this.orchestrator.getNousModelChoices() : []
                },
                policy: this.orchestrator.permissionPolicy
            };
            this._json(res, payload);
        } catch (err) { this._json(res, { error: err.message }, 500); }
    }

    _startDiscoveryIfNeeded() {
        if (this._discoveryStarted) return;
        this._discoveryStarted = true;
        const run = async () => {
            try { await this.orchestrator.discover(true); } catch (_) {}
            try { if (this.orchestrator.cloudConfigured()) await this.orchestrator.discoverCloud(true); } catch (_) {}
        };
        run().catch(() => {});
    }

    async _send(req, res) {
        const body = await this._body(req);
        this._json(res, { ok: true }); // la risposta vera arriva via SSE
        const prompt = String(body.prompt || "").trim();
        if (!prompt) return;

        // CODA (niente più "aspetta la fine"): se sto già lavorando, ACCODO il
        // messaggio ed eco subito la domanda a tutti i client. Appena finisco il
        // turno in corso prendo il prossimo — come un assistente che continua il
        // lavoro e risponde appena può, senza far ripetere niente all'utente.
        this._queue = this._queue || [];
        this._queue.push(body);
        this._broadcast({ type: "userMessage", value: prompt }); // eco immediato su telefono + VS Code
        if (this.busy) {
            this._broadcast({ type: "status", value: `📥 Aggiunto in coda (${this._queue.length}). Lo faccio appena finisco quello in corso.` });
            return;
        }
        this._drainQueue();
    }

    /**
     * Esegue i messaggi in coda uno per volta, in ordine, riprendendo da solo.
     * Registra ogni messaggio nella conversazione condivisa SOLO quando arriva il
     * suo turno, così la cronologia inviata al modello resta coerente anche con
     * più messaggi accodati.
     */
    async _drainQueue() {
        if (this.busy) return;
        const body = this._queue && this._queue.shift();
        if (!body) return;
        this.busy = true;

        const prompt = String(body.prompt || "").trim();
        const provider = body.provider || "local";
        this._appendMessage({ role: "user", content: prompt });
        const history = this.conversation.slice(0, -1).map(m => ({ role: m.role, content: m.content }));

        // ★ 2026-09-01 — RIPRESA di una conversazione di Claude Code scelta dal
        // telefono: se questa chat ne ha una agganciata, Claude riparte da QUEL
        // filo e con IL SUO cwd (le sessioni sono legate alla cartella d'origine,
        // e --resume le cerca lì). Vale solo col provider Claude.
        const active = this._active();
        const ripresa = provider === "claude" ? (active && active.claudeResume) : null;
        if (ripresa && this.orchestrator.claude) {
            this.orchestrator.claude.primeResume(this.activeId, ripresa.sessionId);
        }

        try {
            // Per il locale (e per Hermes, che gira su Ollama) serve Ollama: se spento,
            // prova ad avviarlo. Cloud e Claude Code non ne hanno bisogno.
            if (provider === "local" || provider === "hermes") {
                const ok = await this._ensureOllama();
                if (!ok) { this._broadcast({ type: "addResponse", value: "⚠️ Ollama non è raggiungibile e non sono riuscito ad avviarlo. Avvialo sul PC e riprova." }); return; }
            }
            await this.orchestrator.handle(prompt, {
                mode: body.mode || "auto",
                model: body.model || "auto",
                // Corsia scelta nel pannello modelli: "come vuoi che risponda"
                // (fast/big/unc/paid/auto). Non e' un modello: e' un modo di
                // ordinare i candidati. Vedi cloudEngine.resilientCandidates.
                lane: body.lane || "auto",
                provider,
                channel: body.channel || "normal",
                history,
                conversationId: this.activeId,   // Claude riprende la SUA sessione per questa chat
                // Se stai riprendendo un filo salvato, il cwd è quello della sessione
                // originale; altrimenti quello di sempre.
                workspaceRoot: (ripresa && ripresa.cwd) || body.workspaceRoot || this.workspaceRoot,
                webview: this.webview
            });
        } catch (err) {
            this._broadcast({ type: "addResponse", value: "❌ Errore: " + err.message });
        } finally {
            this.busy = false;
            // Prossimo in coda: riprende da solo appena può.
            if (this._queue && this._queue.length) {
                this._broadcast({ type: "status", value: `▶️ Riprendo dalla coda (${this._queue.length} rimasti)…` });
                this._drainQueue();
            }
        }
    }

    // ── PONTE COL TELEFONO ────────────────────────────────────────────────
    /** Elenco delle conversazioni di Claude Code salvate sul PC (le più recenti). */
    _claudeSessions(res) {
        const claude = this.orchestrator.claude;
        if (!claude || !claude.available()) return this._json(res, { available: false, list: [] });
        let list = [];
        try { list = claude.listSessions({ limit: 60 }); }
        catch (e) { return this._json(res, { available: true, list: [], error: e.message }); }
        // Non mando l'id nudo in chiaro più del necessario: basta id, titolo, data,
        // progetto e cwd (serve alla ripresa). Niente contenuto dei messaggi.
        return this._json(res, { available: true, list });
    }

    /**
     * Aggancia una conversazione di Claude Code alla chat ATTIVA: dal messaggio
     * successivo, con provider "claude", riprende quel filo. Corpo: {sessionId, cwd}.
     */
    async _claudeResume(req, res) {
        let body = {};
        try { body = await this._body(req); } catch (_) { /* corpo vuoto */ }
        const sessionId = String(body.sessionId || "").trim();
        if (!sessionId) return this._json(res, { ok: false, error: "manca sessionId" }, 400);
        const active = this._active();
        active.claudeResume = { sessionId, cwd: body.cwd || null, title: body.title || "" };
        active.updatedAt = Date.now();
        // Il titolo della chat prende quello della sessione ripresa, se ne ha uno.
        if (body.title && (!active.title || active.title === "Nuova chat")) active.title = "↩ " + String(body.title).slice(0, 40);
        if (this.orchestrator.claude) this.orchestrator.claude.primeResume(this.activeId, sessionId);
        this._saveConversations();
        this._broadcastList();
        return this._json(res, { ok: true, resumed: sessionId });
    }

    _clear(res) {
        // Svuota la chat ATTIVA (mantiene le altre).
        const active = this._active();
        // La chat riparte da zero: anche Claude deve dimenticare la sua sessione,
        // altrimenti riprenderebbe il filo di una conversazione che l'utente ha buttato.
        if (this.orchestrator.forgetClaudeSession) this.orchestrator.forgetClaudeSession(active.id);
        active.messages.length = 0;
        active.clearedIndex = 0;
        active.title = "Nuova chat";
        active.updatedAt = Date.now();
        this.conversation = active.messages;
        this._saveConversations();
        this._broadcast({ type: "cleared" });
        this._broadcastList();
        this._json(res, { ok: true });
    }

    // ── GESTIONE SERVER (lato server) ─────────────────────────────────────
    // Stato/uptime del processo server (leggero, per monitor esterni/crontab).
    _serverStatus(req, res) {
        const mem = process.memoryUsage();
        const up = Date.now() - (this._startedAt || Date.now());
        const days = Math.floor(up / 86400000), hrs = Math.floor((up % 86400000) / 3600000),
              mins = Math.floor((up % 3600000) / 60000), secs = Math.floor((up % 60000) / 1000);
        const upStr = (days ? days + "g " : "") + (hrs ? hrs + "h " : "") + mins + "m " + secs + "s";
        this._json(res, {
            pid: process.pid,
            platform: process.platform,
            node: process.version,
            uptimeMs: up,
            uptime: upStr,
            startedAt: new Date(this._startedAt || Date.now()).toISOString(),
            busy: !!this.busy,
            clients: (this.clients && this.clients.size) || 0,
            conversations: (this.convs && this.convs.length) || 0,
            memory: { rssMb: Math.round(mem.rss / 1048576), heapMb: Math.round(mem.heapUsed / 1048576) },
            logFile: this._logFile || null
        });
    }

    // Health COMPLETO: riusa la dashboard /status ma aggiunge uptime/pid e
    // un campo `healthy` (true se server vivo + Ollama/cloud raggiungibili).
    async _serverHealth(req, res) {
        try {
            const dash = await this._statusDashboardRaw();
            const up = Date.now() - (this._startedAt || Date.now());
            const ok = dash && dash.server === true &&
                       (dash.engines && (dash.engines.local || dash.engines.cloud));
            this._json(res, { healthy: !!ok, uptimeMs: up, pid: process.pid, dashboard: dash });
        } catch (e) {
            this._json(res, { healthy: false, error: e.message }, 500);
        }
    }

    // Ultimi N righe del log su file (tail). N da query ?n= (default 200, max 2000).
    _serverLogs(req, res) {
        let n = 200;
        try { const q = new URL(req.url, "http://x"); const v = parseInt(q.searchParams.get("n") || "200", 10); if (v > 0 && v <= 2000) n = v; } catch (_) {}
        let lines = [];
        try { const txt = fs.readFileSync(this._logFile || "", "utf8"); lines = txt.split("\n"); } catch (_) {}
        lines = lines.filter(Boolean).slice(-n);
        this._json(res, { file: this._logFile, lines: lines.length, tail: lines.join("\n") });
    }

    // RIAVVIO PULITO del server: spawna una nuova istanza (lo stesso ingresso
    // heal-and-run.js, detached), chiude le connessioni SSE, libera la porta e
    // fa exit. Il VBS di autostart non serve (siamo già vivi): il nuovo processo
    // prende la 8790 e resta su. ⚠️ Le sessioni SSE aperte vanno ricaricate
    // (Developer: Reload Window / pull-to-refresh sul telefono).
    _serverRestart(req, res) {
        try {
            const { spawn } = require("child_process");
            const entry = require("path").join(__dirname, "heal-and-run.js");
            // Scrivi subito la risposta: dopo l'exit non potremmo più farlo.
            this._json(res, { ok: true, restarting: true, pid: process.pid, spawned: entry });
            this.logger.log && this.logger.log("[MobileServer] riavvio richiesto da /server/restart → spawn " + entry);
            try { spawn(process.execPath, [entry], { detached: true, stdio: "ignore", windowsHide: true }).unref(); } catch (e) { /* ripiego: il VBS riprenderà */ }
            // Dai 1s al nuovo processo per agganciare la porta, poi esci.
            const srv = this;
            setTimeout(() => {
                try { srv.stop(); } catch (_) {}
                try { process.exit(0); } catch (_) {}
            }, 1000);
        } catch (e) {
            this._json(res, { ok: false, error: e.message }, 500);
        }
    }

    // STOP/START dei motori pesanti (Ollama + ComfyUI) da remoto (telefono):
    // libera la VRAM quando non servono. action=stop | start (default stop).
    // Su Windows usa taskkill (no distruttivo: solo i NOSTRI processi).
    async _serverEngines(req, res) {
        // 2026-08-31 - PRIMA: qualunque GET nudo a /server/engines valeva "stop" e
        // ammazzava Ollama (taskkill /F). Bastava aprire l'indirizzo per sbaglio, o
        // un controllo di stato, per spegnere il motore sotto ai piedi dell'agente.
        // Ora l'azione va CHIESTA: senza action= si risponde solo con lo stato.
        const m = /(?:\?|&)action=(start|stop|status)/i.exec(req.url || "");
        const action = m ? m[1].toLowerCase() : "status";
        if (action === "status") {
            const { execSync } = require("child_process");
            let ollamaUp = false;
            try { ollamaUp = /ollama\.exe/i.test(execSync("tasklist /FI \"IMAGENAME eq ollama.exe\"", { windowsHide: true }).toString()); } catch (_) {}
            return this._json(res, {
                ok: true, action: "status", ollama: ollamaUp,
                note: "Sola lettura. Per agire servono ?action=start oppure ?action=stop (stop ferma Ollama e ComfyUI)."
            });
        }
        try {
            const { execSync } = require("child_process");
            if (action === "stop") {
                // Ferma SOLO i processi che noi stessi avviamo (ollama, comfy python).
                try { execSync("taskkill /IM ollama.exe /F", { windowsHide: true }); } catch (_) {}
                try { execSync("taskkill /FI \"WINDOWTITLE eq ComfyUI*\" /F", { windowsHide: true }); } catch (_) {}
                this._json(res, { ok: true, action: "stop", engines: ["ollama", "comfy"], note: "fermati. Riavviali da VS Code o con action=start." });
            } else {
                const os = require("os"), pth = require("path"), fss = require("fs");
                const exe = pth.join(os.homedir(), "AppData", "Local", "Programs", "Ollama", "ollama.exe");
                if (fss.existsSync(exe)) spawn(exe, ["serve"], { detached: true, stdio: "ignore", windowsHide: true }).unref();
                this._json(res, { ok: true, action: "start", engines: ["ollama"], note: "Ollama avviato. ComfyUI si accende da solo alla prima generazione." });
            }
        } catch (e) {
            this._json(res, { ok: false, error: e.message }, 500);
        }
    }

    async _systemToggle(req, res) {
        try {
            const b = await this._body(req);
            const comp = String(b.component || "").trim();
            const enabled = !!b.enabled;
            const allowed = ["discovery", "fileWatcher", "bugHunter"];
            if (!allowed.includes(comp)) {
                return this._json(res, { ok: false, error: "componente non valido: " + comp + ". Usa: " + allowed.join(", ") }, 400);
            }
            const prev = this._components[comp];
            this._components[comp] = enabled;
            if (comp === "discovery") {
                if (enabled && !this._discoveryStarted) {
                    this._startDiscoveryIfNeeded();
                }
                return this._json(res, { ok: true, component: comp, enabled, action: enabled ? "started" : "stopped" });
            }
            if (comp === "fileWatcher") {
                if (enabled) {
                    if (!this._fileWatcherInstance) {
                        try {
                            const { start } = require("./fileWatcher");
                            start();
                            this._fileWatcherInstance = true;
                        } catch (_) { this._components.fileWatcher = false; return this._json(res, { ok: false, error: "fileWatcher non disponibile" }, 500); }
                    }
                } else {
                    this._fileWatcherInstance = null;
                }
                return this._json(res, { ok: true, component: comp, enabled, action: enabled ? "started" : "stopped" });
            }
            if (comp === "bugHunter") {
                if (enabled) {
                    if (!this._bugHunterInstance) {
                        try {
                            this._bugHunterInstance = require("./bugHunter");
                        } catch (_) { this._components.bugHunter = false; return this._json(res, { ok: false, error: "bugHunter non disponibile" }, 500); }
                    }
                } else {
                    this._bugHunterInstance = null;
                }
                return this._json(res, { ok: true, component: comp, enabled, action: enabled ? "enabled" : "disabled", note: "Per avviare la scansione: POST /bugHunter/scan" });
            }
            return this._json(res, { ok: true, component: comp, enabled });
        } catch (e) {
            return this._json(res, { ok: false, error: e.message }, 500);
        }
    }

    async _statusDashboardRaw() {
        // Versione "cruda" di _statusDashboard (senza req/res) riusabile da health.
        const o = this.orchestrator || {};
        const out = { server: true, time: new Date().toISOString(), engines: {}, kaggle: null, tor: null, keys_configured: 0, models_local: 0, nous: false };
        try { out.engines.local = !!(await o.isOnline && o.isOnline().catch(() => false)); } catch (_) { out.engines.local = false; }
        try { out.engines.cloud = !!(o.cloudConfigured && o.cloudConfigured()); } catch (_) { out.engines.cloud = false; }
        try { const ms = o.engine && o.engine.getModels ? o.engine.getModels() : []; out.models_local = Array.isArray(ms) ? ms.length : 0; } catch (_) { out.models_local = 0; }
        try { out.nous = !!(o.nous && o.nous.available && o.nous.available()); } catch (_) { out.nous = false; }
        try { out.kaggle = status ? (await status()) : null; } catch (_) { out.kaggle = null; }
        try { out.tor = (this.tor && this.tor.available && this.tor.available()) ? "installed" : (TorBrowser ? "missing" : "n/a"); } catch (_) { out.tor = null; }
        try {
            const cloud = o.cloud;
            if (cloud && cloud.listKnownProviders) {
                const provs = cloud.listKnownProviders();
                out.keys_configured = Array.isArray(provs) ? provs.filter(p => p.configured).length : 0;
            }
        } catch (_) {}
        try { out.providers = this._statoProvider(out); } catch (_) { out.providers = null; }
        return out;
    }

    /**
     * ★ 2026-08-31 — PRONTO oppure NO, detto prima di premere.
     *
     * La tendina dei provider elencava sei voci tutte uguali, come se fossero
     * tutte pronte. Non lo erano: ComfyUI puo' essere spento, Kaggle idem, il
     * Cloud senza chiavi non va da nessuna parte. Uno strumento professionale
     * non promette quello che non puo' fare: qui ogni voce dice se e' pronta e,
     * se non lo e', perche'. Il controllo e' sui FATTI (file, porte, chiavi), non
     * su un elenco scritto a mano che invecchia.
     */
    _statoProvider(dash) {
        const fs2 = require("fs");
        const esiste = (p) => { try { return fs2.existsSync(p); } catch (_) { return false; } };
        const home = require("os").homedir();
        const path2 = require("path");

        const ghidra = ["C:/Program Files", home].some(base => {
            try { return fs2.readdirSync(base).some(n => /^ghidra[_-]/i.test(n)); } catch (_) { return false; }
        });
        const zw3d = esiste("C:/Program Files/ZWSOFT/ZW3D 2025/api/inc");
        // Per ComfyUI NON si indovina il percorso: si chiede a chi lo sa gia'
        // (comfyClient.installed(), che controlla il suo python e main.py).
        // Una risposta inventata qui varrebbe meno di nessuna risposta.
        const comfy = (() => {
            try {
                const { ComfyClient } = require("./comfyClient");
                const c = this.orchestrator && this.orchestrator.comfy;
                if (c && typeof c.installed === "function") return !!c.installed();
                if (ComfyClient) return !!new ComfyClient().installed();
                return false;
            } catch (_) { return false; }
        })();

        return {
            local: dash.models_local > 0
                ? { pronto: true }
                : { pronto: false, motivo: "Ollama non ha modelli installati" },
            cloud: dash.keys_configured > 0
                ? { pronto: true }
                : { pronto: false, motivo: "nessuna chiave API configurata (pannello 🔑)" },
            ghidra: ghidra
                ? { pronto: true }
                : { pronto: false, motivo: "Ghidra non trovato in Programmi" },
            zw3d: zw3d
                ? { pronto: true }
                : { pronto: false, motivo: "SDK ZW3D 2025 non trovato" },
            maintenance: { pronto: true },
            comfy: comfy
                ? { pronto: true, motivo: "si accende alla prima immagine" }
                : { pronto: false, motivo: "ComfyUI non installato" }
        };
    }

    async _approve(req, res) {
        const body = await this._body(req);
        this.orchestrator.resolveApproval(body.id, !!body.approved);
        // Eco a TUTTI i client: il riquadro di approvazione sparisce su entrambi i
        // device (telefono + VS Code), non solo su quello che ha cliccato.
        this._broadcast({ type: "approvalResolved", id: body.id, approved: !!body.approved });
        this._json(res, { ok: true });
    }

    // Pulisce SOLO la vista su tutti i device: i messaggi restano nella
    // conversazione (memoria intatta, il modello continua a ricordarli), ma da qui
    // in poi non vengono più disegnati finché non si azzera del tutto la chat.
    _clearView(res) {
        const active = this._active();
        active.clearedIndex = active.messages.length;
        this._saveConversations();
        this._broadcast({ type: "clearView" });
        this._json(res, { ok: true });
    }

    async _policy(req, res) {
        const body = await this._body(req);
        this.orchestrator.setPermissionPolicy(body.policy);
        this._json(res, { ok: true, policy: this.orchestrator.permissionPolicy });
    }

    // ---- helpers -----------------------------------------------------------

    _body(req) {
        return new Promise((resolve) => {
            let d = "";
            req.on("data", c => { d += c; if (d.length > 2e6) req.destroy(); });
            req.on("end", () => { try { resolve(JSON.parse(d || "{}")); } catch (_) { resolve({}); } });
            req.on("error", () => resolve({}));
        });
    }

    _json(res, obj, code = 200) {
        res.writeHead(code, { "Content-Type": "application/json" });
        res.end(JSON.stringify(obj));
    }
}


module.exports = { MobileServer, DEFAULT_PORT };

// Avvio standalone: node src/mobileServer.js
if (require.main === module) {
    const srv = new MobileServer({ rootDir: path.join(__dirname, "..") });
    srv.start().then(({ urls, token }) => {
        console.log("\n=== Server mobile Antigravity avviato ===");
        console.log("TOKEN:", token);
        console.log("Apri sul telefono uno di questi URL:");
        for (const u of urls) console.log("  " + u);
        console.log("(serve Ollama acceso; Ctrl+C per fermare)\n");
    }).catch(err => {
        console.error("Avvio fallito:", err.message);
        process.exit(1);
    });
}
