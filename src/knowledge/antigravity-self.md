# Antigravity — Conoscenza CHIRURGICA per l'auto-manutenzione

> Questo file è la "mappa completa" di Antigravity. Chi lo legge (un modello di
> manutenzione, o Hermes) deve poter **capire, aggiustare e migliorare** l'app
> SENZA romperla. Leggi le REGOLE ANTI-DANNO in fondo PRIMA di modificare qualcosa.

## 0. Cos'è Antigravity
Copilot AI locale + cloud, senza filtri, con chat unificata (VS Code **e** telefono
sulla stessa conversazione), agente con strumenti, generazione immagini, e provider
specialistici (Ghidra RE, ZW3D, Tor, Hermes). Un **server Node** unico gira su
`127.0.0.1:8790` e serve la web-UI (`mobile-page.html`) sia al pannello VS Code
(iframe) sia al telefono (via URL Tailscale). Sorgente in `C:\Users\infoa\src\`.
`package.json` (versione) sta nella HOME `C:\Users\infoa\`.

## 1. Come si AVVIA e resta acceso
- **Startup Windows**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\antigravity-mobile-server.vbs`
  → è un VBS con un ciclo NASCOSTO (`Do … WScript.Sleep 5000 … Loop`) che lancia
  `node heal-and-run.js` in una cmd invisibile e lo riavvia se esce. (★2026-07-22:
  tolto il vecchio `for /l … timeout` che faceva LAMPEGGIARE una finestra.)
- `heal-and-run.js` = entry point: (1) ripara i file critici da backup (selfHeal),
  (2) avvia `MobileServer` (porta 8790), (3) avvia `kaggleToolProxy` (porta 8791).
- Anche l'**estensione VS Code** può avviare lo stesso server: un solo padrone della
  porta 8790; le istanze in più falliscono con EADDRINUSE ed escono (il ciclo riprova).

## 2. Mappa dei FILE (`src/`)
- **heal-and-run.js** — bootstrap: selfHeal + avvia server + proxy Kaggle.
- **mobileServer.js** — server HTTP 8790: serve `mobile-page.html` (riletta ad OGNI
  richiesta, quindi le modifiche HTML sono LIVE), API REST + SSE (streaming chat),
  gestione chiavi (`/keys`, saveKey), approvazioni, `/clear`/`/clearView`, Tor routes,
  `/clientError` (log errori del browser telefono). Inietta `{{VER}}` (data file).
- **mobile-page.html** — TUTTA la UI (HTML+CSS+JS inline). Header, striscia stato
  (`#curModel` + barre token per-provider), selettori (provider/model/policy), chat
  con streaming/ragionamento/tool-card/piano-TODO, cassetto chiavi, pannello Tor.
- **localOrchestrator.js** — il CERVELLO: `handle(prompt, ctx)` instrada per
  `ctx.provider` (claude/cloud/comfy/ghidra/hermes/local) + zw3d + auto-riconoscimento
  dominio + Tor. Costruisce gli agenti, gestisce stream/stop/coda, failover motori.
- **nativeAgent.js** — l'AGENTE: loop `run()` (tool-calling nativo) e `runReact()`
  (protocollo JSON testuale per modelli senza tool nativi). Definisce i TOOLS.
- **cloudEngine.js** — provider cloud multi (OpenAI-compat): discovery modelli,
  `chat`/`chatTools`, **failover intelligente** (`resilientCandidates`,
  `chatToolsResilient`), cooldown, barra uso token, budget.
