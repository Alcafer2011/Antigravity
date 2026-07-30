"use strict";

/**
 * cantiere — IL LAVORO CHE STAI COSTRUENDO DAL TELEFONO NON SI TOCCA.
 *
 * ★ 2026-07-30 — Problema vero, ripetuto: apri l'app dal cellulare, cominci a
 * costruire qualcosa, e nel frattempo un altro pezzo dell'app ti passa sopra —
 * selfHeal che "ripara" un file che stavi scrivendo, rollback che rimette una
 * copia vecchia, il cacciatore di bug che delega a Hermes e Hermes riscrive,
 * apply-change.ps1 che risincronizza, il failover che cambia piattaforma a metà
 * lavoro. Ogni singolo pezzo, da solo, sta facendo la cosa giusta. Insieme
 * distruggono quello che stai facendo.
 *
 * Un CANTIERE è una dichiarazione: «sto lavorando su questi file, fino a che non
 * chiudo, nessun automatismo li tocca». Chi vuole modificarli deve chiedere il
 * permesso a `guardia()` e riceve NO — e il tentativo finisce nel diario, così
 * tu vedi chi ha provato a passarti sopra invece di scoprire il danno dopo.
 *
 * E poiché il lavoro si interrompe (finisce il contesto, chiudi il telefono,
 * riavvii il PC), il cantiere è anche un DIARIO: ogni passo fatto e il prossimo
 * passo previsto. `ripresa()` restituisce il testo con cui ripartire esattamente
 * da dove eri: non serve più raccontare da capo, basta "continua".
 *
 * Regole di sicurezza (per non trasformare la protezione in un'altra trappola):
 *  - Protegge SOLO i file dichiarati nel cantiere. Tutto il resto continua a
 *    guarire da solo come prima.
 *  - Se un file protetto è davvero ROTTO (non compila) e il server non parte,
 *    selfHeal può ripararlo, ma prima mette al sicuro la versione rotta in
 *    `<id>/rotti/` e lo scrive nel diario: non si perde niente lo stesso.
 *  - Nessuna chiusura automatica. Dopo 24h senza attività il cantiere diventa
 *    "sospeso" (te lo dice, resta protetto): un cantiere dimenticato non deve
 *    poter sparire da solo, ma nemmeno restare invisibile.
 *
 * Dipende solo da fs/path: può essere caricato prestissimo, come selfHeal.
 */

const fs = require("fs");
const path = require("path");

const SRC = __dirname;
const BASE = path.join(SRC, ".cantiere");
const ATTIVO = path.join(BASE, "attivo.json");
const STORICO = path.join(BASE, "storico");

/** Dopo quanto silenzio un cantiere è "sospeso" (protetto, ma segnalato). */
const SOSPENSIONE_MS = 24 * 60 * 60 * 1000;

function _dir(d) { try { fs.mkdirSync(d, { recursive: true }); } catch (_) {} }
function _ora() { return new Date().toISOString(); }
function _id() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

/**
 * Normalizza il nome di un file al formato usato nel manifesto: percorso
 * relativo a src/ con separatori "/". Accetta assoluti, relativi, con "\".
 */
function normalizza(file) {
    if (!file) return null;
    let f = String(file).trim();
    if (path.isAbsolute(f)) {
        const rel = path.relative(SRC, f);
        // Fuori da src/: si tiene l'assoluto (un cantiere può toccare anche
        // extension.js o package.json nella radice del progetto).
        f = rel.startsWith("..") ? f : rel;
    }
    return f.replace(/\\/g, "/");
}

// --- lettura/scrittura dello stato -------------------------------------------

function _leggi() {
    try { return JSON.parse(fs.readFileSync(ATTIVO, "utf8")); } catch (_) { return null; }
}
function _scrivi(c) {
    _dir(BASE);
    fs.writeFileSync(ATTIVO, JSON.stringify(c, null, 2), "utf8");
    return c;
}

/**
 * Il cantiere aperto in questo momento, o null. Aggiorna lo stato "sospeso"
 * (solo informativo: la protezione resta).
 */
function attivo() {
    const c = _leggi();
    if (!c || c.stato === "chiuso") return null;
    c.sospeso = (Date.now() - new Date(c.ultimoTocco || c.aperto).getTime()) > SOSPENSIONE_MS;
    return c;
}

function _cartella(c) { return path.join(BASE, c.id); }

// --- diario -------------------------------------------------------------------

function _diario(c, voce) {
    try {
        _dir(_cartella(c));
        fs.appendFileSync(path.join(_cartella(c), "diario.jsonl"),
            JSON.stringify(Object.assign({ t: _ora() }, voce)) + "\n", "utf8");
    } catch (_) {}
}

