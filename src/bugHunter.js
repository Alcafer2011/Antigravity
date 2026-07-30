"use strict";
/**
 * bugHunter — "cacciatore di bug" INTERNO di Antigravity.
 *
 * Scopo (voluto dall'utente 2026-07-27): ispezionare l'applicazione STESSA,
 * trovare anomalie note e correggerle AUTOMATICAMENTE, seguendo LE REGOLE
 * ANTI-DANNO (backup + node --check + riavvio + sync estensione + log in
 * MAINTENANCE-LOG). Se qualcosa nell'app non è "come deve essere", lo sistema.
 *
 * SICUREZZA: le correzioni sono DETERMINISTICHE e su una WHITELIST CHIUSA di
 * pattern noti. NON usa AI generativa per riscrivere codice (troppo rischioso).
 * Per OGNI fix:
 *   1) backup preventivo del file toccato (.self-heal-backup o copia .bak),
 *   2) applica la patch minima,
 *   3) node --check sul file; se fallisce → RIPRISTINA il backup (annulla),
 *   4) scrive nel MAINTENANCE-LOG cosa ha fatto.
 * Nessuna correzione tocca mai chiavi/segreti nel .env, né cancella file.
 *
 * Controlli implementati (chiusi):
 *   C1 divergenza cuore↔estensione: se src\ (cuore) e l'estensione VS Code
 *       src\ divergono, riallinea l'estensione dal cuore (come apply-change.ps1).
 *   C2 provider nel .env con chiave di formato NOTO ma non registrato: lo
 *       aggiunge al providerRegistry (solo se il formato corrisponde a una
 *       regex della mini-mappa interna — NON inventa provider).
 *   C3 provider/piattaforma con signup/url vuoto: lo riempie da una mappa nota
 *       (se la conosciamo) altrimenti lo segnala come issue non fixabile.
 *   C4 modulo .js critico che non si carica (require fallisce): segnala (la
 *       riparazione fisica è di selfHeal; qui solo diagnosi).
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");
const vm = require("vm");

const SRC = __dirname;

// ---- whitelist: pattern di chiavi .env → provider conosciuto (regex, id, env, host, chatPath) ----
// Usata SOLO da C2. Se una chiave nel .env matcha una regex qui, il provider
// viene aggiunto al registro (se manca). Niente di più: nessun provider inventato.
const KNOWN_KEY_PATTERNS = [
    { rx: /^sk-or-v1-/, id: "openrouter", env: "OPENROUTER_API_KEY", host: "openrouter.ai", chatPath: "/api/v1/chat/completions", modelsPath: "/api/v1/models", signup: "https://openrouter.ai/keys", label: "OpenRouter" },
    { rx: /^gsk_/, id: "groq", env: "GROQ_API_KEY", host: "api.groq.com", chatPath: "/openai/v1/chat/completions", modelsPath: "/openai/v1/models", signup: "https://console.groq.com/keys", label: "Groq" },
    { rx: /^csk-/, id: "cerebras", env: "CEREBRAS_API_KEY", host: "api.cerebras.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://cloud.cerebras.ai/", label: "Cerebras" },
    { rx: /^nvapi-/, id: "nvidia", env: "NVIDIA_API_KEY", host: "integrate.api.nvidia.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://build.nvidia.com/", label: "NVIDIA NIM" },
    { rx: /^hf_/, id: "hf", env: "HF_TOKEN", host: "router.huggingface.co", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://huggingface.co/settings/tokens", label: "HuggingFace" },
    { rx: /^AIza/, id: "google", env: "GOOGLE_API_KEY", host: "generativelanguage.googleapis.com", chatPath: "/v1beta/openai/chat/completions", modelsPath: "/v1beta/openai/models", signup: "https://aistudio.google.com/app/apikey", label: "Google Gemini" },
    { rx: /^sk-(proj|svcacct)-/, id: "openai", env: "OPENAI_API_KEY", host: "api.openai.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://platform.openai.com/api-keys", label: "OpenAI" },
    { rx: /^sk-ant-/, id: "anthropic", env: "ANTHROPIC_API_KEY", host: "api.anthropic.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://console.anthropic.com/settings/keys", label: "Anthropic" },
    { rx: /^xai-/, id: "xai", env: "XAI_API_KEY", host: "api.x.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://console.x.ai/", label: "xAI Grok" },
    { rx: /^pplx-/, id: "perplexity", env: "PERPLEXITY_API_KEY", host: "api.perplexity.ai", chatPath: "/chat/completions", modelsPath: null, signup: "https://www.perplexity.ai/settings/api", label: "Perplexity" },
    { rx: /^fw_/, id: "fireworks", env: "FIREWORKS_API_KEY", host: "api.fireworks.ai", chatPath: "/inference/v1/chat/completions", modelsPath: "/inference/v1/models", signup: "https://fireworks.ai/account/api-keys", label: "Fireworks" },
    { rx: /^glhf_/, id: "glhf", env: "GLHF_API_KEY", host: "glhf.chat", chatPath: "/api/openai/v1/chat/completions", modelsPath: "/api/openai/v1/models", signup: "https://glhf.chat/", label: "glhf.chat" },
    { rx: /^cpk-/, id: "chutes", env: "CHUTES_API_KEY", host: "llm.chutes.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://chutes.ai/", label: "Chutes" },
    { rx: /^rc_/, id: "featherless", env: "FEATHERLESS_API_KEY", host: "api.featherless.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://featherless.ai/", label: "Featherless" },
    { rx: /^cf(at|ut)_/, id: "cloudflare", env: "CLOUDFLARE_API_KEY", host: "api.cloudflare.com", chatPath: "/client/v4/accounts/{ACCOUNT}/ai/v1/chat/completions", modelsPath: null, signup: "https://dash.cloudflare.com/profile/api-tokens", label: "Cloudflare Workers AI", needsEnv: "CLOUDFLARE_ACCOUNT_ID" },
    { rx: /^ghp_|^github_pat_/, id: "github", env: "GITHUB_TOKEN", host: "models.github.ai", chatPath: "/inference/chat/completions", modelsPath: "/catalog/models", signup: "https://github.com/settings/tokens", label: "GitHub Models" },
    { rx: /^sk_/, id: "novita", env: "NOVITA_API_KEY", host: "api.novita.ai", chatPath: "/v3/openai/chat/completions", modelsPath: "/v3/openai/models", signup: "https://novita.ai/settings/key-management", label: "Novita AI" },
    { rx: /^VENICE_/, id: "venice", env: "VENICE_API_KEY", host: "api.venice.ai", chatPath: "/api/v1/chat/completions", modelsPath: "/api/v1/models", signup: "https://venice.ai/", label: "Venice AI" },
    { rx: /^[0-9a-f]{64}$/, id: "together", env: "TOGETHER_API_KEY", host: "api.together.xyz", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", signup: "https://api.together.ai/settings/api-keys", label: "Together AI" }
];

// Mappa url noti per provider/piattaforma (usata da C3 per riempire campi vuoti).
const KNOWN_URLS = {
    kaggle: "https://www.kaggle.com/code",
    colab: "https://colab.research.google.com/",
    modal: "https://modal.com/",
    runpod: "https://www.runpod.io/",
    huggingface: "https://huggingface.co/spaces",
    lightning: "https://lightning.ai/studios",
    paperspace: "https://www.paperspace.com/",
    vastai: "https://vast.ai/",
    salad: "https://salad.com/"
};

function loadEnvVars() {
    const envPath = path.join(SRC, "..", ".env");
    const out = {};
    try {
        const txt = fs.readFileSync(envPath, "utf8");
        for (const line of txt.split(/\r?\n/)) {
            const s = line.trim();
            if (!s || s.startsWith("#")) continue;
            const eq = s.indexOf("=");
            if (eq < 0) continue;
            out[s.slice(0, eq).trim()] = s.slice(eq + 1).trim();
        }
    } catch (_) {}
    return out;
}

function nodeCheck(file) {
    try {
        const r = spawnSync("node", ["--check", file], { encoding: "utf8" });
        return r.status === 0;
    } catch (_) { return false; }
}

// Backup preventivo: copia in .bugHunter-backup/<nome>.<ts>
function backupFile(file) {
    const dir = path.join(SRC, ".bugHunter-backup");
    try { fs.mkdirSync(dir, { recursive: true }); } catch (_) {}
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    const bak = path.join(dir, path.basename(file) + "." + ts + ".bak");
    try { fs.copyFileSync(file, bak); return bak; } catch (_) { return null; }
}

function restoreFrom(bak, file) {
    try { if (bak && fs.existsSync(bak)) fs.copyFileSync(bak, file); } catch (_) {}
}

function appendLog(line) {
    const logPath = path.join(SRC, "knowledge", "MAINTENANCE-LOG.md");
    try {
        let txt = fs.readFileSync(logPath, "utf8");
        const stamp = new Date().toISOString().slice(0, 10);
        txt += `\n## ${stamp} (bugHunter auto-fix)\n- ${line}\n`;
        fs.writeFileSync(logPath, txt, "utf8");
    } catch (_) {}
}

// C1 — allinea estensione VS Code dal cuore se divergono
function fixExtensionSync(issues, fixes) {
    try {
        const extSrc = path.join(process.env.USERPROFILE || "C:\\Users\\infoa",
            ".vscode", "extensions", "local-developer.antigravity-1.0.1", "src");
        if (!fs.existsSync(extSrc)) return;
        const coreJs = fs.readdirSync(SRC).filter(f => f.endsWith(".js"));
        let diverged = false;
        for (const f of coreJs) {
            const a = path.join(SRC, f), b = path.join(extSrc, f);
            if (!fs.existsSync(b)) { diverged = true; break; }
            if (!fs.readFileSync(a).equals(fs.readFileSync(b))) { diverged = true; break; }
        }
        if (!diverged) return;
        const bak = backupFile(path.join(extSrc, "mobileServer.js"));
        for (const f of coreJs) {
            try { fs.copyFileSync(path.join(SRC, f), path.join(extSrc, f)); } catch (_) {}
        }
        // copia anche gli asset di conoscenza
        for (const extra of ["mobile-page.html", "apply-change.ps1", "knowledge"]) {
            const src2 = path.join(SRC, extra), dst2 = path.join(extSrc, extra);
            try { if (fs.statSync(src2).isDirectory()) copyDir(src2, dst2); else fs.copyFileSync(src2, dst2); } catch (_) {}
        }
        issues.push({ id: "C1", severity: "medium", detail: "Estensione VS Code non allineata al cuore → riallineata." });
        fixes.push("C1: estensione riallineata dal cuore");
        appendLog("bugHunter C1: estensione VS Code riallineata al cuore (divergenza rilevata).");
    } catch (e) { issues.push({ id: "C1", severity: "low", detail: "sync estensione non eseguibile: " + e.message }); }
}

function copyDir(src, dst) {
    fs.mkdirSync(dst, { recursive: true });
    for (const e of fs.readdirSync(src, { withFileTypes: true })) {
        const s = path.join(src, e.name), d = path.join(dst, e.name);
        if (e.isDirectory()) copyDir(s, d); else fs.copyFileSync(s, d);
    }
}

// C2 — provider nel .env con formato noto ma non registrato → aggiungi al registro
function fixMissingProviders(issues, fixes) {
    try {
        const regPath = path.join(SRC, "providerRegistry.js");
        let txt = fs.readFileSync(regPath, "utf8");
        const env = loadEnvVars();
        // trova provider id già presenti nel registro
        const presentIds = new Set();
        const idRe = /id:\s*"([a-z0-9]+)"/g; let m;
        while ((m = idRe.exec(txt))) presentIds.add(m[1]);

        let added = [];
        for (const k of KNOWN_KEY_PATTERNS) {
            const envName = k.env;
            const val = env[envName];
            if (!val) continue;                       // chiave non presente nel .env
            if (presentIds.has(k.id)) continue;        // già registrato
            // aggiungi voce al registro (prima della chiusura dell'array PROVIDERS)
            const entry = `\n    { keyFmt: "Chiave ${k.id} (rilevata da bugHunter)", id: "${k.id}", label: "${k.label}", env: "${k.env}", host: "${k.host}", chatPath: "${k.chatPath}", modelsPath: ${k.modelsPath ? '"' + k.modelsPath + '"' : "null"}, detect: ${k.rx.toString()}, signup: "${k.signup}", free: false, billed: true, note: "Aggiunto automaticamente da bugHunter dal formato della chiave nel .env." },\n`;
            const idx = txt.lastIndexOf("];");
            if (idx < 0) continue;
            const bak = backupFile(regPath);
            txt = txt.slice(0, idx) + entry + txt.slice(idx);
            fs.writeFileSync(regPath, txt, "utf8");
            if (!nodeCheck(regPath)) { restoreFrom(bak, regPath); continue; } // annulla se rotto
            presentIds.add(k.id);
            added.push(k.id);
        }
        if (added.length) {
            issues.push({ id: "C2", severity: "medium", detail: "Provider mancanti aggiunti dal .env: " + added.join(", ") });
            fixes.push("C2: aggiunti " + added.join(", "));
            appendLog("bugHunter C2: aggiunti provider dal .env → " + added.join(", "));
        }
    } catch (e) { issues.push({ id: "C2", severity: "low", detail: "scan provider fallita: " + e.message }); }
}

// C3 — provider/piattaforma con url/signup vuoto → riempi da mappa nota
function fixEmptyUrls(issues, fixes) {
    try {
        const gpPath = path.join(SRC, "gpuPlatforms.js");
        let gpt = fs.readFileSync(gpPath, "utf8");
        let changed = false;
        for (const [id, url] of Object.entries(KNOWN_URLS)) {
            const re = new RegExp('id:\\s*"' + id + '",\\s*\\n(\\s*)url:', "m");
            if (re.test(gpt)) continue; // ha già url
            const re2 = new RegExp('(id:\\s*"' + id + '",\\n)', "m");
            const mm = re2.exec(gpt);
            if (!mm) continue;
            const bak = backupFile(gpPath);
            gpt = gpt.replace(re2, `$1    url: "${url}",\n`);
            fs.writeFileSync(gpPath, gpt, "utf8");
            if (!nodeCheck(gpPath)) { restoreFrom(bak, gpPath); continue; }
            changed = true;
        }
        if (changed) { issues.push({ id: "C3", severity: "low", detail: "URL mancanti riempiti nelle piattaforme GPU." }); fixes.push("C3: url piattaforme riempiti"); appendLog("bugHunter C3: url piattaforme GPU riempiti da mappa nota."); }
    } catch (e) { issues.push({ id: "C3", severity: "low", detail: "scan url fallita: " + e.message }); }
}

// C5 — provider in PROVIDERS con regex `detect` CORROTTA → la ripristina da mappa nota.
// NOTA: molti provider hanno detect:null di proposito (chiave fittizia o logica
// custom, es. kaggle/kilo/sambanova): quelli NON vanno segnalati (è normale).
// Controlliamo SOLO i provider dentro l'array PROVIDERS (non FREE_PROVIDERS).
function fixProviderDetect(issues, fixes) {
    try {
        const regPath = path.join(SRC, "providerRegistry.js");
        let txt = fs.readFileSync(regPath, "utf8");
        // ★ 2026-07-27 — NON riparare provider che NON hai nel .env: evita di
        // "ripristinare" roba obsoleta/non tua (es. Together) solo per avere la regex.
        const envKeys = new Set(Object.keys(loadEnvVars()).map(k => k.toUpperCase()));
        // considera solo l'array PROVIDERS (prima di FREE_PROVIDERS)
        const provOnly = txt.split(/const FREE_PROVIDERS/)[0];
        // ★ 2026-07-30 — FIX LOOP INFINITO. Prima il blocco di un provider veniva
        // preso con `id:"x"[\s\S]*?\}`, cioè fino alla PRIMA graffa chiusa: ma le
        // regex `detect` contengono quantificatori con graffe ({32}, {40,}, {20,}),
        // quindi il blocco veniva tagliato IN MEZZO alla regex. Risultato: detect
        // sembrava corrotto su 6 provider sani (mistral, openai, arliai, deepinfra,
        // cloudrift, together), la "riparazione" non trovava nulla da sostituire e
        // riscriveva il file IDENTICO — con un backup — ad OGNI scansione. È l'origine
        // dei 26.000 file in .bugHunter-backup. Ora il blocco va da un `id:` al
        // successivo (le graffe interne non contano) e si scrive SOLO se il testo
        // cambia davvero.
        const marks = []; const idRe = /id:\s*"([a-z0-9]+)"/g; let m;
        while ((m = idRe.exec(provOnly))) marks.push({ id: m[1], start: m.index });
        let changed = false;
        for (let i = 0; i < marks.length; i++) {
            const id = marks[i].id;
            const end = (i + 1 < marks.length) ? marks[i + 1].start : provOnly.length;
            const blk = provOnly.slice(marks[i].start, end);
            // salta provider non configurati nel .env (evita fix su roba obsoleta)
            const envMatch = blk.match(/env:\s*"([^"]+)"/);
            if (envMatch && !envKeys.has(envMatch[1].toUpperCase())) continue;
            const hasDetect = /detect:\s*/.test(blk);
            if (!hasDetect) continue;                         // nessun detect: normale, salta
            const detMatch = blk.match(/detect:\s*(\/.*?\/[a-z]*|null)/);
            let valid = false;
            if (detMatch) {
                const v = detMatch[1];
                if (v === "null") continue;                  // detect:null esplicito = ok
                try { new RegExp(v.replace(/^\/|\/$/g, "")); valid = true; } catch (_) { valid = false; }
            }
            if (valid) continue;                              // regex ok
            const kp = KNOWN_KEY_PATTERNS.find(k => k.id === id);
            if (!kp) { issues.push({ id: "C5", severity: "low", detail: "provider " + id + " con detect corrotto e senza mappa nota (non auto-fixabile)" }); continue; }
            const fixed = blk.replace(/detect:\s*\/.*?\/[a-z]*/, "detect: " + kp.rx.toString());
            // SALVAGENTE: se la patch non cambia nulla, NON scrivere e NON fare backup
            // (era il secondo pezzo del loop: `changed` diventava true a vuoto).
            if (fixed === blk || !txt.includes(blk)) {
                issues.push({ id: "C5", severity: "low", detail: "provider " + id + ": detect non riconosciuto ma non correggibile automaticamente (nessuna modifica applicata)" });
                continue;
            }
            const bak = backupFile(regPath);
            const next = txt.replace(blk, () => fixed);       // funzione: evita che $ nella regex venga interpretato
            fs.writeFileSync(regPath, next, "utf8");
            if (!nodeCheck(regPath)) { restoreFrom(bak, regPath); continue; }
            txt = next;
            changed = true;
        }
        if (changed) { issues.push({ id: "C5", severity: "low", detail: "regex detect corrotte ripristinate da mappa nota." }); fixes.push("C5: detect ripristinati"); appendLog("bugHunter C5: regex detect ripristinate su provider noti."); }
    } catch (e) { issues.push({ id: "C5", severity: "low", detail: "C5 fallita: " + e.message }); }
}