- **localEngine.js** — Ollama locale: discovery, routing categoria/modalità, chat.
- **providerRegistry.js** — catalogo dei ~22 provider (host, endpoint, regex della
  chiave per l'AUTO-RILEVAMENTO), suggerimenti gratis.
- **claudeEngine.js / claudeHook.js** — provider Claude Code (CLI headless) + hook permessi.
- **hermesClient.js** — delega a Hermes Agent via CLI one-shot; accende Kaggle e il
  proxy prima di partire; traduce la scelta modello negli argomenti CLI.
- **hermesAcp.js** — vecchio canale ACP (NON usare: forza streaming, tool inaffidabili).
- **nousClient.js** — integrazione DIRETTA con i modelli :free del Nous Portal (Laguna,
  HY3, StepFun). Legge il `refresh_token` da `%LOCALAPPDATA%\hermes\auth.json`
  (`providers.nous`) e lo rinnova in autonomia. ⚠️ Vedi §12: il refresh_token di Nous
  è ROTANTE e rileva il riuso → nousClient lo RISCRIVE in auth.json dopo ogni refresh
  (ANTISLOGGO Hermes). NON toccare questa logica di persistenza.
- **kaggleWaker.js** — accensione ON-DEMAND del notebook Kaggle: `isUp()` (curl
  endpoint), `ensureUp()` (se giù → `kaggle kernels push` + poll fino a vivo).
- **kaggleToolProxy.js** — proxy 8791 DAVANTI a Kaggle: traduce le tool-call TESTUALI
  (```json / <tools>) dei modelli abliterated nel formato nativo `tool_calls` che
  Hermes sa eseguire. Antigravity NON lo usa (traduce già lato agente).
- **ghidraClient.js / ghidraHeadless.js / ghidraLauncher.js** — bridge a Ghidra
  (HTTP :8080 GhidraMCP), analisi headless, avvio automatico.
- **comfyClient.js** — ComfyUI (immagini). **torBrowser.js** — lettore .onion via Tor.
- **webSearch.js** — ricerca web/fetch. **reTools.js** — utility reverse engineering.
- **learningMemory.js** — memoria evolutiva (impara dalle correzioni utente).
- **selfHeal.js** — auto-riparazione (vedi §4). **services.js** — avvio Ollama.
- **mcpServer.js** — espone Antigravity come server MCP (per Hermes). **serverClient.js**,
  **webview.js** — colla VS Code.

## 3. FLUSSO di una richiesta
`mobile-page.html` (fetch/SSE) → `mobileServer` route → `localOrchestrator.handle()`
→ instrada al provider → costruisce `NativeAgent` (o chat diretta) → l'agente chiama
i tool via `_exec` → eventi (message/tool/plan/status/image/model) tornano in SSE →
la UI li disegna. Lo **streaming** usa `_streamStart/_streamToken/_streamEnd`.

## 4. SELF-HEAL (fondamentale, non farti fregare)
- `selfHeal.js` ha `CRITICAL_FILES` (localOrchestrator, localEngine, nativeAgent,
  cloudEngine, claudeEngine, claudeHook, comfyClient, hermesClient, reTools, services,
  serverClient, mcpServer, ghidra*, providerRegistry, webSearch, learningMemory,
  mobileServer, mobile-page.html, kaggleToolProxy, kaggleWaker).
- I backup stanno in `src/.self-heal-backup/`. All'avvio `verifyAndRepair` RIPRISTINA
  dal backup i file che non compilano/sono corrotti. `snapshotHealthy` AGGIORNA il
  backup ad ogni avvio SANO.
- ⚠️ **REGOLA D'ORO**: dopo aver modificato un CRITICAL_FILE, **copia subito il file
  aggiornato nel backup**: `cp src/<file> src/.self-heal-backup/<file>`. Altrimenti,
  se il server riparte e il tuo file "sembra" da riparare, torna la versione vecchia.

## 5. DEPLOY (come applicare una modifica)
- **mobile-page.html** → riletto ad ogni richiesta HTTP: basta **RICARICARE la pagina**
  (telefono + Reload Window in VS Code). Nessun riavvio.
- **file .js** → sono `require`-cached: il server li carica all'avvio. Per applicarli
  bisogna **RIAVVIARE il server**: uccidi il node su 8790 → il VBS lo rilancia in ~5s.
  `Get-NetTCPConnection -LocalPort 8790` per il PID, `Stop-Process -Id <pid> -Force`.
- **SEMPRE** prima: `node --check <file>.js`. Poi aggiorna il backup self-heal.
- **Versione**: bump di `C:\Users\infoa\package.json` ad OGNI correzione (regola utente).
  Il badge versione della pagina è la data del file (automatico).

## 6. PROVIDER e FAILOVER
- Chiavi in `C:\Users\infoa\.env` (gitignored). `cloudEngine._buildProviders` attiva
  un provider se la sua `env` c'è. L'auto-rilevamento (`providerRegistry.detectProvider`)
  riconosce il provider dalla FORMA della chiave incollata.
- **Failover gratuito** (`resilientCandidates`): usa SOLO
  `kaggle, openrouter, groq, google, nvidia, sambanova, hyperbolic, cerebras, mistral,
  alibaba`. Kaggle = corsia PRIORITARIA (rank 20). HF/openai/deepseek/chutes/novita =
  a consumo → ESCLUSI dal failover (usabili solo se selezionati a mano).
- `_classifyAndCooldown`: 401/403→auth (6h), 402/429/quota→30min, 502/503/saturo→20min,
  errore/timeout→3min. Cooldown persistito in `cloud-cooldown.json`.
- Stato chiavi (verificato 2026-07-22): TUTTE vive tranne **google (401, da rigenerare)**.
  chutes/novita = chiave valida ma **saldo $0** (non gratis, inerti).

## 7. AGENTE e TOOL
- `nativeAgent.run()` = loop tool-calling NATIVO. `runReact()` = per modelli senza tool
  nativi (protocollo: UN oggetto JSON per turno: `{action,args}` o `{final}`).
- ★ FIX CRITICO (2026-07-22): molti modelli abliterated (Qwen-Coder su Kaggle) NON
  riempiono `tool_calls`: mettono la chiamata come blocco ```json in `content`.
  `run()` ora, se non ci sono tool_calls, usa `_toolCallFromContent()` per estrarla ed
  eseguirla; `runReact` usa `_parseReact` (gestisce fence non chiuso) e `_salvageFinal`
  (mai dumpare json grezzo). NON rimuovere queste protezioni.
- I 39 tool esposti (`MODEL_TOOLS`): read_file, write_file, list_dir, search,
  run_command, analyze_binary, generate_image, delegate_to_hermes, update_todos,
  web_search, fetch_url, remember, tor, zw3d, e **ghidra** (unico tool con `op:` che
  accorpa 23 operazioni live; i ghidra_* storici restano per il ri-dispatch in `_exec`).
- Scelta modello RISPETTATA: se `ctx.model` non è "auto", l'agente lo usa PINNATO (niente
  rotazione); vale per ghidra/zw3d/tor (`_runAgentResilient`), cloud-agent, local, chat.

## 8. CONOSCENZA iniettata
`LocalOrchestrator._knowledge(file)` carica `src/knowledge/*.md` in testa al prompt:
`ghidra-rules.md`, `zw3d-rules.md`, `tor-guide.md`, `hermes-orchestrator.md`, e QUESTO
file per il provider di manutenzione. Per aggiungere sapere a un dominio: modifica il
suo .md (nessun riavvio se il file è letto a runtime — verifica in `_knowledge`).

## 9. KAGGLE (setup completo)
- Notebook UNICO: `alcafer2011/notebook39aa15083b`. Serve Ollama via ngrok dominio
  FISSO `paving-preschool-facelift.ngrok-free.dev` (authtoken ngrok DENTRO il notebook).
- Modelli abliterated: **Qwen2.5-Coder-14B** (9GB, il migliore per l'agente coi tool)
  e **Qwen3-Coder-30B-A3B MoE** (18.6GB, per T4×2).
- GPU: nel menù Kaggle solo **T4×2** (32GB) o **P100** (16GB). Via API `machine_shape`
  affidabile solo `NvidiaTeslaT4` (T4 singola); P100 si salva come `"Gpu"` (generico).
  Bench: 14B ~20 tok/s su 1 GPU, ~6.6 su T4×2 (split), ~19 su P100. 32B denso inutile
  su 16GB. → default = **14B**; 30B-MoE solo su T4×2.
- **CLI Kaggle**: `python -m kaggle …` (Python `C:\Program Files\Python312\python.exe`),
  token `KAGGLE_API_TOKEN` nel `.env`. Comandi: `kernels push/pull/status`, `datasets
  create/list`, `quota_view` (ore GPU: usate/totale/reset). ⚠️ NIENTE stop/cancel via
  API (per spegnere: UI Kaggle, o shutdown via Cloudflare).
- **On-demand**: `kaggleWaker.ensureUp()` fa `kaggle kernels push` del notebook in
  `src/kaggle-notebook/` (14B) o `src/kaggle-notebook-big/` (30B) e aspetta l'endpoint.
- **Proxy**: `kaggleToolProxy` (8791) traduce le tool-call testuali per Hermes.
- **Dataset-cache** (in costruzione): dataset privato `ollama-abliterated-coders` coi
  modelli, così i notebook caricano da lì (veloce + indipendenti da HF se lo rimuovono).

## 10. ⚠️ REGOLE ANTI-DANNO (leggi PRIMA di toccare)
1. `node --check` su ogni .js modificato PRIMA di deployare. Mai deployare codice rotto.
2. Dopo aver modificato un CRITICAL_FILE, **aggiorna il backup self-heal** (§4).
3. Modifiche .js → **riavvia il server**; modifiche HTML → basta ricaricare (§5).
4. **Bump versione** in `package.json` ad ogni correzione.
5. **MAI committare/esporre segreti**: `.env`, authtoken ngrok, token Kaggle, chiavi.
   NON metterli in memoria né in file versionati.
6. Non rompere i fix critici: paint (mobile-page endStream/_flushPaint annulla il
   timer), tool-call-da-content (nativeAgent), renderMd (normalizza CRLF).
7. Modifica INCREMENTALE e verificabile: una cosa per volta, testa, poi la prossima.
8. Se un provider dà errore, **classificalo** (auth vs quota vs saturo) prima di
   dichiararlo morto — vedi §6 e testa la chiave con un GET a `/models`.
9. Il server è UNO solo sulla 8790: non avviarne due (EADDRINUSE, loop, lampeggio).
10. In dubbio: NON cancellare, NON riscrivere in blocco. Proponi e chiedi.
11. ⚠️ **REGOLA FISSA — AGGIORNA QUESTO FILE A FINE SESSIONE**: se durante la sessione
    LAVORATIVA sono state fatte modifiche (da QUALSIASI modello/agente) a file di
    Antigravity, l'agente di manutenzione DEVE aggiornare QUESTO `antigravity-self.md`
    PRIMA di chiudere, in modo CHIRURGICO e coerente con lo stile delle sezioni qui
    sopra (numerate, tono diretto, percorsi assoluti Windows). Cosa scrivere:
    - **Cosa è cambiato**: file toccati + percorso + cosa fa ora la funzione.
    - **Regole**: vincoli scoperti (es. token rotante, non creare provider a parte).
    - **Percorsi**: nuovi file, backup, dove leggere le credenziali.
    - **Scoperte di compilazione ERRATE / da NON rifare**: errori fatti e come evitarli
      (es. escape doppio nelle modifiche HTML che rompe il JS della pagina e stacca
      VS Code + telefono; consumare un refresh_token senza riscriverlo → logout Hermes).
    - NON serve riscrivere tutto: aggiungi una voce in §12 (cronaca) e aggiorna le
      sezioni interessate (§2 mappa file, §10 regole). L'utente NON legge il file:
      ci pensa l'agente a tenerlo esatto. Ogni voce in §12 porta data + versione package.json.

## 11. ⚠️⚠️ DOVE VIVE OGNI COSA (Antigravity è SPARSA su più percorsi)
Questa è la trappola numero 1: esistono **DUE copie del codice**. Sbagliare copia =
"modifico ma non cambia niente".

### Il codice del SERVER (dove modificare per l'app)
- **`C:\Users\infoa\src\`** = ★ FONTE DI VERITÀ del server VIVO. Il VBS di avvio lancia
  `node C:\Users\infoa\src\heal-and-run.js` → il server in esecuzione legge SEMPRE da
  qui. **Modifica QUI** ogni cosa dell'app (mobile-page.html, engines, agent,
  orchestrator, kaggle*, knowledge). Verifica il node vivo:
  `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | ? {$_.CommandLine -like '*heal-and-run*'}`
- **`C:\Users\infoa\src\.self-heal-backup\`** = backup dei CRITICAL_FILES (§4).
- **`C:\Users\infoa\src\knowledge\`** = i .md di conoscenza (incluso questo).
- **`C:\Users\infoa\src\kaggle-notebook\` (14B)** e **`kaggle-notebook-big\` (30B)** =
  i notebook che `kaggleWaker` pusha per l'on-demand.

### Il WRAPPER dell'estensione VS Code (diverso dal server!)
- **`C:\Users\infoa\extension.js` + `package.json` + `interface.html`** (nella HOME) =
  il codice di ATTIVAZIONE dell'estensione VS Code (crea il pannello/webview su :8790,
  e se il server standalone non è su lo avvia — in-process da `./src` o detached da
  `~/src/heal-and-run.js`). `package.json` HOME = manifest + **VERSIONE** da bumpare.
- **`C:\Users\infoa\.vscode\extensions\local-developer.antigravity-1.0.1\`** =
  l'estensione INSTALLATA (copia: `extension.js`, `package.json`, `interface.html`,
  e una **PROPRIA `src/`**). VS Code carica QUESTA. La sua `src/` è **DORMIENTE**
  finché lo standalone (VBS) tiene la porta 8790; ma se lo standalone è giù, l'estensione
  serve dalla SUA `src/` (che può essere VECCHIA → UI/funzioni mancanti = bug storico).
  Ha anche `_src_backup_2026-07-17`.
- **`C:\Users\infoa\antigravity-1.0.x.vsix`** = pacchetti installabili.

### REGOLA che risolve la confusione
- Cambi al **server/UI/agente** → modifica `C:\Users\infoa\src\` → riavvia il server.
  L'estensione installata è irrilevante FINCHÉ lo standalone (VBS) è su (lo è di norma).
- Se vuoi coerenza totale (o l'estensione gira in-process), **allinea anche la copia
  installata**: `cp` i file cambiati in `.vscode\extensions\local-developer.antigravity-1.0.1\src\`
  (era il fix della sessione 14), oppure ripacchetta il `.vsix` e reinstalla.
- Cambi all'**attivazione VS Code** (extension.js/package.json comandi) → vanno nella
  HOME e poi ripacchettati/reinstallati (o copiati nell'installata).

### Fuori dall'app (percorsi di sistema che l'agente deve conoscere)
- **`C:\Users\infoa\.env`** = TUTTE le chiavi (gitignored). MAI esporre.
- **`%APPDATA%\…\Startup\antigravity-mobile-server.vbs`** = avvio server (loop nascosto).
  **`…\Startup\tor-antigravity.vbs`** = avvio Tor. **`Startup\Ollama.lnk`** = Ollama.
- **`%LOCALAPPDATA%\antigravity-mobile.log`** = log del server (righe `[CLIENT-ERROR]`
  = errori del browser telefono).
- **`%LOCALAPPDATA%\hermes\`** = HERMES_HOME: `config.yaml` (provider/modelli, incl.
  kaggle via proxy 8791), `hermes-agent\venv\Scripts\hermes.exe`. Backup config.yaml.bak.*
- **`C:\Program Files\Python312\python.exe`** + `python -m kaggle` (CLI Kaggle).
- **Ollama**: `%LOCALAPPDATA%\Programs\Ollama\ollama.exe` (locale), modelli in `.ollama`.
- **Tor**: `C:\Users\infoa\tor-bundle\tor\tor.exe` (SOCKS 9050).
- **Kaggle cloud**: notebook `alcafer2011/notebook39aa15083b`, dominio ngrok fisso
  `paving-preschool-facelift.ngrok-free.dev`, dataset `alcafer2011/ollama-abliterated-coders`.
- **Memoria persistente Claude** (NON è codice dell'app): `C:\Users\infoa\.claude\projects\…\memory\`.
- ⚠️ Il repo git coincide con la HOME `C:\Users\infoa\` (piena di roba di profilo);
  `.vscodeignore` esclude la home-junk dal pacchetto. La cartella aperta in VS Code
  `OneDrive\Documenti\mia estensione vs code` è QUASI VUOTA — NON è l'app.

## 12. ⚠️ CRONACA MODIFICHE (sessioni di manutenzione — vedi regola §10.11)

Ogni voce: data + versione `package.json`. Stile: cosa è cambiato, regole, percorsi,
ERRORI DA NON RIFARE.

### 2026-07-22 (v1.0.12) — Integrazione modelli :free Nous + anti-logout + menu fuso
**Cosa è cambiato**
- Nuovo file `C:\Users\infoa\src\nousClient.js` (client OAuth diretto Nous Portal).
  Legge `refresh_token` da `%LOCALAPPDATA%\hermes\auth.json` → `providers.nous`,
  rinnova via `/api/oauth/token`, espone `chat()` / `chatTools()` / `getModelChoices()`.
  Modelli :free esposti (verificati, nessun credito): `poolside/laguna-s-2.1:free`,
  `poolside/laguna-xs-2.1:free`, `tencent/hy3:free`, `stepfun/step-3.7-flash:free`.
- `localOrchestrator.js`: `require("./nousClient")`, istanza `this.nous`, metodi
  `nousAvailable()` / `getNousModelChoices()`. **Routing NON più per `ctx.provider`
  ma per PREFISSO del modello**: se `ctx.model` inizia con `nous::` → `_runNous` /
  `_runNousAgent`. Così i modelli Nous funzionano dentro QUALSIASI provider (Hermes,
  Manutenzione). Anche `_runAgentResilient` pinnna il motore Nous se `wantModel`
  inizia con `nous::`.
- `mobileServer.js`: payload `/models` include il blocco `nous` (usato internamente
  per popolare il catalogo; NON è più un provider a parte).
- `mobile-page.html`: **rimossa la voce `<option value="nous">` dal `<select>`**.
  I modelli Nous sono FUSI dentro **Hermes** (`CATALOG.hermes.push` con prefisso 🜂)
  E mostrati anche nella sezione **Manutenzione** (branch generico `addGrp("🜂 Nous
  (free)", CATALOG.nous)`). Rimossa la `if(p==="nous")` in `fillModels`.
- `config.yaml` di Hermes (`%LOCALAPPDATA%\hermes\config.yaml`): **rimosso il default
  forzato** `provider: nous` / `default: tencent/hy3:free` che Claude Code aveva messo
  e che faceva andare Hermes in 401 ("out of funds") quando il token scadeva. Ora
  Hermes fa self-routing (default `anthropic/claude-opus-4.6`).

**Regole / vincoli scoperti**
- Modelli Nous = `value: "nous::<id>"`. L'orchestratore instrada per prefisso, non per
  provider. Tenere il prefisso `nous::` nei value, altrimenti finiscono su Ollama.
- NON creare mai un provider "Nous" separato nel menu: l'utente vuole i modelli Nous
  DENTRO Hermes (e in Manutenzione).

**Percorsi / credenziali**
- Refresh token Nous: `%LOCALAPPDATA%\hermes\auth.json` → `providers.nous.refresh_token`
  (e duplicato in `credential_pool.nous[0]`). Lo legge `nousClient.js`.
- Inference base Nous è già `…/v1`: URL chat = base + `/chat/completions`
  (NON `/v1/chat/completions` doppio).

**ERRORI DA NON RIFARE (scoperte di compilazione / runtime)**
1. ❌ **Escape doppio nelle modifiche HTML**: in `mobile-page.html` le virgolette
   dentro gli attributi/stringhe JS vanno scritte UNA volta (`"option[value=\"nous\"]"`),
   NON `\"` doppio. Il doppio escape rompe la SINTASSI del `<script>` → il browser
   si ferma → la pagina non parte il client SSE → **VS Code E telefono restano ROSSI**
   pur con il server vivo (nessuna richiesta arriva al server). Sintomo: `node --check`
   sul JS estratto dà `SyntaxError: Invalid or unexpected token`. ✅ Verifica sempre
   la sintassi del JS della pagina dopo averla toccata (estrai `<script>` e `node --check`).
2. ❌ **Consumare il refresh_token Nous senza riscriverlo**: il refresh_token di Nous
   è **ROTANTE e rileva il riuso** (vedi commento in `hermes-agent/.../main.ts`:
   "24h ROTATING, reuse-detected refresh token"). Se `nousClient` rinfresca e tiene il
   nuovo token solo in memoria, Hermes resta col vecchio → lo riusa → il server Nous
   lo REVOCA ("Refresh session has been revoked") → **Hermes si slogga dal portale**.
   ✅ Fix: `nousClient._persistNousToken()` riscrive `access_token`/`refresh_token`/
   `expires_at` in `auth.json` (`providers.nous` E `credential_pool.nous`) DOPO ogni
   refresh, con scrittura atomica (tmp+rename) e lock file cooperativo (`auth.json.nouslock`)
   per non sfasarsi con Hermes. NON rimuovere questa persistenza.
3. ❌ **Non riavviare il server senza poi dire all'utente di ricaricare**: ogni kill
   del node su 8790 uccide le connessioni SSE aperte di VS Code/telefono. Dopo un
   riavvio .js, l'utente deve fare "Developer: Reload Window" (VS Code) o pull-to-refresh
   (telefono). Il server risponde comunque a ping/`GET /`/`/events`: se resta rosso,
   è la connessione morta lato client, non il server.
4. ⚠️ I modelli Nous sono RAGIONAMENTO (Laguna): scrivono in `reasoning`, risposta in
   `content`. `poolside/laguna-s-2.1:free` a volte dà `504 "operation aborted"` lato
   Nous (timeout server, non codice nostro): usare `laguna-xs` o `hy3` in quel caso.

### 2026-07-22 (v1.0.14) — Feature 1-3 (pannello chiavi, cacciatore di taglie, menu raggruppati) + piano Feature 4
**Cosa è cambiato (delegate a sub-agent, verificato live)**
- `providerRegistry.js`: aggiunto `FREE_PROVIDERS` (16 provider gratuiti curati, NO
  discovery automatica) + `freeProviders()`. Inclusi uncensored free (dolphin/abliterated
  su HF+Ollama). Nessun segreto esposto.
- `mobileServer.js`: aggiunti `POST /keys/check?provider=xxx` (probe live colla CHIAVE
  reale da `.env`, classifica `live`/`dead`/`quota` via HTTP status; chiave MAI al client)
  e `GET /freeProviders`. Rotta registrata.
- `mobile-page.html`: FEATURE 1 → `loadKeys()` mostra ogni provider con dot + bottone
  VERIFICA (`/keys/check`); FEATURE 2 → "Cacciatore di taglie" con OTTLENI CHIAVE (apre
  keyUrl) + INCOLLA QUI (focus keyInput, pre-set keyProvider); FEATURE 3 → `fillModels()`
  raggruppa `#model` per provider con `<optgroup>`, free-prima poi alfabetico. I value dei
  modelli NON cambiano (ancora `provider::model`): routing preservato. Salvataggio/
  eliminazione chiavi esistenti intatti.
- package.json 1.0.13 → 1.0.14. Backup in `.self-heal-backup/`.

**Verifiche live (200)**: `GET /keys` (16 provider), `GET /freeProviders` (16), `POST
/keys/check?provider=openrouter` → `{"status":"live"}`. node --check ok.

### 2026-07-22 (v1.0.15) — FASE B + C: proiettili agente + agente unificato
**Cosa è cambiato (eseguito a mano, verificato)**
- `nativeAgent.js`: aggiunti DUE nuovi tool nativi all'array `TOOLS` (entrano in
  `MODEL_TOOLS`, quindi sempre visibili all'agente):
  - `run_code` (sandbox Python/JS): esegue codice in sandbox (file temp, timeout 60s,
    stdout/stderr), AZIONE MUTANTE (gate `askApproval`). Metodo `_runSandbox`.
  - `edit_file` (patch chirurgico): sostituisce `old_string`→`new_string` in un file
    di testo, con controllo UNICITA' (errore se non unico, nessun cambio), AZIONE
    MUTANTE. Non rompe `write_file` (quello riscrive tutto).
  Dispatch aggiunto in `_exec` per `run_code`/`edit_file`. `_runSandbox` specchiato su `_shell`.
- `localOrchestrator.js` `_runAgentResilient`: REGOLA §13 blindata. Se `provider==="ghidra"`
  e il modello scelto e' uncensored (regex abliter/uncensor/dolphin/...), lo PINNIAMO
  per primo e vietiamo fallback a modello censurato. `ctx.model` NON viene MAI sovrascritto.
- FASE C gia' presente in architettura (non serviva altro): `remember` → memoria
  persistente `~/.antigravity/learning.json` (learningMemory.js); `update_todos` →
  pianificazione; policy `ask-writes`/`auto-allow`/`read-only` nel select `#policy`.
- package.json 1.0.14 → 1.0.15. Backup `.self-heal-backup/`.

**Verifiche**: `node --check` ok su nativeAgent.js / localOrchestrator.js; server
riavviato (PID 34132); `require("./nativeAgent.js").MODEL_TOOLS` contiene `run_code`,
`edit_file` (più ghidra/zw3d/tor/web_search/fetch_url/remember/comfy/delegate_to_hermes).

**Regole / vincoli scoperti**
- `run_code` gira in SANDBOX (no shell libera): per comandi di sistema usa `run_command`.
- `edit_file` richiede `old_string` UNICO: se non lo e', ritorna errore senza cambiare.
- La regola Ghidra-uncensored e' ora doppiamente garantita (pinnamento modello + nessun override).

### 2026-07-22 (v1.0.16) — A: git nativo · B: failover Kaggle · C: dashboard stato
**Cosa è cambiato (eseguito a mano, verificato ad-hoc)**
- `nativeAgent.js`: aggiunto tool `git` (array `TOOLS` + dispatch in `_exec`). Comandi
  READ-ONLY (status/log/diff/branch) SENZA conferma; comandi MUTANTI (add/commit/push/
  pull/checkout/reset/clone/merge) CON conferma (`askApproval`). SICUREZZA: bloccati
  `push --force` e `reset --hard` (mai distruttivi). Usa `_shell("git ...")`.
- `kaggleEngine.js` (NUOVO): motore OpenAI-compatible verso i notebook Kaggle (14B/30B
  abliterated via ngrok). `chatTools`/`chat`/`configured`/`isOnline`. NESSUN segreto
  (host da kaggleWaker.KAGGLE_HOST; il notebook non richiede API key).
- `localOrchestrator.js`: registrato `this.kaggle = new KaggleEngine` nel constructor;
  catena failover (`_runAgentResilient`) ora include `kaggle::30b` DOPO cloud e PRIMA
  del locale. Se il notebook e' SPENTO l'inferenza fallisce e il failover passa oltre
  (non accende qui: l'accensione on-demand resta solo per scelta esplicita `kaggle::`).
- `mobileServer.js`: nuovo endpoint `GET /status` (dashboard, NESSUN segreto) →
  `{server, engines:{local,cloud}, kaggle, tor, keys_configured, models_local, nous}`.
  Metodo `_statusDashboard` (riusa `cloud.listKnownProviders()` per contare le chiavi).
- `mobile-page.html`: nel cassetto chiavi, bottone "📊 Stato sistema" + div `#statusOut`
  che chiama `/status` e mostra cosa e' vivo (server/Ollama/cloud/Nous/Kaggle/Tor/chiavi).
- package.json 1.0.15 → 1.0.16. Backup `.self-heal-backup/`.

**Verifiche ad-hoc (5/5 PASS, script cancellato)**: `git` in MODEL_TOOLS; `git status`
  esegue; `git push --force` bloccato; `kaggleEngine.configured()` true; server :8790
  raggiungibile. Verifica live `/status` → server ON, Ollama 25 modelli, cloud ON,
  Kaggle ON (notebook acceso), Tor installed, 16 chiavi, Nous ON.

**Regole / vincoli scoperti**
- `git` NON esegue mai force/hard: se servono davvero, falli tu da terminale.
- Failover Kaggle si attiva SOLO se il notebook e' gia acceso (altrimenti passa oltre).
- `/status` NON espone chiavi/segreti: solo conteggi e stati di salute.

### 2026-07-22 (v1.0.17) — 1 voce(già c'era) · 2 visione foto · 3 auto-commit · 4 compressione · 5 salute
**Cosa è cambiato (eseguito a mano, verificato ad-hoc)**
- 1) DETTATURA VOCALE: GIA' PRESENTE in mobile-page.html (Web Speech API, bottone `#mic`,
  `webkitSpeechRecognition`, lang it-IT). NIENTE da implementare. Su iPhone Safari può
  essere instabile: in tal caso il bottone si nasconde e resta la dettatura iOS.
- 2) VISIONE FOTO: l'upload c'era già (input `#fileInput` + endpoint `/upload`, gli allegati
  arrivano al prompt come percorsi reali su disco). AGGIUNTO il "vederle":
  - `nativeAgent.js`: tool `read_image` (legge png/jpg/webp/gif → base64 + MIME); in `run()`
    il messaggio user con percorsi immagine viene arricchito di `images` (base64) se i file
    esistono → un modello VISIONE le vede. I modelli non-visione ignorano il campo.
  - `localEngine.js`: nuovo static `_toMultiModal(messages)` converte i messaggi con `.images`
    in contenuto OpenAI-compatible (text + image_url data:base64); applicato in `chat` e
    `chatTools`. Serve a llava (Ollama) e modelli cloud visione.
  - `MODEL_VISION`: per usare la foto serve un modello visione. In pull `ollama pull llava`
    (modello visione locale, ~4.1GB) in background — se la GPU (T1000 4GB) non regge, usare
    un cloud con visione (OpenRouter con un vision model) o saltare.
- 3) AUTO-COMMIT GIT: nel system prompt di `run()` istruito l'agente a fare `git add -A` +
  `commit -m` DOPO aver modificato file in una repo git (col tool `git`, con conferma). Non
  usa mai `push --force`/`reset --hard`. Si appoggia al tool `git` (v1.0.16).
