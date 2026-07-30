"use strict";

// torBrowser.js — "lettore" Tor integrato nell'app.
//
// COS'È: il SERVER (sul PC) fa da client Tor. Scarica le pagine .onion/clearnet
// attraverso il proxy SOCKS di Tor (127.0.0.1:9050), le RIPULISCE e le manda
// all'app. Il telefono/VS Code non parla mai con Tor: vede solo HTML già pulito.
//
// PERCHÉ COSÌ (e non il vero Tor Browser in un iframe): Tor Browser è Firefox,
// non è incorporabile; e Safari non sa risolvere .onion. Facendolo lato server
// si ottiene un vantaggio di SICUREZZA enorme:
//   - niente JavaScript dei siti (rimosso): niente exploit del browser
//   - niente risorse esterne caricate dal telefono (rimosse/riproxate): un
//     <img>/<script> verso la clearnet, caricato da Safari, RIVELEREBBE il tuo
//     IP vero (deanonimizzazione). Qui non può succedere: tutto passa da Tor.
//   - niente download eseguibili: il server prende solo testo/immagini.
//
// LIMITE ONESTO: è un LETTORE. I siti pieni di JavaScript non funzioneranno
// come in un browser vero. La gran parte dei .onion è HTML semplice e si legge
// bene. I link restano navigabili (reindirizzati di nuovo dentro Tor).

