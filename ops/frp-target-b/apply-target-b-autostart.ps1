$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path 'C:\\ProgramData\\ReverseSshTunnel' | Out-Null
Copy-Item 'C:\\Users\\emcyj\\.ssh\\id_rsa' 'C:\\ProgramData\\ReverseSshTunnel\\id_rsa' -Force
icacls 'C:\\ProgramData\\ReverseSshTunnel\\id_rsa' /inheritance:r /grant:r 'SYSTEM:F' 'Administrators:F' 'emcyj:R' | Out-Null
New-Item -ItemType Directory -Force -Path 'C:\\ProgramData\\ReverseSshTunnel' | Out-Null
Copy-Item 'C:\\Users\\emcyj\\AppData\\Local\\ReverseSshTunnel\\start_reverse_ssh_tunnel.ps1' 'C:\\ProgramData\\ReverseSshTunnel\\start_reverse_ssh_tunnel.ps1' -Force
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\\ProgramData\\ReverseSshTunnel\\start_reverse_ssh_tunnel.ps1"'
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName 'ReverseSshTunnel' -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'ReverseSshTunnel'
Get-ScheduledTask -TaskName 'ReverseSshTunnel' | Format-List TaskName,State,Principal
