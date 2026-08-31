"use strict";
/**
 * diffPreview — DIFF VERO + ANNULLAMENTO PER SINGOLA MODIFICA.
 *
 * ★ 2026-08-01 — Prima l'approvazione di una scrittura mostrava solo i primi 200
 * caratteri di old_string e new_string ("- ...\n+ ..."): senza numeri di riga,
 * senza contesto, e troncati a meta' parola. Impossibile capire davvero cosa si
 * stava approvando. E "torna indietro" (rollback.js) ripristina l'ultima copia
 * SANA di un file per NOME — non lo stato di prima di QUESTA modifica: annullava
 * molto piu' del dovuto, o non trovava nulla.
 *
 * Qui ci sono le due cose che mancavano:
 *   1) unified(): un diff unificato leggibile (stile git), con numeri di riga e
 *      righe di contesto, calcolato con LCS. Nessuna dipendenza esterna.
 *   2) istantanea()/annulla(): prima di ogni scrittura si salva una copia del
 *      file; ogni istantanea ha un id e si annulla singolarmente, in ordine
 *      inverso. E' l'annullamento puntuale che prima non esisteva.
 *
 * Nessuna dipendenza da un modello o da un provider: funziona identico con Nous
 * free, Ollama locale o qualunque altro motore.
 */

const fs = require("fs");
const path = require("path");

const SRC = __dirname;
const UNDO_DIR = path.join(SRC, ".undo");
const INDICE = path.join(UNDO_DIR, "indice.json");
const MAX_ISTANTANEE = 200;          // oltre, si potano le piu' vecchie
const MAX_BYTE_DIFF = 2 * 1024 * 1024; // oltre, niente diff riga-per-riga

// ---------------------------------------------------------------- diff

