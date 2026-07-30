# ANTIGRAVITY — ANALISI MODULI (riga per riga)

Analisi completa dei moduli del cuore `C:\Users\infoa\src\`. Fatta il 2026-07-27.
Ogni file ha la sua analisi in `analisi\<nome>.md`. L'analisi è su disco, NON in chat.

## Stato analisi — COMPLETATA (29/29 moduli .js di src\)
- [x] heal-and-run.js (loader/entry, 42 righe)
- [x] mobileServer.js (web server 8790, 1008 righe)
- [x] localOrchestrator.js (motore + failover + uncensored, 1221 righe)
- [x] cloudEngine.js (motore cloud multi-provider, 1153 righe)
- [x] providerRegistry.js (catalogo provider auto-detect, 272 righe)
- [x] selfHeal.js (auto-riparazione estensione/server, 181 righe)
- [x] ghidraClient.js + ghidraLauncher.js + ghidraHeadless.js + reTools.js (RE, 111+106+87+72)
- [x] claudeEngine.js + claudeHook.js (Claude Code provider, 381+72)
- [x] nousClient.js + hermesClient.js + hermesAcp.js (Nous/Hermes, 315+278+325)
- [x] localEngine.js + nativeAgent.js (motore Ollama + loop agente, 537+2462)
- [x] kaggleWaker.js + kaggleEngine.js + kaggleToolProxy.js (Kaggle GPU, 190+101+171)
- [x] comfyClient.js + webSearch.js + torBrowser.js (immagini/web/Tor, 212+282+211)
- [x] mcpServer.js + services.js + webview.js + serverClient.js (MCP/Ollama/UI/client, 106+66+487+132)
- [x] bountyHunter.js + gpuPlatforms.js + learningMemory.js (cacciatore taglie/GPU/memoria, 323+246+80)

NOTE: efesto.js NON esiste in src\ (è separato in C:\Users\infoa\EfestoAI). I 30 file stimati erano 29 effettivi.

## File di analisi (in questa cartella analisi\)
- heal-and-run.md — entry/loader
- mobileServer.md — web server 8790 (routing, SSE, Tor, chiavi, discover, agenti)
- localOrchestrator.md — motore, failover, uncensored, canali
- cloudEngine.md — motore cloud, canali uncensored/normal, quota, rate-limit
- providerRegistry.md — catalogo provider, auto-detect da chiave
- selfHeal.md — auto-riparazione, CRITICAL_FILES, verifyAndRepair
- ghidra_RE.md — ghidraClient/Launcher/Headless/reTools
- claudeEngine.md — claudeEngine + claudeHook
- nous_hermes.md — nousClient + hermesClient + hermesAcp
- localEngine_nativeAgent.md — localEngine (Ollama) + nativeAgent (loop agente, MANIFESTO, TOOLS)
- kaggle.md — kaggleWaker + kaggleEngine + kaggleToolProxy
- comfy_websearch_tor.md — comfyClient + webSearch + torBrowser
- mcp_services_webview_serverclient.md — mcpServer + services + webview + serverClient
- bounty_gpu_memory.md — bountyHunter + gpuPlatforms + learningMemory

## Regole anti-danno (vedi anche REGOLA-ASSOLUTA.md + apply-change.ps1)
Ogni modifica a un .js del cuore DEVE: (1) backup, (2) node --check, (3) riavvio server 8790,
(4) sync modulo nell'estensione src\, (5) log in MAINTENANCE-LOG.md. Lo script apply-change.ps1
automatizza backup+check+riavvio+sync.

## Punti caldi / rischi trovati
- mcpServer.js riga 84: versione "1.0.35" FISSA (aggiornare al bump).
- comfyClient.CHECKPOINT: Realistic Vision Hyper (SD1.5), NON Z-Image come dice la doc.
- nativeAgent.ZW3D: percorsi fissi (headersDir 2025, msbuild VS18) → aggiornare se sposti installazione.
- webSearch: richiede GITHUB_TOKEN + GEMINI_API_KEY nel .env (home).
- kaggleWaker: richiede KAGGLE_API_TOKEN nel .env (home) per accendere il notebook.
- services.ensureOllama: percorso Ollama fisso (AppData\Local\Programs\Ollama).
- kaggleToolProxy: porta 8791 (se occupata, assume già attivo).
- gpuPlatforms: SOLO Kaggle è cablato (remote); le altre piattaforme sono informative, NON funzionanti.
- learningMemory: storage in ~/.antigravity/learning.json (fuori da src\).
- Tor: richiede ~/tor-bundle/tor/tor.exe; è un LETTORE (siti JS-heavy non funzionano).
