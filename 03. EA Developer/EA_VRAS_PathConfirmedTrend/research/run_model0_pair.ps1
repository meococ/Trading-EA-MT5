param(
    [ValidateSet('pair', 'control', 'challenger')]
    [string]$Arm = 'pair'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$preflight = Join-Path $PSScriptRoot 'preflight\HYP-VRAS-EURUSD-M5-004'
$alpha = Join-Path $repo '02. AlphaFactory\alpha.ps1'
$selected = if ($Arm -eq 'pair') { @('control', 'challenger') } else { @($Arm) }

foreach ($name in $selected) {
    $taskPath = Join-Path $preflight "task_packet.$name.json"
    $receipt = Join-Path $preflight "contract_receipt.$name.json"
    $task = Get-Content -LiteralPath $taskPath -Raw | ConvertFrom-Json
    $receiptSha = (Get-FileHash -LiteralPath $receipt -Algorithm SHA256).Hash

    Write-Host "[VRAS-HYP004] Starting $name Model-0 run..."
    & $alpha backtest 'EA_VRAS_PathConfirmedTrend' `
        -Symbol $task.symbol -Period $task.period -From $task.from -To $task.to `
        -Model $task.model -ExecutionMode $task.execution_mode -FixedDelayMs $task.fixed_delay_ms `
        -Overrides $task.overrides -HypothesisId $task.hypothesis_id -RunRole $task.run_role `
        -TelemetryTier $task.telemetry_tier -Deposit $task.deposit -Leverage $task.leverage `
        -ContractReceipt $receipt -ContractReceiptSha256 $receiptSha `
        -RequiredSidecars ($task.required_sidecars -join ';') -TimeoutSec 5400
    if ($LASTEXITCODE -ne 0) {
        throw "Model-0 $name failed with exit code $LASTEXITCODE"
    }
}