// C6 — Antigravity deve restare registrato in Hermes (LOCK, riusa selfHeal)
function fixHermesMcp(issues, fixes) {
    try {
        const { ensureHermesMcp } = require("./selfHeal");
        if (ensureHermesMcp({ srcDir: SRC, logger: console })) {
            issues.push({ id: "C6", severity: "medium", detail: "Antigravity ri-registrato in Hermes (config.yaml ripulito)." });
            fixes.push("C6: Hermes MCP ripristinato"); appendLog("bugHunter C6: Antigravity ri-registrato in Hermes.");
        }
    } catch (_) { /* selfHeal assente: salta */ }
}

// C7 — .env presente e con MOBILE_TOKEN (solo segnalazione: non lo crea per non sovrascrivere)
function diagEnv(issues) {
    try {
        const envPath = path.join(SRC, "..", ".env");
        if (!fs.existsSync(envPath)) { issues.push({ id: "C7", severity: "high", detail: ".env mancante in HOME (l'app non può leggere le chiavi)" }); return; }
        const txt = fs.readFileSync(envPath, "utf8");
        // tollerante: ignora CRLF/commenti/spazi — basta che esista una riga MOBILE_TOKEN=...
        if (!/MOBILE_TOKEN\s*=/i.test(txt)) issues.push({ id: "C7", severity: "high", detail: "MOBILE_TOKEN mancante nel .env (il telefono non si connette)" });
    } catch (e) { issues.push({ id: "C7", severity: "low", detail: "C7 fallita: " + e.message }); }
}