function diario(c, limite = 200) {
    const cc = c || attivo();
    if (!cc) return [];
    try {
        return fs.readFileSync(path.join(_cartella(cc), "diario.jsonl"), "utf8")
            .split("\n").filter(Boolean).map(r => { try { return JSON.parse(r); } catch (_) { return null; } })
            .filter(Boolean).slice(-limite);
    } catch (_) { return []; }
}

// --- copie di sicurezza dei file del cantiere ---------------------------------

/**
 * Mette da parte la versione ATTUALE del file, una volta sola, prima che il
 * cantiere cominci a modificarlo. È il punto di ritorno "com'era prima che
 * cominciassi", indipendente dai backup di selfHeal (che nel frattempo possono
 * essere sovrascritti).
 */
function _copiaPrima(c, nome) {
    try {
        const sorgente = path.isAbsolute(nome) ? nome : path.join(SRC, nome);
        if (!fs.existsSync(sorgente)) return false;             // file nuovo: niente "prima"
        const dest = path.join(_cartella(c), "prima", nome.replace(/[:\\/]+/g, "__"));
        if (fs.existsSync(dest)) return false;                  // già fotografato
        _dir(path.dirname(dest));
        fs.copyFileSync(sorgente, dest);
        return true;
    } catch (_) { return false; }
}

/** Percorso della copia "com'era prima", o null. */
function fontePrima(nome) {
    const c = attivo();
    if (!c) return null;
    const n = normalizza(nome);
    const p = path.join(_cartella(c), "prima", n.replace(/[:\\/]+/g, "__"));
    return fs.existsSync(p) ? p : null;
}

/**
 * Mette al sicuro una versione ROTTA prima che qualcuno la sovrascriva.
 * Chiamata da selfHeal quando deve riparare un file protetto: il lavoro a metà
 * non si butta, si archivia e si annota.
 */
function salvaVersioneRotta(nome, percorsoFile) {
    const c = attivo();
    if (!c) return null;
    try {
        const n = normalizza(nome);
        const dest = path.join(_cartella(c), "rotti", n.replace(/[:\\/]+/g, "__") + "." + Date.now().toString(36));
        _dir(path.dirname(dest));
        fs.copyFileSync(percorsoFile, dest);
        _diario(c, { tipo: "salvataggio", file: n, testo: "versione non compilabile messa da parte prima della riparazione", dove: dest });
        return dest;
    } catch (_) { return null; }
}

// --- apertura / chiusura -------------------------------------------------------

/**
 * Apre un cantiere. Se ce n'è già uno aperto NON lo sostituisce (sarebbe lo
 * stesso problema che vogliamo risolvere): aggiunge i file al cantiere esistente
 * e lo segnala.
 *
 * @param {object} o  titolo, files[], obiettivo, prossimo, origine ("mobile"|"vscode"|...)
 */
function apri(o = {}) {
    const files = (o.files || []).map(normalizza).filter(Boolean);
    const esistente = attivo();
    if (esistente) {
        const nuovi = files.filter(f => !esistente.files.includes(f));
        esistente.files.push(...nuovi);
        esistente.ultimoTocco = _ora();
        for (const f of nuovi) _copiaPrima(esistente, f);
        if (nuovi.length) _diario(esistente, { tipo: "file", testo: "aggiunti al cantiere: " + nuovi.join(", ") });
        _scrivi(esistente);
        return { ok: true, giaAperto: true, cantiere: esistente,
            nota: "C'era già un cantiere aperto («" + esistente.titolo + "»): ho aggiunto i file a quello invece di aprirne un altro." };
    }

    const c = {
        id: _id(),
        titolo: o.titolo || "Lavoro senza titolo",
        obiettivo: o.obiettivo || "",
        prossimo: o.prossimo || "",
        origine: o.origine || "mobile",
        files,
        stato: "aperto",
        aperto: _ora(),
        ultimoTocco: _ora(),
        pinPiattaforma: o.pinPiattaforma || null,   // il failover non cambia corsia a metà lavoro
        passi: 0,
        blocchi: 0
    };
    _dir(_cartella(c));
    for (const f of files) _copiaPrima(c, f);
    _diario(c, { tipo: "apertura", testo: c.titolo, obiettivo: c.obiettivo, files });
    _scrivi(c);
    return { ok: true, cantiere: c };
}

/** Aggiunge file alla protezione di un cantiere già aperto. */
function proteggi(files) {
    const c = attivo();
    if (!c) return { ok: false, error: "nessun cantiere aperto" };
    const nuovi = (Array.isArray(files) ? files : [files]).map(normalizza).filter(f => f && !c.files.includes(f));
    c.files.push(...nuovi);
    c.ultimoTocco = _ora();
    for (const f of nuovi) _copiaPrima(c, f);
    if (nuovi.length) _diario(c, { tipo: "file", testo: "protetti: " + nuovi.join(", ") });
    _scrivi(c);
    return { ok: true, aggiunti: nuovi, files: c.files };
}

