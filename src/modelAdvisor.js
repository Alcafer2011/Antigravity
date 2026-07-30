"use strict";

/**
 * modelAdvisor — «che modello ci sta su questa GPU?», con il conto, non a naso.
 *
 * ★ 2026-07-30 — Regola: dalla VRAM della GPU che la piattaforma ti offre esce
 * la taglia + la quantizzazione, calcolate. Niente "secondo me ci sta": si
 * moltiplica il numero di parametri per i bit-per-peso della quantizzazione, si
 * aggiunge la cache del contesto, si confronta con la VRAM utile. Se non ci sta,
 * si scende di quantizzazione o di taglia — nell'ordine, perché un modello più
 * grande quantizzato più stretto batte quasi sempre un modello più piccolo largo.
 *
 * Tutti i modelli in elenco sono ABLITERATED (senza filtri): è la corsia che usi.
 */

/** Bit per peso reali dei formati GGUF più usati (media misurata, non nominale). */
const BPW = { "Q3_K_M": 3.9, "Q4_K_M": 4.8, "Q5_K_M": 5.7, "Q6_K": 6.6, "Q8_0": 8.5 };
const SCALA = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M"];   // dal più largo al più stretto

/**
 * Catalogo. `attivi` = parametri che stanno davvero in VRAM durante l'inferenza:
 * per i MoE (Qwen3-Coder-30B-A3B) i pesi stanno tutti in VRAM, quindi attivi=totali
 * per il calcolo della memoria (i 3B "attivi" riguardano la VELOCITÀ, non lo spazio:
 * è un errore classico e qui è scritto apposta per non rifarlo).
 * `kv32k` = GB di cache KV per 32k di contesto con cache quantizzata q8_0.
 */
const MODELLI = [
    { id: "qwen25-coder-7b",  nome: "Qwen2.5-Coder-7B abliterated",      params: 7.6,  kv32k: 1.0,
      repo: "bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF", uso: "coder" },
    { id: "qwen25-coder-14b", nome: "Qwen2.5-Coder-14B abliterated",     params: 14.8, kv32k: 1.6,
      repo: "bartowski/Qwen2.5-Coder-14B-Instruct-abliterated-GGUF", uso: "coder" },
    { id: "qwen25-coder-32b", nome: "Qwen2.5-Coder-32B abliterated",     params: 32.8, kv32k: 2.6,
      repo: "bartowski/Qwen2.5-Coder-32B-Instruct-abliterated-GGUF", uso: "coder" },
    { id: "qwen3-coder-30b",  nome: "Qwen3-Coder-30B-A3B abliterated (MoE, veloce)", params: 30.5, kv32k: 2.2,
      repo: "bartowski/Qwen3-Coder-30B-A3B-Instruct-abliterated-GGUF", uso: "coder", moe: true },
    { id: "qwen3-32b",        nome: "Qwen3-32B abliterated (generalista)", params: 32.8, kv32k: 2.6,
      repo: "bartowski/Qwen3-32B-abliterated-GGUF", uso: "generale" },
    { id: "llama31-8b",       nome: "Llama-3.1-8B abliterated",          params: 8.0,  kv32k: 1.0,
      repo: "bartowski/Meta-Llama-3.1-8B-Instruct-abliterated-GGUF", uso: "generale" }
];

/** GPU note e la loro VRAM, per non doverla chiedere all'utente. */
const GPU = {
    "t4": 16, "tesla t4": 16, "p100": 16, "tesla p100": 16, "v100": 16,
    "l4": 24, "a10g": 24, "rtx4090": 24, "4090": 24, "rtx3090": 24, "3090": 24,
    "l40s": 48, "a6000": 48, "a100": 40, "a100-40gb": 40, "a100-80gb": 80,
    "h100": 80, "h200": 141, "m4000": 8, "p5000": 16, "rtx2000": 16
};

function vramDi(gpu) {
    if (typeof gpu === "number") return gpu;
    const k = String(gpu || "").toLowerCase().replace(/\s+/g, "");
    for (const nome of Object.keys(GPU)) if (k.includes(nome.replace(/\s+/g, ""))) return GPU[nome];
    return null;
}

function pesoGB(m, quant) { return (m.params * (BPW[quant] || BPW.Q4_K_M)) / 8; }

/**
 * Consiglio per una GPU.
 * @param {object} o  gpu ("T4" o 16), contesto (token, default 32768),
 *                    uso ("coder"|"generale"), oreQuota (per la nota sulla quota)
 * @returns { ok, vramGB, scelta, alternative[], scartati[], spiegazione }
 */