- 4) COMPRESSIONE CHAT: nel loop di `run()`, se `messages.length > 26`, i messaggi vecchi
  (tranne system + ultimi 10) vengono sintetizzati in un riassunto (via `engine.chat`, temp
  0.2) per non saturare il contesto e mantenere coerenza su sessioni lunghe.
- 5) SALUTE MOTORI: `localOrchestrator` tiene `this._health[label]` (conteggio errori, finestra
  5 min). Nel failover (`_runAgentResilient`) salta i motori con >=3 errori recenti e azzera i
  fallimenti a successo. Auto-switch verso provider sani senza che l'utente cambi modello.
- package.json 1.0.16 → 1.0.17. Backup `.self-heal-backup/`.

**Verifiche ad-hoc (4/4 PASS, script cancellato)**: `read_image` in MODEL_TOOLS; `_toMultiModal`
  converte user→multimodale con image_url; senza images resta testo; server :8790 raggiungibile.

**Regole / vincoli scoperti**
- La foto si vede SOLO con modello visione (llava o cloud vision). Senza, l'agente descrive
  il percorso ma non "vede" i pixel.
- Compressione chat parte solo oltre 26 messaggi: sessioni brevi non subiscono overhead.
- Salute motore: dopo 3 errori in 5 min un provider è saltato nel failover (si riabilita
  da solo a successo).

