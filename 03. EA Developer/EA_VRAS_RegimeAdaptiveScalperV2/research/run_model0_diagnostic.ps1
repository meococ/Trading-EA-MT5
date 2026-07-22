param()

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$preflight = Join-Path $PSScriptRoot 'preflight\HYP-VRAS-EURUSD-M5-002'
$task = Get-Content -LiteralPath (Join-Path $preflight 'task_packet.control.json') -Raw | ConvertFrom-Json
$receipt = Join-Path $preflight 'contract_receipt.control.json'
$receiptSha = (Get-FileHash -LiteralPath $receipt -Algorithm SHA256).Hash
$exitPath = Join-Path $repo '02. AlphaFactory\runtime\vras_model0.exitcode.txt'

try {
    & (Join-Path $repo '02. AlphaFactory\alpha.ps1') backtest 'EA_VRAS_RegimeAdaptiveScalperV2' `
        -Symbol $task.symbol -Period $task.period -From $task.from -To $task.to `
        -Model $task.model -ExecutionMode $task.execution_mode -FixedDelayMs $task.fixed_delay_ms `
        -Overrides $task.overrides -HypothesisId $task.hypothesis_id -RunRole $task.run_role `
        -TelemetryTier $task.telemetry_tier -Deposit $task.deposit -Leverage $task.leverage `
        -ContractReceipt $receipt -ContractReceiptSha256 $receiptSha `
        -RequiredSidecars ($task.required_sidecars -join ';') -TimeoutSec 3600
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
} catch {
    Write-Error $_
    $code = 1
}

[IO.File]::WriteAllText($exitPath, [string]$code + "`n", [Text.UTF8Encoding]::new($false))
exit $code
