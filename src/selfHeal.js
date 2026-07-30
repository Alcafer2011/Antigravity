"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

/**
 * selfHeal — auto-riparazione dei file dell'estensione/server.
 *
 * IDEA: ogni volta che il server parte BENE, salva una copia "sana" dei propri
 * file sorgente in una cartella di backup nascosta. Se in un avvio successivo un
 * file risulta MANCANTE o CORROTTO (troncato, errore di sintassi, JSON/HTML rotto),
 * lo RIPRISTINA da quella copia sana — prima ancora che il resto del codice provi
 * a usarlo. Unito al riavvio automatico del server, l'effetto è: "se qualcosa si
 * corrompe, alla ripartenza è già a posto".
 *
 * Non richiede rete né una build esterna: la copia di riferimento nasce dal primo
 * avvio funzionante e si aggiorna a ogni avvio sano (così il backup segue gli
 * aggiornamenti legittimi del codice, ma non le corruzioni).
 *
 * Dipendenze: solo moduli nativi (fs/path/vm). Così questo file può girare per
 * primo, prima di caricare qualsiasi altro modulo che potrebbe essere corrotto.
 */

const BACKUP_DIRNAME = ".self-heal-backup";

/**
 * ★ 2026-07-30 — CANTIERE: se stai costruendo qualcosa dal telefono, i file che
 * hai dichiarato NON vanno né ripristinati né usati come nuovo riferimento sano.
 * cantiere.js dipende solo da fs/path come questo file, quindi si può caricare
 * anche qui, prima di tutto il resto; se manca, si torna al comportamento di
 * prima (nessuna protezione, ma nessun crash).
 */
function _cantiere() {
    try { return require("./cantiere"); } catch (_) { return null; }
}

/** Un file è "sano"? (parsa/è coerente per il suo tipo) */
function isHealthy(file) {
    let content;
    try { content = fs.readFileSync(file); } catch (_) { return false; }
    if (!content || content.length === 0) return false;
    const ext = path.extname(file).toLowerCase();
    try {
        if (ext === ".js") {
            // Compila SENZA eseguire: intercetta troncature ed errori di sintassi.
            new vm.Script(content.toString("utf8"), { filename: file });
            return true;
        }
        if (ext === ".json") { JSON.parse(content.toString("utf8")); return true; }
        if (ext === ".html") {
            const s = content.toString("utf8");
            return s.length > 32 && s.includes("<");
        }
        // Altri tipi: basta che non siano vuoti.
        return true;
    } catch (_) {
        return false;
    }
}

function ensureDir(d) { try { fs.mkdirSync(d, { recursive: true }); } catch (_) {} }

/**
 * Verifica e ripara i file elencati. Va chiamata PRIMA di require-are gli altri
 * moduli. Ritorna la lista dei file riparati (vuota = nulla da fare).
 *
 * @param {object} o
 *   srcDir   cartella dei sorgenti (es. .../src)
 *   files    nomi file da proteggere (relativi a srcDir)
 *   backupDir cartella backup (default: srcDir/.self-heal-backup)
 *   logger
 */
