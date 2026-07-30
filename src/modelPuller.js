"use strict";
/**
 * modelPuller — SUPERPOTERE: scarica modelli UNCENSORED da HuggingFace DIRETTAMENTE
 * SULLA PIATTAFORMA GPU (Kaggle/Modal/Lightning/Paperspace), NON in locale sul PC.
 * L'utente non scarica nulla sul suo computer: il modello finisce nel container/
 * istanza remota, dove poi gira Ollama/vLLM.
 *
 * FUNZIONAMENTO:
 *  - pull(repo, { target }) genera lo script di download (Python che usa HF_TOKEN)
 *    da eseguire SULLA PIATTAFORMA. Se target="kaggle" e kaggleWaker può inoltrarlo,
 *    lo fa; altrimenti salva lo script in models/<repo>/pull_on_<target>.* così il
 *    notebook/container lo lancia.
 *  - HF_TOKEN viene letto dal .env (già presente) e iniettato nello script remoto.
 *
 * SICUREZZA: non scarica nulla in locale. Non cancella. Solo prepara/invia comandi.
 */
const fs = require("fs");
const path = require("path");
const os = require("os");

function _hfToken() {
  try {
    const txt = fs.readFileSync(path.join(os.homedir(), ".env"), "utf8");
    const m = txt.match(/HF_TOKEN\s*=\s*"?([^"\r\n]+)"?/i);
    return m ? m[1].trim() : null;
  } catch (_) { return null; }
}

// Script Python che scarica il repo HF dentro il container (usa HF_TOKEN)
// e poi, se siamo su Kaggle, prepara il SALVATAGGIO COME DATASET (memoria tua,
// sempre disponibile — non sul PC, non su HF), come vuole l'utente.
function _pyScript(repo, pattern, token, makeDataset) {
  const lines = [
    "import os",
    "from huggingface_hub import snapshot_download",
    "os.environ['HF_TOKEN'] = '" + (token || "") + "'",
    "repo = '" + repo + "'",
    "pat = " + JSON.stringify(pattern || "*.gguf"),
    "local = '/kaggle/working/models/' + repo.replace('/', '__') if os.path.exists('/kaggle') else ('./models/' + repo.replace('/', '__'))",
    "os.makedirs(local, exist_ok=True)",
    "snapshot_download(repo_id=repo, allow_patterns=pat, local_dir=local, token=os.environ['HF_TOKEN'])",
    "print('SCARICATO IN:', local)",
    "# --- SALVATAGGIO PERSISTENTE (Kaggle Dataset) ---",
    "if os.path.exists('/kaggle'):",
    "    ds = '/kaggle/working/' + repo.replace('/', '__') + '_dataset'",
    "    os.makedirs(ds, exist_ok=True)",
    "    os.system('cp -r ' + local + '/* ' + ds + '/')",
    "    print('Ora crea il Dataset su Kaggle (una tantum):')",
    "    print('  !kaggle datasets create -p ' + ds + ' -n modello-uncensored')",
    "    print('Il modello resta sempre disponibile nel tuo Dataset, anche a notebook chiuso.')"
  ];
  return lines.join("\n");
}

/**
 * @param {string} repo   es. "huihui-ai/Qwen2.5-Coder-14B-Instruct-abliterated-GGUF"
 * @param {object} opts   { target:"kaggle"|"modal"|"lightning"|"paperspace", pattern? }
 * @returns Promise<{ ok, target, scriptPath?, pushed?, error? }>
 */
function pull(repo, opts = {}) {
  return new Promise((resolve) => {
    const target = opts.target || "kaggle";
    const token = _hfToken();
    const destDir = path.join(__dirname, "models", repo.replace(/\//g, "__"));
    fs.mkdirSync(destDir, { recursive: true });
    const scriptPath = path.join(destDir, "pull_on_" + target + ".py");
    fs.writeFileSync(scriptPath, _pyScript(repo, opts.pattern, token, true), "utf8");

    // Se target=kaggle e kaggleWaker può inoltrarci uno script, prova.
    if (target === "kaggle") {
      try {
        const kw = require("./kaggleWaker");
        if (typeof kw.runScript === "function") {
          kw.runScript(scriptPath).then(r => resolve({ ok: true, target, pushed: true, result: r }))
                                   .catch(e => resolve({ ok: true, target, pushed: false, scriptPath, note: "script pronto, push manuale: " + e.message }));
          return;
        }
      } catch (_) {}
    }
    // Altrimenti: script pronto da eseguire SULLA PIATTAFORMA quando accesa.
    resolve({ ok: true, target, pushed: false, scriptPath,
      note: "Script di download pronto per " + target + ". Eseguilo nel container (ha HF_TOKEN). Kaggle: carica pull_on_" + target + ".py nel notebook." });
  });
}

module.exports = { pull, kind: "hf-pull-remote" };
