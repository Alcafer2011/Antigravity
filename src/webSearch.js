"use strict";

const https = require("https");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");

/**
 * webSearch — ricerca online e lettura di pagine. Serve all'agente (cercare API,
 * codici errore, documentazione) e ai "cacciatori" di Efesto.
 *
 * ★★ RISCRITTO IL 2026-07-26, PERCHÉ NON FUNZIONAVA PIÙ.
 * La versione precedente raschiava l'endpoint HTML di DuckDuckGo. Oggi non passa:
 * misurato dal vivo, `html.duckduckgo.com` risponde **HTTP 202 con una pagina
 * anti-bot** e zero risultati. Provati anche lite.duckduckgo, Mojeek, Bing, Brave,
 * Startpage, searx.be, Ecosia: **bloccano tutti** lo scraping (202/403/429 o markup
 * senza risultati). Quindi lo scraping è una strada morta, non un dettaglio da
 * aggiustare.
 *
 * Le due strade che FUNZIONANO davvero su questa macchina, con le chiavi che
 * l'utente ha già nel .env:
 *   1) **GitHub Search API** (GITHUB_TOKEN) — per repository, plugin, codice.
 *      Deterministica, veloce, nessun HTML da interpretare.
 *   2) **Gemini + grounding Google** (GEMINI_API_KEY / GOOGLE_API_KEY) — vera
 *      ricerca sul web: il modello cerca e restituisce le CITAZIONI, cioè URL reali.
 * Lo scraping DuckDuckGo resta solo come ultimo tentativo, nel caso un giorno riapra.
 *
 * `search()` prova le fonti in ordine e ritorna la prima che dà risultati, così
 * chi la chiama non deve sapere niente di tutto questo.
 */

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36";

// ── chiavi ───────────────────────────────────────────────────────────────────
// Si leggono da process.env; se non c'è nulla, dal .env dell'applicazione (Efesto
// lo ha in EfestoAI\.env, Antigravity in C:\Users\infoa\.env — un livello sopra src\).
let _env = null;
function env(nome) {
    if (process.env[nome]) return process.env[nome];
    if (!_env) {
        _env = {};
        for (const c of [path.join(__dirname, "..", ".env"), path.join(__dirname, ".env")]) {
            try {
                for (const riga of fs.readFileSync(c, "utf8").split(/\r?\n/)) {
                    const m = riga.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/);
                    if (m && !_env[m[1]]) _env[m[1]] = m[2].trim();
                }
                break;
            } catch (_) {}
        }
    }
    return _env[nome] || "";
}

// ── HTTP di servizio ─────────────────────────────────────────────────────────
function httpGet(urlStr, { headers = {}, timeout = 15000, maxLen = 600000, redirects = 4 } = {}) {
    return new Promise((resolve, reject) => {
        let u;
        try { u = new URL(urlStr); } catch (e) { return reject(e); }
        const req = https.request({
            host: u.hostname, path: u.pathname + u.search, method: "GET",
            headers: Object.assign({ "User-Agent": UA, "Accept": "text/html,application/xhtml+xml" }, headers)
        }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && redirects > 0) {
                res.resume();
                const next = res.headers.location.startsWith("http") ? res.headers.location : u.origin + res.headers.location;
                return resolve(httpGet(next, { headers, timeout, maxLen, redirects: redirects - 1 }));
            }
            let data = "";
            res.setEncoding("utf8");
            res.on("data", c => { data += c; if (data.length > maxLen) { req.destroy(); } });
            res.on("end", () => resolve({ status: res.statusCode, body: data }));
        });
        req.setTimeout(timeout, () => req.destroy(new Error("timeout")));
        req.on("error", reject);
        req.end();
    });
}

function httpJson(opt, body) {
    return new Promise((resolve, reject) => {
        const r = https.request(opt, (x) => {
            let b = "";
            x.setEncoding("utf8");
            x.on("data", c => { b += c; if (b.length > 2000000) x.destroy(); });
            x.on("end", () => {
                try { resolve({ status: x.statusCode, json: JSON.parse(b || "{}") }); }
                catch (e) { resolve({ status: x.statusCode, json: null, raw: b }); }
            });
        });
        r.setTimeout(30000, () => r.destroy(new Error("timeout")));
        r.on("error", reject);
        if (body) r.write(body);
        r.end();
    });
}

