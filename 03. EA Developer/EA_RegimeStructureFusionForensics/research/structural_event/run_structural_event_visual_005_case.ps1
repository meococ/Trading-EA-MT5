param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('C01','C02','C03','C04','C05','C06','C07','C08')]
    [string]$Case
)

$ErrorActionPreference = 'Stop'
$hypothesisId = "HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-VISUAL-005-$Case"
$caseNames = @{
    C01 = 'BREAKOUT_LONG_LOSS'
    C02 = 'BREAKOUT_LONG_WIN'
    C03 = 'BREAKOUT_SHORT_LOSS'
    C04 = 'BREAKOUT_SHORT_WIN'
    C05 = 'TREND_LONG_LOSS'
    C06 = 'TREND_LONG_WIN'
    C07 = 'TREND_SHORT_LOSS'
    C08 = 'TREND_SHORT_WIN'
}

$repoRoot = $PSScriptRoot
for ($i = 0; $i -lt 4; $i++) { $repoRoot = Split-Path -Parent $repoRoot }

$packetPath = Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$receiptPath = Join-Path $PSScriptRoot "$hypothesisId`_CONTRACT_RECEIPT.json"
$receiptBuilder = Join-Path $PSScriptRoot 'build_structural_event_visual_005_case_receipt.ps1'
$chartDir = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusionForensics\research\visual\native_structural_event_005'
$alpha = Join-Path $repoRoot '02. AlphaFactory\alpha.ps1'

& $receiptBuilder -Case $Case
$packet = Get-Content -Raw -LiteralPath $packetPath | ConvertFrom-Json
$receiptSha = (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash
New-Item -ItemType Directory -Force -Path $chartDir | Out-Null
$chartPath = Join-Path $chartDir ("NATIVE_MT5_SE005_{0}_{1}.png" -f $Case, $caseNames[$Case])
Remove-Item -LiteralPath $chartPath -Force -ErrorAction SilentlyContinue
$spreadArg = if ([string]$packet.spread -eq 'current') { '' } else { [string]$packet.spread }

& $alpha backtest `
    -Name $packet.ea_name `
    -Symbol $packet.symbol `
    -Period $packet.period `
    -From $packet.from `
    -To $packet.to `
    -Model $packet.model `
    -ExecutionMode $packet.execution_mode `
    -FixedDelayMs $packet.fixed_delay_ms `
    -Spread $spreadArg `
    -HypothesisId $packet.hypothesis_id `
    -RunRole $packet.run_role `
    -TelemetryTier $packet.telemetry_tier `
    -Deposit $packet.deposit `
    -Leverage $packet.leverage `
    -Overrides $packet.overrides `
    -ContractReceipt $receiptPath `
    -ContractReceiptSha256 $receiptSha `
    -RequiredSidecars ([string]::Join(';', @($packet.required_sidecars))) `
    -Visual `
    -NativeChartEvidence $chartPath `
    -TimeoutSec 300

if ($LASTEXITCODE -ne 0) {
    throw "AlphaFactory visual case $Case failed with exit code $LASTEXITCODE."
}
