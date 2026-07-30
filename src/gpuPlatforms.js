"use strict";

/**
 * gpuPlatforms — "Cacciatore di piattaforme GPU" (tipo Kaggle).
 *
 * ★ 2026-07-27 — L'utente vuole ospitare i SUOI modelli abliterated (senza filtri)
 * su GPU gratis/ economiche, oltre a Kaggle. Questo modulo è il catalogo di
 * confronto: per ognuna dice pro / contro / come si accende / se Antigravity la
 * comanda a distanza. NON crea account: è informazione + (per Kaggle) il comando
 * di accensione/spegnimento che gia esiste in kaggleWaker.
 *
 * Le piattaforme "compute" (Kaggle/Colab/Modal/RunPod) sono DIVERSE dai provider
 * API (Groq/NVIDIA/...): qui TU porti il modello, li. I provider API li trova
 * invece bountyHunter.js. Questo modulo completa il quadro.
 *
 * Campi per piattaforma:
 *   id, name, kind (free|paid|freemium)
 *   freeGpu       vero se ha GPU gratis
 *   alwaysOn      vero se il server resta acceso 24/7 (Kaggle/Colab NO)
 *   uncensoredOk  se i modelli senza filtri (abliterated) sono ammessi nei termini
 *   pros[], cons[], howto, costo, remote  -> "remoto" = Antigravity puo accenderlo
 */