/** Matrice LCS sulle righe. Ritorna la lista di operazioni (=, -, +). */
function _lcsOps(a, b) {
    const n = a.length, m = b.length;
    // Taglio di sicurezza: su file enormi la matrice esplode. Meglio un diff
    // grezzo che far bloccare l'agente.
    if (n * m > 4_000_000) {
        return [{ op: "-", righe: a }, { op: "+", righe: b }];
    }
    const L = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
    for (let i = n - 1; i >= 0; i--) {
        for (let j = m - 1; j >= 0; j--) {
            L[i][j] = a[i] === b[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
        }
    }
    const ops = [];
    let i = 0, j = 0;
    while (i < n && j < m) {
        if (a[i] === b[j]) { ops.push({ op: "=", riga: a[i], ai: i, bi: j }); i++; j++; }
        else if (L[i + 1][j] >= L[i][j + 1]) { ops.push({ op: "-", riga: a[i], ai: i }); i++; }
        else { ops.push({ op: "+", riga: b[j], bi: j }); j++; }
    }
    while (i < n) { ops.push({ op: "-", riga: a[i], ai: i }); i++; }
    while (j < m) { ops.push({ op: "+", riga: b[j], bi: j }); j++; }
    return ops;
}

/**
 * Diff unificato leggibile tra due testi.
 * @param {string} prima
 * @param {string} dopo
 * @param {object} o  { path, contesto = 3, maxRighe = 400 }
 * @returns {string}
 */
function unified(prima, dopo, o = {}) {
    const contesto = o.contesto == null ? 3 : o.contesto;
    const maxRighe = o.maxRighe == null ? 400 : o.maxRighe;
    prima = String(prima == null ? "" : prima);
    dopo = String(dopo == null ? "" : dopo);

    if (prima === dopo) return "(nessuna differenza)";
    if (prima.length + dopo.length > MAX_BYTE_DIFF) {
        return "(file troppo grande per il diff riga-per-riga: "
            + prima.length + " byte prima, " + dopo.length + " byte dopo)";
    }

    const a = prima.split(/\r?\n/);
    const b = dopo.split(/\r?\n/);
    const ops = _lcsOps(a, b);

    // Raggruppa in blocchi (hunk) attorno alle differenze, con N righe di contesto.
    const interessanti = ops.map((x, k) => (x.op === "=" ? -1 : k)).filter(k => k >= 0);
    if (!interessanti.length) return "(nessuna differenza)";

    const blocchi = [];
    let ini = Math.max(0, interessanti[0] - contesto);
    let fine = Math.min(ops.length - 1, interessanti[0] + contesto);
    for (const k of interessanti.slice(1)) {
        if (k - contesto <= fine + 1) { fine = Math.min(ops.length - 1, k + contesto); }
        else { blocchi.push([ini, fine]); ini = Math.max(0, k - contesto); fine = Math.min(ops.length - 1, k + contesto); }
    }
    blocchi.push([ini, fine]);

    const out = [];
    if (o.path) out.push("--- " + o.path + "  (prima)", "+++ " + o.path + "  (dopo)");
    let righeStampate = 0;
    let troncato = false;

    for (const [da, aa] of blocchi) {
        // numeri di riga di partenza del blocco
        let ra = null, rb = null;
        for (let k = da; k <= aa; k++) {
            if (ra == null && ops[k].ai != null) ra = ops[k].ai + 1;
            if (rb == null && ops[k].bi != null) rb = ops[k].bi + 1;
        }
        const contA = ops.slice(da, aa + 1).filter(x => x.op !== "+").length;
        const contB = ops.slice(da, aa + 1).filter(x => x.op !== "-").length;
        out.push("@@ -" + (ra || 0) + "," + contA + " +" + (rb || 0) + "," + contB + " @@");
        for (let k = da; k <= aa; k++) {
            if (righeStampate >= maxRighe) { troncato = true; break; }
            const x = ops[k];
            const seg = x.op === "=" ? " " : x.op;
            out.push(seg + x.riga);
            righeStampate++;
        }
        if (troncato) break;
    }
    if (troncato) out.push("… (diff troncato a " + maxRighe + " righe)");

    // Riepilogo in cima: quante righe tolte/messe. E' la prima cosa da guardare.
    const tolte = ops.filter(x => x.op === "-").length;
    const messe = ops.filter(x => x.op === "+").length;
    return "▸ " + tolte + " righe tolte, " + messe + " righe aggiunte\n" + out.join("\n");
}

// ---------------------------------------------------------- istantanee

function _leggiIndice() {
    try { return JSON.parse(fs.readFileSync(INDICE, "utf8")); } catch (_) { return []; }
}

function _scriviIndice(arr) {
    try {
        fs.mkdirSync(UNDO_DIR, { recursive: true });
        fs.writeFileSync(INDICE, JSON.stringify(arr, null, 2), "utf8");
    } catch (_) {}
}

/**
 * Salva lo stato attuale di un file PRIMA di modificarlo.
 * Se il file non esiste ancora (creazione), lo registra come "nuovo": annullare
 * significhera' cancellarlo.
 *
 * @param {string} fp   percorso assoluto del file
 * @param {object} o    { tool, motivo }
 * @returns {object}    { id, esisteva }
 */
function istantanea(fp, o = {}) {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const esisteva = fs.existsSync(fp);
    let copia = null;
    try {
        fs.mkdirSync(UNDO_DIR, { recursive: true });
        if (esisteva) {
            copia = path.join(UNDO_DIR, id + "__" + path.basename(fp));
            fs.copyFileSync(fp, copia);
        }
    } catch (e) {
        return { id: null, esisteva, errore: e.message };
    }
    const voce = {
        id, file: fp, copia, esisteva,
        tool: o.tool || "?", motivo: o.motivo || "",
        quando: new Date().toISOString(),
        annullata: false
    };
    const arr = _leggiIndice();
    arr.push(voce);
    // potatura: elimina le piu' vecchie oltre il tetto
    while (arr.length > MAX_ISTANTANEE) {
        const vecchia = arr.shift();
        try { if (vecchia.copia && fs.existsSync(vecchia.copia)) fs.unlinkSync(vecchia.copia); } catch (_) {}
    }
    _scriviIndice(arr);
    return { id, esisteva };
}

/**
 * Annulla una modifica: riporta il file com'era prima di quella istantanea.
 * Senza id, annulla l'ULTIMA non ancora annullata.
 *
 * Rispetta il cantiere come fa rollback.js: se il file appartiene a un cantiere
 * aperto, si ferma salvo force:true. Il lavoro dal telefono non si tocca.
 *
 * @param {object} o { id, force }
 */
function annulla(o = {}) {
    const arr = _leggiIndice();
    const voce = o.id
        ? arr.find(v => v.id === o.id)
        : [...arr].reverse().find(v => !v.annullata);
    if (!voce) return { ok: false, error: o.id ? "istantanea non trovata: " + o.id : "niente da annullare" };
    if (voce.annullata) return { ok: false, error: "istantanea gia' annullata: " + voce.id };

    // Guardia cantiere (stessa regola di rollback.js).
    try {
        const cant = require("./cantiere");
        const nome = path.basename(voce.file);
        if (cant && cant.protetto && cant.protetto(nome)) {
            const g = cant.guardia(nome, "annulla modifica (" + voce.id + ")", { motivo: voce.motivo || "annullamento puntuale" });
            if (!g.consentito && !o.force) {
                return { ok: false, bloccato: true, error: g.motivo, cantiere: cant.stato && cant.stato() };
            }
        }
    } catch (_) { /* cantiere assente: si prosegue */ }

    try {
        if (voce.esisteva) {
            if (!voce.copia || !fs.existsSync(voce.copia)) return { ok: false, error: "copia di sicurezza mancante per " + voce.id };
            // salva lo stato attuale prima di sovrascrivere: annullare non deve mai
            // distruggere senza rete (stessa cautela di rollback.js).
            let sicurezza = null;
            try {
                if (fs.existsSync(voce.file)) {
                    sicurezza = path.join(UNDO_DIR, "prima-di-annullare__" + voce.id + "__" + path.basename(voce.file));
                    fs.copyFileSync(voce.file, sicurezza);
                }
            } catch (_) {}
            fs.copyFileSync(voce.copia, voce.file);
            voce.annullata = true; voce.sicurezza = sicurezza;
            _scriviIndice(arr);
            return { ok: true, file: voce.file, ripristinatoDa: voce.copia, sicurezza };
        }
        // il file non esisteva prima: annullare = rimuoverlo
        if (fs.existsSync(voce.file)) fs.unlinkSync(voce.file);
        voce.annullata = true;
        _scriviIndice(arr);
        return { ok: true, file: voce.file, rimosso: true };
    } catch (e) {
        return { ok: false, error: e.message };
    }
}

/** Ultime N istantanee, piu' recenti prima. */
function elenco(n = 20) {
    return _leggiIndice().slice(-n).reverse().map(v => ({
        id: v.id, file: v.file, tool: v.tool, quando: v.quando,
        annullata: v.annullata, nuovoFile: !v.esisteva
    }));
}

module.exports = { unified, istantanea, annulla, elenco, UNDO_DIR };
