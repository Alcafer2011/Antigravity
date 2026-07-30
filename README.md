# Antigravity

**Il tuo copilota AI locale e senza filtri, dentro VS Code — e sul telefono.**

Antigravity è un assistente AI che vive sulla tua macchina: apre, legge e analizza qualsiasi file, codice o binario, scrive e modifica progetti, genera immagini e ragiona senza censure. La stessa conversazione è disponibile nel pannello di VS Code **e** sul telefono, in tempo reale.

Tre motori nello stesso pannello — **locale** (privato, senza filtri), **cloud gratuito** (più potenza) e **Claude Code** (il tuo abbonamento) — con instradamento e ripiego automatici.

---

## Cosa sa fare

### 💬 Chat unificata, condivisa col telefono
Una sola conversazione, due schermi. Il pannello dentro VS Code e la pagina web sul telefono (via rete locale / Tailscale) mostrano **la stessa chat**: inizi a scrivere dal computer e continui dal telefono, senza copiare niente. Conversazioni multiple, salvate e con titolo automatico.

### 🧠 Tre motori, instradamento automatico
- **Locale (Ollama):** modelli *uncensored* (abliterati) che girano sul tuo PC, offline e privati. Si avvia da solo se è spento.
- **Cloud (OpenRouter · Groq · Gemini · HuggingFace):** più potenza quando serve. Due canali separati — *normale* e *uncensored* — con **rotazione automatica**: se un modello è occupato o a limite, passa da solo al successivo.
- **🤖 Claude Code:** usa la CLI di Claude già installata e il tuo **abbonamento esistente** — nessuna chiave API da inserire. Testo in streaming, strumenti come schede, la sua TODO list nel pannello Piano, e la **barra dei limiti di utilizzo** (percentuale usata, tipo di finestra, quando si azzera) proprio come nell'app Claude Code.

L'estensione sceglie da sola motore e modello in base alla richiesta; se un canale è esaurito o a limite, **ripiega automaticamente** su un altro (es. limite Claude raggiunto → passa al locale).

### 🤝 Claude + la squadra locale, insieme
Quando usi il provider Claude, l'estensione gli presta **gli stessi strumenti della squadra locale** via MCP: generazione immagini (ComfyUI) e analisi binari (toolchain reverse). Così Claude lavora con la tua cassetta degli attrezzi, e la stessa politica dei permessi vale anche per lui.

### 🤖 Agente con strumenti reali
In modalità **Agente**, il modello non chiacchiera soltanto: *agisce*. Legge file, analizza binari (Detect-It-Easy, pefile, Ghidra headless), cerca nel codice, esegue comandi, scrive file — mostrando il piano e i passi mentre lavora.
- Sui modelli con tool nativi usa il **tool-calling** diretto.
- Sui modelli che sanno solo chattare (molti uncensored cloud) usa un'**armatura ReAct**: il modello scrive le azioni, l'estensione le esegue.

### 🎨 Generazione immagini (ComfyUI)
Chiedi un'immagine in italiano nella chat — *"disegnami un logo con un'aquila"* — e Antigravity avvia ComfyUI da solo, genera l'immagine e te la mostra **dentro la chat**.

### 🜂 Delega ad Hermes
I compiti pesanti e autonomi possono essere delegati all'agente **Hermes** (memoria, skill, sotto-agenti), che lavora a testa bassa e riporta il risultato nella tua chat.

### 🔒 Permessi sotto controllo
Tre politiche selezionabili, valide per **tutti** i motori (Claude compreso):
- **Chiedi** — conferma inline nella chat prima di ogni scrittura o comando;
- **Autonomo** — fa da solo;
- **Sola lettura** — non tocca nulla (a Claude vengono passati solo gli strumenti di lettura).

---

## Installazione

Antigravity coordina strumenti gratuiti open-source. Installa quelli che ti servono: **funziona già con il solo Ollama**, il resto è opzionale.

