param()

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$hypothesisId = 'HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-006'
$registryPath = Join-Path $repoRoot '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$preregPath = Join-Path $PSScriptRoot "$hypothesisId`_FROZEN_PREREG.md"
$packetPath = Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$costPath = Join-Path $PSScriptRoot "$hypothesisId`_COST_SOURCE_MANIFEST.json"
$sourcePath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$eaContractPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\ALPHAFACTORY_EA_CONTRACT.json'
$identityManifestPath = Join-Path $repoRoot '02. AlphaFactory\runs\EA_RegimeStructureFusion\20260806_210021\run_manifest.json'

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-RelativePath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    return $full.Substring($repoRoot.Length).TrimStart('\', '/').Replace('\', '/')
}

$registryLines = [System.IO.File]::ReadAllLines($registryPath, [System.Text.UTF8Encoding]::new($false))
$latestRaw = $null
foreach ($line in $registryLines) {
    if ($line -match ('"hypothesis_id"\s*:\s*"' + [regex]::Escape($hypothesisId) + '"')) {
        $latestRaw = $line
    }
}
if ([string]::IsNullOrWhiteSpace($latestRaw)) {
    throw "Latest registry row not found for $hypothesisId"
}
$latest = $latestRaw | ConvertFrom-Json
if ([string]$latest.state -cne 'screened') {
    throw "Latest registry state must be screened, got '$($latest.state)'"
}

$gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repoRoot status --short --untracked-files=all | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) {
    throw 'git status failed'
}
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))
$identity = Get-Content -LiteralPath $identityManifestPath -Raw | ConvertFrom-Json
$eaContract = Get-Content -LiteralPath $eaContractPath -Raw | ConvertFrom-Json
$indicatorDependencies = @(
    foreach ($dependency in @($eaContract.indicator_dependencies)) {
        $dependencySource = Join-Path $repoRoot (([string]$dependency.source).Replace('/', '\'))
        [ordered]@{
            name = [string]$dependency.name
            source = ([string]$dependency.source).Replace('\', '/')
            source_sha256 = (Get-FileHash -LiteralPath $dependencySource -Algorithm SHA256).Hash
            terminal_ex5 = [string]$dependency.terminal_ex5
        }
    }
)

$packet = [ordered]@{
    schema_version = 'alphafactory_research_task_packet.v1'
    hypothesis_id = $hypothesisId
    run_role = 'control'
    purpose = 'Exactly one development-only Model0 falsification of the causal unconsumed swing-liquidity pool objective derived from the terminal HYP-005 data-contract failure; no tuning, route pruning, validation, or holdout access.'
    ea_name = 'EA_RegimeStructureFusion'
    source_path = Get-RelativePath $sourcePath
    source_sha256 = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    registry_path = Get-RelativePath $registryPath
    registry_sha256 = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash
    registry_row_sha256 = Get-TextSha256 $latestRaw
    prereg_path = Get-RelativePath $preregPath
    prereg_sha256 = (Get-FileHash -LiteralPath $preregPath -Algorithm SHA256).Hash
    symbol = 'EURUSD'
    period = 'M5'
    from = '2018.01.01'
    to = '2022.12.31'
    model = 0
    execution_mode = 0
    fixed_delay_ms = 0
    overrides = 'InpAllowBreakoutMode=true;InpAllowRangeMode=false;InpAllowTrendMode=true;InpEnableTelemetry=true;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-006;InpMagic=5867386;InpManualModeMask=6;InpManualSessionMask=6;InpProfileMode=1;InpResearchAutoMode=true;InpStructuralExpiryBars=8;InpStructuralInvalidationAtr=0.20;InpStructuralMaxExtensionAtr=0.35;InpStructuralMinObjectiveR=1.25;InpStructuralQqeVetoThreshold=3.0;InpStructuralRequireLiveObjective=true;InpStructuralRetestToleranceAtr=0.15;InpStructuralUseLiquidityPoolObjective=true;InpUseContextRouter=true;InpUseQqeTiming=true;InpUseRoleAwareSequence=false;InpUseStructuralEventSequence=true;InpUseTbStructure=true;InpUseTemporalSequence=false;InpVariantTag=LIQUIDITY_POOL_CAUSAL_V1'
    telemetry_tier = 'trade-only'
    telemetry_profile = 'lifecycle-v3'
    comparison_adapter = 'generic-control-improvement-v1'
    acceptance_contract = [ordered]@{
        min_profit_factor = 1.3
        min_trades_per_week = 2
        max_trades_per_week = 5
        max_drawdown_pct = 8
        min_cost_pf_x1_5 = 1.25
        min_cost_pf_x2 = 1
        max_monte_carlo_p95_dd_pct = 8
    }
    ea_contract_path = Get-RelativePath $eaContractPath
    ea_contract_sha256 = (Get-FileHash -LiteralPath $eaContractPath -Algorithm SHA256).Hash
    indicator_dependencies = @($indicatorDependencies)
    required_sidecars = @('*_LifecycleTrades_*.csv', '*_EntryContext_*.csv', '*_RunMeta_*.json')
    deposit = 100000
    leverage = 100
    spread = 'current'
    validation_stage = 'challenger'
    holding_contract = 'scalp'
    cost_evidence_tier = 'research_proxy'
    cost_source_manifest_path = Get-RelativePath $costPath
    cost_source_manifest_sha256 = (Get-FileHash -LiteralPath $costPath -Algorithm SHA256).Hash
    git_commit = $gitCommit
    git_status = $gitStatus
    git_status_sha256 = $gitStatusSha
    include_closure = @()
    include_closure_sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
    broker_fingerprint = [string]$identity.broker_fingerprint
    server_fingerprint = [string]$identity.server_fingerprint
    account_fingerprint = [string]$identity.account_fingerprint
    data_fingerprint = [string]$identity.data_fingerprint
    symbol_geometry = [ordered]@{
        digits = 5
        point = 0.00001
        pip_size = 0.0001
    }
    required_manifest_hashes = @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')
    economic_claims_authorized = $false
    promotion_eligible = $false
}

$json = $packet | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($packetPath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Output ("TASK_PACKET_OK path={0} sha256={1} registry_row_sha256={2} git_status_sha256={3}" -f `
    $packetPath,
    (Get-FileHash -LiteralPath $packetPath -Algorithm SHA256).Hash,
    $packet.registry_row_sha256,
    $packet.git_status_sha256)