### 2026-07-22 (v1.0.23) — SUGGERIMENTI EXTRA: decode / diff / apk / frida / mitm / report
**Cosa è cambiato (eseguito a mano, verificato ad-hoc)** — 6 tool RE/analisi aggiunti:
- `decode`: decode/encode/hash locale (CyberChef-like, pur Node): b64, hex, XOR (con chiave),
  base85, URL, JWT decode, MD5/SHA1/SHA256 testo+file. Usatissimo in RE. ZERO install.
- `binary_diff`: confronto binario via `radiff2` (radare2, gia installato) tra due file
  (patch analysis / crackmes / update RE). ZERO install.
- `apk_re`: reverse engineering APK (apktool + jadx, installati on-demand) per ANALISI LOCALE
  (lettura codice, nessun invio online) — rilevante per giochi mobile. Richiede conferma.
- `frida_hook`: hooking runtime Frida (injection nei processi), script JS. On-demand. SOLO su
  processi propri/di test. Richiede conferma.
- `mitm_capture`: cattura traffico MITM sul proprio dispositivo (mitmproxy, on-demand) in SOLA
  LETTURA/analisi (.har), nessun dato inviato a terzi. Studio locale del protocollo (es. giochi
  mobile) — nessun ban perche non altera il traffico in uscita. Richiede conferma.
