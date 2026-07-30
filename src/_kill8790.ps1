$p = Get-NetTCPConnection -LocalPort 8790 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($p) {
  $p | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
  Write-Host "killed: $p"
} else {
  Write-Host "none running"
}
Start-Sleep -Seconds 2
