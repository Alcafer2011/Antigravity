# apply-change.ps1 — Antigravity: applica modifiche in modo SICURO e AUTOMATICO.
# Esegue: backup -> node --check -> riavvio server 8790 -> sync estensione VS Code.
# USO:  powershell.exe -ExecutionPolicy Bypass -File "<cartella>\apply-change.ps1"
# NOTA: il MAINTENANCE-LOG.md va aggiornato a MANO (R4 della REGOLA ASSOLUTA).
#
# ★ 2026-07-30 — CONSOLIDAMENTO: lo script ora si localizza da solo ($PSScriptRoot).
#   Prima puntava a "C:\Users\infoa\src" (una copia VECCHIA rimasta indietro) e la
#   copiava sopra l'estensione, DISTRUGGENDO il codice aggiornato ad ogni manutenzione.
#   Ora $src = cartella dove sta QUESTO script, e la sync verso l'estensione viene
#   SALTATA quando estensione e cuore sono lo stesso posto (junction/symlink).

$ErrorActionPreference = "Stop"
$src      = $PSScriptRoot
$extSrc   = "C:\Users\infoa\.vscode\extensions\local-developer.antigravity-1.0.1\src"
$backup   = Join-Path $src ".self-heal-backup"
$staging  = "C:\Users\infoa\ANTIGRAVITY_COPIE_ELIMINATE\apply_change_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss")
$port     = 8790
# lock per il fileWatcher: segnala che siamo in fase di modifica legittima
$lock = "$env:TEMP\antigravity_applychange.lock"
try { New-Item -ItemType File -Path $lock -Force | Out-Null } catch { }

# Moduli che esistono SIA nel cuore SIA nell'estensione: da sincronizzare.
$syncMods = @("providerRegistry.js","localOrchestrator.js","mcpServer.js",
               "cloudEngine.js","mobileServer.js","heal-and-run.js","selfHeal.js",
               "nativeAgent.js","services.js","ghidraClient.js","ghidraHeadless.js",
               "ghidraLauncher.js","hermesClient.js","hermesAcp.js","kaggleEngine.js",
               "kaggleWaker.js","kaggleToolProxy.js","claudeEngine.js","nousClient.js",
               "bountyHunter.js","torBrowser.js","webSearch.js","comfyClient.js",
               "learningMemory.js","reTools.js","claudeHook.js","serverClient.js",
               "cantiere.js","modelAdvisor.js","notebookTemplate.js","platformWizard.js",
               "modelMirror.js","gpuFailover.js","gpuPlatforms.js","rollback.js","bugHunter.js")

Write-Host "=== [1/4] BACKUP ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $staging | Out-Null
if (-not (Test-Path $backup)) { New-Item -ItemType Directory -Force -Path $backup | Out-Null }
# Backup di tutti i .js del cuore nello staging (così c'e' sempre un punto di ritorno)
Copy-Item "$src\*.js" $staging -Force
Write-Host "Backup in: $staging"

Write-Host "=== [2/4] node --check SU TUTTI I .js ===" -ForegroundColor Cyan
$ok = $true
Get-ChildItem "$src\*.js" | ForEach-Object {
    $r = & node --check $_.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERRORE SINTASSI in $($_.Name): $r" -ForegroundColor Red
        $ok = $false
    }
}
if (-not $ok) {
    Write-Host "=== node --check FALLITO: NON riavvio. Correggi e rilancia. ===" -ForegroundColor Red
    exit 1
}
Write-Host "Tutti i .js OK." -ForegroundColor Green

Write-Host "=== [3/4] RIAVVIO SERVER 8790 ===" -ForegroundColor Cyan
# Trova e killa il processo sulla porta 8790
$pidLine = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1 OwningProcess).OwningProcess
if ($pidLine) {
    Write-Host "Kill PID $pidLine sulla porta $port"
    Stop-Process -Id $pidLine -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
# Riavvia in background (nascosto), catturando output in log (stdout e stderr su file diversi)
$log = "$src\apply-change-server.log"
$logErr = "$src\apply-change-server.err.log"
Start-Process -FilePath "node" -ArgumentList "$src\heal-and-run.js" -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $logErr
Start-Sleep -Seconds 4
$newPid = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1 OwningProcess).OwningProcess
if ($newPid) { Write-Host "Server riavviato (PID $newPid) su $port." -ForegroundColor Green }
else { Write-Host "ATTENZIONE: server NON in ascolto dopo riavvio. Controlla $log" -ForegroundColor Yellow }

