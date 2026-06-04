param(
    [string]$RemoteUser = "root",
    [string]$RemoteHost = "103.203.48.178",
    [int]$RemotePort = 19789,
    [string]$LocalHost = "127.0.0.1",
    [int]$LocalPort = 22,
    [string]$KeyFile = "C:\ProgramData\ReverseSshTunnel\id_rsa",
    [string]$LogDir = "$env:LOCALAPPDATA\ReverseSshTunnel",
    [int]$ReconnectDelaySeconds = 10,
    [int]$BootstrapDelaySeconds = 30
)

$ErrorActionPreference = "Stop"

function Write-TunnelLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $script:LogFile -Value "[$timestamp] $Message" -Encoding UTF8
}

function Resolve-SshPath {
    $command = Get-Command ssh.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidates = @(
        "$env:WINDIR\System32\OpenSSH\ssh.exe",
        "$env:ProgramFiles\Git\usr\bin\ssh.exe",
        "${env:ProgramFiles(x86)}\Git\usr\bin\ssh.exe",
        "$env:ProgramFiles\OpenSSH-Win64\ssh.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    throw "ssh.exe not found."
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir "tunnel.log"
$lockFile = Join-Path $LogDir "watchdog.lock"

$mutexName = "ReverseSshTunnel_${RemoteHost}_${RemotePort}".Replace(".", "_")
$mutex = [System.Threading.Mutex]::new($false, $mutexName)
if (-not $mutex.WaitOne(0)) { exit 0 }

try {
    Set-Content -LiteralPath $lockFile -Value "$PID" -Encoding ASCII
    $sshExe = Resolve-SshPath
    Write-TunnelLog "Watchdog started. PID=$PID, SSH=$sshExe"
    Write-TunnelLog "Target: ${RemoteUser}@${RemoteHost}:${RemotePort} -> ${LocalHost}:${LocalPort}"

    Start-Sleep -Seconds $BootstrapDelaySeconds

    while ($true) {
        try {
            $reachable = Test-NetConnection -ComputerName $RemoteHost -Port $RemotePort -InformationLevel Quiet
            if (-not $reachable) {
                Write-TunnelLog "Remote unavailable: ${RemoteHost}:${RemotePort}. Retry after ${ReconnectDelaySeconds}s."
                Start-Sleep -Seconds $ReconnectDelaySeconds
                continue
            }

            $arguments = @(
                "-N",
                "-T",
                "-i", $KeyFile,
                "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=15",
                "-o", "ServerAliveCountMax=2",
                "-o", "TCPKeepAlive=yes",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "BatchMode=yes",
                "-R", "127.0.0.1:${RemotePort}:${LocalHost}:${LocalPort}",
                "${RemoteUser}@${RemoteHost}"
            )

            Write-TunnelLog "Starting SSH tunnel."
            & $sshExe @arguments 2>&1 | ForEach-Object { Write-TunnelLog "ssh: $_" }
            Write-TunnelLog "SSH exited. ExitCode=$LASTEXITCODE. Reconnect after ${ReconnectDelaySeconds}s."
        }
        catch {
            Write-TunnelLog "Watchdog error: $($_.Exception.Message). Retry after ${ReconnectDelaySeconds}s."
        }
        Start-Sleep -Seconds $ReconnectDelaySeconds
    }
}
finally {
    Remove-Item -LiteralPath $lockFile -Force -ErrorAction SilentlyContinue
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
