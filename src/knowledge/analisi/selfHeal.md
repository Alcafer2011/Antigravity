# selfHeal.js — ANALISI RIGA PER RIGA

AUTO-RIPARAZIONE dei file dell'estensione/server. Dipende SOLO da fs/path/vm (nativi),
così può girare per primo, prima di caricare moduli che potrebbero essere corrotti.
Esporta `{ verifyAndRepair, snapshotHealthy, isHealthy, ensureHermesMcp, CRITICAL_FILES,
BACKUP_DIRNAME }`.

## isHealthy (28-49)
Un file è "sano"? Legge il contenuto; se vuoto → falso. Per `.js` compila con `vm.Script`
(senza eseguire) → intercetta troncature/errori sintassi. Per `.json` fa `JSON.parse`.
Per `.html` controlla lunghezza>32 e presenza di `<`. Altri tipi: basta non vuoto.

## verifyAndRepair (63-87)
Chiamata PRIMA di require-are gli altri moduli. Per ogni file in `CRITICAL_FILES`:
se sano → skip; se corrotto e c'è una copia sana in backup → ripristina da lì (copia
backup→src) e verifica. Ritorna lista riparati. ⚠️ NON propaga corruzioni: se il backup
stesso è corrotto, skip.

## snapshotHealthy (93-115)
Chiamata DOPO che il server è partito bene. Copia i file sani in `.self-heal-backup/`
(ignora i corrotti, così non salva roba rotta). Solo se diverso (evita scritture inutili).
⚠️ REGOLA ANTI-DANNO: quando modifichi un CRITICAL_FILE, devi copiarlo a mano nel backup
(`cp <file> .self-heal-backup/<file>`) altrimenti il self-heal ripristina la VERSIONE
VECCHIA al prossimo avvio! (vedi localOrchestrator._runMaintenance regola 2).

## CRITICAL_FILES (118-125)
localOrchestrator, localEngine, nativeAgent, cloudEngine, claudeEngine, claudeHook,
comfyClient, hermesClient, reTools, services, serverClient, mcpServer, ghidraClient,
ghidraHeadless, ghidraLauncher, providerRegistry, webSearch, learningMemory,
mobileServer, mobile-page.html, kaggleToolProxy, kaggleWaker, kaggleEngine, nousClient.
⚠️ NOTA: apply-change.ps1 e la REGOLA assoluta devono includere questo elenco nel backup.

## ensureHermesMcp (139-179)
LOCK: garantisce Antigravity registrato come server MCP in Hermes. Se un "autofix" di
Hermes riscrive config.yaml e toglie il nostro blocco, lo RI-AGGIUNGE al prossimo avvio
del server (nascosto, via autostart Windows). Idempotente: se il blocco c'è, non tocca.
Scrive sotto `mcp_servers:` in `%LOCALAPPDATA%/hermes/config.yaml` puntando a mcpServer.js.

## Dipendenze
- Solo nativi (fs/path/vm).

## Rischi / note
- Il backup è in `src/.self-heal-backup/`: se lo cancelli, il self-heal non ha copia sana.
- La sincronizzazione estensione↔cuore che ho fatto oggi DEVE replicare anche nel backup
  se tocchiamo i CRITICAL_FILES dell'estensione.
