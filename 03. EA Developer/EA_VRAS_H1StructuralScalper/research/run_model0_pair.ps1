param(
    [ValidateSet('pair', 'control', 'challenger')]
    [string]$Arm = 'challenger'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package = Join-Path $PSScriptRoot '..'
$preflight = Join-Path $PSScriptRoot 'preflight\HYP-VRAS-EURUSD-M5-005'
$alpha = Join-Path $repo '02. AlphaFactory\alpha.ps1'

# Rebuild preflight receipts so git status SHA matches live state exactly
& (Join-Path $PSScriptRoot 'build_matched_pair_receipts.ps1') -TargetArm $Arm

$selected = if ($Arm -eq 'pair') { @('control', 'challenger') } else { @($Arm) }

foreach ($name in $selected) {
    $taskPath = Join-Path $preflight "task_packet.$name.json"
    $receipt = Join-Path $preflight "contract_receipt.$name.json"
    $task = Get-Content -LiteralPath $taskPath -Raw | ConvertFrom-Json
    $receiptSha = (Get-FileHash -LiteralPath $receipt -Algorithm SHA256).Hash

    Write-Host "[VRAS-HYP005] Starting $name Model-0 run..."
    & $alpha backtest 'EA_VRAS_H1StructuralScalper' `
        -Symbol $task.binding.symbol -Period $task.binding.period -From $task.binding.from -To $task.binding.to `
        -Model $task.binding.model -ExecutionMode $task.binding.execution_mode -FixedDelayMs $task.binding.fixed_delay_ms `
        -Overrides $task.binding.overrides -HypothesisId $task.binding.hypothesis_id -RunRole $task.binding.run_role `
        -TelemetryTier $task.binding.telemetry_tier -Deposit $task.binding.deposit -Leverage $task.binding.leverage `
        -ContractReceipt $receipt -ContractReceiptSha256 $receiptSha `
        -RequiredSidecars '*_LifecycleTrades_*.csv;*_RunMeta_*.json;*_DecisionTelemetry_*.csv' -TimeoutSec 5400
    if ($LASTEXITCODE -ne 0) {
        throw "Model-0 $name failed with exit code $LASTEXITCODE"
    }
}
