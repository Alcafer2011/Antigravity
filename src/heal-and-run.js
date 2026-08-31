"use strict";

/**
 * heal-and-run.js — punto d'ingresso del SERVER PERMANENTE con auto-riparazione.
 *
 * È il file che lancia l'autostart di Windows (al posto di mobileServer.js diretto).
 * Prima di caricare qualsiasi cosa, RIPARA i file corrotti (incluso mobileServer.js
 * stesso) da una copia sana; poi avvia il server. Così, se durante l'uso qualche
 * file si rovina, alla ripartenza (il VBS riavvia in loop) è già a posto.
 *
 * Dipende solo da selfHeal (moduli nativi) finché i file non sono verificati.
 */

const path = require("path");
const fs = require("fs");
const net = require("net");

// ★ 2026-08-01 — GUARDIA ISTANZA SINGOLA.
// Prima c'era un ciclo infinito: se un'altra istanza teneva gia' la 8790, questa
// arrivava fino a srv.start(), falliva con EADDRINUSE, usciva con codice 1 e il VBS
// dello Startup la rilanciava dopo 5s. All'infinito (16 MB di log in due giorni).
// Peggio: verifyAndRepair() girava PRIMA del fallimento, quindi ogni pochi secondi
// partiva una passata di auto-riparazione sul codice vivo — proprio il rischio che
// il cantiere deve impedire.
// Ora si controlla la porta PRIMA di qualsiasi altra cosa, e se il server e' gia'
// acceso si esce in silenzio con codice 0 (nessuna riparazione, nessun rumore).
function portaOccupata(port, host, timeoutMs) {
    return new Promise(resolve => {
        const sock = new net.Socket();
        let esito = false;
        const chiudi = () => { try { sock.destroy(); } catch (e) {} resolve(esito); };
        sock.setTimeout(timeoutMs);
        sock.once("connect", () => { esito = true; chiudi(); });
        sock.once("timeout", chiudi);
        sock.once("error", chiudi);
        sock.connect(port, host);
    });
}

function portaConfigurata() {
    // Stessa precedenza di MobileServer: MOBILE_PORT dal .env, altrimenti 8790.
    // Letto a mano: qui non possiamo ancora fidarci dei moduli non verificati.
    try {
        const envPath = path.join(__dirname, "..", ".env");
        const riga = fs.readFileSync(envPath, "utf8")
            .split(/\r?\n/)
            .find(l => /^\s*MOBILE_PORT\s*=/.test(l));
        if (riga) {
            const n = parseInt(riga.split("=")[1].trim(), 10);
            if (Number.isFinite(n) && n > 0) return n;
        }
    } catch (e) {}
    return 8790;
}

async function main() {

const PORTA = portaConfigurata();
if (await portaOccupata(PORTA, "127.0.0.1", 2000)) {
    console.log("[heal-and-run] server gia' in ascolto sulla " + PORTA + ": esco senza fare nulla.");
    process.exit(0);
}

// 1) Ripara i file critici PRIMA di caricare il server.
try {
    const { verifyAndRepair, ensureHermesMcp, CRITICAL_FILES } = require("./selfHeal");
    const repaired = verifyAndRepair({ srcDir: __dirname, files: CRITICAL_FILES, logger: console });
    if (repaired.length) console.log("[heal-and-run] file riparati all'avvio: " + repaired.join(", "));
    // LOCK: se Hermes ha ripulito la sua config, ri-registra Antigravity come MCP.
    if (ensureHermesMcp) ensureHermesMcp({ srcDir: __dirname, logger: console });
} catch (e) {
    console.error("[heal-and-run] selfHeal non disponibile: " + e.message);
}

// 2) Avvia il server (ora i moduli sono verificati/riparati).
const { MobileServer } = require("./mobileServer");
const srv = new MobileServer({ rootDir: path.join(__dirname, "..") });

// 2b) ★ 2026-07-26 — il proxy di traduzione delle tool-call di Kaggle NON parte più
// all'avvio. Serve soltanto quando si usa davvero un modello Kaggle, e adesso è
// hermesClient.delegate() ad accenderlo in quel caso (insieme al notebook). Tenerlo
// sempre su faceva parte del "Kaggle che si accende da solo" segnalato dall'utente.
srv.start().then(({ urls, token }) => {
    console.log("\n=== Server mobile Antigravity avviato (con auto-riparazione) ===");
    console.log("TOKEN:", token);
    for (const u of urls) console.log("  " + u);
}).catch(err => {
    console.error("Avvio fallito:", err.message);
    // Se nel frattempo un'altra istanza ha preso la porta (corsa tra la guardia e
    // il listen), non e' un guasto: esci con 0 per non far ripartire il ciclo.
    process.exit(err && err.code === "EADDRINUSE" ? 0 : 1);
});

} // fine main()

main().catch(err => {
    console.error("[heal-and-run] errore fatale:", err && err.message);
    process.exit(1);
});
