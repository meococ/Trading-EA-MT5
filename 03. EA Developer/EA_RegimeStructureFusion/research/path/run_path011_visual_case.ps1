param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('C01','C03','C05','C07')]
    [string]$Case
)

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$alpha = Join-Path $repoRoot '02. AlphaFactory\alpha.ps1'
$forensicSource = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusionForensics\EA_RegimeStructureFusionForensics.mq5'
$parentSource = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$forensicContract = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusionForensics\ALPHAFACTORY_EA_CONTRACT.json'
$pathPrereg = Join-Path $PSScriptRoot 'HYP-RSF-EURUSD-M5-PATH-011_FROZEN_PREREG.md'
$pathAudit = Join-Path $PSScriptRoot 'HYP-RSF-EURUSD-M5-PATH-011_NONREPAINT_AUDIT.json'
$costManifest = Join-Path $PSScriptRoot 'HYP-RSF-EURUSD-M5-PATH-011_COST_SOURCE_MANIFEST.json'
$registryPath = Join-Path $repoRoot '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$chartDir = Join-Path $PSScriptRoot 'visual'

$cases = @{
    C01 = [ordered]@{ Index=1; From='2019.04.27'; To='2019.05.09'; Magic=5867511; Label='BREAKOUT_LONG_LOSS' }
    C03 = [ordered]@{ Index=3; From='2017.12.25'; To='2018.01.06'; Magic=5867513; Label='BREAKOUT_SHORT_LOSS' }
    C05 = [ordered]@{ Index=5; From='2018.07.16'; To='2018.07.28'; Magic=5867515; Label='TREND_LONG_LOSS' }
    C07 = [ordered]@{ Index=7; From='2019.09.14'; To='2019.09.26'; Magic=5867517; Label='TREND_SHORT_LOSS' }
}
$c = $cases[$Case]
$hypothesisId = "HYP-RSF-EURUSD-M5-PATH-011-VISUAL-$Case"
$packetPath = Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$receiptPath = Join-Path $PSScriptRoot "$hypothesisId`_CONTRACT_RECEIPT.json"
$chartPath = Join-Path $chartDir ("NATIVE_MT5_PATH011_{0}_{1}.png" -f $Case,$c.Label)
New-Item -ItemType Directory -Force -Path $chartDir | Out-Null
Remove-Item -LiteralPath $chartPath -Force -ErrorAction SilentlyContinue
if(-not (Test-Path -LiteralPath $receiptPath)){
    [System.IO.File]::WriteAllText($receiptPath,"{}`n",[System.Text.UTF8Encoding]::new($false))
}

