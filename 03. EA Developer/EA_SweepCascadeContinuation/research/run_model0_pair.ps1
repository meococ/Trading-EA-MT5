param(
    [ValidateSet('control', 'challenger')]
    [string]$Arm
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$preflight = Join-Path $PSScriptRoot 'preflight\HYP-SCC-MT5-REPLICATION-EURUSD-M5-004'
$alpha = Join-Path $repo '02. AlphaFactory\alpha.ps1'
$taskPath = Join-Path $preflight "task_packet.$Arm.json"
$receiptPath = Join-Path $preflight "contract_receipt.$Arm.json"
$task = Get-Content -LiteralPath $taskPath -Raw | ConvertFrom-Json
$receiptSha = (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash

& $alpha backtest 'EA_SweepCascadeContinuation' `
    -Symbol $task.symbol -Period $task.period -From $task.from -To $task.to `
    -Model $task.model -ExecutionMode $task.execution_mode `
    -FixedDelayMs $task.fixed_delay_ms -Overrides $task.overrides `
    -HypothesisId $task.hypothesis_id -RunRole $task.run_role `
    -TelemetryTier $task.telemetry_tier -Deposit $task.deposit `
    -Leverage $task.leverage -ContractReceipt $receiptPath `
    -ContractReceiptSha256 $receiptSha `
    -RequiredSidecars ($task.required_sidecars -join ';') -TimeoutSec 5400

if ($LASTEXITCODE -ne 0) {
    throw "SCC Model-0 $Arm failed with exit code $LASTEXITCODE"
}
