param()

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$hypothesisId = 'HYP-RSF-EURUSD-M5-PATH-011'
$registryPath = Join-Path $repoRoot '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$sourcePath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$contractPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\ALPHAFACTORY_EA_CONTRACT.json'
$preregPath = Join-Path $PSScriptRoot "$hypothesisId`_FROZEN_PREREG.md"
$auditPath = Join-Path $PSScriptRoot "$hypothesisId`_NONREPAINT_AUDIT.json"
$costPath = Join-Path $PSScriptRoot "$hypothesisId`_COST_SOURCE_MANIFEST.json"
$packetPath = Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$receiptPath = Join-Path $PSScriptRoot "$hypothesisId`_CONTRACT_RECEIPT.json"
$parentCostPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\research\structural_event\HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-004_COST_SOURCE_MANIFEST.json'
$identityPath = Join-Path $repoRoot '02. AlphaFactory\runs\EA_RegimeStructureFusion\20260807_080936\run_manifest.json'
$independentReviewPath = Join-Path $PSScriptRoot "$hypothesisId`_CODE_REVIEW.json"
$overrides = 'InpAllowBreakoutMode=true;InpAllowRangeMode=false;InpAllowTrendMode=true;InpEnableTelemetry=true;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-RSF-EURUSD-M5-PATH-011;InpMagic=5867431;InpManualModeMask=6;InpManualSessionMask=6;InpPathBreakEvenTriggerR=1.0;InpPathMinInvalidationBars=3;InpPathUseBasisQqeExit=true;InpPathUseOppositeStructureExit=true;InpProfileMode=1;InpResearchAutoMode=true;InpStructuralExpiryBars=8;InpStructuralInvalidationAtr=0.20;InpStructuralMaxExtensionAtr=0.35;InpStructuralMinObjectiveR=1.25;InpStructuralQqeVetoThreshold=3.0;InpStructuralRequireLiveObjective=false;InpStructuralRetestToleranceAtr=0.15;InpStructuralUseLiquidityPoolObjective=false;InpUseContextRouter=true;InpUsePathManagement=true;InpUseQqeTiming=true;InpUseRoleAwareSequence=false;InpUseStructuralEventSequence=true;InpUseTbStructure=true;InpUseTemporalSequence=false;InpVariantTag=PATH_MANAGEMENT_V1'

function Write-Utf8Json($value, [string]$path, [int]$depth = 16) {
    $json = $value | ConvertTo-Json -Depth $depth
    [System.IO.File]::WriteAllText($path, $json + "`n", [System.Text.UTF8Encoding]::new($false))
}

function Get-TextSha256([string]$text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.UTF8Encoding]::new($false).GetBytes($text)))).Replace('-', '') }
    finally { $sha.Dispose() }
}