function Write-Utf8Json($Value,[string]$Path,[int]$Depth=20) {
    [System.IO.File]::WriteAllText($Path,(ConvertTo-Json $Value -Depth $Depth)+"`n",[System.Text.UTF8Encoding]::new($false))
}
function Get-TextSha256([string]$Text) {
    $sha=[System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.UTF8Encoding]::new($false).GetBytes($Text)))).Replace('-','') }
    finally { $sha.Dispose() }
}
function Get-Evidence([string]$Label,[string]$Path) {
    if(-not (Test-Path -LiteralPath $Path -PathType Leaf)){ throw "Missing evidence ${Label}: $Path" }
    [ordered]@{label=$Label;kind='file';path=[IO.Path]::GetFullPath($Path);sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
}

$dependencyNames = @(
    'AI_Regime_Detection',
    'Modern_Bollinger_Bands_GBB',
    'QQE_MOD',
    'TB_Smart_Money_Concept_2026',
    'Volatility_Regime_Classifier_QuantRegime'
)
$dependencies = @(
    foreach($name in $dependencyNames){
        $source = Join-Path $repoRoot "06.Indicator Alpha\$name.mq5"
        [ordered]@{
            name=$name
            source=("06.Indicator Alpha/$name.mq5")
            source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
            terminal_ex5=("AlphaFactory\$name.ex5")
        }
    }
)

$overrides = @(
    'InpAllowBreakoutMode=true','InpAllowRangeMode=false','InpAllowTrendMode=true',
    'InpEnableTelemetry=true','InpExpectedSymbol=EURUSD',
    'InpForensicAttachM5Indicators=true','InpForensicCaptureWindows=FROZEN_13_V1',
    'InpForensicCleanChart=false','InpForensicExternalCapturePauseMs=15000',
    "InpForensicNativeCaseIndex=$($c.Index)",
    'InpForensicNativeLossSchedule=FROZEN_STRUCTURAL_EVENT_004_OUTCOMES_V1',
    'InpForensicShotHeight=900','InpForensicShotSettleMs=1000',
    'InpForensicShotVerifyTicks=200','InpForensicShotWidth=1600',
    'InpForensicVisualScreenshots=true',"InpHypothesisId=$hypothesisId","InpMagic=$($c.Magic)",
    'InpManualModeMask=6','InpManualSessionMask=6','InpProfileMode=1',
    'InpResearchAutoMode=true','InpStructuralExpiryBars=8',
    'InpStructuralInvalidationAtr=0.20','InpStructuralMaxExtensionAtr=0.35',
    'InpStructuralMinObjectiveR=1.25','InpStructuralQqeVetoThreshold=3.0',
    'InpStructuralRequireLiveObjective=false','InpStructuralRetestToleranceAtr=0.15',
    'InpStructuralUseLiquidityPoolObjective=false','InpUseContextRouter=true',
    'InpUsePathManagement=true','InpPathBreakEvenTriggerR=1.0',
    'InpPathMinInvalidationBars=3','InpPathUseBasisQqeExit=true',
    'InpPathUseOppositeStructureExit=true','InpUseQqeTiming=true',
    'InpUseRoleAwareSequence=false','InpUseStructuralEventSequence=true',
    'InpUseTbStructure=true','InpUseTemporalSequence=false',
    "InpVariantTag=PATH011_VISUAL_$($Case)_$($c.Label)"
) -join ';'
# AlphaFactory canonicalizes every override by input name and enforces the
# receipt against that effective string, not the caller's presentation order.
$overrideMap = @{}
foreach($item in $overrides -split ';'){
    $parts=$item.Split('=',2)
    $overrideMap[$parts[0].Trim()]=$parts[1].Trim()
}
$overrideMap['InpEnableTelemetry']='true'
$overrides=[string]::Join(';',@($overrideMap.Keys | Sort-Object | ForEach-Object {"$_=$($overrideMap[$_])"}))
$requiredSidecars = @('*_LifecycleTrades_*.csv','*_RSFForensic_*.csv','*_RunMeta_*.json','*_VisualShots_*.csv','*_PathActions_*.csv') | Sort-Object

$packet = [ordered]@{
    schema_version='alphafactory_research_task_packet.v1'; hypothesis_id=$hypothesisId; run_role='control'
    purpose="Native MT5 Visual Tester replay of PATH-011 on frozen failed case $Case $($c.Label); engineering diagnosis only."
    ea_name='EA_RegimeStructureFusionForensics'; symbol='EURUSD'; period='M5'
    from=$c.From; to=$c.To; model=1; execution_mode=0; fixed_delay_ms=0
    overrides=$overrides; telemetry_tier='trade-only'; telemetry_profile='lifecycle-v3'
    deposit=100000; leverage=100; spread='current'; visual_mode=$true
    required_sidecars=$requiredSidecars; indicator_dependencies=$dependencies
    source_sha256=(Get-FileHash -LiteralPath $parentSource -Algorithm SHA256).Hash
    economic_claims_authorized=$false; promotion_eligible=$false
}
Write-Utf8Json $packet $packetPath

$evidence = @(
    Get-Evidence 'task_packet' $packetPath
    Get-Evidence 'candidate_registry' $registryPath
    Get-Evidence 'source' $forensicSource
    Get-Evidence 'include_parent_ea' $parentSource
    Get-Evidence 'ea_capability_contract' $forensicContract
    Get-Evidence 'prereg' $pathPrereg
    Get-Evidence 'cost_source_manifest' $costManifest
    Get-Evidence 'nonrepaint_audit' $pathAudit
)
foreach($dependency in $dependencies){
    $evidence += Get-Evidence ("indicator_{0}_source" -f $dependency.name.ToLowerInvariant()) (Join-Path $repoRoot $dependency.source)
}
$includeRecords = @($evidence | Where-Object {$_.label -like 'include_*'} | Sort-Object path | ForEach-Object {
    ([IO.Path]::GetFullPath([string]$_.path).ToLowerInvariant())+"`t"+([string]$_.sha256).ToUpperInvariant()
})
$includeClosure = Get-TextSha256 ([string]::Join("`n",$includeRecords))
$gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repoRoot status --short --untracked-files=all | ForEach-Object {[string]$_})
$gitStatusSha = Get-TextSha256 ([string]::Join("`n",$gitStatus))
$binding = [ordered]@{
    hypothesis_id=$hypothesisId;run_role='control';ea_name='EA_RegimeStructureFusionForensics'
    symbol='EURUSD';period='M5';from=$c.From;to=$c.To;model=1;execution_mode=0;fixed_delay_ms=0
    overrides=$overrides;telemetry_tier='trade-only';telemetry_profile='lifecycle-v3'
    deposit=100000;leverage=100;spread='current';visual_mode=$true
    required_sidecars=$requiredSidecars;indicator_dependencies=$dependencies
    symbol_geometry=[ordered]@{digits=5;point=0.00001;pip_size=0.0001};include_closure_sha256=$includeClosure
}
$receipt = [ordered]@{
    schema_version='alphafactory_execution_receipt.v1';hypothesis_id=$hypothesisId
    task_packet_sha256=(Get-FileHash -LiteralPath $packetPath -Algorithm SHA256).Hash
    git_commit=$gitCommit;git_status_sha256=$gitStatusSha;binding=$binding;evidence=$evidence
    generated_at_utc=[datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    note='Native MT5 visual engineering replay only; no economic, optimization, OOS, promotion or live authority.'
}
Write-Utf8Json $receipt $receiptPath 24

$receiptSha=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash
& $alpha backtest -Name $packet.ea_name -Symbol $packet.symbol -Period $packet.period `
    -From $packet.from -To $packet.to -Model $packet.model -ExecutionMode $packet.execution_mode `
    -FixedDelayMs $packet.fixed_delay_ms -HypothesisId $packet.hypothesis_id -RunRole $packet.run_role `
    -TelemetryTier $packet.telemetry_tier -Deposit $packet.deposit -Leverage $packet.leverage `
    -Overrides $packet.overrides -ContractReceipt $receiptPath -ContractReceiptSha256 $receiptSha `
    -RequiredSidecars ([string]::Join(';',$packet.required_sidecars)) -Visual `
    -NativeChartEvidence $chartPath -TimeoutSec 300
if($LASTEXITCODE -ne 0){ throw "PATH-011 visual case $Case failed with exit code $LASTEXITCODE" }
Write-Output "PATH011_VISUAL_OK case=$Case chart=$chartPath"