// C8 — file di conoscenza/regola presenti nel cuore e nell'estensione (copia dal cuore)
function fixKnowledgeSync(issues, fixes) {
    try {
        const extSrc = path.join(process.env.USERPROFILE || "C:\\Users\\infoa",
            ".vscode", "extensions", "local-developer.antigravity-1.0.1", "src");
        if (!fs.existsSync(extSrc)) return;
        const assets = ["knowledge/ISTRUZIONI_VIVE.md", "knowledge/ANTIGRAVITY-REGOLA-ASSOLUTA.md", "knowledge/MAINTENANCE-LOG.md", "apply-change.ps1", "liveInstructions.js", "specialists.js"];
        let did = [];
        for (const a of assets) {
            const s = path.join(SRC, a), d = path.join(extSrc, a);
            if (!fs.existsSync(s)) continue;
            if (fs.existsSync(d) && fs.readFileSync(s).equals(fs.readFileSync(d))) continue;
            try { fs.mkdirSync(path.dirname(d), { recursive: true }); fs.copyFileSync(s, d); did.push(a); } catch (_) {}
        }
        if (did.length) { issues.push({ id: "C8", severity: "low", detail: "Asset di conoscenza/regola non allineati → copiati dal cuore: " + did.join(", ") }); fixes.push("C8: " + did.length + " asset sincronizzati"); appendLog("bugHunter C8: sincronizzati asset → " + did.join(", ")); }
    } catch (e) { issues.push({ id: "C8", severity: "low", detail: "C8 fallita: " + e.message }); }
}