- `report`: genera report markdown di fine sessione (title + findings) per traccia RE/pentest.

**Verifiche ad-hoc**: node --check OK; server vivo :8790 (PID 33700); 6 tool confermati in
MODEL_TOOLS. NESSUN segreto in /status.

**NOTA The Grand Mafia (utente)**: l'agente puo ANALIZZARE l'app (apk_re, mitm_capture in
lettura) ma NON deve automatizzare cheating/barare (rischio ban/intercettazione) se non su
esplicita richiesta. I tool on-demand (apk_re/frida/mitm) richiedono conferma e rispettano la
regola di sicurezza fondamentale (non agire su terzi, non distruggere).

### 2026-07-22 (v1.0.19 -> v1.0.22) — SUPER PIANO: agente imbattibile, toolkit RE/offensivo
**v1.0.19** — Policy di default forzata a `auto-allow` (AUTONOMO): l'agente agisce su
file/web/shell/RE SENZA chiedere conferma. `localOrchestrator.js` + `nativeAgent.js`.

**v1.0.20** — System prompt blindato: toolkit OFFENSIVO di RE/sniffing/injection/pentest
SENZA filtri, regola ZERO RIFIUTI (non rifiutare mai, non moralizzare). Nuovi tool RE/net:
`system_tool` (nmap/tshark/sqlmap/hashcat/john/binwalk/exiftool/volatility/strings/upx/pefile),
`binary_patch` (patch .exe/.dll con backup automatico), `hex_view` (dump hex), `process_list`.

