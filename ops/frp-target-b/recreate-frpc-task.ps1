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

Stop-Process -Name frpc -Force -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute 'C:\ProgramData\frp\frpc.exe' -Argument '-c "C:\ProgramData\frp\frpc.toml"'
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask -TaskName 'FrpcTargetB' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'FrpcTargetB'
Get-ScheduledTask -TaskName 'FrpcTargetB' | Format-List TaskName,State,TaskPath,Principal