function consiglia(o = {}) {
    const vram = vramDi(o.gpu);
    if (!vram) return { ok: false, error: "GPU non riconosciuta: " + o.gpu + ". Passa i GB di VRAM come numero." };

    const contesto = Math.max(4096, Math.min(o.contesto || 32768, 262144));
    const uso = o.uso || "coder";
    // Margine: driver, attivazioni, frammentazione. 12% è il valore che regge
    // senza far cadere l'inferenza a metà generazione.
    const utile = vram * 0.88;

    // Ordine di preferenza: prima i più grandi, ma a parità sostanziale di taglia
    // vince il MoE perché risponde molto più in fretta (Qwen3-Coder-30B-A3B occupa
    // quanto un 30B pieno e va come un 3B: sulla stessa VRAM è la scelta giusta).
    const candidati = MODELLI.filter(m => uso === "qualsiasi" || m.uso === uso)
        .sort((a, b) => (b.params * (b.moe ? 1.1 : 1)) - (a.params * (a.moe ? 1.1 : 1)));

    const scartati = [];
    let scelta = null;
    const alternative = [];

    // ★ Due passate. Nella prima Q3_K_M è ESCLUSA: per scrivere codice un 32B a
    // Q3 sbaglia le parentesi più di un 14B a Q6, quindi "modello più grande,
    // quantizzazione più stretta" vale fino a Q4 e non oltre. Q3 si usa solo se
    // altrimenti non entrerebbe niente.
    const scalaDecente = SCALA.filter(q => q !== "Q3_K_M");
    let ammesse = scalaDecente;

    for (let passata = 0; passata < 2; passata++) {
      for (const m of candidati) {
        const kv = m.kv32k * (contesto / 32768);
        for (const q of ammesse) {
            const tot = pesoGB(m, q) + kv;
            if (tot <= utile) {
                const voce = {
                    id: m.id, nome: m.nome, repo: m.repo, quant: q, moe: !!m.moe,
                    pesoGB: +pesoGB(m, q).toFixed(1), cacheGB: +kv.toFixed(1), totaleGB: +tot.toFixed(1),
                    margineGB: +(utile - tot).toFixed(1), contesto,
                    tag: "hf.co/" + m.repo + ":" + q
                };
                if (!scelta) scelta = voce; else alternative.push(voce);
                break;                       // per ogni modello si tiene la quantizzazione migliore che entra
            }
        }
      }
      if (scelta) break;                        // la prima passata è bastata
      // Seconda passata: niente entrava a Q4 o meglio. Si apre a Q3_K_M, ma la
      // spiegazione lo dirà chiaramente invece di spacciarlo per una buona scelta.
      ammesse = SCALA;
      scartati.push({ nome: "(tutti)", motivo: "nessun modello entrava a Q4_K_M o meglio: si scende a Q3_K_M, con perdita di qualità visibile sul codice" });
    }

    if (!scelta) {
        for (const m of candidati) {
            scartati.push({ nome: m.nome, motivo: "non entra nemmeno a Q3_K_M (servono ~" + (pesoGB(m, "Q3_K_M") + m.kv32k * (contesto / 32768)).toFixed(1) + " GB)" });
        }
        return { ok: false, vramGB: vram,
            error: "Con " + vram + " GB e " + contesto + " token di contesto non entra nessun modello dell'elenco. Abbassa il contesto o scegli una GPU più grande.",
            scartati };
    }

    const spiegazione = [
        "GPU " + (typeof o.gpu === "number" ? o.gpu + " GB" : o.gpu) + " → " + vram + " GB, utilizzabili ~" + utile.toFixed(1) + " GB (12% di margine per driver e attivazioni).",
        "Scelta: " + scelta.nome + " a " + scelta.quant + " = " + scelta.pesoGB + " GB di pesi + " + scelta.cacheGB + " GB di cache per " + contesto + " token = " + scelta.totaleGB + " GB.",
        "Restano " + scelta.margineGB + " GB liberi.",
        scelta.moe ? "È un MoE: i pesi stanno TUTTI in VRAM (i «3B attivi» riguardano la velocità, non lo spazio), ma risponde molto più in fretta di un 30B pieno." : null,
        scelta.quant === "Q3_K_M" ? "⚠️ Q3_K_M: su questa GPU non entrava niente di meglio. Per scrivere codice la qualità cala in modo visibile — meglio un modello più piccolo su un contesto più corto, o una GPU più grande." : null,
        o.oreQuota ? ("Quota della piattaforma: " + o.oreQuota + " h. A ~" + Math.round(scelta.totaleGB * 1.5) + " min di primo avvio (scaricamento del modello), conviene tenerlo acceso a sessioni lunghe invece che accendere e spegnere.") : null
    ].filter(Boolean).join("\n");

    return { ok: true, vramGB: vram, utileGB: +utile.toFixed(1), contesto, scelta, alternative: alternative.slice(0, 3), scartati, spiegazione };
}

/** Il modello per id (per il generatore di notebook). */
function perId(id) { return MODELLI.find(m => m.id === id) || null; }

module.exports = { consiglia, perId, vramDi, MODELLI, GPU, BPW };
