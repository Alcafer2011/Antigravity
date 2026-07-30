"use strict";

/**
 * notebookTemplate — UNA sorgente, tante piattaforme.
 *
 * ★ 2026-07-30 — Il notebook Kaggle era scritto a mano e copiato a mano nella
 * variante "big": due file quasi identici che divergono al primo ritocco. Qui la
 * ricetta è UNA (installa Ollama → scarica il modello → esponi l'endpoint →
 * resta in ascolto dello spegnimento) e le piattaforme sono solo il modo di
 * confezionarla: notebook .ipynb per Kaggle/Colab/Saturn/SageMaker, script
 * Python per Modal, Dockerfile per Fly/Koyeb/Beam.
 *
 * La configurazione arriva da modelAdvisor (modello+quantizzazione calcolati
 * dalla VRAM) e dal .env (token ngrok, mirror HuggingFace, URL di spegnimento).
 */

const fs = require("fs");
const path = require("path");

/**
 * Normalizza la configurazione. Se non passi il modello, lo chiede all'advisor
 * partendo dalla GPU della piattaforma.
 *
 * @param {object} o  piattaforma, gpu, modello{repo,quant}|null, contesto,
 *                    tunnel ("ngrok"|"nativo"|"nessuno"), dominio, ngrokToken,
 *                    shutdownUrl, mirror (repo HF privato da cui scaricare)
 */
function piano(o = {}) {
    const cfg = {
        piattaforma: o.piattaforma || "kaggle",
        gpu: o.gpu || "T4",
        contesto: o.contesto || 32768,
        tunnel: o.tunnel || "ngrok",
        dominio: o.dominio || null,
        ngrokToken: o.ngrokToken || null,
        shutdownUrl: o.shutdownUrl || null,
        mirror: o.mirror || null,
        modello: o.modello || null
    };
    if (!cfg.modello) {
        const { consiglia } = require("./modelAdvisor");
        const c = consiglia({ gpu: cfg.gpu, contesto: cfg.contesto, uso: o.uso || "coder" });
        if (!c.ok) throw new Error("Nessun modello adatto: " + c.error);
        cfg.modello = { repo: c.scelta.repo, quant: c.scelta.quant, nome: c.scelta.nome, tag: c.scelta.tag };
        cfg.consiglio = c;
    }
    // Con un mirror privato si scarica da lì: più vicino, più veloce, e non
    // dipende dal fatto che la repo originale resti pubblica.
    cfg.tag = cfg.mirror
        ? "hf.co/" + cfg.mirror + ":" + cfg.modello.quant
        : (cfg.modello.tag || ("hf.co/" + cfg.modello.repo + ":" + cfg.modello.quant));
    return cfg;
}

// ---- i pezzi della ricetta, condivisi da tutte le confezioni ------------------

function passoInstalla() {
    return [
        "get_ipython().system('curl -fsSL https://ollama.com/install.sh | sh')",
        "print('Ollama installato')"
    ];
}

function passoAvvia(cfg) {
    return [
        "import os, subprocess, time",
        "os.environ['OLLAMA_HOST'] = '0.0.0.0:11434'",
        "os.environ['OLLAMA_CONTEXT_LENGTH'] = '" + cfg.contesto + "'",
        "os.environ['OLLAMA_FLASH_ATTENTION'] = '1'",
        "os.environ['OLLAMA_KV_CACHE_TYPE'] = 'q8_0'",
        "subprocess.Popen(['ollama', 'serve'])",
        "time.sleep(8)",
        "print('Ollama avviato (contesto " + cfg.contesto + ")')"
    ];
}

function passoModello(cfg) {
    const righe = [];
    if (cfg.mirror) {
        righe.push("# Mirror privato: scarica dal TUO repo HuggingFace (piu' veloce, non dipende dalla repo originale)");
        righe.push("import os");
        righe.push("os.environ['HF_TOKEN'] = os.environ.get('HF_TOKEN', '" + (cfg.hfToken || "") + "')");
    }
    righe.push("get_ipython().system('ollama pull " + cfg.tag + "')");
    righe.push("print('Modello pronto: " + (cfg.modello.nome || cfg.tag) + "')");
    return righe;
}

