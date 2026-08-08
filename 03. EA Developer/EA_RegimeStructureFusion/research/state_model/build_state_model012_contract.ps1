param(
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
  [string]$CostRelativePath='03. EA Developer\EA_RegimeStructureFusion\research\state_model\HYP-RSF-EURUSD-M5-STATE-MODEL-012_COLLECTION_ONLY_COST_SOURCE_MANIFEST.json',
  [string]$IdentityRelativePath='02. AlphaFactory\runs\EA_RegimeStructureFusion\20260807_235223\run_manifest.json'
)

$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$hypothesisId=$HypothesisId
$eaName=$EaName
$sourcePath=Join-Path $repoRoot $SourceRelativePath
$basePath=Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$contractPath=Join-Path $repoRoot $ContractRelativePath
$registryPath=Join-Path $repoRoot '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$preregPath=Join-Path $repoRoot $PreregRelativePath
$auditPath=Join-Path $repoRoot $AuditRelativePath
$testPath=Join-Path $repoRoot $TestRelativePath
$costPath=Join-Path $repoRoot $CostRelativePath
$packetPath=Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$receiptPath=Join-Path $PSScriptRoot "$hypothesisId`_CONTRACT_RECEIPT.json"
$identityPath=Join-Path $repoRoot $IdentityRelativePath
$overrides=('InpAllowBreakoutMode=false;InpAllowRangeMode=false;InpAllowTrendMode=false;InpCensusFlushEveryRows=512;InpCensusFrom=2018.01.01 00:00;InpCensusTo=2022.12.31 23:59;InpEnableTelemetry=true;InpExpectedSymbol={0};InpHypothesisId={1};InpMagic={2};InpManualModeMask=7;InpManualSessionMask=63;InpProfileMode=1;InpResearchAutoMode=true;InpUsePathManagement=false;InpUseRoleAwareSequence=false;InpUseStructuralEventSequence=false;InpUseTemporalSequence=false;InpVariantTag={3}' -f $Symbol,$hypothesisId,$Magic,$VariantTag)

