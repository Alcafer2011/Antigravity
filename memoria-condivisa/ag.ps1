<#
  ag.ps1 — cassetta degli attrezzi Antigravity.
  Un solo comando da ricordare. Funziona identico da PowerShell tuo e da Claude/Hermes.

    ag diagnosi          fotografa RAM, browser orfani, server mobile — e scrive nel diario
    ag pulisci           chiude i browser agente orfani e libera la RAM  (-Anche node)
    ag guardia           installa la pulizia automatica ogni 30 minuti   (ag guardia via = toglie)
    ag riavvia           riavvia il server mobile su :8790
    ag stato             stampa STATO.md
    ag nota "testo"      aggiunge una riga al diario condiviso
    ag hermes "mandato"  lancia Hermes con la memoria condivisa già in testa
    ag apri              stampa il link col token per il telefono
#>
param(
  [Parameter(Position=0)][string]$Comando = "aiuto",
  [Parameter(Position=1, ValueFromRemainingArguments=$true)][string[]]$Resto
)

$ErrorActionPreference = 'Stop'
$RADICE  = Split-Path -Parent $PSCommandPath
$PROG    = Split-Path -Parent $RADICE          # C:\Users\infoa\Antigravity
$STATO   = Join-Path $RADICE 'STATO.md'
$Testo   = ($Resto -join ' ')

function Ora { (Get-Date).ToString('yyyy-MM-dd HH:mm') }
function Dì([string]$m, [string]$c = 'Gray') { Write-Host $m -ForegroundColor $c }
function Titolo([string]$m) { Write-Host ''; Write-Host "== $m" -ForegroundColor Cyan }

# --- diario condiviso: ogni azione lascia traccia, così nessuno rispiega niente ---
function Nota([string]$riga) {
  if (-not (Test-Path $STATO)) { return }
  Add-Content -Path $STATO -Value ("- **{0}** — {1}" -f (Ora), $riga) -Encoding UTF8
}

# --- i browser orfani: SOLO quelli con profilo temporaneo agent-browser-chrome-*.
#     Il Chrome con cui navighi tu non ha quel profilo e non viene mai toccato. ---
function BrowserOrfani {
  $tutti = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue)
  if (-not $tutti) { return @() }
  $radici = $tutti | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -notmatch '--type=' -and
    $_.CommandLine -match 'agent-browser-chrome-'
  }
  $pidRadici = @($radici.ProcessId)
  if (-not $pidRadici) { return @() }
  # discendenti (renderer, gpu, utility, crashpad) + le radici stesse
  $figli = $tutti | Where-Object { $pidRadici -contains $_.ParentProcessId }
  @($radici) + @($figli)
}

function RamGB {
  param($proc)
  if (-not $proc) { return 0 }
  # gli oggetti CIM usano WorkingSetSize, quelli di Get-Process WorkingSet64
  $b = 0
  foreach ($p in $proc) { $b += [double]($p.WorkingSetSize ?? $p.WorkingSet64 ?? 0) }
  [math]::Round($b / 1GB, 2)
}