const PLATFORMS = [
  {
    id: "kaggle",
    url: "https://www.kaggle.com/code",
    name: "Kaggle Notebooks (GPU)",
    kind: "free",
    freeGpu: true,
    alwaysOn: false,
    uncensoredOk: true,           // è IL TUO notebook privato, nessuno lo guarda
    remote: true,                // kaggleWaker accende/spegne via API
    costo: "0€ — 30h GPU/settimana (quota settimanale, si resetta il lunedi)",
    pros: [
      "GPU gratis (spesso P100/T4) senza carta di credito",
      "Tuoi modelli abliterated: nessuno controlla cio' che ospiti (notebook privato)",
      "Tunnel ngrok con dominio fisso gia cablato in Antigravity",
      "Accensione da remoto gia pronta (kaggle:: dal telefono)"
    ],
    cons: [
      "Solo 30h/settimana: se bruci la quota, niente GPU fino a lunedi",
      "Avvio lento: il download dei modelli (14B/30B) puo volerci minuti",
      "Il notebook si addormenta se resta inattivo troppo a lungo"
    ],
    howto: "Antigravity accende il notebook su richiesta (kaggle::). La quota si controlla dal pannello chiavi.",
    note: "La tua corsia abliterated coder (Qwen2.5-Coder 14B / Qwen3-Coder 30B MoE) gira qui."
  },
  {
    id: "colab",
    url: "https://colab.research.google.com/",
    name: "Google Colab (free tier)",
    kind: "freemium",
    freeGpu: true,
    alwaysOn: false,
    uncensoredOk: false,          // termini Google: niente modelli vietati/NSFW
    remote: false,
    costo: "0€ free / ~10-12€ mese Colab Pro",
    pros: [
      "GPU gratis subito, interfaccia notebook familiare",
      "Facile montarci Ollama + ngrok"
    ],
    cons: [
      "Si disconnette dopo ~12h e la RAM puo essere raschiata",
      "ngrok free su Colab e instabile e rischia il ban dell'account",
      "I modelli abliterated violano i termini Google -> rischio sospensione",
      "Non gestibile a distanza in modo affidabile"
    ],
    howto: "Sconsigliato per i tuoi modelli senza filtri. Va bene solo per test veloci di modelli 'puliti'.",
    note: "Usalo solo per prove, non come server permanente dell'app."
  },
  {
    id: "modal",
    url: "https://modal.com/",
    name: "Modal (free tier GPU)",
    kind: "freemium",
    freeGpu: true,
    alwaysOn: true,               // gli app Modal restano attivi finche il processo vive
    uncensoredOk: true,           // i tuoi container, nessuno li censura
    remote: false,                // da cablare: servirebbe token Modal nel .env
    costo: "0€ free tier (GPU condivisa, timeout) / poi a consumo",
    pros: [
      "Container Python persistenti: ci metti Ollama e resta acceso",
      "Nessun termine che vieta i modelli abliterated (sono i tuoi container)",
      "Tunnel locale stabili, meglio di ngrok free",
      "Piu flessibile di Kaggle (niente quota settimanale rigida)"
    ],
    cons: [
      "Il free tier e limitato (GPU condivisa, timeout sulle funzioni)",
      "Serve un account Modal + token API (non ancora cablato in Antigravity)",
      "Per un server 24/7 vero serve il tier a pagamento"
    ],
    howto: "Da aggiungere: con MODAL_TOKEN nel .env si puo fare un'app Ollama esposta e farla puntare al failover come Kaggle.",
    note: "Migliore alternativa FREE a Kaggle per un server tuo sempre on."
  },
  {
    id: "runpod",
    url: "https://www.runpod.io/",
    name: "RunPod (GPU economica 24/7)",
    kind: "paid",
    freeGpu: false,
    alwaysOn: true,
    uncensoredOk: true,
    remote: false,                // da cablare con RUNPOD_API_KEY
    costo: "da ~0,15€/ora di GPU (es. RTX 4090/24GB) — si paga solo se acceso",
    pros: [
      "GPU sempre accessa 24/7: il tuo abliterated e disponibile quando vuoi",
      "Nessun limite sui modelli: ci metti quello che vuoi",
      "Prezzi bassi (molto meno di un VPS con GPU)",
      "Template 'Ollama' pronti: si avvia in un click"
    ],
    cons: [
      "A pagamento (ma economico: pochi euro al giorno per una 4090)",
      "Serve un account RunPod + API key (non ancora cablato in Antigravity)",
      "Il container si ferma se finisci il credito"
    ],
    howto: "Da aggiungere: con RUNPOD_API_KEY si puo avviare/spegnere il pod da remoto (come Kaggle) e puntarlo al failover.",
    note: "La scelta migliore se vuoi il tuo modello abliterated SEMPRE disponibile invece di dipendere dalla quota Kaggle."
  },
  {
    id: "huggingface",
    url: "https://huggingface.co/spaces",
    name: "HuggingFace Spaces (GPU)",
    kind: "freemium",
    freeGpu: true,
    alwaysOn: false,
    uncensoredOk: false,          // HF proibisce i modelli abliterated/NSFW nei termini
    remote: false,
    costo: "0€ CPU / GPU a credito",
    pros: [
      "Hosting Docker facile, ci puoi mettere Ollama",
      "Community enorme di modelli"
    ],
    cons: [
      "I modelli 'abliterated/uncensored' violano i termini di HF -> rischio chiusura repo",
      "Spazio disco e RAM limitati nel free"
    ],
    howto: "Sconsigliato per i tuoi modelli senza filtri. Va bene per modelli 'puliti' da far girare in cloud.",
    note: "Usalo solo con modelli che rispettano i termini HF."
  },
  {
    id: "lightning",
    url: "https://lightning.ai/studios",
    name: "Lightning AI Studios (GPU free tier)",
    kind: "freemium",
    freeGpu: true,
    alwaysOn: false,
    uncensoredOk: true,           // i tuoi Studio, container tuoi
    remote: false,                // da cablare con token Lightning
    costo: "0€ — ~22 ore GPU/mese gratis (free tier), poi a consumo",
    pros: [
      "22 ore di GPU al mese gratis senza carta",
      "Ambiente 'Studio' persistente: ci installi Ollama e resta configurato",
      "Piu' stabile di Colab, tunnel piu' affidabili"
    ],
    cons: [
      "22 ore/mese finiscono in fretta se lo tieni acceso",
      "Serve account Lightning + token (non ancora cablato in Antigravity)"
    ],
    howto: "Da aggiungere: con LIGHTNING_TOKEN nel .env si potrebbe accendere lo Studio e puntarlo al failover come Kaggle.",
    note: "Buona alternativa a Kaggle per ore GPU gratis su un ambiente piu' stabile."
  },
  {
    id: "paperspace",
    url: "https://www.paperspace.com/",
    name: "Paperspace Gradient (free GPU)",
    kind: "freemium",
    freeGpu: true,
    alwaysOn: false,
    uncensoredOk: true,
    remote: false,
    costo: "0€ free GPU (M4000/P5000 quando disponibili) / ~8€ mese per priorita'",
    pros: [
      "GPU gratis (secondo disponibilita') su notebook Gradient",
      "I tuoi notebook, nessuno controlla i modelli",
      "Sessioni piu' lunghe di Colab"
    ],
    cons: [
      "Le GPU gratis sono 'a disponibilita': a volte non ce ne sono",
      "Auto-shutdown dopo qualche ora di inattivita'",
      "Serve account + API key (non ancora cablato)"
    ],
    howto: "Da aggiungere: con PAPERSPACE_API_KEY si potrebbe avviare/spegnere un notebook e puntarlo al failover.",
    note: "Alternativa free a Kaggle, ma le GPU gratis non sono sempre disponibili."
  },
  {
    id: "vastai",
    url: "https://vast.ai/",
    name: "Vast.ai (GPU affitto economico)",
    kind: "paid",
    freeGpu: false,
    alwaysOn: true,
    uncensoredOk: true,
    remote: false,                // da cablare con VAST_API_KEY
    costo: "da ~0,10€/ora (marketplace: GPU di privati, prezzi bassissimi)",
    pros: [
      "GPU 24/7 a prezzi minimi (marketplace tra privati)",
      "Nessun limite sui modelli: metti quello che vuoi",
      "Scegli tu la GPU (dalla piccola alla H100)",
      "Template Ollama/vLLM pronti"
    ],
    cons: [
      "A pagamento (ma economico, si paga a ore)",
      "Affidabilita' variabile (macchine di privati)",
      "Serve account + API key (non ancora cablato)"
    ],
    howto: "Da aggiungere: con VAST_API_KEY si affitta/spegne un'istanza da remoto (come Kaggle) e si punta al failover.",
    note: "La piu' economica per un abliterated sempre acceso, se accetti macchine di privati."
  },
  {
    id: "salad",
    url: "https://salad.com/",
    name: "SaladCloud (GPU community economica)",
    kind: "paid",
    freeGpu: false,
    alwaysOn: true,
    uncensoredOk: true,
    remote: false,
    costo: "da ~0,10€/ora (GPU di gaming PC condivisi)",
    pros: [
      "Prezzi tra i piu' bassi (GPU consumer condivise)",
      "Container tuoi, nessun controllo sui modelli",
      "Bene per inferenza 24/7 a basso costo"
    ],
    cons: [
      "A pagamento; nodi consumer, meno affidabili di un datacenter",
      "Setup container un po' piu' tecnico",
      "Serve account + API key (non ancora cablato)"
    ],
    howto: "Da aggiungere: deploy di un container Ollama e puntarlo al failover.",
    note: "Alternativa economica a RunPod per un modello abliterated sempre disponibile."
  }
];

