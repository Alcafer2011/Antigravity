# mcpServer.js + services.js + webview.js + serverClient.js — ANALISI RIGA PER RIGA

## mcpServer.js (106 righe)
Server MCP (stdio, JSON-RPC 2.0) che espone gli strumenti di Antigravity a HERMES.
- Strumenti: `generate_image` (→ comfyClient.generate), `analyze_binary` (→ reTools.analyzeBinary), `delegate_to_hermes` (→ hermesClient.delegate).
- `send` (56): scrive un messaggio JSON per riga su stdout. `reply`/`fail` (57-58).
- `callTool` (60-73): mappa nome→funzione; errori tornano come `isError` (testo), non JSON-RPC error (così il modello legge e prosegue).
- `rl.on("line")` (76-106): loop JSON-RPC. `initialize` (84) dichiara versione serverInfo "1.0.35" (⚠️ FISSA: se fai bump, aggiorna qui oltre a mcpServer.js del cuore e package.json estensione). `tools/list`, `tools/call`, `ping` supportati.
- Registrazione (in locale): `hermes mcp add antigravity -- node C:\Users\infoa\src\mcpServer.js`.
- ⚠️ Questo è un process SEPARATO (stdio), NON il server 8790. selfHeal.ensureHermesMcp lo ri-registra se un autofix lo rimuove.

## services.js (66 righe)
Avvio servizi locali su richiesta.
- `ping` (16-24): probe HTTP su 127.0.0.1:port.
- `ollamaUp` (27): ping 11434 /api/tags.
- `ensureOllama` (33-64): se spento, spawn `ollama serve`. ★ 2026-07-19 FIX: prova il percorso REALE `AppData\Local\Programs\Ollama\ollama.exe` prima di "ollama" nel PATH (su questa macchina non è nel PATH). detached+unref (sopravvive alla richiesta). Aspetta 20×1s.
- ComfyUI si avvia da solo in comfyClient (che sa il suo venv).

## webview.js (487 righe) — FRONTEND chat (VS Code)
UI seria stile assistente agentico. Gira nel webview di VS Code (`acquireVsCodeApi`).
- DOM refs (7-28): chat, input, bottoni, select modelli/provider/canale, usage bar, policy, roles.
- `history`/`currentMode`(auto)/`currentProvider`(local)/`currentChannel`(normal) (31-37).
- `saveState`/`restoreState` (53-71): persistenza su vscode.setState (solo controlli, NON messaggi — la conversazione è CONDIVISA col server, arriva via evento "history").
- `renderMarkdown` (74-105): markdown minimale SICURO (parte da testo escapato, blocchi codice estratti prima).
- `send` (133-148): postMessage al server {type:"sendMessage", value, mode, provider, channel, model}. NON tiene lo storico qui (il server rimanda "userMessage" a tutti i dispositivi).
- `renderConversation` (152-167): ridisegna la chat condivisa; setProvenance (modello).
- Streaming (207-254): ensureBubble/ensureStreamText/startTurn/appendStream/endStream. Le tool-card e il piano sono FRATELLI del testo (non cancellati dal re-render).
- `toolCard` (257-281): card strumento (read/edit/execute) con stato run→ok.
- `renderPlan` (284-299): piano (update_todos).
- `requestApproval` (302-319): gate approvazione UI (Approva/Nega → postMessage approvalResponse).
- Listener `message` (322-384): gestisce history/userMessage/cleared/localModels/cloudStatus/cloudModels/cloudUsage/updateStatus/stream*/addResponse/agentEvent/requestApproval.
- `populateModels` (387-404): menu modelli per provider/canale. Avvisa se uncensored cloud vuoto (usa locale senza filtri).
- Eventi UI (431-487): send/stop/refresh/regen/newChat/policy/provider/channel/ubReset/modes/copy.

## serverClient.js (132 righe) — CLIENT Node verso mobileServer (8790)
Fa diventare l'estensione VS Code un client dello STESSO server del telefono (chat condivisa).
- `ping` (30): probe /models.
- `connect`/`_openSse` (35-72): stream SSE su /events?t=TOKEN; parser "data:"; riconnessione auto (_scheduleReconnect, 1.5s).
- `close` (79-83): chiude SSE + timer.
- Azioni POST (86-90): send/stop/approve/policy/clear/models.
- `_get`/`_post` (94-129): helper HTTP con token `?t=`.

## Dipendenze
- mcpServer: readline, comfyClient, reTools, hermesClient.
- services: http, child_process.
- webview: solo DOM/vscode API (browser).
- serverClient: http.

## Rischi / note
- mcpServer versione "1.0.35" FISSA (riga 84): ricordati di aggiornarla al prossimo bump.
- webview.js è browser-code: NON va eseguito in Node, gira solo nel webview VS Code.
- serverClient + webview = l'estensione VS Code è SOLO client UI; il server vivo è mobileServer (cuore src\).
- ensureOllama ha percorsi fissi: se sposti Ollama, aggiorna services.js.
