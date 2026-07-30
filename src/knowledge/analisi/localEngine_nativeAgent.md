# localEngine.js + nativeAgent.js — ANALISI RIGA PER RIGA

Motore locale (Ollama) + loop-agente nativo con tool-calling.

## localEngine.js (537 righe)
Motore modelli locali Ollama (127.0.0.1:11434). Nessuna chiave.
- `parseSizeB` (25-39): stima parametri (gestisce MoE "8x7b", numero grezzo, T/B).
- `isRemoteModel` (42-44): suffisso :cloud/-cloud → modelli cloud su server Ollama.
- `CATEGORY` (47-52): AGENT/CODING/REVERSE/REASONING.
- `MODEL_PREFERENCES` (59-107): per categoria, pattern in ordine di priorità.
  AGENT: requireTools+requireUncensored (motore squadra = uncensored, no rifiuti).
  REVERSE: prefer dolphin/abliterated (uncensored essenziale).
- `discover` (120-155): /api/tags → modelli con tools/uncensored/remote. Re-verifica
  capabilities via /api/show per i modelli custom che /api/tags non popola.
- `classify` (177-213): segnali di prompt → categoria (agentSignals/reverseSignals/
  codingSignals). forcedMode ha priorità.
- `pickModel` (219-241): sceglie per categoria, filtra tools/uncensored, punteggio.
- `_score` (250-285): aderenza compito + tools + uncensored + coder + taglia vs HW
  (sweet spot 3-15B). I "coder" PENALIZZATI per ruolo AGENTE (dichiarano tools ma non
  li invocano). Modelli cloud (remote) NON prendono bonus taglia (non girano su GPU casa).
- `route` (319-340): se tocca file/percorso concreto → mode "agent" (con tool), altrimenti
  "direct" (chat). Regola: percorso concreto = c'è un file vero → serve l'agente.
- `chat`/`chatTools` (348-419): chat diretta streaming + tool nativi (NON streaming:
  Ollama affidabile solo in non-streaming). `keep_alive:"30m"` per non scaricare il modello.
- `chatWithFallback`/`chatToolsWithFallback` (440-467): cloud→locale se fallisce.
- `_toMultiModal` (519-534): immagini → formato visione (llava).

## nativeAgent.js (2462 righe — PARTE LETTA: 1-500)
Loop-agente locale AFFIDABILE, function-calling NATIVO Ollama in NON-streaming.
- `MAX_STEPS=24`. `MANIFESTO` (29-49): ANTI-MORALISMO (ZERO rifiuti, ZERO prediche,
  l'utente è proprietario) + PENSA A FONDO + AUTONOMIA TOTALE. Iniettato in ogni system.
- `RE_TOOLS` (57-60): diec, ghidra (percorsi reali).
- `ZW3D` (67-109): ancoraggio API ZW3D REALE (indexDir OneDrive, headersDir 2025,
  examplesDir, msbuild VS18, remotec, exe, blankPart, remotePort 8000). knowledgeDir
  DERIVATO (prova src/knowledge ed EfestoAI/knowledge, tiene chi ha l'indice). catalog
  da data/zw3d_command_catalog.json. ⚠️ I percorsi sono fissi: se cambi installazione
  ZW3D, aggiorna qui.
- `SHELL_ENV` (116-126): rileva pwsh 7 / powershell 5.1 / bash. Preferisce pwsh 7.
- `shellContextLine` (130-142): dice al modello ESATTAMENTE dove sta e quale shell usare
  (WINDOWS + PowerShell, NON cmd/linux). Critico: evita comandi a vuoto.
- `PS_PRELUDE` (147-164): forza UTF-8 + shim Unix (strings/head/tail/grep/file/which/touch/
  true/false) per PowerShell. Anti-mojibake.
- `TOOLS` (166-...): ~40 strumenti. Letti: read_file, read_image, analyze_binary,
  list_dir, search, write_file (mutante, chiede OK), run_command (mutante, chiede OK),
  system_tool (nmap/tshark/sqlmap/hashcat/john/binwalk/exiftool/volatility/strings/upx/
  pefile), binary_patch (DISTRUTTIVO, fai backup), hex_view, process_list, file_op
  (copy/move/rename/list/info, MAI delete), run_program, registry_read (solo lettura),
  remind, schedule_task, semantic_search, notify, decode (CyberChef-like), binary_diff
  (radiff2), apk_re, frida_hook, mitm_capture (sola lettura), report, git, generate_image
  (ComfyUI), delegate_to_hermes, update_todos (piano), ghidra_* (25 tool RE live:
  list_functions/search/decompile/disassemble/list_strings/decompile_at/list_imports/
  list_exports/list_classes/...), e altri.

## Parte NON ancora letta di nativeAgent (501-2462)
Implementazioni dei tool (read_file scrive su disco, run_command esegue PowerShell col
PS_PRELUDE, ghidra_* chiama ghidraClient, analyze_binary chiama reTools, generate_image
chiama comfyClient, delegate_to_hermes chiama hermesClient) + loop `run` (non-streaming,
tool-calling nativo) + `runReact` (protocollo ReAct testuale per modelli senza tool
nativi) + gestione approvazioni (askApproval) + streaming eventi (onEvent).
⚠️ Da leggere se si tocca la logica agente. Per ora mappato a grandi linee.

## Dipendenze
- localEngine: solo http.
- nativeAgent: fs/path/os/child_process, torBrowser (opzionale), ghidraClient, reTools,
  comfyClient, hermesClient, cloudEngine (per runReact con modelli cloud).

## Rischi / note
- localEngine.discover ha timeout 20s (non 5s): i modelli grandi in RAM rispondono lenti.
- nativeAgent MANIFESTO = anti-moralismo hardcoded: se lo togli, l'agente ricomincia a rifiutare.
- ZW3D ha percorsi fissi: spostare l'installazione richiede aggiornare nativeAgent.ZW3D.
- run_command gira su PowerShell (NON cmd/linux): il PS_PRELUDE evita mojibake.
- write_file/run_command/binary_patch SONO MUTANTI: passano dal gate di approvazione UI.
