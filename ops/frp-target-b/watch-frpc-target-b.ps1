$ErrorActionPreference = 'SilentlyContinue'

$Frpc = 'C:\ProgramData\frp\frpc.exe'
$Config = 'C:\ProgramData\frp\frpc.toml'
$Log = 'C:\ProgramData\frp\frpc-watchdog.log'

if (-not (Test-Path -LiteralPath $Frpc) -or -not (Test-Path -LiteralPath $Config)) {
    "$(Get-Date -Format s) missing frpc or config" | Add-Content -LiteralPath $Log
    exit 1
}

$proc = Get-Process frpc -ErrorAction SilentlyContinue
if ($proc) {
    exit 0
}

"$(Get-Date -Format s) frpc not running, starting FrpcTargetB" | Add-Content -LiteralPath $Log
Start-ScheduledTask -TaskName 'FrpcTargetB'
Start-Sleep -Seconds 5

if (-not (Get-Process frpc -ErrorAction SilentlyContinue)) {
    "$(Get-Date -Format s) scheduled task did not start frpc, starting process directly" | Add-Content -LiteralPath $Log
    Start-Process -FilePath $Frpc -ArgumentList '-c "C:\ProgramData\frp\frpc.toml"' -WindowStyle Hidden
}
