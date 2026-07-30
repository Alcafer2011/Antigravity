# Moduli Ghidra / RE — ANALISI RIGA PER RIGA

Quattro file per il reverse engineering: ghidraClient (ponte HTTP), ghidraLauncher
(avvio Ghidra), ghidraHeadless (analisi senza GUI), reTools (toolchain RE locale).

## ghidraClient.js (111 righe)
Ponte HTTP verso il plugin GhidraMCP (LaurieWired) su `http://127.0.0.1:8080/`
(default da `GHIDRA_SERVER` nel .env). Solo modulo `http` di Node.
- `_request` (28-63): GET/POST verso endpoint GhidraMCP. Timeout 15s. Se risposta
  >200KB → tronca (anti-intasamento). Su ECONNREFUSED/timeout → messaggio GHIDRA_OFFLINE
  con istruzioni (apri Ghidra, carica programma, attiva plugin porta 8080).
- Lettura (sicure): ping, listFunctions, searchFunctions, decompileByName/ByAddress,
  disassemble, listStrings/Imports/Exports/Classes/Segments, xrefsTo/From, functionXrefs,
  namespaces, data, getCurrentAddress/Function.
- Scrittura (mutano il programma, passano dal gate di approvazione in localOrchestrator):
  renameFunction(+byAddress), renameData, renameVariable, setDecompilerComment,
  setDisassemblyComment, setFunctionPrototype, setLocalVariableType.
- ⚠️ Le operazioni di SCRITTURA vanno usate con cautela: rinominano/commentano nel
  programma aperto. Il gate di approvazione (UI) le protegge.

## ghidraLauncher.js (106 righe)
Avvia Ghidra "a un bottone". `GHIDRA_RUN_CANDIDATES` (17-20): chocolatey o Program Files.
- `isServerUp`/`programLoaded`: probe su porta 8080.
- `launchGhidra` (53-79): avvia ghidraRun.bat via VBS nascosto (Run(...,0,False)) così
  niente finestra nera (fix findstr/wmic figli). Fallback a cmd.exe se VBS non scrivibile.
- `ensureReady(onStatus)` (89-104): se server già up → ritorna; altrimenti avvia e
  aspetta ~90s (45×2s). Ritorna `{up, loaded}` o `{up:false, error}`.
- ⚠️ L'import del binario nel CodeBrowser resta manuale (GUI). Il launcher fa il resto.

## ghidraHeadless.js (87 righe)
Analisi Ghidra SENZA GUI: analyzeHeadless + script decompile_dump.java. `HEADLESS_CANDIDATES`
(come launcher). `SCRIPT_DIR = ~/ghidra_scripts`.
- `analyzeFile(binaryPath, {functionName, timeoutMs})` (37-85): importa in progetto
  temp, esegue postScript decompile_dump.java, cancella progetto. Timeout 5 min.
  Estrae output dopo `=== FUNZIONI/DECOMPILE`. Se PyGhidra/OSGi fallisce → indirizza
  al flusso GUI. ⚠️ Più lento del flusso live (rifà l'analisi ogni volta).

## reTools.js (72 righe)
Toolchain RE installata localmente. `RE_TOOLS` (10-13): diec (Detect-It-Easy a
`C:\RE-Tools\die\die\diec.exe`), ghidra (analyzeHeadless).
- `analyzeBinary(fp)` (16-70): (1) Detect-It-Easy (tipo/packer/compilatore); (2) pefile
  (header PE, sezioni, import/export via script Python temporaneo `antigravity_pe.py`);
  (3) stringhe stampabili rilevanti (.dll/.exe/http/key/licen/passw/regist/error/version).
  Output troncato a 40KB. ⚠️ Richiede python+pefile installati; se mancano, fallback
  a stringhe nativo.

## Dipendenze incrociate
- localOrchestrator._runGhidra → ghidraLauncher.ensureReady + agente con 25 tool
  `ghidra_*`. I tool `ghidra_*` sono esposti da NativeAgent (vedi nativeAgent) e mappati
  su ghidraClient.
- L'uncensored per Ghidra (modifica di oggi in localOrchestrator) fa partire la catena
  failover con modelli senza filtri in TESTA per il canale ghidra.

## Rischi / note
- GhidraMCP deve essere installato e attivo su porta 8080 (plugin GUI, non automatizzabile).
- Le scritture su Ghidra mutano il programma: sempre con approvazione UI.
- reTools richiede `C:\RE-Tools\die\...` e python+pefile; se assenti, analisi parziale.
