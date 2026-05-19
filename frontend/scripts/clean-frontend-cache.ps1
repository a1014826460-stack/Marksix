$ErrorActionPreference = "Stop"

$target = Join-Path $PSScriptRoot "..\.next"
$resolvedTarget = [System.IO.Path]::GetFullPath($target)

if (-not (Test-Path $resolvedTarget)) {
  Write-Host "frontend/.next does not exist."
  exit 0
}

Write-Host ("Removing cache directory: {0}" -f $resolvedTarget)
Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
Write-Host "frontend/.next cleanup finished."