/**
 * Segna un passo. `prossimo` è la cosa più importante del modulo: è quello che
 * permette di riprendere senza rispiegare tutto.
 */
function passo(testo, o = {}) {
    const c = attivo();
    if (!c) return { ok: false, error: "nessun cantiere aperto" };
    c.passi++;
    c.ultimoPasso = String(testo || "").slice(0, 2000);
    if (o.prossimo !== undefined) c.prossimo = String(o.prossimo || "").slice(0, 2000);
    c.ultimoTocco = _ora();
    _diario(c, { tipo: "passo", testo: c.ultimoPasso, prossimo: c.prossimo || null });
    _scrivi(c);
    return { ok: true, passi: c.passi, prossimo: c.prossimo };
}

/**
 * Appunta la corsia GPU al cantiere: finché è aperto, il failover non cambia
 * piattaforma (cambiare endpoint e modello a metà lavoro è un altro modo di
 * rompere quello che stai costruendo). Vedi gpuFailover.pickActive.
 */
function appunta(piattaforma) {
    const c = attivo();
    if (!c) return { ok: false, error: "nessun cantiere aperto" };
    if (c.pinPiattaforma === piattaforma) return { ok: true, pinPiattaforma: piattaforma, gia: true };
    c.pinPiattaforma = piattaforma || null;
    c.ultimoTocco = _ora();
    _diario(c, { tipo: "nota", testo: "corsia GPU appuntata su «" + piattaforma + "»: il failover non la cambierà fino alla chiusura del cantiere" });
    _scrivi(c);
    return { ok: true, pinPiattaforma: piattaforma };
}

/** Solo "sono ancora qui": rinvia la sospensione senza sporcare il diario. */
function tocca() {
    const c = attivo();
    if (!c) return { ok: false };
    c.ultimoTocco = _ora();
    _scrivi(c);
    return { ok: true };
}

/** Chiude il cantiere (l'unico modo: nessuna scadenza automatica). */
function chiudi(esito) {
    const c = attivo();
    if (!c) return { ok: false, error: "nessun cantiere aperto" };
    c.stato = "chiuso";
    c.chiuso = _ora();
    c.esito = String(esito || "").slice(0, 4000);
    _diario(c, { tipo: "chiusura", testo: c.esito });
    try {
        _dir(STORICO);
        fs.writeFileSync(path.join(STORICO, c.id + ".json"), JSON.stringify(c, null, 2), "utf8");
    } catch (_) {}
    _scrivi(c);
    return { ok: true, cantiere: c };
}

// --- la guardia ----------------------------------------------------------------

/**
 * IL PUNTO CHIAVE. Ogni automatismo che sta per sovrascrivere un file chiede qui.
 *
 * @param {string} file   nome file (relativo a src/ o assoluto)
 * @param {string} chi    chi sta chiedendo ("selfHeal", "rollback", "bugHunter/hermes", "apply-change", ...)
 * @param {object} o      motivo (perché vuole toccarlo), emergenza (true = file rotto, il server non parte)
 * @returns {{consentito:boolean, motivo:string, cantiere?:object, fontePrima?:string}}
 */
function guardia(file, chi, o = {}) {
    const c = attivo();
    const n = normalizza(file);
    if (!c || !n || !c.files.includes(n)) return { consentito: true, motivo: "nessun cantiere su questo file" };

    if (o.emergenza) {
        // Il file protetto non compila: se lo lasciamo così l'app non parte, e un
        // cantiere che blocca l'app non protegge niente. Si ripara, ma la versione
        // a metà si archivia prima (salvaVersioneRotta) e resta nel diario.
        _diario(c, { tipo: "emergenza", file: n, chi, testo: o.motivo || "file non compilabile: riparazione consentita" });
        c.ultimoTocco = _ora(); _scrivi(c);
        return { consentito: true, emergenza: true, cantiere: c, fontePrima: fontePrima(n),
            motivo: "file protetto ma non compilabile: riparazione consentita, versione rotta archiviata" };
    }

    c.blocchi++;
    c.ultimoBlocco = { chi, file: n, quando: _ora(), motivo: o.motivo || null };
    _diario(c, { tipo: "blocco", chi, file: n, testo: o.motivo || "tentativo di sovrascrittura bloccato" });
    _scrivi(c);
    return {
        consentito: false, cantiere: c,
        motivo: "🔒 «" + n + "» fa parte del cantiere aperto «" + c.titolo + "»: "
            + chi + " non può sovrascriverlo finché non chiudi il cantiere."
    };
}

