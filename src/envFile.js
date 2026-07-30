"use strict";

/**
 * envFile — dice dove sta il .env del progetto.
 *
 * ★ 2026-07-30 (riordino) — Antigravity ora vive tutto sotto una sola cartella
 * (C:\Users\infoa\Antigravity) e il .env sta nella radice del PROGETTO, non nella
 * home dell'utente. Prima cinque moduli (gpuFailover, gpuWaker, modelPuller,
 * planner, whatsappBridge) lo cercavano con os.homedir(): restavano incollati a
 * C:\Users\infoa anche spostando il progetto, e le loro chiavi sarebbero sparite
 * senza dare errore (il readFileSync è dentro un try che ingoia tutto).
 *
 * Ordine di ricerca: radice del progetto → src\ → home (per compatibilità con
 * installazioni vecchie).
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

function envFilePath() {
    const candidati = [
        path.join(__dirname, "..", ".env"),
        path.join(__dirname, ".env"),
        path.join(os.homedir(), ".env"),
    ];
    for (const p of candidati) {
        try { if (fs.existsSync(p)) return p; } catch (_) {}
    }
    return candidati[0];
}

module.exports = { envFilePath };
