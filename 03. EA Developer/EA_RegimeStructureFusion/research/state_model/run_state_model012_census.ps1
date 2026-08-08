param(
  [int]$TimeoutSec=1800,
  [string]$HypothesisId='HYP-RSF-EURUSD-M5-STATE-MODEL-012',
  [string]$Symbol='EURUSD',
  [int]$Magic=5867442,
  [int]$Digits=5,
  [double]$Point=0.00001,
  [double]$PipSize=0.0001,
  [string]$EaName='EA_RegimeStructureFusionStateCensus',
  [string]$Period='M5',
  [string]$VariantTag='STATE_CENSUS_DISCOVERY_V1',
  [string]$SourceRelativePath='03. EA Developer\EA_RegimeStructureFusionStateCensus\EA_RegimeStructureFusionStateCensus.mq5',
  [string]$ContractRelativePath='03. EA Developer\EA_RegimeStructureFusionStateCensus\ALPHAFACTORY_EA_CONTRACT.json',
  [string]$AuditRelativePath='03. EA Developer\EA_RegimeStructureFusion\research\state_model\HYP-RSF-EURUSD-M5-STATE-MODEL-012_NONREPAINT_AUDIT.json',
  [string]$TestRelativePath='03. EA Developer\EA_RegimeStructureFusion\research\state_model\tests\test_state_model012_census_contract.py',
  [string]$PreregRelativePath='03. EA Developer\EA_RegimeStructureFusionStateCensus\research\HYP-RSF-EURUSD-M5-STATE-MODEL-012_FROZEN_PREREG.md',
  [string]$CostRelativePath='03. EA Developer\EA_RegimeStructureFusion\research\state_model\HYP-RSF-EURUSD-M5-STATE-MODEL-012_COLLECTION_ONLY_COST_SOURCE_MANIFEST.json'
)

$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$alpha=Join-Path $repoRoot '02. AlphaFactory\alpha.ps1'
$builder=Join-Path $PSScriptRoot 'build_state_model012_contract.ps1'
$packetPath=Join-Path $PSScriptRoot "$HypothesisId`_TASK_PACKET.json"
$receiptPath=Join-Path $PSScriptRoot "$HypothesisId`_CONTRACT_RECEIPT.json"

& $builder -HypothesisId $HypothesisId -Symbol $Symbol -Magic $Magic -Digits $Digits -Point $Point -PipSize $PipSize `
  -EaName $EaName -Period $Period -VariantTag $VariantTag -SourceRelativePath $SourceRelativePath `
  -ContractRelativePath $ContractRelativePath -AuditRelativePath $AuditRelativePath -TestRelativePath $TestRelativePath `
  -PreregRelativePath $PreregRelativePath -CostRelativePath $CostRelativePath
if($LASTEXITCODE -ne 0){throw 'Contract generation failed'}
$packet=Get-Content -Raw -LiteralPath $packetPath|ConvertFrom-Json
$receiptSha=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash
& $alpha backtest -Name $packet.ea_name -Symbol $packet.symbol -Period $packet.period `
  -From $packet.from -To $packet.to -Model $packet.model -ExecutionMode $packet.execution_mode `
  -FixedDelayMs $packet.fixed_delay_ms -HypothesisId $packet.hypothesis_id -RunRole $packet.run_role `
  -TelemetryTier $packet.telemetry_tier -Deposit $packet.deposit -Leverage $packet.leverage `
  -Overrides $packet.overrides -ContractReceipt $receiptPath -ContractReceiptSha256 $receiptSha `
  -RequiredSidecars ([string]::Join(';',$packet.required_sidecars)) -TimeoutSec $TimeoutSec
if($LASTEXITCODE -ne 0){throw "$HypothesisId census failed with exit code $LASTEXITCODE"}