### 1) Ollama — il motore locale (consigliato)
Scarica da **[ollama.com](https://ollama.com)**, poi da terminale scarica i modelli. Suggeriti per l'uso quotidiano (con hardware ~8 GB VRAM o 32 GB RAM):

```bash
# Agente potente, uncensored, con tool nativi (motore principale)
ollama pull richardyoung/qwen2.5-14b-instruct-abliterated

# Alternativa più veloce (8B) per agente/ragionamento
ollama pull huihui_ai/dolphin3-abliterated:8b

# Coding
ollama pull huihui_ai/qwen2.5-coder-abliterate:7b
```

Il router aggancia da solo i modelli appena scaricati. Ollama si avvia automaticamente quando invii un messaggio in modalità Locale.

### 2) Claude Code — il tuo abbonamento (opzionale)
Se hai un abbonamento Claude, installa la CLI una volta sola:

```bash
npm install -g @anthropic-ai/claude-code
claude            # esegui una volta per accedere
```

Fatto questo, nel pannello compare il provider **🤖 Claude Code** con i suoi modelli (Opus / Sonnet / Haiku) e la barra dei limiti di utilizzo. Nessuna chiave API da configurare.

### 3) ComfyUI — immagini (opzionale)
Installa **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** (o ComfyUI Desktop). Metti almeno un checkpoint nella cartella modelli (`models/checkpoints/`). Con 4 GB di VRAM va bene **SD 1.5**; per SDXL usa `--lowvram`. Antigravity avvia ComfyUI da solo quando chiedi un'immagine.

### 4) Hermes — agente autonomo (opzionale)
Per la delega dei compiti complessi, scarica **Hermes** da GitHub:

```bash
# Nous Research — Hermes / Function Calling
git clone https://github.com/NousResearch/Hermes-Function-Calling
```

Configura la sua `HERMES_HOME` e il modello (un modello con *tool-calling* uncensored, es. `huihui_ai/hermes-3-llama-3.2-abliterated`). Antigravity lo usa come sotto-agente quando serve potenza autonoma.

### 5) Cloud gratuito (opzionale)
Crea un file `.env` nella cartella dell'estensione con le chiavi che hai (tutte gratuite):

```env
OPENROUTER_API_KEY=...     # canale uncensored (modelli :free)
GROQ_API_KEY=...           # velocissimo, canale normale
GOOGLE_API_KEY=...         # Gemini (flash gratis)
HF_TOKEN=...               # HuggingFace
# Chat sul telefono (Tailscale):
MOBILE_TOKEN=...           # un token segreto a tua scelta
MOBILE_PORT=8790
```

Il file `.env` **non** viene mai incluso nel pacchetto: le chiavi restano solo sul tuo PC.

---

## Comandi

| Comando | Cosa fa |
|---|---|
| **Antigravity: Aggiorna modelli locali** | Ripesca i modelli disponibili su Ollama |
| **Antigravity: Stato motore locale** | Mostra la mappa dei ruoli e lo stato |
| **Antigravity: Autonomia squadra** | Cambia la politica dei permessi (chiedi / auto / sola lettura) |
| **Antigravity: Avvia/ferma server mobile** | Accende la chat sul telefono (via Tailscale) |
| **Antigravity: Spegni i motori** | Libera la VRAM (ComfyUI e Ollama) |

---

## Come si usa

1. Apri il pannello **Antigravity** dalla barra laterale.
2. Scrivi in italiano quello che ti serve: una domanda, *"analizza questo file .exe"*, *"genera un'immagine di…"*, *"studia questo progetto"*.
3. Scegli, se vuoi, la modalità (Auto / Agente / Reverse / Codice), il **provider** (Locale / Cloud / Claude Code) e la politica dei permessi.
4. Per usarlo dal telefono: lancia *Avvia server mobile* e apri l'indirizzo sul telefono (stessa chat, in tempo reale).

---

## Perché è diverso (e perché è un prodotto)

- **Un pannello, tre motori.** Locale privato, cloud gratuito e Claude ad abbonamento convivono nella stessa chat, con ripiego automatico: non resti mai a piedi.
- **Privacy prima di tutto.** Il motore locale è offline e senza filtri; niente lascia il PC se non lo decidi tu.
- **Trasparenza su costi e limiti.** Barra d'uso del cloud (token/costo stimato del mese) e barra dei limiti dell'abbonamento Claude, sempre visibili.
- **Stesso assistente ovunque.** VS Code e telefono condividono la conversazione in tempo reale.
- **Estendibile.** Gli strumenti (immagini, reverse engineering) sono esposti via MCP e riusati da tutti i motori.

Antigravity impacchetta in un'unica esperienza pulita ciò che di solito richiede mezza giornata di configurazione tra Ollama, ComfyUI, chiavi cloud e agenti.

---

*Antigravity — locale prima di tutto, senza filtri, sotto il tuo controllo.*
