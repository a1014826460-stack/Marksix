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

New-Item -ItemType Directory -Force -Path 'C:\ProgramData\frp' | Out-Null
Copy-Item 'C:\frp\frpc.exe' 'C:\ProgramData\frp\frpc.exe' -Force
Copy-Item 'C:\frp\frpc.toml' 'C:\ProgramData\frp\frpc.toml' -Force
try { Stop-Service frpc-target-b -ErrorAction SilentlyContinue } catch {}
try { sc.exe delete frpc-target-b | Out-Null } catch {}
$action = New-ScheduledTaskAction -Execute 'C:\ProgramData\frp\frpc.exe' -Argument '-c "C:\ProgramData\frp\frpc.toml"'
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName 'FrpcTargetB' -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'FrpcTargetB'
Get-ScheduledTask -TaskName 'FrpcTargetB' | Format-List TaskName,State,TaskPath,Principal
