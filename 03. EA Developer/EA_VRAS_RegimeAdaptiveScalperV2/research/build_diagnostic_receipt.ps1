param()

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package = Join-Path $repo '03. EA Developer\EA_VRAS_RegimeAdaptiveScalperV2'
$preflight = Join-Path $package 'research\preflight\HYP-VRAS-EURUSD-M5-002'
$taskPath = Join-Path $preflight 'task_packet.control.json'
$receiptPath = Join-Path $preflight 'contract_receipt.control.json'
$sourcePath = Join-Path $package 'EA_VRAS_RegimeAdaptiveScalperV2.mq5'
$includePath = Join-Path $package 'NewsCalendar2019_2022.mqh'
$preregPath = Join-Path $package 'research\HYP-VRAS-EURUSD-M5-002_FROZEN_PREREG.md'
$contractPath = Join-Path $package 'ALPHAFACTORY_EA_CONTRACT.json'
$registryPath = Join-Path $repo '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$costManifestPath = Join-Path $preflight 'cost_source_manifest.unverified.json'
$costEvidencePath = Join-Path $repo '02. AlphaFactory\data\fivepercent\EURUSD\cost_evidence\EURUSD_M1_SPREAD_2019_2022.csv'

function Get-TextSha256([string]$text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-FileSha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Write-Utf8Json($value, [string]$path) {
    $json = $value | ConvertTo-Json -Depth 16
    [IO.File]::WriteAllText($path, $json + "`n", [Text.UTF8Encoding]::new($false))
}

# Both generated paths must already exist before this snapshot. Updating their
# content does not alter porcelain status, avoiding a provenance hash cycle.
foreach ($path in @($taskPath, $receiptPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Pre-create generated receipt path before running: $path"
    }
}

$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))
$registryLines = @(Get-Content -LiteralPath $registryPath)
$registryRow = @($registryLines | Where-Object { $_ -match '"hypothesis_id":"HYP-VRAS-EURUSD-M5-002"' } | Select-Object -Last 1)
if ($registryRow.Count -ne 1) { throw 'VRAS registry row is missing or ambiguous.' }

$overrides = @(
    'InpAdxEnter=25.0',
    'InpAdxExit=19.0',
    'InpAdxPeriod=14',
    'InpAnchorLookbackBars=60',
    'InpAnchorMode=0',
    'InpAtrPeriod=14',
    'InpBandMultiplier=2.0',
    'InpBrokerFollowsUS_DST=true',
    'InpBrokerGMTOffsetWinter=2',
    'InpCommissionPips=0.70',
    'InpCostDistanceMultiple=8.0',
    'InpDailyLossPct=1.50',
    'InpEnableTelemetry=true',
    'InpHypothesisId=HYP-VRAS-EURUSD-M5-002',
    'InpMagic=5600742',
    'InpMaxAccountDrawdownPct=6.00',
    'InpMaxHoldBars=20',
    'InpMaxSpreadPips=1.20',
    'InpMaxTradesPerDay=3',
    'InpMinRegimeDwellBars=6',
    'InpNewsBlackoutMinutes=45',
    'InpRangeStopAtr=0.30',
    'InpRangeStopSd=2.50',
    'InpRequireNewsGuard=true',
    'InpResearchAutoMode=true',
    'InpRiskPercent=0.25',
    'InpRsiLongFloor=25.0',
    'InpRsiPeriod=14',
    'InpRsiShortCeiling=75.0',
    'InpSdFloorAtr=0.30',
    'InpSlippageOneWayPips=0.40',
    'InpTrendStopAtr=0.40',
    'InpTrendTargetR=1.80',
    'InpUseM15Bias=true',
    'InpVariantTag=PRIMARY_TICK_LONDON',
    'InpVolumeMode=0',
    'InpWarmupBars=15'
) -join ';'

