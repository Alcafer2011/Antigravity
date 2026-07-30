# ANTIGRAVITY — REGOLA ASSOLUTA (lettura OBBLIGATORIA prima di toccare qualsiasi file)

> Questo file è la LEGGE per chiunque metta mano ad Antigravity: Hermes, un altro
> agente, o l'utente stesso. VIOLARE UNA REGOLA = RISCHIO DI DISTRUGGERE L'APP.
> Le regole sono anche AUTOMATIZZABILI tramite `src\apply-change.ps1` (vedi fondo).

---

## 1. DOVE STA LA VERITÀ (percorsi)

| Cosa | Percorso | Note |
|------|----------|------|
| **CUORE / SERVER VIVO** | `C:\Users\infoa\src\` | Il server su 8790 parte da `src\heal-and-run.js`. È l'unica fonte di verità del codice. |
| **File chiavi AI** | `C:\Users\infoa\.env` | Il server legge da QUI (rootDir = home). **NON** `src\.env`. Contiene tutte le API key + `MOBILE_TOKEN` + `MOBILE_PORT`. |
| **Estensione VS Code (solo UI)** | `C:\Users\infoa\.vscode\extensions\local-developer.antigravity-1.0.1\` | Interfaccia. NON avvia il server (fa solo `ping` su 8790 dal 2026-07-19). Il suo `src\` DEVE essere speculare al cuore. |
| **Pagina web (UI mobile)** | `C:\Users\infoa\src\mobile-page.html` | Lettura otra ogni richiesta. Modifiche solo-CSS si vedono col refresh. |
| **Versione app** | `C:\Users\infoa\src\mcpServer.js` riga 84 (`version: "1.0.35"`) + `package.json` estensione | La versione si dichiara QUI, non in src\.env. |
| **Log obbligatorio modifiche** | `C:\Users\infoa\src\knowledge\MAINTENANCE-LOG.md` | Ogni modifica va annotata qui (formato in fondo). |
| **Regola assoluta (questo file)** | `C:\Users\infoa\src\knowledge\ANTIGRAVITY-REGOLA-ASSOLUTA.md` | |
| **Backup self-heal** | `C:\Users\infoa\src\.self-heal-backup\` | Copie sane dei file critici; selfHeal le ripristina se un file si corrompe. |
| **Staging copie eliminate** | `C:\Users\infoa\ANTIGRAVITY_COPIE_ELIMINATE\` | Copie reversibili (Antigravity-Clone, Codice-Estensione, vecchi src). NON toccare se non sai. |
| **.vsix (installer)** | `C:\Users\infoa\antigravity-*.vsix` | Pacchetto installazione. NON modificare a mano. |

**REGOLA 0 — IL CUORE È `src\`.** Ogni modifica va fatta in `C:\Users\infoa\src\`.
Dopo aver modificato `src\`, se hai toccato un modulo che esiste ANCHE nell'estensione
(`providerRegistry.js`, `localOrchestrator.js`, `mcpServer.js`, `cloudEngine.js`,
`mobileServer.js`, `heal-and-run.js`, `selfHeal.js`, ecc.), DEVI risincronizzare
l'estensione: copia lo stesso file da `src\` a
`C:\Users\infoa\.vscode\extensions\local-developer.antigravity-1.0.1\src\`.
Lo script `apply-change.ps1` lo fa da solo.

---

## 2. COSA FA OGNI MODULO (mappa rapida)

### Server / core
- **heal-and-run.js** — ENTRY POINT. Avvia `MobileServer` + `LocalOrchestrator`. Se lo tocchi: riavvio server.
- **mobileServer.js** — Web-server locale (porta 8790). API: `/status`, `/keys`, `/keys/check?provider=X`, `/models`, `/send`, `/stop`, `/freeProviders`, `/freeProviders/hunt`, `/addKey`, `/kaggle/*`, `/tor/*`. Auth: `?t=MOBILE_TOKEN`. Se lo tocchi: riavvio server + node --check.
- **localOrchestrator.js** — MOTORE. Sceglie modello/canale, catena di failover, instradamento Ghidra/ZW/Hermes, uncensored. **MODULO PIÙ DELICATO.** Se lo tocchi: riavvio + node --check + test logica.
- **cloudEngine.js** — Failover provider cloud, rate-limit, discovery modelli. Se lo tocchi: riavvio + node --check.
- **providerRegistry.js** — CATALOGO provider (groq, cerebras, venice, ecc.) + `FREE_PROVIDERS` (cacciatore di taglie). Se aggiungi provider: anche `.env` + riavvio.
- **mcpServer.js** — Server MCP (VS Code/agenti esterni). Dichiara `version`. Se cambi versione: anche package.json estensione.
- **selfHeal.js** — Ripristina file corrotti da `.self-heal-backup`. CRITICAL_FILES = lista protetta.
- **serverClient.js** — Client Node vs mobileServer (usato dall'estensione VS Code per condividere la chat).

### Provider / motori
- **claudeEngine.js** — Claude Code come provider (CLI headless). **claudeHook.js** — hook PreToolUse di Claude Code (fail-closed).
- **nousClient.js** — Integrazione Nous Portal (token OAuth, SINGLE-WRITER: non ruotare mai il refresh_token, altrimenti slogga Hermes).
- **kaggleWaker.js** / **kaggleEngine.js** / **kaggleToolProxy.js** — Accende/inferenzia notebook Kaggle (modelli abliterated 14B/30B su GPU, via ngrok). Uncensored failback.
- **localEngine.js** — Motore locale (Ollama).
- **nativeAgent.js** — Loop-agente locale (function-calling Ollama).
- **hermesClient.js** / **hermesAcp.js** — Usa Hermes Agent come lavoratore (CLI / ACP).
- **comfyClient.js** — Genera immagini con ComfyUI (API HTTP).
- **webSearch.js** — Ricerca online (riscritto 2026-07-26).

### Servizi / strumenti RE
- **services.js** — Accende servizi locali (Ollama, ComfyUI).
- **ghidraClient.js** — Ponte HTTP verso GhidraMCP (porta 8080). Reverse engineering live.
- **ghidraHeadless.js** — Analisi Ghidra automatica (analyzeHeadless + script).
- **ghidraLauncher.js** — Avvia Ghidra da solo se spento.
- **reTools.js** — Percorsi strumenti RE (diec.exe, ghidra analyzeHeadless).
- **torBrowser.js** — Lettore Tor lato server (proxy SOCKS 127.0.0.1:9050).
- **gpuPlatforms.js** — Catalogo piattaforme GPU (Kaggle/Colab/Modal/RunPod) per modelli abliterated.
- **bountyHunter.js** — Cacciatore di taglie: trova provider LLM gratuiti online (rotte `/freeProviders/hunt`).
- **learningMemory.js** — Memoria evolutiva (lezioni apprese reiniettate nel prompt).
- **webview.js** — UI webview chat (VS Code).

---

## 3. INST RADAMENTI (come arriva una risposta)

1. Utente scrive in UI (VS Code / telefono) → `mobileServer.js` (`/send`).
2. `localOrchestrator.js` decide: canale `ghidra` / `zw3d` / `hermes` / `normal` (auto-dominio dai token nel testo).
3. Catena di failover: modello scelto → `cloud` (`auto:coder`) → `kaggle` (abliterated) → `locale` (`auto`).
4. Se `wantUncensored` (nome modello contiene abliter|uncensor|dolphin|freedom|liberated|deali|no-refus|refusal-free) e contesto ∈ {ghidra, zw3d, hermes, null} → modello uncensored in TESTA.
5. `cloudEngine.js` fa la chiamata al provider cloud (OpenAI-compat), gestisce rate-limit/cooldown.
6. Streaming via SSE all'UI.

**Endpoint utili:**
- `GET /status?t=TOKEN` → server vivo, provider configurati, Kaggle up.
- `GET /keys?t=TOKEN` → provider configurati (con `configured:true/false`).
- `GET /keys/check?provider=NOME&t=TOKEN` → probe LIVE stato chiave (live/quota/morta).
- `GET /freeProviders?t=TOKEN` → lista provider gratuiti + link creazione chiave.
- `GET /freeProviders/hunt?t=TOKEN` → scopre provider gratuiti online.

---

## 4. REGOLE TASSATIVE (NON OPZIONALI)

**R1 — BACKUP PRIMA DI TOCCARE.** Prima di modificare un `.js` del cuore:
copia il file in `C:\Users\infoa\src\.self-heal-backup\` (se non c'è già) OPPURE
fai un backup con timestamp in `ANTIGRAVITY_COPIE_ELIMINATE\`. Mai modificare senza backup.

**R2 — `node --check` SU OGNI `.js` MODIFICATO.** Prima di riavviare, verifica sintassi:
`node --check "C:\Users\infoa\src\NOMEFILE.js"` (usa path Windows, non `/c/...` che node sbaglia).
Se dà errore → NON riavviare, correggi.

**R3 — RIAVVIO SERVER DOPO `.js`.** Il server su 8790 è un processo Node. Dopo
modifica a un `.js`: kill del PID su 8790, poi `node "C:\Users\infoa\src\heal-and-run.js"`.
(Un VBS di auto-riparazione può riavviarlo se killato; in caso, lanciarlo a mano.)
Per `.html` (solo UI): basta ricaricare la pagina / Reload Window, NON serve riavvio.

**R4 — LOG OBBLIGATORIO.** Ogni modifica va annotata in `MAINTENANCE-LOG.md`
(formato: `## AAAA-MM-GG HH:MM — <titolo> (v<da> → <a>)`, poi COSA/PERCHÉ/ESITO/ERRORI).
NESSUNA MODIFICA SENZA LOG. È la regola che è stata violata il 26-07 e ha causato
disallineo versione (codice 1.0.0 vs log 1.0.33).

**R5 — MAI ESPORRE SEGRETI.** Non stampare chiavi/token in chat, log, né commit.
Il `.env` è gitignorato. `MOBILE_TOKEN` serve solo per auth API (`?t=`).

**R6 — SINCRONIZZA ESTENSIONE.** Se modifichi un modulo presente ANCHE nell'estensione
VS Code, copialo da `src\` a `.vscode/extensions/.../src\` (vedi REGOLA 0).

**R7 — VERSION BUMP.** Ogni modifica significativa → bump versione in `mcpServer.js`
(rimasto a 1.0.0 mentre il log era a 1.0.33 = bug del 26-07). Aggiorna anche
`package.json` estensione se la versione cambia.

---

## 5. AUTOMATIZZARE (renderlo "non a mano")

Lo script **`C:\Users\infoa\src\apply-change.ps1`** fa TUTTO da solo:
1. Backup dei file `.js` toccati (in `.self-heal-backup\` o staging con timestamp).
2. `node --check` su tutti i `.js` di `src\`.
3. Se OK: kill server 8790 + riavvio + sincronizza i moduli chiave nell'estensione.
4. Ricorda di aggiornare il MAINTENANCE-LOG (quello resta a mano, è la traccia umana).

**USO:** dopo aver modificato i `.js` in `src\`, lancia:
`powershell.exe -ExecutionPolicy Bypass -File "C:\Users\infoa\src\apply-change.ps1"`
Lo script riavvia il server in modo pulito. Il log resta da scrivere a mano (R4).

**SEQUENZA SICURA:** modifica in `src\` → lancia `apply-change.ps1` → scrivi il log in
`MAINTENANCE-LOG.md` → verifica con `GET /status?t=TOKEN` che il server risponda.

---

## 6. ERRORI GIÀ INCONTRATI (non rifarli)
- `node --check` con path `/c/Users/...` → errore "C:\c\Users...". Usare SEMPRE `C:\Users\...`.
- Estensione spostata dallo staging → VS Code perde l'estensione (errore package.json).
  L'estensione va in `.vscode/extensions\`, NON nello staging.
- `.env` sbagliato: il server legge `C:\Users\infoa\.env`, non `src\.env`.
- Venice: aggiunto in providerRegistry.js MA serve anche `VENICE_API_KEY` in `.env`.
- Uncensored: rilevato dal NOME del modello, non da un flag. Se non contiene
  abliter/uncensor/dolphin/freedom/liberated/deali/no-refus/refusal-free → non scatta.
