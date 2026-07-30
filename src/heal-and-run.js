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
    process.exit(1);
});