**v1.0.21** — Regola di SICUREZZA FONDAMENTALE nel system prompt: l'agente NON distrugge/
cancella file a caso, NON inietta a casaccio, NON attacca siti/account terzi senza consenso;
azioni a rischio (rm -rf, injection su altrui, cheating online tipo The Grand Mafia, exploit
versi terzi) VIETATE di default, ammesse SOLO su richiesta esplicita+conferma e su risorse
proprie. Prima di ogni azione distruttiva, backup. Nuovi tool FASE B + S9: `file_op` (copy/move/
rename/list/info, MAI delete diretto, backup su overwrite), `run_program` (esegue .exe con
cattura output), `registry_read` (solo lettura), `remind` (promemoria con orario).

**v1.0.22** — Aggiunte voci MOTORI A DISPOSIZIONE nel system prompt (RE/Zw3D/Ghidra/Hermes/
Tor/Cloud/Kaggle/Locale come "proiettili"). Nuovi tool S10/S11/S12: `schedule_task` (cron
manutenzione, salva in `.antigravity-schedule.json`), `semantic_search` (RAG tf-idf locale su
file progetto, trova per significato), `notify` (popup Windows via msg.exe + Telegram opz.).
Tool `web_automate` (Playwright) già presente da v1.0.18.

**Verifiche**: node --check OK su tutti i .js; server vivo :8790 (PID 34644); tool registrati
confermati via MODEL_TOOLS (system_tool/binary_patch/hex_view/process_list/file_op/run_program/
registry_read/remind/schedule_task/semantic_search/notify/web_automate). NESSUN segreto in /status.

