$ErrorActionPreference = 'Stop'

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        '-NoProfile'
        '-ExecutionPolicy'
        'Bypass'
        '-File'
        "`"$scriptPath`""
    )
    return
}

$watchScript = 'C:\ProgramData\frp\watch-frpc-target-b.ps1'
if (-not (Test-Path -LiteralPath $watchScript)) {
    throw "Missing $watchScript"
}

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\frp\watch-frpc-target-b.ps1"'
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal `
    -UserId 'SYSTEM' `
    -LogonType ServiceAccount `
    -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask `
    -TaskName 'FrpcTargetBWatchdog' `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName 'FrpcTargetBWatchdog'
Get-ScheduledTask -TaskName 'FrpcTargetBWatchdog' | Format-List TaskName,State,TaskPath,Principal