// ★ 2026-07-30 — PIATTAFORME AGGIUNTIVE dal catalogo preconfigurato
// (providerCatalog.PLATFORMS_EXTRA): Beam, Cerebrium, Koyeb, Fly.io, TensorDock,
// JarvisLabs, Novita GPU, SageMaker Studio Lab, Saturn, Thunder, Prime Intellect,
// Hyperstack. Le voci qui sopra VINCONO (Kaggle è cablata e ha lo stato live).
try {
  const extra = require("./providerCatalog").PLATFORMS_EXTRA || [];
  for (const p of extra) if (!PLATFORMS.some(x => x.id === p.id)) PLATFORMS.push(p);
} catch (_) { /* catalogo assente: si resta con le piattaforme di base */ }

/**
 * Stato Kaggle (riusa kaggleWaker). Per le altre piattaforme ritorna solo i metadati.
 * Ritorna Promise<{ platforms:[...con stato...], kaggle:{...} }>.
 */
async function summary() {
  let kaggleState = { available: false, up: false, host: null, quota: null, error: null };
  try {
    const kw = require("./kaggleWaker");
    kaggleState.host = kw.KAGGLE_HOST || null;
    kaggleState.up = !!(await kw.isUp());
    kaggleState.available = true;
    try { kaggleState.quota = await kw.quota(); } catch (e) { kaggleState.error = e.message; }
  } catch (e) { kaggleState.error = "kaggleWaker non disponibile: " + e.message; }

  const platforms = PLATFORMS.map(p => Object.assign({}, p, {
    statusNote: p.id === "kaggle" ? (kaggleState.up ? "✅ acceso" : "🔴 spento") : null
  }));
  return { platforms, kaggle: kaggleState };
}

module.exports = { PLATFORMS, summary };
