"use strict";
/**
 * rollback — RIPRISTINA L'ULTIMO BACKUP BUONO (blocco 5, n.13).
 * L'utente preme "torna indietro" e l'app ripristina un file alla sua ultima
 * copia sana. Sicuro: prima di ripristinare, salva la versione attuale in un
 * backup aggiuntivo (non cancella mai senza salvataggio).
 */
const fs = require("fs");
const path = require("path");

const SRC = __dirname;
const BACKUP_DIRS = [
  path.join(SRC, ".self-heal-backup"),
  path.join(process.env.USERPROFILE || "C:\\Users\\infoa", "ANTIGRAVITY_COPIE_ELIMINATE"),
];

// Trova l'ultimo backup disponibile per un file.
function _findBackup(name) {
  let best = null;
  for (const d of BACKUP_DIRS) {
    if (!fs.existsSync(d)) continue;
    // cerca ricorsivamente il file con quel nome
    const walk = (dir) => {
      for (const f of fs.readdirSync(dir)) {
        const fp = path.join(dir, f);
        try {
          if (fs.statSync(fp).isDirectory()) { if (f !== "node_modules") walk(fp); }
          else if (f === name && (!best || fs.statSync(fp).mtimeMs > best.mtime)) best = { fp, mtime: fs.statSync(fp).mtimeMs };
        } catch (_) {}
      }
    };
    walk(d);
  }
  return best;
}

/**
 * Ripristina `name` dall'ultimo backup.
 *
 * ★ 2026-07-30 — Se il file fa parte di un CANTIERE aperto, il ripristino si
 * FERMA: "torna indietro" premuto per sbaglio dal telefono era uno dei modi in
 * cui il lavoro in corso spariva. Si può comunque forzare passando force:true
 * (allora il cantiere lo registra nel diario), e il punto di ritorno del
 * cantiere ("com'era prima che cominciassi") resta sempre disponibile.
 *
 * @param {string} name
 * @param {object} o  force (true = ripristina lo stesso)
 * @returns { ok, restoredFrom, backedUpCurrent?, error?, cantiere? }
 */
function rollback(name, o = {}) {
  try {
    const target = path.join(SRC, name);
    if (!fs.existsSync(target)) return { ok: false, error: "file non esistente: " + name };

    let cant = null;
    try { cant = require("./cantiere"); } catch (_) {}
    if (cant && cant.protetto(name)) {
      const g = cant.guardia(name, "rollback (torna indietro)", { motivo: "ripristino manuale dell'ultimo backup" });
      if (!g.consentito && !o.force) {
        return { ok: false, bloccato: true, error: g.motivo,
          cantiere: cant.stato(),
          suggerimento: "Se vuoi davvero buttare il lavoro di questo cantiere, richiama con force. "
            + "La versione «com'era prima che cominciassi» è già salvata: " + (cant.fontePrima(name) || "(nessuna: il file non esisteva)") };
      }
    }
    const bak = _findBackup(name);
    if (!bak) return { ok: false, error: "nessun backup trovato per " + name };
    // salva la versione attuale prima di sovrascrivere
    const safety = path.join(SRC, ".rollback-safety", name + "." + Date.now().toString(36) + ".bak");
    fs.mkdirSync(path.dirname(safety), { recursive: true });
    fs.copyFileSync(target, safety);
    // ripristina dal backup
    fs.copyFileSync(bak.fp, target);
    return { ok: true, restoredFrom: bak.fp, backedUpCurrent: safety };
  } catch (e) { return { ok: false, error: e.message }; }
}

module.exports = { rollback, BACKUP_DIRS };