function Get-Relative([string]$path) {
    return ([IO.Path]::GetFullPath($path)).Substring($repoRoot.Length).TrimStart('\', '/').Replace('\', '/')
}

function Get-Evidence([string]$label, [string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing evidence $label`: $path" }
    return [ordered]@{ label = $label; kind = 'file'; path = [IO.Path]::GetFullPath($path); sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
}

# Rebind the already verified same-symbol/window cost proxy; no cost parameter
# is inferred from PATH-011 outcomes.
$cost = Get-Content -Raw -LiteralPath $parentCostPath | ConvertFrom-Json
$cost.hypothesis_id = $hypothesisId
$cost | Add-Member -NotePropertyName parent_cost_manifest -NotePropertyValue (Get-Relative $parentCostPath) -Force
$cost | Add-Member -NotePropertyName parent_cost_manifest_sha256 -NotePropertyValue ((Get-FileHash -LiteralPath $parentCostPath -Algorithm SHA256).Hash) -Force
Write-Utf8Json $cost $costPath 20

$registryRaw = $null
foreach ($line in [IO.File]::ReadAllLines($registryPath, [Text.UTF8Encoding]::new($false))) {
    if ($line -match ('"hypothesis_id"\s*:\s*"' + [regex]::Escape($hypothesisId) + '"')) { $registryRaw = $line }
}
if ([string]::IsNullOrWhiteSpace($registryRaw)) { throw "Registry row missing for $hypothesisId" }
$registry = $registryRaw | ConvertFrom-Json
if ([string]$registry.state -cne 'screened') { throw "PATH-011 must be screened before receipt generation" }

$eaContract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json
$identity = Get-Content -Raw -LiteralPath $identityPath | ConvertFrom-Json
$dependencies = @(
    foreach ($dependency in @($eaContract.indicator_dependencies)) {
        $dependencyPath = Join-Path $repoRoot (([string]$dependency.source).Replace('/', '\'))
        [ordered]@{
            name = [string]$dependency.name
            source = ([string]$dependency.source).Replace('\', '/')
            source_sha256 = (Get-FileHash -LiteralPath $dependencyPath -Algorithm SHA256).Hash
            terminal_ex5 = [string]$dependency.terminal_ex5
        }
    }
)
$requiredSidecars = @('*_LifecycleTrades_*.csv', '*_RunMeta_*.json', '*_EntryContext_*.csv', '*_PathActions_*.csv')

# Make both generated paths visible to git identity before freezing the status.
if (-not (Test-Path -LiteralPath $packetPath)) { [IO.File]::WriteAllText($packetPath, "{}`n", [Text.UTF8Encoding]::new($false)) }
if (-not (Test-Path -LiteralPath $receiptPath)) { [IO.File]::WriteAllText($receiptPath, "{}`n", [Text.UTF8Encoding]::new($false)) }

$packet = [ordered]@{
    schema_version = 'alphafactory_research_task_packet.v1'
    hypothesis_id = $hypothesisId
    run_role = 'control'
    purpose = 'One frozen EURUSD M5 development falsification of closed-bar post-entry path management while preserving Structural-Event-004 entries; no optimization or holdout access.'
    ea_name = 'EA_RegimeStructureFusion'
    source_path = Get-Relative $sourcePath
    source_sha256 = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    registry_path = Get-Relative $registryPath
    registry_sha256 = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash
    registry_row_sha256 = Get-TextSha256 $registryRaw
    prereg_path = Get-Relative $preregPath
    prereg_sha256 = (Get-FileHash -LiteralPath $preregPath -Algorithm SHA256).Hash
    symbol = 'EURUSD'; period = 'M5'; from = '2018.01.01'; to = '2022.12.31'
    model = 0; execution_mode = 0; fixed_delay_ms = 0
    overrides = $overrides
    telemetry_tier = 'trade-only'; telemetry_profile = 'lifecycle-v3'
    comparison_adapter = 'generic-control-improvement-v1'
    acceptance_contract = [ordered]@{
        min_profit_factor = 1.30; min_trades_per_week = 2.0; max_trades_per_week = 5
        max_drawdown_pct = 8; min_cost_pf_x1_5 = 1.25; min_cost_pf_x2 = 1.0; max_monte_carlo_p95_dd_pct = 8
    }
    ea_contract_path = Get-Relative $contractPath
    ea_contract_sha256 = (Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash
    indicator_dependencies = @($dependencies)
    required_sidecars = @($requiredSidecars)
    deposit = 100000; leverage = 100; spread = 'current'
    validation_stage = 'challenger'; holding_contract = 'scalp'; cost_evidence_tier = 'research_proxy'
    cost_source_manifest_path = Get-Relative $costPath
    cost_source_manifest_sha256 = (Get-FileHash -LiteralPath $costPath -Algorithm SHA256).Hash
    include_closure = @(); include_closure_sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
    broker_fingerprint = [string]$identity.broker_fingerprint
    server_fingerprint = [string]$identity.server_fingerprint
    account_fingerprint = [string]$identity.account_fingerprint
    data_fingerprint = [string]$identity.data_fingerprint
    symbol_geometry = [ordered]@{ digits = 5; point = 0.00001; pip_size = 0.0001 }
    required_manifest_hashes = @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')
    economic_claims_authorized = $false; promotion_eligible = $false
}
Write-Utf8Json $packet $packetPath 20

$gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repoRoot status --short --untracked-files=all | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))

$evidence = @(
    Get-Evidence 'task_packet' $packetPath
    Get-Evidence 'candidate_registry' $registryPath
    Get-Evidence 'source' $sourcePath
    Get-Evidence 'ea_capability_contract' $contractPath
    Get-Evidence 'prereg' $preregPath
    Get-Evidence 'cost_source_manifest' $costPath
    Get-Evidence 'nonrepaint_audit' $auditPath
    Get-Evidence 'independent_review' $independentReviewPath
)
foreach ($dependency in @($dependencies)) {
    $dependencyPath = Join-Path $repoRoot (([string]$dependency.source).Replace('/', '\'))
    $evidence += Get-Evidence ("indicator_{0}_source" -f ([string]$dependency.name).ToLowerInvariant()) $dependencyPath
}

$binding = [ordered]@{
    hypothesis_id = $hypothesisId; run_role = 'control'; ea_name = 'EA_RegimeStructureFusion'
    symbol = 'EURUSD'; period = 'M5'; from = '2018.01.01'; to = '2022.12.31'
    model = 0; execution_mode = 0; fixed_delay_ms = 0; overrides = $overrides
    telemetry_tier = 'trade-only'; telemetry_profile = 'lifecycle-v3'
    deposit = 100000; leverage = 100; spread = 'current'; visual_mode = $false
    required_sidecars = @($requiredSidecars); indicator_dependencies = @($dependencies)
    symbol_geometry = [ordered]@{ digits = 5; point = 0.00001; pip_size = 0.0001 }
    include_closure_sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
}
$receipt = [ordered]@{
    schema_version = 'alphafactory_execution_receipt.v1'; hypothesis_id = $hypothesisId
    task_packet_sha256 = (Get-FileHash -LiteralPath $packetPath -Algorithm SHA256).Hash
    git_commit = $gitCommit; git_status_sha256 = $gitStatusSha; binding = $binding; evidence = $evidence
    generated_at_utc = [datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    note = 'Exactly one frozen Model0 development path-management test. No optimization, OOS, promotion or live authority.'
}
Write-Utf8Json $receipt $receiptPath 24
Write-Output ("PATH011_CONTRACT_OK packet={0} receipt={1} receipt_sha256={2}" -f $packetPath, $receiptPath, (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash)
