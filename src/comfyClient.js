"use strict";

const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

/**
 * ComfyClient — genera immagini con ComfyUI SENZA aprire ComfyUI.
 *
 * ComfyUI espone un'API HTTP: si manda un "workflow" (il grafo dei nodi, in
 * formato API) a POST /prompt, si aspetta che la coda lo esegua, e si ritira
 * il risultato da GET /history/<id>. Qui dentro:
 *   - se ComfyUI è spento, lo AVVIA da solo (col suo venv) e aspetta che risponda
 *   - costruisce il workflow di Z-Image Turbo (l'unico modello installato)
 *   - ritorna il percorso del PNG prodotto
 *
 * Nota sul modello: si usa Realistic Vision V6 (SD 1.5), l'unico modello che la
 * GPU dell'utente (Quadro T1000, 4 GB VRAM) può far girare davvero. SD 1.5 si
 * carica come CHECKPOINT UNICO (modello+CLIP+VAE in un solo file). Questa è la
 * variante "Hyper" (VAE incorporata): genera in POCHI passi (6, CFG basso),
 * perfetta per una scheda piccola. Grafo txt2img classico SD 1.5.
 */

const HOST = "127.0.0.1";
const PORT = 8188;

const COMFY_ROOT = path.join(os.homedir(), "AppData", "Local", "Comfy-Desktop", "ComfyUI-Installs", "ComfyUI", "ComfyUI");
const COMFY_PY = path.join(COMFY_ROOT, ".venv", "Scripts", "python.exe");
const COMFY_SHARED = path.join(os.homedir(), "AppData", "Local", "Comfy-Desktop", "ComfyUI-Shared");
const COMFY_OUTPUT = path.join(COMFY_SHARED, "output");

const CHECKPOINT = "realisticVisionV60B1_v51HyperVAE.safetensors";

// Negativo di base: tiene lontani gli artefatti tipici di SD 1.5.
const NEG_PROMPT = "(deformed, distorted, disfigured), poorly drawn, bad anatomy, extra limbs, blurry, low quality, watermark, text";

/** Workflow txt2img SD 1.5 (Realistic Vision Hyper) in formato API. */
function workflow({ prompt, width, height, steps, seed, cfg }) {
    return {
        "4": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: CHECKPOINT } },
        "6": { class_type: "CLIPTextEncode", inputs: { text: prompt, clip: ["4", 1] } },
        "7": { class_type: "CLIPTextEncode", inputs: { text: NEG_PROMPT, clip: ["4", 1] } },
        "5": { class_type: "EmptyLatentImage", inputs: { width, height, batch_size: 1 } },
        "3": {
            class_type: "KSampler",
            inputs: {
                seed, steps, cfg,
                // La variante Hyper rende bene con dpmpp_sde + karras a pochi passi.
                sampler_name: "dpmpp_sde", scheduler: "karras", denoise: 1,
                model: ["4", 0], positive: ["6", 0], negative: ["7", 0], latent_image: ["5", 0]
            }
        },
        "8": { class_type: "VAEDecode", inputs: { samples: ["3", 0], vae: ["4", 2] } },
        "9": { class_type: "SaveImage", inputs: { filename_prefix: "antigravity", images: ["8", 0] } }
    };
}