switch -Regex ($Comando) {

  '^diagnosi$' {
    $os     = Get-CimInstance Win32_OperatingSystem
    $tot    = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    $libera = [math]::Round($os.FreePhysicalMemory   / 1MB, 1)
    $orfani = BrowserOrfani
    $nOrf   = ($orfani | Where-Object { $_.CommandLine -notmatch '--type=' }).Count
    $ramOrf = RamGB $orfani
    $node   = @(Get-Process node -ErrorAction SilentlyContinue)

    Titolo "MEMORIA"
    $colore = if ($libera -lt 4) { 'Red' } elseif ($libera -lt 8) { 'Yellow' } else { 'Green' }
    Dì ("  RAM totale : {0} GB" -f $tot)
    Write-Host ("  RAM libera : {0} GB" -f $libera) -ForegroundColor $colore

    Titolo "BROWSER AGENTE ORFANI  <-- e' questa la causa dei blocchi"
    if ($nOrf -eq 0) { Dì "  nessuno. Pulito." 'Green' }
    else { Write-Host ("  {0} browser ({1} processi) che occupano {2} GB  ->  ag pulisci" -f $nOrf, $orfani.Count, $ramOrf) -ForegroundColor Red }

    Titolo "ALTRO"
    Dì ("  node.exe (server MCP) : {0} processi, {1} GB" -f $node.Count, (RamGB $node))

    Titolo "SERVER MOBILE :8790"
    $tok = $null
    if (Test-Path (Join-Path $PROG '.env')) {
      $m = Select-String -Path (Join-Path $PROG '.env') -Pattern '^\s*MOBILE_TOKEN\s*=\s*(.+)$' | Select-Object -First 1
      if ($m) { $tok = $m.Matches[0].Groups[1].Value.Trim().Trim('"') }
    }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
      $u = "http://127.0.0.1:8790/" + $(if ($tok) { "?t=$tok" } else { "" })
      $r = Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 30
      $sw.Stop()
      $c = if ($sw.ElapsedMilliseconds -gt 3000) { 'Red' } elseif ($sw.ElapsedMilliseconds -gt 1000) { 'Yellow' } else { 'Green' }
      Write-Host ("  risponde {0} in {1} ms ({2} KB)" -f $r.StatusCode, $sw.ElapsedMilliseconds, [math]::Round($r.RawContentLength/1KB)) -ForegroundColor $c
      if ($sw.ElapsedMilliseconds -gt 3000) { Dì "  > oltre 3 secondi: il telefono qui si pianta. Lancia: ag pulisci" 'Yellow' }
    } catch { $sw.Stop(); Write-Host "  NON RISPONDE -> ag riavvia" -ForegroundColor Red }

    Write-Host ''
    if ($nOrf -gt 0) { Write-Host "  VERDETTO: RAM mangiata dai browser orfani. Lancia:  ag pulisci  e poi  ag guardia" -ForegroundColor Yellow }
    else { Write-Host "  VERDETTO: memoria a posto. Se si blocca ancora, e' un'altra causa: scrivila con  ag nota" -ForegroundColor Green }
    Nota ("diagnosi: {0} GB liberi su {1}, {2} browser orfani ({3} GB), node {4}" -f $libera, $tot, $nOrf, $ramOrf, $node.Count)
  }

  '^pulisci$' {
    $orfani = BrowserOrfani
    $nOrf   = ($orfani | Where-Object { $_.CommandLine -notmatch '--type=' }).Count
    $ramOrf = RamGB $orfani
    if ($orfani.Count -eq 0) { Dì "Nessun browser orfano. Niente da fare." 'Green' }
    else {
      Dì ("Chiudo {0} browser agente orfani ({1} processi, {2} GB)..." -f $nOrf, $orfani.Count, $ramOrf) 'Yellow'
      # prima i figli, poi le radici: così il browser non li fa rinascere
      foreach ($p in ($orfani | Sort-Object { $_.CommandLine -notmatch '--type=' })) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {}
      }
      # I figli muoiono qualche secondo dopo la radice: li ricontrollo per PID,
      # non per parentela (la radice ormai non c'è più e non li ritroverei).
      $pidTutti = @($orfani.ProcessId)
      $rimasti  = $pidTutti.Count
      for ($giro = 0; $giro -lt 6 -and $rimasti -gt 0; $giro++) {
        Start-Sleep -Seconds 2
        $vivi = @(Get-Process -Id $pidTutti -ErrorAction SilentlyContinue)
        foreach ($p in $vivi) { try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch {} }
        $rimasti = @(Get-Process -Id $pidTutti -ErrorAction SilentlyContinue).Count
      }
      if ($rimasti -eq 0) { Dì ("Fatto: liberati circa {0} GB." -f $ramOrf) 'Green' }
      else { Dì ("Chiusi quasi tutti; {0} processi resistono (riprova o riavvia)." -f $rimasti) 'Yellow' }
      Nota ("pulisci: chiusi {0} browser orfani, ~{1} GB liberati" -f $nOrf, $ramOrf)
    }

    # i profili temporanei restano su disco anche dopo: si portano via GB
    $prof = @(Get-ChildItem $env:TEMP -Directory -Filter 'agent-browser-chrome-*' -ErrorAction SilentlyContinue)
    if ($prof.Count) {
      $ok = 0
      foreach ($d in $prof) { try { Remove-Item $d.FullName -Recurse -Force -ErrorAction Stop; $ok++ } catch {} }
      Dì ("Profili temporanei rimossi: {0} su {1}." -f $ok, $prof.Count)
    }

    if ($Testo -match '(?i)node') {
      $vivi = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {
        $_.CommandLine -match 'npm-cache\\_npx|npx-cli\.js' -and $_.CommandLine -notmatch 'heal-and-run'
      })
      Dì ("Chiudo anche {0} server MCP node (heal-and-run resta vivo)..." -f $vivi.Count) 'Yellow'
      foreach ($p in $vivi) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }
      Nota ("pulisci -anche node: chiusi {0} processi MCP" -f $vivi.Count)
    }
  }

  '^guardia$' {
    $nome = 'Antigravity-PuliziaBrowserOrfani'
    if ($Testo -match '(?i)^via|^off|^togli') {
      try { Unregister-ScheduledTask -TaskName $nome -Confirm:$false; Dì "Guardia rimossa." 'Yellow'; Nota "guardia disinstallata" }
      catch { Dì "Non era installata." }
      break
    }
    $az  = New-ScheduledTaskAction -Execute 'powershell.exe' `
             -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" pulisci' -f $PSCommandPath)
    $tr  = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) `
             -RepetitionInterval (New-TimeSpan -Minutes 30)
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
             -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $nome -Action $az -Trigger $tr -Settings $set `
      -Description 'Chiude i browser agente orfani che saturano la RAM (vedi memoria-condivisa\STATO.md)' -Force | Out-Null
    Dì "Guardia installata: pulizia automatica ogni 30 minuti, finestra nascosta." 'Green'
    Dì "Per toglierla:  ag guardia via"
    Nota "guardia installata (pulizia automatica ogni 30 min)"
  }

  '^riavvia$' {
    $vecchi = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'heal-and-run' })
    foreach ($p in $vecchi) { try { Stop-Process -Id $p.ProcessId -Force } catch {} }
    Dì ("Fermati {0} server. Riavvio..." -f $vecchi.Count)
    Start-Process -FilePath 'wscript.exe' -ArgumentList ('"{0}"' -f (Join-Path $PROG 'antigravity-mobile-server.vbs')) -WindowStyle Hidden
    Start-Sleep -Seconds 6
    & $PSCommandPath apri
    Nota "server mobile riavviato"
  }

  '^apri$' {
    $tok = $null
    $m = Select-String -Path (Join-Path $PROG '.env') -Pattern '^\s*MOBILE_TOKEN\s*=\s*(.+)$' | Select-Object -First 1
    if ($m) { $tok = $m.Matches[0].Groups[1].Value.Trim().Trim('"') }
    Dì ("  PC        : http://localhost:8790/?t={0}" -f $tok) 'Green'
    # L'ordine conta: le schede virtuali (Hyper-V, WSL) hanno un IP che il telefono
    # non raggiungerà mai. Tailscale funziona ovunque, il Wi-Fi solo in casa.
    $ips = @(Get-NetIPAddress -AddressFamily IPv4 |
             Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' } |
             Sort-Object @{ e = {
               if     ($_.IPAddress -like '100.*')       { 0 }   # Tailscale: sempre
               elseif ($_.InterfaceAlias -match 'Wi-Fi') { 1 }   # casa
               elseif ($_.InterfaceAlias -match 'Ethernet' -and $_.InterfaceAlias -notmatch 'vEthernet') { 2 }
               else                                      { 9 }   # virtuali: inutili
             }})
    foreach ($a in $ips) {
      $eti = if ($a.IPAddress -like '100.*') { 'telefono, ovunque (Tailscale)' }
             elseif ($a.InterfaceAlias -match 'vEthernet|WSL') { 'scheda virtuale — NON funziona dal telefono' }
             else { 'telefono, stessa rete (' + $a.InterfaceAlias + ')' }
      $col = if ($eti -match 'NON funziona') { 'DarkGray' } else { 'Green' }
      Write-Host ("  {0,-15} http://{1}:8790/?t={2}   [{3}]" -f '', $a.IPAddress, $tok, $eti) -ForegroundColor $col
    }
  }

  # La scatola nera: la pagina segnala da sola quando si è inchiodata.
  # Qui si leggono le segnalazioni, senza doverle cercare a mano nel log.
  '^blocchi$' {
    $log = Join-Path $PROG 'antigravity-server.log'
    if (-not (Test-Path $log)) { Dì "Log non trovato." 'Yellow'; break }
    $righe = @(Select-String -Path $log -Pattern '\[CLIENT-ERROR\].*"tipo":"(BLOCCO|errore|promise)"' | Select-Object -Last 25)
    if (-not $righe) {
      Dì "Nessun blocco registrato." 'Green'
      Dì "Se si e' bloccato DOPO l'ultimo riavvio del server, ricarica la pagina sul telefono:"
      Dì "la scatola nera vive dentro la pagina, serve che il telefono prenda la versione nuova."
      break
    }
    Dì ("Ultimi {0} eventi dal telefono / da VS Code:" -f $righe.Count) 'Cyan'
    foreach ($r in $righe) {
      $j = $null
      if ($r.Line -match '(\{.*\})\s*$') { try { $j = $matches[1] | ConvertFrom-Json } catch {} }
      $quando = if ($r.Line -match '^\[([^\]]+)\]') { $matches[1] } else { '?' }
      if (-not $j) { Dì ("  {0}  (illeggibile)" -f $quando); continue }
      $dove = if ($j.ua -match 'iPhone|Android') { 'TELEFONO' } elseif ($j.ua -match 'Electron') { 'VS CODE' } else { 'browser' }
      if ($j.tipo -eq 'BLOCCO') {
        Write-Host ("  {0}  [{1}]  BLOCCATA {2} s" -f $quando, $dove, [math]::Round($j.bloccatoPerMs/1000,1)) -ForegroundColor Red
        Dì ("      ultimo gesto : {0}" -f $j.ultimoGesto)
        Dì ("      menu modelli : {0} voci   nodi pagina: {1}" -f $j.opzioniModello, $j.nodiPagina)
      } else {
        Write-Host ("  {0}  [{1}]  {2}: {3}" -f $quando, $dove, $j.tipo, $j.messaggio) -ForegroundColor Yellow
        if ($j.stack) { Dì ("      {0}" -f ($j.stack -split "`n")[0]) }
      }
    }
  }

  '^stato$' { Get-Content $STATO -Encoding UTF8 }

  '^nota$' {
    if (-not $Testo) { Dì 'Uso: ag nota "cosa e'' successo"' 'Yellow'; break }
    Nota $Testo
    Dì "Scritto nel diario condiviso." 'Green'
  }

  '^hermes$' {
    if (-not $Testo) { Dì 'Uso: ag hermes "il mandato"' 'Yellow'; break }
    $exe = Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent\venv\Scripts\hermes.exe'
    if (-not (Test-Path $exe)) { Dì "Hermes non trovato in $exe" 'Red'; break }
    if (-not $env:HERMES_HOME) { $env:HERMES_HOME = Join-Path $env:LOCALAPPDATA 'hermes' }

    # Il preambolo è ciò che rende la memoria DAVVERO condivisa: stesso file,
    # stessa sessione --continue antigravity, stesse regole per tutti.
    $mandato = @"
Prima di tutto leggi il file $STATO : è la memoria condivisa del progetto, la scrivono
sia Claude Code sia tu. Contiene la diagnosi già chiusa e i lavori aperti: non rifare
quello che risulta già fatto.

MANDATO: $Testo

REGOLE:
- Lavora dentro C:\Users\infoa\Antigravity.
- Verifica sul file quello che scrivi. Dichiarare "fatto" una modifica non salvata
  su disco è l'errore più grave; "non ci sono riuscito perché X" è una risposta
  perfettamente accettabile, un "fatto" falso no.
- Alla fine aggiungi in fondo a $STATO , sotto '## 5. DIARIO', una riga sola:
  "- **<data ora>** — <cosa hai fatto davvero, o cosa ti ha bloccato>".
"@
    Dì "Hermes al lavoro (sessione condivisa 'antigravity')..." 'Cyan'
    & $exe -z $mandato --continue antigravity --provider nous -m 'stepfun/step-3.7-flash:free'
  }

  default {
    Write-Host @"

  ag — cassetta degli attrezzi Antigravity

    ag diagnosi           guarda com'e' messo il PC e il server mobile
    ag pulisci            libera la RAM dai browser agente orfani
    ag pulisci node       ...e chiude anche i server MCP node di troppo
    ag guardia            pulizia automatica ogni 30 min (ag guardia via = toglie)
    ag blocchi            SCATOLA NERA: cosa si e' inchiodato, quando, dopo quale gesto
    ag riavvia            riavvia il server mobile :8790
    ag apri               link col token per il telefono
    ag stato              leggi la memoria condivisa
    ag nota "testo"       scrivi nella memoria condivisa
    ag hermes "mandato"   delega a Hermes con la memoria gia' in testa

"@ -ForegroundColor Cyan
  }
}
