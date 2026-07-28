[CmdletBinding()]
param(
    [string[]]$PytestArgs = @()
)

$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = $utf8
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $repoRoot
try {
    $env:PYTHONPATH = (Resolve-Path 'backend/src').Path
    $groups = [ordered]@{
        generation = @(
            'backend/src/tests/unit/test_prediction_generation_control_integration.py',
            'backend/src/tests/unit/test_prediction_generation_simulation_integration.py',
            'backend/src/tests/unit/test_prediction_generation_overwrite_guard.py'
        )
        'missing-alert' = @(
            'backend/src/tests/unit/test_alert_service.py'
        )
        'scheduled-draw' = @(
            'backend/src/tests/unit/test_scheduler_worker_separation.py',
            'backend/src/tests/unit/test_scheduler_task_loop_runs.py',
            'backend/src/tests/unit/test_taiwan_next_issue_logic.py'
        )
        'public-redaction' = @(
            'backend/src/tests/unit/test_prediction_safety_service.py',
            'backend/src/tests/unit/test_api_contract_prediction_routes.py',
            'backend/src/tests/unit/test_api_contract_public_routes.py',
            'backend/src/tests/unit/test_public_api_image_url.py'
        )
    }

    foreach ($entry in $groups.GetEnumerator()) {
        Write-Host "== $($entry.Key) =="
        & python -m pytest @($entry.Value) @PytestArgs -q
        if ($LASTEXITCODE -ne 0) {
            throw "Prediction release review failed in group: $($entry.Key)"
        }
    }
}
finally {
    Pop-Location
}