function verifyAndRepair(o = {}) {
    const srcDir = o.srcDir;
    const files = o.files || [];
    const backupDir = o.backupDir || path.join(srcDir, BACKUP_DIRNAME);
    const logger = o.logger || console;
    const repaired = [];

    const cant = _cantiere();

    for (const name of files) {
        const src = path.join(srcDir, name);
        const bak = path.join(backupDir, name);
        if (isHealthy(src)) continue;               // sano: niente da fare

        // ★ 2026-07-30 — File sotto cantiere e NON compilabile: è il caso di
        // emergenza (senza riparazione il server non parte, e un cantiere che
        // impedisce all'app di avviarsi non protegge nulla). Si ripara, ma prima
        // la versione a metà viene archiviata in .cantiere/<id>/rotti/ e scritta
        // nel diario: il lavoro non si perde, si mette da parte.
        let fontePrima = null;
        if (cant && cant.protetto(name)) {
            const g = cant.guardia(name, "selfHeal", { emergenza: true, motivo: "il file non compila: senza ripristino il server non parte" });
            if (!g.consentito) continue;
            try { cant.salvaVersioneRotta(name, src); } catch (_) {}
            fontePrima = g.fontePrima || null;      // "com'era prima che cominciassi"
        }

        // ★ 2026-07-30 — Due generazioni: se il backup più recente è a sua volta
        // inutilizzabile, si ricade su quello precedente (.prev). Prima esisteva una
        // sola copia: se veniva sovrascritta con un file guasto, non restava nulla.
        // Il cantiere, se c'è, ha la precedenza: la sua copia è più vicina al lavoro in corso.
        const fonte = (fontePrima && isHealthy(fontePrima)) ? fontePrima
            : (fs.existsSync(bak) && isHealthy(bak)) ? bak
            : (fs.existsSync(bak + ".prev") && isHealthy(bak + ".prev")) ? bak + ".prev"
            : null;
        if (!fonte) continue;                       // nessuna copia sana da cui ripristinare
        try {
            ensureDir(path.dirname(src));
            fs.copyFileSync(fonte, src);
            if (isHealthy(src)) {
                repaired.push(name);
                (logger.warn || logger.log || console.log).call(logger,
                    `[selfHeal] riparato file corrotto: ${name}${fonte.endsWith(".prev") ? " (dalla copia precedente)" : ""}`);
            }
        } catch (e) {
            (logger.error || console.error).call(logger, `[selfHeal] ripristino fallito ${name}: ${e.message}`);
        }
    }
    return repaired;
}

/**
 * Aggiorna la copia sana di riferimento. Va chiamata DOPO che il server è partito
 * bene. Copia solo i file attualmente sani (non propaga eventuali corruzioni).
 */
function snapshotHealthy(o = {}) {
    const srcDir = o.srcDir;
    const files = o.files || [];
    const backupDir = o.backupDir || path.join(srcDir, BACKUP_DIRNAME);
    const logger = o.logger || console;
    ensureDir(backupDir);
    const cant = _cantiere();
    let saved = 0, saltati = 0;
    for (const name of files) {
        const src = path.join(srcDir, name);
        const bak = path.join(backupDir, name);
        if (!isHealthy(src)) continue;
        // ★ 2026-07-30 — File sotto cantiere: NON diventa il nuovo riferimento
        // "sano". Un lavoro a metà compila benissimo: promuoverlo a backup
        // significherebbe buttare via l'ultima versione davvero funzionante e
        // ritrovarsela ripristinata al prossimo avvio.
        if (cant && cant.protetto(name)) { saltati++; continue; }
        try {
            // Copia solo se diverso (evita scritture inutili).
            let same = false;
            try { same = fs.existsSync(bak) && fs.readFileSync(bak).equals(fs.readFileSync(src)); } catch (_) {}
            if (!same) {
                ensureDir(path.dirname(bak));
                // ★ 2026-07-30 — Ruota la generazione precedente PRIMA di sovrascrivere.
                // "isHealthy" dice solo che il file compila, non che funziona: un file
                // guasto ma sintatticamente valido può diventare il nuovo riferimento.
                // Conservando .prev, la versione buona sopravvive comunque.
                try { if (fs.existsSync(bak)) fs.copyFileSync(bak, bak + ".prev"); } catch (_) {}
                fs.copyFileSync(src, bak);
                saved++;
            }
        } catch (e) {
            (logger.error || console.error).call(logger, `[selfHeal] backup fallito ${name}: ${e.message}`);
        }
    }
    if (saved) (logger.log || console.log).call(logger, `[selfHeal] snapshot sano aggiornato (${saved} file)`);
    if (saltati) (logger.log || console.log).call(logger, `[selfHeal] ${saltati} file saltati: sono in un cantiere aperto (lavoro in corso).`);
    return saved;
}