// La radice dell'ESTENSIONE (src\ sta dentro): qui vivono extension.js, package.json,
// interface.html — cioè il punto d'ingresso vero di VS Code.
const ROOT = path.join(SRC, "..");

// Cartelle che non sono "l'estensione": copie di sicurezza, dipendenze, git.
const IGNORA_DIR = /^(node_modules|\.git|\.bugHunter|\.bugHunter-backup|\.self-heal-backup|\.vscode|icons)$/;
// File che sono copie, non codice vivo: non ha senso segnalarli.
const IGNORA_FILE = /\.bak|\.restored$|\.vecchia|-backup/i;

/** Tutti i file con una certa estensione sotto `dir`, ricorsivo, saltando le copie. */
function elencaFile(dir, ext, out = []) {
    let voci;
    try { voci = fs.readdirSync(dir, { withFileTypes: true }); } catch (_) { return out; }
    for (const v of voci) {
        if (v.isDirectory()) {
            if (IGNORA_DIR.test(v.name)) continue;
            elencaFile(path.join(dir, v.name), ext, out);
        } else if (v.name.endsWith(ext) && !IGNORA_FILE.test(v.name)) {
            out.push(path.join(dir, v.name));
        }
    }
    return out;
}

// C9 — SCANSIONE GLOBALE di TUTTA l'estensione.
//  ★ 2026-07-30 — prima guardava solo `src\*.js` di PRIMO livello: restavano fuori
//  src\agents\ e — soprattutto — extension.js, cioè il file che VS Code carica per
//  avviare l'estensione. Un errore lì non veniva visto da nessuno. Ora scende
//  ricorsivamente da tutta la radice dell'estensione e controlla anche i JSON e il
//  cablaggio di package.json.
//  Per ogni .js: (a) compila, (b) i require("./x") puntano a file esistenti —
//  risolti rispetto alla cartella DEL FILE, non a src\ (altro difetto di prima:
//  per src\agents\*.js cercava le dipendenze nella cartella sbagliata).
function diagAllJs(issues) {
    try {
        const files = elencaFile(ROOT, ".js");
        for (const p of files) {
            const f = path.relative(ROOT, p).replace(/\\/g, "/");
            let code;
            try { code = fs.readFileSync(p, "utf8"); } catch (e) { issues.push({ id: "C9", severity: "high", detail: "File illeggibile: " + f + " (" + e.message + ")" }); continue; }
            // (a) sintassi
            try { new vm.Script(code, { filename: p }); } catch (e) { issues.push({ id: "C9", severity: "high", detail: "Errore di sintassi in " + f + ": " + (e.message || "").split("\n")[0] }); continue; }
            // (b) require locali (ignora i commenti: non segnalare gli esempi)
            const base = path.dirname(p);
            for (const raw of code.split(/\r?\n/)) {
                const line = raw.trim();
                if (line.startsWith("//") || line.startsWith("*") || line.startsWith("/*")) continue;
                const reqRe = /require\(\s*["'](\.\.?\/[^"']+)["']\s*\)/g; let m;
                while ((m = reqRe.exec(raw))) {
                    const grezzo = m[1];
                    const cand = [grezzo, grezzo + ".js", grezzo + ".json", grezzo + "/index.js"];
                    if (!cand.some(c => { try { return fs.statSync(path.resolve(base, c)).isFile(); } catch (_) { return false; } }))
                        issues.push({ id: "C9", severity: "high", detail: "Dipendenza mancante in " + f + ": require('" + grezzo + "') non esiste" });
                }
            }
        }
    } catch (e) { issues.push({ id: "C9", severity: "high", detail: "C9 fallita: " + e.message }); }
}