const { spawn, spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");

const TOR_DIR = path.join(os.homedir(), "tor-bundle");
const TOR_EXE = path.join(TOR_DIR, "tor", "tor.exe");
const TOR_LOG = path.join(TOR_DIR, "tor-log.txt");
const SOCKS = "127.0.0.1:9050";
// curl di Windows (C:\Windows\System32\curl.exe) parla SOCKS5 nativo: zero
// dipendenze npm, stessa filosofia del resto del progetto.
const CURL = process.env.SystemRoot ? path.join(process.env.SystemRoot, "System32", "curl.exe") : "curl";

class TorBrowser {
    constructor(logger = console) {
        this.logger = logger;
        this.proc = null;
        this._starting = null;
    }

    available() { return fs.existsSync(TOR_EXE); }

    /** true se il proxy SOCKS risponde (Tor è su e connesso). */
    isUp() {
        try {
            // -x SOCKS, chiediamo l'endpoint di conferma di Tor: se risponde, siamo dentro.
            const r = spawnSync(CURL, ["-s", "--max-time", "8", "--socks5-hostname", SOCKS,
                "https://check.torproject.org/api/ip"], { encoding: "utf8", windowsHide: true });
            return /"IsTor"\s*:\s*true/.test(r.stdout || "");
        } catch (_) { return false; }
    }

    /**
     * Garantisce che Tor sia avviato e connesso. Se già su, ritorna subito.
     * Avvia tor.exe (nascosto) e aspetta il bootstrap 100% leggendo il log.
     */
    async ensureRunning(onStatus = () => {}) {
        if (!this.available()) throw new Error("Tor non è installato (manca " + TOR_EXE + ").");
        if (this.isUp()) return true;
        if (this._starting) return this._starting;

        this._starting = (async () => {
            onStatus("🧅 Avvio Tor…");
            try { fs.writeFileSync(TOR_LOG, ""); } catch (_) {}
            const p = spawn(TOR_EXE, [], { cwd: path.join(TOR_DIR, "tor"), windowsHide: true, detached: true, stdio: ["ignore", fs.openSync(TOR_LOG, "a"), "ignore"] });
            p.unref();
            this.proc = p;
            // aspetta il bootstrap (max ~60s)
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 2000));
                let log = ""; try { log = fs.readFileSync(TOR_LOG, "utf8"); } catch (_) {}
                const m = /Bootstrapped (\d+)%/.exec(log.split("\n").reverse().find(l => /Bootstrapped/.test(l)) || "");
                if (m) onStatus(`🧅 Tor: connessione ${m[1]}%`);
                if (/Bootstrapped 100%/.test(log)) { onStatus("🧅 Tor connesso."); this._starting = null; return true; }
            }
            this._starting = null;
            throw new Error("Tor non ha completato la connessione in tempo. Riprova tra poco.");
        })();
        return this._starting;
    }

    /**
     * Scarica una URL attraverso Tor. Ritorna { ok, status, contentType, body(Buffer) }.
     * Nessuna dipendenza: usa curl con SOCKS5.
     */
    fetch(url, { maxTime = 45, binary = false } = {}) {
        return new Promise((resolve) => {
            const args = ["-s", "-L", "--max-redirs", "5", "--max-time", String(maxTime),
                "--socks5-hostname", SOCKS,
                "-A", "Mozilla/5.0 (Windows NT 10.0; rv:128.0) Gecko/20100101 Firefox/128.0",
                "-w", "\n__HTTP__%{http_code}__CT__%{content_type}__", url];
            const chunks = [];
            const c = spawn(CURL, args, { windowsHide: true });
            c.stdout.on("data", d => chunks.push(d));
            c.on("error", e => resolve({ ok: false, status: 0, error: e.message }));
            c.on("close", () => {
                const buf = Buffer.concat(chunks);
                // la coda "\n__HTTP__200__CT__text/html__" porta stato e content-type
                const s = buf.toString("latin1");
                const mk = s.lastIndexOf("\n__HTTP__");
                let status = 0, contentType = "";
                if (mk >= 0) {
                    const tail = s.slice(mk + 1);
                    const m = /__HTTP__(\d+)__CT__([^_]*)__/.exec(tail);
                    if (m) { status = parseInt(m[1], 10); contentType = m[2].trim(); }
                }
                const body = mk >= 0 ? buf.subarray(0, mk) : buf;
                resolve({ ok: status >= 200 && status < 400, status, contentType, body });
            });
        });
    }

    /** Normalizza una URL relativa/assoluta rispetto alla pagina corrente. */
    static resolveUrl(href, base) {
        try { return new URL(href, base).href; } catch (_) { return null; }
    }

    /**
     * PRE-ANALISI DEL RISCHIO (richiesta utente): guarda l'HTML GREZZO della pagina
     * PRIMA di mostrarla e segnala i pericoli. NON è un antivirus: è un semaforo che
     * ti avvisa su cosa c'è nel codice della pagina e nei download, così decidi tu.
     * @returns {{level:'ok'|'attenzione'|'pericolo', warnings:string[]}}
     */
    static analyzeRisk(rawHtml, url) {
        const h = String(rawHtml || "");
        const low = h.toLowerCase();
        const w = [];
        let danger = 0;

        // 1) DOWNLOAD di eseguibili: il vettore d'infezione n°1.
        const dlRx = /href\s*=\s*["']([^"']+\.(exe|scr|bat|cmd|com|msi|apk|jar|dll|ps1|vbs|zip|rar|7z|iso|img))(\?[^"']*)?["']/gi;
        const downloads = new Set(); let m;
        while ((m = dlRx.exec(h)) && downloads.size < 12) downloads.add(m[1]);
        if (downloads.size) { danger += 2; w.push("⛔ DOWNLOAD ESEGUIBILI nella pagina (" + downloads.size + "): " + [...downloads].slice(0, 3).map(s => s.split("/").pop()).join(", ") + (downloads.size > 3 ? "…" : "") + ". NON scaricarli/aprirli fuori dalla sandbox."); }

        // 2) Moduli che chiedono CREDENZIALI/pagamenti (phishing).
        if (/<input[^>]+type\s*=\s*["']?password/i.test(h)) { danger += 1; w.push("🔐 La pagina chiede una PASSWORD: non inserire MAI credenziali vere sui siti .onion."); }
        if (/\b(cvv|card\s*number|numero\s*carta|seed\s*phrase|private\s*key|chiave\s*privata|frase\s*seme)\b/i.test(low)) { danger += 2; w.push("💳 Chiede DATI SENSIBILI (carta/chiavi/seed): segnale forte di TRUFFA. Non inserire nulla."); }

        // 3) Wallet crypto in chiaro (mercati/estorsioni/truffe).
        if (/\b(bc1|[13])[a-hj-np-z0-9]{25,39}\b/i.test(h) || /\b4[0-9ab][0-9a-z]{93}\b/i.test(low)) { danger += 1; w.push("₿ Indirizzi di WALLET (Bitcoin/Monero) nella pagina: tipico di mercati/estorsioni/truffe. Nessun pagamento è recuperabile."); }

        // 4) JavaScript (nel lettore è disattivato, ma segnala se la pagina ne è piena).
        const scripts = (h.match(/<script\b/gi) || []).length;
        if (scripts >= 8) { w.push("⚙️ Pagina molto ricca di JavaScript (" + scripts + " script): nel lettore è disattivato (sicuro), ma potrebbe non vedersi bene. Per usarla davvero serve la sandbox."); }
        if (/eval\(|atob\(|unescape\(|fromCharCode|\\x[0-9a-f]{2}/i.test(h)) { danger += 1; w.push("🧬 Codice JavaScript OFFUSCATO (eval/atob/hex): spesso nasconde qualcosa. Il lettore non lo esegue."); }

        // 5) Redirect automatici.
        if (/<meta[^>]+http-equiv\s*=\s*["']?refresh/i.test(h)) { w.push("↪️ La pagina fa un REDIRECT automatico: potrebbe portarti altrove."); }

        // 6) Parole-spia di contenuti illegali/mercati (informative, non blocco).
        const flags = ["carding", "cvv dump", "counterfeit", "stolen", "hacked account", "drugs", "escrow", "market", "vendor"];
        const hit = flags.filter(f => low.includes(f));
        if (hit.length >= 2) { w.push("⚠️ La pagina contiene termini da MERCATO/illecito (" + hit.slice(0, 3).join(", ") + "): occhio a truffe ed esche."); }

        const level = danger >= 2 ? "pericolo" : (danger === 1 || w.length ? "attenzione" : "ok");
        return { level, warnings: w };
    }

    /**
     * Ripulisce l'HTML: toglie tutto ciò che è pericoloso o che potrebbe
     * deanonimizzare, e riscrive i link perché restino dentro Tor.
     * @param html stringa
     * @param baseUrl la URL della pagina (per risolvere i link relativi)
     * @param token il token dell'app (per il proxy delle immagini)
     */
    static sanitize(html, baseUrl, token) {
        let h = String(html);

        // 1) via gli elementi ATTIVI o che caricano risorse esterne (leak IP/exploit).
        h = h.replace(/<script\b[\s\S]*?<\/script>/gi, "");
        h = h.replace(/<style\b[\s\S]*?<\/style>/gi, "");
        h = h.replace(/<link\b[^>]*>/gi, "");
        h = h.replace(/<iframe\b[\s\S]*?<\/iframe>/gi, "");
        h = h.replace(/<(object|embed|video|audio|source|track|applet|form)\b[\s\S]*?<\/\1>/gi, "");
        h = h.replace(/<(object|embed|source|input|button|base|meta)\b[^>]*>/gi, "");
        // gestori inline on*="..." e javascript:
        h = h.replace(/\son\w+\s*=\s*"[^"]*"/gi, "").replace(/\son\w+\s*=\s*'[^']*'/gi, "");
        h = h.replace(/\son\w+\s*=\s*[^\s>]+/gi, "");
        h = h.replace(/href\s*=\s*(['"])\s*javascript:[^'"]*\1/gi, 'href="#"');

        // 2) IMMAGINI: riproxate attraverso Tor (raw), così le vedi senza che
        //    il telefono contatti direttamente nessun server.
        const tok = encodeURIComponent(token || "");
        h = h.replace(/<img\b([^>]*?)\ssrc\s*=\s*(['"])([^'"]+)\2([^>]*)>/gi, (m, pre, q, src, post) => {
            const abs = TorBrowser.resolveUrl(src, baseUrl);
            if (!abs || /^data:/i.test(src)) return `<img${pre} src="${src}"${post}>`;
            return `<img${pre} src="/tor/raw?u=${encodeURIComponent(abs)}&t=${tok}" loading="lazy"${post}>`;
        });
        // srcset non lo sappiamo riproxare bene → via
        h = h.replace(/\ssrcset\s*=\s*"[^"]*"/gi, "");

        // 3) LINK: niente navigazione diretta di Safari (romperebbe l'anonimato).
        //    Togliamo href e mettiamo data-tor-url: l'app intercetta il clic e
        //    riapre la pagina DENTRO Tor.
        h = h.replace(/<a\b([^>]*?)\shref\s*=\s*(['"])([^'"]+)\2([^>]*)>/gi, (m, pre, q, href, post) => {
            if (/^#/.test(href)) return m;                         // ancore interne: lasciale
            const abs = TorBrowser.resolveUrl(href, baseUrl);
            if (!abs) return `<a${pre}${post}>`;
            return `<a${pre} data-tor-url="${abs.replace(/"/g, "&quot;")}" href="#"${post}>`;
        });

        // 4) via i <base> e gli attributi che forzano risorse
        h = h.replace(/\s(background|poster|data-src)\s*=\s*"[^"]*"/gi, "");

        return h;
    }
}

module.exports = { TorBrowser, TOR_EXE, SOCKS };