function req(method, urlPath, body) {
    return new Promise((resolve, reject) => {
        const data = body ? Buffer.from(JSON.stringify(body)) : null;
        const r = http.request({
            host: HOST, port: PORT, path: urlPath, method,
            headers: data ? { "Content-Type": "application/json", "Content-Length": data.length } : {},
            timeout: 15000
        }, res => {
            let buf = "";
            res.on("data", c => buf += c);
            res.on("end", () => {
                if (res.statusCode >= 400) return reject(new Error("ComfyUI HTTP " + res.statusCode + ": " + buf.slice(0, 400)));
                try { resolve(JSON.parse(buf)); } catch (_) { resolve(buf); }
            });
        });
        r.on("timeout", () => r.destroy(new Error("timeout")));
        r.on("error", reject);
        if (data) r.write(data);
        r.end();
    });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

class ComfyClient {
    constructor(opts = {}) {
        this.logger = opts.logger || console;
        this.onEvent = opts.onEvent || (() => {});
        this.proc = null;
    }

    installed() { return fs.existsSync(COMFY_PY) && fs.existsSync(path.join(COMFY_ROOT, "main.py")); }

    /**
     * Controlla che i file .safetensors non siano troncati (download interrotti):
     * l'header safetensors dichiara quanti byte di pesi servono; se il file è più
     * piccolo, il modello è incompleto e la generazione fallirebbe con un errore
     * criptico sui tensori. Ritorna la lista dei modelli incompleti (vuota = ok).
     */
    incompleteModels() {
        const bad = [];
        const fp = path.join(COMFY_SHARED, "models", "checkpoints", CHECKPOINT);
        try {
            if (!fs.existsSync(fp)) { bad.push({ name: CHECKPOINT, reason: "mancante" }); return bad; }
            const fd = fs.openSync(fp, "r");
            const b = Buffer.alloc(8); fs.readSync(fd, b, 0, 8, 0);
            const hlen = Number(b.readBigUInt64LE(0));
            const hdr = Buffer.alloc(hlen); fs.readSync(fd, hdr, 0, hlen, 8); fs.closeSync(fd);
            let end = 0;
            const j = JSON.parse(hdr.toString("utf8"));
            for (const k in j) if (j[k].data_offsets) end = Math.max(end, j[k].data_offsets[1]);
            const need = 8 + hlen + end, have = fs.statSync(fp).size;
            if (have < need) bad.push({ name: CHECKPOINT, reason: `incompleto (${(have / 1e6).toFixed(0)} MB su ${(need / 1e9).toFixed(1)} GB)` });
        } catch (e) { bad.push({ name: CHECKPOINT, reason: "illeggibile" }); }
        return bad;
    }

    async isUp() {
        try { await req("GET", "/system_stats"); return true; } catch (_) { return false; }
    }

    /** Avvia ComfyUI se è spento e aspetta che risponda. */
    async ensureUp(onStatus = () => {}) {
        if (await this.isUp()) return true;
        if (!this.installed()) throw new Error("ComfyUI non trovato in " + COMFY_ROOT);

        onStatus("🎨 ComfyUI è spento: lo avvio…");
        // Con --base-directory ComfyUI si aspetta che custom_nodes esista nella base:
        // la cartella condivisa non ce l'ha, la creiamo (vuota, innocua).
        try { fs.mkdirSync(path.join(COMFY_SHARED, "custom_nodes"), { recursive: true }); } catch (_) {}
        // --base-directory: i modelli/output NON stanno nell'installazione ma nella
        //   cartella condivisa di ComfyUI Desktop; senza questo, non trova i checkpoint.
        // --disable-auto-launch: non deve aprire il browser. Resta in background.
        this.proc = spawn(COMFY_PY, [
            "main.py", "--port", String(PORT),
            "--base-directory", COMFY_SHARED,
            "--disable-auto-launch"
        ], {
            cwd: COMFY_ROOT, detached: true, stdio: "ignore", windowsHide: true
        });
        this.proc.unref();

        // Il primo avvio carica torch/CUDA: può volerci un po'.
        for (let i = 0; i < 90; i++) {
            await sleep(2000);
            if (await this.isUp()) { onStatus("🎨 ComfyUI pronto."); return true; }
        }
        throw new Error("ComfyUI non è partito entro 3 minuti.");
    }

    /**
     * Genera un'immagine e ritorna { file, filename } (PNG su disco).
     * @param {object} o { prompt, width, height, steps, seed, onStatus }
     */
    async generate(o = {}) {
        const onStatus = o.onStatus || (() => {});
        const prompt = String(o.prompt || "").trim();
        if (!prompt) throw new Error("prompt mancante");

        // Se i modelli sono scaricati a metà, fermati con un messaggio chiaro
        // invece di lasciare che ComfyUI dia un errore criptico sui tensori.
        const bad = this.incompleteModels();
        if (bad.length) {
            throw new Error("I modelli di ComfyUI non sono scaricati per intero: " +
                bad.map(m => m.name + " (" + m.reason + ")").join(", ") +
                ". Apri ComfyUI Desktop e completa il download del modello Z-Image Turbo, poi riprova.");
        }

        await this.ensureUp(onStatus);

        const wf = workflow({
            prompt,
            // SD 1.5 rende meglio intorno a 512-768; su 4 GB VRAM stiamo prudenti.
            width: Math.min(Math.max(parseInt(o.width) || 768, 256), 1024),
            height: Math.min(Math.max(parseInt(o.height) || 768, 256), 1024),
            // Hyper: pochi passi, CFG basso.
            steps: Math.min(Math.max(parseInt(o.steps) || 6, 1), 20),
            cfg: (typeof o.cfg === "number" && o.cfg > 0) ? o.cfg : 1.5,
            seed: Number.isInteger(o.seed) ? o.seed : Math.floor(Math.random() * 1e15)
        });

        onStatus("🎨 Genero l'immagine…");
        const res = await req("POST", "/prompt", { prompt: wf, client_id: "antigravity" });
        const id = res && res.prompt_id;
        if (!id) throw new Error("ComfyUI non ha accettato il workflow: " + JSON.stringify(res).slice(0, 300));

        // Attende il risultato in coda (Z-Image Turbo a 8 passi è veloce, ma il
        // PRIMO giro carica i pesi in VRAM e può richiedere parecchio).
        for (let i = 0; i < 150; i++) {
            await sleep(2000);
            let hist;
            try { hist = await req("GET", "/history/" + id); } catch (_) { continue; }
            const entry = hist && hist[id];
            if (!entry) continue;

            const st = entry.status || {};
            if (st.status_str === "error") {
                throw new Error("ComfyUI ha fallito l'esecuzione: " + JSON.stringify(st.messages || []).slice(0, 400));
            }
            for (const nodeId of Object.keys(entry.outputs || {})) {
                const imgs = entry.outputs[nodeId].images || [];
                if (imgs.length) {
                    const im = imgs[0];
                    const file = path.join(COMFY_OUTPUT, im.subfolder || "", im.filename);
                    return { file, filename: im.filename };
                }
            }
        }
        throw new Error("ComfyUI non ha prodotto l'immagine entro il tempo massimo.");
    }
}

module.exports = { ComfyClient, COMFY_OUTPUT, COMFY_ROOT };
