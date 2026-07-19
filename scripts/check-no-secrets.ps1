$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Targets = @(
    "backend/scripts/restart-backend.ps1",
    "ops/frp-target-b/frpc.toml",
    "ops/frp-target-b/install-frpc-target-b.ps1",
    "backend/src/deprecated/tools/generate_missing_types.py",
    "backend/src/deprecated/tools/repair_created_mode_payload_197.py",
    "backend/src/tests/brain_teaser_image_generator.py"
)
$PostgresPasswordPattern = 'postgres(?:ql)?://[^:\s]+:[^@\s]+@'
$FrpTokenPattern = '(?mi)^\s*auth\.token\s*=\s*["''][0-9a-f]{24,}["'']'
$Findings = @()

foreach ($RelativePath in $Targets) {
    $Path = Join-Path $ProjectRoot $RelativePath
    $Content = Get-Content -Raw -LiteralPath $Path
    if ($Content -match $PostgresPasswordPattern) {
        $Findings += "${RelativePath}: PostgreSQL password embedded in DSN"
    }
    if ($Content -match $FrpTokenPattern) {
        $Findings += "${RelativePath}: FRP token embedded in config"
    }
}

if ($Findings) {
    $Findings | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Secret scan passed."