Write-Host "=== [4/5] SYNC ESTENSIONE VS CODE ===" -ForegroundColor Cyan
# GUARDIA CONSOLIDAMENTO: se l'estensione è una junction/symlink al cuore, $extSrc
# e $src puntano allo STESSO posto. Copiare i file su se stessi è inutile e, se le
# due sorgenti divergono, distruttivo. Confrontiamo i percorsi REALI e saltiamo.
$srcReal = (Get-Item -LiteralPath $src).Target; if (-not $srcReal) { $srcReal = (Get-Item -LiteralPath $src).FullName }
$extReal = $null
if (Test-Path $extSrc) { $extReal = (Get-Item -LiteralPath $extSrc).Target; if (-not $extReal) { $extReal = (Get-Item -LiteralPath $extSrc).FullName } }
if ($extReal -and ($srcReal.TrimEnd('\') -ieq $extReal.TrimEnd('\'))) {
    Write-Host "Estensione e cuore sono la STESSA cartella (junction): sync saltata (gia' consolidato)." -ForegroundColor Green
} elseif (Test-Path $extSrc) {
    # ★ 2026-07-30 — CANTIERE: i file dichiarati in un cantiere aperto NON vengono
    # copiati sull'estensione. Un file a meta' copiato nell'estensione la manda in
    # errore proprio mentre stai costruendo dal telefono.
    $protetti = @()
    $attivo = Join-Path $src ".cantiere\attivo.json"
    if (Test-Path $attivo) {
        try {
            $c = Get-Content $attivo -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($c.stato -ne "chiuso") {
                $protetti = @($c.files | ForEach-Object { Split-Path $_ -Leaf })
                Write-Host "Cantiere aperto ('$($c.titolo)'): $($protetti.Count) file NON sincronizzati." -ForegroundColor Yellow
            }
        } catch { }
    }
    foreach ($m in $syncMods) {
        if ($protetti -contains $m) { Write-Host "  saltato (cantiere): $m" -ForegroundColor Yellow; continue }
        if (Test-Path "$src\$m") { Copy-Item "$src\$m" "$extSrc\$m" -Force }
    }
    # sync anche cartella knowledge
    if (Test-Path "$src\knowledge") { Copy-Item "$src\knowledge" $extSrc -Recurse -Force }
    Write-Host "Estensione sincronizzata con il cuore." -ForegroundColor Green
} else {
    Write-Host "Estensione NON trovata in $extSrc (saltata la sync)." -ForegroundColor Yellow
}

Write-Host "=== [5/5] AGGIORNA ISTRUZIONI VIVE (auto-aggiornamento agente) ===" -ForegroundColor Cyan
# Ricompila il riassunto dell'agente: alza la versione e compatta se serve, cosi
# l'agente si aggiorna da solo ad ogni modifica senza gonfiarsi.
$ivPath = "$src\knowledge\ISTRUZIONI_VIVE.md"
if (Test-Path $ivPath) {
    $txt = Get-Content $ivPath -Raw -Encoding UTF8
    # alza versione x.y.z -> x.y.(z+1)
    if ($txt -match 'VERSION:\s*([0-9]+)\.([0-9]+)\.([0-9]+)') {
        $maj,$min,$pat = [int]$Matches[1],[int]$Matches[2],[int]$Matches[3]
        $pat++
        $newVer = "$maj.$min.$pat"
        $txt = $txt -replace 'VERSION:\s*[0-9]+\.[0-9]+\.[0-9]+', "VERSION: $newVer"
        # compatta se supera 8000 char: tieni testa (VERSION + prime 7600) e avvisa
        if ($txt.Length -gt 8000) {
            $head = $txt.Substring(0, $txt.IndexOf("`n") + 1)
            $body = $txt.Substring($txt.IndexOf("`n") + 1, [Math]::Min(7600, $txt.Length - $txt.IndexOf("`n") - 1))
            $txt = $head + $body + "`n[... compattato per tetto 8000 char ...]`n"
        }
        Set-Content $ivPath $txt -Encoding UTF8
        Write-Host "Istruzioni vive aggiornate a v$newVer." -ForegroundColor Green
    } else {
        Write-Host "VERSION non trovata in ISTRUZIONI_VIVE.md: saltato bump." -ForegroundColor Yellow
    }
} else {
    Write-Host "ISTRUZIONI_VIVE.md non trovata: saltato aggiornamento." -ForegroundColor Yellow
}

Write-Host "=== FATTO. Ora aggiorna MAINTENANCE-LOG.md (R4) e verifica GET /status?t=MOBILE_TOKEN ===" -ForegroundColor Cyan
