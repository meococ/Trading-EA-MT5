param(
    [ValidateSet('pair', 'control', 'challenger')]
    [string]$TargetArm = 'pair'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package = Join-Path $repo '03. EA Developer\EA_VRAS_PathConfirmedTrend'
$preflight = Join-Path $package 'research\preflight\HYP-VRAS-EURUSD-M5-004'
$sourcePath = Join-Path $package 'EA_VRAS_PathConfirmedTrend.mq5'
$binaryPath = Join-Path $package 'EA_VRAS_PathConfirmedTrend.ex5'
$includePath = Join-Path $package 'NewsCalendar2019_2022.mqh'
$preregPath = Join-Path $package 'research\HYP-VRAS-EURUSD-M5-004_FROZEN_PREREG.md'
$probePlanPath = Join-Path $package 'research\HYP-VRAS-EURUSD-M5-004_PROBE_PLAN.md'
$contractPath = Join-Path $package 'ALPHAFACTORY_EA_CONTRACT.json'
$auditManifestPath = Join-Path $package 'NONREPAINT_AUDIT_V1_manifest.json'
$auditPath = Join-Path $package 'research\evidence\20260722_NONREPAINT_AUDIT_V1\nonrepaint_audit.json'
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

$arms = @(
    [ordered]@{ name = 'control'; run_role = 'control'; variant = 'CONTROL_IMMEDIATE_TREND'; path_confirmation = 'false' },
    [ordered]@{ name = 'challenger'; run_role = 'challenger'; variant = 'CHALLENGER_PATH_CONFIRM'; path_confirmation = 'true' }
)
$selectedArms = if ($TargetArm -eq 'pair') { $arms } else { @($arms | Where-Object { $_.name -eq $TargetArm }) }

foreach ($arm in $selectedArms) {
    foreach ($suffix in @("task_packet.$($arm.name).json", "contract_receipt.$($arm.name).json")) {
        $generatedPath = Join-Path $preflight $suffix
        if (-not (Test-Path -LiteralPath $generatedPath -PathType Leaf)) {
            throw "Pre-create generated receipt path before running: $generatedPath"
        }
    }
}

$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))
$registryLines = @(Get-Content -LiteralPath $registryPath)
$registryRow = @($registryLines | Where-Object { $_ -match '"hypothesis_id":"HYP-VRAS-EURUSD-M5-004"' } | Select-Object -Last 1)
if ($registryRow.Count -ne 1 -or $registryRow[0] -notmatch '"state":"screened"') {
    throw 'Latest HYP-004 registry row must be the screened SHA-bound authorization.'
}

$commonOverrides = @(
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
    'InpHypothesisId=HYP-VRAS-EURUSD-M5-004',
    'InpMagic=5600744',
    'InpMaxAccountDrawdownPct=6.00',
    'InpMaxHoldBars=20',
    'InpMaxSpreadPips=1.20',
    'InpMaxTradesPerDay=3',
    'InpMinRegimeDwellBars=6',
    'InpNewsBlackoutMinutes=45',
    'InpRangeStopAtr=0.30',
    'InpRangeStopSd=2.50',
    'InpRequireNewsGuard=false',
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
    'InpVolumeMode=0',
    'InpWarmupBars=15'
)

$includeRecord = $includePath.ToLowerInvariant() + "`t" + (Get-FileSha256 $includePath)
$includeClosureSha = Get-TextSha256 $includeRecord
$results = @()