// C11 — ★ 2026-07-30 — I FILE NON-JS CHE FANNO FUNZIONARE L'ESTENSIONE.
//  Nessuno li controllava: un package.json rotto o un `main` che punta a un file
//  inesistente spegne l'estensione intera, e il cacciatore diceva "app sana".
function diagStrutturaEstensione(issues) {
    // (a) tutti i JSON devono essere leggibili: uno rotto e VS Code non parte.
    for (const p of elencaFile(ROOT, ".json")) {
        const f = path.relative(ROOT, p).replace(/\\/g, "/");
        if (/package-lock\.json$/.test(f)) continue;               // enorme e rigenerabile
        try { JSON.parse(fs.readFileSync(p, "utf8")); }
        catch (e) { issues.push({ id: "C11", severity: /package\.json$/.test(f) ? "high" : "medium", detail: "JSON illeggibile: " + f + " (" + (e.message || "").split("\n")[0] + ")" }); }
    }

    // (b) il cablaggio di package.json: main, icona, comandi.
    let pkg = null;
    try { pkg = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8")); }
    catch (_) { issues.push({ id: "C11", severity: "high", detail: "package.json mancante o illeggibile: l'estensione non può caricarsi." }); }
    if (pkg) {
        if (!pkg.main) issues.push({ id: "C11", severity: "high", detail: "package.json non dichiara `main`: VS Code non sa quale file caricare." });
        else if (!fs.existsSync(path.resolve(ROOT, pkg.main))) issues.push({ id: "C11", severity: "high", detail: "package.json `main` punta a un file inesistente: " + pkg.main });
        if (pkg.icon && !fs.existsSync(path.resolve(ROOT, pkg.icon))) issues.push({ id: "C11", severity: "low", detail: "icona dichiarata ma mancante: " + pkg.icon });
        const cmds = (pkg.contributes && pkg.contributes.commands) || [];
        for (const c of cmds) if (!c.command) issues.push({ id: "C11", severity: "medium", detail: "package.json: un comando in contributes.commands non ha `command`." });
    }

    // (c) le pagine servite all'utente devono esserci e non essere vuote.
    const pagine = [["interface.html", ROOT], ["mobile-page.html", SRC]];
    for (const [nome, dir] of pagine) {
        const p = path.join(dir, nome);
        if (!fs.existsSync(p)) { issues.push({ id: "C11", severity: "high", detail: "Pagina mancante: " + nome }); continue; }
        let size = 0; try { size = fs.statSync(p).size; } catch (_) {}
        if (size < 500) issues.push({ id: "C11", severity: "high", detail: "Pagina sospetta (troppo piccola, " + size + " byte): " + nome });
    }
}

// C10 — CHIAVI MORTE NEL .env: segnala le API key non valide (es. Together scaduta)
// come "obsolete da rimuovere". NON le cancella (decide l'utente). Legge la cache
// degli stati chiavi scritta dal server quando qualcuno apre /keys (file
// .bugHunter/key-status.json) — così NON fa probe HTTP bloccanti qui dentro.
function diagDeadKeys(issues) {
  try {
    const cacheFile = path.join(SRC, ".bugHunter", "key-status.json");
    if (!fs.existsSync(cacheFile)) return; // nessun dato ancora: non segnalare
    const data = JSON.parse(fs.readFileSync(cacheFile, "utf8"));
    const dead = (data.dead || []).map(x => (x.id || x));
    const env = loadEnvVars();
    for (const id of dead) {
      // trova la env var relativa
      let envName = id;
      try { const reg = require("./providerRegistry"); const p = reg.all().find(x => x.id === id); if (p) envName = p.env; } catch (_) {}
      if (env[envName]) issues.push({ id: "C10", severity: "medium", detail: "Chiave OBSOLETA/non valida in .env: " + envName + " (segnalata dal pannello). Da rimuovere o rinnovare." });
    }
  } catch (e) { /* never block scan */ }
}
function diagModules(issues) {
    // ★ 2026-07-30 — aggiunti extension.js (il punto d'ingresso di VS Code, che non
    // era nell'elenco) e hermesClient.js (il canale verso Hermes: quando si rompe,
    // si rompe in silenzio — è successo davvero).
    const crit = [
        ["extension.js", ROOT],
        ["localOrchestrator.js", SRC], ["cloudEngine.js", SRC], ["nativeAgent.js", SRC],
        ["mobileServer.js", SRC], ["providerRegistry.js", SRC], ["selfHeal.js", SRC],
        ["bugHunter.js", SRC], ["hermesClient.js", SRC]
    ];
    for (const [f, dir] of crit) {
        const p = path.join(dir, f);
        if (!fs.existsSync(p)) { issues.push({ id: "C4", severity: "high", detail: "File critico MANCANTE: " + f }); continue; }
        try { new vm.Script(fs.readFileSync(p, "utf8"), { filename: p }); }
        catch (e) { issues.push({ id: "C4", severity: "high", detail: "File " + f + " non compila: " + e.message }); }
    }
}

/**
 * Esegue la scansione + le correzioni automatiche (whitelist chiusa).
 * @param {object} o  { autoFix:true } per applicare i fix; altrimenti solo report.
 * @returns {{issues:Array, fixed:number, scannedAt:string}}
 */
function scan(o = {}) {
    let autoFix = o.autoFix !== false; // default: ripara
    const issues = [];
    const fixes = [];
    // ★ 2026-07-30 — CANTIERE APERTO: la DIAGNOSI continua (vuoi comunque sapere
    // se qualcosa è rotto), ma le riparazioni automatiche si fermano. Le fix di
    // questo modulo riscrivono providerRegistry.js, gpuPlatforms.js, gli asset di
    // knowledge e risincronizzano l'estensione: esattamente i modi in cui il
    // lavoro in corso spariva mentre stavi costruendo dal telefono.
    let cantiereAperto = null;
    try {
        const cant = require("./cantiere");
        const st = cant.stato();
        if (st.aperto && autoFix) {
            autoFix = false;
            cantiereAperto = st.titolo;
            issues.push({ id: "C0", severity: "info",
                detail: "Riparazioni automatiche sospese: cantiere aperto «" + st.titolo + "» (" + st.files.length + " file protetti). Diagnosi comunque eseguita." });
        }
    } catch (_) { /* cantiere assente: comportamento di prima */ }
    try {
        if (autoFix) {
            fixExtensionSync(issues, fixes);    // C1 estensione↔cuore
            fixMissingProviders(issues, fixes); // C2 provider dal .env
            fixEmptyUrls(issues, fixes);        // C3 url piattaforme
            fixProviderDetect(issues, fixes);   // C5 detect mancanti
            fixHermesMcp(issues, fixes);        // C6 LOCK Hermes
            fixKnowledgeSync(issues, fixes);    // C8 asset conoscenza/regola
        }
        diagModules(issues);                    // C4 diagnosi moduli
        diagAllJs(issues);                      // C9 scansione GLOBALE tutti i .js
        diagStrutturaEstensione(issues);        // C11 json + cablaggio package.json + pagine
        diagEnv(issues);                       // C7 diagnosi .env
        diagDeadKeys(issues);                  // C10 chiavi morte nel .env
    } catch (e) { issues.push({ id: "ERR", severity: "high", detail: "bugHunter crash: " + e.message }); }
    // ★ 2026-07-27 — PERSISTENZA + DIALOGO CON HERMES:
    //  - scrive sempre un report su disco (bugHunter-errors.json) così è leggibile
    //    anche senza server (e Hermes può analizzarlo).
    //  - per ogni issue `high` NON auto-fissabile, apre un "ticket" nella coda
    //    (.bugHunter/queue/<ts>.json) che Hermes legge e risolve (no rete, solo file).
    const highUnfixed = issues.filter(i => i.severity === "high");
    writeReport({ issues, fixes, fixed: fixes.length, scannedAt: new Date().toISOString(), highUnfixed: highUnfixed.length });
    for (const i of highUnfixed) openTicket(i);
    return { issues, fixed: fixes.length, fixes, scannedAt: new Date().toISOString(), tickets: highUnfixed.length,
        riparazioniSospese: cantiereAperto ? ("cantiere aperto: " + cantiereAperto) : null };
}

// Scrive il report persistente su disco (sempre, anche se 0 issue).
function writeReport(obj) {
    try {
        const p = path.join(SRC, "bugHunter-errors.json");
        const prev = fs.existsSync(p) ? safeParse(fs.readFileSync(p, "utf8")) : { history: [] };
        const out = Object.assign({}, obj, { history: (prev.history || []).slice(-20).concat([{ at: obj.scannedAt, issues: obj.issues.length, fixed: obj.fixed }]) });
        fs.writeFileSync(p, JSON.stringify(out, null, 2), "utf8");
    } catch (_) {}
}
function safeParse(s) { try { return JSON.parse(s); } catch (_) { return {}; } }

// ---- CODA TICKET -----------------------------------------------------------
// ★ 2026-07-30 — Prima questa coda era una "buca delle lettere" senza postino:
// openTicket() scriveva i file e NESSUNO li leggeva mai. Il commento diceva
// "che Hermes legge e risolve", ma bugHunter.js non nominava hermesClient
// nemmeno una volta: un ticket di prova è rimasto aperto dal 27 al 30 luglio.
// Ora i ticket si elencano, si delegano a Hermes su richiesta esplicita
// dell'utente (bottone) e si chiudono. Vedi mobileServer._bugHunterDelegate.
const QUEUE_DIR = path.join(SRC, ".bugHunter", "queue");

// Apre (o aggiorna) un ticket per un issue high non auto-fissabile.
// Evita duplicati: se esiste già un ticket APERTO per lo stesso id, lo aggiorna.
function openTicket(issue) {
    try {
        fs.mkdirSync(QUEUE_DIR, { recursive: true });
        // cerca ticket già presente e NON chiuso per lo stesso id
        let existing = null;
        for (const f of fs.readdirSync(QUEUE_DIR)) {
            if (!f.endsWith(".json")) continue;
            const t = safeParse(fs.readFileSync(path.join(QUEUE_DIR, f), "utf8"));
            if (t && t.id === issue.id && (t.status === "open" || t.status === "in-progress")) { existing = { f, t }; break; }
        }
        const ticket = existing ? existing.t : {
            id: issue.id, severity: issue.severity, detail: issue.detail,
            status: "open", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
            resolution: null
        };
        ticket.updatedAt = new Date().toISOString();
        ticket.detail = issue.detail;
        const fp = existing ? path.join(QUEUE_DIR, existing.f) : path.join(QUEUE_DIR, Date.now().toString(36) + "_" + issue.id + ".json");
        fs.writeFileSync(fp, JSON.stringify(ticket, null, 2), "utf8");
    } catch (_) {}
}

/** Elenca i ticket. Ogni voce porta `file` (il nome, che è la sua chiave). */
function listTickets() {
    const out = [];
    try {
        if (!fs.existsSync(QUEUE_DIR)) return out;
        for (const f of fs.readdirSync(QUEUE_DIR)) {
            if (!f.endsWith(".json")) continue;
            const t = safeParse(fs.readFileSync(path.join(QUEUE_DIR, f), "utf8"));
            if (t && t.id) out.push(Object.assign({ file: f }, t));
        }
    } catch (_) {}
    out.sort((a, b) => String(b.updatedAt || "").localeCompare(String(a.updatedAt || "")));
    return out;
}

/** Aggiorna i campi di un ticket. `file` è il nome dentro la coda (niente path:
 *  qualsiasi separatore viene rifiutato, così un nome che arriva da HTTP non può
 *  farci scrivere fuori dalla cartella della coda). */
function updateTicket(file, patch) {
    const name = String(file || "");
    if (!name.endsWith(".json") || /[\\/]|\.\./.test(name)) throw new Error("nome ticket non valido");
    const fp = path.join(QUEUE_DIR, name);
    if (!fs.existsSync(fp)) throw new Error("ticket inesistente: " + name);
    const t = safeParse(fs.readFileSync(fp, "utf8"));
    const next = Object.assign({}, t, patch, { updatedAt: new Date().toISOString() });
    fs.writeFileSync(fp, JSON.stringify(next, null, 2), "utf8");
    return Object.assign({ file: name }, next);
}

// ---- GUARDIA: fotografia dell'albero dei file ------------------------------
// ★ 2026-07-30 — serve a rendere VERIFICATA, non creduta, la promessa "in fase di
// analisi non tocco niente". Hermes gira con --yolo (altrimenti si blocca sulle
// conferme, headless), quindi il "non modificare" del prompt da solo varrebbe
// zero: confrontiamo la fotografia prima/dopo e, se qualcosa è cambiato, lo
// diciamo invece di fidarci.
// File che l'applicazione riscrive DA SOLA mentre gira (report, cataloghi, indici):
// se restassero nella fotografia, ogni delega segnalerebbe "Hermes ha toccato dei
// file" quando invece li ha cambiati il server. Verificato: durante una delega si
// muovono cloud-catalog.json e bugHunter-errors.json.
const SCRITTI_DALL_APP = /(^|\/)(package-lock\.json|cloud-catalog\.json|bugHunter-errors\.json|PROJECT_INDEX\.json)$/;

function fotografiaAlbero() {
    const mappa = {};
    for (const ext of [".js", ".json", ".html"])
        for (const p of elencaFile(ROOT, ext)) {
            const rel = path.relative(ROOT, p).replace(/\\/g, "/");
            if (SCRITTI_DALL_APP.test(rel)) continue;
            try {
                mappa[rel] = crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
            } catch (_) {}
        }
    return mappa;
}

/** Che cosa è cambiato fra due fotografie. → ["modificato: x", "creato: y", …] */
function confrontaAlbero(prima, dopo) {
    const out = [];
    for (const f of Object.keys(dopo)) {
        if (!(f in prima)) out.push("creato: " + f);
        else if (prima[f] !== dopo[f]) out.push("modificato: " + f);
    }
    for (const f of Object.keys(prima)) if (!(f in dopo)) out.push("cancellato: " + f);
    return out;
}

// ---- I DUE PROMPT ----------------------------------------------------------
// Stanno qui, non nel server: una sola fonte di verità, leggibile senza far
// partire niente. Fase 1 propone e basta; fase 2 esegue ciò che hai approvato.

/** FASE 1 — analisi. Hermes deve solo capire e PROPORRE, in un formato che tu
 *  possa leggere e approvare consapevolmente. */
function promptAnalisi(t) {
    return [
        "Sei chiamato dal cacciatore di bug interno di Antigravity (progetto in " + ROOT + ").",
        "",
        "ERRORE RILEVATO [" + t.id + ", gravità " + t.severity + "]:",
        t.detail,
        "",
        "QUESTA È UNA FASE DI SOLA ANALISI. NON MODIFICARE, NON CREARE E NON CANCELLARE",
        "NESSUN FILE. Leggi quello che ti serve e basta. Le modifiche te le chiederò dopo,",
        "se approvo la tua proposta. (Un controllo automatico confronta i file prima e dopo:",
        "se tocchi qualcosa, viene segnalato.)",
        "",
        "Rispondi in italiano, conciso, ESATTAMENTE con queste quattro sezioni:",
        "",
        "CAUSA: perché succede, in 1-3 frasi comprensibili a chi non ha scritto il codice.",
        "FILE DA TOCCARE: elenco dei file, uno per riga, con il numero di riga se lo sai.",
        "COSA CAMBIO: la modifica precisa che proponi, con il codice prima → dopo.",
        "RISCHI: che cosa potrebbe rompersi se la applico, e come me ne accorgerei.",
        "",
        "Se non sei sicuro della causa, dillo apertamente in CAUSA e non inventare una patch."
    ].join("\n");
}

/** FASE 2 — esecuzione. Parte SOLO dopo che l'utente ha letto e approvato il
 *  piano, e riceve quel piano testuale come mandato. */
function promptEsecuzione(t) {
    return [
        "Sei chiamato dal cacciatore di bug interno di Antigravity (progetto in " + ROOT + ").",
        "",
        "ERRORE [" + t.id + "]: " + t.detail,
        "",
        "L'UTENTE HA LETTO E APPROVATO QUESTO PIANO. Applicalo, senza allargarti ad altro:",
        "--- inizio piano approvato ---",
        String(t.plan || "").slice(0, 12000),
        "--- fine piano approvato ---",
        "",
        "REGOLE ANTI-DANNO, obbligatorie:",
        "1) backup del file prima di toccarlo,",
        "2) patch minima e mirata: NON riscrivere il file intero,",
        "3) `node --check` sul file dopo la modifica; se fallisce, ripristina il backup e fermati,",
        "4) non toccare MAI il .env né le chiavi,",
        "5) non modificare file che non sono nel piano approvato: se ti accorgi che ne servono altri,",
        "   FERMATI e spiegalo invece di farlo.",
        "",
        "Alla fine elenca i file che hai modificato e cosa hai cambiato. Rispondi in italiano, conciso."
    ].join("\n");
}

module.exports = {
    scan, KNOWN_KEY_PATTERNS, KNOWN_URLS,
    listTickets, updateTicket, QUEUE_DIR,
    promptAnalisi, promptEsecuzione,
    fotografiaAlbero, confrontaAlbero
};