function passoTunnel(cfg) {
    if (cfg.tunnel !== "ngrok") {
        return ["print('Endpoint locale su :11434 — la piattaforma lo espone da sola.')"];
    }
    return [
        "from pyngrok import ngrok, conf",
        "conf.get_default().auth_token = '" + (cfg.ngrokToken || "") + "'",
        cfg.dominio
            ? "tunnel = ngrok.connect(11434, 'http', domain='" + cfg.dominio + "', host_header='localhost:11434')"
            : "tunnel = ngrok.connect(11434, 'http', host_header='localhost:11434')",
        "print('>>> CORSIA VIVA <<<', tunnel.public_url)"
    ];
}

function passoKeepAlive(cfg) {
    if (!cfg.shutdownUrl) {
        return ["import time", "print('Keep-alive (nessun URL di spegnimento configurato).')",
                "while True: time.sleep(60)"];
    }
    return [
        "import time, requests",
        "SHUTDOWN_URL = '" + cfg.shutdownUrl + "'",
        "print('Keep-alive + ascolto spegnimento da Antigravity...')",
        "while True:",
        "    try:",
        "        r = requests.get(SHUTDOWN_URL + '/?clear=1', timeout=10).json()",
        "        if r.get('stop') and (time.time()*1000 - r['stop']) < 600000:",
        "            print('Stop richiesto da Antigravity -> esco.')",
        "            import os; os._exit(0)",
        "    except Exception:",
        "        pass",
        "    time.sleep(25)"
    ];
}

// ---- confezione 1: notebook (.ipynb) -----------------------------------------

function _cella(righe) {
    const src = righe.map((r, i) => r + (i < righe.length - 1 ? "\n" : ""));
    return { cell_type: "code", metadata: {}, execution_count: null, outputs: [], source: src };
}

/**
 * Notebook Jupyter. Va bene per Kaggle, Colab, Saturn, SageMaker Studio Lab:
 * cambia solo la preparazione iniziale (pyngrok, apt) e i metadati.
 */
function notebook(cfg) {
    const prep = ["get_ipython().system('pip install pyngrok requests -q')"];
    if (cfg.piattaforma === "kaggle") prep.unshift("get_ipython().system('apt-get update -qq && apt-get install -y -qq zstd')");

    const celle = [
        _cella(["import subprocess", "print('GPU:', subprocess.run(['nvidia-smi','-L'],capture_output=True,text=True).stdout)"]),
        _cella(prep.concat(passoInstalla())),
        _cella(passoAvvia(cfg)),
        _cella(passoModello(cfg)),
        _cella(passoTunnel(cfg)),
        _cella(passoKeepAlive(cfg))
    ];
    return {
        cells: celle,
        metadata: {
            kernelspec: { language: "python", display_name: "Python 3", name: "python3" },
            language_info: { name: "python", version: "3.10.0" },
            antigravity: { generato: new Date().toISOString(), piattaforma: cfg.piattaforma, modello: cfg.tag, contesto: cfg.contesto }
        },
        nbformat: 4, nbformat_minor: 5
    };
}

// ---- confezione 2: app Modal (Python) ----------------------------------------

/**
 * Script Modal. Modal non ha bisogno di ngrok: `@modal.web_server` espone la
 * porta con un URL suo, stabile, in https. È il motivo per cui è il primo driver
 * cablato dopo Kaggle.
 */
function appModal(cfg) {
    const nomeApp = cfg.nomeApp || "antigravity-ollama";
    const gpu = cfg.gpuModal || "T4";
    return `# Generato da Antigravity (notebookTemplate) — ${new Date().toISOString()}
# Modello: ${cfg.tag}   GPU: ${gpu}   contesto: ${cfg.contesto}
#
# Deploy:  python -m modal deploy modal_app.py
# Stop:    python -m modal app stop ${nomeApp}
#
# @modal.web_server espone la porta 11434 di Ollama con un URL https stabile:
# niente ngrok, niente dominio da rinnovare.

import modal

MODELLO = "${cfg.tag}"
CONTESTO = "${cfg.contesto}"

immagine = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl")
    .run_commands("curl -fsSL https://ollama.com/install.sh | sh")
    .env({
        "OLLAMA_HOST": "0.0.0.0:11434",
        "OLLAMA_CONTEXT_LENGTH": CONTESTO,
        "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_KV_CACHE_TYPE": "q8_0",
        "OLLAMA_MODELS": "/modelli",
    })
)

app = modal.App("${nomeApp}", image=immagine)

# I pesi vivono in un volume: si scaricano UNA volta sola. Senza questo, ogni
# avvio ripaga i minuti di download del modello.
modelli = modal.Volume.from_name("${nomeApp}-modelli", create_if_missing=True)


@app.function(
    gpu="${gpu}",
    volumes={"/modelli": modelli},
    timeout=60 * 60,
    scaledown_window=${cfg.idleSeconds || 300},
    max_containers=1,
)
@modal.concurrent(max_inputs=20)
@modal.web_server(11434, startup_timeout=60 * 15)
def serve():
    import subprocess, time, urllib.request

    subprocess.Popen(["ollama", "serve"])

    # Aspetta che il server risponda prima di scaricare (ollama pull parla con lui).
    for _ in range(60):
        try:
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            break
        except Exception:
            time.sleep(1)

    presenti = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    if MODELLO.split(":")[0] not in presenti:
        print("Scarico", MODELLO, "(la prima volta ci mette qualche minuto)")
        subprocess.run(["ollama", "pull", MODELLO], check=True)
        modelli.commit()
    else:
        print("Modello gia' nel volume:", MODELLO)

    # Tiene il modello caldo in VRAM: la prima richiesta non paga il caricamento.
    subprocess.run(["ollama", "run", MODELLO, "ok"], capture_output=True)
    print("Pronto:", MODELLO)
`;
}

