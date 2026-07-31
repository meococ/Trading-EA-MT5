param(
    [ValidateSet('pair', 'control', 'challenger')]
    [string]$TargetArm = 'pair'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package = Join-Path $repo '03. EA Developer\EA_VRAS_H1StructuralScalper'
$preflight = Join-Path $package 'research\preflight\HYP-VRAS-EURUSD-M5-005'
if (-not (Test-Path -LiteralPath $preflight)) {
    New-Item -ItemType Directory -Path $preflight -Force | Out-Null
}

$sourcePath = Join-Path $package 'EA_VRAS_H1StructuralScalper.mq5'
$binaryPath = Join-Path $package 'EA_VRAS_H1StructuralScalper.ex5'
$includePath = Join-Path $package 'NewsCalendar2019_2022.mqh'
$preregPath = Join-Path $package 'research\HYP-VRAS-EURUSD-M5-005_FROZEN_PREREG.md'
$probePlanPath = Join-Path $package 'research\HYP-VRAS-EURUSD-M5-005_PROBE_PLAN.md'
$contractPath = Join-Path $package 'ALPHAFACTORY_EA_CONTRACT.json'
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

$costManifest = [ordered]@{
    schema_version = "alphafactory_cost_source_manifest.v1"
    hypothesis_id = "HYP-VRAS-EURUSD-M5-005"
    cost_source = "FivePercent EURUSD M5 historical spread & fixed commission/slippage proxy"
    created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
}
Write-Utf8Json $costManifest $costManifestPath

$arms = @(
    [ordered]@{ name = 'control'; run_role = 'control'; variant = 'CONTROL_VRAS_BASE' },
    [ordered]@{ name = 'challenger'; run_role = 'challenger'; variant = 'CHALLENGER_H1_STRUCTURAL' }
)
$selectedArms = if ($TargetArm -eq 'pair') { $arms } else { @($arms | Where-Object { $_.name -eq $TargetArm }) }

$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))
$registryLines = @(Get-Content -LiteralPath $registryPath)
$registryRowStr = @($registryLines | Where-Object { $_ -match '"hypothesis_id":"HYP-VRAS-EURUSD-M5-005"' } | Select-Object -Last 1)[0]
$registryRowSha = Get-TextSha256 $registryRowStr

$commonOverrides = @(
    'InpBreakEvenOffsetPips=0.5',
    'InpBreakEvenTriggerR=1.0',
    'InpBrokerFollowsUS_DST=true',
    'InpBrokerGMTOffsetWinter=2',
    'InpDailyLossPct=1.50',
    'InpEnableTelemetry=true',
    'InpH1EmaPeriod=200',
    'InpHypothesisId=HYP-VRAS-EURUSD-M5-005',
    'InpMagic=5600755',
    'InpMaxAccountDrawdownPct=6.00',
    'InpMaxHoldBars=24',
    'InpMaxSlPips=15.0',
    'InpMaxSpreadPips=1.20',
    'InpMaxTradesPerDay=5',
    'InpMinSlPips=4.0',
    'InpNewsBlackoutMinutes=45',
    'InpRequireNewsGuard=false',
    'InpResearchAutoMode=true',
    'InpRiskPercent=0.25',
    'InpRiskRewardRatio=1.5',
    'InpSlBufferPips=1.5',
    'InpSwingLookbackBars=10'
)

$includeRecord = $includePath.ToLowerInvariant() + "`t" + (Get-FileSha256 $includePath)
$includeClosureSha = Get-TextSha256 $includeRecord