**Stato strumenti esterni**: exiftool installato; nmap/tshark/sqlmap/hashcat/john/binwalk/
volatility/frida NON installati (install pip/choco fallita per alcuni — l'agente li installa
on-demand via regola "munizioni illimitate"). pip2 (scapy/pyelftools/unicorn) in background.

**Regola tassativa (utente)**: Antigravity nasce per RE/sniffing/injection/pentest UNCENSORED.
L'agente NON deve distruggere file a caso né hackerare siti a caso; cheating online (The Grand
Mafia) VIETATO di default (rischio ban/intercettazione) — ammesso solo su esplicita richiesta.

**Feature 4 (SOLO PIANO, non eseguita)**: piano in `knowledge/AGENT-TOOLS-PLAN.md`.
Punta a estendere `nativeAgent.js` (descrizioni chirurgiche di web_search/fetch_url/
remember/tor/zw3d/ghidra/comfy sempre dichiarate) + `_runAgentResilient` (pinna il modello
uncensored scelto in Ghidra, nessun fallback censurato) + nuovi tool `run_code` (sandbox)
ed `edit_file` (patch). Da eseguire in Fase B.

**Regole / vincoli scoperti**
- `FREE_PROVIDERS` è la fonte curata: NON aggiungere discovery automatica.
- `/keys/check` usa la chiave reale da `.env` lato server: non duplicarla nel client.