// ---- confezione 3: Dockerfile (Fly / Koyeb / Beam / Cerebrium) ----------------

function dockerfile(cfg) {
    return `# Generato da Antigravity (notebookTemplate) — ${new Date().toISOString()}
# Modello: ${cfg.tag}
FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:11434 \\
    OLLAMA_CONTEXT_LENGTH=${cfg.contesto} \\
    OLLAMA_FLASH_ATTENTION=1 \\
    OLLAMA_KV_CACHE_TYPE=q8_0

# Il modello viene scaricato al primo avvio dentro il volume montato su /root/.ollama:
# metterlo nell'immagine la farebbe pesare decine di GB e molte piattaforme la rifiutano.
COPY avvio.sh /avvio.sh
RUN chmod +x /avvio.sh
EXPOSE 11434
ENTRYPOINT ["/avvio.sh"]
`;
}

function avvioSh(cfg) {
    return `#!/bin/sh
# Generato da Antigravity — scarica il modello se manca, poi resta in ascolto.
ollama serve &
until curl -sf http://localhost:11434/api/tags >/dev/null; do sleep 1; done
ollama list | grep -q "${cfg.tag.split(":")[0]}" || ollama pull "${cfg.tag}"
ollama run "${cfg.tag}" ok >/dev/null 2>&1
wait
`;
}

// ---- uscita ------------------------------------------------------------------

/**
 * Genera i file per una piattaforma.
 * @returns {{cfg, file:[{nome, contenuto}]}}
 */
function genera(o = {}) {
    const cfg = piano(o);
    const p = cfg.piattaforma;
    let file;

    if (p === "modal") {
        file = [{ nome: "modal_app.py", contenuto: appModal(cfg) }];
    } else if (["flyio", "koyeb", "beam", "cerebrium", "runpod", "docker"].includes(p)) {
        file = [
            { nome: "Dockerfile", contenuto: dockerfile(cfg) },
            { nome: "avvio.sh", contenuto: avvioSh(cfg) }
        ];
    } else {
        // kaggle, colab, saturn, sagemaker-lab, paperspace, lightning, thunder…
        const nb = notebook(cfg);
        file = [{ nome: "notebook.ipynb", contenuto: JSON.stringify(nb, null, 1) }];
        if (p === "kaggle") {
            file.push({ nome: "kernel-metadata.json", contenuto: JSON.stringify({
                id: cfg.slugKaggle || "alcafer2011/notebook39aa15083b",
                title: (cfg.slugKaggle || "notebook39aa15083b").split("/").pop(),
                code_file: "notebook.ipynb",
                language: "python", kernel_type: "notebook",
                is_private: true, enable_gpu: true, enable_tpu: false, enable_internet: true,
                keywords: [], dataset_sources: [], kernel_sources: [], competition_sources: [], model_sources: []
            }, null, 2) });
        }
    }
    return { cfg, file };
}

/** Scrive i file generati in una cartella (creandola). */
function scrivi(cartella, o = {}) {
    const g = genera(o);
    fs.mkdirSync(cartella, { recursive: true });
    const scritti = [];
    for (const f of g.file) {
        const dest = path.join(cartella, f.nome);
        fs.writeFileSync(dest, f.contenuto, "utf8");
        scritti.push(dest);
    }
    return { ok: true, cfg: g.cfg, scritti };
}

module.exports = { piano, genera, scrivi, notebook, appModal, dockerfile, avvioSh };
