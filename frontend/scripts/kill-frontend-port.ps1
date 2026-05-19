$ErrorActionPreference = "Stop"

$connections = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique

if (-not $connections) {
  Write-Host "Port 3000 is already free."
  exit 0
}

foreach ($processId in $connections) {
  try {
    $process = Get-Process -Id $processId -ErrorAction Stop
    Write-Host ("Stopping PID {0} ({1})" -f $process.Id, $process.ProcessName)
    Stop-Process -Id $process.Id -Force
  } catch {
    Write-Warning ("Failed to stop PID {0}: {1}" -f $processId, $_.Exception.Message)
  }
}

Write-Host "Port 3000 cleanup finished."
