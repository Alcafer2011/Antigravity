"use strict";
/**
 * platformGuide — ASSISTENTE DI CONFIGURAZIONE GUIDATA (come faceva Claude Code,
 * ma dentro Antigravity e in italiano semplice).
 * Scegli la piattaforma -> ti dice:
 *   - quanto è grande il modello che ci sta
 *   - cosa incollare nel notebook / console
 *   - quali "spazi" (ngrok / URL pubblico / localhost:8790) girano e come raggiungerli
 *   - cosa fa Antigravity da sola vs cosa devi fare tu (una tantum)
 * Inoltre: per Kaggle salva il modello come DATASET (memoria sempre disponibile,
 * non sul PC, non su HF) — come vuole l'utente.
 */
function guide(name) {
  const N = (name || "").toLowerCase();
  if (N === "kaggle") return kaggle();
  if (N === "modal") return modal();
  if (N === "lightning") return lightning();
  if (N === "paperspace") return paperspace();
  // panoramica di tutte
  return {
    ok: true,
    piattaforme: ["kaggle", "modal", "lightning", "paperspace"],
    msg: "Scegli una piattaforma con /platform/guide?name=kaggle (o modal/lightning/paperspace). " +
         "Kaggle e' quella gia' pronta: hai le chiavi e Antigravity puo' accenderla."
  };
}

function kaggle() {
  return {
    ok: true, name: "kaggle",
    maxModello: "Fino a ~20 GB a file (limite dataset Kaggle). Un 13B in GGUF q4 (~8GB) ci sta tranquillo; un 70B q4 (~40GB) va diviso o usi Modal/Lightning.",
    quota: "GPU gratis ~30 ore/settimana (P100/T4). Il notebook si spegne da solo se superi il tempo: il modello resta nel DATASET, non perdi nulla.",
    doveStaIlModello: "Su un Kaggle DATASET (memoria tua, sempre disponibile). NON sul PC, NON su HuggingFace. Antigravity lo scarica li' dentro.",
    cosaFareTuUnaTantum: [
      "1) Hai gia' l'account Kaggle e la API key (già nel .env come KAGGLE_USERNAME/KAGGLE_KEY).",
      "2) Crea un Dataset su Kaggle (una volta sola): Antigravity ti da' lo script 'kaggle datasets create'.",
      "3) Avvia il notebook GPU (Antigravity lo fa da sola con kaggleWaker)."
    ],
    cosaFaAntigravity: [
      "Accende la GPU Kaggle (kaggleWaker).",
      "Genera lo script di download da HF verso il tuo Dataset.",
      "Ti dà il comando ngrok da incollare nel notebook per renderlo raggiungibile dal telefono."
    ],
    scriptDownloadVersoDataset: [
      "# nel notebook Kaggle (Antigravity lo prepara):",
      "import os",
      "os.makedirs('/kaggle/working/mio-modello', exist_ok=True)",
      "os.system('huggingface-cli download <REPO_HF> --local-dir /kaggle/working/mio-modello')",
      "# poi: kaggle datasets create -p /kaggle/working/mio-modello  (lo fa Antigravity)"
    ].join("\n"),
    tunnelRaggiungibile: "Nel notebook incolla: !ngrok http 5000  -> ti da' un URL pubblico. Antigravity (e il tuo telefono) ci parla sopra. Oppure resta su localhost:8790 se usi il PC.",
    limiti: "Non puoi superare ~20GB a file. Se il modello e' piu' grosso, Antigravity ti suggerisce Modal o Lightning."
  };
}

function modal() {
  return {
    ok: true, name: "modal",
    maxModello: "Quasi illimitato: i Volume Modal tengono decine di GB. Un 70B q4 ci sta.",
    quota: "Crediti una-tantum ~$30 (free tier). Dopo finisce: serve ricarica (a pagamento, quindi fermati a Kaggle se vuoi gratis).",
    doveStaIlModello: "Su un Modal Volume (persistente).",
    cosaFareTuUnaTantum: [
      "1) Crea account Modal.dev.",
      "2) Incolla MODAL_TOKEN nel .env (Antigravity ti dira' dove).",
      "3) Lancia 'modal token set' una volta."
    ],
    cosaFaAntigravity: ["Genera lo script Modal che monta il Volume, scarica da HF e serve il modello.", "Ti dà l'URL pubblico di Modal."],
    tunnelRaggiungibile: "Modal da' un URL .modal.run pubblico automatico.",
    limiti: "Dopo i $30 free diventa a pagamento: se vuoi SOLO gratis, usa Kaggle."
  };
}

function lightning() {
  return {
    ok: true, name: "lightning",
    maxModello: "Decine di GB sui volumi Lightning.",
    quota: "Free tier ~22 ore/mese (Studio community).",
    doveStaIlModello: "Sul cloud Lightning (persistente).",
    cosaFareTuUnaTantum: ["1) Account lightning.ai.", "2) Incolla LIGHTNING_TOKEN nel .env."],
    cosaFaAntigravity: ["Genera lo script Lightning che scarica da HF e serve il modello."],
    tunnelRaggiungibile: "Lightning Studio da' URL pubblico.",
    limiti: "Solo ~22h/mese gratis."
  };
}

function paperspace() {
  return {
    ok: true, name: "paperspace",
    maxModello: "Dipende dal piano; free e' molto limitato oggi.",
    quota: "Le istanze Free sono state rimosse: serve un piano a pagamento. NON gratis.",
    doveStaIlModello: "Su Gradient Storage (a pagamento).",
    cosaFareTuUnaTantum: ["Account paperspace.com + PAPERSPACE_API_KEY."],
    cosaFaAntigravity: ["Genera lo script, ma attenzione: non e' gratis."],
    tunnelRaggiungibile: "URL Gradient.",
    limiti: "NON gratuito: se vuoi gratis, usa Kaggle/Modal/Lightning. Paperspace escluso."
  };
}

module.exports = { guide };