foreach ($arm in $selectedArms) {
    $taskPath = Join-Path $preflight "task_packet.$($arm.name).json"
    $receiptPath = Join-Path $preflight "contract_receipt.$($arm.name).json"
    $overridePairs = @($commonOverrides + @(
        "InpUsePathConfirmation=$($arm.path_confirmation)",
        "InpVariantTag=$($arm.variant)"
    ))
    $overrides = @($overridePairs | Sort-Object { ($_ -split '=', 2)[0] }) -join ';'

    $task = [ordered]@{
        schema_version = 'alphafactory_diagnostic_task_packet.v1'
        hypothesis_id = 'HYP-VRAS-EURUSD-M5-004'
        run_role = $arm.run_role
        purpose = 'Owner-authorized fresh-window matched Model-0 mechanism comparison; diagnostic only'
        ea_name = 'EA_VRAS_PathConfirmedTrend'
        source_path = '03. EA Developer/EA_VRAS_PathConfirmedTrend/EA_VRAS_PathConfirmedTrend.mq5'
        source_sha256 = Get-FileSha256 $sourcePath
        registry_path = '04. Memory/research/CANDIDATE_REGISTRY.jsonl'
        registry_sha256 = Get-FileSha256 $registryPath
        registry_row_sha256 = Get-TextSha256 ([string]$registryRow[0])
        prereg_path = '03. EA Developer/EA_VRAS_PathConfirmedTrend/research/HYP-VRAS-EURUSD-M5-004_FROZEN_PREREG.md'
        prereg_sha256 = Get-FileSha256 $preregPath
        probe_plan_path = '03. EA Developer/EA_VRAS_PathConfirmedTrend/research/HYP-VRAS-EURUSD-M5-004_PROBE_PLAN.md'
        probe_plan_sha256 = Get-FileSha256 $probePlanPath
        ea_contract_path = '03. EA Developer/EA_VRAS_PathConfirmedTrend/ALPHAFACTORY_EA_CONTRACT.json'
        ea_contract_sha256 = Get-FileSha256 $contractPath
        symbol = 'EURUSD'
        period = 'M5'
        from = '2023.01.03'
        to = '2026.06.30'
        model = 0
        execution_mode = 0
        fixed_delay_ms = 0
        overrides = $overrides
        telemetry_tier = 'trade-only'
        telemetry_profile = 'lifecycle-v3'
        required_sidecars = @('*_LifecycleTrades_*.csv', '*_RunMeta_*.json', '*_DecisionTelemetry_*.csv')
        deposit = 100000
        leverage = 100
        spread = 'current'
        cost_status = 'UNVERIFIED_DIAGNOSTIC_ONLY'
        news_guard = 'DISABLED_MATCHED_NO_2023PLUS_CALENDAR'
        promotion_eligible = $false
        git_commit = $gitCommit
        git_status = $gitStatus
        git_status_sha256 = $gitStatusSha
    }
    Write-Utf8Json $task $taskPath

    $evidence = @(
        [ordered]@{ label = 'task_packet'; kind = 'file'; path = $taskPath; sha256 = Get-FileSha256 $taskPath },
        [ordered]@{ label = 'candidate_registry'; kind = 'file'; path = $registryPath; sha256 = Get-FileSha256 $registryPath },
        [ordered]@{ label = 'source'; kind = 'file'; path = $sourcePath; sha256 = Get-FileSha256 $sourcePath },
        [ordered]@{ label = 'compiled_binary'; kind = 'file'; path = $binaryPath; sha256 = Get-FileSha256 $binaryPath },
        [ordered]@{ label = 'ea_capability_contract'; kind = 'file'; path = $contractPath; sha256 = Get-FileSha256 $contractPath },
        [ordered]@{ label = 'include_0000'; kind = 'file'; path = $includePath; sha256 = Get-FileSha256 $includePath },
        [ordered]@{ label = 'prereg'; kind = 'file'; path = $preregPath; sha256 = Get-FileSha256 $preregPath },
        [ordered]@{ label = 'probe_plan'; kind = 'file'; path = $probePlanPath; sha256 = Get-FileSha256 $probePlanPath },
        [ordered]@{ label = 'nonrepaint_manifest'; kind = 'file'; path = $auditManifestPath; sha256 = Get-FileSha256 $auditManifestPath },
        [ordered]@{ label = 'nonrepaint_audit'; kind = 'file'; path = $auditPath; sha256 = Get-FileSha256 $auditPath },
        [ordered]@{ label = 'cost_source_manifest'; kind = 'file'; path = $costManifestPath; sha256 = Get-FileSha256 $costManifestPath }
    )
    if ($arm.name -eq 'challenger') {
        $controlManifest = $null
        $runRoot = Join-Path $repo '02. AlphaFactory\runs\EA_VRAS_PathConfirmedTrend'
        if (Test-Path -LiteralPath $runRoot -PathType Container) {
            foreach ($candidate in @(Get-ChildItem -LiteralPath $runRoot -Directory | Sort-Object LastWriteTime -Descending)) {
                $manifestPath = Join-Path $candidate.FullName 'run_manifest.json'
                $reportPath = Join-Path $candidate.FullName 'report.html'
                if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
                    -not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
                    continue
                }
                $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
                if ([string]$manifest.hypothesis_id -ceq 'HYP-VRAS-EURUSD-M5-004' -and
                    [string]$manifest.run_role -ceq 'control') {
                    $controlManifest = [ordered]@{ manifest = $manifestPath; report = $reportPath }
                    break
                }
            }
        }
        if ($null -eq $controlManifest) {
            throw 'A completed HYP-004 control manifest and report are required before building the challenger receipt.'
        }
        $evidence += @(
            [ordered]@{ label = 'matched_control_manifest'; kind = 'file'; path = $controlManifest.manifest; sha256 = Get-FileSha256 $controlManifest.manifest },
            [ordered]@{ label = 'matched_control_report'; kind = 'file'; path = $controlManifest.report; sha256 = Get-FileSha256 $controlManifest.report }
        )
    }
    $receipt = [ordered]@{
        schema_version = 'alphafactory_execution_receipt.v1'
        hypothesis_id = 'HYP-VRAS-EURUSD-M5-004'
        registry_row_sha256 = Get-TextSha256 ([string]$registryRow[0])
        task_packet_sha256 = Get-FileSha256 $taskPath
        git_commit = $gitCommit
        git_status_sha256 = $gitStatusSha
        binding = [ordered]@{
            hypothesis_id = 'HYP-VRAS-EURUSD-M5-004'
            run_role = $arm.run_role
            ea_name = 'EA_VRAS_PathConfirmedTrend'
            symbol = 'EURUSD'
            period = 'M5'
            from = '2023.01.03'
            to = '2026.06.30'
            model = 0
            execution_mode = 0
            fixed_delay_ms = 0
            overrides = $overrides
            telemetry_tier = 'trade-only'
            telemetry_profile = 'lifecycle-v3'
            deposit = 100000
            leverage = 100
            spread = 'current'
            required_sidecars = @('*_LifecycleTrades_*.csv', '*_RunMeta_*.json', '*_DecisionTelemetry_*.csv')
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
    $results += [ordered]@{
        arm = $arm.name
        task_packet = $taskPath
        task_sha256 = Get-FileSha256 $taskPath
        receipt = $receiptPath
        receipt_sha256 = Get-FileSha256 $receiptPath
        overrides = $overrides
    }
}

$results | ConvertTo-Json -Depth 5