function decodeEntities(s) {
    return String(s)
        .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'").replace(/&nbsp;/g, " ")
        .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(parseInt(n, 10)));
}
function stripTags(html) { return decodeEntities(String(html).replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim(); }

// ── 1) GitHub ────────────────────────────────────────────────────────────────
/**
 * Cerca repository su GitHub. Toglie dalla query gli operatori da motore di
 * ricerca (`site:github.com`, virgolette) che a GitHub non servono e che
 * anzi azzererebbero i risultati.
 */
async function searchGitHub(query, limit = 8) {
    const q = String(query || "")
        .replace(/site:\s*github\.com/gi, "")
        .replace(/["']/g, "")
        .trim();
    if (!q) return [];
    const tok = env("GITHUB_TOKEN");
    const headers = { "User-Agent": "EfestoAI", "Accept": "application/vnd.github+json" };
    if (tok) headers["Authorization"] = "Bearer " + tok;
    const { json } = await httpJson({
        host: "api.github.com",
        path: "/search/repositories?q=" + encodeURIComponent(q) + "&sort=stars&order=desc&per_page=" + Math.min(limit, 20),
        method: "GET", headers
    });
    if (!json || !Array.isArray(json.items)) return [];
    return json.items.slice(0, limit).map(i => ({
        title: i.full_name + (i.stargazers_count ? "  ★" + i.stargazers_count : ""),
        url: i.html_url,
        snippet: (i.description || "") + (i.language ? "  [" + i.language + "]" : ""),
        fonte: "github"
    }));
}

/**
 * Segue UN redirect e ritorna l'indirizzo di destinazione (senza scaricare la
 * pagina). Se non risponde o non è un redirect, torna l'URL di partenza: meglio
 * un link brutto che nessun link.
 */
function risolviRedirect(urlStr, timeout = 7000) {
    return new Promise((resolve) => {
        let u;
        try { u = new URL(urlStr); } catch (_) { return resolve(urlStr); }
        const req = https.request({
            host: u.hostname, path: u.pathname + u.search, method: "HEAD",
            headers: { "User-Agent": UA }
        }, (res) => {
            res.resume();
            const loc = res.headers.location;
            resolve(loc && /^https?:\/\//.test(loc) ? loc : urlStr);
        });
        req.setTimeout(timeout, () => { req.destroy(); resolve(urlStr); });
        req.on("error", () => resolve(urlStr));
        req.end();
    });
}

/** Risolve in parallelo i redirect di una lista di risultati e ne pulisce il titolo. */
async function risolviTutti(risultati) {
    const veri = await Promise.all(risultati.map(async (r) => {
        if (!/vertexaisearch\.cloud\.google\.com|grounding-api-redirect/.test(r.url)) return r;
        const vero = await risolviRedirect(r.url);
        let host = "";
        try { host = new URL(vero).hostname.replace(/^www\./, ""); } catch (_) {}
        return Object.assign({}, r, { url: vero, title: r.title && r.title !== "risultato" ? r.title : (host || r.title) });
    }));
    // via i doppioni (spesso la stessa pagina è citata più volte)
    const visti = new Set(), out = [];
    for (const r of veri) {
        const k = String(r.url).replace(/[#?].*$/, "");
        if (visti.has(k)) continue;
        visti.add(k);
        out.push(r);
    }
    return out;
}

// ── 2) Gemini con grounding Google ───────────────────────────────────────────
/**
 * Vera ricerca sul web: si chiede a Gemini di cercare, con lo strumento
 * `google_search` attivo. Nella risposta arrivano le CITAZIONI (groundingChunks),
 * cioè le pagine davvero consultate: quelle diventano i nostri risultati.
 * Ritorna { risultati:[…], sintesi:"…" } — la sintesi è gratis, l'ha già scritta.
 */
async function searchGrounded(query, limit = 8) {
    const chiave = env("GEMINI_API_KEY") || env("GOOGLE_API_KEY");
    if (!chiave) return { risultati: [], sintesi: "" };
    const q = String(query || "").trim();
    if (!q) return { risultati: [], sintesi: "" };

    const payload = JSON.stringify({
        contents: [{ parts: [{ text: "Cerca online e rispondi in italiano, conciso: " + q + "\nElenca i risultati utili con nome e indirizzo." }] }],
        tools: [{ google_search: {} }]
    });

    // Più modelli in cascata: i nomi cambiano nel tempo, il primo che risponde vince.
    for (const modello of ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]) {
        try {
            const { json } = await httpJson({
                host: "generativelanguage.googleapis.com",
                path: "/v1beta/models/" + modello + ":generateContent?key=" + chiave,
                method: "POST",
                headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(payload) }
            }, payload);
            if (!json || json.error) continue;
            const c = (json.candidates || [])[0];
            if (!c) continue;
            const sintesi = ((c.content && c.content.parts) || []).map(p => p.text || "").join("").trim();
            const chunks = (c.groundingMetadata && c.groundingMetadata.groundingChunks) || [];
            let risultati = chunks.slice(0, limit).map(k => ({
                title: (k.web && (k.web.title || k.web.domain)) || "risultato",
                url: (k.web && k.web.uri) || "",
                snippet: "",
                fonte: "google"
            })).filter(r => r.url);
            // Gli URL di grounding sono redirect (vertexaisearch...): illeggibili e
            // inutili da mostrare. Li seguiamo per ricavare l'indirizzo VERO.
            risultati = await risolviTutti(risultati);
            if (risultati.length || sintesi) return { risultati, sintesi };
        } catch (_) { /* provo il modello successivo */ }
    }
    return { risultati: [], sintesi: "" };
}

// ── 3) DuckDuckGo (ultimo tentativo: oggi risponde 202 anti-bot) ─────────────
async function searchDdg(query, limit = 6) {
    const q = encodeURIComponent(String(query || "").trim());
    if (!q) return [];
    let body = "";
    try { ({ body } = await httpGet("https://html.duckduckgo.com/html/?q=" + q, { headers: { "Accept-Language": "it,en" } })); }
    catch (_) { return []; }
    const results = [];
    const re = /<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g;
    let m;
    while ((m = re.exec(body)) && results.length < limit) {
        let href = decodeEntities(m[1]);
        const uddg = href.match(/[?&]uddg=([^&]+)/);
        if (uddg) href = decodeURIComponent(uddg[1]);
        if (href.startsWith("//")) href = "https:" + href;
        const after = body.slice(m.index, m.index + 1200);
        const sn = after.match(/class="result__snippet"[^>]*>([\s\S]*?)<\/a>/);
        results.push({ title: stripTags(m[2]), url: href, snippet: sn ? stripTags(sn[1]).slice(0, 300) : "", fonte: "duckduckgo" });
    }
    return results;
}

// ── API pubblica ─────────────────────────────────────────────────────────────
/**
 * Ricerca web. Ritorna [{title, url, snippet, fonte}].
 * Ordine: se la query parla di GitHub/repo/plugin prima GitHub (è precisa), poi
 * il grounding Google, infine DuckDuckGo. Si ferma alla prima fonte che dà frutti.
 */
async function search(query, limit = 6) {
    const q = String(query || "").trim();
    if (!q) return [];
    const sembraCodice = /github|repo(sitory)?|plugin|add-?in|sdk|open ?source|libreria|library/i.test(q);

    const fonti = sembraCodice
        ? [() => searchGitHub(q, limit), async () => (await searchGrounded(q, limit)).risultati, () => searchDdg(q, limit)]
        : [async () => (await searchGrounded(q, limit)).risultati, () => searchGitHub(q, limit), () => searchDdg(q, limit)];

    for (const f of fonti) {
        try { const r = await f(); if (r && r.length) return r; } catch (_) {}
    }
    return [];
}

/** Scarica una pagina e ne estrae il TESTO leggibile (per l'agente). */
async function fetchPage(url, maxChars = 8000) {
    const { status, body } = await httpGet(url, { headers: { "Accept-Language": "it,en" } });
    if (status >= 400) return "ERRORE HTTP " + status + " su " + url;
    let txt = body
        .replace(/<script[\s\S]*?<\/script>/gi, " ")
        .replace(/<style[\s\S]*?<\/style>/gi, " ")
        .replace(/<!--[\s\S]*?-->/g, " ");
    const title = (txt.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [, ""])[1];
    txt = stripTags(txt);
    const head = title ? ("# " + stripTags(title) + "\n") : "";
    return (head + txt).slice(0, maxChars);
}

module.exports = { search, fetchPage, searchGitHub, searchGrounded, searchDdg };
