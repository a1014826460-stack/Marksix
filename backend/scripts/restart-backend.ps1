$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\pythonProject\outsource\Liuhecai"
$BackendRoot = Join-Path $ProjectRoot "backend"
$PythonExe = "D:\python\python.exe"
$DefaultDbUrl = "postgresql://postgres:2225427@localhost:5432/liuhecai"
$Port = 8000

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

function Test-PortReleased {
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) {
        Write-Host "Port $Port is free."
        return
    }

    Write-Host "Port $Port still has listeners:"
    $listeners | Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize
    throw "Port $Port is still occupied."
}

function Start-Backend {
    param(
        [string]$DbUrl = $DefaultDbUrl
    )

    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }

    $command = "`"$PythonExe`" backend/src/app.py --db_path $DbUrl"
    Write-Host "Starting backend..."
    Write-Host "  $command"

    $process = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @("backend/src/app.py", "--db_path", $DbUrl) `
        -WorkingDirectory $ProjectRoot `
        -PassThru

    Start-Sleep -Seconds 2

    Write-Host ("Started backend PID: {0}" -f $process.Id)
}

Stop-BackendProcesses
Test-PortReleased
Start-Backend

Write-Host ""
Write-Host "Done. You can now retry: http://127.0.0.1:8000/"