function Write-Utf8Json($value,[string]$path,[int]$depth=24){
  [IO.File]::WriteAllText($path,(($value|ConvertTo-Json -Depth $depth)+"`n"),[Text.UTF8Encoding]::new($false))
}
function Get-TextSha256([string]$text){
  $sha=[Security.Cryptography.SHA256]::Create()
  try{return ([BitConverter]::ToString($sha.ComputeHash([Text.UTF8Encoding]::new($false).GetBytes($text)))).Replace('-','')}
  finally{$sha.Dispose()}
}
function Get-Relative([string]$path){
  ([IO.Path]::GetFullPath($path)).Substring($repoRoot.Length).TrimStart('\','/').Replace('\','/')
}
function Get-Evidence([string]$label,[string]$path){
  if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "Missing evidence $label`: $path"}
  [ordered]@{label=$label;kind='file';path=[IO.Path]::GetFullPath($path);sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
}

$registryRaw=$null
foreach($line in [IO.File]::ReadAllLines($registryPath,[Text.UTF8Encoding]::new($false))){
  if($line -match ('"hypothesis_id"\s*:\s*"'+[regex]::Escape($hypothesisId)+'"')){$registryRaw=$line}
}
if([string]::IsNullOrWhiteSpace($registryRaw)){throw "Registry row missing for $hypothesisId"}
$registry=$registryRaw|ConvertFrom-Json
if([string]$registry.state -cne 'screened'){throw "$hypothesisId must be screened"}
if((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash -ine [string]$registry.source_hash){throw 'Source hash differs from screened registry row'}

$eaContract=Get-Content -Raw -LiteralPath $contractPath|ConvertFrom-Json
$identity=Get-Content -Raw -LiteralPath $identityPath|ConvertFrom-Json
$dependencies=@(foreach($d in @($eaContract.indicator_dependencies)){
  $p=Join-Path $repoRoot (([string]$d.source).Replace('/','\'))
  [ordered]@{name=[string]$d.name;source=([string]$d.source).Replace('\','/');source_sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash;terminal_ex5=[string]$d.terminal_ex5}
})
$includeEvidence=Get-Evidence 'include_0001' $basePath
$includeRecord=([IO.Path]::GetFullPath($basePath).ToLowerInvariant()+"`t"+$includeEvidence.sha256.ToUpperInvariant())
$includeClosureSha=Get-TextSha256 $includeRecord
$requiredSidecars=@('*_LifecycleTrades_*.csv','*_RunMeta_*.json','*_RSFStateCensus_*.csv')

if(-not(Test-Path -LiteralPath $packetPath)){[IO.File]::WriteAllText($packetPath,"{}`n",[Text.UTF8Encoding]::new($false))}
if(-not(Test-Path -LiteralPath $receiptPath)){[IO.File]::WriteAllText($receiptPath,"{}`n",[Text.UTF8Encoding]::new($false))}

$packet=[ordered]@{
  schema_version='alphafactory_research_task_packet.v1';hypothesis_id=$hypothesisId;run_role='control'
  purpose=("One zero-trade closed-bar census of all five RSF indicators on {0} {1} discovery data; no future labels or economics in MT5." -f $Symbol,$Period)
  ea_name=$eaName;source_path=Get-Relative $sourcePath;source_sha256=(Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
  registry_path=Get-Relative $registryPath;registry_sha256=(Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash;registry_row_sha256=Get-TextSha256 $registryRaw
  prereg_path=Get-Relative $preregPath;prereg_sha256=(Get-FileHash -LiteralPath $preregPath -Algorithm SHA256).Hash
  symbol=$Symbol;period=$Period;from='2018.01.01';to='2023.01.01';model=0;execution_mode=0;fixed_delay_ms=0
  overrides=$overrides;telemetry_tier='trade-only';telemetry_profile='lifecycle-v3';comparison_adapter='generic-control-improvement-v1'
  ea_contract_path=Get-Relative $contractPath;ea_contract_sha256=(Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash
  indicator_dependencies=@($dependencies);required_sidecars=@($requiredSidecars);deposit=100000;leverage=100;spread='current'
  validation_stage='discovery';holding_contract='none-zero-trade';cost_evidence_tier='collection_only_no_economics'
  cost_source_manifest_path=Get-Relative $costPath;cost_source_manifest_sha256=(Get-FileHash -LiteralPath $costPath -Algorithm SHA256).Hash
  include_closure=@([ordered]@{path=Get-Relative $basePath;sha256=$includeEvidence.sha256});include_closure_sha256=$includeClosureSha
  broker_fingerprint=[string]$identity.broker_fingerprint;server_fingerprint=[string]$identity.server_fingerprint
  account_fingerprint=[string]$identity.account_fingerprint;data_fingerprint=[string]$identity.data_fingerprint
  symbol_geometry=[ordered]@{digits=$Digits;point=$Point;pip_size=$PipSize}
  required_manifest_hashes=@('source_sha256','config_sha256','report_sha256','ex5_sha256','includes_sha256')
  economic_claims_authorized=$false;promotion_eligible=$false
}
Write-Utf8Json $packet $packetPath

$gitCommit=(& git -C $repoRoot rev-parse HEAD).Trim()
$gitStatus=@(& git -C $repoRoot status --short --untracked-files=all|ForEach-Object{[string]$_})
if($LASTEXITCODE -ne 0){throw 'git status failed'}
$gitStatusSha=Get-TextSha256([string]::Join("`n",$gitStatus))
$evidence=@(
  Get-Evidence 'task_packet' $packetPath
  Get-Evidence 'candidate_registry' $registryPath
  Get-Evidence 'source' $sourcePath
  Get-Evidence 'ea_capability_contract' $contractPath
  Get-Evidence 'prereg' $preregPath
  Get-Evidence 'cost_source_manifest' $costPath
  Get-Evidence 'nonrepaint_audit' $auditPath
  Get-Evidence 'focused_tests' $testPath
  $includeEvidence
)
foreach($d in @($dependencies)){
  $p=Join-Path $repoRoot (([string]$d.source).Replace('/','\'))
  $evidence+=Get-Evidence ("indicator_{0}_source" -f ([string]$d.name).ToLowerInvariant()) $p
}
$binding=[ordered]@{
  hypothesis_id=$hypothesisId;run_role='control';ea_name=$eaName;symbol=$Symbol;period=$Period;from='2018.01.01';to='2023.01.01'
  model=0;execution_mode=0;fixed_delay_ms=0;overrides=$overrides;telemetry_tier='trade-only';telemetry_profile='lifecycle-v3'
  deposit=100000;leverage=100;spread='current';visual_mode=$false;required_sidecars=@($requiredSidecars)
  indicator_dependencies=@($dependencies);symbol_geometry=[ordered]@{digits=$Digits;point=$Point;pip_size=$PipSize};include_closure_sha256=$includeClosureSha
}
$receipt=[ordered]@{
  schema_version='alphafactory_execution_receipt.v1';hypothesis_id=$hypothesisId;task_packet_sha256=(Get-FileHash -LiteralPath $packetPath -Algorithm SHA256).Hash
  git_commit=$gitCommit;git_status_sha256=$gitStatusSha;binding=$binding;evidence=$evidence;generated_at_utc=[datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
  note='Exactly one zero-trade Model-0 discovery census. No economics, validation, holdout, promotion, paper or live authority.'
}
Write-Utf8Json $receipt $receiptPath
Write-Output("STATE_CENSUS_CONTRACT_OK hypothesis_id=$hypothesisId receipt_sha256="+(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash)