/** Elenco standard dei file critici di Antigravity (relativi a src/). */
const CRITICAL_FILES = [
    "localOrchestrator.js", "localEngine.js", "nativeAgent.js", "cloudEngine.js",
    "claudeEngine.js", "claudeHook.js", "comfyClient.js", "hermesClient.js",
    "reTools.js", "services.js", "serverClient.js", "mcpServer.js",
    "ghidraClient.js", "ghidraHeadless.js", "ghidraLauncher.js", "providerRegistry.js",
    // ★ 2026-07-30 — providerCatalog.js: catalogo preconfigurato dei provider.
    // È protetto come gli altri, ma providerRegistry lo richiede dentro un try:
    // se sparisse, il registro tornerebbe alla sola lista curata senza crash.
    "providerCatalog.js", "webSearch.js",
    "learningMemory.js", "mobileServer.js", "mobile-page.html", "kaggleToolProxy.js", "kaggleWaker.js",
    "kaggleEngine.js", "nousClient.js", "whatsappBridge.js", "gpuPlatforms.js",
    // ★ 2026-07-30 — cantiere.js è il modulo che PROTEGGE il lavoro in corso:
    // se si corrompe, spariscono anche le protezioni, quindi è il primo che deve
    // poter tornare sano. (Nessun cortocircuito: se è rotto, il require qui sopra
    // fallisce e le riparazioni tornano a comportarsi come prima.)
    "cantiere.js", "modelAdvisor.js", "notebookTemplate.js", "platformWizard.js", "modelMirror.js",
    "platforms/base.js", "platforms/index.js", "platforms/modal.js", "platforms/kaggle.js"
];

/**
 * ensureHermesMcp — LOCK: garantisce che Antigravity resti registrato come server
 * MCP dentro Hermes. Se un "autofix" di Hermes riscrive config.yaml e rimuove il
 * nostro blocco, questa funzione lo RI-AGGIUNGE al successivo avvio del server
 * (che è sempre attivo, nascosto, via l'autostart di Windows). Nessun processo
 * nuovo, nessuna finestra: è un semplice controllo di testo su config.yaml.
 *
 * Dipende solo da fs/path. Idempotente: se il blocco c'è già, non tocca nulla.
 *
 * @param {object} o  srcDir (cartella src, dove sta mcpServer.js), logger
 * @returns {boolean} true se ha dovuto ripristinare il blocco
 */
function ensureHermesMcp(o = {}) {
    const srcDir = o.srcDir;
    const logger = o.logger || console;
    try {
        const local = process.env.LOCALAPPDATA || path.join(process.env.USERPROFILE || "", "AppData", "Local");
        const cfg = path.join(local, "hermes", "config.yaml");
        if (!fs.existsSync(cfg)) return false;                 // Hermes non installato: niente da fare
        const mcpPath = path.join(srcDir, "mcpServer.js");
        let txt = fs.readFileSync(cfg, "utf8");
        // Già presente? (riconosciuto dal percorso di mcpServer.js) → nulla da fare.
        if (txt.indexOf("mcpServer.js") !== -1) return false;

        const nodeExe = process.execPath || "C:\\Program Files\\nodejs\\node.exe";
        const block =
            "  antigravity:\n" +
            "    command: " + nodeExe + "\n" +
            "    args:\n" +
            "      - " + mcpPath + "\n" +
            "    enabled: true\n";

        const eol = txt.indexOf("\r\n") !== -1 ? "\r\n" : "\n";
        const blockEol = block.replace(/\n/g, eol);

        if (/^mcp_servers:\s*$/m.test(txt)) {
            // Esiste già la sezione mcp_servers (con altri server): inseriamo il
            // nostro sotto-blocco subito dopo l'intestazione, senza duplicare la chiave.
            txt = txt.replace(/^(mcp_servers:\s*)$/m, "$1" + eol + blockEol.replace(/\s+$/,'') );
        } else {
            // Nessuna sezione: la creiamo in fondo (l'ordine delle chiavi YAML è irrilevante).
            if (!txt.endsWith(eol)) txt += eol;
            txt += "mcp_servers:" + eol + blockEol;
        }
        fs.writeFileSync(cfg, txt, "utf8");
        (logger.warn || logger.log || console.log).call(logger,
            "[selfHeal] LOCK: Antigravity ri-registrato in Hermes (config.yaml era stato ripulito).");
        return true;
    } catch (e) {
        try { (logger.error || console.error).call(logger, "[selfHeal] ensureHermesMcp: " + e.message); } catch (_) {}
        return false;
    }
}

module.exports = { verifyAndRepair, snapshotHealthy, isHealthy, ensureHermesMcp, CRITICAL_FILES, BACKUP_DIRNAME };
