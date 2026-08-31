# Generato da Antigravity (notebookTemplate) — 2026-07-31T21:52:44.787Z
# Modello: hf.co/bartowski/Qwen2.5-Coder-14B-Instruct-abliterated-GGUF:Q6_K   GPU: T4   contesto: 32768
#
# Deploy:  python -m modal deploy modal_app.py
# Stop:    python -m modal app stop antigravity-ollama
#
# @modal.web_server espone la porta 11434 di Ollama con un URL https stabile:
# niente ngrok, niente dominio da rinnovare.

import modal

MODELLO = "hf.co/bartowski/Qwen2.5-Coder-14B-Instruct-abliterated-GGUF:Q6_K"
CONTESTO = "32768"

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

app = modal.App("antigravity-ollama", image=immagine)

# I pesi vivono in un volume: si scaricano UNA volta sola. Senza questo, ogni
# avvio ripaga i minuti di download del modello.
modelli = modal.Volume.from_name("antigravity-ollama-modelli", create_if_missing=True)


@app.function(
    gpu="T4",
    volumes={"/modelli": modelli},
    timeout=60 * 60,
    scaledown_window=300,
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
