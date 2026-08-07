param()

$ErrorActionPreference = 'Stop'
$repo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$eaRoot = Join-Path $repo '03. EA Developer\EA_JumpClusterDecayReversal'
$registryPath = Join-Path $repo '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$outDir = Join-Path $eaRoot 'research\preflight\HYP-JCDR-EURUSD-M5-003'
$outPath = Join-Path $outDir 'task_packet.control.json'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

# Materialize the path before taking git status so the untracked-file set is
# stable and the packet can bind its own pathname without self-reference.
if (-not (Test-Path -LiteralPath $outPath -PathType Leaf)) {
    [System.IO.File]::WriteAllText($outPath, '{}', [System.Text.UTF8Encoding]::new($false))
}

$rows = Get-Content -LiteralPath $registryPath
$latest = $rows[-1] | ConvertFrom-Json
if ([string]$latest.hypothesis_id -cne 'HYP-JCDR-EURUSD-M5-003' -or [string]$latest.state -cne 'screened') {
    throw 'Latest registry row is not the screened JCDR003 execution authority.'
}
$registryRowSha = Get-TextSha256 ([string]$rows[-1])

$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $gitCommit -notmatch '^[A-Fa-f0-9]{40,64}$') {
    throw 'Git commit is unavailable.'
}
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) { throw 'Git status is unavailable.' }
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))

$contractPath = Join-Path $eaRoot 'ALPHAFACTORY_EA_CONTRACT.json'
$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
$indicatorDependencies = @(
    foreach ($dependency in @($contract.indicator_dependencies)) {
        $sourceRelative = ([string]$dependency.source).Replace('\', '/')
        $sourceAbsolute = Join-Path $repo $sourceRelative
        [ordered]@{
            name = [string]$dependency.name
            source = $sourceRelative
            source_sha256 = Get-Sha256 $sourceAbsolute
            terminal_ex5 = [string]$dependency.terminal_ex5
        }
    }
)

$sourcePath = '03. EA Developer/EA_JumpClusterDecayReversal/EA_JumpClusterDecayReversal.mq5'
$preregPath = '03. EA Developer/EA_JumpClusterDecayReversal/research/HYP-JCDR-EURUSD-M5-003_INDICATOR_ROUTING_FEASIBILITY_PLAN.md'
$costPath = '03. EA Developer/EA_JumpClusterDecayReversal/research/HYP-JCDR-EURUSD-M5-003_COLLECTION_ONLY_COST_SOURCE_MANIFEST.json'
$overrides = 'InpAnalysisFrom=2016.01.04;InpAnalysisTo=2020.12.31;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-JCDR-EURUSD-M5-003;InpResearchAutoMode=true;InpVariantTag=JCDR_ROUTER_FEASIBILITY_V1'

$packet = [ordered]@{
    schema_version = 'alphafactory_research_task_packet.v1'
    authority = 'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE'
    hypothesis_id = 'HYP-JCDR-EURUSD-M5-003'
    run_role = 'control'
    ea_name = 'EA_JumpClusterDecayReversal'
    source_path = $sourcePath
    source_sha256 = Get-Sha256 (Join-Path $repo $sourcePath)
    registry_path = '04. Memory/research/CANDIDATE_REGISTRY.jsonl'
    registry_sha256 = Get-Sha256 $registryPath
    registry_row_sha256 = $registryRowSha
    prereg_path = $preregPath
    prereg_sha256 = Get-Sha256 (Join-Path $repo $preregPath)
    ea_contract_path = '03. EA Developer/EA_JumpClusterDecayReversal/ALPHAFACTORY_EA_CONTRACT.json'
    ea_contract_sha256 = Get-Sha256 $contractPath
    telemetry_profile = 'none'
    comparison_adapter = 'generic-control-improvement-v1'
    indicator_dependencies = $indicatorDependencies
    symbol = 'EURUSD'
    period = 'M5'
    from = '1970.01.01'
    to = '2026.07.30'
    data_quality_contract = [ordered]@{
        history_quality = [ordered]@{ operator = 'gt'; value = 97.0 }
        coverage_mode = 'all_available_asof'
        availability_asof_utc = '2026-07-30T23:59:59Z'
        requested_from = '1970.01.01'
        requested_to = '2026.07.30'
        require_tester_journal_bounds = $true
    }
    model = 0
    execution_mode = 0
    fixed_delay_ms = 0
    overrides = $overrides
    telemetry_tier = 'off'
    deposit = 10000
    leverage = 100
    spread = 'current'
    validation_stage = 'challenger'
    holding_contract = 'non_scalp'
    git_commit = $gitCommit
    git_status = $gitStatus
    git_status_sha256 = $gitStatusSha
    include_closure = @()
    include_closure_sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
    broker_fingerprint = 'E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54'
    server_fingerprint = '7AFEBB7D8511ECD0BA3A6BB20BE0A502372EC01001734019C6AFF45AE45152EE'
    account_fingerprint = '0635F9333630C605B51F8208861007B4267011E5F4D7C3C841309F04FE39BF02'
    data_fingerprint = 'E85CE106F0844EC51303163725BFCB5061CBBCEFE127919D405812B5A6BC6A55'
    symbol_geometry = [ordered]@{ digits = 5; point = 0.00001; pip_size = 0.0001 }
    required_sidecars = @()
    required_manifest_hashes = @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')
    cost_source_manifest_path = $costPath
    cost_source_manifest_sha256 = Get-Sha256 (Join-Path $repo $costPath)
    matched_control_run_id = ''
    matched_control_hypothesis_id = ''
    matched_control_manifest_sha256 = ''
    matched_control_report_sha256 = ''
    matched_control_overrides = ''
    matched_control_source_sha256 = ''
    matched_control_config_sha256 = ''
    matched_control_ex5_sha256 = ''
    matched_control_includes_sha256 = ''
    matched_control_git_commit = ''
    matched_control_git_status_sha256 = ''
    wfa_artifact_path = ''
    wfa_artifact_sha256 = ''
    variants_dir = ''
    variants_sha256 = ''
}

$json = $packet | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($outPath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Output $outPath
Write-Output (Get-Sha256 $outPath)
