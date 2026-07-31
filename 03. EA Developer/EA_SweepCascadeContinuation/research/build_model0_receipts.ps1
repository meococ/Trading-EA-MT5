param(
    [ValidateSet('control', 'challenger')]
    [string]$Arm
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package = Join-Path $repo '03. EA Developer\EA_SweepCascadeContinuation'
$preflight = Join-Path $package 'research\preflight\HYP-SCC-MT5-REPLICATION-EURUSD-M5-004'
$sourcePath = Join-Path $package 'EA_SweepCascadeContinuation.mq5'
$binaryPath = Join-Path $package 'EA_SweepCascadeContinuation.ex5'
$preregPath = Join-Path $package 'research\HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_FROZEN_PREREG.md'
$matrixPath = Join-Path $package 'research\LOGIC_TO_CODE_MATRIX.md'
$contractPath = Join-Path $package 'ALPHAFACTORY_EA_CONTRACT.json'
$buildReceiptPath = Join-Path $package 'research\evidence\HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_BUILD\build_receipt.json'
$auditManifestPath = Join-Path $package 'research\evidence\HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_BUILD\nonrepaint_manifest.json'
$auditPath = Join-Path $package 'research\evidence\HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_BUILD\nonrepaint_audit.json'
$registryPath = Join-Path $repo '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$costManifestPath = Join-Path $preflight 'cost_source_manifest.unverified.json'

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

$registryRows = @(Get-Content -LiteralPath $registryPath | Where-Object {
    $_ -match '"hypothesis_id":"HYP-SCC-MT5-REPLICATION-EURUSD-M5-004"'
})
if ($registryRows.Count -lt 1) {
    throw 'SCC HYP-004 registry row is missing.'
}
$registryRow = [string]$registryRows[-1]
if ($registryRow -notmatch '"state":"screened"' -or
    $registryRow -notmatch '"model0_authorized":true') {
    throw 'Latest SCC HYP-004 registry row must be screened and Model-0 authorized.'
}

$variant = if ($Arm -eq 'control') {
    'CONTROL_FIRST_CLOSE_BREAK'
} else {
    'CHALLENGER_HOLD_RETEST'
}
$useHoldRetest = if ($Arm -eq 'control') { 'false' } else { 'true' }
$commonOverrides = @(
    'InpAtrPeriod=14',
    'InpBrokerFollowsEuropeDST=true',
    'InpBrokerGMTOffsetWinter=2',
    'InpDeviationPips=0.50',
    'InpEnableTelemetry=true',
    'InpHypothesisId=HYP-SCC-MT5-REPLICATION-EURUSD-M5-004',
    'InpMagic=5600754',
    'InpMaxHoldBars=24',
    'InpMaxSpreadPips=2.00',
    'InpPivotStrength=2',
    'InpResearchAutoMode=true',
    'InpRetestBars=12',
    'InpRiskPercent=0.01',
    'InpStopAtrBuffer=0.25',
    'InpTargetR=2.00',
    "InpUseHoldRetest=$useHoldRetest",
    "InpVariantTag=$variant"
)
$overrides = @($commonOverrides | Sort-Object { ($_ -split '=', 2)[0] }) -join ';'
$requiredSidecars = @(
    '*_LifecycleTrades_*.csv',
    '*_RunMeta_*.json',
    '*_DecisionTelemetry_*.csv'
)
$taskPath = Join-Path $preflight "task_packet.$Arm.json"
$receiptPath = Join-Path $preflight "contract_receipt.$Arm.json"
$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))

$task = [ordered]@{
    schema_version = 'alphafactory_diagnostic_task_packet.v1'
    hypothesis_id = 'HYP-SCC-MT5-REPLICATION-EURUSD-M5-004'
    run_role = $Arm
    purpose = 'Owner-directed SCC native MT5 micro-risk matched Model-0 diagnostic; parents remain parked'
    ea_name = 'EA_SweepCascadeContinuation'
    source_path = '03. EA Developer/EA_SweepCascadeContinuation/EA_SweepCascadeContinuation.mq5'
    source_sha256 = Get-FileSha256 $sourcePath
    registry_path = '04. Memory/research/CANDIDATE_REGISTRY.jsonl'
    registry_sha256 = Get-FileSha256 $registryPath
    registry_row_sha256 = Get-TextSha256 $registryRow
    prereg_path = '03. EA Developer/EA_SweepCascadeContinuation/research/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_FROZEN_PREREG.md'
    prereg_sha256 = Get-FileSha256 $preregPath
    ea_contract_path = '03. EA Developer/EA_SweepCascadeContinuation/ALPHAFACTORY_EA_CONTRACT.json'
    ea_contract_sha256 = Get-FileSha256 $contractPath
    symbol = 'EURUSD'
    period = 'M5'
    from = '2019.01.01'
    to = '2022.12.31'
    model = 0
    execution_mode = 0
    fixed_delay_ms = 0
    overrides = $overrides
    telemetry_tier = 'trade-only'
    telemetry_profile = 'lifecycle-v3'
    required_sidecars = $requiredSidecars
    deposit = 100000
    leverage = 100
    spread = 'current'
    cost_status = 'UNVERIFIED_DIAGNOSTIC_ONLY'
    news_guard = 'DISABLED_MATCHED'
    promotion_eligible = $false
    git_commit = $gitCommit
    git_status = $gitStatus
    git_status_sha256 = $gitStatusSha
}
Write-Utf8Json $task $taskPath