/** Versione secca: true se il file è sotto cantiere (senza registrare nulla). */
function protetto(file) {
    const c = attivo();
    const n = normalizza(file);
    return !!(c && n && c.files.includes(n));
}

/**
 * Un intero automatismo può chiedere se è il momento di lavorare. Usato dalle
 * manutenzioni che riscrivono file a piacere (Hermes, simulazione disastro):
 * lì non basta proteggere i singoli file, va fermata l'operazione.
 */
function manutenzioneAmmessa(chi) {
    const c = attivo();
    if (!c) return { ammessa: true };
    _diario(c, { tipo: "blocco", chi, testo: "manutenzione rinviata: cantiere aperto" });
    c.blocchi++; _scrivi(c);
    return {
        ammessa: false, cantiere: { id: c.id, titolo: c.titolo, files: c.files },
        motivo: "🔒 Cantiere aperto («" + c.titolo + "»): " + chi + " è rinviata per non sovrascrivere il lavoro in corso. "
            + "Chiudi il cantiere (o forza esplicitamente) e rilancia."
    };
}

// --- ripresa dopo un'interruzione ---------------------------------------------

/**
 * «Riprendi da dove ti sei interrotto», ma scritto dai fatti invece che dalla
 * memoria. Restituisce lo stato + un testo pronto da incollare come mandato al
 * modello: obiettivo, cosa è già stato fatto, qual è il prossimo passo.
 */
function ripresa() {
    const c = attivo();
    if (!c) return { ok: false, aperto: false, testo: "Nessun cantiere aperto: non c'è lavoro interrotto da riprendere." };

    const voci = diario(c, 400);
    const passi = voci.filter(v => v.tipo === "passo");
    const blocchi = voci.filter(v => v.tipo === "blocco");
    const fatti = passi.slice(-12).map((p, i) => "  " + (passi.length - Math.min(12, passi.length) + i + 1) + ". " + p.testo);

    const testo = [
        "=== RIPRENDI IL CANTIERE «" + c.titolo + "» ===",
        "Aperto: " + c.aperto + (c.sospeso ? "  ⚠️ fermo da più di 24h" : ""),
        c.obiettivo ? "Obiettivo: " + c.obiettivo : null,
        "",
        "File del cantiere (protetti dagli automatismi):",
        ...c.files.map(f => "  - " + f),
        "",
        passi.length ? "Passi già fatti (" + passi.length + "):" : "Nessun passo registrato ancora.",
        ...fatti,
        "",
        "PROSSIMO PASSO: " + (c.prossimo || "(non registrato — riparti dall'ultimo passo fatto)"),
        blocchi.length ? "\nNota: " + blocchi.length + " tentativi di sovrascrittura sono stati bloccati (vedi diario)." : null,
        "",
        "Continua da qui. Non ricominciare da capo e non toccare file fuori dall'elenco."
    ].filter(v => v !== null).join("\n");

    return {
        ok: true, aperto: true, cantiere: c,
        passiFatti: passi.length, bloccati: blocchi.length,
        prossimo: c.prossimo || null,
        testo
    };
}

/** Stato compatto per il telefono. */
function stato() {
    const c = attivo();
    if (!c) return { aperto: false };
    return {
        aperto: true, id: c.id, titolo: c.titolo, obiettivo: c.obiettivo,
        files: c.files, passi: c.passi, blocchi: c.blocchi,
        prossimo: c.prossimo || null, ultimoPasso: c.ultimoPasso || null,
        ultimoBlocco: c.ultimoBlocco || null,
        sospeso: !!c.sospeso, aperturaIso: c.aperto, ultimoTocco: c.ultimoTocco,
        pinPiattaforma: c.pinPiattaforma || null
    };
}

/** Elenco dei cantieri chiusi (per ritrovare un lavoro vecchio). */
function storico(limite = 20) {
    try {
        return fs.readdirSync(STORICO).filter(f => f.endsWith(".json")).sort().slice(-limite).reverse()
            .map(f => { try { const c = JSON.parse(fs.readFileSync(path.join(STORICO, f), "utf8")); return { id: c.id, titolo: c.titolo, aperto: c.aperto, chiuso: c.chiuso, files: c.files, esito: (c.esito || "").slice(0, 200) }; } catch (_) { return null; } })
            .filter(Boolean);
    } catch (_) { return []; }
}

module.exports = {
    apri, chiudi, proteggi, passo, tocca, appunta,
    attivo, stato, ripresa, diario, storico,
    guardia, protetto, manutenzioneAmmessa,
    fontePrima, salvaVersioneRotta, normalizza,
    BASE, SOSPENSIONE_MS
};