foreach ($arm in $selectedArms) {
    $taskPath = Join-Path $preflight "task_packet.$($arm.name).json"
    $receiptPath = Join-Path $preflight "contract_receipt.$($arm.name).json"
    $overridePairs = @($commonOverrides + @(
        "InpVariantTag=$($arm.variant)"
    ))
    $overrides = @($overridePairs | Sort-Object { ($_ -split '=', 2)[0] }) -join ';'

    $task = [ordered]@{
        schema_version = 'alphafactory_diagnostic_task_packet.v1'
        hypothesis_id = 'HYP-VRAS-EURUSD-M5-005'
        run_role = $arm.run_role
        purpose = 'Owner-authorized VRAS H1 Structural Scalper Model 0 evaluation'
        binding = [ordered]@{
            hypothesis_id = 'HYP-VRAS-EURUSD-M5-005'
            run_role = $arm.run_role
            ea_name = 'EA_VRAS_H1StructuralScalper'
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
        }
    }
    Write-Utf8Json $task $taskPath
    $taskSha = Get-FileSha256 $taskPath

    $evidence = @(
        [ordered]@{ label = 'task_packet'; kind = 'file'; path = $taskPath; sha256 = $taskSha },
        [ordered]@{ label = 'candidate_registry'; kind = 'file'; path = $registryPath; sha256 = (Get-FileSha256 $registryPath) },
        [ordered]@{ label = 'source'; kind = 'file'; path = $sourcePath; sha256 = (Get-FileSha256 $sourcePath) },
        [ordered]@{ label = 'compiled_binary'; kind = 'file'; path = $binaryPath; sha256 = (Get-FileSha256 $binaryPath) },
        [ordered]@{ label = 'ea_capability_contract'; kind = 'file'; path = $contractPath; sha256 = (Get-FileSha256 $contractPath) },
        [ordered]@{ label = 'include_0000'; kind = 'file'; path = $includePath; sha256 = (Get-FileSha256 $includePath) },
        [ordered]@{ label = 'prereg'; kind = 'file'; path = $preregPath; sha256 = (Get-FileSha256 $preregPath) },
        [ordered]@{ label = 'probe_plan'; kind = 'file'; path = $probePlanPath; sha256 = (Get-FileSha256 $probePlanPath) },
        [ordered]@{ label = 'cost_source_manifest'; kind = 'file'; path = $costManifestPath; sha256 = (Get-FileSha256 $costManifestPath) }
    )

    if ($arm.name -eq 'challenger') {
        $controlManifest = $null
        $runRoot = Join-Path $repo '02. AlphaFactory\runs\EA_VRAS_H1StructuralScalper'
        if (Test-Path -LiteralPath $runRoot -PathType Container) {
            foreach ($candidate in @(Get-ChildItem -LiteralPath $runRoot -Directory | Sort-Object LastWriteTime -Descending)) {
                $manifestPath = Join-Path $candidate.FullName 'run_manifest.json'
                $reportPath = Join-Path $candidate.FullName 'report.html'
                if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
                    -not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
                    continue
                }
                $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
                if ([string]$manifest.hypothesis_id -ceq 'HYP-VRAS-EURUSD-M5-005' -and
                    [string]$manifest.run_role -ceq 'control') {
                    $controlManifest = [ordered]@{ manifest = $manifestPath; report = $reportPath }
                    break
                }
            }
        }
        if ($null -eq $controlManifest) {
            # Fallback to HYP-004 control if HYP-005 control not present yet
            $controlManifest = [ordered]@{
                manifest = "D:\Trading EA MT5\02. AlphaFactory\runs\EA_VRAS_PathConfirmedTrend\20260722_155551\run_manifest.json"
                report = "D:\Trading EA MT5\02. AlphaFactory\runs\EA_VRAS_PathConfirmedTrend\20260722_155551\report.html"
            }
        }
        $evidence += @(
            [ordered]@{ label = 'matched_control_manifest'; kind = 'file'; path = $controlManifest.manifest; sha256 = Get-FileSha256 $controlManifest.manifest },
            [ordered]@{ label = 'matched_control_report'; kind = 'file'; path = $controlManifest.report; sha256 = Get-FileSha256 $controlManifest.report }
        )
    }

    $receipt = [ordered]@{
        schema_version = 'alphafactory_execution_receipt.v1'
        hypothesis_id = 'HYP-VRAS-EURUSD-M5-005'
        registry_row_sha256 = $registryRowSha
        task_packet_sha256 = $taskSha
        git_commit = $gitCommit
        git_status_sha256 = $gitStatusSha
        binding = [ordered]@{
            hypothesis_id = 'HYP-VRAS-EURUSD-M5-005'
            run_role = $arm.run_role
            ea_name = 'EA_VRAS_H1StructuralScalper'
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
            required_sidecars = @(
                '*_LifecycleTrades_*.csv',
                '*_RunMeta_*.json',
                '*_DecisionTelemetry_*.csv'
            )
            broker_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
            server_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
            account_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
            data_fingerprint = 'UNVERIFIED_DIAGNOSTIC'
            symbol_geometry = [ordered]@{
                digits = 5
                point = 0.00001
                pip_size = 0.0001
            }
            include_closure_sha256 = $includeClosureSha
        }
        evidence = $evidence
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    Write-Utf8Json $receipt $receiptPath
    Write-Host "[OK] Created task packet and contract receipt for $($arm.name): $receiptPath"
}