$task = [ordered]@{
    schema_version = 'alphafactory_diagnostic_task_packet.v1'
    hypothesis_id = 'HYP-VRAS-EURUSD-M5-002'
    run_role = 'control'
    purpose = 'Owner-authorized build-first Model-0 mechanism diagnostic; not promotion evidence'
    ea_name = 'EA_VRAS_RegimeAdaptiveScalperV2'
    source_path = '03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV2/EA_VRAS_RegimeAdaptiveScalperV2.mq5'
    source_sha256 = Get-FileSha256 $sourcePath
    registry_path = '04. Memory/research/CANDIDATE_REGISTRY.jsonl'
    registry_sha256 = Get-FileSha256 $registryPath
    registry_row_sha256 = Get-TextSha256 ([string]$registryRow[0])
    prereg_path = '03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV2/research/HYP-VRAS-EURUSD-M5-002_FROZEN_PREREG.md'
    prereg_sha256 = Get-FileSha256 $preregPath
    ea_contract_path = '03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV2/ALPHAFACTORY_EA_CONTRACT.json'
    ea_contract_sha256 = Get-FileSha256 $contractPath
    symbol = 'EURUSD'
    period = 'M5'
    from = '2019.01.03'
    to = '2022.12.31'
    model = 0
    execution_mode = 0
    fixed_delay_ms = 0
    overrides = $overrides
    telemetry_tier = 'trade-only'
    telemetry_profile = 'lifecycle-v3'
    required_sidecars = @('*_LifecycleTrades_*.csv', '*_RunMeta_*.json')
    deposit = 100000
    leverage = 100
    spread = 'current'
    cost_status = 'UNVERIFIED_DIAGNOSTIC_ONLY'
    news_guard = 'THIRD_PARTY_DIAGNOSTIC_ONLY'
    promotion_eligible = $false
    git_commit = $gitCommit
    git_status = $gitStatus
    git_status_sha256 = $gitStatusSha
}
Write-Utf8Json $task $taskPath

$includeRecord = $includePath.ToLowerInvariant() + "`t" + (Get-FileSha256 $includePath)
$includeClosureSha = Get-TextSha256 $includeRecord
$evidence = @(
    [ordered]@{ label = 'task_packet'; kind = 'file'; path = $taskPath; sha256 = Get-FileSha256 $taskPath },
    [ordered]@{ label = 'candidate_registry'; kind = 'file'; path = $registryPath; sha256 = Get-FileSha256 $registryPath },
    [ordered]@{ label = 'source'; kind = 'file'; path = $sourcePath; sha256 = Get-FileSha256 $sourcePath },
    [ordered]@{ label = 'ea_capability_contract'; kind = 'file'; path = $contractPath; sha256 = Get-FileSha256 $contractPath },
    [ordered]@{ label = 'include_0000'; kind = 'file'; path = $includePath; sha256 = Get-FileSha256 $includePath },
    [ordered]@{ label = 'prereg'; kind = 'file'; path = $preregPath; sha256 = Get-FileSha256 $preregPath },
    [ordered]@{ label = 'cost_source_manifest'; kind = 'file'; path = $costManifestPath; sha256 = Get-FileSha256 $costManifestPath },
    [ordered]@{ label = 'cost_evidence_0000'; kind = 'file'; path = $costEvidencePath; sha256 = Get-FileSha256 $costEvidencePath; provenance_label = 'historical_spread_with_known_zero_rows' }
)
$receipt = [ordered]@{
    schema_version = 'alphafactory_execution_receipt.v1'
    hypothesis_id = 'HYP-VRAS-EURUSD-M5-002'
    registry_row_sha256 = Get-TextSha256 ([string]$registryRow[0])
    task_packet_sha256 = Get-FileSha256 $taskPath
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
    binding = [ordered]@{
        hypothesis_id = 'HYP-VRAS-EURUSD-M5-002'
        run_role = 'control'
        ea_name = 'EA_VRAS_RegimeAdaptiveScalperV2'
        symbol = 'EURUSD'
        period = 'M5'
        from = '2019.01.03'
        to = '2022.12.31'
        model = 0
        execution_mode = 0
        fixed_delay_ms = 0
        overrides = $overrides
        telemetry_tier = 'trade-only'
        telemetry_profile = 'lifecycle-v3'
        deposit = 100000
        leverage = 100
        spread = 'current'
        required_sidecars = @('*_LifecycleTrades_*.csv', '*_RunMeta_*.json')
        broker_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
        server_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
        account_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
        data_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
        symbol_geometry = [ordered]@{ digits = 5; point = 0.00001; pip_size = 0.0001 }
        include_closure_sha256 = $includeClosureSha
    }
    evidence = $evidence
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
}
Write-Utf8Json $receipt $receiptPath

[ordered]@{
    task_packet = $taskPath
    task_sha256 = Get-FileSha256 $taskPath
    receipt = $receiptPath
    receipt_sha256 = Get-FileSha256 $receiptPath
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
    overrides = $overrides
} | ConvertTo-Json -Depth 4
