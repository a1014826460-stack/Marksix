$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\pythonProject\outsource\Liuhecai"
$BackendRoot = Join-Path $ProjectRoot "backend"
$PythonExe = "D:\python\python.exe"

# Local secrets stay in the ignored backend/.env.local file.
$LocalEnvFile = Join-Path $BackendRoot ".env.local"
if (Test-Path $LocalEnvFile) {
    foreach ($line in Get-Content -LiteralPath $LocalEnvFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
            $name = $Matches[1]
            $value = $Matches[2]
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

$NodeExe = (Get-Command node).Source
$PowerShellExe = (Get-Command powershell.exe).Source
$NextCli = Join-Path $BackendRoot "node_modules\next\dist\bin\next"
$DefaultDbUrl = $env:DATABASE_URL
$Port = 8000
$AdminPort = 3002
$BackendConsoleMarker = "LIUHECAI_BACKEND_CONSOLE"
$AdminConsoleMarker = "LIUHECAI_BACKEND_ADMIN_CONSOLE"
$SchedulerWorkerConsoleMarker = "LIUHECAI_SCHEDULER_WORKER_CONSOLE"

function Get-BackendProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^python(\.exe)?$' -and
            $_.CommandLine -and
            (
                $_.CommandLine -like "*backend/src/app.py*" -or
                $_.CommandLine -like "*backend/src/main.py*"
            )
        }
}

function Get-BackendAdminProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^node(\.exe)?$' -and
            $_.CommandLine -and
            (
                $_.CommandLine -like "*next dev*" -and
                $_.CommandLine -like "*3002*"
            )
        }
}

function Get-SchedulerWorkerProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^python(\.exe)?$' -and
            $_.CommandLine -and
            $_.CommandLine -like "*backend/src/scheduler_worker.py*"
        }
}

function Get-ManagedConsoleProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^powershell(\.exe)?$' -and
            $_.CommandLine -and
            (
                $_.CommandLine -like "*$BackendConsoleMarker*" -or
                $_.CommandLine -like "*$AdminConsoleMarker*" -or
                $_.CommandLine -like "*$SchedulerWorkerConsoleMarker*"
            )
        }
}

