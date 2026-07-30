# claudeEngine.js + claudeHook.js — ANALISI RIGA PER RIGA

Claude Code come PROVIDER di Antigravity. Niente estensione a parte: lancia la CLI
`claude` installata in headless e traduce il suo stream-json nel nostro protocollo.
Usa l'abbonamento esistente (nessuna chiave API).

## claudeEngine.js (381 righe)
- Costruttore (36-47): cliPath da `_findCli` (candidati: CLAUDE_CLI_PATH, npm global,
  ~/.local/bin, /usr/local/bin). hookPath=claudeHook.js, mcpPath=mcpServer.js (i nostri
  strumenti prestati a Claude via MCP). sessions=Map convId→session_id.
- `available()` (50): vero se CLI trovata (provider visibile in UI).
- `_findCli` (52-64): cerca l'eseguibile claude.exe nei percorsi noti.
- `getModelChoices` (67-74): auto/opus/sonnet/haiku.
- `chat(prompt, o)` (92-208): costruisce args CLI: `-p prompt --output-format stream-json
  --verbose --include-partial-messages`. --resume se sessione esistente. --model se scelto.
  Aggiunge `--mcp-config` con il nostro mcpServer.js (strumenti generate_image/analyze_binary).
  PERMESSI: read-only → `--tools` solo lettura + bypassPermissions; auto-allow →
  bypassPermissions; ask-writes → bypassPermissions + hook PreToolUse (claudeHook) che
  chiede a te dalla chat via server di approvazione efimero (porta 0, segreto random).
  spawn claude.exe (windowsHide). Parsa stdout linee JSON (eventi): system/init (sessionId),
  stream_event (text_delta → onToken), assistant (tool_use → tool-card; TodoWrite → piano),
  user (tool_result → chiude card), rate_limit_event (barra limiti), result (costo/token).
  `finish` (155-169): se delta non arrivati, usa finalText dal result.
- `_onEvent` (211-284): traduce eventi stream-json → nostro protocollo (onToken/onEvent/
  onLimit). rate_limit_info → `_limit` (percent, resetsHuman).
- Server approvazione (335-371): `_startApprovalServer` crea HTTP su 127.0.0.1:porta casuale
  (secret random). L'hook ci POSTa "Claude vuole X" → `askApproval(...)` (la UI chiede a te)
  → risponde {allow}. FAIL-CLOSED: in dubbio nega.

## claudeHook.js (72 righe)
Hook PreToolUse lanciato da Claude prima di scritture/comandi. Legge
`ANTIGRAVITY_APPROVAL_URL` + `ANTIGRAVITY_APPROVAL_SECRET` (passati da claudeEngine).
- `decide(allow, reason)` (21-30): scrive JSON hookSpecificOutput permissionDecision
  allow/deny ed esce. 
- `ask(payload)` (32-53): POST al server di approvazione (timeout 290s, sotto il limite
  hook 300s). Su errore/timeout → resolve(false) (NEGA).
- stdin (55-72): se URL/SECRET assenti → nega. Parsa evento hook, chiama ask, decide.
  FAIL-CLOSED: qualsiasi problema → nega.

## Sicurezza
- FAIL-CLOSED ovunque: se il canale di approvazione non risponde → NEGA (mai autorizza per errore).
- Segreto random per turno: l'hook non può essere triggerato da estranei.
- read-only: Claude non può scrivere (solo strumenti di lettura).

## Dipendenze
- claudeEngine: child_process, http, crypto, fs, os, path. Usa mcpServer.js (nostri tool).
- claudeHook: solo http (lanciato da Claude come subprocess).

## Rischi / note
- Richiede Claude Code CLI installata (npm i -g @anthropic-ai/claude-code) o non parte.
- Le scritture di Claude passano dal TUO via libera (ask-writes) → non fa danni senza OK.
- auto-allow: bypassPermissions → Claude scrive SENZA chiedere. Usa con cautela.