$emptyIncludeClosureSha = Get-TextSha256 ''
$evidence = @(
    [ordered]@{ label = 'task_packet'; kind = 'file'; path = $taskPath; sha256 = Get-FileSha256 $taskPath },
    [ordered]@{ label = 'candidate_registry'; kind = 'file'; path = $registryPath; sha256 = Get-FileSha256 $registryPath },
    [ordered]@{ label = 'source'; kind = 'file'; path = $sourcePath; sha256 = Get-FileSha256 $sourcePath },
    [ordered]@{ label = 'compiled_binary'; kind = 'file'; path = $binaryPath; sha256 = Get-FileSha256 $binaryPath },
    [ordered]@{ label = 'ea_capability_contract'; kind = 'file'; path = $contractPath; sha256 = Get-FileSha256 $contractPath },
    [ordered]@{ label = 'prereg'; kind = 'file'; path = $preregPath; sha256 = Get-FileSha256 $preregPath },
    [ordered]@{ label = 'logic_matrix'; kind = 'file'; path = $matrixPath; sha256 = Get-FileSha256 $matrixPath },
    [ordered]@{ label = 'build_receipt'; kind = 'file'; path = $buildReceiptPath; sha256 = Get-FileSha256 $buildReceiptPath },
    [ordered]@{ label = 'nonrepaint_manifest'; kind = 'file'; path = $auditManifestPath; sha256 = Get-FileSha256 $auditManifestPath },
    [ordered]@{ label = 'nonrepaint_audit'; kind = 'file'; path = $auditPath; sha256 = Get-FileSha256 $auditPath },
    [ordered]@{ label = 'cost_source_manifest'; kind = 'file'; path = $costManifestPath; sha256 = Get-FileSha256 $costManifestPath }
)

if ($Arm -eq 'challenger') {
    $control = $null
    $runRoot = Join-Path $repo '02. AlphaFactory\runs\EA_SweepCascadeContinuation'
    if (Test-Path -LiteralPath $runRoot -PathType Container) {
        foreach ($candidate in @(Get-ChildItem -LiteralPath $runRoot -Directory | Sort-Object LastWriteTime -Descending)) {
            $manifestPath = Join-Path $candidate.FullName 'run_manifest.json'
            $reportPath = Join-Path $candidate.FullName 'report.html'
            if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
                -not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
                continue
            }
            $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            if ([string]$manifest.hypothesis_id -ceq 'HYP-SCC-MT5-REPLICATION-EURUSD-M5-004' -and
                [string]$manifest.run_role -ceq 'control') {
                $control = [ordered]@{ manifest = $manifestPath; report = $reportPath }
                break
            }
        }
    }
    if ($null -eq $control) {
        throw 'A completed SCC HYP-004 control run is required before challenger receipt generation.'
    }
    $evidence += @(
        [ordered]@{ label = 'matched_control_manifest'; kind = 'file'; path = $control.manifest; sha256 = Get-FileSha256 $control.manifest },
        [ordered]@{ label = 'matched_control_report'; kind = 'file'; path = $control.report; sha256 = Get-FileSha256 $control.report }
    )
}

$receipt = [ordered]@{
    schema_version = 'alphafactory_execution_receipt.v1'
    hypothesis_id = 'HYP-SCC-MT5-REPLICATION-EURUSD-M5-004'
    registry_row_sha256 = Get-TextSha256 $registryRow
    task_packet_sha256 = Get-FileSha256 $taskPath
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
    binding = [ordered]@{
        hypothesis_id = 'HYP-SCC-MT5-REPLICATION-EURUSD-M5-004'
        run_role = $Arm
        ea_name = 'EA_SweepCascadeContinuation'
        symbol = 'EURUSD'
        period = 'M5'
        from = '2019.01.01'
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
        required_sidecars = $requiredSidecars
        broker_fingerprint = 'FIVEPERCENT_PORTABLE_DIAGNOSTIC'
        server_fingerprint = 'FIVEPERCENT_PORTABLE_DIAGNOSTIC'
        account_fingerprint = 'TESTER_ONLY'
        data_fingerprint = 'RUN_MANIFEST_BOUND'
        symbol_geometry = [ordered]@{ digits = 5; point = 0.00001; pip_size = 0.0001 }
        include_closure_sha256 = $emptyIncludeClosureSha
    }
    evidence = $evidence
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
}
Write-Utf8Json $receipt $receiptPath

[ordered]@{
    arm = $Arm
    task_packet = $taskPath
    task_sha256 = Get-FileSha256 $taskPath
    receipt = $receiptPath
    receipt_sha256 = Get-FileSha256 $receiptPath
    overrides = $overrides
} | ConvertTo-Json -Depth 6