function Stop-BackendProcesses {
    $listenerPids = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    $targets = @()
    if ($listenerPids.Count -gt 0) {
        $targets = Get-CimInstance Win32_Process |
            Where-Object {
                $_.ProcessId -in $listenerPids -and
                $_.Name -match '^python(\.exe)?$' -and
                $_.CommandLine -and
                (
                    $_.CommandLine -like "*backend/src/app.py*" -or
                    $_.CommandLine -like "*backend/src/main.py*"
                )
            }
    }

    if (-not $targets) {
        $targets = Get-BackendProcesses
    }

    if (-not $targets) {
        Write-Host "No matching backend python processes found."
        return
    }

    Write-Host "Stopping backend processes..."
    foreach ($proc in $targets) {
        Write-Host ("  PID {0} -> {1}" -f $proc.ProcessId, $proc.CommandLine)
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2
}

function Stop-BackendAdminProcesses {
    $listenerPids = @(
        Get-NetTCPConnection -LocalPort $AdminPort -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    $targets = @()
    if ($listenerPids.Count -gt 0) {
        $targets = Get-CimInstance Win32_Process |
            Where-Object {
                $_.ProcessId -in $listenerPids -and
                $_.Name -match '^node(\.exe)?$' -and
                $_.CommandLine -and
                (
                    $_.CommandLine -like "*next dev*" -and
                    $_.CommandLine -like "*3002*"
                )
            }
    }

    if (-not $targets) {
        $targets = Get-BackendAdminProcesses
    }

    if (-not $targets) {
        Write-Host "No matching backend admin processes found."
        return
    }

    Write-Host "Stopping backend admin processes..."
    foreach ($proc in $targets) {
        Write-Host ("  PID {0} -> {1}" -f $proc.ProcessId, $proc.CommandLine)
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2
}

function Stop-SchedulerWorkerProcesses {
    $targets = Get-SchedulerWorkerProcesses
    if (-not $targets) {
        Write-Host "No matching scheduler worker processes found."
        return
    }

    Write-Host "Stopping scheduler worker processes..."
    foreach ($proc in $targets) {
        Write-Host ("  PID {0} -> {1}" -f $proc.ProcessId, $proc.CommandLine)
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2
}

function Stop-ManagedConsoleProcesses {
    $targets = Get-ManagedConsoleProcesses
    if (-not $targets) {
        return
    }

    Write-Host "Stopping managed console windows..."
    foreach ($proc in $targets) {
        Write-Host ("  PID {0} -> {1}" -f $proc.ProcessId, $proc.CommandLine)
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 1
}

function Test-PortReleased {
    param(
        [int]$TargetPort
    )

    $listeners = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) {
        Write-Host "Port $TargetPort is free."
        return
    }

    Write-Host "Port $TargetPort still has listeners:"
    $listeners | Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize
    throw "Port $TargetPort is still occupied."
}

function Start-Backend {
    param(
        [string]$DbUrl = $DefaultDbUrl
    )

    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }
    if ([string]::IsNullOrWhiteSpace($DbUrl)) {
        throw "DATABASE_URL must be set before starting the backend."
    }

    Write-Host "Starting backend..."
    Write-Host "  $PythonExe backend/src/app.py --db_path <DATABASE_URL>"
    $windowCommand = @"
`$env:$BackendConsoleMarker = '1'
`$Host.UI.RawUI.WindowTitle = 'Liuhecai Backend :8000'
Set-Location '$ProjectRoot'
Write-Host 'Starting Liuhecai backend on http://127.0.0.1:$Port/' -ForegroundColor Cyan
Write-Host ''
& '$PythonExe' 'backend/src/app.py' --db_path '$DbUrl'
"@

    $process = Start-Process `
        -FilePath $PowerShellExe `
        -ArgumentList @('-NoExit', '-Command', $windowCommand) `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Normal `
        -PassThru

    Start-Sleep -Seconds 3

    if ($process.HasExited) {
        throw "Backend exited immediately with code $($process.ExitCode). See logs above."
    }

    Write-Host ("Started backend PID: {0}" -f $process.Id)
}

function Start-BackendAdmin {
    if (-not (Test-Path $NodeExe)) {
        throw "node executable not found: $NodeExe"
    }

    if (-not (Test-Path $NextCli)) {
        throw "Next CLI not found: $NextCli"
    }

    $command = "`"$NodeExe`" `"$NextCli`" dev --hostname 127.0.0.1 --port $AdminPort"
    Write-Host "Starting backend admin..."
    Write-Host "  $command"
    $windowCommand = @"
`$env:$AdminConsoleMarker = '1'
`$Host.UI.RawUI.WindowTitle = 'Liuhecai Backend Admin :3002'
Set-Location '$BackendRoot'
Write-Host 'Starting backend admin on http://127.0.0.1:$AdminPort/fackyou/login' -ForegroundColor Cyan
Write-Host ''
& '$NodeExe' '$NextCli' dev --hostname 127.0.0.1 --port $AdminPort
"@

    $process = Start-Process `
        -FilePath $PowerShellExe `
        -ArgumentList @('-NoExit', '-Command', $windowCommand) `
        -WorkingDirectory $BackendRoot `
        -WindowStyle Normal `
        -PassThru

    Start-Sleep -Seconds 5

    if ($process.HasExited) {
        throw "Backend admin exited immediately with code $($process.ExitCode). See logs above."
    }

    Write-Host ("Started backend admin PID: {0}" -f $process.Id)
}

function Start-SchedulerWorker {
    param(
        [string]$DbUrl = $DefaultDbUrl
    )

    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }
    if ([string]::IsNullOrWhiteSpace($DbUrl)) {
        throw "DATABASE_URL must be set before starting the scheduler worker."
    }

    Write-Host "Starting scheduler worker..."
    Write-Host "  $PythonExe backend/src/scheduler_worker.py --db_path <DATABASE_URL>"
    $windowCommand = @"
`$env:$SchedulerWorkerConsoleMarker = '1'
`$Host.UI.RawUI.WindowTitle = 'Liuhecai Scheduler Worker'
Set-Location '$ProjectRoot'
Write-Host 'Starting Liuhecai scheduler worker' -ForegroundColor Cyan
Write-Host ''
& '$PythonExe' 'backend/src/scheduler_worker.py' --db_path '$DbUrl'
"@

    $process = Start-Process `
        -FilePath $PowerShellExe `
        -ArgumentList @('-NoExit', '-Command', $windowCommand) `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Normal `
        -PassThru

    Start-Sleep -Seconds 3

    if ($process.HasExited) {
        throw "Scheduler worker exited immediately with code $($process.ExitCode). See logs above."
    }

    Write-Host ("Started scheduler worker PID: {0}" -f $process.Id)
}

function Test-SchedulerWorkerHealthy {
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
            if ($health.scheduler_worker.active -eq $true) {
                Write-Host ("Scheduler worker healthy: {0}" -f $health.scheduler_worker.holder_id)
                return
            }
        } catch {
            # The HTTP API or worker may still be initializing.
        }
        Start-Sleep -Seconds 1
    }
    throw "Scheduler worker did not acquire its lease. Check the Scheduler Worker console."
}

Stop-ManagedConsoleProcesses
Stop-BackendProcesses
Stop-BackendAdminProcesses
Stop-SchedulerWorkerProcesses
Test-PortReleased -TargetPort $Port
Test-PortReleased -TargetPort $AdminPort
Start-Backend
Start-BackendAdmin
Start-SchedulerWorker
Test-SchedulerWorkerHealthy

Write-Host ""
Write-Host "Done. Backend: http://127.0.0.1:8000/"
Write-Host "Done. Backend admin: http://127.0.0.1:3002/fackyou/login"
Write-Host "Done. Scheduler worker: active"
