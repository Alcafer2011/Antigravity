# mobileServer.js — ANALISI RIGA PER RIGA

Web-server locale su porta 8790. NON dipende da VS Code (gira anche a editor chiuso).
Avvio: `node src/mobileServer.js` o da heal-and-run.js. Auto-riparazione via selfHeal
prima del caricamento dei moduli (righe 30-33). Tipo: classe `MobileServer`.
Esporta `{ MobileServer, DEFAULT_PORT }` (riga 993).

## Costruttore (52-74)
- rootDir = opts.rootDir || path.join(__dirname,"..") → `C:\Users\infoa` (HOME).
  Perciò `_loadEnv()` legge `C:\Users\infoa\.env` (NON src\.env).
- Carica env (MOBILE_HOST/PORT/TOKEN), crea LocalOrchestrator, optional TorBrowser,
  kaggleWaker. DEFAULT_PORT = 8790.

## Routing (256-423)
- `_authOk(req,url)`: token da `?t=` o header `x-token` → confrontato con `this.token`
  (MOBILE_TOKEN). Tutte le API tranne `/` e `/img/` richiedono il token.
- Endpoint principali:
  - `/` → pagina web (mobile-page.html), anti-cache forte.
  - `/img/<file>` → immagini ComfyUI (solo basename, no traversal).
  - `/tor/page`, `/tor/raw`, `/tor/status` → lettore Tor lato server.
  - `/events` (SSE), `/history`, `/conversations`, `/models`, `/send`, `/stop`,
    `/approve`, `/policy`, `/clear`, `/clearView`, `/newChat`, `/switch`, `/delete`,
    `/keys`, `/keys/check`, `/detectKey`, `/addKey`, `/freeProviders`,
    `/freeProviders/hunt`, `/upload`.
  - Kaggle: `/kaggle/up`, `/kaggle/status`, `/kaggle/shutdown`, `/kaggle/quota`.
  - Server: `/server/status`, `/server/health`, `/server/logs`, `/server/restart`,
    `/server/engines`.
  - `/status` → dashboard (CODICE VERIFICA: ritorna keys_configured, engines, kaggle).

## Funzioni chiave
- `_statusDashboard` (426-456): costruisce JSON stato SENZA segreti. Conta i provider
  configurati via `cloud.listKnownProviders().filter(p=>p.configured)`.
- `_sse` (458-472): stream SSE verso i client (telefono+VS Code condividono chat).
  Ping ogni 20s. Alla connessione manda subito history+conversations.
- `_torPage` (477-507): scarica via Tor, analizza rischio, sanitizza HTML, estrae body.
- `_torRaw` (511-525): proxy immagini via Tor (solo image/*, no HTML/exec).
- `_keys` (530-537): `cloud.listKnownProviders()` + `cloud.freeSuggestions()`.
- `_detectKey` (538-543): `cloud.detectKey(key)` → riconosce provider dal prefisso.
- `_addKey` (544-551): `cloud.saveKey(key,provider)` → `discoverCloud(true)`.
- `_checkKey` (560-609): PROBE LIVE di una chiave. Fa `/models` (riconoscimento) POI
  mini-chat reale (rivela quota/saldo). Classifica: live/dead/quota. Non espone chiave.
- `_freeProviders` (618-629): provider gratuiti vivi (catalogo auto). `?uncensored=1`
  filtra solo i senza filtri.
- `_translate` (635-643): dato URL esterno, ritorna link traduttore Google in italiano.
- `_huntProviders` (648-663): cacciatore di taglie reale (bountyHunter.hunt).
  `?uncensored=1` → solo provider abliterated.
- `_gpuPlatforms` (667-675): confronto piattaforme GPU (gpuPlatforms.summary).
- `_upload` (678-697): salva allegato su disco (`storageDir/uploads`), nome sanitizzato.
- `_ensureOllama` (703-721): se Ollama spento, lo avvia (exe reale poi PATH), aspetta ~10s.
- `_models` (723-750): payload completo per UI (modelli, ruoli, canali cloud, claude,
  hermes, nous, policy).
- `_send` (752-770): accoda il messaggio, echo immediato, `_drainQueue()` se non busy.
- `_drainQueue` (778+): esegue i messaggi in coda uno per volta, riprende da solo.
- `_serverStatus` (837-856): pid, uptime, memoria, client, conversazioni.
- `_serverHealth` (860-870): riusa dashboard + campo `healthy`.
- `_serverLogs` (873-880): tail del log su file (?n= righe, max 2000).
- `_serverRestart` (887-904): spawna nuova istanza heal-and-run.js (detached), libera
  porta, exit. ⚠️ NON killa forzatamente: lascia 1s al nuovo processo.
- `_serverEngines` (909-927): stop/start Ollama+Comfy via taskkill/spawn (solo processi
  nostri, non distruttivo).
- `_statusDashboardRaw` (929-947): versione cruda per health.
- `_approve` (949-956): `orchestrator.resolveApproval(id, approved)` + echo a tutti i client.
- `_clear` (818-833): svuota chat attiva, dimentica sessione Claude.
- `_clearView` (961-967): pulisce solo la vista (memoria intatta).
- `_policy` (969-973): `setPermissionPolicy` (auto-allow/ask-writes/read-only).
- `_body` (977-984): parse JSON body (max 2MB).
- `_json` (986-989): risposta JSON.

## Dipendenze
- selfHeal (auto-riparazione), LocalOrchestrator, TorBrowser (optional), kaggleWaker.
- Richiesto dinamicamente: bountyHunter, gpuPlatforms, comfyClient (lazily).

## Rischi / note
- `/server/restart` può causare doppio processo se il nuovo non aggancia la porta in 1s.
- `_checkKey` fa una vera chiamata API (costo micro): normale, ma non chiamarlo in loop.
- NESSUN segreto esposto nelle risposte (verificato: /status, /keys non mostrano chiavi).
- Auth solo `?t=MOBILE_TOKEN` (NON Bearer) — confermato testando l'API.