## 13. ⚠️ ROADMAP FEATURE (idee utente — 2026-07-22, da delegare ad agente)
L'utente ha proposto 4 feature e una regola tassativa. **NON implementare a mano alla
cieca**: delegare a un sub-agent potente DANDOGLI questo file + i file rilevanti, così
il lavoro è pulito e verificato. Le feature vanno fatte con le regole anti-danno §10.

### REGOLA TASSATIVA — Ghidra + modello uncensored (NON rifiutare)
- Quando `provider === "ghidra"` e l'utente ha selezionato un modello **uncensored**
  (es. dolphin abliterated, qwen2.5-coder-abliterated), l'agente di Antigravity DEVE
  usare QUEL modello. **Nessun fallback a un modello censurato, nessun rifiuto.**
- Più in generale: **l'app usa SEMPRE il modello che l'utente seleziona** (nel select
  #model), in ogni provider (zw3d, ghidra, hermes, cloud, local). Nessun override
  automatico del modello scelto. Se l'utente cambia modello, l'app tiene quello.
- Verifica: `localOrchestrator.js` `_runAgentResilient` / `run()` non deve sostituire
  `ctx.model` con un default censurato quando il provider è ghidra (o mai, in generale).

### FEATURE 1 — Pannello chiavi "vive / morte / quota" con un click (fattibile)
- Oggi: cassetto `#keys` (🔑) con `keyInput` (incolla chiave, auto-detect), `keySave`,
  `keyProvider`, `keyDelete`. Server: `/keys` (lista+stato), `/detectKey`, `/addKey`.
  `providerRegistry.detectProvider` riconosce il provider dalla forma chiave.
- Da fare: nel cassetto chiavi, per OGNI provider configurato mostrare un indicatore
  vivo / morto / quota con un bottone VERIFICA che fa un probe live (es.
  `/keys/check?provider=xxx` lato server, chiama un endpoint leggero del provider).
  Stato già parzialmente in `/keys` (vedi §6: google 401, altri vivi).
- Sorgenti: `mobile-page.html` (cassetto chiavi), `mobileServer.js` `_keys/_detectKey/
  _addKey`, `providerRegistry.js`.

### FEATURE 2 — "Cacciatore di taglie": lista curata di provider/modelli FREE (sicuro)
- NO discovery automatica (rischiosa: tanti falsi, rate-limit, ban). SÌ lista CURATA
  (l'agente la mantiene in `providerRegistry.js`) di provider gratuiti verificati, con
  per-ciascuno: nome, link dove prendere la chiave, modelli free noti.
- UI: nel cassetto chiavi, sotto "incolla chiave", una lista di provider free curati,
  ognuno con bottone "Ottieni chiave" (apre il sito) + "Incolla qui" (focus su keyInput
  pre-impostando `keyProvider`). L'agente popola la lista da `FREE_PROVIDERS`.
- Lista free curata iniziale (l'agente la completa/verifica): OpenRouter, Groq, Google
  AI Studio, HuggingFace Inference, Cloudflare Workers AI, Cerebras, NVIDIA, SambaNova,
  Hyperbolic, Novita, Chutes, Ollama-cloud, Kaggle, Nous Portal (:free). Uncensored free:
  dolphin/abliterated su HF+Ollama.
- MAI esporre le chiavi (§10.5); i link portano sul sito del provider.

### FEATURE 3 — Menu a tendina provider/modello ripensati (fattibile)
- Oggi: select `#provider` (locale/cloud/comfy/ghidra/zw3d/manutenzione) e select
  `#model` piatto con modelli + provider scritto vicino. `loadModels`/`fillModels`
  popolano `CATALOG` (local/claude/hermes/nous/cloud/cloudUnc/cloudNorm).
- Da fare: raggruppare per PROVIDER (optgroup) con i suoi modelli sotto, free prima
  dei non-free, ordinati alfabeticamente.
- Sorgenti: `mobile-page.html` `loadModels`/`fillModels`, `CATALOG`.

### FEATURE 4 — Agente chirurgico ZW + Ghidra + Hermes che USA i tool nativi (grosso)
- Obiettivo: l'agente di Antigravity espone i tool NATIVI (web_search, fetch_url,
  remember, tor, zw3d, ghidra, comfy) come FUNZIONI dell'agente, così qualsiasi agente
  che ha bisogno di me non ha problemi a usarmi. L'utente NON conosce i comandi: scrive
  cosa vuole, l'agente capisce e usa lo strumento giusto.
- Antigravity NON usa PowerShell per parlare con Tor (lo fa via `torBrowser.js`/proxy).
- Estendere `localOrchestrator.js` (`_exec` tool dispatch, `NativeAgent`,
  `_runAgentResilient`) per registrare i tool in ZW3D (`zw3d*`) e Ghidra (`ghidra`,
  `ghidraClient.js`) e Hermes (`hermesClient.js`), con descrizioni chirurgiche. L'agente
  esistente va MIGLIORATO con tutte le funzioni native, non riscritto da zero.
- Conoscenza per dominio in `knowledge/`: `ghidra-rules.md`, `zw3d-rules.md`,
  `tor-guide.md`, `hermes-orchestrator.md`. Leggerli prima di toccare i tool.
- Tassativo: in Ghidra con modello uncensored → nessun rifiuto (vedi regola sopra).

### COME delegare (note per l'agente esecutore)
- Leggere QUESTO file §10 (anti-danno) + §11 (dove vive ogni cosa) + i file sorgente
  citati. `node --check` su ogni .js, backup `.self-heal-backup/`, bump `package.json`,
  riavvio + reload. Verificare nel browser/telefono.
- `FREE_PROVIDERS` (lista curata, in `providerRegistry.js`): array di {id, name,
  keyUrl, freeModels:[], note}. Da non confondere con discovery automatica.
