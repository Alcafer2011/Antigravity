"use strict";
/**
 * gpuWaker — cablaggio delle piattaforme GPU GRATIS (Modal / Lightning / Paperspace)
 * per ospitare IL TUO modello abliterated sempre acceso. Legge i token dal .env:
 *   MODAL_TOKEN, LIGHTNING_TOKEN, PAPERSPACE_API_KEY
 * Se un token manca, quella piattaforma resta "da configurare" (non la tocchiamo).
 * RunPod/Vast/Salad SONO A PAGAMENTO → non cablate (l'utente vuole GRATIS).
 *
 * Ogni piattaforma, se accesa, esegue uno script che monta Ollama + espone un
 * endpoint che Antigravity può usare come failover (come Kaggle).
 */
const fs = require("fs");
const path = require("path");
const os = require("os");

function _token(name) {
  try {
    const txt = fs.readFileSync(path.join(os.homedir(), ".env"), "utf8");
    const m = txt.match(new RegExp(name + "\\s*=\\s*\"?([^\"\\r\\n]+)\"?", "i"));
    return m ? m[1].trim() : null;
  } catch (_) { return null; }
}

// Stato/assetto delle piattaforme GRATIS cablabili.
const FREE_PLATFORMS = [
  { id: "modal",     tokenEnv: "MODAL_TOKEN",      alwaysOn: true,  note: "Container Python persistenti: Ollama resta acceso. Nessun divieto uncensored." },
  { id: "lightning", tokenEnv: "LIGHTNING_TOKEN",  alwaysOn: false, note: "22h GPU/mese gratis. Studio persistente con Ollama." },
  { id: "paperspace",tokenEnv: "PAPERSPACE_API_KEY",alwaysOn: false, note: "Free GPU (quando disponibile). Notebook tuoi." },
];

/**
 * Ritorna lo stato di ogni piattaforma gratis: configured (hai il token?) + up.
 */
function status() {
  return FREE_PLATFORMS.map(p => {
    const has = !!_token(p.tokenEnv);
    return { id: p.id, configured: has, alwaysOn: p.alwaysOn, note: p.note, uncensoredOk: true };
  });
}

/**
 * Accende una piattaforma (placeholder: la logica reale richiede l'SDK della
 * piattaforma + il token). Se il token manca, ritorna istruzioni per l'utente.
 * Quando l'utente incolla il token, qui si aggiunge la chiamata API reale.
 */
function wake(id) {
  const p = FREE_PLATFORMS.find(x => x.id === id);
  if (!p) return { ok: false, error: "piattaforma sconosciuta: " + id };
  const tok = _token(p.tokenEnv);
  if (!tok) return { ok: false, configured: false,
    instructions: "Manca " + p.tokenEnv + " nel .env. Crea l'account " + id +
      ", copia il token in C:\\Users\\infoa\\.env come " + p.tokenEnv + "=**** poi riprova." };
  // TODO(reale): con il token, chiamare l'SDK della piattaforma e avviare il container Ollama.
  return { ok: true, configured: true, started: "pending-sdk",
    note: "Token presente. Inserire qui la chiamata API " + id + " per avviare Ollama." };
}

module.exports = { status, wake, FREE_PLATFORMS };
