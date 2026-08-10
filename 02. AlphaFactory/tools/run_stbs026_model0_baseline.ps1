param(
    [string]$EaName = "",
    [string]$HypothesisId = "",
    [string]$RegistryPath = "",
    [string]$TaskPacket = "",
    [ValidateSet("control", "challenger")]
    [string]$RunRole = "challenger",
    [string]$Symbol = "XAUUSD",
    [string]$Period = "M5",
    [string]$From = "2024.01.01",
    [string]$To = "2025.12.31",
    [ValidateSet(0, 1, 2, 4)]
    [int]$Model = 0,
    [int]$ExecutionMode = 0,
    [int]$FixedDelayMs = 0,
    [int]$TimeoutSec = 7200,
    [string]$Overrides = "",
    [string]$VariantTag = "",
    [ValidateSet("off", "trade-only", "state-lite", "state-full", "snapshot-casebook")]
    [string]$TelemetryTier = "off",
    [int]$Deposit = 10000,
    [int]$Leverage = 100,
    [string]$Spread = "",
    [ValidateSet("challenger", "confirmed")]
    [string]$ValidationStage = "challenger",
    [ValidateSet("scalp", "non_scalp")]
    [string]$HoldingContract = "scalp",
    [string]$CostSourceManifest = "",
    [string]$WfaArtifact = "",
    [string]$VariantsDir = "",
    [string]$MatchedControlRunId = "",
    [switch]$SkipCompile,
    [switch]$SkipValidate,
    [switch]$SkipCostStress,
    [switch]$SkipMarketPhase,
    [switch]$SkipCompare,
    [switch]$CleanupCommonFiles,
    [switch]$AllowResearchCostProxy,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
$repoRoot = Split-Path -Parent $alphaRoot
$runtimeRoot = Join-Path $alphaRoot "runtime"
$alphaPs1 = Join-Path $alphaRoot "alpha.ps1"
$validatorPath = Join-Path $alphaRoot "analysis\unified_validation.py"
$costBuilderPath = Join-Path $toolsRoot "build_verified_cost_artifact.py"
$nonRepaintToolPath = Join-Path $toolsRoot "audit_mql5_nonrepaint.py"
$hyp026NonRepaintAuditorSha256 = "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360"
$hyp026StaticNonRepaintManifestPath = Join-Path $repoRoot "03. EA Developer\EA_SupertrendBurstScalperTradeV13\HYP-STBS-XAUUSD-M15-026_NONREPAINT_MANIFEST.json"
$hyp026StaticNonRepaintManifestSha256 = "958B4678772D2FFEF8DAC9A22ADCACEFCD0D868862180D02974C0C7433138E63"
$hyp026StaticNonRepaintAuditPath = Join-Path $repoRoot "03. EA Developer\EA_SupertrendBurstScalperTradeV13\research\HYP-STBS-XAUUSD-M15-026_NONREPAINT_AUDIT.json"
$hyp026StaticNonRepaintAuditSha256 = "D94C9745A0349D946C242B72B2F230B03E43F7E6334711D9ACDB2F89A00DA1E0"
$hyp026SourceSha256 = "F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4"
$hyp026ReservedPostPacketReviewRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_POST_PACKET_REVIEW.md"
$hyp026ReservedPostPacketReviewPlaceholderSha256 = "57D1D71A41020FCDE27D54A18D1C43FAD87BB4BFBA10F77BB5255B4F65E8F3B7"
$hyp026ReservedPostPacketReviewStatusLine = '?? "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_POST_PACKET_REVIEW.md"'
$hyp026ParentTerminalRowSha256 = "702308403DE58F752A8ECF6F249D7167546F9BD837D42F04386D4B3F3D86B6AA"
$hyp026ParentTerminalVerdict = "KILL_POSTCLAIM_ONE_SHOT_SELF_REJECTION_NO_ALPHA_NO_MT5_NO_ECONOMIC_VERDICT"
$hyp026ParentFailurePacketRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV12/research/HYP-STBS-XAUUSD-M15-025_POSTCLAIM_SELF_REJECTION_FAILURE.md"
$hyp026ParentFailurePacketSha256 = "F1B8F99D3D49974D20B8A77A6C554A49A4FBE20AE4FA1067122C509623270292"
$hyp026ParentFailureReviewRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV12/research/HYP-STBS-XAUUSD-M15-025_INDEPENDENT_POST_FAILURE_REVIEW.md"
$hyp026ParentFailureReviewSha256 = "3ED0948EB0C7D3E59C6E86539BAA38DA2E20E0AAB4C03884120AB41BBDBEBB9F"
$hyp026TesterProjectionRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV10/research/evidence/HYP-STBS-XAUUSD-M15-023/STBS023-FAILURE-CLOSE-001/tester_hyp023_no_spam_projection.utf16le.log"
$hyp026TesterProjectionSha256 = "DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B"
$hyp026TesterProjectionBytes = 871692L
$hyp026AgentProjectionRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV10/research/evidence/HYP-STBS-XAUUSD-M15-023/STBS023-FAILURE-CLOSE-001/agent_hyp023_no_spam_projection.utf16le.log"
$hyp026AgentProjectionSha256 = "2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF"
$hyp026AgentProjectionBytes = 858852L
$hyp026JournalBudgetAddendumRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_JOURNAL_BUDGET_ADDENDUM.md"
$hyp026JournalBudgetAddendumSha256 = "17D03D4936C9146441BA01D6F4F16DB13CBC2B622E01C56E78EF291981854176"
$hyp026PreExecutionHarnessAddendumRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_PRE_EXECUTION_HARNESS_ADDENDUM.md"
$hyp026PreExecutionHarnessAddendumSha256 = "68DAF00C76CDFEAC2F8558A6BC275A72E10D9CC3B7A68AD193C236A9CDF8D882"
$hyp026IndependentPreProbeReviewRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_INDEPENDENT_PRE_PROBE_REVIEW.md"
$hyp026IndependentPreProbeReviewSha256 = "1F58551217D6AF2895D2E1A133A9F148D1037BC763FE0A8963817123C549FAF6"
$hyp026BoundedDiffProofRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_V12_V13_POSTCLAIM_RECONCILIATION_DIFF_PROOF.md"
$hyp026BoundedDiffProofSha256 = "7E1BD63D851B6E77C94106DBCE5B737EA7C1A04539B683C34B33D87745FF3095"
$hyp026CompactTelemetryTestRelative = "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/tests/test_stbs026_v13_identity_contract.py"
$hyp026CompactTelemetryTestSha256 = "66DD9F7B31A85DF16AEFBFC7941EB1B36D67707D890CF5B5F222DB7F96E19FDE"
$hyp026CopyTimeLine = 678
$researchRoot = Join-Path $repoRoot "04. Memory\research"
$canonicalRegistryPath = [System.IO.Path]::GetFullPath((Join-Path $researchRoot "CANDIDATE_REGISTRY.jsonl"))
$registryPath = if ([string]::IsNullOrWhiteSpace($RegistryPath)) {
    $canonicalRegistryPath
} elseif ([System.IO.Path]::IsPathRooted($RegistryPath)) {
    [System.IO.Path]::GetFullPath($RegistryPath)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $RegistryPath))
}
$registryValidatorPath = Join-Path $researchRoot "validate_candidate_registry.py"
$lockPath = Join-Path $runtimeRoot "ea_research_loop.lock"
$globalValidationLockPath = Join-Path $runtimeRoot "alpha_backtest.lock"
$script:transitions = New-Object System.Collections.Generic.List[object]
$script:transitionLogPath = $null
$script:transitionHypothesisId = $HypothesisId
$script:earlyModel0EconomicAttemptRecord = $null

function Get-EarlySha256([byte[]]$Bytes) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Write-EarlyModel0FailureTerminal([string]$ErrorMessage) {
    $attempt = $script:earlyModel0EconomicAttemptRecord
    if ($null -eq $attempt -or (Test-Path -LiteralPath $attempt.TerminalPath)) { return }
    $terminal = [ordered]@{
        schema_version = 'alphafactory_model0_economic_attempt_terminal.v1'
        hypothesis_id = 'HYP-STBS-XAUUSD-M15-026'
        attempt_id = 'STBS026-MODEL0-TRAIN-001'
        status = 'FAILED'
        attempt_started_path = [string]$attempt.Path
        attempt_started_sha256 = [string]$attempt.Sha256
        run_id = $null
        run_dir = $null
        error = $ErrorMessage
        same_id_retry_authorized = $false
        terminal_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($terminal | ConvertTo-Json -Depth 10))
    $stream = [System.IO.File]::Open(
        [string]$attempt.TerminalPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally {
        $stream.Dispose()
    }
}

function New-EarlyModel0EconomicLaunchClaim {
    if (-not $Execute) { return $null }
    if (-not [string]::Equals($registryPath, $canonicalRegistryPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Execute requires the canonical registry before claim: $canonicalRegistryPath"
    }
    if ($EaName -cne 'EA_SupertrendBurstScalperTradeV13' -or
        $HypothesisId -cne 'HYP-STBS-XAUUSD-M15-026' -or
        $RunRole -cne 'control' -or $Symbol -cne 'XAUUSD' -or $Period -cne 'M15' -or
        $From -cne '2005.01.01' -or $To -cne '2023.01.01' -or $Model -ne 0 -or
        $ExecutionMode -ne 0 -or $FixedDelayMs -ne 0 -or $TimeoutSec -ne 900 -or
        $TelemetryTier -cne 'trade-only' -or $Deposit -ne 100000 -or $Leverage -ne 100 -or
        -not [string]::IsNullOrWhiteSpace($Spread)) {
        throw 'HYP026 execution scalars are invalid before claim.'
    }
    $registryBytes = [System.IO.File]::ReadAllBytes($registryPath)
    $registryText = [System.Text.UTF8Encoding]::new($false, $true).GetString($registryBytes)
    $rows = @($registryText -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $latest = $null
    $latestRaw = $null
    $latestLine = 0
    for ($index = 0; $index -lt $rows.Count; $index++) {
        $row = $rows[$index] | ConvertFrom-Json
        if ([string]$row.hypothesis_id -ceq 'HYP-STBS-XAUUSD-M15-026') {
            $latest = $row
            $latestRaw = [string]$rows[$index]
            $latestLine = $index + 1
        }
    }
    if ($null -eq $latest -or [string]$latest.state -cne 'screened') {
        throw 'HYP026 early claim requires the latest screened authority row.'
    }
    $validation = $latest.validation
    $metrics = $latest.metrics
    $expectedPacket = '03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/preflight/HYP-STBS-XAUUSD-M15-026/V1/task_packet.control.json'
    if ([string]$validation.authority -cne 'MODEL0_TRAIN_FALSIFICATION_ONLY' -or
        [string]$validation.one_shot_economic_harness_version -cne 'model0-economic-one-shot-v1' -or
        [string]$validation.mt5_attempt_id -cne 'STBS026-MODEL0-TRAIN-001' -or
        [int]$validation.mt5_attempt_limit -ne 1 -or [int]$metrics.mt5_attempts_consumed -ne 0 -or
        $validation.same_id_retry_authorized -ne $false -or
        [string]$validation.task_packet_path -cne $expectedPacket -or
        [string]::IsNullOrWhiteSpace([string]$validation.task_packet_sha256)) {
        throw 'HYP026 screened authority metadata is invalid before claim.'
    }
    $root = Join-Path $runtimeRoot 'model0_economic_attempts\HYP-STBS-XAUUSD-M15-026\STBS026-MODEL0-TRAIN-001'
    New-Item -ItemType Directory -Path (Split-Path -Parent $root) -Force | Out-Null
    New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
    $startPath = Join-Path $root 'attempt_started.json'
    $terminalPath = Join-Path $root 'attempt_terminal.json'
    $rowBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($latestRaw)
    $claim = [ordered]@{
        schema_version = 'alphafactory_model0_economic_attempt_started.v1'
        hypothesis_id = 'HYP-STBS-XAUUSD-M15-026'
        attempt_id = 'STBS026-MODEL0-TRAIN-001'
        registry_line = $latestLine
        registry_sha256 = Get-EarlySha256 $registryBytes
        registry_row_sha256 = Get-EarlySha256 $rowBytes
        task_packet_path = $expectedPacket
        task_packet_sha256 = [string]$validation.task_packet_sha256
        timeout_sec = 900
        model = 0
        run_role = 'control'
        claimed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $claimBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($claim | ConvertTo-Json -Depth 10))
    $stream = [System.IO.File]::Open(
        $startPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($claimBytes, 0, $claimBytes.Length)
        $stream.Flush($true)
    } finally {
        $stream.Dispose()
    }
    $attemptRecord = [pscustomobject]@{
        Kind = 'model0_economic'
        AttemptId = 'STBS026-MODEL0-TRAIN-001'
        Path = $startPath
        Sha256 = Get-EarlySha256 $claimBytes
        TerminalPath = $terminalPath
        RegistrySha256 = [string]$claim.registry_sha256
        RegistryRowSha256 = [string]$claim.registry_row_sha256
        TaskPacketPath = $expectedPacket
        TaskPacketSha256 = [string]$validation.task_packet_sha256
    }
    $script:earlyModel0EconomicAttemptRecord = $attemptRecord
    return $attemptRecord
}

trap {
    if ($null -ne $script:earlyModel0EconomicAttemptRecord) {
        try { Write-EarlyModel0FailureTerminal ([string]$_.Exception.Message) } catch {}
    }
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}

$script:earlyModel0EconomicAttemptRecord = New-EarlyModel0EconomicLaunchClaim
$eaContractResolverPath = Join-Path $toolsRoot "ea_contract.ps1"
if (-not (Test-Path -LiteralPath $eaContractResolverPath -PathType Leaf)) {
    throw "EA source contract resolver is missing: $eaContractResolverPath"
}
. $eaContractResolverPath
$terminalProcessGuardPath = Join-Path $toolsRoot 'terminal_process_guard.ps1'
if (-not (Test-Path -LiteralPath $terminalProcessGuardPath -PathType Leaf)) {
    throw "Terminal process guard helper is missing: $terminalProcessGuardPath"
}
. $terminalProcessGuardPath

function Write-Status($Message, $Type = "INFO") {
    $color = switch ($Type) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERR" { "Red" }
        default { "Cyan" }
    }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Write-JsonAtomically($Value, $Path, $Depth = 12) {
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $tempPath = Join-Path $directory (".{0}.{1}.tmp" -f (Split-Path -Leaf $Path), ([guid]::NewGuid().ToString("N")))
    try {
        $Value | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $tempPath -Encoding UTF8
        Move-Item -LiteralPath $tempPath -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Add-Override($Existing, $Name, $Value) {
    if ([string]::IsNullOrWhiteSpace($Name)) { return $Existing }
    if ($Existing -match "(^|;)\s*$([regex]::Escape($Name))\s*=") { return $Existing }
    $pair = "$Name=$Value"
    if ([string]::IsNullOrWhiteSpace($Existing)) { return $pair }
    return "$Existing;$pair"
}

function Get-Sha256IfExists($Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes([string]$Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-PathHashSetSha256($Entries) {
    $sortedEntries = @($Entries | ForEach-Object { $_ } | Sort-Object Path)
    $records = @(
        foreach ($entry in $sortedEntries) {
            $path = [System.IO.Path]::GetFullPath([string]$entry.Path).ToLowerInvariant()
            $hash = ([string]$entry.Sha256).ToUpperInvariant()
            "$path`t$hash"
        }
    )
    return Get-TextSha256 ([string]::Join("`n", $records))
}

function Test-NoGitWorkspace {
    $gitDir = Join-Path $repoRoot ".git"
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $insideOutput = @(& git -C $repoRoot rev-parse --is-inside-work-tree 2>$null)
        $insideExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldEap
    }
    $inside = ""
    if ($null -ne $insideOutput -and @($insideOutput).Count -gt 0 -and $null -ne $insideOutput[0]) {
        $inside = ([string]$insideOutput[0]).Trim()
    }
    if (($insideExit -eq 0) -and ($inside -ceq 'true')) { return $false }
    # Empty placeholder or non-work-tree .git => NO-GIT provenance.
    if (Test-Path -LiteralPath $gitDir) { return $true }
    return $true
}

function Get-NoGitProvenanceSnapshot([string]$ActiveSource = "") {
    $agentsPath = Join-Path $repoRoot "AGENTS.md"
    $goalPath = Join-Path $repoRoot "01. GOAL\GOAL.md"
    $provenancePaths = @($agentsPath, $goalPath)
    foreach ($required in $provenancePaths) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "NO-GIT provenance file missing (fail-closed): $required"
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($ActiveSource) -and (Test-Path -LiteralPath $ActiveSource -PathType Leaf)) {
        $provenancePaths += $ActiveSource
    }
    $records = New-Object System.Collections.Generic.List[string]
    foreach ($path in $provenancePaths) {
        $full = [System.IO.Path]::GetFullPath($path)
        $rootFull = [System.IO.Path]::GetFullPath($repoRoot).TrimEnd('\', '/')
        $rel = if ($full.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            $full.Substring($rootFull.Length).TrimStart('\', '/').Replace('\', '/')
        } else {
            $full.Replace('\', '/')
        }
        $fileHash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToUpperInvariant()
        $records.Add(("$rel`t$fileHash"))
    }
    $payload = [string]::Join("`n", @($records))
    $provSha = (Get-TextSha256 $payload).ToUpperInvariant()
    $commit = "NOGIT-$provSha"
    $statusLines = @("nogit=true", "dirty=true", "provenance_sha256=$provSha")
    return [pscustomobject]@{
        Commit = $commit
        Status = $statusLines
        StatusSha256 = Get-TextSha256 ([string]::Join("`n", $statusLines))
        NoGit = $true
        Dirty = $true
    }
}

function Get-GitSnapshot([string]$ActiveSource = "") {
    if (Test-NoGitWorkspace) {
        return Get-NoGitProvenanceSnapshot $ActiveSource
    }
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $commitOutput = @(& git -C $repoRoot rev-parse HEAD 2>$null)
        $commitExitCode = $LASTEXITCODE
        $commit = $commitOutput | Select-Object -First 1
        if (($commitExitCode -ne 0) -or [string]::IsNullOrWhiteSpace([string]$commit)) {
            return Get-NoGitProvenanceSnapshot $ActiveSource
        }
        $status = @(& git -C $repoRoot status --short --untracked-files=all 2>$null)
        $statusExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldEap
    }
    if ($statusExitCode -ne 0) { throw "Git status is unavailable for task-packet validation." }
    $statusLines = @($status | ForEach-Object { [string]$_ })
    return [pscustomobject]@{
        Commit = ([string]$commit).Trim()
        Status = $statusLines
        StatusSha256 = Get-TextSha256 ([string]::Join("`n", $statusLines))
        NoGit = $false
        Dirty = ($statusLines.Count -gt 0)
    }
}

function Assert-BacktestScalarContract($EANameValue, $HypothesisValue, $SymbolValue, $PeriodValue, $FromValue, $ToValue, $SpreadValue, $ExecutionModeValue, $FixedDelayValue) {
    $patterns = [ordered]@{
        EAName = '^[A-Za-z0-9][A-Za-z0-9 _.-]{0,127}$'
        HypothesisId = '^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$'
        Symbol = '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'
        Period = '^[A-Za-z0-9]{2,8}$'
    }
    $values = [ordered]@{
        EAName = [string]$EANameValue
        HypothesisId = [string]$HypothesisValue
        Symbol = [string]$SymbolValue
        Period = [string]$PeriodValue
    }
    foreach ($field in $patterns.Keys) {
        $value = $values[$field]
        if ($value -match '[\x00-\x1F\x7F]' -or $value -notmatch $patterns[$field]) {
            throw "$field contains unsupported or unsafe INI characters."
        }
    }
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $dateStyle = [System.Globalization.DateTimeStyles]::None
    $fromDate = [datetime]::MinValue
    $toDate = [datetime]::MinValue
    if (-not [datetime]::TryParseExact([string]$FromValue, 'yyyy.MM.dd', $culture, $dateStyle, [ref]$fromDate)) {
        throw "From must use a real yyyy.MM.dd date with no control characters."
    }
    if (-not [datetime]::TryParseExact([string]$ToValue, 'yyyy.MM.dd', $culture, $dateStyle, [ref]$toDate)) {
        throw "To must use a real yyyy.MM.dd date with no control characters."
    }
    if ($fromDate -gt $toDate) { throw "From must not be later than To." }
    if (-not [string]::IsNullOrWhiteSpace([string]$SpreadValue) -and [string]$SpreadValue -notmatch '^\d+(?:\.\d+)?$') {
        throw "Spread must be an empty current-spread request or a non-negative numeric value."
    }
    if ([int64]$ExecutionModeValue -lt 0 -or [int64]$FixedDelayValue -lt 0) {
        throw "ExecutionMode and FixedDelayMs must be non-negative."
    }
}

function ConvertTo-NormalizedOverrideMap([string]$OverrideText) {
    $map = [ordered]@{}
    if ([string]::IsNullOrWhiteSpace($OverrideText)) { return $map }
    foreach ($pair in ($OverrideText -split ';')) {
        $trimmed = $pair.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed -notmatch '^[^=\r\n]+=[^=\r\n]*$') { throw "Malformed tester override '$trimmed'. Expected Name=Value." }
        $parts = $trimmed.Split('=', 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ([string]::IsNullOrWhiteSpace($name)) { throw "Malformed tester override '$trimmed': input name is empty." }
        if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "Tester override input name '$name' is unsafe." }
        if ($value -match '[\x00-\x1F\x7F|]') { throw "Tester override '$name' contains unsafe control or delimiter characters." }
        if ($map.Contains($name)) { throw "Duplicate tester override '$name' is not deterministic." }
        $map[$name] = $value
    }
    return $map
}

function ConvertFrom-NormalizedOverrideMap($Map) {
    return [string]::Join(';', @($Map.Keys | Sort-Object | ForEach-Object { "$_=$($Map[$_])" }))
}

function Get-TelemetryInputNames {
    return @(
        'InpEnableTelemetry', 'InpEnableOpportunityLogger', 'InpEnableShadowNarrative',
        'InpEnableStateTelemetry', 'InpEnableGoldRegimeTelemetry',
        'InpEnableSourceClassicDragonEdgeDistanceTelemetry', 'InpEnableSourceH4TargetRunwayTelemetry',
        'InpEnableFxM15MtfPvaWeakeningTelemetry', 'InpEnableFxClassicNearMissTelemetry'
    )
}

function Resolve-TelemetryTierOverrides([string]$Tier, [string]$MainFile, [string]$OverrideText, [string]$TelemetryProfile = 'sonic-strict') {
    if ($Tier -notin @('off', 'trade-only', 'state-lite', 'state-full', 'snapshot-casebook')) {
        throw "Unsupported telemetry tier '$Tier'."
    }
    $source = Get-Content -LiteralPath $MainFile -Raw
    $inputs = @(Get-TelemetryInputNames)

    if ($TelemetryProfile -ceq 'none') {
        if ($Tier -cne 'off') {
            throw "telemetry tier '$Tier' is not supported by EA telemetry profile 'none' for $MainFile."
        }
        $map = ConvertTo-NormalizedOverrideMap $OverrideText
        foreach ($name in $inputs) {
            if ($map.Contains($name)) {
                throw "EA telemetry profile 'none' forbids Sonic override '$name' for $MainFile."
            }
        }
        return ConvertFrom-NormalizedOverrideMap $map
    }
    if ($TelemetryProfile -ceq 'lifecycle-v3') {
        if ($Tier -notin @('off', 'trade-only')) {
            throw "telemetry profile 'lifecycle-v3' supports only 'off' and 'trade-only'; got '$Tier'."
        }
        $declaration = '(?m)^\s*(?:sinput|input)\s+[^;\r\n]*\bInpEnableTelemetry\b\s*(?:=|;)'
        if ($source -notmatch $declaration) {
            throw "EA input 'InpEnableTelemetry' required by telemetry profile 'lifecycle-v3' is absent from $MainFile."
        }
        $map = ConvertTo-NormalizedOverrideMap $OverrideText
        $map['InpEnableTelemetry'] = if ($Tier -ceq 'trade-only') { 'true' } else { 'false' }
        return ConvertFrom-NormalizedOverrideMap $map
    }
    if ($TelemetryProfile -cne 'sonic-strict') {
        throw "Unsupported EA telemetry profile '$TelemetryProfile'."
    }

    foreach ($name in $inputs) {
        $declaration = '(?m)^\s*(?:sinput|input)\s+[^;\r\n]*\b' + [regex]::Escape($name) + '\b\s*(?:=|;)'
        if ($source -notmatch $declaration) {
            throw "EA input '$name' required for telemetry tier '$Tier' is absent from $MainFile."
        }
    }
    $enabled = switch ($Tier) {
        'off' { @() }
        'trade-only' { @('InpEnableTelemetry') }
        'state-lite' { @('InpEnableTelemetry', 'InpEnableOpportunityLogger', 'InpEnableStateTelemetry') }
        'state-full' { @($inputs) }
        'snapshot-casebook' { @($inputs) }
    }
    $map = ConvertTo-NormalizedOverrideMap $OverrideText
    foreach ($name in $inputs) { $map[$name] = if ($name -in $enabled) { 'true' } else { 'false' } }
    return ConvertFrom-NormalizedOverrideMap $map
}

function Get-RequiredSidecarsForTier([string]$Tier, [string]$TelemetryProfile = 'sonic-strict') {
    if ($TelemetryProfile -ceq 'none') {
        if ($Tier -cne 'off') { throw "telemetry profile 'none' supports only tier 'off'." }
        return @()
    }
    if ($TelemetryProfile -ceq 'lifecycle-v3') {
        switch ($Tier) {
            'off' { return @() }
            'trade-only' { return @('*_LifecycleTrades_*.csv', '*_RunMeta_*.json') }
            default { throw "telemetry profile 'lifecycle-v3' does not support tier '$Tier'." }
        }
    }
    if ($TelemetryProfile -cne 'sonic-strict') { throw "Unsupported EA telemetry profile '$TelemetryProfile'." }
    $trade = @('*_Signals_*.csv', '*_Trades_*.csv', '*_PVSRA_SR_Fields_*.csv', '*_RunMeta_*.json')
    $lite = @($trade + @('*_Opportunities_*.csv', '*_StateTelemetry_*.csv'))
    $full = @($lite + @('*_FxClassicNearMiss_*.csv', '*_GoldRegimeContext_*.csv'))
    switch ($Tier) {
        'off' { return @() }
        'trade-only' { return $trade }
        'state-lite' { return $lite }
        'state-full' { return $full }
        'snapshot-casebook' { return $full }
        default { throw "Unsupported telemetry tier '$Tier'." }
    }
}

function Get-DirectoryTreeSha256($Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $null }
    $root = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $records = @(
        Get-ChildItem -LiteralPath $root -Recurse -File | Sort-Object FullName | ForEach-Object {
            $relative = $_.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
            "$relative`t$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)"
        }
    )
    $payload = [string]::Join("`n", $records)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($payload)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-ManifestIncludeSetSha256($Manifest) {
    $snapshotRoot = [System.IO.Path]::GetFullPath([string](Get-ObjectProperty $Manifest 'snapshot_root')).TrimEnd('\')
    $snapshotPrefix = "$snapshotRoot\"
    $records = @(
        @(Get-ObjectProperty $Manifest 'include_snapshots') | Sort-Object snapshot_path | ForEach-Object {
            $path = [System.IO.Path]::GetFullPath([string](Get-ObjectProperty $_ 'snapshot_path'))
            if (-not $path.StartsWith($snapshotPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Include snapshot escapes snapshot root: $path"
            }
            $actual = Get-Sha256IfExists $path
            if (-not (Test-Sha256Text $actual) -or $actual -ine [string](Get-ObjectProperty $_ 'sha256')) {
                throw "Include snapshot hash mismatch: $path"
            }
            $relative = $path.Substring($snapshotPrefix.Length).Replace('\', '/')
            "$relative`t$actual"
        }
    )
    return Get-TextSha256 ([string]::Join("`n", $records))
}

function Test-IntegerValue($Value) {
    return ($Value -is [byte]) -or ($Value -is [sbyte]) -or
        ($Value -is [int16]) -or ($Value -is [uint16]) -or
        ($Value -is [int32]) -or ($Value -is [uint32]) -or
        ($Value -is [int64]) -or ($Value -is [uint64])
}

function Test-Sha256Text($Value) {
    return (-not [string]::IsNullOrWhiteSpace([string]$Value)) -and ([string]$Value -match '^[A-Fa-f0-9]{64}$')
}

function Test-ProvenanceObject($Value) {
    return ($null -ne $Value) -and ($Value -is [pscustomobject])
}

function Test-PositiveInteger($Value) {
    return (Test-IntegerValue $Value) -and ([int64]$Value -gt 0)
}

function Test-NonNegativeNumber($Value) {
    if ($Value -isnot [byte] -and $Value -isnot [sbyte] -and
        $Value -isnot [int16] -and $Value -isnot [uint16] -and
        $Value -isnot [int32] -and $Value -isnot [uint32] -and
        $Value -isnot [int64] -and $Value -isnot [uint64] -and
        $Value -isnot [single] -and $Value -isnot [double] -and
        $Value -isnot [decimal]) {
        return $false
    }
    $number = [double]$Value
    return (-not [double]::IsNaN($number)) -and (-not [double]::IsInfinity($number)) -and ($number -ge 0)
}

function Test-FiniteNumber($Value) {
    if ($Value -isnot [byte] -and $Value -isnot [sbyte] -and
        $Value -isnot [int16] -and $Value -isnot [uint16] -and
        $Value -isnot [int32] -and $Value -isnot [uint32] -and
        $Value -isnot [int64] -and $Value -isnot [uint64] -and
        $Value -isnot [single] -and $Value -isnot [double] -and
        $Value -isnot [decimal]) {
        return $false
    }
    $number = [double]$Value
    return (-not [double]::IsNaN($number)) -and (-not [double]::IsInfinity($number))
}

function Get-ObjectProperty($Object, $Name) {
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Get-IndicatorDependencyBindingRecords($Dependencies) {
    $seen = @{}
    return @(
        foreach ($dependency in @($Dependencies) | Sort-Object { [string](Get-ObjectProperty $_ 'name') }) {
            $name = [string](Get-ObjectProperty $dependency 'name')
            $source = ([string](Get-ObjectProperty $dependency 'source')).Replace('\', '/')
            $sourceSha = ([string](Get-ObjectProperty $dependency 'source_sha256')).ToUpperInvariant()
            $terminalEx5 = ([string](Get-ObjectProperty $dependency 'terminal_ex5')).Replace('/', '\')
            if ($name -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$' -or $seen.ContainsKey($name) -or
                [string]::IsNullOrWhiteSpace($source) -or $sourceSha -notmatch '^[A-F0-9]{64}$' -or
                [string]::IsNullOrWhiteSpace($terminalEx5)) {
                throw "Malformed or duplicate indicator dependency binding '$name'."
            }
            $seen[$name] = $true
            "$name`t$source`t$sourceSha`t$terminalEx5"
        }
    )
}

function Get-LiveIndicatorDependencyBinding($Dependencies) {
    return @(
        foreach ($dependency in @($Dependencies)) {
            [pscustomobject][ordered]@{
                name = [string]$dependency.Name
                source = [string]$dependency.SourceRelativePath
                source_sha256 = Get-Sha256IfExists ([string]$dependency.SourceAbsolutePath)
                terminal_ex5 = [string]$dependency.TerminalEx5RelativePath
                source_absolute_path = [string]$dependency.SourceAbsolutePath
            }
        }
    )
}

function Test-ExactObjectKeys($Object, [string[]]$ExpectedKeys) {
    if (-not (Test-ProvenanceObject $Object)) { return $false }
    $actual = @($Object.PSObject.Properties | ForEach-Object { $_.Name } | Sort-Object)
    $expected = @($ExpectedKeys | Sort-Object)
    return [string]::Join("`n", $actual) -ceq [string]::Join("`n", $expected)
}

function Test-ResearchDate($Value) {
    $text = [string]$Value
    if ($text -notmatch '^\d{4}\.\d{2}\.\d{2}$') { return $false }
    try {
        [void][datetime]::ParseExact(
            $text,
            'yyyy.MM.dd',
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::None
        )
        return $true
    } catch {
        return $false
    }
}

function Test-ZuluTimestamp($Value) {
    $text = [string]$Value
    if ($text -notmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$') { return $false }
    try {
        $parsed = [datetimeoffset]::Parse(
            $text,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        )
        return $parsed.Offset -eq [timespan]::Zero
    } catch {
        return $false
    }
}

function Resolve-DataQualityContract($Packet, $Binding, $Blockers) {
    $dataQualityCandidates = @(
        $Packet.PSObject.Properties |
            Where-Object { $_.Name -ieq 'data_quality_contract' }
    )
    $dataQualityExact = @($dataQualityCandidates | Where-Object { $_.Name -ceq 'data_quality_contract' })
    if ($dataQualityCandidates.Count -eq 0) { return $null }
    if ($dataQualityCandidates.Count -ne 1 -or $dataQualityExact.Count -ne 1) {
        $Blockers.Add("Task packet optional field name must be exactly case-sensitive 'data_quality_contract'.")
        return $null
    }
    $dataQualityProperty = $dataQualityExact[0]
    $startingBlockerCount = $Blockers.Count

    $dataQuality = $dataQualityProperty.Value
    $contractKeys = @(
        'history_quality', 'coverage_mode', 'availability_asof_utc',
        'requested_from', 'requested_to', 'require_tester_journal_bounds',
        'max_journal_delta_bytes'
    )
    if (-not (Test-ExactObjectKeys $dataQuality $contractKeys)) {
        $Blockers.Add("Task packet data_quality_contract must contain the six base fields plus max_journal_delta_bytes.")
        return $null
    }

    $historyQuality = Get-ObjectProperty $dataQuality 'history_quality'
    $operator = $null
    $threshold = $null
    if (-not (Test-ExactObjectKeys $historyQuality @('operator', 'value'))) {
        $Blockers.Add("Task packet data_quality_contract.history_quality must contain exactly operator and value.")
    } else {
        $operator = [string](Get-ObjectProperty $historyQuality 'operator')
        $threshold = Get-ObjectProperty $historyQuality 'value'
        if ($operator -cne 'gt') {
            $Blockers.Add("Task packet data_quality_contract.history_quality.operator must equal 'gt'.")
        }
        if (-not (Test-FiniteNumber $threshold) -or [double]$threshold -lt 97.0 -or [double]$threshold -ge 100.0) {
            $Blockers.Add("Task packet data_quality_contract.history_quality.value must be a finite number in [97,100).")
        }
    }

    $coverageMode = [string](Get-ObjectProperty $dataQuality 'coverage_mode')
    if ($coverageMode -notin @('all_available_asof', 'fixed_window')) {
        $Blockers.Add("Task packet data_quality_contract.coverage_mode must equal 'all_available_asof' or 'fixed_window'.")
    }
    $availabilityAsOfUtc = [string](Get-ObjectProperty $dataQuality 'availability_asof_utc')
    if (-not (Test-ZuluTimestamp $availabilityAsOfUtc)) {
        $Blockers.Add("Task packet data_quality_contract.availability_asof_utc must be a Z timestamp.")
    } else {
        $parsedAsOf = [datetimeoffset]::Parse(
            $availabilityAsOfUtc,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        )
        if ($parsedAsOf.UtcDateTime -gt (Get-Date).ToUniversalTime()) {
            $Blockers.Add("Task packet data_quality_contract.availability_asof_utc must not be in the future at preflight.")
        }
    }
    $requestedFrom = [string](Get-ObjectProperty $dataQuality 'requested_from')
    $requestedTo = [string](Get-ObjectProperty $dataQuality 'requested_to')
    if (-not (Test-ResearchDate $requestedFrom)) {
        $Blockers.Add("Task packet data_quality_contract.requested_from must use YYYY.MM.DD.")
    } elseif ($requestedFrom -cne [string]$Binding.From) {
        $Blockers.Add("Task packet data_quality_contract.requested_from must match task packet/from binding '$($Binding.From)'.")
    } elseif ($coverageMode -ceq 'all_available_asof' -and $requestedFrom -cne '1970.01.01') {
        $Blockers.Add("Task packet all_available_asof requested_from must equal the frozen sentinel '1970.01.01'.")
    } elseif ($coverageMode -ceq 'fixed_window' -and $requestedFrom -ceq '1970.01.01') {
        $Blockers.Add("Task packet fixed_window requested_from must not use the all-available sentinel '1970.01.01'.")
    }
    if (-not (Test-ResearchDate $requestedTo)) {
        $Blockers.Add("Task packet data_quality_contract.requested_to must use YYYY.MM.DD.")
    } elseif ($requestedTo -cne [string]$Binding.To) {
        $Blockers.Add("Task packet data_quality_contract.requested_to must match task packet/to binding '$($Binding.To)'.")
    } elseif ($coverageMode -ceq 'all_available_asof' -and (Test-ZuluTimestamp $availabilityAsOfUtc)) {
        $asOfDate = [datetimeoffset]::Parse(
            $availabilityAsOfUtc,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        ).UtcDateTime.ToString('yyyy.MM.dd')
        if ($requestedTo -cne $asOfDate) {
            $Blockers.Add("Task packet data_quality_contract.requested_to must equal the UTC calendar date of availability_asof_utc '$asOfDate'.")
        }
    } elseif ($coverageMode -ceq 'fixed_window' -and (Test-ZuluTimestamp $availabilityAsOfUtc)) {
        $fromDate = [datetime]::ParseExact($requestedFrom, 'yyyy.MM.dd', [System.Globalization.CultureInfo]::InvariantCulture)
        $toDate = [datetime]::ParseExact($requestedTo, 'yyyy.MM.dd', [System.Globalization.CultureInfo]::InvariantCulture)
        $asOfDate = [datetimeoffset]::Parse(
            $availabilityAsOfUtc,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        ).UtcDateTime.Date
        if ($fromDate -ge $toDate) {
            $Blockers.Add("Task packet fixed_window requested_from must be earlier than requested_to.")
        }
        if ($toDate -gt $asOfDate) {
            $Blockers.Add("Task packet fixed_window requested_to must not be later than availability_asof_utc.")
        }
    }
    $journalBounds = Get-ObjectProperty $dataQuality 'require_tester_journal_bounds'
    if ($journalBounds -isnot [bool] -or (-not [bool]$journalBounds)) {
        $Blockers.Add("Task packet data_quality_contract.require_tester_journal_bounds must be true.")
    }
    $maxJournalDeltaBytes = Get-ObjectProperty $dataQuality 'max_journal_delta_bytes'
    $integerTypes = @([byte], [sbyte], [int16], [uint16], [int32], [uint32], [int64], [uint64])
    if ($null -eq $maxJournalDeltaBytes -or $maxJournalDeltaBytes.GetType() -notin $integerTypes -or
        [uint64]$maxJournalDeltaBytes -ne 4194304L) {
        $Blockers.Add("Task packet data_quality_contract.max_journal_delta_bytes must equal the frozen 4194304-byte raw-delta cap.")
    }

    if ($Blockers.Count -gt $startingBlockerCount) { return $null }
    return [pscustomobject][ordered]@{
        history_quality = [pscustomobject][ordered]@{
            operator = $operator
            value = [double]$threshold
        }
        coverage_mode = $coverageMode
        availability_asof_utc = $availabilityAsOfUtc
        requested_from = $requestedFrom
        requested_to = $requestedTo
        require_tester_journal_bounds = [bool]$journalBounds
        max_journal_delta_bytes = [int64]$maxJournalDeltaBytes
    }
}

function Add-RegisteredDataAcceptanceBlockers($Registered, $DataQuality, $Binding, $Blockers) {
    if (-not (Test-ProvenanceObject $Registered)) {
        $Blockers.Add("Latest data-acquisition registry row has no structured data_acceptance_contract.")
        return
    }
    if ($null -eq $DataQuality) {
        $Blockers.Add("Data-acquisition task packet must provide a valid data_quality_contract.")
        return
    }
    $symbols = @(Get-ObjectProperty $Registered 'mandatory_symbols')
    if ($symbols.Count -eq 0 -or [string]$Binding.Symbol -cnotin @($symbols | ForEach-Object { [string]$_ })) {
        $Blockers.Add("Data-acquisition symbol '$($Binding.Symbol)' is outside the frozen mandatory_symbols set.")
    }
    if ([string](Get-ObjectProperty $Registered 'history_quality_operator') -cne
        [string](Get-ObjectProperty $DataQuality.history_quality 'operator') -or
        [double](Get-ObjectProperty $Registered 'history_quality_threshold_pct') -ne
        [double](Get-ObjectProperty $DataQuality.history_quality 'value')) {
        $Blockers.Add("Task packet history-quality gate does not match the frozen data_acceptance_contract.")
    }
    if ([string](Get-ObjectProperty $Registered 'coverage_mode') -cne
        [string](Get-ObjectProperty $DataQuality 'coverage_mode')) {
        $Blockers.Add("Task packet coverage_mode does not match the frozen data_acceptance_contract.")
    }
    foreach ($requiredTrue in @('no_skip', 'require_tester_journal_bounds', 'require_series_proof')) {
        if ((Get-ObjectProperty $Registered $requiredTrue) -ne $true) {
            $Blockers.Add("Frozen data_acceptance_contract.$requiredTrue must be true.")
        }
    }
    if ((Get-ObjectProperty $DataQuality 'require_tester_journal_bounds') -ne $true) {
        $Blockers.Add("Task packet must preserve require_tester_journal_bounds=true.")
    }
}

function Resolve-EvidencePath($RawPath) {
    if ([string]::IsNullOrWhiteSpace([string]$RawPath)) { return $null }
    $candidate = if ([System.IO.Path]::IsPathRooted([string]$RawPath)) {
        [System.IO.Path]::GetFullPath([string]$RawPath)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot ([string]$RawPath)))
    }
    return $candidate
}

function Get-RepoRelativePath($Path) {
    $fullPath = [System.IO.Path]::GetFullPath([string]$Path)
    $fullRoot = [System.IO.Path]::GetFullPath($repoRoot).TrimEnd('\', '/')
    $prefix = "$fullRoot\"
    if (-not $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Evidence path is outside the workspace: $fullPath"
    }
    return $fullPath.Substring($prefix.Length).Replace('\', '/')
}

function Resolve-CostEvidenceFile($RawPath, $ExpectedSha256, [string]$Label, $Blockers) {
    if ([string]::IsNullOrWhiteSpace([string]$RawPath)) {
        $Blockers.Add("$Label.source is required.")
        return $null
    }

    $resolvedPath = Resolve-EvidencePath ([string]$RawPath)
    if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
        $Blockers.Add("$Label.source is missing: $resolvedPath")
        return $null
    }
    if (-not (Test-Sha256Text $ExpectedSha256)) {
        $Blockers.Add("$Label.source_sha256 must be a SHA256 value.")
        return $null
    }

    $actualSha256 = Get-Sha256IfExists $resolvedPath
    if ($actualSha256 -ine [string]$ExpectedSha256) {
        $Blockers.Add("$Label.source_sha256 mismatch: expected '$ExpectedSha256', got '$actualSha256'.")
        return $null
    }

    return [pscustomobject]@{
        Label = $Label
        Path = $resolvedPath
        Sha256 = $actualSha256
    }
}

function Assert-CandidateRegistryValid {
    if (-not (Test-Path -LiteralPath $registryValidatorPath -PathType Leaf)) {
        throw "Candidate registry validator is missing: $registryValidatorPath"
    }

    $validatorOutput = @(& python $registryValidatorPath --registry $registryPath 2>&1)
    $validatorExitCode = $LASTEXITCODE
    $validatorText = ($validatorOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    foreach ($line in $validatorOutput) {
        Write-Host ([string]$line)
    }
    if ($validatorExitCode -ne 0) {
        throw "Candidate registry validator failed with exit code $validatorExitCode.`n$validatorText"
    }
    if ($validatorText -notmatch 'CANDIDATE_REGISTRY_OK') {
        throw "Candidate registry validator did not emit CANDIDATE_REGISTRY_OK.`n$validatorText"
    }
}

function Get-LatestCandidateRegistryIdentity([string]$RegistryPath, [string]$HypothesisId) {
    if (-not (Test-Path -LiteralPath $RegistryPath -PathType Leaf)) {
        throw "Candidate registry is missing: $RegistryPath"
    }
    $matches = New-Object System.Collections.Generic.List[object]
    $lineNumber = 0
    foreach ($line in (Get-Content -LiteralPath $RegistryPath)) {
        $lineNumber++
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $row = $line | ConvertFrom-Json
        } catch {
            throw "Candidate registry is malformed at line ${lineNumber}: $($_.Exception.Message)"
        }
        $rowHypothesis = Get-ObjectProperty $row 'hypothesis_id'
        if (($null -ne $rowHypothesis) -and ([string]$rowHypothesis -ceq $HypothesisId)) {
            $matches.Add([pscustomobject]@{
                Line = $lineNumber
                Raw = [string]$line
                RowSha256 = Get-TextSha256 ([string]$line)
            })
        }
    }
    if ($matches.Count -eq 0) {
        throw "HypothesisId '$HypothesisId' not found in registry: $RegistryPath"
    }
    return $matches[$matches.Count - 1]
}

function Resolve-ResearchContract($RequestedHypothesisId, $RequestedEaName) {
    if ([string]::IsNullOrWhiteSpace($RequestedHypothesisId)) {
        throw "HypothesisId is required before dry-run or execution."
    }
    if ($RequestedHypothesisId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$') {
        throw "HypothesisId contains unsupported characters: $RequestedHypothesisId"
    }
    if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) {
        throw "Canonical candidate registry is missing: $registryPath"
    }
    Assert-CandidateRegistryValid

    $matches = New-Object System.Collections.Generic.List[object]
    $lineNumber = 0
    foreach ($line in (Get-Content -LiteralPath $registryPath)) {
        $lineNumber++
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $row = $line | ConvertFrom-Json
        } catch {
            throw "Candidate registry is malformed at line ${lineNumber}: $($_.Exception.Message)"
        }
        $rowHypothesis = Get-ObjectProperty $row 'hypothesis_id'
        if (($null -ne $rowHypothesis) -and ([string]$rowHypothesis -ceq $RequestedHypothesisId)) {
            $matches.Add([pscustomobject]@{ Row = $row; Line = $lineNumber; Raw = [string]$line })
        }
    }
    if ($matches.Count -eq 0) {
        throw "HypothesisId '$RequestedHypothesisId' not found in registry: $registryPath"
    }

    $latest = $matches[$matches.Count - 1]
    $latestRow = $latest.Row
    $registeredPreregPath = [string](Get-ObjectProperty $latestRow 'prereg_path')
    $resolvedPreregPath = if (
        [string]::IsNullOrWhiteSpace($registeredPreregPath) -or
        $registeredPreregPath -like 'not-created:*'
    ) {
        $null
    } else {
        Resolve-EvidencePath $registeredPreregPath
    }
    $sourceContract = Resolve-EaSourceContract -RepoRoot $repoRoot -EaName $RequestedEaName
    $canonicalSourcePath = $sourceContract.RepoRelativeSource
    $canonicalSourceAbsolute = $sourceContract.AbsoluteSource

    return [pscustomobject]@{
        HypothesisId = $RequestedHypothesisId
        RegistryPath = (Resolve-Path -LiteralPath $registryPath).Path
        RegistrySha256 = Get-Sha256IfExists $registryPath
        RegistryLine = $latest.Line
        RegistryRowSha256 = Get-TextSha256 $latest.Raw
        LatestRow = $latestRow
        RegistryState = [string](Get-ObjectProperty $latestRow 'state')
        RegistryRecordType = [string](Get-ObjectProperty $latestRow 'record_type')
        RegistryModel = Get-ObjectProperty $latestRow 'model'
        RegistrySourcePath = [string](Get-ObjectProperty $latestRow 'source_path')
        RegistrySourceHash = [string](Get-ObjectProperty $latestRow 'source_hash')
        EvidenceContractKind = [string](Get-ObjectProperty $latestRow 'evidence_contract_kind')
        AcceptanceContract = Get-ObjectProperty $latestRow 'acceptance_contract'
        DataAcceptanceContract = Get-ObjectProperty $latestRow 'data_acceptance_contract'
        RegisteredPreregPath = $registeredPreregPath
        PreregPath = $resolvedPreregPath
        PreregSha256 = Get-Sha256IfExists $resolvedPreregPath
        CanonicalSourcePath = $canonicalSourcePath
        CanonicalSourceAbsolute = $canonicalSourceAbsolute
        CurrentSourceSha256 = Get-Sha256IfExists $canonicalSourceAbsolute
        TelemetryProfile = $sourceContract.TelemetryProfile
        MarketPhaseAdapter = $sourceContract.MarketPhaseAdapter
        ComparisonAdapter = $sourceContract.ComparisonAdapter
        VariantTagInput = $sourceContract.VariantTagInput
        EaContractPath = $sourceContract.ContractRelativePath
        EaContractAbsolutePath = $sourceContract.ContractAbsolutePath
        EaContractSha256 = $sourceContract.ContractSha256
        IndicatorDependencies = @($sourceContract.IndicatorDependencies)
        SourceContractPinned = $sourceContract.IsPinned
    }
}

function Get-ResearchContractBlockers($Contract, $RequestedModel, $RequestedTelemetryTier, [string]$ExecutionAuthority = '') {
    $blockers = New-Object System.Collections.Generic.List[string]
    if ($Contract.RegistryState -in @('killed', 'parked')) {
        $blockers.Add("Latest registry row is terminal state '$($Contract.RegistryState)'; execution is rejected.")
    }
    if ($Contract.RegistryState -notin @('screened', 'challenger')) {
        $blockers.Add("Latest registry state '$($Contract.RegistryState)' is not execution-eligible; freeze the prereg and append state 'screened' before Model 0.")
    }
    $isDataAcquisition = $ExecutionAuthority -in @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )
    if ($Contract.TelemetryProfile -ceq 'none' -and -not $isDataAcquisition) {
        $blockers.Add("EA has no AlphaFactory lifecycle telemetry contract; meaningful execution would fail verified-cost validation. Add ALPHAFACTORY_EA_CONTRACT.json and implement lifecycle-v3 telemetry before Model 0.")
    }
    if ($isDataAcquisition -and ($Contract.TelemetryProfile -cne 'none' -or $RequestedTelemetryTier -cne 'off')) {
        $blockers.Add("Data-acquisition authority requires telemetry_profile='none' and TelemetryTier=off.")
    }
    if ($Contract.TelemetryProfile -ceq 'lifecycle-v3' -and $RequestedTelemetryTier -cne 'trade-only') {
        $blockers.Add("EA telemetry profile 'lifecycle-v3' requires TelemetryTier=trade-only before MT5; got '$RequestedTelemetryTier'.")
    }
    if ($Contract.TelemetryProfile -ceq 'sonic-strict' -and $RequestedTelemetryTier -ceq 'off') {
        $blockers.Add("EA telemetry profile 'sonic-strict' cannot execute with TelemetryTier=off.")
    }
    if ($Contract.TelemetryProfile -ne 'none' -and [string]::IsNullOrWhiteSpace($Contract.EaContractSha256)) {
        $blockers.Add("EA telemetry capability is not bound to ALPHAFACTORY_EA_CONTRACT.json.")
    }
    if (-not (Test-IntegerValue $Contract.RegistryModel)) {
        $blockers.Add("Latest registry row does not declare an integer MT5 model; offline/non-EA rows cannot execute.")
    } elseif ([int64]$Contract.RegistryModel -notin @(0, 1, 2, 4)) {
        $blockers.Add("Latest registry row declares unsupported MT5 model '$($Contract.RegistryModel)'.")
    } elseif ([int]$Contract.RegistryModel -ne $RequestedModel) {
        $blockers.Add("CLI model '$RequestedModel' does not match latest registry model '$($Contract.RegistryModel)'.")
    }
    if ($Contract.RegistrySourcePath -cne $Contract.CanonicalSourcePath) {
        $blockers.Add("Latest registry source_path is not canonical; expected '$($Contract.CanonicalSourcePath)', got '$($Contract.RegistrySourcePath)'.")
    }
    if ([string]::IsNullOrWhiteSpace($Contract.CurrentSourceSha256)) {
        $blockers.Add("Canonical EA source is missing: $($Contract.CanonicalSourceAbsolute)")
    } elseif ([string]::IsNullOrWhiteSpace($Contract.RegistrySourceHash)) {
        $blockers.Add("Latest registry row has no source SHA256.")
    } elseif ($Contract.CurrentSourceSha256 -ine $Contract.RegistrySourceHash) {
        $blockers.Add("Current source SHA256 '$($Contract.CurrentSourceSha256)' does not match registry source SHA256 '$($Contract.RegistrySourceHash)'.")
    }
    if ([string]::IsNullOrWhiteSpace($Contract.RegisteredPreregPath) -or $Contract.RegisteredPreregPath -like 'not-created:*') {
        $blockers.Add("Latest registry row has no executable prereg_path.")
    } elseif ([string]::IsNullOrWhiteSpace($Contract.PreregSha256)) {
        $blockers.Add("Registered prereg file is missing: $($Contract.PreregPath)")
    }
    return @($blockers | ForEach-Object { $_ })
}

function Resolve-MatchedControl($RunId, $ControlHypothesisId, $ExpectedManifestHash, $ExpectedReportHash, $Contract, $Binding) {
    $blockers = New-Object System.Collections.Generic.List[string]
    $sidecarEvidence = New-Object System.Collections.Generic.List[object]
    $artifactEvidence = New-Object System.Collections.Generic.List[object]
    if ([string]::IsNullOrWhiteSpace($RunId)) {
        $blockers.Add("Task packet field 'matched_control_run_id' is required.")
    } elseif ($RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$') {
        $blockers.Add("Control run id contains unsupported characters or path traversal: $RunId")
    }
    if ([string]::IsNullOrWhiteSpace($ControlHypothesisId)) {
        $blockers.Add("Task packet field 'matched_control_hypothesis_id' is required.")
    } else {
        $registeredParent = [string](Get-ObjectProperty $Contract.LatestRow 'parent_candidate')
        if (($ControlHypothesisId -cne $Contract.HypothesisId) -and
            ([string]::IsNullOrWhiteSpace($registeredParent) -or $ControlHypothesisId -cne $registeredParent)) {
            $blockers.Add("Matched control hypothesis '$ControlHypothesisId' is neither the current hypothesis nor its explicitly registered parent '$registeredParent'.")
        }
    }
    if (-not (Test-Sha256Text $ExpectedManifestHash)) {
        $blockers.Add("Task packet field 'matched_control_manifest_sha256' must be a SHA256 value.")
    }
    if (-not (Test-Sha256Text $ExpectedReportHash)) {
        $blockers.Add("Task packet field 'matched_control_report_sha256' must be a SHA256 value.")
    }

    $runDir = $null
    $manifestPath = $null
    $reportPath = $null
    if ($RunId -match '^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$') {
        $runsRoot = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $alphaRoot "runs") $Binding.EaName)).TrimEnd('\')
        $runDir = [System.IO.Path]::GetFullPath((Join-Path $runsRoot $RunId))
        $runsPrefix = "$runsRoot\"
        if (-not $runDir.StartsWith($runsPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            $blockers.Add("Matched control path escapes the EA runs root: $runDir")
        } elseif (-not (Test-Path -LiteralPath $runDir -PathType Container)) {
            $blockers.Add("Matched control run directory is missing: $runDir")
        } else {
            $manifestPath = Join-Path $runDir "run_manifest.json"
            $reportPath = Join-Path $runDir "report.html"
            if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
                $blockers.Add("Matched control manifest is missing: $manifestPath")
            }
            if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
                $blockers.Add("Matched control report is missing: $reportPath")
            }
        }
    }

    $actualManifestHash = Get-Sha256IfExists $manifestPath
    $actualReportHash = Get-Sha256IfExists $reportPath
    if (-not [string]::IsNullOrWhiteSpace($actualManifestHash) -and
        (Test-Sha256Text $ExpectedManifestHash) -and
        $actualManifestHash -ine $ExpectedManifestHash) {
        $blockers.Add("Matched control manifest SHA256 mismatch: expected '$ExpectedManifestHash', got '$actualManifestHash'.")
    }
    if (-not [string]::IsNullOrWhiteSpace($actualReportHash) -and
        (Test-Sha256Text $ExpectedReportHash) -and
        $actualReportHash -ine $ExpectedReportHash) {
        $blockers.Add("Matched control report SHA256 mismatch: expected '$ExpectedReportHash', got '$actualReportHash'.")
    }

    if (-not [string]::IsNullOrWhiteSpace($actualManifestHash)) {
        try {
            $controlManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            $expectedFields = [ordered]@{
                ea_name = $Binding.EaName
                hypothesis_id = $ControlHypothesisId
                run_role = 'control'
                symbol = $Binding.Symbol
                period = $Binding.Period
                from = $Binding.From
                to = $Binding.To
                model = $Binding.Model
                execution_mode = $Binding.ExecutionMode
                fixed_delay_ms = $Binding.FixedDelayMs
                overrides = $Binding.ControlOverrides
                deposit = $Binding.Deposit
                leverage = $Binding.Leverage
                spread = $Binding.Spread
                source_sha256 = $Binding.ControlSourceSha256
                config_sha256 = $Binding.ControlConfigSha256
                ex5_sha256 = $Binding.ControlEx5Sha256
                tester_ex5_sha256 = $Binding.ControlEx5Sha256
                includes_sha256 = $Binding.ControlIncludesSha256
                report_sha256 = $ExpectedReportHash
                git_commit = $Binding.ControlGitCommit
                git_status_sha256 = $Binding.ControlGitStatusSha256
                broker_fingerprint = $Binding.BrokerFingerprint
                server_fingerprint = $Binding.ServerFingerprint
                account_fingerprint = $Binding.AccountFingerprint
                data_fingerprint = $Binding.DataFingerprint
                required_sidecars = @($Binding.RequiredSidecars)
            }
            foreach ($field in $expectedFields.Keys) {
                $actual = Get-ObjectProperty $controlManifest $field
                $expected = $expectedFields[$field]
                if ($field -in @('model', 'execution_mode', 'fixed_delay_ms', 'deposit', 'leverage')) {
                    if (-not (Test-IntegerValue $actual) -or [int64]$actual -ne [int64]$expected) {
                        $blockers.Add("Matched control manifest field '$field' does not match '$expected'.")
                    }
                } elseif ($field -eq 'required_sidecars') {
                    $actualList = @($actual | ForEach-Object { [string]$_ } | Sort-Object)
                    $expectedList = @($expected | ForEach-Object { [string]$_ } | Sort-Object)
                    if ([string]::Join("`n", $actualList) -cne [string]::Join("`n", $expectedList)) {
                        $blockers.Add("Matched control manifest field 'required_sidecars' does not match the task packet.")
                    }
                } elseif ($field -match 'sha256$|_fingerprint$') {
                    if (-not (Test-Sha256Text $actual) -or [string]$actual -ine [string]$expected) {
                        $blockers.Add("Matched control manifest field '$field' does not match bound identity '$expected'.")
                    }
                } elseif ([string]$actual -cne [string]$expected) {
                    $blockers.Add("Matched control manifest field '$field' does not match '$expected'.")
                }
            }

            $researchLoopAttestation = Get-ObjectProperty $controlManifest 'research_loop'
            if ($null -eq $researchLoopAttestation -or $researchLoopAttestation -isnot [pscustomobject]) {
                $blockers.Add("Matched control completion attestation is missing from research_loop.")
            } else {
                if ([string](Get-ObjectProperty $researchLoopAttestation 'schema_version') -notin @('alphafactory_research_loop_manifest.v1', 'sonic_research_loop_manifest.v3') -or
                    [string](Get-ObjectProperty $researchLoopAttestation 'run_role') -cne 'control') {
                    $blockers.Add("Matched control completion attestation has invalid schema or run_role.")
                }
                $controlTransitions = @(Get-ObjectProperty $researchLoopAttestation 'state_transitions')
                $terminalTransition = if ($controlTransitions.Count -gt 0) { $controlTransitions[$controlTransitions.Count - 1] } else { $null }
                $failedTransitions = @($controlTransitions | Where-Object { [string](Get-ObjectProperty $_ 'state') -ceq 'failed' })
                if ($null -eq $terminalTransition -or
                    [string](Get-ObjectProperty $terminalTransition 'state') -cne 'completed' -or
                    $failedTransitions.Count -gt 0) {
                    $blockers.Add("Matched control completion attestation is not a clean terminal 'completed' transition.")
                }

                $completionEvidence = Get-ObjectProperty $researchLoopAttestation 'evidence'
                $completionRunRoot = [System.IO.Path]::GetFullPath($runDir).TrimEnd('\')
                $completionRunPrefix = "$completionRunRoot\"
                $completionArtifacts = [ordered]@{
                    verified_cost_artifact = @('cost_artifact_path', 'cost_artifact_sha256')
                    validation_summary = @('validation_summary_path', 'validation_summary_sha256')
                    research_loop_summary = @('research_loop_summary_path', 'research_loop_summary_sha256')
                }
                foreach ($artifactName in $completionArtifacts.Keys) {
                    $fieldNames = $completionArtifacts[$artifactName]
                    $completionPath = [string](Get-ObjectProperty $completionEvidence $fieldNames[0])
                    $completionHash = [string](Get-ObjectProperty $completionEvidence $fieldNames[1])
                    if ([string]::IsNullOrWhiteSpace($completionPath) -or -not (Test-Sha256Text $completionHash)) {
                        $blockers.Add("Matched control completion artifact '$artifactName' path/hash is missing.")
                        continue
                    }
                    $resolvedCompletionPath = [System.IO.Path]::GetFullPath($completionPath)
                    if (-not $resolvedCompletionPath.StartsWith($completionRunPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                        $blockers.Add("Matched control completion artifact '$artifactName' escapes the control run directory.")
                        continue
                    }
                    $actualCompletionHash = Get-Sha256IfExists $resolvedCompletionPath
                    if ($actualCompletionHash -ine $completionHash) {
                        $blockers.Add("Matched control completion artifact '$artifactName' hash mismatch.")
                        continue
                    }
                    $artifactEvidence.Add([pscustomobject]@{
                        Path = $resolvedCompletionPath
                        Sha256 = $actualCompletionHash
                        Kind = $artifactName
                    })
                }
            }

            $controlArtifacts = [ordered]@{
                source_sha256 = [string](Get-ObjectProperty $controlManifest 'source_snapshot')
                config_sha256 = [string](Get-ObjectProperty $controlManifest 'config_snapshot')
                ex5_sha256 = [string](Get-ObjectProperty $controlManifest 'ex5_snapshot')
                tester_ex5_sha256 = [string](Get-ObjectProperty $controlManifest 'tester_ex5_path')
                report_sha256 = $reportPath
            }
            foreach ($hashField in $controlArtifacts.Keys) {
                $artifactPath = $controlArtifacts[$hashField]
                if ([string]::IsNullOrWhiteSpace($artifactPath) -or -not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
                    $blockers.Add("Matched control artifact for '$hashField' is missing: $artifactPath")
                    continue
                }
                $artifactHash = Get-Sha256IfExists $artifactPath
                if ($artifactHash -ine [string](Get-ObjectProperty $controlManifest $hashField)) {
                    $blockers.Add("Matched control artifact '$hashField' does not match its manifest hash.")
                } else {
                    $artifactEvidence.Add([pscustomobject]@{ Path = $artifactPath; Sha256 = $artifactHash; Kind = $hashField })
                }
            }
            try {
                $controlIncludesHash = Get-ManifestIncludeSetSha256 $controlManifest
                if ($controlIncludesHash -ine [string](Get-ObjectProperty $controlManifest 'includes_sha256')) {
                    $blockers.Add("Matched control artifact 'includes_sha256' does not match its manifest hash.")
                } else {
                    foreach ($includeSnapshot in @(Get-ObjectProperty $controlManifest 'include_snapshots')) {
                        $includeSnapshotPath = [string](Get-ObjectProperty $includeSnapshot 'snapshot_path')
                        $includeSnapshotHash = Get-Sha256IfExists $includeSnapshotPath
                        $artifactEvidence.Add([pscustomobject]@{ Path = $includeSnapshotPath; Sha256 = $includeSnapshotHash; Kind = 'include_snapshot' })
                    }
                }
            } catch {
                $blockers.Add("Matched control include closure is invalid: $($_.Exception.Message)")
            }
            $controlSidecars = @(Get-ObjectProperty $controlManifest 'sidecars')
            $controlRunRoot = [System.IO.Path]::GetFullPath($runDir).TrimEnd('\')
            $controlRunPrefix = "$controlRunRoot\"
            foreach ($sidecar in $controlSidecars) {
                $relativeSidecar = ([string](Get-ObjectProperty $sidecar 'path')).Replace('/', '\')
                if ([string]::IsNullOrWhiteSpace($relativeSidecar)) {
                    $blockers.Add("Matched control manifest has a sidecar with no path.")
                    continue
                }
                $sidecarPath = [System.IO.Path]::GetFullPath((Join-Path $controlRunRoot $relativeSidecar))
                if (-not $sidecarPath.StartsWith($controlRunPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                    $blockers.Add("Matched control sidecar escapes the control run directory: $relativeSidecar")
                    continue
                }
                $expectedSidecarHash = [string](Get-ObjectProperty $sidecar 'sha256')
                $actualSidecarHash = Get-Sha256IfExists $sidecarPath
                if (-not (Test-Sha256Text $expectedSidecarHash) -or $actualSidecarHash -ine $expectedSidecarHash) {
                    $blockers.Add("Matched control sidecar hash mismatch: $relativeSidecar")
                    continue
                }
                $sidecarEvidence.Add([pscustomobject]@{
                    Path = $sidecarPath
                    Sha256 = $actualSidecarHash
                    RelativePath = $relativeSidecar.Replace('\', '/')
                })
            }
            foreach ($pattern in @($Binding.RequiredSidecars)) {
                $sidecarMatch = @($controlSidecars | Where-Object { (Split-Path -Leaf ([string](Get-ObjectProperty $_ 'path'))) -like $pattern })
                if ($sidecarMatch.Count -eq 0) {
                    $blockers.Add("Matched control manifest sidecars do not satisfy required pattern '$pattern'.")
                }
            }
        } catch {
            $blockers.Add("Matched control manifest JSON is malformed: $($_.Exception.Message)")
        }
    }

    return [pscustomobject]@{
        RunId = $RunId
        HypothesisId = $ControlHypothesisId
        RunDir = $runDir
        ManifestPath = $manifestPath
        ManifestSha256 = $actualManifestHash
        ReportPath = $reportPath
        ReportSha256 = $actualReportHash
        Sidecars = @($sidecarEvidence | ForEach-Object { $_ })
        Artifacts = @($artifactEvidence | ForEach-Object { $_ })
        Blockers = @($blockers | ForEach-Object { $_ })
    }
}

function Add-PacketMismatch($Blockers, $Packet, $Field, $Expected, [switch]$Integer, [switch]$Hash) {
    $actual = Get-ObjectProperty $Packet $Field
    if ($null -eq $actual -or ([string]$actual).Length -eq 0) {
        $Blockers.Add("Task packet field '$Field' is required.")
        return
    }
    if ($Integer) {
        if (-not (Test-IntegerValue $actual) -or [int64]$actual -ne [int64]$Expected) {
            $Blockers.Add("Task packet field '$Field' does not match CLI value '$Expected'.")
        }
        return
    }
    if ($Hash) {
        if ([string]$actual -ine [string]$Expected) {
            $Blockers.Add("Task packet field '$Field' does not match verified SHA256 '$Expected'.")
        }
        return
    }
    if ([string]$actual -cne [string]$Expected) {
        $Blockers.Add("Task packet field '$Field' does not match CLI value '$Expected'.")
    }
}

function Resolve-EconomicWindow($Packet, $Binding, [bool]$Required, $Blockers) {
    $node = Get-ObjectProperty $Packet 'economic_window'
    if ($null -eq $node) {
        if ($Required) {
            $Blockers.Add("RESEARCH_PROXY task packet requires an explicit economic_window distinct from tester preload when applicable.")
        }
        return [pscustomobject]@{ From = [string]$Binding.From; To = [string]$Binding.To }
    }
    if (-not (Test-ProvenanceObject $node)) {
        $Blockers.Add("Task packet economic_window must be an object.")
        return [pscustomobject]@{ From = ''; To = '' }
    }
    $names = @($node.PSObject.Properties | ForEach-Object { $_.Name })
    if ($names.Count -ne 2 -or 'from' -notin $names -or 'to' -notin $names) {
        $Blockers.Add("Task packet economic_window must contain exactly 'from' and 'to'.")
    }
    $economicFrom = [string](Get-ObjectProperty $node 'from')
    $economicTo = [string](Get-ObjectProperty $node 'to')
    try {
        $testerFrom = [datetime]::ParseExact([string]$Binding.From, 'yyyy.MM.dd', [Globalization.CultureInfo]::InvariantCulture)
        $testerTo = [datetime]::ParseExact([string]$Binding.To, 'yyyy.MM.dd', [Globalization.CultureInfo]::InvariantCulture)
        $parsedFrom = [datetime]::ParseExact($economicFrom, 'yyyy.MM.dd', [Globalization.CultureInfo]::InvariantCulture)
        $parsedTo = [datetime]::ParseExact($economicTo, 'yyyy.MM.dd', [Globalization.CultureInfo]::InvariantCulture)
        if ($parsedFrom -gt $parsedTo) {
            $Blockers.Add("Task packet economic_window.from must be on or before economic_window.to.")
        }
        if ($parsedFrom -lt $testerFrom -or $parsedTo -gt $testerTo) {
            $Blockers.Add("Task packet economic_window must be contained within the tester preload window.")
        }
    } catch {
        $Blockers.Add("Task packet economic_window dates must use yyyy.MM.dd.")
    }
    return [pscustomobject]@{ From = $economicFrom; To = $economicTo }
}

function Resolve-BaselineAcceptanceContract($Packet, [bool]$Required, $Blockers) {
    $node = Get-ObjectProperty $Packet 'baseline_acceptance_contract'
    if ($null -eq $node) {
        if ($Required) {
            $Blockers.Add("RESEARCH_PROXY task packet requires baseline_acceptance_contract.")
        }
        return $null
    }
    $fields = @(
        'min_completed_trades', 'min_direction_share', 'max_year_trade_share',
        'require_positive_cost_expectancy', 'require_all_calendar_years_positive'
    )
    if (-not (Test-ProvenanceObject $node)) {
        $Blockers.Add("Task packet baseline_acceptance_contract must be an object.")
        return $null
    }
    $names = @($node.PSObject.Properties | ForEach-Object { $_.Name })
    if ($names.Count -ne $fields.Count -or @($names | Where-Object { $_ -notin $fields }).Count -gt 0) {
        $Blockers.Add("Task packet baseline_acceptance_contract must contain exactly the five supported fields.")
    }
    $minimumTrades = Get-ObjectProperty $node 'min_completed_trades'
    $minimumSide = Get-ObjectProperty $node 'min_direction_share'
    $maximumYear = Get-ObjectProperty $node 'max_year_trade_share'
    if (-not (Test-PositiveInteger $minimumTrades)) {
        $Blockers.Add("baseline_acceptance_contract.min_completed_trades must be a positive integer.")
    }
    if (-not (Test-NonNegativeNumber $minimumSide) -or [double]$minimumSide -gt 0.5) {
        $Blockers.Add("baseline_acceptance_contract.min_direction_share must be between 0 and 0.5.")
    }
    if (-not (Test-NonNegativeNumber $maximumYear) -or [double]$maximumYear -le 0 -or [double]$maximumYear -gt 1) {
        $Blockers.Add("baseline_acceptance_contract.max_year_trade_share must be greater than 0 and at most 1.")
    }
    if ((Get-ObjectProperty $node 'require_positive_cost_expectancy') -ne $true -or
        (Get-ObjectProperty $node 'require_all_calendar_years_positive') -ne $true) {
        $Blockers.Add("Baseline expectancy and every-calendar-year positivity requirements must both be true.")
    }
    return $node
}

function Resolve-ExecutionAuthority($Packet, $Binding, $Blockers) {
    $exactProperty = @($Packet.PSObject.Properties | Where-Object { $_.Name -ceq 'authority' })
    $caseFoldedProperty = @($Packet.PSObject.Properties | Where-Object { $_.Name -ieq 'authority' })
    if ($exactProperty.Count -eq 0) {
        if ($caseFoldedProperty.Count -gt 0) {
            $Blockers.Add("Task packet authority field must be exactly case-sensitive 'authority'.")
        }
        return ''
    }
    if ($exactProperty.Count -ne 1) {
        $Blockers.Add("Task packet must contain at most one exact 'authority' field.")
        return ''
    }

    $authority = [string]$exactProperty[0].Value
    if ([string]::IsNullOrWhiteSpace($authority)) {
        return ''
    }
    if ($authority -notin @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )) {
        $Blockers.Add("Task packet authority '$authority' is unsupported.")
        return ''
    }
    if ([string]$Binding.RunRole -cne 'control') {
        $Blockers.Add("Data-acquisition authority requires RunRole=control.")
    }
    $expectedModel = if ($authority -ceq 'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE') { 0 } else { 4 }
    if ([int]$Binding.Model -ne $expectedModel) {
        $Blockers.Add("Data-acquisition authority '$authority' requires MT5 Model=$expectedModel.")
    }
    if ([string]$Binding.TelemetryProfile -cne 'none' -or [string]$Binding.TelemetryTier -cne 'off') {
        $Blockers.Add("Data-acquisition authority requires telemetry_profile='none' and TelemetryTier=off.")
    }
    if ([bool]$Binding.AllowResearchCostProxy) {
        $Blockers.Add("Data-acquisition authority forbids research cost proxy mode.")
    }
    if ($null -eq $Binding.DataQualityContract) {
        $Blockers.Add("Data-acquisition authority requires a valid data_quality_contract.")
    }
    return $authority
}

function Resolve-CollectionCostManifest($Manifest, [string]$Authority, $Binding, $Blockers) {
    $collectionCostKeys = @(
        'schema_version', 'evidence_tier', 'provenance_status', 'audit_status', 'verdict',
        'promotion_eligible', 'performance_metrics_authorized', 'economics_authorized',
        'authority', 'epoch_manifest_path', 'epoch_manifest_sha256', 'note'
    )
    if (-not (Test-ExactObjectKeys $Manifest $collectionCostKeys)) {
        $Blockers.Add("Data-acquisition cost manifest must contain exactly the collection-only schema fields.")
    }
    if ([string](Get-ObjectProperty $Manifest 'schema_version') -cne 'alphafactory_cost_source_manifest.v1' -or
        [string](Get-ObjectProperty $Manifest 'evidence_tier') -cne 'DATA_ACQUISITION_ONLY' -or
        [string](Get-ObjectProperty $Manifest 'provenance_status') -cne 'UNVERIFIED' -or
        [string](Get-ObjectProperty $Manifest 'audit_status') -cne 'NOT_APPLICABLE' -or
        [string](Get-ObjectProperty $Manifest 'verdict') -cne 'NO_ECONOMIC_AUTHORITY' -or
        [string](Get-ObjectProperty $Manifest 'authority') -cne $Authority) {
        $Blockers.Add("Data-acquisition cost manifest identity/status contract is invalid.")
    }
    if ((Get-ObjectProperty $Manifest 'promotion_eligible') -ne $false -or
        (Get-ObjectProperty $Manifest 'performance_metrics_authorized') -ne $false -or
        (Get-ObjectProperty $Manifest 'economics_authorized') -ne $false) {
        $Blockers.Add("Data-acquisition cost manifest must forbid promotion, performance metrics, and economics.")
    }
    if ([string]::IsNullOrWhiteSpace([string](Get-ObjectProperty $Manifest 'note'))) {
        $Blockers.Add("Data-acquisition cost manifest note must explicitly preserve unverified-cost status.")
    }
    $epochEvidence = Resolve-CostEvidenceFile `
        (Get-ObjectProperty $Manifest 'epoch_manifest_path') `
        (Get-ObjectProperty $Manifest 'epoch_manifest_sha256') `
        'data_acquisition_epoch_manifest' $Blockers
    if ($null -eq $epochEvidence) {
        return $null
    }
    try {
        $epochManifest = Get-Content -LiteralPath $epochEvidence.Path -Raw | ConvertFrom-Json
    } catch {
        $Blockers.Add("Data-acquisition epoch manifest is malformed JSON: $($_.Exception.Message)")
        return $null
    }
    $epochServer = [string](Get-ObjectProperty $epochManifest 'server')
    $epochPeriod = [string](Get-ObjectProperty $epochManifest 'timeframe')
    $epochModel = Get-ObjectProperty $epochManifest 'tester_model'
    if ([string]::IsNullOrWhiteSpace($epochServer)) {
        $Blockers.Add("Data-acquisition epoch manifest server is required.")
    }
    if ($epochPeriod -cne [string]$Binding.Period) {
        $Blockers.Add(
            "Data-acquisition epoch manifest timeframe '$epochPeriod' does not match task packet period '$($Binding.Period)'."
        )
    }
    if (-not (Test-IntegerValue $epochModel) -or [int]$epochModel -ne [int]$Binding.Model) {
        $Blockers.Add(
            "Data-acquisition epoch manifest tester_model '$epochModel' does not match task packet model '$($Binding.Model)'."
        )
    }
    return [pscustomobject]@{
        Evidence = $epochEvidence
        Server = $epochServer
        Period = $epochPeriod
    }
}

function Add-Model4CollectionSourceEpochBlockers($Contract, $Binding, $Manifest, $Blockers) {
    $epochSha = [string](Get-ObjectProperty $Manifest 'epoch_manifest_sha256')
    if ($epochSha -notmatch '^[A-F0-9]{64}$') {
        $Blockers.Add("Model4 collection epoch manifest SHA must be uppercase SHA256.")
        return
    }
    try {
        $overrideMap = ConvertTo-NormalizedOverrideMap ([string]$Binding.Overrides)
    } catch {
        $Blockers.Add("Model4 collection overrides are invalid: $($_.Exception.Message)")
        return
    }
    if (-not $overrideMap.Contains('InpEpochManifestSha256') -or
        [string]$overrideMap['InpEpochManifestSha256'] -cne $epochSha) {
        $Blockers.Add("Model4 collection override InpEpochManifestSha256 must equal the hash-bound epoch manifest.")
    }
    $sourcePath = [string]$Contract.CanonicalSourceAbsolute
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        $Blockers.Add("Model4 collection canonical source is missing: $sourcePath")
        return
    }
    $sourceText = Get-Content -LiteralPath $sourcePath -Raw
    $epochOccurrences = [regex]::Matches($sourceText, [regex]::Escape($epochSha)).Count
    if ($epochOccurrences -ne 2) {
        $Blockers.Add(
            "Model4 collection source must bind the epoch manifest SHA exactly twice " +
            "(input default and fail-closed Configure comparison); found $epochOccurrences."
        )
    }
}

function Test-ScopedModel4PriorRegistryPacket($Packet, $Contract, $Binding, $PacketPath) {
    if ([string](Get-ObjectProperty $Packet 'authority') -cne 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        return $false
    }
    if (
        [int]$Binding.Model -ne 4 -or
        [string]$Binding.RunRole -cne 'control' -or
        [string]$Binding.Symbol -cne 'XAUUSD' -or
        [string]$Contract.RegistryState -cne 'screened'
    ) {
        return $false
    }
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    if (-not (Test-ProvenanceObject $validation)) {
        return $false
    }
    $packetRelativePath = Get-RepoRelativePath $PacketPath
    $packetSha256 = Get-Sha256IfExists $PacketPath
    return (
        [string](Get-ObjectProperty $validation 'probe_status') -ceq
            'SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED' -and
        (Get-ObjectProperty $validation 'task_packets_created') -eq $true -and
        (Get-ObjectProperty $validation 'task_packet_authorized_next') -eq $false -and
        (Get-ObjectProperty $validation 'xau_model4_collection_launch_authorized') -eq $true -and
        (Get-ObjectProperty $validation 'mt5_data_collection_authorized') -eq $true -and
        (Get-ObjectProperty $validation 'model4_data_collection_authorized') -eq $true -and
        (Get-ObjectProperty $validation 'mt5_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'model4_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'trading_backtest_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'trades_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'performance_metrics_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'economics_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'optimization_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'validation_access_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'holdout_access_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'promotion_eligible') -eq $false -and
        (Get-ObjectProperty $validation 'paper_trading_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'live_trading_authorized') -eq $false -and
        (Get-ObjectProperty $validation 'market_edge_claim_authorized') -eq $false -and
        [string](Get-ObjectProperty $validation 'authorized_symbol') -ceq 'XAUUSD' -and
        [int](Get-ObjectProperty $validation 'authorized_symbol_order_index') -eq 0 -and
        [int](Get-ObjectProperty $validation 'authorized_launch_limit') -eq 1 -and
        [int](Get-ObjectProperty $validation 'authorized_launches_consumed') -eq 0 -and
        [string](Get-ObjectProperty $validation 'xau_task_packet_path') -ceq
            $packetRelativePath -and
        [string](Get-ObjectProperty $validation 'xau_task_packet_sha256') -ceq
            $packetSha256 -and
        [string](Get-ObjectProperty $validation 'authorized_packet_registry_sha256') -ceq
            [string](Get-ObjectProperty $Packet 'registry_sha256') -and
        [string](Get-ObjectProperty $validation 'authorized_packet_registry_row_sha256') -ceq
            [string](Get-ObjectProperty $Packet 'registry_row_sha256') -and
        [string](Get-ObjectProperty $validation 'authorized_packet_git_status_sha256') -ceq
            [string](Get-ObjectProperty $Packet 'git_status_sha256') -and
        [int](Get-ObjectProperty $validation 'execute_gate_prior_registry_line') -eq
            ([int]$Contract.RegistryLine - 1) -and
        (Test-Sha256Text ([string](Get-ObjectProperty $validation 'execute_gate_prior_registry_sha256'))) -and
        (Test-Sha256Text ([string](Get-ObjectProperty $validation 'execute_gate_prior_registry_row_sha256'))) -and
        [string](Get-ObjectProperty $validation 'authorized_current_git_status_sha256') -ceq
            [string]$Binding.GitStatusSha256
    )
}

function Test-ScopedModel0EconomicPriorRegistryPacket($Packet, $Contract, $Binding, $PacketPath) {
    if (-not [string]::IsNullOrWhiteSpace([string](Get-ObjectProperty $Packet 'authority'))) {
        return $false
    }
    if (
        [int]$Binding.Model -ne 0 -or
        [string]$Binding.RunRole -cne 'control' -or
        [string]$Contract.RegistryState -cne 'screened'
    ) {
        return $false
    }
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    $metrics = Get-ObjectProperty $Contract.LatestRow 'metrics'
    if (-not (Test-ProvenanceObject $validation) -or -not (Test-ProvenanceObject $metrics)) {
        return $false
    }
    $packetRelativePath = Get-RepoRelativePath $PacketPath
    $packetSha256 = Get-Sha256IfExists $PacketPath
    return (
        [string](Get-ObjectProperty $validation 'authority') -ceq 'MODEL0_TRAIN_FALSIFICATION_ONLY' -and
        [string](Get-ObjectProperty $validation 'one_shot_economic_harness_version') -ceq 'model0-economic-one-shot-v1' -and
        [string](Get-ObjectProperty $validation 'probe_status') -ceq 'SCREENED_STBS013_ONE_SHOT_PACKET_BOUND_MODEL0_BASELINE_AUTHORIZED' -and
        (Get-ObjectProperty $validation 'mt5_train_run_authorized') -eq $true -and
        [string](Get-ObjectProperty $validation 'mt5_attempt_id') -ceq [string](Get-ObjectProperty $Packet 'attempt_id') -and
        [int](Get-ObjectProperty $validation 'mt5_attempt_limit') -eq 1 -and
        [int](Get-ObjectProperty $Packet 'attempt_limit') -eq 1 -and
        [int](Get-ObjectProperty $metrics 'mt5_attempts_consumed') -eq 0 -and
        (Get-ObjectProperty $validation 'same_id_retry_authorized') -eq $false -and
        [int](Get-ObjectProperty $validation 'authorized_timeout_sec') -eq [int]$Binding.TimeoutSec -and
        [int](Get-ObjectProperty $Packet 'timeout_sec') -eq [int]$Binding.TimeoutSec -and
        [string](Get-ObjectProperty $validation 'task_packet_path') -ceq $packetRelativePath -and
        [string](Get-ObjectProperty $validation 'task_packet_sha256') -ceq $packetSha256 -and
        [string](Get-ObjectProperty $validation 'authorized_packet_registry_sha256') -ceq
            [string](Get-ObjectProperty $Packet 'registry_sha256') -and
        [string](Get-ObjectProperty $validation 'authorized_packet_registry_row_sha256') -ceq
            [string](Get-ObjectProperty $Packet 'registry_row_sha256') -and
        [string](Get-ObjectProperty $validation 'authorized_packet_git_status_sha256') -ceq
            [string](Get-ObjectProperty $Packet 'git_status_sha256') -and
        [int](Get-ObjectProperty $validation 'execute_gate_prior_registry_line') -eq
            ([int]$Contract.RegistryLine - 1) -and
        (Test-Sha256Text ([string](Get-ObjectProperty $validation 'execute_gate_prior_registry_sha256'))) -and
        (Test-Sha256Text ([string](Get-ObjectProperty $validation 'execute_gate_prior_registry_row_sha256'))) -and
        [string](Get-ObjectProperty $validation 'authorized_current_git_status_sha256') -ceq
            [string]$Binding.GitStatusSha256
    )
}

function Get-Model4ControlPlaneBinding([string]$RunnerPath) {
    $runner = [System.IO.Path]::GetFullPath($RunnerPath)
    $tools = Split-Path -Parent $runner
    $alpha = Split-Path -Parent $tools
    $root = Split-Path -Parent $alpha
    return [pscustomobject]@{
        RunnerPath = $runner
        RunnerSha256 = Get-Sha256IfExists $runner
        ValidatorPath = [System.IO.Path]::GetFullPath((Join-Path $root '04. Memory\research\validate_candidate_registry.py'))
        ValidatorSha256 = Get-Sha256IfExists (Join-Path $root '04. Memory\research\validate_candidate_registry.py')
        AlphaPath = [System.IO.Path]::GetFullPath((Join-Path $alpha 'alpha.ps1'))
        AlphaSha256 = Get-Sha256IfExists (Join-Path $alpha 'alpha.ps1')
    }
}

function Get-Model4ExecutionDependencyBindings([string]$RunnerPath) {
    $runner = [System.IO.Path]::GetFullPath($RunnerPath)
    $tools = Split-Path -Parent $runner
    $alpha = Split-Path -Parent $tools
    $root = Split-Path -Parent $alpha
    $relativePaths = @(
        '02. AlphaFactory/alpha.ps1',
        '02. AlphaFactory/tools/mt5_storage_contract.ps1',
        '02. AlphaFactory/tools/ea_contract.ps1',
        '02. AlphaFactory/tools/log_storage.ps1',
        '02. AlphaFactory/tools/audit_mql5_nonrepaint.py'
    )
    return @(
        foreach ($relativePath in $relativePaths) {
            $absolutePath = [System.IO.Path]::GetFullPath((Join-Path $root ($relativePath.Replace('/', '\'))))
            [pscustomobject]@{
                path = $relativePath
                absolute_path = $absolutePath
                sha256 = Get-Sha256IfExists $absolutePath
            }
        }
    )
}

function Test-Model4ExecutionDependencyBindings($CandidateBindings, $ExpectedBindings, $Blockers, [string]$Label) {
    $candidate = @($CandidateBindings)
    $expected = @($ExpectedBindings)
    if ($candidate.Count -ne $expected.Count) {
        $Blockers.Add("Model4 collection $Label execution_dependency_bindings count is invalid.")
        return $false
    }
    $ok = $true
    for ($i = 0; $i -lt $expected.Count; $i++) {
        $candidateItem = $candidate[$i]
        $expectedItem = $expected[$i]
        if (-not (Test-ExactObjectKeys $candidateItem @('path', 'sha256'))) {
            $Blockers.Add("Model4 collection $Label execution_dependency_bindings[$i] schema is malformed.")
            $ok = $false
            continue
        }
        $actualSha = Get-Sha256IfExists ([string]$expectedItem.absolute_path)
        if ([string](Get-ObjectProperty $candidateItem 'path') -cne [string]$expectedItem.path -or
            [string](Get-ObjectProperty $candidateItem 'sha256') -cne [string]$expectedItem.sha256 -or
            -not (Test-Sha256Text $actualSha) -or
            $actualSha -ine [string]$expectedItem.sha256) {
            $Blockers.Add("Model4 collection $Label execution_dependency_bindings[$i] is stale or wrong.")
            $ok = $false
        }
    }
    return $ok
}

function Get-ExpectedModel4BoundTestRelativePaths {
    return @(
        '02. AlphaFactory/tests/test_ea_golden_path.py',
        '02. AlphaFactory/tests/test_nonrepaint_collection_probe.py',
        '03. EA Developer/EA_PTR_T2_DataEpochD0V3/tests/test_mql5_contract.py',
        '03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/test_append_t2_data_epoch_evidence.py',
        '03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/test_append_t2_data_epoch_model4_evidence.py',
        '03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/test_t2_d0_model4_wrappers.py',
        '03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/test_t2_d0_hyp005_wrappers.py',
        '04. Memory/research/tests/test_validate_data_epoch.py',
        '04. Memory/research/tests/test_validate_campaign_exposure.py',
        '04. Memory/research/tests/test_validate_candidate_registry_model4_collection.py'
    )
}

function Test-Model4BoundTestBindings($CandidateBindings, $Blockers, [string]$Label) {
    $expectedPaths = @(Get-ExpectedModel4BoundTestRelativePaths)
    $candidate = @($CandidateBindings)
    if ($candidate.Count -ne $expectedPaths.Count) {
        $Blockers.Add(
            "Model4 collection $Label bound_tests must contain exactly $($expectedPaths.Count) ordered bindings."
        )
        return $false
    }
    $ok = $true
    for ($i = 0; $i -lt $expectedPaths.Count; $i++) {
        $item = $candidate[$i]
        if (-not (Test-ExactObjectKeys $item @('path', 'sha256'))) {
            $Blockers.Add("Model4 collection $Label bound_tests[$i] schema is malformed.")
            $ok = $false
            continue
        }
        $path = [string](Get-ObjectProperty $item 'path')
        $expectedSha = [string](Get-ObjectProperty $item 'sha256')
        if ($path -cne $expectedPaths[$i] -or -not (Test-Sha256Text $expectedSha)) {
            $Blockers.Add("Model4 collection $Label bound_tests[$i] path/SHA is invalid.")
            $ok = $false
            continue
        }
        $actualSha = Get-Sha256IfExists (Resolve-EvidencePath $path)
        if (-not (Test-Sha256Text $actualSha) -or $actualSha -ine $expectedSha) {
            $Blockers.Add("Model4 collection $Label bound_tests[$i] is stale or missing.")
            $ok = $false
        }
    }
    return $ok
}

function Get-ExpectedModel4LaunchClaimRelativePath {
    return '03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/evidence/HYP-PTR-T2-DATA-EPOCH-D0-M5-005/HYP005_XAU_MODEL4_LAUNCH_CLAIM.json'
}

function Add-Model4ReceiptObjectBlockers($Object, [string[]]$ExpectedKeys, [string]$Label, $Blockers) {
    if (-not (Test-ExactObjectKeys $Object $ExpectedKeys)) {
        $Blockers.Add("Model4 collection hardening receipt $Label schema is malformed.")
        return $false
    }
    return $true
}

function Resolve-TaskPacket($TaskPacketPath, $Contract, $Binding) {
    $blockers = New-Object System.Collections.Generic.List[string]
    $costEvidence = New-Object System.Collections.Generic.List[object]
    $collectionServer = $null
    $collectionPeriod = $null
    if ([string]::IsNullOrWhiteSpace($TaskPacketPath)) {
        $blockers.Add("TaskPacket is required for -Execute.")
        return [pscustomobject]@{
            Present = $false
            Packet = $null
            PacketPath = $null
            PacketSha256 = $null
            CostSourceManifestPath = $null
            WfaArtifactPath = $null
            VariantsDir = $null
            ValidationStage = $null
            HoldingContract = $null
            AcceptanceContract = $null
            DataAcceptanceContract = $Contract.DataAcceptanceContract
            DataQualityContract = $null
            CostEvidenceTier = $null
            EconomicFrom = $null
            EconomicTo = $null
            BaselineAcceptanceContract = $null
            Authority = $null
            CollectionSymbol = $null
            CollectionPeriod = $null
            CollectionServer = $null
            MatchedControlRunId = $null
            MatchedControl = $null
            IncludeClosure = @()
            IncludeClosureSha256 = Get-PathHashSetSha256 @()
            RequiredSidecars = @()
            RequiredManifestHashes = @()
            CostEvidence = @()
            Blockers = @($blockers | ForEach-Object { $_ })
        }
    }

    $resolvedPacketPath = Resolve-EvidencePath $TaskPacketPath
    if (-not (Test-Path -LiteralPath $resolvedPacketPath -PathType Leaf)) {
        $blockers.Add("Task packet file is missing: $resolvedPacketPath")
        return [pscustomobject]@{
            Present = $true; Packet = $null; PacketPath = $resolvedPacketPath; PacketSha256 = $null
            CostSourceManifestPath = $null; WfaArtifactPath = $null; VariantsDir = $null
            ValidationStage = $null; HoldingContract = $null; MatchedControlRunId = $null
            AcceptanceContract = $null
            DataAcceptanceContract = $Contract.DataAcceptanceContract
            DataQualityContract = $null
            CostEvidenceTier = $null
            EconomicFrom = $null; EconomicTo = $null; BaselineAcceptanceContract = $null
            Authority = $null
            CollectionSymbol = $null; CollectionPeriod = $null; CollectionServer = $null
            MatchedControl = $null
            IncludeClosure = @(); IncludeClosureSha256 = Get-PathHashSetSha256 @()
            RequiredSidecars = @(); RequiredManifestHashes = @()
            CostEvidence = @()
            Blockers = @($blockers | ForEach-Object { $_ })
        }
    }

    try {
        $packet = Get-Content -LiteralPath $resolvedPacketPath -Raw | ConvertFrom-Json
    } catch {
        $blockers.Add("Task packet JSON is malformed: $($_.Exception.Message)")
        $packet = $null
    }
    if ($null -eq $packet) {
        return [pscustomobject]@{
            Present = $true; Packet = $null; PacketPath = $resolvedPacketPath
            PacketSha256 = Get-Sha256IfExists $resolvedPacketPath
            CostSourceManifestPath = $null; WfaArtifactPath = $null; VariantsDir = $null
            ValidationStage = $null; HoldingContract = $null; MatchedControlRunId = $null
            AcceptanceContract = $null
            DataAcceptanceContract = $Contract.DataAcceptanceContract
            DataQualityContract = $null
            CostEvidenceTier = $null
            EconomicFrom = $null; EconomicTo = $null; BaselineAcceptanceContract = $null
            Authority = $null
            CollectionSymbol = $null; CollectionPeriod = $null; CollectionServer = $null
            MatchedControl = $null
            IncludeClosure = @(); IncludeClosureSha256 = Get-PathHashSetSha256 @()
            RequiredSidecars = @(); RequiredManifestHashes = @()
            CostEvidence = @()
            Blockers = @($blockers | ForEach-Object { $_ })
        }
    }

    $taskPacketSchema = [string](Get-ObjectProperty $packet 'schema_version')
    if ($taskPacketSchema -cne 'alphafactory_research_task_packet.v1') {
        $blockers.Add("Task packet field 'schema_version' must be 'alphafactory_research_task_packet.v1'.")
    }
    Add-PacketMismatch $blockers $packet 'hypothesis_id' $Contract.HypothesisId
    Add-PacketMismatch $blockers $packet 'run_role' $Binding.RunRole
    Add-PacketMismatch $blockers $packet 'ea_name' $Binding.EaName
    Add-PacketMismatch $blockers $packet 'source_path' $Contract.CanonicalSourcePath
    Add-PacketMismatch $blockers $packet 'source_sha256' $Contract.CurrentSourceSha256 -Hash
    Add-PacketMismatch $blockers $packet 'registry_path' (Get-RepoRelativePath $Contract.RegistryPath)
    $scopedPriorRegistryPacket = (
        (Test-ScopedModel4PriorRegistryPacket $packet $Contract $Binding $resolvedPacketPath) -or
        (Test-ScopedModel0EconomicPriorRegistryPacket $packet $Contract $Binding $resolvedPacketPath)
    )
    if ($scopedPriorRegistryPacket) {
        $scopedValidation = Get-ObjectProperty $Contract.LatestRow 'validation'
        Add-PacketMismatch $blockers $packet 'registry_sha256' `
            (Get-ObjectProperty $scopedValidation 'authorized_packet_registry_sha256') -Hash
        Add-PacketMismatch $blockers $packet 'registry_row_sha256' `
            (Get-ObjectProperty $scopedValidation 'authorized_packet_registry_row_sha256') -Hash
    } else {
        Add-PacketMismatch $blockers $packet 'registry_sha256' $Contract.RegistrySha256 -Hash
        Add-PacketMismatch $blockers $packet 'registry_row_sha256' $Contract.RegistryRowSha256 -Hash
    }
    Add-PacketMismatch $blockers $packet 'prereg_path' $Contract.RegisteredPreregPath
    Add-PacketMismatch $blockers $packet 'prereg_sha256' $Contract.PreregSha256 -Hash
    Add-PacketMismatch $blockers $packet 'telemetry_profile' $Contract.TelemetryProfile
    Add-PacketMismatch $blockers $packet 'comparison_adapter' $Contract.ComparisonAdapter
    $packetAuthority = [string](Get-ObjectProperty $packet 'authority')
    $isDataAcquisitionPacket = $packetAuthority -in @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )
    $useTieredDataContract = $isDataAcquisitionPacket -and
        [string]$Contract.EvidenceContractKind -ceq 'data_acquisition'
    $acceptanceFields = @(
        'min_profit_factor', 'min_trades_per_week', 'max_trades_per_week',
        'max_drawdown_pct', 'min_cost_pf_x1_5', 'min_cost_pf_x2',
        'max_monte_carlo_p95_dd_pct'
    )
    $packetAcceptance = Get-ObjectProperty $packet 'acceptance_contract'
    $registeredAcceptance = $Contract.AcceptanceContract
    if ($useTieredDataContract) {
        if ($null -ne $packet.PSObject.Properties['acceptance_contract']) {
            $blockers.Add("Tiered data-acquisition task packet must not carry economic acceptance_contract.")
        }
        $registeredAcceptance = $null
    } else {
        if (-not (Test-ProvenanceObject $registeredAcceptance)) {
            $blockers.Add("Latest registry row has no structured acceptance_contract.")
        }
        if (-not (Test-ProvenanceObject $packetAcceptance)) {
            $blockers.Add("Task packet field 'acceptance_contract' is required and must be an object.")
        }
    }
    if (-not $useTieredDataContract -and (Test-ProvenanceObject $packetAcceptance)) {
        $packetAcceptanceNames = @($packetAcceptance.PSObject.Properties | ForEach-Object { $_.Name })
        if ($packetAcceptanceNames.Count -ne $acceptanceFields.Count -or @($packetAcceptanceNames | Where-Object { $_ -notin $acceptanceFields }).Count -gt 0) {
            $blockers.Add("Task packet acceptance_contract must contain exactly the seven supported gate fields.")
        }
        foreach ($field in $acceptanceFields) {
            $packetValue = Get-ObjectProperty $packetAcceptance $field
            $registeredValue = Get-ObjectProperty $registeredAcceptance $field
            if (-not (Test-NonNegativeNumber $packetValue)) {
                $blockers.Add("Task packet acceptance_contract.$field must be a finite non-negative number.")
            } elseif (-not (Test-NonNegativeNumber $registeredValue) -or [double]$packetValue -ne [double]$registeredValue) {
                $blockers.Add("Task packet acceptance_contract.$field does not match the frozen registry value '$registeredValue'.")
            }
        }
    }
    $Binding | Add-Member -MemberType NoteProperty -Name AcceptanceContract -Value $registeredAcceptance -Force
    if (-not [string]::IsNullOrWhiteSpace($Contract.EaContractSha256)) {
        Add-PacketMismatch $blockers $packet 'ea_contract_path' $Contract.EaContractPath
        Add-PacketMismatch $blockers $packet 'ea_contract_sha256' $Contract.EaContractSha256 -Hash
    }
    $packetIndicatorProperty = $packet.PSObject.Properties['indicator_dependencies']
    $packetIndicatorDependencies = if ($null -eq $packetIndicatorProperty) { @() } else { @($packetIndicatorProperty.Value) }
    if ($null -eq $packetIndicatorProperty) {
        $blockers.Add("Task packet field 'indicator_dependencies' is required (use [] when the EA has none).")
    }
    try {
        $liveIndicatorRecords = @(Get-IndicatorDependencyBindingRecords $Binding.IndicatorDependencies)
        $packetIndicatorRecords = @(Get-IndicatorDependencyBindingRecords $packetIndicatorDependencies)
        if ([string]::Join("`n", $liveIndicatorRecords) -cne [string]::Join("`n", $packetIndicatorRecords)) {
            $blockers.Add("Task packet indicator_dependencies do not match the live EA capability contract and source hashes.")
        }
    } catch {
        $blockers.Add("Task packet indicator_dependencies are invalid: $($_.Exception.Message)")
    }
    Add-PacketMismatch $blockers $packet 'symbol' $Binding.Symbol
    Add-PacketMismatch $blockers $packet 'period' $Binding.Period
    Add-PacketMismatch $blockers $packet 'from' $Binding.From
    Add-PacketMismatch $blockers $packet 'to' $Binding.To
    Add-PacketMismatch $blockers $packet 'model' $Binding.Model -Integer
    Add-PacketMismatch $blockers $packet 'execution_mode' $Binding.ExecutionMode -Integer
    Add-PacketMismatch $blockers $packet 'fixed_delay_ms' $Binding.FixedDelayMs -Integer
    Add-PacketMismatch $blockers $packet 'timeout_sec' $Binding.TimeoutSec -Integer
    Add-PacketMismatch $blockers $packet 'overrides' $Binding.Overrides
    Add-PacketMismatch $blockers $packet 'telemetry_tier' $Binding.TelemetryTier
    Add-PacketMismatch $blockers $packet 'deposit' $Binding.Deposit -Integer
    Add-PacketMismatch $blockers $packet 'leverage' $Binding.Leverage -Integer
    Add-PacketMismatch $blockers $packet 'spread' $Binding.Spread
    Add-PacketMismatch $blockers $packet 'validation_stage' $Binding.ValidationStage
    Add-PacketMismatch $blockers $packet 'holding_contract' $Binding.HoldingContract
    Add-PacketMismatch $blockers $packet 'git_commit' $Binding.GitCommit
    if ($scopedPriorRegistryPacket) {
        Add-PacketMismatch $blockers $packet 'git_status_sha256' `
            (Get-ObjectProperty $scopedValidation 'authorized_packet_git_status_sha256') -Hash
    } else {
        Add-PacketMismatch $blockers $packet 'git_status_sha256' $Binding.GitStatusSha256 -Hash
    }

    $dataQualityContract = Resolve-DataQualityContract $packet $Binding $blockers
    $Binding | Add-Member -MemberType NoteProperty -Name DataQualityContract -Value $dataQualityContract -Force
    $authority = Resolve-ExecutionAuthority $packet $Binding $blockers
    if ($useTieredDataContract) {
        Add-RegisteredDataAcceptanceBlockers `
            $Contract.DataAcceptanceContract $dataQualityContract $Binding $blockers
    } elseif ($isDataAcquisitionPacket -and
        -not [string]::IsNullOrWhiteSpace([string]$Contract.EvidenceContractKind)) {
        $blockers.Add("Data-acquisition task packet requires evidence_contract_kind='data_acquisition'.")
    }

    $packetGitStatusProperty = $packet.PSObject.Properties['git_status']
    if ($null -eq $packetGitStatusProperty) {
        $blockers.Add("Task packet field 'git_status' is required.")
    } else {
        $packetGitStatus = @($packetGitStatusProperty.Value | ForEach-Object { [string]$_ })
        if (
            -not $scopedPriorRegistryPacket -and
            [string]::Join("`n", $packetGitStatus) -cne
                [string]::Join("`n", @($Binding.GitStatus))
        ) {
            $blockers.Add("Task packet field 'git_status' does not match current porcelain status.")
        }
    }

    $includeClosureProperty = $packet.PSObject.Properties['include_closure']
    $includeClosure = New-Object System.Collections.Generic.List[object]
    if ($null -eq $includeClosureProperty) {
        $blockers.Add("Task packet field 'include_closure' is required.")
    } else {
        foreach ($entry in @($includeClosureProperty.Value)) {
            $rawIncludePath = [string](Get-ObjectProperty $entry 'path')
            $expectedIncludeHash = [string](Get-ObjectProperty $entry 'sha256')
            if ([string]::IsNullOrWhiteSpace($rawIncludePath)) {
                $blockers.Add("Task packet include_closure entry path is required.")
                continue
            }
            $includePath = Resolve-EvidencePath $rawIncludePath
            if (-not (Test-Sha256Text $expectedIncludeHash)) {
                $blockers.Add("Task packet include_closure SHA256 is invalid for '$rawIncludePath'.")
                continue
            }
            $actualIncludeHash = Get-Sha256IfExists $includePath
            if ($actualIncludeHash -ine $expectedIncludeHash) {
                $blockers.Add("Task packet include_closure hash mismatch for '$includePath'.")
                continue
            }
            $includeClosure.Add([pscustomobject]@{ Path = $includePath; Sha256 = $actualIncludeHash })
        }
        $duplicateIncludePaths = @($includeClosure | Group-Object { $_.Path.ToLowerInvariant() } | Where-Object { $_.Count -gt 1 })
        if ($duplicateIncludePaths.Count -gt 0) {
            $blockers.Add("Task packet include_closure contains duplicate paths.")
        }
    }
    $computedIncludeClosureHash = Get-PathHashSetSha256 $includeClosure
    $expectedIncludeClosureHash = [string](Get-ObjectProperty $packet 'include_closure_sha256')
    if (-not (Test-Sha256Text $expectedIncludeClosureHash)) {
        $blockers.Add("Task packet field 'include_closure_sha256' must be a SHA256 value.")
    } elseif ($computedIncludeClosureHash -ine $expectedIncludeClosureHash) {
        $blockers.Add("Task packet include_closure_sha256 does not match the verified include set.")
    }
    $Binding | Add-Member -MemberType NoteProperty -Name IncludeClosure -Value @($includeClosure | ForEach-Object { $_ }) -Force
    $Binding | Add-Member -MemberType NoteProperty -Name IncludeClosureSha256 -Value $computedIncludeClosureHash -Force

    foreach ($identityField in @('broker_fingerprint', 'server_fingerprint', 'account_fingerprint', 'data_fingerprint')) {
        $identityValue = [string](Get-ObjectProperty $packet $identityField)
        if (-not (Test-Sha256Text $identityValue)) {
            $blockers.Add("Task packet field '$identityField' must be a SHA256 value.")
        }
        $bindingName = switch ($identityField) {
            'broker_fingerprint' { 'BrokerFingerprint' }
            'server_fingerprint' { 'ServerFingerprint' }
            'account_fingerprint' { 'AccountFingerprint' }
            'data_fingerprint' { 'DataFingerprint' }
        }
        $Binding | Add-Member -MemberType NoteProperty -Name $bindingName -Value $identityValue -Force
    }

    $packetGeometry = Get-ObjectProperty $packet 'symbol_geometry'
    $symbolDigits = $null
    $symbolPoint = $null
    $pipSize = $null
    if (-not (Test-ProvenanceObject $packetGeometry)) {
        $blockers.Add("Task packet field 'symbol_geometry' is required and must be an object.")
    } else {
        $symbolDigits = Get-ObjectProperty $packetGeometry 'digits'
        if (-not (Test-IntegerValue $symbolDigits) -or [int64]$symbolDigits -lt 0 -or [int64]$symbolDigits -gt 15) {
            $blockers.Add("Task packet field 'symbol_geometry.digits' is required and must be an integer from 0 through 15.")
        }
        $symbolPoint = Get-ObjectProperty $packetGeometry 'point'
        if (-not (Test-NonNegativeNumber $symbolPoint) -or [double]$symbolPoint -le 0) {
            $blockers.Add("Task packet field 'symbol_geometry.point' is required and must be a finite number greater than zero.")
        }
        $pipSize = Get-ObjectProperty $packetGeometry 'pip_size'
        if (-not (Test-NonNegativeNumber $pipSize) -or [double]$pipSize -le 0) {
            $blockers.Add("Task packet field 'symbol_geometry.pip_size' is required and must be a finite number greater than zero.")
        }
    }
    $Binding | Add-Member -MemberType NoteProperty -Name SymbolDigits -Value $symbolDigits -Force
    $Binding | Add-Member -MemberType NoteProperty -Name SymbolPoint -Value $symbolPoint -Force
    $Binding | Add-Member -MemberType NoteProperty -Name PipSize -Value $pipSize -Force

    $requiredSidecarsProperty = $packet.PSObject.Properties['required_sidecars']
    $requiredSidecars = @()
    if ($null -eq $requiredSidecarsProperty) {
        $blockers.Add("Task packet field 'required_sidecars' is required.")
    } else {
        $requiredSidecars = @($requiredSidecarsProperty.Value | ForEach-Object { [string]$_ } | Sort-Object)
        if ($requiredSidecars.Count -ne (@($requiredSidecars | Select-Object -Unique)).Count) {
            $blockers.Add("Task packet field 'required_sidecars' contains duplicate patterns.")
        }
        foreach ($pattern in $requiredSidecars) {
            if ([string]::IsNullOrWhiteSpace($pattern) -or $pattern -notmatch '^[A-Za-z0-9_.?*-]+$' -or $pattern -match '\.\.') {
                $blockers.Add("Task packet required_sidecars pattern is invalid: '$pattern'.")
            }
        }
        foreach ($minimum in (Get-RequiredSidecarsForTier $Binding.TelemetryTier $Binding.TelemetryProfile)) {
            if ($minimum -notin $requiredSidecars) {
                $blockers.Add("Task packet required_sidecars is missing telemetry-tier minimum '$minimum'.")
            }
        }
    }
    if ($authority -in @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    ) -and $requiredSidecars.Count -ne 0) {
        $blockers.Add("Data-acquisition authority requires required_sidecars=[] because lifecycle/performance telemetry is forbidden.")
    }
    $Binding | Add-Member -MemberType NoteProperty -Name RequiredSidecars -Value @($requiredSidecars) -Force

    $requiredManifestHashesProperty = $packet.PSObject.Properties['required_manifest_hashes']
    $requiredManifestHashes = @()
    if ($null -eq $requiredManifestHashesProperty) {
        $blockers.Add("Task packet field 'required_manifest_hashes' is required.")
    } else {
        $requiredManifestHashes = @($requiredManifestHashesProperty.Value | ForEach-Object { [string]$_ } | Sort-Object)
        if ($requiredManifestHashes.Count -ne (@($requiredManifestHashes | Select-Object -Unique)).Count) {
            $blockers.Add("Task packet field 'required_manifest_hashes' contains duplicates.")
        }
        foreach ($declaredHash in $requiredManifestHashes) {
            if ($declaredHash -notin @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')) {
                $blockers.Add("Task packet required_manifest_hashes contains unsupported field '$declaredHash'.")
            }
        }
        foreach ($requiredHash in @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')) {
            if ($requiredHash -notin $requiredManifestHashes) {
                $blockers.Add("Task packet required_manifest_hashes must include '$requiredHash'.")
            }
        }
    }
    $Binding | Add-Member -MemberType NoteProperty -Name RequiredManifestHashes -Value @($requiredManifestHashes) -Force

    if ($Binding.RunRole -ceq 'challenger') {
        $controlBindings = [ordered]@{
            ControlOverrides = [string](Get-ObjectProperty $packet 'matched_control_overrides')
            ControlSourceSha256 = [string](Get-ObjectProperty $packet 'matched_control_source_sha256')
            ControlConfigSha256 = [string](Get-ObjectProperty $packet 'matched_control_config_sha256')
            ControlEx5Sha256 = [string](Get-ObjectProperty $packet 'matched_control_ex5_sha256')
            ControlIncludesSha256 = [string](Get-ObjectProperty $packet 'matched_control_includes_sha256')
            ControlGitCommit = [string](Get-ObjectProperty $packet 'matched_control_git_commit')
            ControlGitStatusSha256 = [string](Get-ObjectProperty $packet 'matched_control_git_status_sha256')
        }
        if ([string]::IsNullOrWhiteSpace($controlBindings.ControlOverrides)) {
            $blockers.Add("Task packet field 'matched_control_overrides' is required.")
        }
        foreach ($field in @('ControlSourceSha256', 'ControlConfigSha256', 'ControlEx5Sha256', 'ControlIncludesSha256', 'ControlGitStatusSha256')) {
            if (-not (Test-Sha256Text $controlBindings[$field])) {
                $packetName = switch ($field) {
                    'ControlSourceSha256' { 'matched_control_source_sha256' }
                    'ControlConfigSha256' { 'matched_control_config_sha256' }
                    'ControlEx5Sha256' { 'matched_control_ex5_sha256' }
                    'ControlIncludesSha256' { 'matched_control_includes_sha256' }
                    'ControlGitStatusSha256' { 'matched_control_git_status_sha256' }
                }
                $blockers.Add("Task packet field '$packetName' must be a SHA256 value.")
            }
        }
        if ($controlBindings.ControlGitCommit -notmatch '^[A-Fa-f0-9]{40,64}$') {
            $blockers.Add("Task packet field 'matched_control_git_commit' must be a git object id.")
        }
        foreach ($name in $controlBindings.Keys) {
            $Binding | Add-Member -MemberType NoteProperty -Name $name -Value $controlBindings[$name] -Force
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($Binding.MatchedControlRunId)) {
        $blockers.Add("MatchedControlRunId must be empty for RunRole=control bootstrap.")
    }

    $validationStage = [string](Get-ObjectProperty $packet 'validation_stage')
    if ($validationStage -notin @('challenger', 'confirmed')) {
        $blockers.Add("Task packet field 'validation_stage' must be 'challenger' or 'confirmed'.")
    }
    if ($Binding.RunRole -ceq 'control' -and $validationStage -cne 'challenger') {
        $blockers.Add("RunRole=control bootstrap requires validation_stage='challenger'; a bootstrap control cannot be promotion-confirmed.")
    }
    $costEvidenceTier = [string](Get-ObjectProperty $packet 'cost_evidence_tier')
    $researchCostProxy = [bool]$Binding.AllowResearchCostProxy
    if ($researchCostProxy) {
        if ($costEvidenceTier -cne 'research_proxy') {
            $blockers.Add("AllowResearchCostProxy requires task packet cost_evidence_tier='research_proxy'.")
        }
        if ($Binding.RunRole -cne 'control') {
            $blockers.Add("RESEARCH_PROXY requires RunRole=control; it cannot be a challenger or promotion input.")
        }
        if ($validationStage -cne 'challenger') {
            $blockers.Add("RESEARCH_PROXY requires validation_stage='challenger'.")
        }
    } elseif ($costEvidenceTier -ceq 'research_proxy') {
        $blockers.Add("Task packet requests research_proxy cost evidence without -AllowResearchCostProxy.")
    }
    $economicWindow = Resolve-EconomicWindow $packet $Binding $researchCostProxy $blockers
    $baselineAcceptance = Resolve-BaselineAcceptanceContract $packet $researchCostProxy $blockers
    if ($researchCostProxy) {
        if ((Get-ObjectProperty $packet 'performance_metrics_authorized') -ne $true -or
            (Get-ObjectProperty $packet 'economics_authorized') -ne $true -or
            (Get-ObjectProperty $packet 'promotion_eligible') -ne $false) {
            $blockers.Add("RESEARCH_PROXY task packet must set performance_metrics_authorized=true, economics_authorized=true, and promotion_eligible=false.")
        }
    }
    $isModel4CollectionAuthority = (
        $authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE' -and
        [int]$Binding.Model -eq 4 -and
        [string]$Binding.RunRole -ceq 'control'
    )
    if ([int]$Binding.Model -ne 0 -and -not $isModel4CollectionAuthority) {
        $blockers.Add("Strict challenger/confirmed research requires MT5 Model=0 (every tick generated from M1 bars; not broker real ticks); got '$($Binding.Model)'.")
    }
    $holdingContract = [string](Get-ObjectProperty $packet 'holding_contract')
    if ($holdingContract -notin @('scalp', 'non_scalp')) {
        $blockers.Add("Task packet field 'holding_contract' must be 'scalp' or 'non_scalp'.")
    }

    $costSourceRaw = [string](Get-ObjectProperty $packet 'cost_source_manifest_path')
    $costSourceExpectedHash = [string](Get-ObjectProperty $packet 'cost_source_manifest_sha256')
    if ($costSourceRaw -cne $Binding.CostSourceManifest) {
        $blockers.Add("Task packet field 'cost_source_manifest_path' does not match CLI value '$($Binding.CostSourceManifest)'.")
    }
    $costSourcePath = Resolve-EvidencePath $costSourceRaw
    if ([string]::IsNullOrWhiteSpace($costSourceRaw)) {
        $blockers.Add("Task packet field 'cost_source_manifest_path' is required.")
    } elseif (-not (Test-Path -LiteralPath $costSourcePath -PathType Leaf)) {
        $blockers.Add("Cost source manifest is missing: $costSourcePath")
    }
    if ([string]::IsNullOrWhiteSpace($costSourceExpectedHash)) {
        $blockers.Add("Task packet field 'cost_source_manifest_sha256' is required.")
    } elseif (Test-Path -LiteralPath $costSourcePath -PathType Leaf) {
        $actualCostSourceHash = Get-Sha256IfExists $costSourcePath
        if ($actualCostSourceHash -ine $costSourceExpectedHash) {
            $blockers.Add("Cost source manifest SHA256 mismatch: expected '$costSourceExpectedHash', got '$actualCostSourceHash'.")
        } else {
            try {
                $costSourceManifest = Get-Content -LiteralPath $costSourcePath -Raw | ConvertFrom-Json
                if ($authority -in @(
                    'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
                    'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
                )) {
                    $collectionContract = Resolve-CollectionCostManifest `
                        $costSourceManifest $authority $Binding $blockers
                    if ($null -ne $collectionContract) {
                        [void]$costEvidence.Add($collectionContract.Evidence)
                        $collectionServer = [string]$collectionContract.Server
                        $collectionPeriod = [string]$collectionContract.Period
                    }
                    if ($authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
                        Add-Model4CollectionSourceEpochBlockers `
                            $Contract $Binding $costSourceManifest $blockers
                    }
                } else {
                $costSchema = [string](Get-ObjectProperty $costSourceManifest 'schema_version')
                if ($costSchema -cne 'alphafactory_cost_source_manifest.v1') {
                    $blockers.Add("Cost source manifest schema_version must be 'alphafactory_cost_source_manifest.v1'.")
                }
                $manifestEvidenceTier = [string](Get-ObjectProperty $costSourceManifest 'evidence_tier')
                if ($researchCostProxy -and $manifestEvidenceTier -cne 'RESEARCH_PROXY') {
                    $blockers.Add("RESEARCH_PROXY manifest evidence_tier must equal RESEARCH_PROXY.")
                } elseif (-not $researchCostProxy -and $manifestEvidenceTier -ceq 'RESEARCH_PROXY') {
                    $blockers.Add("RESEARCH_PROXY manifest requires explicit runner opt-in.")
                }
                $expectedProvenanceStatus = if ($researchCostProxy) { 'VERIFIED_RESEARCH_PROXY' } else { 'VERIFIED' }
                $provenanceStatus = [string](Get-ObjectProperty $costSourceManifest 'provenance_status')
                if ($provenanceStatus -cne $expectedProvenanceStatus) {
                    $blockers.Add("Cost source manifest provenance_status must be $expectedProvenanceStatus; got '$provenanceStatus'.")
                }
                $rootAuditStatus = [string](Get-ObjectProperty $costSourceManifest 'audit_status')
                $allowedAuditStatus = if ($researchCostProxy) { @('PASS_RESEARCH_ONLY') } else { @('PASS', 'VERIFIED') }
                if (-not [string]::IsNullOrWhiteSpace($rootAuditStatus) -and $rootAuditStatus -notin $allowedAuditStatus) {
                    $blockers.Add("Cost source manifest audit_status '$rootAuditStatus' is incompatible with evidence tier '$costEvidenceTier'.")
                }
                $rootVerdict = [string](Get-ObjectProperty $costSourceManifest 'verdict')
                $expectedRootVerdict = if ($researchCostProxy) { 'PASS_RESEARCH_ONLY' } else { 'PASS' }
                if (-not [string]::IsNullOrWhiteSpace($rootVerdict) -and $rootVerdict -cne $expectedRootVerdict) {
                    $blockers.Add("Cost source manifest verdict '$rootVerdict' is incompatible with evidence tier '$costEvidenceTier'.")
                }
                if ($researchCostProxy -and (Get-ObjectProperty $costSourceManifest 'promotion_eligible') -ne $false) {
                    $blockers.Add("RESEARCH_PROXY cost source promotion_eligible must be false.")
                }
                $costBroker = [string](Get-ObjectProperty $costSourceManifest 'broker')
                if ([string]::IsNullOrWhiteSpace($costBroker)) {
                    $blockers.Add("Cost source manifest field 'broker' is required.")
                }

                $identityBindings = [ordered]@{
                    broker_fingerprint = [string]$Binding.BrokerFingerprint
                    server_fingerprint = [string]$Binding.ServerFingerprint
                    account_fingerprint = [string]$Binding.AccountFingerprint
                    data_fingerprint = [string]$Binding.DataFingerprint
                }
                foreach ($identityName in $identityBindings.Keys) {
                    $manifestIdentity = [string](Get-ObjectProperty $costSourceManifest $identityName)
                    if (-not (Test-Sha256Text $manifestIdentity)) {
                        $blockers.Add("Cost source manifest field '$identityName' must be a SHA256 value.")
                    } elseif ($manifestIdentity -ine $identityBindings[$identityName]) {
                        $blockers.Add("Cost source manifest field '$identityName' does not match task packet fingerprint '$($identityBindings[$identityName])'.")
                    }
                }

                $costSymbol = [string](Get-ObjectProperty $costSourceManifest 'symbol')
                if ($costSymbol -cne $Binding.Symbol) {
                    $blockers.Add("Cost source manifest symbol '$costSymbol' does not match task packet symbol '$($Binding.Symbol)'.")
                }
                $costFrom = [string](Get-ObjectProperty $costSourceManifest 'from')
                $costTo = [string](Get-ObjectProperty $costSourceManifest 'to')
                if ($costFrom -cne $economicWindow.From -or $costTo -cne $economicWindow.To) {
                    $blockers.Add("Cost source manifest window '$costFrom' to '$costTo' does not match task packet economic window '$($economicWindow.From)' to '$($economicWindow.To)'.")
                }

                $costGeometry = Get-ObjectProperty $costSourceManifest 'symbol_geometry'
                if (-not (Test-ProvenanceObject $costGeometry)) {
                    $blockers.Add("Cost source manifest field 'symbol_geometry' is required and must be an object.")
                } else {
                    $costDigits = Get-ObjectProperty $costGeometry 'digits'
                    if (-not (Test-IntegerValue $costDigits) -or [int64]$costDigits -lt 0 -or [int64]$costDigits -gt 15) {
                        $blockers.Add("Cost source manifest symbol_geometry.digits is required and must be an integer from 0 through 15.")
                    } elseif ((Test-IntegerValue $Binding.SymbolDigits) -and [int64]$costDigits -ne [int64]$Binding.SymbolDigits) {
                        $blockers.Add("Cost source manifest symbol_geometry.digits does not match task packet value '$($Binding.SymbolDigits)'.")
                    }
                    $costPoint = Get-ObjectProperty $costGeometry 'point'
                    if (-not (Test-NonNegativeNumber $costPoint) -or [double]$costPoint -le 0) {
                        $blockers.Add("Cost source manifest symbol_geometry.point is required and must be a finite number greater than zero.")
                    } elseif ((Test-NonNegativeNumber $Binding.SymbolPoint) -and [double]$costPoint -ne [double]$Binding.SymbolPoint) {
                        $blockers.Add("Cost source manifest symbol_geometry.point does not match task packet value '$($Binding.SymbolPoint)'.")
                    }
                    $costPipSize = Get-ObjectProperty $costGeometry 'pip_size'
                    if (-not (Test-NonNegativeNumber $costPipSize) -or [double]$costPipSize -le 0) {
                        $blockers.Add("Cost source manifest symbol_geometry.pip_size is required and must be a finite number greater than zero.")
                    } elseif ((Test-NonNegativeNumber $Binding.PipSize) -and [double]$costPipSize -ne [double]$Binding.PipSize) {
                        $blockers.Add("Cost source manifest symbol_geometry.pip_size does not match task packet value '$($Binding.PipSize)'.")
                    }
                }

                $spreadNode = Get-ObjectProperty $costSourceManifest 'historical_spread_provenance'
                if (-not (Test-ProvenanceObject $spreadNode)) {
                    $blockers.Add("Cost source manifest field 'historical_spread_provenance' must be an object.")
                } else {
                    if ([string](Get-ObjectProperty $spreadNode 'verification_status') -cne 'VERIFIED') {
                        $blockers.Add("historical_spread_provenance.verification_status must be VERIFIED.")
                    }
                    $spreadEvidence = Resolve-CostEvidenceFile (Get-ObjectProperty $spreadNode 'source') (Get-ObjectProperty $spreadNode 'source_sha256') 'historical_spread_provenance' $blockers
                    if ($null -ne $spreadEvidence) {
                        [void]$costEvidence.Add($spreadEvidence)
                    }
                    $spreadSymbol = [string](Get-ObjectProperty $spreadNode 'symbol')
                    if ($spreadSymbol -cne $Binding.Symbol) {
                        $blockers.Add("historical_spread_provenance.symbol '$spreadSymbol' does not match task packet symbol '$($Binding.Symbol)'.")
                    }
                    $coverage = Get-ObjectProperty $spreadNode 'coverage'
                    if (-not (Test-ProvenanceObject $coverage)) {
                        $blockers.Add("historical_spread_provenance.coverage must be an object.")
                    } else {
                        $coverageFrom = [string](Get-ObjectProperty $coverage 'from')
                        $coverageTo = [string](Get-ObjectProperty $coverage 'to')
                        if ($coverageFrom -cne $economicWindow.From -or $coverageTo -cne $economicWindow.To) {
                            $blockers.Add("historical_spread_provenance.coverage window '$coverageFrom' to '$coverageTo' does not match task packet economic window '$($economicWindow.From)' to '$($economicWindow.To)'.")
                        }
                        $coverageSamples = Get-ObjectProperty $coverage 'sample_count'
                        $coverageTotal = Get-ObjectProperty $coverage 'total_count'
                        if (-not (Test-PositiveInteger $coverageSamples) -or -not (Test-PositiveInteger $coverageTotal)) {
                            $blockers.Add("historical_spread_provenance.coverage requires positive integer sample_count and total_count.")
                        } elseif ([int64]$coverageSamples -gt [int64]$coverageTotal) {
                            $blockers.Add("historical_spread_provenance.coverage.sample_count cannot exceed total_count.")
                        }
                        $coverageRatio = Get-ObjectProperty $coverage 'coverage_ratio'
                        $coverageRatioValid = Test-NonNegativeNumber $coverageRatio
                        if (-not $coverageRatioValid -or [double]$coverageRatio -lt 0.99 -or [double]$coverageRatio -gt 1.0) {
                            $blockers.Add("historical_spread_provenance.coverage.coverage_ratio must be at least 0.99 and no greater than 1.0.")
                        } elseif ((Test-PositiveInteger $coverageSamples) -and (Test-PositiveInteger $coverageTotal)) {
                            $computedCoverageRatio = [double]$coverageSamples / [double]$coverageTotal
                            if ([math]::Abs(([double]$coverageRatio) - $computedCoverageRatio) -gt 0.000001) {
                                $blockers.Add("historical_spread_provenance.coverage.coverage_ratio does not match sample_count divided by total_count.")
                            }
                        }
                    }
                }

                $commissionNode = Get-ObjectProperty $costSourceManifest 'commission_provenance'
                if (-not (Test-ProvenanceObject $commissionNode)) {
                    $blockers.Add("Cost source manifest field 'commission_provenance' must be an object.")
                } else {
                    $expectedCommissionStatus = if ($researchCostProxy) { 'VERIFIED_RESEARCH_PROXY' } else { 'VERIFIED' }
                    if ([string](Get-ObjectProperty $commissionNode 'verification_status') -cne $expectedCommissionStatus) {
                        $blockers.Add("commission_provenance.verification_status must be $expectedCommissionStatus.")
                    }
                    if (-not (Test-NonNegativeNumber (Get-ObjectProperty $commissionNode 'value'))) {
                        $blockers.Add("commission_provenance.value must be a non-negative number.")
                    }
                    $commissionSymbol = [string](Get-ObjectProperty $commissionNode 'symbol')
                    $commissionSymbolValid = $commissionSymbol -ceq $Binding.Symbol
                    if (-not $commissionSymbolValid) {
                        $blockers.Add("commission_provenance.symbol '$commissionSymbol' does not match task packet symbol '$($Binding.Symbol)'.")
                    }
                    $commissionSamples = Get-ObjectProperty $commissionNode 'sample_count'
                    $commissionHasThirtySamples = (Test-PositiveInteger $commissionSamples) -and ([int64]$commissionSamples -ge 30)
                    $commissionSameSymbol = (Get-ObjectProperty $commissionNode 'same_symbol_lifecycles') -eq $true
                    $commissionMethod = [string](Get-ObjectProperty $commissionNode 'method')
                    if ($researchCostProxy) {
                        if ([string](Get-ObjectProperty $commissionNode 'source_kind') -cne 'strategy_tester_simulation') {
                            $blockers.Add("RESEARCH_PROXY commission source_kind must equal strategy_tester_simulation.")
                        }
                        if ([string](Get-ObjectProperty $commissionNode 'statistic') -cne 'maximum') {
                            $blockers.Add("RESEARCH_PROXY commission statistic must equal maximum.")
                        }
                    }
                    $commissionSourceRaw = Get-ObjectProperty $commissionNode 'source'
                    $commissionSourceHash = Get-ObjectProperty $commissionNode 'source_sha256'
                    $commissionSourceDeclared = -not [string]::IsNullOrWhiteSpace([string]$commissionSourceRaw) -or
                        -not [string]::IsNullOrWhiteSpace([string]$commissionSourceHash)
                    $commissionEvidence = $null
                    if ($commissionSourceDeclared -or ($commissionHasThirtySamples -and $commissionSameSymbol)) {
                        $commissionEvidence = Resolve-CostEvidenceFile $commissionSourceRaw $commissionSourceHash 'commission_provenance' $blockers
                        if ($null -ne $commissionEvidence) {
                            [void]$costEvidence.Add($commissionEvidence)
                        }
                    }
                    if ($commissionSourceDeclared -and [string]::IsNullOrWhiteSpace($commissionMethod)) {
                        $blockers.Add("commission_provenance.method is required for empirical lifecycle evidence.")
                    }
                    $empiricalCommissionValid = $commissionHasThirtySamples -and $commissionSameSymbol -and
                        $commissionSymbolValid -and (-not [string]::IsNullOrWhiteSpace($commissionMethod)) -and
                        ($null -ne $commissionEvidence)

                    $brokerContractValid = $false
                    $brokerContractProperty = $commissionNode.PSObject.Properties['broker_contract']
                    if ($null -ne $brokerContractProperty) {
                        $brokerContract = $brokerContractProperty.Value
                        if (-not (Test-ProvenanceObject $brokerContract)) {
                            $blockers.Add("commission_provenance.broker_contract must be an object when supplied.")
                        } else {
                            $brokerContractEvidence = Resolve-CostEvidenceFile (Get-ObjectProperty $brokerContract 'source') (Get-ObjectProperty $brokerContract 'source_sha256') 'commission_provenance.broker_contract' $blockers
                            if ($null -ne $brokerContractEvidence) {
                                [void]$costEvidence.Add($brokerContractEvidence)
                            }
                            $contractBrokerFingerprint = [string](Get-ObjectProperty $brokerContract 'broker_fingerprint')
                            $contractBrokerIdentityValid = Test-Sha256Text $contractBrokerFingerprint
                            if (-not $contractBrokerIdentityValid) {
                                $blockers.Add("commission_provenance.broker_contract.broker_fingerprint must be a SHA256 value.")
                            } elseif ($contractBrokerFingerprint -ine $Binding.BrokerFingerprint) {
                                $blockers.Add("commission_provenance.broker_contract.broker_fingerprint does not match task packet fingerprint '$($Binding.BrokerFingerprint)'.")
                                $contractBrokerIdentityValid = $false
                            }
                            $contractServerFingerprint = [string](Get-ObjectProperty $brokerContract 'server_fingerprint')
                            $contractServerIdentityValid = Test-Sha256Text $contractServerFingerprint
                            if (-not $contractServerIdentityValid) {
                                $blockers.Add("commission_provenance.broker_contract.server_fingerprint must be a SHA256 value.")
                            } elseif ($contractServerFingerprint -ine $Binding.ServerFingerprint) {
                                $blockers.Add("commission_provenance.broker_contract.server_fingerprint does not match task packet fingerprint '$($Binding.ServerFingerprint)'.")
                                $contractServerIdentityValid = $false
                            }
                            $contractAccountFingerprint = [string](Get-ObjectProperty $brokerContract 'account_fingerprint')
                            $contractAccountIdentityValid = Test-Sha256Text $contractAccountFingerprint
                            if (-not $contractAccountIdentityValid) {
                                $blockers.Add("commission_provenance.broker_contract.account_fingerprint must be a SHA256 value.")
                            } elseif ($contractAccountFingerprint -ine $Binding.AccountFingerprint) {
                                $blockers.Add("commission_provenance.broker_contract.account_fingerprint does not match task packet fingerprint '$($Binding.AccountFingerprint)'.")
                                $contractAccountIdentityValid = $false
                            }
                            $contractSymbol = [string](Get-ObjectProperty $brokerContract 'symbol')
                            $contractSymbolValid = $contractSymbol -ceq $Binding.Symbol
                            if (-not $contractSymbolValid) {
                                $blockers.Add("commission_provenance.broker_contract.symbol '$contractSymbol' does not match task packet symbol '$($Binding.Symbol)'.")
                            }
                            $costAccountCurrency = [string](Get-ObjectProperty $costSourceManifest 'account_currency')
                            $contractAccountCurrency = [string](Get-ObjectProperty $brokerContract 'account_currency')
                            $contractCurrencyValid = (-not [string]::IsNullOrWhiteSpace($costAccountCurrency)) -and
                                ($contractAccountCurrency -ceq $costAccountCurrency)
                            if (-not $contractCurrencyValid) {
                                $blockers.Add("commission_provenance.broker_contract.account_currency '$contractAccountCurrency' does not match cost manifest account_currency '$costAccountCurrency'.")
                            }
                            $contractPerLotBasis = (Get-ObjectProperty $brokerContract 'per_lot_basis') -eq $true
                            if (-not $contractPerLotBasis) {
                                $blockers.Add("commission_provenance.broker_contract.per_lot_basis must be true.")
                            }
                            $contractFrom = [string](Get-ObjectProperty $brokerContract 'from')
                            $contractFromValid = $contractFrom -ceq $economicWindow.From
                            if (-not $contractFromValid) {
                                $blockers.Add("commission_provenance.broker_contract.from '$contractFrom' does not match task packet economic from '$($economicWindow.From)'.")
                            }
                            $contractTo = [string](Get-ObjectProperty $brokerContract 'to')
                            $contractToValid = $contractTo -ceq $economicWindow.To
                            if (-not $contractToValid) {
                                $blockers.Add("commission_provenance.broker_contract.to '$contractTo' does not match task packet economic to '$($economicWindow.To)'.")
                            }
                            $contractConversionMethod = [string](Get-ObjectProperty $brokerContract 'conversion_method')
                            $contractConversionValid = $contractConversionMethod -ceq 'per_trade_contemporaneous'
                            if (-not $contractConversionValid) {
                                $blockers.Add("commission_provenance.broker_contract.conversion_method must equal per_trade_contemporaneous.")
                            }
                            $contractRoundTurnPerLot = Get-ObjectProperty $brokerContract 'round_turn_account_per_lot'
                            $contractRoundTurnPositive = (Test-NonNegativeNumber $contractRoundTurnPerLot) -and
                                ([double]$contractRoundTurnPerLot -gt 0)
                            if (-not $contractRoundTurnPositive) {
                                $blockers.Add("commission_provenance.broker_contract.round_turn_account_per_lot must be a finite number greater than zero.")
                            }
                            $commissionValue = Get-ObjectProperty $commissionNode 'value'
                            $contractRoundTurnMatchesValue = $contractRoundTurnPositive -and
                                (Test-NonNegativeNumber $commissionValue) -and
                                ([double]$contractRoundTurnPerLot -eq [double]$commissionValue)
                            if ($contractRoundTurnPositive -and -not $contractRoundTurnMatchesValue) {
                                $blockers.Add("commission_provenance.broker_contract.round_turn_account_per_lot must equal commission_provenance.value.")
                            }
                            $contractDescription = [string](Get-ObjectProperty $brokerContract 'description')
                            if ([string]::IsNullOrWhiteSpace($contractDescription)) {
                                $blockers.Add("commission_provenance.broker_contract.description is required for an explicit broker contract.")
                            }
                            $brokerContractValid = ($null -ne $brokerContractEvidence) -and
                                $contractBrokerIdentityValid -and $contractServerIdentityValid -and
                                $contractAccountIdentityValid -and $contractSymbolValid -and
                                $contractCurrencyValid -and $contractPerLotBasis -and
                                $contractFromValid -and $contractToValid -and $contractConversionValid -and
                                $contractRoundTurnPositive -and $contractRoundTurnMatchesValue -and
                                (-not [string]::IsNullOrWhiteSpace($contractDescription))
                        }
                    }
                    if (-not $empiricalCommissionValid -and -not $brokerContractValid) {
                        $blockers.Add("commission_provenance requires at least 30 same-symbol lifecycles with hashed empirical evidence or a hashed explicit broker contract.")
                    }
                }

                $slippageNode = Get-ObjectProperty $costSourceManifest 'slippage_provenance'
                if (-not (Test-ProvenanceObject $slippageNode)) {
                    $blockers.Add("Cost source manifest field 'slippage_provenance' must be an object.")
                } else {
                    $expectedSlippageStatus = if ($researchCostProxy) { 'VERIFIED_RESEARCH_PROXY' } else { 'VERIFIED' }
                    if ([string](Get-ObjectProperty $slippageNode 'verification_status') -cne $expectedSlippageStatus) {
                        $blockers.Add("slippage_provenance.verification_status must be $expectedSlippageStatus.")
                    }
                    $slippageEvidence = Resolve-CostEvidenceFile (Get-ObjectProperty $slippageNode 'source') (Get-ObjectProperty $slippageNode 'source_sha256') 'slippage_provenance' $blockers
                    if ($null -ne $slippageEvidence) {
                        [void]$costEvidence.Add($slippageEvidence)
                    }
                    $slippageSymbol = [string](Get-ObjectProperty $slippageNode 'symbol')
                    if ($slippageSymbol -cne $Binding.Symbol) {
                        $blockers.Add("slippage_provenance.symbol '$slippageSymbol' does not match task packet symbol '$($Binding.Symbol)'.")
                    }
                    $slippageSamples = Get-ObjectProperty $slippageNode 'sample_count'
                    $slippageIndependent = (Get-ObjectProperty $slippageNode 'independent_reference') -eq $true
                    $slippageQuoteIndependent = (Get-ObjectProperty $slippageNode 'independent_quote_reference') -eq $true
                    $slippageFillObserved = (Get-ObjectProperty $slippageNode 'fill_observed') -eq $true
                    if (-not (Test-PositiveInteger $slippageSamples) -or [int64]$slippageSamples -lt 100) {
                        $blockers.Add("slippage_provenance requires at least 100 samples.")
                    } elseif ($researchCostProxy) {
                        if ($slippageIndependent -or -not $slippageQuoteIndependent -or $slippageFillObserved) {
                            $blockers.Add("RESEARCH_PROXY slippage must be independent-quote, non-fill evidence.")
                        }
                        if (-not (Test-PositiveInteger (Get-ObjectProperty $slippageNode 'fixed_latency_ms'))) {
                            $blockers.Add("RESEARCH_PROXY slippage fixed_latency_ms must be a positive integer.")
                        }
                    } elseif (-not $slippageIndependent) {
                        $blockers.Add("slippage_provenance requires independent-reference fill evidence.")
                    }
                    $slippageBuyCount = Get-ObjectProperty $slippageNode 'buy_count'
                    if (-not (Test-PositiveInteger $slippageBuyCount) -or [int64]$slippageBuyCount -lt 30) {
                        $blockers.Add("slippage_provenance.buy_count must be at least 30.")
                    }
                    $slippageSellCount = Get-ObjectProperty $slippageNode 'sell_count'
                    if (-not (Test-PositiveInteger $slippageSellCount) -or [int64]$slippageSellCount -lt 30) {
                        $blockers.Add("slippage_provenance.sell_count must be at least 30.")
                    }
                    if ((Test-PositiveInteger $slippageSamples) -and
                        (Test-PositiveInteger $slippageBuyCount) -and
                        (Test-PositiveInteger $slippageSellCount) -and
                        ([int64]$slippageSamples -ne ([int64]$slippageBuyCount + [int64]$slippageSellCount))) {
                        $blockers.Add("slippage_provenance.sample_count must equal buy_count plus sell_count.")
                    }
                    $buyReferenceSide = [string](Get-ObjectProperty $slippageNode 'buy_reference_side')
                    if ($buyReferenceSide -cne 'ask') {
                        $blockers.Add("slippage_provenance.buy_reference_side must equal ask.")
                    }
                    $sellReferenceSide = [string](Get-ObjectProperty $slippageNode 'sell_reference_side')
                    if ($sellReferenceSide -cne 'bid') {
                        $blockers.Add("slippage_provenance.sell_reference_side must equal bid.")
                    }
                    if ([string](Get-ObjectProperty $slippageNode 'slippage_unit') -cne 'pips') {
                        $blockers.Add("slippage_provenance.slippage_unit must equal pips.")
                    }
                    if ([string]::IsNullOrWhiteSpace([string](Get-ObjectProperty $slippageNode 'method'))) {
                        $blockers.Add("slippage_provenance.method is required.")
                    }
                    $p90Buy = Get-ObjectProperty $slippageNode 'p90_buy'
                    if (-not (Test-NonNegativeNumber $p90Buy)) {
                        $blockers.Add("slippage_provenance.p90_buy must be a finite non-negative number.")
                    }
                    $p90Sell = Get-ObjectProperty $slippageNode 'p90_sell'
                    if (-not (Test-NonNegativeNumber $p90Sell)) {
                        $blockers.Add("slippage_provenance.p90_sell must be a finite non-negative number.")
                    }
                    $p90Roundturn = Get-ObjectProperty $slippageNode 'p90_roundturn'
                    if (-not (Test-NonNegativeNumber $p90Roundturn)) {
                        $blockers.Add("slippage_provenance.p90_roundturn must be a finite non-negative number.")
                    } elseif ((Test-NonNegativeNumber $p90Buy) -and (Test-NonNegativeNumber $p90Sell) -and
                        [math]::Abs(([double]$p90Roundturn) - ([double]$p90Buy + [double]$p90Sell)) -gt 0.000000001) {
                        $blockers.Add("slippage_provenance.p90_roundturn must equal p90_buy plus p90_sell.")
                    }
                }

                $methodologyNode = Get-ObjectProperty $costSourceManifest 'direction_aware_methodology'
                if (-not (Test-ProvenanceObject $methodologyNode)) {
                    $blockers.Add("Cost source manifest field 'direction_aware_methodology' must be an object.")
                } else {
                    $expectedMethodologyStatus = if ($researchCostProxy) { 'VERIFIED_RESEARCH_PROXY' } else { 'VERIFIED' }
                    if ([string](Get-ObjectProperty $methodologyNode 'verification_status') -cne $expectedMethodologyStatus) {
                        $blockers.Add("direction_aware_methodology.verification_status must be $expectedMethodologyStatus.")
                    }
                    if ((Get-ObjectProperty $methodologyNode 'direction_aware') -ne $true) {
                        $blockers.Add("direction_aware_methodology.direction_aware must be true.")
                    }
                    $longTreatment = [string](Get-ObjectProperty $methodologyNode 'long_cost_treatment')
                    $shortTreatment = [string](Get-ObjectProperty $methodologyNode 'short_cost_treatment')
                    if ([string]::IsNullOrWhiteSpace($longTreatment) -or [string]::IsNullOrWhiteSpace($shortTreatment)) {
                        $blockers.Add("direction_aware_methodology requires long_cost_treatment and short_cost_treatment.")
                    } elseif ($longTreatment -ceq $shortTreatment) {
                        $blockers.Add("direction_aware_methodology long and short cost treatments must be direction-specific.")
                    }
                }
                }
            } catch {
                $blockers.Add("Cost source manifest JSON is malformed: $($_.Exception.Message)")
            }
        }
    }

    $matchedControl = ''
    $matchedControlResult = $null
    if ($Binding.RunRole -ceq 'challenger') {
        $matchedControl = [string](Get-ObjectProperty $packet 'matched_control_run_id')
        if (-not [string]::IsNullOrWhiteSpace($matchedControl) -and $matchedControl -cne $Binding.MatchedControlRunId) {
            $blockers.Add("Task packet field 'matched_control_run_id' does not match CLI value '$($Binding.MatchedControlRunId)'.")
        }
        $controlHypothesisId = [string](Get-ObjectProperty $packet 'matched_control_hypothesis_id')
        $controlManifestHash = [string](Get-ObjectProperty $packet 'matched_control_manifest_sha256')
        $controlReportHash = [string](Get-ObjectProperty $packet 'matched_control_report_sha256')
        $matchedControlResult = Resolve-MatchedControl $matchedControl $controlHypothesisId $controlManifestHash $controlReportHash $Contract $Binding
        foreach ($controlBlocker in $matchedControlResult.Blockers) {
            $blockers.Add([string]$controlBlocker)
        }
    } else {
        foreach ($field in @(
            'matched_control_run_id', 'matched_control_hypothesis_id', 'matched_control_manifest_sha256',
            'matched_control_report_sha256', 'matched_control_overrides', 'matched_control_source_sha256',
            'matched_control_config_sha256', 'matched_control_ex5_sha256', 'matched_control_includes_sha256',
            'matched_control_git_commit', 'matched_control_git_status_sha256'
        )) {
            if (-not [string]::IsNullOrWhiteSpace([string](Get-ObjectProperty $packet $field))) {
                $blockers.Add("Task packet field '$field' must be absent for RunRole=control bootstrap.")
            }
        }
    }

    $wfaRaw = [string](Get-ObjectProperty $packet 'wfa_artifact_path')
    $wfaHash = [string](Get-ObjectProperty $packet 'wfa_artifact_sha256')
    if ($wfaRaw -cne $Binding.WfaArtifact) {
        $blockers.Add("Task packet field 'wfa_artifact_path' does not match CLI value '$($Binding.WfaArtifact)'.")
    }
    $wfaPath = Resolve-EvidencePath $wfaRaw
    if (-not [string]::IsNullOrWhiteSpace($wfaRaw)) {
        if (-not (Test-Path -LiteralPath $wfaPath -PathType Leaf)) {
            $blockers.Add("WFA artifact is missing: $wfaPath")
        } elseif ([string]::IsNullOrWhiteSpace($wfaHash)) {
            $blockers.Add("Task packet field 'wfa_artifact_sha256' is required when wfa_artifact_path is supplied.")
        } elseif ((Get-Sha256IfExists $wfaPath) -ine $wfaHash) {
            $blockers.Add("WFA artifact SHA256 mismatch.")
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($wfaHash)) {
        $blockers.Add("Task packet field 'wfa_artifact_path' is required when wfa_artifact_sha256 is supplied.")
    }

    $variantsRaw = [string](Get-ObjectProperty $packet 'variants_dir')
    $variantsHash = [string](Get-ObjectProperty $packet 'variants_sha256')
    if ($variantsRaw -cne $Binding.VariantsDir) {
        $blockers.Add("Task packet field 'variants_dir' does not match CLI value '$($Binding.VariantsDir)'.")
    }
    $variantsPath = Resolve-EvidencePath $variantsRaw
    if (-not [string]::IsNullOrWhiteSpace($variantsRaw)) {
        if (-not (Test-Path -LiteralPath $variantsPath -PathType Container)) {
            $blockers.Add("Variants directory is missing: $variantsPath")
        } elseif ([string]::IsNullOrWhiteSpace($variantsHash)) {
            $blockers.Add("Task packet field 'variants_sha256' is required when variants_dir is supplied.")
        } elseif ((Get-DirectoryTreeSha256 $variantsPath) -ine $variantsHash) {
            $blockers.Add("Variants directory SHA256 mismatch.")
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($variantsHash)) {
        $blockers.Add("Task packet field 'variants_dir' is required when variants_sha256 is supplied.")
    }

    return [pscustomobject]@{
        Present = $true
        Packet = $packet
        PacketPath = $resolvedPacketPath
        PacketSha256 = Get-Sha256IfExists $resolvedPacketPath
        CostSourceManifestPath = $costSourcePath
        WfaArtifactPath = $wfaPath
        VariantsDir = $variantsPath
        ValidationStage = $validationStage
        CostEvidenceTier = $costEvidenceTier
        EconomicFrom = $economicWindow.From
        EconomicTo = $economicWindow.To
        BaselineAcceptanceContract = $baselineAcceptance
        HoldingContract = $holdingContract
        AcceptanceContract = $registeredAcceptance
        DataAcceptanceContract = $Contract.DataAcceptanceContract
        DataQualityContract = $dataQualityContract
        Authority = $authority
        CollectionSymbol = if ($authority -in @(
            'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
            'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
        )) { [string]$Binding.Symbol } else { $null }
        CollectionPeriod = $collectionPeriod
        CollectionServer = $collectionServer
        MatchedControlRunId = $matchedControl
        MatchedControl = $matchedControlResult
        IncludeClosure = @($includeClosure | ForEach-Object { $_ })
        IncludeClosureSha256 = $computedIncludeClosureHash
        RequiredSidecars = @($requiredSidecars)
        RequiredManifestHashes = @($requiredManifestHashes)
        CostEvidence = @($costEvidence | ForEach-Object { $_ })
        Blockers = @($blockers | ForEach-Object { $_ })
    }
}

function Add-Model4CollectionLaunchAuthorityBlockers(
    $Contract,
    $Binding,
    $PacketResult,
    [string]$RunnerPath,
    $Blockers
) {
    if ([string]$PacketResult.Authority -cne 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        return
    }
    if (-not (Test-ScopedModel4PriorRegistryPacket `
        $PacketResult.Packet $Contract $Binding $PacketResult.PacketPath)) {
        $Blockers.Add(
            "Model4 collection -Execute requires the exact one-shot XAUUSD " +
            "collection-only registry authority bound to this prior-registry task packet."
        )
        return
    }
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    $controlPlane = Get-Model4ControlPlaneBinding $RunnerPath
    $executionDependencyBindings = @(Get-Model4ExecutionDependencyBindings $RunnerPath)
    $registeredRunnerSha256 = [string](Get-ObjectProperty $validation 'runner_engine_sha256')
    if (
        -not (Test-Sha256Text $registeredRunnerSha256) -or
        $registeredRunnerSha256 -cne $controlPlane.RunnerSha256
    ) {
        $Blockers.Add(
            "Model4 collection -Execute requires runner_engine_sha256 to bind the current runner."
        )
    }
    $registeredValidatorSha256 = [string](Get-ObjectProperty $validation 'candidate_registry_validator_sha256')
    if (
        -not (Test-Sha256Text $registeredValidatorSha256) -or
        $registeredValidatorSha256 -cne $controlPlane.ValidatorSha256
    ) {
        $Blockers.Add(
            "Model4 collection -Execute requires candidate_registry_validator_sha256 to bind the current registry validator."
        )
    }
    $registeredAlphaSha256 = [string](Get-ObjectProperty $validation 'alpha_entrypoint_sha256')
    if (
        -not (Test-Sha256Text $registeredAlphaSha256) -or
        $registeredAlphaSha256 -cne $controlPlane.AlphaSha256
    ) {
        $Blockers.Add(
            "Model4 collection -Execute requires alpha_entrypoint_sha256 to bind the current AlphaFactory entrypoint."
        )
    }
    [void](Test-Model4ExecutionDependencyBindings `
        (Get-ObjectProperty $validation 'execution_dependency_bindings') `
        $executionDependencyBindings $Blockers 'validation')
    [void](Test-Model4BoundTestBindings `
        (Get-ObjectProperty $validation 'bound_tests') $Blockers 'validation')
    $priorRegistryLine = Get-ObjectProperty $validation 'execute_gate_prior_registry_line'
    $priorRegistrySha256 = [string](Get-ObjectProperty $validation 'execute_gate_prior_registry_sha256')
    $priorRegistryRowSha256 = [string](Get-ObjectProperty $validation 'execute_gate_prior_registry_row_sha256')
    if (
        [int]$priorRegistryLine -ne ([int]$Contract.RegistryLine - 1) -or
        -not (Test-Sha256Text $priorRegistrySha256) -or
        -not (Test-Sha256Text $priorRegistryRowSha256)
    ) {
        $Blockers.Add(
            "Model4 collection -Execute requires the actual prior authorization registry line, prefix SHA, and row SHA."
        )
    }

    $claimRelativePath = [string](Get-ObjectProperty $validation 'launch_claim_path')
    $expectedClaimRelativePath = Get-ExpectedModel4LaunchClaimRelativePath
    if ($claimRelativePath -cne $expectedClaimRelativePath) {
        $Blockers.Add("Model4 collection -Execute requires launch_claim_path to equal '$expectedClaimRelativePath'.")
    } else {
        $claimPath = Resolve-EvidencePath $claimRelativePath
        if (Test-Path -LiteralPath $claimPath -PathType Leaf) {
            $Blockers.Add("Model4 collection launch claim already exists; one-shot Execute was already claimed: $claimPath")
        }
    }

    $hardeningReceiptRaw = [string](Get-ObjectProperty $validation 'execute_gate_hardening_receipt_path')
    $hardeningReceiptExpectedSha = [string](Get-ObjectProperty $validation 'execute_gate_hardening_receipt_sha256')
    if ([string]::IsNullOrWhiteSpace($hardeningReceiptRaw) -or -not (Test-Sha256Text $hardeningReceiptExpectedSha)) {
        $Blockers.Add("Model4 collection -Execute requires execute_gate_hardening_receipt_path and execute_gate_hardening_receipt_sha256.")
        return
    }
    $hardeningReceiptPath = Resolve-EvidencePath $hardeningReceiptRaw
    $hardeningReceiptActualSha = Get-Sha256IfExists $hardeningReceiptPath
    if (-not (Test-Sha256Text $hardeningReceiptActualSha) -or $hardeningReceiptActualSha -ine $hardeningReceiptExpectedSha) {
        $Blockers.Add("Model4 collection execute-gate hardening receipt path/SHA is stale or missing.")
        return
    }
    try {
        $receipt = Get-Content -LiteralPath $hardeningReceiptPath -Raw | ConvertFrom-Json
    } catch {
        $Blockers.Add("Model4 collection execute-gate hardening receipt is malformed JSON: $($_.Exception.Message)")
        return
    }

    [void](Add-Model4ReceiptObjectBlockers $receipt @(
        'schema_version', 'hypothesis_id', 'classification', 'authority', 'verdict',
        'execution_authorized', 'full_suite_attested', 'prior_registry',
        'prior_bridge_receipt', 'prior_authority_receipt',
        'authorized_git_status', 'control_plane', 'bound_tests', 'launch_claim_path',
        'exact_test_run', 'exposure_readback'
    ) 'root' $Blockers)
    $receiptSchemaVersion = [string](Get-ObjectProperty $receipt 'schema_version')
    if ($receiptSchemaVersion -cne 'alphafactory_prelaunch_xau_model4_execute_gate_hardening.v5' -or
        [string](Get-ObjectProperty $receipt 'classification') -cne 'PRELAUNCH_XAU_MODEL4_REGISTRY_LOCK_FULL_SUITE_EXECUTE_AUTHORIZATION' -or
        [string](Get-ObjectProperty $receipt 'authority') -cne 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE' -or
        [string](Get-ObjectProperty $receipt 'verdict') -cne 'PASS_ONE_SHOT_XAU_REGISTRY_LOCK_FULL_SUITE_EXECUTE_GATE' -or
        (Get-ObjectProperty $receipt 'execution_authorized') -ne $true -or
        (Get-ObjectProperty $receipt 'full_suite_attested') -ne $true -or
        [string](Get-ObjectProperty $receipt 'hypothesis_id') -cne [string]$Contract.HypothesisId) {
        $Blockers.Add("Model4 collection execute-gate hardening receipt identity/verdict is invalid.")
    }
    $priorRegistry = Get-ObjectProperty $receipt 'prior_registry'
    if (Add-Model4ReceiptObjectBlockers $priorRegistry @('path', 'line', 'sha256', 'row_sha256') 'prior_registry' $Blockers) {
        if ([string](Get-ObjectProperty $priorRegistry 'path') -cne (Get-RepoRelativePath $Contract.RegistryPath) -or
            [int](Get-ObjectProperty $priorRegistry 'line') -ne [int]$priorRegistryLine -or
            [string](Get-ObjectProperty $priorRegistry 'sha256') -cne $priorRegistrySha256 -or
            [string](Get-ObjectProperty $priorRegistry 'row_sha256') -cne $priorRegistryRowSha256) {
            $Blockers.Add("Model4 collection execute-gate receipt prior_registry binding is invalid.")
        }
    }
    $priorBridgeReceipt = Get-ObjectProperty $receipt 'prior_bridge_receipt'
    if (Add-Model4ReceiptObjectBlockers $priorBridgeReceipt @('path', 'sha256') 'prior_bridge_receipt' $Blockers) {
        $expectedBridgeReceiptPath = (
            '03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/evidence/' +
            'HYP-PTR-T2-DATA-EPOCH-D0-M5-005/HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V4.json'
        )
        $bridgeReceiptPath = [string](Get-ObjectProperty $priorBridgeReceipt 'path')
        $bridgeReceiptSha = [string](Get-ObjectProperty $priorBridgeReceipt 'sha256')
        if (
            $bridgeReceiptPath -cne $expectedBridgeReceiptPath -or
            -not (Test-Sha256Text $bridgeReceiptSha) -or
            (Get-Sha256IfExists (Resolve-EvidencePath $bridgeReceiptPath)) -ine $bridgeReceiptSha
        ) {
            $Blockers.Add("Model4 collection execute-gate receipt is not bound to the V4 registry-lock bridge receipt.")
        }
    }
    $priorReceipt = Get-ObjectProperty $receipt 'prior_authority_receipt'
    if (Add-Model4ReceiptObjectBlockers $priorReceipt @('path', 'sha256') 'prior_authority_receipt' $Blockers) {
        $priorReceiptPath = [string](Get-ObjectProperty $priorReceipt 'path')
        $priorReceiptSha = [string](Get-ObjectProperty $priorReceipt 'sha256')
        if ($priorReceiptPath -cne [string](Get-ObjectProperty $validation 'packet_set_dry_run_receipt_path') -or
            $priorReceiptSha -cne [string](Get-ObjectProperty $validation 'packet_set_dry_run_receipt_sha256') -or
            (Get-Sha256IfExists (Resolve-EvidencePath $priorReceiptPath)) -ine $priorReceiptSha) {
            $Blockers.Add("Model4 collection execute-gate receipt is not bound to the packet-set dry-run receipt.")
        }
    }
    if ([string](Get-ObjectProperty $receipt 'launch_claim_path') -cne $expectedClaimRelativePath) {
        $Blockers.Add("Model4 collection execute-gate receipt launch_claim_path is not the frozen HYP005 path.")
    }
    [void](Test-Model4BoundTestBindings `
        (Get-ObjectProperty $receipt 'bound_tests') $Blockers 'execute-gate receipt')
    $exactTestRun = Get-ObjectProperty $receipt 'exact_test_run'
    if (Add-Model4ReceiptObjectBlockers $exactTestRun @(
        'framework', 'result', 'passed', 'failed', 'declared_test_file_count',
        'symbol', 'model', 'run_role', 'authority'
    ) 'exact_test_run' $Blockers) {
        if ([string](Get-ObjectProperty $exactTestRun 'framework') -cne 'pytest' -or
            [string](Get-ObjectProperty $exactTestRun 'result') -cne 'PASS' -or
            [int](Get-ObjectProperty $exactTestRun 'passed') -ne 124 -or
            [int](Get-ObjectProperty $exactTestRun 'failed') -ne 0 -or
            [int](Get-ObjectProperty $exactTestRun 'declared_test_file_count') -ne 10 -or
            [string](Get-ObjectProperty $exactTestRun 'symbol') -cne 'XAUUSD' -or
            [int](Get-ObjectProperty $exactTestRun 'model') -ne 4 -or
            [string](Get-ObjectProperty $exactTestRun 'run_role') -cne 'control' -or
            [string](Get-ObjectProperty $exactTestRun 'authority') -cne 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
            $Blockers.Add("Model4 collection execute-gate receipt exact_test_run is not the one-shot XAUUSD Model4 control.")
        }
    }
    $gitStatus = Get-ObjectProperty $receipt 'authorized_git_status'
    if (Add-Model4ReceiptObjectBlockers $gitStatus @('current_sha256') 'authorized_git_status' $Blockers) {
        if ([string](Get-ObjectProperty $gitStatus 'current_sha256') -cne [string]$Binding.GitStatusSha256) {
            $Blockers.Add("Model4 collection execute-gate receipt current git status binding is stale.")
        }
    }
    $receiptControlPlane = Get-ObjectProperty $receipt 'control_plane'
    if (Add-Model4ReceiptObjectBlockers $receiptControlPlane @('runner', 'candidate_registry_validator', 'alpha_entrypoint', 'execution_dependency_bindings') 'control_plane' $Blockers) {
        $expectedBindings = [ordered]@{
            runner = [pscustomobject]@{ Path = Get-RepoRelativePath $controlPlane.RunnerPath; Sha256 = $controlPlane.RunnerSha256 }
            candidate_registry_validator = [pscustomobject]@{ Path = Get-RepoRelativePath $controlPlane.ValidatorPath; Sha256 = $controlPlane.ValidatorSha256 }
            alpha_entrypoint = [pscustomobject]@{ Path = Get-RepoRelativePath $controlPlane.AlphaPath; Sha256 = $controlPlane.AlphaSha256 }
        }
        foreach ($name in $expectedBindings.Keys) {
            $node = Get-ObjectProperty $receiptControlPlane $name
            if (Add-Model4ReceiptObjectBlockers $node @('path', 'sha256') "control_plane.$name" $Blockers) {
                if ([string](Get-ObjectProperty $node 'path') -cne [string]$expectedBindings[$name].Path -or
                    [string](Get-ObjectProperty $node 'sha256') -cne [string]$expectedBindings[$name].Sha256) {
                    $Blockers.Add("Model4 collection execute-gate receipt control_plane.$name binding is stale.")
                }
            }
        }
        [void](Test-Model4ExecutionDependencyBindings `
            (Get-ObjectProperty $receiptControlPlane 'execution_dependency_bindings') `
            $executionDependencyBindings $Blockers 'execute-gate receipt')
    }
    $exposureReadback = Get-ObjectProperty $receipt 'exposure_readback'
    $exposureFields = @(
        'hyp005_execution_receipts', 'hyp005_run_manifests', 'launch_claims',
        'trades_executed', 'economic_trials_consumed'
    )
    if (Add-Model4ReceiptObjectBlockers $exposureReadback $exposureFields 'exposure_readback' $Blockers) {
        foreach ($name in $exposureFields) {
            $value = Get-ObjectProperty $exposureReadback $name
            if (-not (Test-IntegerValue $value) -or [int64]$value -ne 0) {
                $Blockers.Add("Model4 collection execute-gate receipt exposure_readback.$name must be zero.")
            }
        }
    }
}

function Add-Model4PostLockRevalidationBlockers(
    $Contract,
    $Binding,
    $PacketResult,
    [string]$RunnerPath,
    $Blockers
) {
    try {
        Assert-CandidateRegistryValid
    } catch {
        $Blockers.Add("Post-lock Model4 canonical candidate registry validation failed: $($_.Exception.Message)")
        return
    }
    try {
        $latestRegistryIdentity = Get-LatestCandidateRegistryIdentity $Contract.RegistryPath $Contract.HypothesisId
        if (
            [int]$latestRegistryIdentity.Line -ne [int]$Contract.RegistryLine -or
            [string]$latestRegistryIdentity.RowSha256 -cne [string]$Contract.RegistryRowSha256
        ) {
            $Blockers.Add(
                "Post-lock Model4 latest registry row identity changed " +
                "(expected line $($Contract.RegistryLine) row $($Contract.RegistryRowSha256); " +
                "actual line $($latestRegistryIdentity.Line) row $($latestRegistryIdentity.RowSha256))."
            )
            return
        }
    } catch {
        $Blockers.Add("Post-lock Model4 latest registry row identity check failed: $($_.Exception.Message)")
        return
    }
    $bindings = New-Object System.Collections.Generic.List[object]
    [void]$bindings.Add([pscustomobject]@{
        Path = $Contract.RegistryPath
        Sha256 = $Contract.RegistrySha256
        Label = 'candidate registry'
    })
    [void]$bindings.Add([pscustomobject]@{
        Path = $Contract.CanonicalSourceAbsolute
        Sha256 = $Contract.CurrentSourceSha256
        Label = 'canonical source'
    })
    [void]$bindings.Add([pscustomobject]@{
        Path = $Contract.PreregPath
        Sha256 = $Contract.PreregSha256
        Label = 'preregistration'
    })
    if (-not [string]::IsNullOrWhiteSpace([string]$Contract.EaContractAbsolutePath)) {
        [void]$bindings.Add([pscustomobject]@{
            Path = $Contract.EaContractAbsolutePath
            Sha256 = $Contract.EaContractSha256
            Label = 'EA capability contract'
        })
    }
    [void]$bindings.Add([pscustomobject]@{
        Path = $PacketResult.PacketPath
        Sha256 = $PacketResult.PacketSha256
        Label = 'task packet'
    })
    if (-not [string]::IsNullOrWhiteSpace([string]$PacketResult.CostSourceManifestPath)) {
        [void]$bindings.Add([pscustomobject]@{
            Path = $PacketResult.CostSourceManifestPath
            Sha256 = [string](Get-ObjectProperty $PacketResult.Packet 'cost_source_manifest_sha256')
            Label = 'cost-source manifest'
        })
    }
    foreach ($item in @($PacketResult.IncludeClosure)) {
        [void]$bindings.Add([pscustomobject]@{
            Path = $item.Path
            Sha256 = $item.Sha256
            Label = "include closure $($item.Path)"
        })
    }
    foreach ($item in @($PacketResult.CostEvidence)) {
        [void]$bindings.Add([pscustomobject]@{
            Path = $item.Path
            Sha256 = $item.Sha256
            Label = "cost evidence $($item.Path)"
        })
    }
    foreach ($item in $bindings) {
        $actualSha = Get-Sha256IfExists ([string]$item.Path)
        if (
            -not (Test-Sha256Text ([string]$item.Sha256)) -or
            -not (Test-Sha256Text $actualSha) -or
            $actualSha -ine [string]$item.Sha256
        ) {
            $Blockers.Add("Post-lock Model4 revalidation failed for $($item.Label).")
        }
    }
    Add-Model4CollectionLaunchAuthorityBlockers `
        $Contract $Binding $PacketResult $RunnerPath $Blockers
}

function Get-Model0EconomicAttemptPaths($Contract) {
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    $attemptId = [string](Get-ObjectProperty $validation 'mt5_attempt_id')
    if ($attemptId -notmatch '^[A-Z0-9-]+$') {
        throw "Model0 economic mt5_attempt_id is missing or unsafe."
    }
    $root = Join-Path $runtimeRoot ("model0_economic_attempts\{0}\{1}" -f $Contract.HypothesisId, $attemptId)
    return [pscustomobject]@{
        AttemptId = $attemptId
        Root = $root
        StartPath = Join-Path $root 'attempt_started.json'
        TerminalPath = Join-Path $root 'attempt_terminal.json'
    }
}

function Test-Hyp026EarlyModel0ClaimIdentity($Early, $Paths, $Contract, $PacketResult) {
    if ($null -eq $Early) { return $false }
    return (
        [string]$Early.Path -ceq [string]$Paths.StartPath -and
        [string]$Early.TerminalPath -ceq [string]$Paths.TerminalPath -and
        [string]$Early.Sha256 -ceq (Get-Sha256IfExists $Paths.StartPath) -and
        [string]$Early.RegistrySha256 -ceq [string]$Contract.RegistrySha256 -and
        [string]$Early.RegistryRowSha256 -ceq [string]$Contract.RegistryRowSha256 -and
        [string]$Early.TaskPacketPath -ceq (Get-RepoRelativePath $PacketResult.PacketPath) -and
        [string]$Early.TaskPacketSha256 -ceq [string]$PacketResult.PacketSha256
    )
}

function Add-Model0EconomicLaunchAuthorityBlockers(
    $Contract,
    $Binding,
    $PacketResult,
    [string]$RunnerPath,
    $Blockers
) {
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    if ([string](Get-ObjectProperty $validation 'authority') -cne 'MODEL0_TRAIN_FALSIFICATION_ONLY') {
        return
    }
    if (-not (Test-ScopedModel0EconomicPriorRegistryPacket `
        $PacketResult.Packet $Contract $Binding $PacketResult.PacketPath)) {
        $Blockers.Add("Model0 economic -Execute requires the exact packet-bound one-shot screened authority.")
        return
    }
    if ([string](Get-ObjectProperty $PacketResult.Packet 'inner_implementation_hypothesis_id') -cne 'HYP-STBS-XAUUSD-M15-026') {
        $Blockers.Add('HYP026 task packet must bind the exact inner MQL5/RunMeta/lifecycle identity HYP026.')
    }
    $runnerSha256 = Get-Sha256IfExists $RunnerPath
    if ([string](Get-ObjectProperty $validation 'reviewed_research_loop_sha256') -cne $runnerSha256) {
        $Blockers.Add("Model0 economic authority does not bind the current research-loop runner SHA256.")
    }
    if ([string](Get-ObjectProperty $validation 'reviewed_alpha_ps1_sha256') -cne (Get-Sha256IfExists $alphaPs1)) {
        $Blockers.Add("Model0 economic authority does not bind the current AlphaFactory entrypoint SHA256.")
    }
    foreach ($boundControl in @(
        [pscustomobject]@{ PathField = 'pre_execution_harness_addendum_path'; ShaField = 'pre_execution_harness_addendum_sha256'; Label = 'pre-execution harness addendum' },
        [pscustomobject]@{ PathField = 'reviewed_task_packet_builder_path'; ShaField = 'reviewed_task_packet_builder_sha256'; Label = 'task-packet builder' },
        [pscustomobject]@{ PathField = 'reviewed_registry_validator_path'; ShaField = 'reviewed_registry_validator_sha256'; Label = 'candidate-registry validator' },
        [pscustomobject]@{ PathField = 'reviewed_registry_model0_preexecution_test_path'; ShaField = 'reviewed_registry_model0_preexecution_test_sha256'; Label = 'Model0 registry hardening test' },
        [pscustomobject]@{ PathField = 'reviewed_cost_test_path'; ShaField = 'reviewed_cost_test_sha256'; Label = 'research-cost governance test' },
        [pscustomobject]@{ PathField = 'reviewed_ea_golden_path_test_path'; ShaField = 'reviewed_ea_golden_path_test_sha256'; Label = 'AlphaFactory golden-path test' },
        [pscustomobject]@{ PathField = 'reviewed_nonrepaint_auditor_path'; ShaField = 'reviewed_nonrepaint_auditor_sha256'; Label = 'HYP026 non-repaint auditor' },
        [pscustomobject]@{ PathField = 'reviewed_static_nonrepaint_manifest_path'; ShaField = 'reviewed_static_nonrepaint_manifest_sha256'; Label = 'HYP026 static non-repaint manifest' },
        [pscustomobject]@{ PathField = 'reviewed_static_nonrepaint_audit_path'; ShaField = 'reviewed_static_nonrepaint_audit_sha256'; Label = 'HYP026 static non-repaint audit' }
    )) {
        $relativePath = [string](Get-ObjectProperty $validation $boundControl.PathField)
        $expectedSha = [string](Get-ObjectProperty $validation $boundControl.ShaField)
        $absolutePath = if ([System.IO.Path]::IsPathRooted($relativePath)) {
            $relativePath
        } else {
            Join-Path $repoRoot $relativePath
        }
        if (-not (Test-Sha256Text $expectedSha) -or (Get-Sha256IfExists $absolutePath) -cne $expectedSha) {
            $Blockers.Add("Model0 economic authority does not bind the current $($boundControl.Label) bytes.")
        }
    }
    foreach ($exactControl in @(
        [pscustomobject]@{ PathField = 'reviewed_nonrepaint_auditor_path'; ShaField = 'reviewed_nonrepaint_auditor_sha256'; ExpectedPath = $nonRepaintToolPath; ExpectedSha = $hyp026NonRepaintAuditorSha256; Label = 'non-repaint auditor' },
        [pscustomobject]@{ PathField = 'reviewed_static_nonrepaint_manifest_path'; ShaField = 'reviewed_static_nonrepaint_manifest_sha256'; ExpectedPath = $hyp026StaticNonRepaintManifestPath; ExpectedSha = $hyp026StaticNonRepaintManifestSha256; Label = 'static non-repaint manifest' },
        [pscustomobject]@{ PathField = 'reviewed_static_nonrepaint_audit_path'; ShaField = 'reviewed_static_nonrepaint_audit_sha256'; ExpectedPath = $hyp026StaticNonRepaintAuditPath; ExpectedSha = $hyp026StaticNonRepaintAuditSha256; Label = 'static non-repaint audit' }
    )) {
        $declaredPath = [string](Get-ObjectProperty $validation $exactControl.PathField)
        $resolvedPath = if ([System.IO.Path]::IsPathRooted($declaredPath)) {
            [System.IO.Path]::GetFullPath($declaredPath)
        } else {
            [System.IO.Path]::GetFullPath((Join-Path $repoRoot $declaredPath))
        }
        if (-not [string]::Equals($resolvedPath, [System.IO.Path]::GetFullPath($exactControl.ExpectedPath), [System.StringComparison]::OrdinalIgnoreCase) -or
            [string](Get-ObjectProperty $validation $exactControl.ShaField) -cne $exactControl.ExpectedSha) {
            $Blockers.Add("Model0 economic authority does not bind the exact HYP026 $($exactControl.Label) path/SHA256.")
        }
    }
    if ((Get-ObjectProperty $PacketResult.Packet 'performance_metrics_authorized') -ne $true -or
        (Get-ObjectProperty $PacketResult.Packet 'economics_authorized') -ne $true -or
        (Get-ObjectProperty $PacketResult.Packet 'promotion_eligible') -ne $false) {
        $Blockers.Add("Model0 economic packet permissions require performance_metrics_authorized=true, economics_authorized=true, promotion_eligible=false.")
    }
    $packetAttemptStart = '03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/evidence/HYP-STBS-XAUUSD-M15-026/STBS026-PACKET-BUILD-001/attempt_started.json'
    $packetAttemptTerminal = '03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/evidence/HYP-STBS-XAUUSD-M15-026/STBS026-PACKET-BUILD-001/attempt_terminal.json'
    if (
        [string](Get-ObjectProperty $validation 'packet_build_attempt_id') -cne 'STBS026-PACKET-BUILD-001' -or
        [int](Get-ObjectProperty $validation 'packet_build_attempt_limit') -ne 1 -or
        [int](Get-ObjectProperty (Get-ObjectProperty $Contract.LatestRow 'metrics') 'packet_build_attempts_consumed') -ne 1 -or
        [string](Get-ObjectProperty $validation 'packet_build_attempt_start_path') -cne $packetAttemptStart -or
        -not (Test-Sha256Text ([string](Get-ObjectProperty $validation 'packet_build_attempt_start_sha256'))) -or
        [string](Get-ObjectProperty $validation 'packet_build_attempt_terminal_path') -cne $packetAttemptTerminal -or
        -not (Test-Sha256Text ([string](Get-ObjectProperty $validation 'packet_build_attempt_terminal_sha256'))) -or
        [string](Get-ObjectProperty $validation 'gitignore_path') -cne '.gitignore' -or
        -not (Test-Sha256Text ([string](Get-ObjectProperty $validation 'gitignore_sha256')))
    ) {
        $Blockers.Add("Model0 economic authority does not bind the exact completed HYP026 packet-build attempt metadata.")
    }
    $declaredReservedReview = [string](Get-ObjectProperty $validation 'reserved_post_packet_review_path')
    $declaredPlaceholderSha = [string](Get-ObjectProperty $validation 'reserved_post_packet_review_placeholder_sha256')
    $declaredFinalReview = [string](Get-ObjectProperty $validation 'independent_post_packet_review_path')
    $declaredFinalReviewSha = [string](Get-ObjectProperty $validation 'independent_post_packet_review_sha256')
    if (
        $declaredReservedReview -cne $hyp026ReservedPostPacketReviewRelative -or
        $declaredPlaceholderSha -cne $hyp026ReservedPostPacketReviewPlaceholderSha256 -or
        $declaredFinalReview -cne $hyp026ReservedPostPacketReviewRelative -or
        -not (Test-Sha256Text $declaredFinalReviewSha) -or
        $declaredFinalReviewSha -ceq $hyp026ReservedPostPacketReviewPlaceholderSha256 -or
        [string](Get-ObjectProperty $PacketResult.Packet 'reserved_post_packet_review_path') -cne $hyp026ReservedPostPacketReviewRelative -or
        [string](Get-ObjectProperty $PacketResult.Packet 'reserved_post_packet_review_placeholder_sha256') -cne $hyp026ReservedPostPacketReviewPlaceholderSha256 -or
        [string](Get-ObjectProperty $PacketResult.Packet 'reserved_post_packet_review_status_line') -cne $hyp026ReservedPostPacketReviewStatusLine
    ) {
        $Blockers.Add("Model0 economic authority does not bind the exact reserved-to-final HYP026 post-packet review contract.")
    }
    if (
        [string](Get-ObjectProperty $Contract.LatestRow 'parent_candidate') -cne 'HYP-STBS-XAUUSD-M15-025' -or
        [string](Get-ObjectProperty $validation 'parent_hyp025_terminal_row_sha256') -cne $hyp026ParentTerminalRowSha256 -or
        [string](Get-ObjectProperty $validation 'parent_hyp025_terminal_verdict') -cne $hyp026ParentTerminalVerdict -or
        [string](Get-ObjectProperty $PacketResult.Packet 'parent_hypothesis_id') -cne 'HYP-STBS-XAUUSD-M15-025' -or
        [string](Get-ObjectProperty $PacketResult.Packet 'parent_terminal_row_sha256') -cne $hyp026ParentTerminalRowSha256 -or
        [string](Get-ObjectProperty $PacketResult.Packet 'parent_terminal_verdict') -cne $hyp026ParentTerminalVerdict
    ) {
        $Blockers.Add("Model0 economic authority does not bind the exact terminal HYP025 post-claim parent.")
    }
    if (
        [string](Get-ObjectProperty $validation 'exact_outer_hypothesis_id') -cne 'HYP-STBS-XAUUSD-M15-026' -or
        [string](Get-ObjectProperty $validation 'exact_inner_mql_identity') -cne 'HYP-STBS-XAUUSD-M15-026'
    ) {
        $Blockers.Add("Model0 economic authority does not bind the exact HYP026 outer/inner identity contract.")
    }
    foreach ($governanceInput in @(
        [pscustomobject]@{ ValidationPath = 'parent_hyp025_failure_path'; ValidationSha = 'parent_hyp025_failure_sha256'; PacketPath = 'parent_failure_packet_path'; PacketSha = 'parent_failure_packet_sha256'; ExpectedPath = $hyp026ParentFailurePacketRelative; ExpectedSha = $hyp026ParentFailurePacketSha256; Label = 'HYP025 failure note' },
        [pscustomobject]@{ ValidationPath = 'parent_hyp025_post_failure_review_path'; ValidationSha = 'parent_hyp025_post_failure_review_sha256'; PacketPath = 'parent_post_failure_review_path'; PacketSha = 'parent_post_failure_review_sha256'; ExpectedPath = $hyp026ParentFailureReviewRelative; ExpectedSha = $hyp026ParentFailureReviewSha256; Label = 'HYP025 failure review' },
        [pscustomobject]@{ ValidationPath = 'journal_budget_tester_projection_path'; ValidationSha = 'journal_budget_tester_projection_sha256'; PacketPath = 'journal_budget_tester_projection_path'; PacketSha = 'journal_budget_tester_projection_sha256'; ExpectedPath = $hyp026TesterProjectionRelative; ExpectedSha = $hyp026TesterProjectionSha256; Label = 'Tester no-spam projection' },
        [pscustomobject]@{ ValidationPath = 'journal_budget_agent_projection_path'; ValidationSha = 'journal_budget_agent_projection_sha256'; PacketPath = 'journal_budget_agent_projection_path'; PacketSha = 'journal_budget_agent_projection_sha256'; ExpectedPath = $hyp026AgentProjectionRelative; ExpectedSha = $hyp026AgentProjectionSha256; Label = 'Agent no-spam projection' },
        [pscustomobject]@{ ValidationPath = 'journal_budget_addendum_path'; ValidationSha = 'journal_budget_addendum_sha256'; PacketPath = 'journal_budget_addendum_path'; PacketSha = 'journal_budget_addendum_sha256'; ExpectedPath = $hyp026JournalBudgetAddendumRelative; ExpectedSha = $hyp026JournalBudgetAddendumSha256; Label = 'journal-budget addendum' },
        [pscustomobject]@{ ValidationPath = 'pre_execution_harness_addendum_path'; ValidationSha = 'pre_execution_harness_addendum_sha256'; PacketPath = 'pre_execution_harness_addendum_path'; PacketSha = 'pre_execution_harness_addendum_sha256'; ExpectedPath = $hyp026PreExecutionHarnessAddendumRelative; ExpectedSha = $hyp026PreExecutionHarnessAddendumSha256; Label = 'pre-execution harness addendum' },
        [pscustomobject]@{ ValidationPath = 'independent_pre_run_review_path'; ValidationSha = 'independent_pre_run_review_sha256'; PacketPath = 'independent_pre_run_review_path'; PacketSha = 'independent_pre_run_review_sha256'; ExpectedPath = $hyp026IndependentPreProbeReviewRelative; ExpectedSha = $hyp026IndependentPreProbeReviewSha256; Label = 'independent pre-probe review' },
        [pscustomobject]@{ ValidationPath = 'bounded_diff_proof_path'; ValidationSha = 'bounded_diff_proof_sha256'; PacketPath = 'bounded_diff_proof_path'; PacketSha = 'bounded_diff_proof_sha256'; ExpectedPath = $hyp026BoundedDiffProofRelative; ExpectedSha = $hyp026BoundedDiffProofSha256; Label = 'V12-to-V13 post-claim reconciliation diff proof' },
        [pscustomobject]@{ ValidationPath = 'source_contract_test_path'; ValidationSha = 'source_contract_test_sha256'; PacketPath = 'source_contract_test_path'; PacketSha = 'source_contract_test_sha256'; ExpectedPath = $hyp026CompactTelemetryTestRelative; ExpectedSha = $hyp026CompactTelemetryTestSha256; Label = 'compact telemetry contract test' }
    )) {
        if (
            [string](Get-ObjectProperty $validation $governanceInput.ValidationPath) -cne $governanceInput.ExpectedPath -or
            [string](Get-ObjectProperty $validation $governanceInput.ValidationSha) -cne $governanceInput.ExpectedSha -or
            [string](Get-ObjectProperty $PacketResult.Packet $governanceInput.PacketPath) -cne $governanceInput.ExpectedPath -or
            [string](Get-ObjectProperty $PacketResult.Packet $governanceInput.PacketSha) -cne $governanceInput.ExpectedSha
        ) {
            $Blockers.Add("Model0 economic authority/packet does not bind the exact $($governanceInput.Label).")
        }
    }
    if (
        [int64](Get-ObjectProperty $validation 'journal_budget_tester_projection_bytes') -ne $hyp026TesterProjectionBytes -or
        [int64](Get-ObjectProperty $validation 'journal_budget_agent_projection_bytes') -ne $hyp026AgentProjectionBytes -or
        [int64](Get-ObjectProperty $PacketResult.Packet 'journal_budget_tester_projection_bytes') -ne $hyp026TesterProjectionBytes -or
        [int64](Get-ObjectProperty $PacketResult.Packet 'journal_budget_agent_projection_bytes') -ne $hyp026AgentProjectionBytes -or
        [int64](Get-ObjectProperty $PacketResult.Packet 'journal_budget_projected_combined_bytes') -ne ($hyp026TesterProjectionBytes + $hyp026AgentProjectionBytes)
    ) {
        $Blockers.Add("Model0 economic authority/packet does not bind the exact HYP023 no-spam replay byte budget.")
    }
    $registeredBaseline = Get-ObjectProperty $validation 'baseline_acceptance_contract'
    $packetBaseline = $PacketResult.BaselineAcceptanceContract
    $baselineFieldMap = [ordered]@{
        min_completed_trades = 'min_completed_trades'
        min_direction_share = 'min_direction_share'
        max_year_trade_share = 'max_year_trade_share'
        require_positive_mean_x1_net_r = 'require_positive_cost_expectancy'
        require_each_calendar_year_positive_x1_net_r = 'require_all_calendar_years_positive'
    }
    if (-not (Test-ProvenanceObject $registeredBaseline) -or -not (Test-ProvenanceObject $packetBaseline)) {
        $Blockers.Add("Model0 economic authority and task packet both require baseline_acceptance_contract.")
    } else {
        foreach ($registeredField in $baselineFieldMap.Keys) {
            $packetField = [string]$baselineFieldMap[$registeredField]
            if ((Get-ObjectProperty $registeredBaseline $registeredField) -ne (Get-ObjectProperty $packetBaseline $packetField)) {
                $Blockers.Add("Model0 economic baseline_acceptance_contract.$registeredField differs from task packet $packetField.")
            }
        }
    }
    foreach ($field in @(
        'mt5_train_run_authorized', 'mt5_authorized', 'model0_authorized',
        'model0_data_acquisition_authorized', 'model0_performance_authorized',
        'source_run_authorized', 'run_compile_authorized', 'mql5_compile_authorized',
        'trade_api_authorized', 'performance_metrics_authorized', 'outcome_prices_authorized',
        'post_event_ohlc_authorized', 'artifact_collection_authorized',
        'economics_authorized', 'research_falsification_authorized'
    )) {
        if ((Get-ObjectProperty $validation $field) -ne $true) {
            $Blockers.Add("Model0 economic authority requires validation.$field=true.")
        }
    }
    foreach ($field in @(
        'packet_build_authorized', 'model0_audit_run_authorized', 'model4_authorized',
        'model4_data_acquisition_authorized', 'model4_performance_authorized',
        'compile_authorized', 'standalone_compile_authorized', 'comparator_execution_authorized',
        'visual_mode_authorized', 'network_authorized', 'paid_requests_authorized',
        'optimization_authorized', 'validation_authorized', 'holdout_authorized',
        'research_validation_access_authorized', 'research_holdout_access_authorized',
        'validation_access_authorized', 'holdout_access_authorized',
        'economic_validity_authorized', 'promotion_eligible', 'paper_trading_authorized',
        'live_trading_authorized', 'market_edge_claim_authorized',
        'same_id_retry_authorized', 'registry_mutation_allowed'
    )) {
        if ((Get-ObjectProperty $validation $field) -ne $false) {
            $Blockers.Add("Model0 economic authority requires validation.$field=false.")
        }
    }
    try {
        $paths = Get-Model0EconomicAttemptPaths $Contract
        if ($Contract.HypothesisId -ceq 'HYP-STBS-XAUUSD-M15-026' -and $Execute) {
            $early = $script:earlyModel0EconomicAttemptRecord
            if ($null -eq $early) {
                $Blockers.Add('HYP026 post-claim validation requires the exact in-memory early Model0 record.')
            } elseif (-not (Test-Hyp026EarlyModel0ClaimIdentity $early $paths $Contract $PacketResult)) {
                $Blockers.Add('HYP026 post-claim early Model0 record does not reconcile path/hash/registry/task-packet identity.')
            }
            if (Test-Path -LiteralPath $paths.TerminalPath) {
                $Blockers.Add("HYP026 post-claim terminal already exists: $($paths.TerminalPath)")
            }
        } else {
            if (Test-Path -LiteralPath $paths.StartPath) {
                $Blockers.Add("Model0 economic one-shot attempt is already consumed: $($paths.StartPath)")
            }
            if (Test-Path -LiteralPath $paths.TerminalPath) {
                $Blockers.Add("Model0 economic one-shot terminal already exists: $($paths.TerminalPath)")
            }
        }
    } catch {
        $Blockers.Add($_.Exception.Message)
    }
}

function New-Model0EconomicLaunchClaim($Contract, $Binding, $PacketResult) {
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    if ([string](Get-ObjectProperty $validation 'one_shot_economic_harness_version') -cne 'model0-economic-one-shot-v1') {
        return $null
    }
    if ($Contract.HypothesisId -ceq 'HYP-STBS-XAUUSD-M15-026') {
        $early = $script:earlyModel0EconomicAttemptRecord
        if ($null -eq $early) {
            throw 'HYP026 execution reached post-claim validation without the durable early Model0 claim.'
        }
        $paths = Get-Model0EconomicAttemptPaths $Contract
        if (-not (Test-Hyp026EarlyModel0ClaimIdentity $early $paths $Contract $PacketResult)) {
            throw 'HYP026 post-claim registry/task-packet reconciliation failed.'
        }
        return $early
    }
    $paths = Get-Model0EconomicAttemptPaths $Contract
    New-Item -ItemType Directory -Path (Split-Path -Parent $paths.Root) -Force | Out-Null
    New-Item -ItemType Directory -Path $paths.Root -ErrorAction Stop | Out-Null
    $claim = [ordered]@{
        schema_version = 'alphafactory_model0_economic_attempt_started.v1'
        hypothesis_id = $Contract.HypothesisId
        attempt_id = $paths.AttemptId
        registry_line = [int]$Contract.RegistryLine
        registry_row_sha256 = [string]$Contract.RegistryRowSha256
        task_packet_path = Get-RepoRelativePath $PacketResult.PacketPath
        task_packet_sha256 = [string]$PacketResult.PacketSha256
        timeout_sec = [int]$Binding.TimeoutSec
        model = [int]$Binding.Model
        run_role = [string]$Binding.RunRole
        claimed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $json = $claim | ConvertTo-Json -Depth 10
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $stream = [System.IO.File]::Open(
        $paths.StartPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally {
        $stream.Dispose()
    }
    return [pscustomobject]@{
        Kind = 'model0_economic'
        AttemptId = $paths.AttemptId
        Path = $paths.StartPath
        Sha256 = Get-Sha256IfExists $paths.StartPath
        TerminalPath = $paths.TerminalPath
    }
}

function Assert-Hyp026PacketBuildChain($Contract, $PacketResult, $LaunchClaimRecord) {
    if ($Contract.HypothesisId -cne 'HYP-STBS-XAUUSD-M15-026') {
        return
    }
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    $metrics = Get-ObjectProperty $Contract.LatestRow 'metrics'
    $expectedStart = '03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/evidence/HYP-STBS-XAUUSD-M15-026/STBS026-PACKET-BUILD-001/attempt_started.json'
    $expectedTerminal = '03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/evidence/HYP-STBS-XAUUSD-M15-026/STBS026-PACKET-BUILD-001/attempt_terminal.json'
    $startRelative = [string](Get-ObjectProperty $validation 'packet_build_attempt_start_path')
    $terminalRelative = [string](Get-ObjectProperty $validation 'packet_build_attempt_terminal_path')
    $startSha = [string](Get-ObjectProperty $validation 'packet_build_attempt_start_sha256')
    $terminalSha = [string](Get-ObjectProperty $validation 'packet_build_attempt_terminal_sha256')
    $gitignoreRelative = [string](Get-ObjectProperty $validation 'gitignore_path')
    $gitignoreSha = [string](Get-ObjectProperty $validation 'gitignore_sha256')
    $reservedReviewRelative = [string](Get-ObjectProperty $validation 'reserved_post_packet_review_path')
    $placeholderReviewSha = [string](Get-ObjectProperty $validation 'reserved_post_packet_review_placeholder_sha256')
    $finalReviewRelative = [string](Get-ObjectProperty $validation 'independent_post_packet_review_path')
    $finalReviewSha = [string](Get-ObjectProperty $validation 'independent_post_packet_review_sha256')
    if (
        [string](Get-ObjectProperty $validation 'packet_build_attempt_id') -cne 'STBS026-PACKET-BUILD-001' -or
        [int](Get-ObjectProperty $validation 'packet_build_attempt_limit') -ne 1 -or
        [int](Get-ObjectProperty $metrics 'packet_build_attempts_consumed') -ne 1 -or
        $startRelative -cne $expectedStart -or
        $terminalRelative -cne $expectedTerminal -or
        $gitignoreRelative -cne '.gitignore' -or
        $reservedReviewRelative -cne $hyp026ReservedPostPacketReviewRelative -or
        $placeholderReviewSha -cne $hyp026ReservedPostPacketReviewPlaceholderSha256 -or
        $finalReviewRelative -cne $hyp026ReservedPostPacketReviewRelative -or
        -not (Test-Sha256Text $finalReviewSha) -or
        $finalReviewSha -ceq $placeholderReviewSha
    ) {
        throw 'HYP026 packet-build authority metadata is not exact.'
    }
    $startPath = Resolve-EvidencePath $startRelative
    $terminalPath = Resolve-EvidencePath $terminalRelative
    $gitignorePath = Resolve-EvidencePath $gitignoreRelative
    $finalReviewPath = Resolve-EvidencePath $finalReviewRelative
    if (
        (Get-Sha256IfExists $startPath) -cne $startSha -or
        (Get-Sha256IfExists $terminalPath) -cne $terminalSha -or
        (Get-Sha256IfExists $gitignorePath) -cne $gitignoreSha -or
        (Get-Sha256IfExists $finalReviewPath) -cne $finalReviewSha -or
        (Get-Sha256IfExists $PacketResult.PacketPath) -cne [string]$PacketResult.PacketSha256
    ) {
        throw 'HYP026 packet-build chain file hash mismatch.'
    }
    $start = Get-Content -LiteralPath $startPath -Raw | ConvertFrom-Json
    $terminal = Get-Content -LiteralPath $terminalPath -Raw | ConvertFrom-Json
    if (-not (Test-ExactObjectKeys $start @(
            'schema_version', 'hypothesis_id', 'attempt_id', 'builder_path', 'claimed_at_utc'
        )) -or
        -not (Test-ExactObjectKeys $terminal @(
            'schema_version', 'hypothesis_id', 'attempt_id', 'status',
            'attempt_started_path', 'attempt_started_sha256', 'packet_path',
            'packet_sha256', 'error', 'same_id_retry_authorized', 'completed_at_utc'
        ))) {
        throw 'HYP026 packet-build start/terminal schema is not exact.'
    }
    if (
        [string]$start.schema_version -cne 'alphafactory_packet_attempt_started.v1' -or
        [string]$start.hypothesis_id -cne 'HYP-STBS-XAUUSD-M15-026' -or
        [string]$start.attempt_id -cne 'STBS026-PACKET-BUILD-001' -or
        [string]$start.builder_path -cne '03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/build_stbs026_task_packet.py' -or
        [string]$terminal.schema_version -cne 'alphafactory_packet_attempt_terminal.v1' -or
        [string]$terminal.hypothesis_id -cne 'HYP-STBS-XAUUSD-M15-026' -or
        [string]$terminal.attempt_id -cne 'STBS026-PACKET-BUILD-001' -or
        [string]$terminal.status -cne 'COMPLETE' -or
        $null -ne $terminal.error -or
        $terminal.same_id_retry_authorized -ne $false -or
        [string]$terminal.attempt_started_path -cne $expectedStart -or
        [string]$terminal.attempt_started_sha256 -cne $startSha -or
        [string]$terminal.packet_path -cne (Get-RepoRelativePath $PacketResult.PacketPath) -or
        [string]$terminal.packet_sha256 -cne [string]$PacketResult.PacketSha256 -or
        [string](Get-ObjectProperty $PacketResult.Packet 'packet_build_attempt_id') -cne 'STBS026-PACKET-BUILD-001' -or
        [string](Get-ObjectProperty $PacketResult.Packet 'packet_build_attempt_start_path') -cne $expectedStart -or
        [string](Get-ObjectProperty $PacketResult.Packet 'packet_build_attempt_start_sha256') -cne $startSha -or
        [string](Get-ObjectProperty $PacketResult.Packet 'gitignore_path') -cne '.gitignore' -or
        [string](Get-ObjectProperty $PacketResult.Packet 'gitignore_sha256') -cne $gitignoreSha -or
        [string](Get-ObjectProperty $PacketResult.Packet 'reserved_post_packet_review_path') -cne $hyp026ReservedPostPacketReviewRelative -or
        [string](Get-ObjectProperty $PacketResult.Packet 'reserved_post_packet_review_placeholder_sha256') -cne $hyp026ReservedPostPacketReviewPlaceholderSha256 -or
        [string](Get-ObjectProperty $PacketResult.Packet 'reserved_post_packet_review_status_line') -cne $hyp026ReservedPostPacketReviewStatusLine
    ) {
        throw 'HYP026 packet-build start/terminal/packet semantic chain is invalid.'
    }
    $reviewStatusMatches = @(
        @(Get-ObjectProperty $PacketResult.Packet 'git_status') |
            Where-Object { [string]$_ -ceq $hyp026ReservedPostPacketReviewStatusLine }
    )
    $finalReviewLines = @(Get-Content -LiteralPath $finalReviewPath)
    $expectedReviewLines = @(
        'schema_version: stbs026_post_packet_review.v1',
        'hypothesis_id: HYP-STBS-XAUUSD-M15-026',
        ('packet_sha256: {0}' -f [string]$PacketResult.PacketSha256),
        ('packet_terminal_sha256: {0}' -f $terminalSha),
        'verdict: PASS_SCREENED_AUTHORITY'
    )
    $reviewExact = $finalReviewLines.Count -eq $expectedReviewLines.Count
    if ($reviewExact) {
        for ($reviewLineIndex = 0; $reviewLineIndex -lt $expectedReviewLines.Count; $reviewLineIndex++) {
            if ([string]$finalReviewLines[$reviewLineIndex] -cne [string]$expectedReviewLines[$reviewLineIndex]) {
                $reviewExact = $false
                break
            }
        }
    }
    if ($reviewStatusMatches.Count -ne 1 -or -not $reviewExact) {
        throw 'HYP026 final post-packet review is not the exact five-line packet/terminal-bound PASS_SCREENED_AUTHORITY control.'
    }
    $parentMatches = New-Object System.Collections.Generic.List[object]
    foreach ($rawRegistryLine in @(Get-Content -LiteralPath $Contract.RegistryPath)) {
        if ((Get-TextSha256 ([string]$rawRegistryLine)) -ceq $hyp026ParentTerminalRowSha256) {
            $parentMatches.Add(([string]$rawRegistryLine | ConvertFrom-Json))
        }
    }
    if (
        $parentMatches.Count -ne 1 -or
        [string]$parentMatches[0].hypothesis_id -cne 'HYP-STBS-XAUUSD-M15-025' -or
        [string]$parentMatches[0].state -cne 'killed' -or
        [string]$parentMatches[0].verdict -cne $hyp026ParentTerminalVerdict
    ) {
        throw 'HYP026 current registry does not contain the exact hash-bound terminal HYP025 parent row.'
    }
    foreach ($governanceInput in @(
        [pscustomobject]@{ PathField = 'parent_hyp025_failure_path'; ShaField = 'parent_hyp025_failure_sha256'; ExpectedPath = $hyp026ParentFailurePacketRelative; ExpectedSha = $hyp026ParentFailurePacketSha256; ExpectedBytes = $null },
        [pscustomobject]@{ PathField = 'parent_hyp025_post_failure_review_path'; ShaField = 'parent_hyp025_post_failure_review_sha256'; ExpectedPath = $hyp026ParentFailureReviewRelative; ExpectedSha = $hyp026ParentFailureReviewSha256; ExpectedBytes = $null },
        [pscustomobject]@{ PathField = 'journal_budget_tester_projection_path'; ShaField = 'journal_budget_tester_projection_sha256'; ExpectedPath = $hyp026TesterProjectionRelative; ExpectedSha = $hyp026TesterProjectionSha256; ExpectedBytes = $hyp026TesterProjectionBytes },
        [pscustomobject]@{ PathField = 'journal_budget_agent_projection_path'; ShaField = 'journal_budget_agent_projection_sha256'; ExpectedPath = $hyp026AgentProjectionRelative; ExpectedSha = $hyp026AgentProjectionSha256; ExpectedBytes = $hyp026AgentProjectionBytes },
        [pscustomobject]@{ PathField = 'journal_budget_addendum_path'; ShaField = 'journal_budget_addendum_sha256'; ExpectedPath = $hyp026JournalBudgetAddendumRelative; ExpectedSha = $hyp026JournalBudgetAddendumSha256; ExpectedBytes = $null },
        [pscustomobject]@{ PathField = 'pre_execution_harness_addendum_path'; ShaField = 'pre_execution_harness_addendum_sha256'; ExpectedPath = $hyp026PreExecutionHarnessAddendumRelative; ExpectedSha = $hyp026PreExecutionHarnessAddendumSha256; ExpectedBytes = $null },
        [pscustomobject]@{ PathField = 'independent_pre_run_review_path'; ShaField = 'independent_pre_run_review_sha256'; ExpectedPath = $hyp026IndependentPreProbeReviewRelative; ExpectedSha = $hyp026IndependentPreProbeReviewSha256; ExpectedBytes = $null },
        [pscustomobject]@{ PathField = 'bounded_diff_proof_path'; ShaField = 'bounded_diff_proof_sha256'; ExpectedPath = $hyp026BoundedDiffProofRelative; ExpectedSha = $hyp026BoundedDiffProofSha256; ExpectedBytes = $null },
        [pscustomobject]@{ PathField = 'source_contract_test_path'; ShaField = 'source_contract_test_sha256'; ExpectedPath = $hyp026CompactTelemetryTestRelative; ExpectedSha = $hyp026CompactTelemetryTestSha256; ExpectedBytes = $null }
    )) {
        $declaredPath = [string](Get-ObjectProperty $validation $governanceInput.PathField)
        $declaredSha = [string](Get-ObjectProperty $validation $governanceInput.ShaField)
        $absolutePath = Resolve-EvidencePath $declaredPath
        if (
            $declaredPath -cne $governanceInput.ExpectedPath -or
            $declaredSha -cne $governanceInput.ExpectedSha -or
            (Get-Sha256IfExists $absolutePath) -cne $governanceInput.ExpectedSha -or
            ($null -ne $governanceInput.ExpectedBytes -and (Get-Item -LiteralPath $absolutePath).Length -ne [int64]$governanceInput.ExpectedBytes)
        ) {
            throw "HYP026 governance/cap evidence drifted: $($governanceInput.ExpectedPath)"
        }
    }
    if ($null -eq $LaunchClaimRecord -or -not (Test-Path -LiteralPath $LaunchClaimRecord.Path -PathType Leaf)) {
        throw 'HYP026 Model0 launch claim is absent before packet-build chain validation.'
    }
    $launch = Get-Content -LiteralPath $LaunchClaimRecord.Path -Raw | ConvertFrom-Json
    $startAt = [datetimeoffset]::Parse([string]$start.claimed_at_utc)
    $terminalAt = [datetimeoffset]::Parse([string]$terminal.completed_at_utc)
    $authorityAt = [datetimeoffset]::Parse([string](Get-ObjectProperty $Contract.LatestRow 'updated_at_utc'))
    $launchAt = [datetimeoffset]::Parse([string]$launch.claimed_at_utc)
    if (-not ($startAt -le $terminalAt -and $terminalAt -le $authorityAt -and $authorityAt -le $launchAt)) {
        throw 'HYP026 packet-build/start/terminal/authority/launch chronology is invalid.'
    }
}

function Write-Model0EconomicAttemptTerminal($AttemptRecord, [string]$Status, $RunId, $RunDir, [string]$ErrorMessage = '') {
    if ($null -eq $AttemptRecord -or [string]$AttemptRecord.Kind -cne 'model0_economic') {
        return $null
    }
    if ($Status -notin @('COMPLETE', 'FAILED')) {
        throw "Unsupported Model0 economic terminal status '$Status'."
    }
    $terminal = [ordered]@{
        schema_version = 'alphafactory_model0_economic_attempt_terminal.v1'
        hypothesis_id = $HypothesisId
        attempt_id = [string]$AttemptRecord.AttemptId
        status = $Status
        attempt_started_path = [string]$AttemptRecord.Path
        attempt_started_sha256 = [string]$AttemptRecord.Sha256
        run_id = $RunId
        run_dir = $RunDir
        error = $ErrorMessage
        same_id_retry_authorized = $false
        terminal_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $json = $terminal | ConvertTo-Json -Depth 10
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $stream = [System.IO.File]::Open(
        [string]$AttemptRecord.TerminalPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally {
        $stream.Dispose()
    }
    return [pscustomobject]@{
        Path = [string]$AttemptRecord.TerminalPath
        Sha256 = Get-Sha256IfExists ([string]$AttemptRecord.TerminalPath)
    }
}

function New-Model4CollectionLaunchClaim($Contract, $Binding, $PacketResult, [string]$RunnerPath) {
    if ([string]$PacketResult.Authority -cne 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        return $null
    }
    $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
    $claimRelativePath = [string](Get-ObjectProperty $validation 'launch_claim_path')
    if ($claimRelativePath -cne (Get-ExpectedModel4LaunchClaimRelativePath)) {
        throw "Model4 collection launch_claim_path is not the frozen one-shot HYP005 path."
    }
    $claimPath = Resolve-EvidencePath $claimRelativePath
    $controlPlane = Get-Model4ControlPlaneBinding $RunnerPath
    $executionDependencyBindings = @(Get-Model4ExecutionDependencyBindings $RunnerPath)
    $claim = [ordered]@{
        schema_version = 'alphafactory_model4_collection_launch_claim.v1'
        hypothesis_id = $Contract.HypothesisId
        authority = [string]$PacketResult.Authority
        symbol = [string]$Binding.Symbol
        model = [int]$Binding.Model
        task_packet_path = Get-RepoRelativePath $PacketResult.PacketPath
        task_packet_sha256 = [string]$PacketResult.PacketSha256
        registry_path = Get-RepoRelativePath $Contract.RegistryPath
        registry_sha256 = [string](Get-ObjectProperty $PacketResult.Packet 'registry_sha256')
        registry_row_sha256 = [string](Get-ObjectProperty $PacketResult.Packet 'registry_row_sha256')
        authorization_registry_sha256 = [string]$Contract.RegistrySha256
        authorization_registry_row_sha256 = [string]$Contract.RegistryRowSha256
        execute_gate_hardening_receipt_path = [string](Get-ObjectProperty $validation 'execute_gate_hardening_receipt_path')
        execute_gate_hardening_receipt_sha256 = [string](Get-ObjectProperty $validation 'execute_gate_hardening_receipt_sha256')
        runner = [ordered]@{
            path = Get-RepoRelativePath $controlPlane.RunnerPath
            sha256 = $controlPlane.RunnerSha256
        }
        candidate_registry_validator = [ordered]@{
            path = Get-RepoRelativePath $controlPlane.ValidatorPath
            sha256 = $controlPlane.ValidatorSha256
        }
        alpha_entrypoint = [ordered]@{
            path = Get-RepoRelativePath $controlPlane.AlphaPath
            sha256 = $controlPlane.AlphaSha256
        }
        execution_dependency_bindings = @(
            $executionDependencyBindings | ForEach-Object {
                [ordered]@{ path = $_.path; sha256 = $_.sha256 }
            }
        )
        current_git_status_sha256 = [string]$Binding.GitStatusSha256
        exposure_readback = [ordered]@{
            orders = 0
            deals = 0
            positions = 0
            trades = 0
            performance_metrics = 0
            optimization_runs = 0
        }
        claimed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $directory = Split-Path -Parent $claimPath
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $json = $claim | ConvertTo-Json -Depth 12
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $stream = [System.IO.File]::Open(
        $claimPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally {
        $stream.Dispose()
    }
    return [pscustomobject]@{
        Path = (Resolve-Path -LiteralPath $claimPath).Path
        Sha256 = Get-Sha256IfExists $claimPath
    }
}

function New-ExecutionReceipt($ReceiptPath, $Contract, $PacketResult, $Binding, $LaunchClaimRecord = $null, [string]$RunnerPath = $PSCommandPath) {
    if ([string]$PacketResult.Authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        if ($null -eq $LaunchClaimRecord -or -not (Test-Sha256Text $LaunchClaimRecord.Sha256)) {
            throw "Model4 collection execution receipt requires a hash-bound one-shot launch claim."
        }
    }

    $evidence = New-Object System.Collections.Generic.List[object]
    $evidence.Add([ordered]@{ label = 'task_packet'; kind = 'file'; path = $PacketResult.PacketPath; sha256 = $PacketResult.PacketSha256 })
    $evidence.Add([ordered]@{ label = 'candidate_registry'; kind = 'file'; path = $Contract.RegistryPath; sha256 = $Contract.RegistrySha256 })
    $evidence.Add([ordered]@{ label = 'source'; kind = 'file'; path = $Contract.CanonicalSourceAbsolute; sha256 = $Contract.CurrentSourceSha256 })
    if (-not [string]::IsNullOrWhiteSpace($Contract.EaContractSha256)) {
        $evidence.Add([ordered]@{ label = 'ea_capability_contract'; kind = 'file'; path = $Contract.EaContractAbsolutePath; sha256 = $Contract.EaContractSha256 })
    }
    $includeIndex = 0
    foreach ($include in @($PacketResult.IncludeClosure)) {
        $evidence.Add([ordered]@{
            label = ('include_{0:D4}' -f $includeIndex)
            kind = 'file'
            path = $include.Path
            sha256 = $include.Sha256
        })
        $includeIndex++
    }
    $evidence.Add([ordered]@{ label = 'prereg'; kind = 'file'; path = $Contract.PreregPath; sha256 = $Contract.PreregSha256 })
    if ([string]$PacketResult.Authority -ceq 'MODEL0_TRAIN_FALSIFICATION_ONLY' -and
        $Contract.HypothesisId -ceq 'HYP-STBS-XAUUSD-M15-026') {
        $validation = Get-ObjectProperty $Contract.LatestRow 'validation'
        foreach ($packetControl in @(
            [pscustomobject]@{ Label = 'hyp026_packet_attempt_start'; PathField = 'packet_build_attempt_start_path'; ShaField = 'packet_build_attempt_start_sha256' },
            [pscustomobject]@{ Label = 'hyp026_packet_attempt_terminal'; PathField = 'packet_build_attempt_terminal_path'; ShaField = 'packet_build_attempt_terminal_sha256' },
            [pscustomobject]@{ Label = 'hyp026_gitignore'; PathField = 'gitignore_path'; ShaField = 'gitignore_sha256' },
            [pscustomobject]@{ Label = 'hyp026_independent_post_packet_review'; PathField = 'independent_post_packet_review_path'; ShaField = 'independent_post_packet_review_sha256' }
        )) {
            $declaredPath = [string](Get-ObjectProperty $validation $packetControl.PathField)
            $evidence.Add([ordered]@{
                label = $packetControl.Label
                kind = 'file'
                path = Resolve-EvidencePath $declaredPath
                sha256 = [string](Get-ObjectProperty $validation $packetControl.ShaField)
            })
        }
        foreach ($governanceControl in @(
            [pscustomobject]@{ Label = 'hyp025_parent_failure_packet'; PathField = 'parent_hyp025_failure_path'; ShaField = 'parent_hyp025_failure_sha256' },
            [pscustomobject]@{ Label = 'hyp025_parent_failure_review'; PathField = 'parent_hyp025_post_failure_review_path'; ShaField = 'parent_hyp025_post_failure_review_sha256' },
            [pscustomobject]@{ Label = 'hyp026_tester_no_spam_projection'; PathField = 'journal_budget_tester_projection_path'; ShaField = 'journal_budget_tester_projection_sha256' },
            [pscustomobject]@{ Label = 'hyp026_agent_no_spam_projection'; PathField = 'journal_budget_agent_projection_path'; ShaField = 'journal_budget_agent_projection_sha256' },
            [pscustomobject]@{ Label = 'hyp026_journal_budget_addendum'; PathField = 'journal_budget_addendum_path'; ShaField = 'journal_budget_addendum_sha256' },
            [pscustomobject]@{ Label = 'hyp026_pre_execution_harness_addendum'; PathField = 'pre_execution_harness_addendum_path'; ShaField = 'pre_execution_harness_addendum_sha256' },
            [pscustomobject]@{ Label = 'hyp026_independent_pre_probe_review'; PathField = 'independent_pre_run_review_path'; ShaField = 'independent_pre_run_review_sha256' },
            [pscustomobject]@{ Label = 'hyp026_bounded_diff_proof'; PathField = 'bounded_diff_proof_path'; ShaField = 'bounded_diff_proof_sha256' },
            [pscustomobject]@{ Label = 'hyp026_compact_telemetry_test'; PathField = 'source_contract_test_path'; ShaField = 'source_contract_test_sha256' }
        )) {
            $declaredPath = [string](Get-ObjectProperty $validation $governanceControl.PathField)
            $evidence.Add([ordered]@{
                label = $governanceControl.Label
                kind = 'file'
                path = Resolve-EvidencePath $declaredPath
                sha256 = [string](Get-ObjectProperty $validation $governanceControl.ShaField)
            })
        }
        foreach ($boundControl in @(
            [pscustomobject]@{ Label = 'hyp026_nonrepaint_auditor'; PathField = 'reviewed_nonrepaint_auditor_path'; ShaField = 'reviewed_nonrepaint_auditor_sha256' },
            [pscustomobject]@{ Label = 'hyp026_static_nonrepaint_manifest'; PathField = 'reviewed_static_nonrepaint_manifest_path'; ShaField = 'reviewed_static_nonrepaint_manifest_sha256' },
            [pscustomobject]@{ Label = 'hyp026_static_nonrepaint_audit'; PathField = 'reviewed_static_nonrepaint_audit_path'; ShaField = 'reviewed_static_nonrepaint_audit_sha256' }
        )) {
            $declaredPath = [string](Get-ObjectProperty $validation $boundControl.PathField)
            $absolutePath = if ([System.IO.Path]::IsPathRooted($declaredPath)) {
                [System.IO.Path]::GetFullPath($declaredPath)
            } else {
                [System.IO.Path]::GetFullPath((Join-Path $repoRoot $declaredPath))
            }
            $evidence.Add([ordered]@{
                label = $boundControl.Label
                kind = 'file'
                path = $absolutePath
                sha256 = [string](Get-ObjectProperty $validation $boundControl.ShaField)
            })
        }
    }
    $evidence.Add([ordered]@{ label = 'cost_source_manifest'; kind = 'file'; path = $PacketResult.CostSourceManifestPath; sha256 = Get-Sha256IfExists $PacketResult.CostSourceManifestPath })
    $costEvidenceIndex = 0
    foreach ($costSourceEvidence in @($PacketResult.CostEvidence)) {
        $evidence.Add([ordered]@{
            label = ('cost_evidence_{0:D4}' -f $costEvidenceIndex)
            kind = 'file'
            path = $costSourceEvidence.Path
            sha256 = $costSourceEvidence.Sha256
            provenance_label = $costSourceEvidence.Label
        })
        $costEvidenceIndex++
    }
    if ($Binding.RunRole -ceq 'challenger') {
        $evidence.Add([ordered]@{ label = 'matched_control_manifest'; kind = 'file'; path = $PacketResult.MatchedControl.ManifestPath; sha256 = $PacketResult.MatchedControl.ManifestSha256 })
        $evidence.Add([ordered]@{ label = 'matched_control_report'; kind = 'file'; path = $PacketResult.MatchedControl.ReportPath; sha256 = $PacketResult.MatchedControl.ReportSha256 })
        $controlArtifactIndex = 0
        foreach ($artifact in @($PacketResult.MatchedControl.Artifacts)) {
            $evidence.Add([ordered]@{
                label = ('matched_control_artifact_{0:D4}' -f $controlArtifactIndex)
                kind = 'file'
                path = $artifact.Path
                sha256 = $artifact.Sha256
            })
            $controlArtifactIndex++
        }
        $controlSidecarIndex = 0
        foreach ($sidecar in @($PacketResult.MatchedControl.Sidecars)) {
            $evidence.Add([ordered]@{
                label = ('matched_control_sidecar_{0:D4}' -f $controlSidecarIndex)
                kind = 'file'
                path = $sidecar.Path
                sha256 = $sidecar.Sha256
            })
            $controlSidecarIndex++
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($PacketResult.WfaArtifactPath)) {
        $evidence.Add([ordered]@{ label = 'wfa_artifact'; kind = 'file'; path = $PacketResult.WfaArtifactPath; sha256 = Get-Sha256IfExists $PacketResult.WfaArtifactPath })
    }
    if (-not [string]::IsNullOrWhiteSpace($PacketResult.VariantsDir)) {
        $evidence.Add([ordered]@{ label = 'variants_dir'; kind = 'directory'; path = $PacketResult.VariantsDir; sha256 = Get-DirectoryTreeSha256 $PacketResult.VariantsDir })
    }
    if ($null -ne $LaunchClaimRecord) {
        $evidence.Add([ordered]@{ label = 'launch_claim'; kind = 'file'; path = $LaunchClaimRecord.Path; sha256 = $LaunchClaimRecord.Sha256 })
    }
    if ([string]$PacketResult.Authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        $model4Validation = Get-ObjectProperty $Contract.LatestRow 'validation'
        $model4ControlPlane = Get-Model4ControlPlaneBinding $RunnerPath
        $evidence.Add([ordered]@{
            label = 'execution_control:runner'
            kind = 'file'
            path = $model4ControlPlane.RunnerPath
            sha256 = $model4ControlPlane.RunnerSha256
        })
        $evidence.Add([ordered]@{
            label = 'execution_control:candidate_registry_validator'
            kind = 'file'
            path = $model4ControlPlane.ValidatorPath
            sha256 = $model4ControlPlane.ValidatorSha256
        })
        foreach ($receiptBinding in @(
            [pscustomobject]@{
                Label = 'execute_gate_hardening_receipt'
                Path = [string](Get-ObjectProperty $model4Validation 'execute_gate_hardening_receipt_path')
                Sha256 = [string](Get-ObjectProperty $model4Validation 'execute_gate_hardening_receipt_sha256')
            },
            [pscustomobject]@{
                Label = 'packet_set_authority_receipt'
                Path = [string](Get-ObjectProperty $model4Validation 'packet_set_dry_run_receipt_path')
                Sha256 = [string](Get-ObjectProperty $model4Validation 'packet_set_dry_run_receipt_sha256')
            }
        )) {
            $evidence.Add([ordered]@{
                label = $receiptBinding.Label
                kind = 'file'
                path = Resolve-EvidencePath $receiptBinding.Path
                sha256 = $receiptBinding.Sha256
            })
        }
        foreach ($dependency in @(Get-Model4ExecutionDependencyBindings $RunnerPath)) {
            $evidence.Add([ordered]@{
                label = "execution_dependency:$($dependency.path)"
                kind = 'file'
                path = $dependency.absolute_path
                sha256 = $dependency.sha256
            })
        }
    }
    foreach ($item in $evidence) {
        if (-not (Test-Sha256Text $item.sha256)) {
            throw "Execution receipt evidence '$($item.label)' has no valid SHA256."
        }
    }

    $receipt = [ordered]@{
        schema_version = 'alphafactory_execution_receipt.v1'
        hypothesis_id = $Contract.HypothesisId
        registry_row_sha256 = $Contract.RegistryRowSha256
        task_packet_sha256 = $PacketResult.PacketSha256
        git_commit = $Binding.GitCommit
        git_status_sha256 = $Binding.GitStatusSha256
        binding = [ordered]@{
            hypothesis_id = $Contract.HypothesisId
            run_role = $Binding.RunRole
            ea_name = $Binding.EaName
            symbol = $Binding.Symbol
            period = $Binding.Period
            from = $Binding.From
            to = $Binding.To
            economic_window = [ordered]@{
                from = $PacketResult.EconomicFrom
                to = $PacketResult.EconomicTo
            }
            baseline_acceptance_contract = $PacketResult.BaselineAcceptanceContract
            model = $Binding.Model
            execution_mode = $Binding.ExecutionMode
            fixed_delay_ms = $Binding.FixedDelayMs
            timeout_sec = $Binding.TimeoutSec
            overrides = $Binding.Overrides
            telemetry_tier = $Binding.TelemetryTier
            telemetry_profile = $Binding.TelemetryProfile
            deposit = $Binding.Deposit
            leverage = $Binding.Leverage
            spread = $Binding.Spread
            required_sidecars = @($Binding.RequiredSidecars)
            broker_fingerprint = $Binding.BrokerFingerprint
            server_fingerprint = $Binding.ServerFingerprint
            account_fingerprint = $Binding.AccountFingerprint
            data_fingerprint = $Binding.DataFingerprint
            symbol_geometry = [ordered]@{
                digits = $Binding.SymbolDigits
                point = $Binding.SymbolPoint
                pip_size = $Binding.PipSize
            }
            include_closure_sha256 = $Binding.IncludeClosureSha256
            visual_mode = $false
            indicator_dependencies = @(
                $Binding.IndicatorDependencies | ForEach-Object {
                    [ordered]@{
                        name = [string](Get-ObjectProperty $_ 'name')
                        source = [string](Get-ObjectProperty $_ 'source')
                        source_sha256 = [string](Get-ObjectProperty $_ 'source_sha256')
                        terminal_ex5 = [string](Get-ObjectProperty $_ 'terminal_ex5')
                    }
                }
            )
        }
        evidence = @($evidence | ForEach-Object { $_ })
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$PacketResult.Authority)) {
        $receipt['authority'] = [string]$PacketResult.Authority
    }
    if ($null -ne $LaunchClaimRecord) {
        $receipt['launch_claim'] = [ordered]@{
            path = $LaunchClaimRecord.Path
            sha256 = $LaunchClaimRecord.Sha256
        }
    }
    Add-DataQualityContractToReceiptBinding $receipt.binding $Binding.DataQualityContract
    Write-JsonAtomically $receipt $ReceiptPath 16
    return [pscustomobject]@{
        Path = (Resolve-Path -LiteralPath $ReceiptPath).Path
        Sha256 = Get-Sha256IfExists $ReceiptPath
        Receipt = $receipt
    }
}

function Add-DataQualityContractToReceiptBinding($ReceiptBinding, $DataQualityContract) {
    if ($null -eq $DataQualityContract) { return }
    $ReceiptBinding['data_quality_contract'] = $DataQualityContract
}

function Assert-EvidenceUnchanged($ReceiptPath, $ExpectedReceiptSha256, $Binding) {
    $actualReceiptHash = Get-Sha256IfExists $ReceiptPath
    if (-not (Test-Sha256Text $ExpectedReceiptSha256) -or $actualReceiptHash -ine $ExpectedReceiptSha256) {
        throw "Execution receipt changed: expected '$ExpectedReceiptSha256', got '$actualReceiptHash'."
    }
    try {
        $receipt = Get-Content -LiteralPath $ReceiptPath -Raw | ConvertFrom-Json
    } catch {
        throw "Execution receipt JSON is malformed: $($_.Exception.Message)"
    }
    if ([string]$receipt.schema_version -cne 'alphafactory_execution_receipt.v1') {
        throw "Execution receipt schema_version is invalid."
    }
    foreach ($item in @($receipt.evidence)) {
        $actual = if ([string]$item.kind -ceq 'directory') {
            Get-DirectoryTreeSha256 ([string]$item.path)
        } elseif ([string]$item.kind -ceq 'file') {
            Get-Sha256IfExists ([string]$item.path)
        } else {
            throw "Execution receipt evidence '$($item.label)' has unsupported kind '$($item.kind)'."
        }
        if (-not (Test-Sha256Text $actual) -or $actual -ine [string]$item.sha256) {
            throw "Execution evidence '$($item.label)' changed after preflight."
        }
    }
    $git = Get-GitSnapshot
    if ($git.Commit -cne [string]$receipt.git_commit -or $git.StatusSha256 -ine [string]$receipt.git_status_sha256 -or
        $git.Commit -cne [string]$Binding.GitCommit -or $git.StatusSha256 -ine [string]$Binding.GitStatusSha256) {
        throw "Git identity changed after execution receipt creation."
    }
    return $receipt
}

function Get-DataQualityReportHistoryQuality([string]$ReportPath) {
    $html = Get-Content -LiteralPath $ReportPath -Raw
    $match = [regex]::Match(
        $html,
        '(?is)<td[^>]*>\s*History Quality\s*:?\s*</td>\s*<td[^>]*>\s*(?:<b>)?\s*([^<]+)'
    )
    if (-not $match.Success) {
        throw "Post-run report History Quality is absent."
    }
    $text = [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value).Trim()
    if ($text.EndsWith('%')) { $text = $text.Substring(0, $text.Length - 1).Trim() }
    $value = 0.0
    if (-not [double]::TryParse(
        $text,
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$value
    ) -or [double]::IsNaN($value) -or [double]::IsInfinity($value)) {
        throw "Post-run report History Quality is not a finite invariant-culture number."
    }
    return $value
}

function Get-DataQualityHistoryRangeFromJournal([string]$JournalText, [string]$Symbol) {
    $symbolPattern = [regex]::Escape($Symbol)
    $pattern = '(?im)(?<![A-Za-z0-9._+-])' + $symbolPattern + ':\s+history synchronized from (?<from>\d{4}\.\d{2}\.\d{2}) to (?<to>\d{4}\.\d{2}\.\d{2})'
    $matches = @([regex]::Matches($JournalText, $pattern))
    $ranges = @(
        $matches | ForEach-Object {
            "{0}|{1}" -f $_.Groups['from'].Value, $_.Groups['to'].Value
        } | Sort-Object -Unique
    )
    if ($ranges.Count -eq 0) {
        throw "Post-run journal has no exact-symbol history synchronization line for '$Symbol'."
    }
    if ($ranges.Count -ne 1) {
        throw "Post-run journal has ambiguous history synchronization ranges for '$Symbol'."
    }
    $parts = $ranges[0].Split('|', 2)
    if (-not (Test-ResearchDate $parts[0]) -or -not (Test-ResearchDate $parts[1])) {
        throw "Post-run journal history synchronization bounds are malformed."
    }
    return [pscustomobject]@{
        actual_from = $parts[0]
        actual_to = $parts[1]
        exact_match_count = $matches.Count
        distinct_range_count = $ranges.Count
    }
}

function Get-DataQualitySeriesProofFromJournal([string]$JournalText, [string]$Symbol, [string]$ActualFrom) {
    $symbolPattern = [regex]::Escape($Symbol)
    $pattern = '(?im)DATA_EPOCH_D0_SERIES_PROOF\s+symbol=' + $symbolPattern +
        '\s+m5_synchronized=(?<sync>[01])' +
        '\s+m5_first_epoch=(?<m5first>\d+)' +
        '\s+m5_terminal_first_epoch=(?<m5terminal>\d+)' +
        '\s+m1_server_first_epoch=(?<m1server>\d+)' +
        '\s+m1_terminal_first_epoch=(?<m1terminal>\d+)' +
        '\s+m5_bars=(?<bars>\d+)' +
        '\s+terminal_maxbars=(?<maxbars>\d+)' +
        '\s+copytime_from_epoch=(?<copyfrom>\d+)' +
        '\s+copytime_count=(?<copycount>-?\d+)' +
        '\s+copytime_result=(?<copyresult>-?\d+)' +
        '\s+copytime_first_epoch=(?<copyfirst>\d+)' +
        '\s+copytime_last_error=(?<copyerror>\d+)'
    $matches = @([regex]::Matches($JournalText, $pattern))
    $records = @($matches | ForEach-Object { $_.Value } | Sort-Object -Unique)
    if ($records.Count -ne 1) {
        throw "Post-run journal requires one distinct D0 series proof for '$Symbol'."
    }
    $match = $matches[0]
    $proof = [ordered]@{
        symbol = $Symbol
        m5_synchronized = [int]$match.Groups['sync'].Value
        m5_first_epoch = [int64]$match.Groups['m5first'].Value
        m5_terminal_first_epoch = [int64]$match.Groups['m5terminal'].Value
        m1_server_first_epoch = [int64]$match.Groups['m1server'].Value
        m1_terminal_first_epoch = [int64]$match.Groups['m1terminal'].Value
        m5_bars = [int64]$match.Groups['bars'].Value
        terminal_maxbars = [int64]$match.Groups['maxbars'].Value
        copytime_from_epoch = [int64]$match.Groups['copyfrom'].Value
        copytime_count = [int]$match.Groups['copycount'].Value
        copytime_result = [int]$match.Groups['copyresult'].Value
        copytime_first_epoch = [int64]$match.Groups['copyfirst'].Value
        copytime_last_error = [int]$match.Groups['copyerror'].Value
    }
    if ($proof.m5_synchronized -ne 1 -or $proof.m5_bars -le 0 -or $proof.terminal_maxbars -le 0 -or
        $proof.copytime_from_epoch -ne $proof.m5_first_epoch -or $proof.copytime_count -ne 1 -or
        $proof.copytime_result -ne 1 -or $proof.copytime_last_error -ne 0 -or
        $proof.m5_first_epoch -le 0 -or $proof.m5_terminal_first_epoch -le 0 -or
        $proof.m1_server_first_epoch -le 0 -or $proof.m1_terminal_first_epoch -le 0 -or
        $proof.copytime_first_epoch -le 0) {
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: D0 series proof has invalid core fields."
    }
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $actualFromDate = [datetime]::ParseExact($ActualFrom, 'yyyy.MM.dd', $culture, [System.Globalization.DateTimeStyles]::None)
    $m5FirstDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m5_first_epoch).UtcDateTime.Date
    $m5TerminalDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m5_terminal_first_epoch).UtcDateTime.Date
    $m1ServerDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m1_server_first_epoch).UtcDateTime.Date
    $m1TerminalDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m1_terminal_first_epoch).UtcDateTime.Date
    $copyFirstDate = [datetimeoffset]::FromUnixTimeSeconds($proof.copytime_first_epoch).UtcDateTime.Date
    # The symbol-level journal range is a broad availability envelope, not the
    # exact first date of every timeframe.  Require it to cover the proven M5
    # start while keeping the M5/terminal/CopyTime witnesses exact.
    if ($actualFromDate -gt $m5FirstDate) {
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: journal history envelope begins after the proven M5 first date."
    }
    if ($m5FirstDate -ne $m5TerminalDate -or $m5FirstDate -ne $copyFirstDate) {
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: M5/terminal/CopyTime first dates disagree."
    }
    if ($m1TerminalDate -ne $m1ServerDate -or $m1ServerDate -gt $m5FirstDate) {
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: terminal M1 first date does not match server history."
    }
    $reportingFloor = [datetime]::new(2018, 1, 1)
    $coverageClass = 'FULL_2018_PLUS'
    if ($m5FirstDate -gt $reportingFloor) {
        if ($m1ServerDate -le $reportingFloor -or ($m5FirstDate - $m1ServerDate).TotalDays -gt 7) {
            throw "INVALID_TRUNCATED_TERMINAL_CACHE: post-2018 start is not justified by MT5 server history."
        }
        $coverageClass = 'BROKER_LIMITED_START'
    }
    return [pscustomobject]@{
        coverage_class = $coverageClass
        series_proof = [pscustomobject]$proof
    }
}

function Assert-DataQualityModel4JournalMode(
    [string]$JournalText,
    [string]$Symbol,
    [string]$Period,
    [string]$Server
) {
    if ([string]::IsNullOrWhiteSpace($Symbol) -or
        [string]::IsNullOrWhiteSpace($Period) -or
        [string]::IsNullOrWhiteSpace($Server)) {
        throw "Post-run Model4 data acquisition requires bound symbol, period and server identity."
    }
    $prefix = [regex]::Escape("$Symbol,$Period ($Server): ")
    $structuredTester = '^(?:[^\r\n\t]*\t){3}Tester\t'
    $realTickMode = '(?m)' + $structuredTester + $prefix +
        [regex]::Escape('generating based on real ticks') + '[ \t]*\r?$'
    $generatedTickMode = '(?m)' + $structuredTester + $prefix +
        '(?:every tick generated from M1 bars|every tick generating)[ \t]*\r?$'
    if (-not [regex]::IsMatch($JournalText, $realTickMode)) {
        throw (
            "Post-run Model4 data acquisition requires the exact structured MT5 journal execution mode line: " +
            "$Symbol,$Period ($Server): generating based on real ticks."
        )
    }
    if ([regex]::IsMatch($JournalText, $generatedTickMode)) {
        throw "Post-run Model4 data acquisition has contradictory generated-tick journal execution mode."
    }
}

function Assert-DataQualityManifestMatchesPacket($Manifest, $PacketResult, [string]$TrustedRunRoot) {
    $packetContract = Get-ObjectProperty $PacketResult 'DataQualityContract'
    $manifestContract = Get-ObjectProperty $Manifest 'data_quality_contract'
    $manifestDelta = Get-ObjectProperty $Manifest 'data_quality_journal_delta'
    $gate = Get-ObjectProperty $Manifest 'data_quality_gate'
    $fingerprintBasis = Get-ObjectProperty $Manifest 'data_quality_fingerprint_basis'
    $fingerprint = [string](Get-ObjectProperty $Manifest 'data_quality_fingerprint')

    if ($null -eq $packetContract) {
        if ($null -ne $manifestContract -or $null -ne $manifestDelta -or $null -ne $gate -or
            $null -ne $fingerprintBasis -or -not [string]::IsNullOrWhiteSpace($fingerprint)) {
            throw "Legacy packet without data_quality_contract must not acquire data-quality authority post-run."
        }
        return
    }

    $trustedRoot = [System.IO.Path]::GetFullPath($TrustedRunRoot).TrimEnd('\', '/')
    $manifestRoot = [System.IO.Path]::GetFullPath([string](Get-ObjectProperty $Manifest 'local_run_dir')).TrimEnd('\', '/')
    if (-not [string]::Equals($manifestRoot, $trustedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Post-run manifest local_run_dir does not match the trusted manifest parent."
    }
    $trustedReportPath = [System.IO.Path]::GetFullPath((Join-Path $trustedRoot 'report.html'))
    $manifestReportPath = [System.IO.Path]::GetFullPath([string](Get-ObjectProperty $Manifest 'report_path'))
    if (-not [string]::Equals($manifestReportPath, $trustedReportPath, [System.StringComparison]::OrdinalIgnoreCase) -or
        (Get-Sha256IfExists $trustedReportPath) -ine [string](Get-ObjectProperty $Manifest 'report_sha256')) {
        throw "Post-run data-quality report path/hash is not run-local and immutable."
    }

    $internalContractKeys = @(
        'schema_version', 'symbol', 'requested_from', 'requested_to',
        'history_quality_threshold', 'coverage_mode', 'availability_asof_utc',
        'require_tester_journal_bounds', 'max_journal_delta_bytes'
    )
    if (-not (Test-ExactObjectKeys $manifestContract $internalContractKeys)) {
        throw "Post-run data_quality_contract does not match the normalized AlphaFactory schema."
    }
    $packetMaxJournalDeltaBytes = [int64](Get-ObjectProperty $packetContract 'max_journal_delta_bytes')
    if ([string](Get-ObjectProperty $manifestContract 'schema_version') -cne 'alphafactory_data_quality_contract.v1' -or
        [string](Get-ObjectProperty $manifestContract 'symbol') -cne [string](Get-ObjectProperty $Manifest 'symbol') -or
        [string](Get-ObjectProperty $manifestContract 'requested_from') -cne [string](Get-ObjectProperty $packetContract 'requested_from') -or
        [string](Get-ObjectProperty $manifestContract 'requested_to') -cne [string](Get-ObjectProperty $packetContract 'requested_to') -or
        [string](Get-ObjectProperty $manifestContract 'coverage_mode') -cne [string](Get-ObjectProperty $packetContract 'coverage_mode') -or
        $packetMaxJournalDeltaBytes -ne 4194304L -or
        [int64](Get-ObjectProperty $manifestContract 'max_journal_delta_bytes') -ne $packetMaxJournalDeltaBytes) {
        throw "Post-run normalized data_quality_contract does not match the task packet."
    }
    $packetThreshold = [double](Get-ObjectProperty (Get-ObjectProperty $packetContract 'history_quality') 'value')
    if ([double](Get-ObjectProperty $manifestContract 'history_quality_threshold') -ne $packetThreshold) {
        throw "Post-run data-quality threshold does not match the task packet."
    }
    $packetJournalRequired = Get-ObjectProperty $packetContract 'require_tester_journal_bounds'
    $manifestJournalRequired = Get-ObjectProperty $manifestContract 'require_tester_journal_bounds'
    if ($packetJournalRequired -isnot [bool] -or $manifestJournalRequired -isnot [bool] -or
        (-not [bool]$packetJournalRequired) -or (-not [bool]$manifestJournalRequired)) {
        throw "Post-run data-quality journal requirement is missing or untyped."
    }
    try {
        $packetAsOf = [datetimeoffset]::Parse(
            [string](Get-ObjectProperty $packetContract 'availability_asof_utc'),
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        )
        $manifestAsOf = [datetimeoffset]::Parse(
            [string](Get-ObjectProperty $manifestContract 'availability_asof_utc'),
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        )
    } catch {
        throw "Post-run data-quality availability_asof_utc is malformed."
    }
    if ($packetAsOf.UtcTicks -ne $manifestAsOf.UtcTicks) {
        throw "Post-run data-quality availability_asof_utc does not match the task packet."
    }

    $gateKeys = @(
        'contract', 'history_quality', 'actual_from', 'actual_to', 'coverage_class', 'series_proof', 'journal_path',
        'journal_sha256', 'journal_bytes_read', 'journal_files_read', 'journal_truncated',
        'exact_match_count', 'distinct_range_count'
    )
    if (-not (Test-ExactObjectKeys $gate $gateKeys)) {
        throw "Post-run data_quality_gate is missing or has an unexpected schema."
    }
    if (($gate.contract | ConvertTo-Json -Depth 12 -Compress) -cne ($manifestContract | ConvertTo-Json -Depth 12 -Compress)) {
        throw "Post-run data_quality_gate contract does not match the normalized manifest contract."
    }
    if (-not (Test-FiniteNumber (Get-ObjectProperty $gate 'history_quality')) -or
        [double](Get-ObjectProperty $gate 'history_quality') -le $packetThreshold) {
        throw "Post-run data_quality_gate History Quality is not strictly above the task-packet threshold."
    }
    $reportHistoryQuality = Get-DataQualityReportHistoryQuality $trustedReportPath
    if ($reportHistoryQuality -ne [double](Get-ObjectProperty $gate 'history_quality')) {
        throw "Post-run data_quality_gate History Quality does not match the hashed report."
    }
    $actualFrom = [string](Get-ObjectProperty $gate 'actual_from')
    $actualTo = [string](Get-ObjectProperty $gate 'actual_to')
    if (-not (Test-ResearchDate $actualFrom) -or -not (Test-ResearchDate $actualTo)) {
        throw "Post-run data_quality_gate actual history bounds are malformed."
    }
    $actualFromDate = [datetime]::ParseExact($actualFrom, 'yyyy.MM.dd', [System.Globalization.CultureInfo]::InvariantCulture)
    $actualToDate = [datetime]::ParseExact($actualTo, 'yyyy.MM.dd', [System.Globalization.CultureInfo]::InvariantCulture)
    $requestedFromDate = [datetime]::ParseExact([string](Get-ObjectProperty $manifestContract 'requested_from'), 'yyyy.MM.dd', [System.Globalization.CultureInfo]::InvariantCulture)
    $requestedToDate = [datetime]::ParseExact([string](Get-ObjectProperty $manifestContract 'requested_to'), 'yyyy.MM.dd', [System.Globalization.CultureInfo]::InvariantCulture)
    if ($actualFromDate -gt $actualToDate) {
        throw "Post-run data_quality_gate actual_from must not be later than actual_to."
    }
    if ($actualToDate -lt $requestedToDate) {
        throw "Post-run data_quality_gate ends before the frozen requested_to date."
    }
    if ([string](Get-ObjectProperty $manifestContract 'coverage_mode') -ceq 'fixed_window' -and
        $actualFromDate -gt $requestedFromDate) {
        throw "Post-run data_quality_gate begins after the frozen fixed_window requested_from date."
    }
    if ((Get-ObjectProperty $gate 'journal_truncated') -isnot [bool] -or [bool](Get-ObjectProperty $gate 'journal_truncated') -or
        [int64](Get-ObjectProperty $gate 'journal_bytes_read') -le 0 -or
        [int64](Get-ObjectProperty $gate 'journal_files_read') -le 0 -or
        [int](Get-ObjectProperty $gate 'exact_match_count') -le 0 -or
        [int](Get-ObjectProperty $gate 'distinct_range_count') -ne 1) {
        throw "Post-run data_quality_gate journal evidence is incomplete, truncated or ambiguous."
    }

    $deltaKeys = @('path', 'sha256', 'bytes_read', 'files_read', 'truncated')
    if (-not (Test-ExactObjectKeys $manifestDelta $deltaKeys) -or
        [string](Get-ObjectProperty $manifestDelta 'path') -cne 'logs/tester_journal_delta.log' -or
        [string](Get-ObjectProperty $gate 'journal_path') -cne [string](Get-ObjectProperty $manifestDelta 'path') -or
        [string](Get-ObjectProperty $gate 'journal_sha256') -ine [string](Get-ObjectProperty $manifestDelta 'sha256') -or
        [int64](Get-ObjectProperty $gate 'journal_bytes_read') -ne [int64](Get-ObjectProperty $manifestDelta 'bytes_read') -or
        [int](Get-ObjectProperty $gate 'journal_files_read') -ne [int](Get-ObjectProperty $manifestDelta 'files_read') -or
        [bool](Get-ObjectProperty $gate 'journal_truncated') -ne [bool](Get-ObjectProperty $manifestDelta 'truncated')) {
        throw "Post-run data-quality journal receipt does not match the validated gate."
    }
    $journalPath = [System.IO.Path]::GetFullPath((Join-Path $trustedRoot ([string](Get-ObjectProperty $manifestDelta 'path'))))
    if (-not $journalPath.StartsWith("$trustedRoot\", [System.StringComparison]::OrdinalIgnoreCase) -or
        (Get-Sha256IfExists $journalPath) -ine [string](Get-ObjectProperty $manifestDelta 'sha256')) {
        throw "Post-run data-quality journal path/hash is not run-local and immutable."
    }
    $journalText = Get-Content -LiteralPath $journalPath -Raw
    $packetAuthority = [string](Get-ObjectProperty $PacketResult 'Authority')
    if ($packetAuthority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        $manifestModel = Get-ObjectProperty $Manifest 'model'
        if (-not (Test-IntegerValue $manifestModel) -or [int]$manifestModel -ne 4) {
            throw "Post-run Model4 data acquisition authority requires run_manifest.model=4."
        }
        $collectionSymbol = [string](Get-ObjectProperty $PacketResult 'CollectionSymbol')
        $collectionPeriod = [string](Get-ObjectProperty $PacketResult 'CollectionPeriod')
        $collectionServer = [string](Get-ObjectProperty $PacketResult 'CollectionServer')
        if ([string](Get-ObjectProperty $Manifest 'symbol') -cne $collectionSymbol -or
            [string](Get-ObjectProperty $Manifest 'period') -cne $collectionPeriod) {
            throw "Post-run Model4 data acquisition manifest symbol/period does not match the hash-bound collection contract."
        }
        Assert-DataQualityModel4JournalMode `
            $journalText $collectionSymbol $collectionPeriod $collectionServer
    }
    $journalRange = Get-DataQualityHistoryRangeFromJournal $journalText ([string](Get-ObjectProperty $Manifest 'symbol'))
    if ([string]$journalRange.actual_from -cne $actualFrom -or
        [string]$journalRange.actual_to -cne $actualTo -or
        [int]$journalRange.exact_match_count -ne [int](Get-ObjectProperty $gate 'exact_match_count') -or
        [int]$journalRange.distinct_range_count -ne [int](Get-ObjectProperty $gate 'distinct_range_count')) {
        throw "Post-run data_quality_gate history bounds/counts do not match the hashed journal."
    }
    $seriesProof = Get-DataQualitySeriesProofFromJournal $journalText ([string](Get-ObjectProperty $Manifest 'symbol')) $actualFrom
    $gateCoverageClass = [string](Get-ObjectProperty $gate 'coverage_class')
    if ($gateCoverageClass -notin @('FULL_2018_PLUS', 'BROKER_LIMITED_START') -or
        $gateCoverageClass -cne [string]$seriesProof.coverage_class -or
        ((Get-ObjectProperty $gate 'series_proof') | ConvertTo-Json -Depth 8 -Compress) -cne ($seriesProof.series_proof | ConvertTo-Json -Depth 8 -Compress)) {
        throw "Post-run data_quality_gate series proof/coverage class does not match the hashed MT5 journal."
    }

    $expectedFingerprintBasis = [ordered]@{
        schema_version = 'alphafactory_data_quality_fingerprint.v1'
        base_data_fingerprint = [string](Get-ObjectProperty $Manifest 'data_fingerprint')
        contract = $manifestContract
        history_quality = [double](Get-ObjectProperty $gate 'history_quality')
        actual_from = $actualFrom
        actual_to = $actualTo
        coverage_class = $gateCoverageClass
        series_proof = $seriesProof.series_proof
        journal_sha256 = [string](Get-ObjectProperty $gate 'journal_sha256')
        journal_bytes_read = [int64](Get-ObjectProperty $gate 'journal_bytes_read')
        journal_files_read = [int](Get-ObjectProperty $gate 'journal_files_read')
        journal_truncated = [bool](Get-ObjectProperty $gate 'journal_truncated')
        exact_match_count = [int](Get-ObjectProperty $gate 'exact_match_count')
        distinct_range_count = [int](Get-ObjectProperty $gate 'distinct_range_count')
    }
    $expectedBasisJson = $expectedFingerprintBasis | ConvertTo-Json -Depth 12 -Compress
    if (-not (Test-ProvenanceObject $fingerprintBasis) -or
        ($fingerprintBasis | ConvertTo-Json -Depth 12 -Compress) -cne $expectedBasisJson -or
        -not (Test-Sha256Text $fingerprint) -or
        $fingerprint -ine (Get-TextSha256 $expectedBasisJson)) {
        throw "Post-run data_quality_fingerprint is absent or does not bind the validated evidence."
    }
}

function Assert-ZeroTradeCollectionSummary([string]$SummaryPath, [string]$Authority) {
    if ($Authority -notin @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )) {
        throw "Unsupported data-acquisition authority '$Authority'."
    }
    if (-not (Test-Path -LiteralPath $SummaryPath -PathType Leaf)) {
        throw "Zero-trade collection summary is missing: $SummaryPath"
    }
    try {
        $summary = Get-Content -LiteralPath $SummaryPath -Raw | ConvertFrom-Json
    } catch {
        throw "Zero-trade collection summary is malformed JSON: $($_.Exception.Message)"
    }
    $expectedKeys = @('schema_version', 'analysis_mode', 'authority', 'n_trades', 'performance_metrics_authorized', 'generated_at_utc')
    $actualKeys = @($summary.PSObject.Properties | ForEach-Object { $_.Name })
    if ($actualKeys.Count -ne $expectedKeys.Count -or @($actualKeys | Where-Object { $_ -notin $expectedKeys }).Count -gt 0) {
        throw "Zero-trade collection summary contains missing or unauthorized fields."
    }
    if ([string]$summary.schema_version -cne 'alphafactory_zero_trade_collection_summary.v1' -or
        [string]$summary.analysis_mode -cne 'data_acquisition_only' -or
        [string]$summary.authority -cne $Authority) {
        throw "Zero-trade collection summary identity/authority mismatch."
    }
    if (-not (Test-IntegerValue $summary.n_trades) -or [int64]$summary.n_trades -ne 0) {
        throw "Zero-trade collection summary must bind n_trades=0."
    }
    if ($summary.performance_metrics_authorized -isnot [bool] -or $summary.performance_metrics_authorized -ne $false) {
        throw "Zero-trade collection summary must set performance_metrics_authorized=false."
    }
    if ([string]::IsNullOrWhiteSpace([string]$summary.generated_at_utc)) {
        throw "Zero-trade collection summary generated_at_utc is required."
    }
    return $summary
}

function Assert-RunManifestMatchesPacket($ManifestPath, $PacketResult, $Binding, $Contract, $ReceiptSha256) {
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        throw "Post-run manifest is missing: $ManifestPath"
    }
    try {
        $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    } catch {
        throw "Post-run manifest JSON is malformed: $($_.Exception.Message)"
    }
    $manifestMain = [System.IO.Path]::GetFullPath([string](Get-ObjectProperty $manifest 'main_file'))
    $contractMain = [System.IO.Path]::GetFullPath([string]$Contract.CanonicalSourceAbsolute)
    if (-not [string]::Equals($manifestMain, $contractMain, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Post-run manifest main_file '$manifestMain' does not match resolved EA main '$contractMain'."
    }
    $expectedFields = [ordered]@{
        hypothesis_id = $Contract.HypothesisId
        run_role = $Binding.RunRole
        ea_name = $Binding.EaName
        symbol = $Binding.Symbol
        period = $Binding.Period
        from = $Binding.From
        to = $Binding.To
        model = $Binding.Model
        execution_mode = $Binding.ExecutionMode
        fixed_delay_ms = $Binding.FixedDelayMs
        timeout_sec = $Binding.TimeoutSec
        overrides = $Binding.Overrides
        telemetry_tier = $Binding.TelemetryTier
        deposit = $Binding.Deposit
        leverage = $Binding.Leverage
        spread = $Binding.Spread
        source_sha256 = $Contract.CurrentSourceSha256
        git_commit = $Binding.GitCommit
        git_status_sha256 = $Binding.GitStatusSha256
        broker_fingerprint = $Binding.BrokerFingerprint
        server_fingerprint = $Binding.ServerFingerprint
        account_fingerprint = $Binding.AccountFingerprint
        data_fingerprint = $Binding.DataFingerprint
        contract_receipt_sha256 = $ReceiptSha256
    }
    foreach ($field in $expectedFields.Keys) {
        $actual = Get-ObjectProperty $manifest $field
        $expected = $expectedFields[$field]
        if ($field -in @('model', 'execution_mode', 'fixed_delay_ms', 'timeout_sec', 'deposit', 'leverage')) {
            if (-not (Test-IntegerValue $actual) -or [int64]$actual -ne [int64]$expected) {
                throw "Post-run manifest field '$field' does not match task packet '$expected'."
            }
        } elseif ($field -match 'sha256$|_fingerprint$') {
            if (-not (Test-Sha256Text $actual) -or [string]$actual -ine [string]$expected) {
                throw "Post-run manifest identity '$field' does not match task packet."
            }
        } elseif ([string]$actual -cne [string]$expected) {
            throw "Post-run manifest field '$field' does not match task packet '$expected'."
        }
    }
    $trustedRunRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $ManifestPath)).TrimEnd('\', '/')
    Assert-DataQualityManifestMatchesPacket $manifest $PacketResult $trustedRunRoot

    $manifestBasis = Get-ObjectProperty $manifest 'fingerprint_basis'
    if (-not (Test-ProvenanceObject $manifestBasis)) {
        throw "Post-run manifest fingerprint_basis is required for report-bound symbol geometry."
    }
    $geometryBindings = [ordered]@{
        digits = $Binding.SymbolDigits
        point = $Binding.SymbolPoint
        pip_size = $Binding.PipSize
    }
    foreach ($geometryField in $geometryBindings.Keys) {
        $actualGeometry = Get-ObjectProperty $manifestBasis $geometryField
        $expectedGeometry = $geometryBindings[$geometryField]
        if ($geometryField -ceq 'digits') {
            if (-not (Test-IntegerValue $actualGeometry)) {
                throw "Post-run manifest fingerprint_basis.$geometryField is required and must be an integer."
            }
            if ([int64]$actualGeometry -ne [int64]$expectedGeometry) {
                throw "Post-run manifest fingerprint_basis.$geometryField does not match task packet symbol geometry."
            }
        } else {
            if (-not (Test-NonNegativeNumber $actualGeometry) -or [double]$actualGeometry -le 0) {
                throw "Post-run manifest fingerprint_basis.$geometryField is required and must be a finite number greater than zero."
            }
            if ([double]$actualGeometry -ne [double]$expectedGeometry) {
                throw "Post-run manifest fingerprint_basis.$geometryField does not match task packet symbol geometry."
            }
        }
    }

    $manifestRequiredSidecars = @(Get-ObjectProperty $manifest 'required_sidecars' | ForEach-Object { [string]$_ } | Sort-Object)
    $packetRequiredSidecars = @($PacketResult.RequiredSidecars | ForEach-Object { [string]$_ } | Sort-Object)
    if ([string]::Join("`n", $manifestRequiredSidecars) -cne [string]::Join("`n", $packetRequiredSidecars)) {
        throw "Post-run manifest required_sidecars does not match task packet."
    }

    $hashArtifacts = [ordered]@{
        source_sha256 = [string](Get-ObjectProperty $manifest 'source_snapshot')
        config_sha256 = [string](Get-ObjectProperty $manifest 'config_snapshot')
        report_sha256 = [string](Get-ObjectProperty $manifest 'report_path')
        ex5_sha256 = [string](Get-ObjectProperty $manifest 'ex5_snapshot')
        includes_sha256 = $null
    }
    foreach ($hashField in @($PacketResult.RequiredManifestHashes)) {
        if (-not $hashArtifacts.Contains($hashField)) {
            throw "Task packet requires unsupported manifest hash '$hashField'."
        }
        $artifactPath = $hashArtifacts[$hashField]
        $actualHash = if ($hashField -ceq 'includes_sha256') {
            Get-ManifestIncludeSetSha256 $manifest
        } else {
            Get-Sha256IfExists $artifactPath
        }
        $manifestHash = [string](Get-ObjectProperty $manifest $hashField)
        if (-not (Test-Sha256Text $manifestHash) -or $actualHash -ine $manifestHash) {
            throw "Post-run manifest hash '$hashField' does not match artifact '$artifactPath'."
        }
    }
    $manifestIncludeClosure = @(
        @(Get-ObjectProperty $manifest 'include_snapshots') | ForEach-Object {
            [pscustomobject]@{
                Path = [string](Get-ObjectProperty $_ 'original_path')
                Sha256 = [string](Get-ObjectProperty $_ 'sha256')
            }
        }
    )
    $manifestIncludeClosureHash = Get-PathHashSetSha256 $manifestIncludeClosure
    if ($manifestIncludeClosureHash -ine [string]$Binding.IncludeClosureSha256) {
        throw "Post-run include closure does not match the task packet include_closure_sha256."
    }
    $testerEx5Path = [string](Get-ObjectProperty $manifest 'tester_ex5_path')
    $actualTesterEx5Hash = Get-Sha256IfExists $testerEx5Path
    if (-not (Test-Sha256Text $actualTesterEx5Hash) -or
        $actualTesterEx5Hash -ine [string](Get-ObjectProperty $manifest 'tester_ex5_sha256') -or
        $actualTesterEx5Hash -ine [string](Get-ObjectProperty $manifest 'ex5_sha256')) {
        throw "Post-run staged tester EX5 identity does not match the snapshotted EX5."
    }

    $runRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $ManifestPath)).TrimEnd('\')
    $runPrefix = "$runRoot\"
    $sidecars = @(Get-ObjectProperty $manifest 'sidecars')
    foreach ($sidecar in $sidecars) {
        $relative = ([string](Get-ObjectProperty $sidecar 'path')).Replace('/', '\')
        $sidecarPath = [System.IO.Path]::GetFullPath((Join-Path $runRoot $relative))
        if (-not $sidecarPath.StartsWith($runPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Post-run sidecar path escapes run directory: $relative"
        }
        $actualHash = Get-Sha256IfExists $sidecarPath
        if ($actualHash -ine [string](Get-ObjectProperty $sidecar 'sha256')) {
            throw "Post-run sidecar hash mismatch: $relative"
        }
    }
    foreach ($pattern in $packetRequiredSidecars) {
        $matches = @($sidecars | Where-Object { (Split-Path -Leaf ([string](Get-ObjectProperty $_ 'path'))) -like $pattern })
        if ($matches.Count -eq 0) { throw "Post-run manifest is missing required sidecar '$pattern'." }
    }
    return $manifest
}

function Invoke-Logged($Label, [scriptblock]$Block) {
    Write-Status $Label
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Stop"
    $global:LASTEXITCODE = 0
    $output = @()
    $exitCode = 0
    $errorMessage = $null
    try {
        $output = @(& $Block 2>&1)
        if ($null -ne $LASTEXITCODE) { $exitCode = [int]$LASTEXITCODE }
    } catch {
        $exitCode = 1
        $errorMessage = $_.Exception.Message
        $output += ($_ | Out-String)
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }
    $output | ForEach-Object { Write-Host $_ }
    return [pscustomobject]@{
        Label = $Label
        ExitCode = $exitCode
        Error = $errorMessage
        Output = (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine)
    }
}

function Invoke-RequiredStep($Label, [scriptblock]$Block, $Steps) {
    $result = Invoke-Logged $Label $Block
    $Steps.Add($result)
    if ($result.ExitCode -ne 0) {
        $detail = if ([string]::IsNullOrWhiteSpace([string]$result.Error)) { "exit code $($result.ExitCode)" } else { $result.Error }
        throw "Required step failed: $Label ($detail)"
    }
    return $result
}

function Parse-RunDir($Text) {
    $markers = New-Object System.Collections.Generic.List[string]
    foreach ($line in (($Text | Out-String) -split "`r?`n")) {
        $match = [regex]::Match($line, '^ALPHA_RUN_DIR=(.+)$')
        if ($match.Success) { $markers.Add($match.Groups[1].Value.Trim()) }
    }
    if ($markers.Count -ne 1) {
        throw "Backtest output must contain exactly one ALPHA_RUN_DIR marker; found $($markers.Count)."
    }
    return $markers[0]
}

function Resolve-ExactRunDir($MarkerPath, $ExpectedEaName, $ExpectedHypothesisId) {
    if (-not (Test-Path -LiteralPath $MarkerPath -PathType Container)) {
        throw "Marked run directory does not exist: $MarkerPath"
    }
    $resolved = (Resolve-Path -LiteralPath $MarkerPath).Path
    $expectedRoot = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $alphaRoot "runs") $ExpectedEaName)).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($expectedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Marked run directory is outside the expected EA run root: $resolved"
    }
    $manifestPath = Join-Path $resolved "run_manifest.json"
    $reportPath = Join-Path $resolved "report.html"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Marked run directory is missing run_manifest.json: $resolved" }
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) { throw "Marked run directory is missing report.html: $resolved" }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([string]$manifest.hypothesis_id -cne $ExpectedHypothesisId) {
        throw "Marked run manifest hypothesis mismatch: expected '$ExpectedHypothesisId', got '$($manifest.hypothesis_id)'."
    }
    return $resolved
}

function Enter-ResearchLock($Plan) {
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    try {
        $stream = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    } catch [System.IO.IOException] {
        throw "Research loop lock already exists: $lockPath. Confirm the owning process before removing it."
    }
    try {
        $payload = [ordered]@{
            schema_version = "alphafactory_research_loop_lock.v1"
            pid = $PID
            started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
            plan = $Plan
        }
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($payload | ConvertTo-Json -Depth 12))
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
        return $stream
    } catch {
        $stream.Dispose()
        Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
        throw
    }
}

function Enter-ImmutableEvidenceReadLocks($Paths, $Streams) {
    $seen = @{}
    try {
        foreach ($rawPath in @($Paths)) {
            if ([string]::IsNullOrWhiteSpace([string]$rawPath)) { continue }
            $path = [System.IO.Path]::GetFullPath([string]$rawPath)
            $key = $path.ToLowerInvariant()
            if ($seen.ContainsKey($key)) { continue }
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "Immutable execution evidence is missing before lock acquisition: $path"
            }
            $stream = [System.IO.File]::Open(
                $path,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::Read
            )
            [void]$Streams.Add($stream)
            $seen[$key] = $true
        }
    } catch {
        foreach ($stream in $Streams) {
            try { $stream.Dispose() } catch {}
        }
        $Streams.Clear()
        throw "Could not lock immutable execution evidence: $($_.Exception.Message)"
    }
}

function Exit-ImmutableEvidenceReadLocks($Streams) {
    if ($null -eq $Streams) { return }
    foreach ($stream in $Streams) {
        try { $stream.Dispose() } catch {}
    }
    $Streams.Clear()
}

function Exit-ResearchLock($Stream) {
    if ($null -eq $Stream) { return }
    $Stream.Dispose()
    if (Test-Path -LiteralPath $lockPath) { Remove-Item -LiteralPath $lockPath -Force }
}

function Enter-GlobalValidationLock($ReceiptRecord) {
    try {
        $stream = [System.IO.File]::Open(
            $globalValidationLockPath,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    } catch [System.IO.IOException] {
        throw "Global AlphaFactory lock is owned by another execution; validation evidence cannot be frozen: $globalValidationLockPath"
    }
    try {
        $payload = [ordered]@{
            schema_version = 'alphafactory_validation_lock.v1'
            owner_pid = $PID
            execution_receipt_path = $ReceiptRecord.Path
            execution_receipt_sha256 = $ReceiptRecord.Sha256
            started_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        }
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($payload | ConvertTo-Json -Depth 6))
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
        return $stream
    } catch {
        $stream.Dispose()
        Remove-Item -LiteralPath $globalValidationLockPath -Force -ErrorAction SilentlyContinue
        throw
    }
}

function Exit-GlobalValidationLock($Stream) {
    if ($null -eq $Stream) { return }
    $Stream.Dispose()
    if (Test-Path -LiteralPath $globalValidationLockPath) {
        Remove-Item -LiteralPath $globalValidationLockPath -Force
    }
}

function Add-StateTransition($State, $Detail = "") {
    $transition = [ordered]@{
        sequence = $script:transitions.Count + 1
        hypothesis_id = $script:transitionHypothesisId
        state = $State
        detail = $Detail
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $script:transitions.Add($transition)
    if (-not [string]::IsNullOrWhiteSpace($script:transitionLogPath)) {
        ($transition | ConvertTo-Json -Compress -Depth 5) | Add-Content -LiteralPath $script:transitionLogPath -Encoding UTF8
    }
    return $transition
}

function Update-RunManifestResearch($ManifestPath, $Contract, $PacketResult, $Plan, $Transitions, $TransitionLog, $Evidence) {
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    $researchLoop = [ordered]@{
        schema_version = "alphafactory_research_loop_manifest.v1"
        hypothesis_id = $Contract.HypothesisId
        run_role = $Plan.run_role
        prereg_path = $Contract.PreregPath
        prereg_sha256 = $Contract.PreregSha256
        registry_path = $Contract.RegistryPath
        registry_line_at_start = $Contract.RegistryLine
        registry_state_at_start = $Contract.RegistryState
        task_packet_path = $PacketResult.PacketPath
        task_packet_sha256 = $PacketResult.PacketSha256
        evidence = $Evidence
        plan = $Plan
        state_transitions = @($Transitions | ForEach-Object { $_ })
        transition_log = $TransitionLog
        registry_mutation = "none; append-only verdict transition remains a coordinator responsibility"
    }
    $manifest | Add-Member -MemberType NoteProperty -Name research_loop -Value $researchLoop -Force
    Write-JsonAtomically $manifest $ManifestPath 16
}

function New-Hyp026NonRepaintAuditManifest($RunManifestPath, $RunManifestSha256, $AnalysisDir) {
    if ($HypothesisId -cne 'HYP-STBS-XAUUSD-M15-026' -or
        $EaName -cne 'EA_SupertrendBurstScalperTradeV13') {
        throw "The HYP026 runner cannot adapt another hypothesis or EA."
    }
    if ((Get-Sha256IfExists $hyp026StaticNonRepaintManifestPath) -ine $hyp026StaticNonRepaintManifestSha256) {
        throw "HYP026 static non-repaint manifest hash mismatch."
    }
    $static = Get-Content -LiteralPath $hyp026StaticNonRepaintManifestPath -Raw | ConvertFrom-Json
    if ((Get-Sha256IfExists $hyp026StaticNonRepaintManifestPath) -ine $hyp026StaticNonRepaintManifestSha256) {
        throw "HYP026 static non-repaint manifest changed while being read."
    }
    if ([string]$static.hypothesis_id -cne $HypothesisId -or
        [string]$static.source_sha256 -cne $hyp026SourceSha256 -or
        $static.nondecision_provenance_copytime_authorized -ne $true) {
        throw "HYP026 static non-repaint provenance authority is invalid."
    }
    if ((Get-Sha256IfExists $RunManifestPath) -ine $RunManifestSha256) {
        throw "HYP026 original run manifest drifted before the audit adapter read."
    }
    $run = Get-Content -LiteralPath $RunManifestPath -Raw | ConvertFrom-Json
    if ((Get-Sha256IfExists $RunManifestPath) -ine $RunManifestSha256) {
        throw "HYP026 original run manifest changed while being read."
    }
    if ([string]$run.hypothesis_id -cne $HypothesisId -or
        [string]$run.ea_name -cne $EaName -or
        [string]$run.source_sha256 -cne $hyp026SourceSha256) {
        throw "HYP026 run manifest identity does not match the frozen static provenance authority."
    }
    if ($null -ne $run.PSObject.Properties['nondecision_provenance_copytime_authorized'] -or
        $null -ne $run.PSObject.Properties['nondecision_provenance_authority_source']) {
        throw "Original HYP026 run manifest already contains unexpected provenance fields."
    }
    $run | Add-Member -MemberType NoteProperty -Name nondecision_provenance_copytime_authorized -Value $true -Force
    $run | Add-Member -MemberType NoteProperty -Name nondecision_provenance_authority_source -Value ([ordered]@{
        path = $hyp026StaticNonRepaintManifestPath
        sha256 = $hyp026StaticNonRepaintManifestSha256
        original_run_manifest_sha256 = $RunManifestSha256
        scope = 'single exact DATA_EPOCH_D0 CopyTime first-date proof; no decision or outcome access'
    }) -Force
    $out = Join-Path $AnalysisDir 'nonrepaint_run_manifest.json'
    Write-JsonAtomically $run $out 16
    if ((Get-Sha256IfExists $RunManifestPath) -ine $RunManifestSha256) {
        throw "HYP026 original run manifest changed while the derivative was written."
    }
    return $out
}

if ([string]::IsNullOrWhiteSpace($EaName)) {
    throw "EaName is required before dry-run or execution."
}
if ($EaName -cne 'EA_SupertrendBurstScalperTradeV13' -or
    $HypothesisId -cne 'HYP-STBS-XAUUSD-M15-026' -or
    $RunRole -cne 'control' -or $Symbol -cne 'XAUUSD' -or $Period -cne 'M15' -or
    $From -cne '2005.01.01' -or $To -cne '2023.01.01' -or $Model -ne 0 -or
    $ExecutionMode -ne 0 -or $FixedDelayMs -ne 0 -or $TimeoutSec -ne 900 -or
    $TelemetryTier -cne 'trade-only' -or $Deposit -ne 100000 -or $Leverage -ne 100 -or
    -not [string]::IsNullOrWhiteSpace($Spread)) {
    throw "The HYP026 runner accepts only the frozen XAUUSD M15 2005-2023 Model0 control baseline contract."
}
if ($Execute -and -not [string]::Equals($registryPath, $canonicalRegistryPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Execute requires the canonical registry: $canonicalRegistryPath"
}
$contract = Resolve-ResearchContract $HypothesisId $EaName
if ($Deposit -le 0) { throw "Deposit must be greater than zero." }
if ($Leverage -le 0) { throw "Leverage must be greater than zero." }
if ($TimeoutSec -le 0) { throw "TimeoutSec must be greater than zero." }
if ($ExecutionMode -lt 0) { throw "ExecutionMode must be non-negative." }
if ($FixedDelayMs -lt 0) { throw "FixedDelayMs must be non-negative." }
Assert-BacktestScalarContract $EaName $HypothesisId $Symbol $Period $From $To $Spread $ExecutionMode $FixedDelayMs

$effectiveOverrides = $Overrides
if (-not [string]::IsNullOrWhiteSpace($VariantTag)) {
    if ([string]::IsNullOrWhiteSpace($contract.VariantTagInput)) {
        throw "VariantTag is not supported by EA '$EaName'; declare variant_tag_input in ALPHAFACTORY_EA_CONTRACT.json or omit VariantTag."
    }
    $effectiveOverrides = Add-Override $effectiveOverrides $contract.VariantTagInput $VariantTag
}
$effectiveOverrides = Resolve-TelemetryTierOverrides $TelemetryTier $contract.CanonicalSourceAbsolute $effectiveOverrides $contract.TelemetryProfile
$effectiveSpread = if ([string]::IsNullOrWhiteSpace($Spread)) { "current" } else { $Spread }
$gitSnapshot = Get-GitSnapshot $contract.CanonicalSourceAbsolute
$indicatorDependencyBinding = @(Get-LiveIndicatorDependencyBinding $contract.IndicatorDependencies)
$binding = [pscustomobject]@{
    EaName = $EaName
    RunRole = $RunRole
    Symbol = $Symbol
    Period = $Period
    From = $From
    To = $To
    Model = $Model
    ExecutionMode = $ExecutionMode
    FixedDelayMs = $FixedDelayMs
    TimeoutSec = $TimeoutSec
    Overrides = $effectiveOverrides
    TelemetryTier = $TelemetryTier
    TelemetryProfile = $contract.TelemetryProfile
    ComparisonAdapter = $contract.ComparisonAdapter
    Deposit = $Deposit
    Leverage = $Leverage
    Spread = $effectiveSpread
    GitCommit = $gitSnapshot.Commit
    GitStatus = @($gitSnapshot.Status)
    GitStatusSha256 = $gitSnapshot.StatusSha256
    ValidationStage = $ValidationStage
    HoldingContract = $HoldingContract
    CostSourceManifest = $CostSourceManifest
    AllowResearchCostProxy = [bool]$AllowResearchCostProxy
    WfaArtifact = $WfaArtifact
    VariantsDir = $VariantsDir
    MatchedControlRunId = $MatchedControlRunId
    IndicatorDependencies = @($indicatorDependencyBinding)
    # Defaults keep a no-packet dry run inspectable under StrictMode.  A valid
    # task packet overwrites every one of these fields inside Resolve-TaskPacket.
    IncludeClosure = @()
    IncludeClosureSha256 = Get-PathHashSetSha256 @()
    BrokerFingerprint = $null
    ServerFingerprint = $null
    AccountFingerprint = $null
    DataFingerprint = $null
    SymbolDigits = $null
    SymbolPoint = $null
    PipSize = $null
    RequiredSidecars = @()
    RequiredManifestHashes = @()
    DataQualityContract = $null
}

$executionBlockers = New-Object System.Collections.Generic.List[string]
$packetResult = Resolve-TaskPacket $TaskPacket $contract $binding
foreach ($blocker in $packetResult.Blockers) { $executionBlockers.Add([string]$blocker) }
foreach ($blocker in (Get-ResearchContractBlockers $contract $Model $TelemetryTier ([string]$packetResult.Authority))) { $executionBlockers.Add($blocker) }
if ([string]$packetResult.Authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
    Add-Model4CollectionLaunchAuthorityBlockers `
        $contract $binding $packetResult $PSCommandPath $executionBlockers
}
Add-Model0EconomicLaunchAuthorityBlockers `
    $contract $binding $packetResult $PSCommandPath $executionBlockers
$isDataAcquisition = [string]$packetResult.Authority -in @(
    'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
    'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
)
if (-not $isDataAcquisition) {
    if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
        $executionBlockers.Add("Unified validator is missing: $validatorPath")
    }
    if (-not (Test-Path -LiteralPath $costBuilderPath -PathType Leaf)) {
        $executionBlockers.Add("Verified cost builder is missing: $costBuilderPath")
    }
}
if (-not (Test-Path -LiteralPath $nonRepaintToolPath -PathType Leaf)) {
    $executionBlockers.Add("Non-repaint audit tool is missing: $nonRepaintToolPath")
}
if ($ValidationStage -ceq 'confirmed') {
    $executionBlockers.Add("ValidationStage=confirmed cannot create a new run in the strict control/challenger loop. Freeze the completed run first, produce optimization-aware WFA and the full variant family, then invoke validate-full against that existing report.")
}
$forbiddenSkips = New-Object System.Collections.Generic.List[string]
if ($SkipCompile) { $forbiddenSkips.Add('SkipCompile') }
if ($SkipValidate) { $forbiddenSkips.Add('SkipValidate') }
if ($SkipCostStress) { $forbiddenSkips.Add('SkipCostStress') }
if ($SkipCompare) { $forbiddenSkips.Add('SkipCompare') }
if ($forbiddenSkips.Count -gt 0) {
    $executionBlockers.Add("Execution cannot use skip flags: SkipCompile, SkipValidate, SkipCostStress, SkipCompare. Supplied: $([string]::Join(', ', $forbiddenSkips.ToArray())).")
}

$executionAllowed = ($executionBlockers.Count -eq 0)
$plan = [ordered]@{
    ea = $EaName
    hypothesis_id = $HypothesisId
    run_role = $RunRole
    latest_registry_row = [ordered]@{
        line = $contract.RegistryLine
        state = $contract.RegistryState
        record_type = $contract.RegistryRecordType
        model = $contract.RegistryModel
        source_path = $contract.RegistrySourcePath
        source_sha256 = $contract.RegistrySourceHash
    }
    prereg_path = $contract.PreregPath
    prereg_sha256 = $contract.PreregSha256
    current_source_sha256 = $contract.CurrentSourceSha256
    ea_contract_path = $contract.EaContractPath
    ea_contract_sha256 = $contract.EaContractSha256
    telemetry_profile = $contract.TelemetryProfile
    market_phase_adapter = $contract.MarketPhaseAdapter
    comparison_adapter = $contract.ComparisonAdapter
    acceptance_contract = $contract.AcceptanceContract
    data_acceptance_contract = $contract.DataAcceptanceContract
    include_closure_sha256 = $packetResult.IncludeClosureSha256
    include_closure_count = @($packetResult.IncludeClosure | Where-Object { $null -ne $_ }).Count
    task_packet_path = $packetResult.PacketPath
    task_packet_sha256 = $packetResult.PacketSha256
    authority = [string]$packetResult.Authority
    symbol = $Symbol
    period = $Period
    from = $From
    to = $To
    model = $Model
    execution_mode = $ExecutionMode
    fixed_delay_ms = $FixedDelayMs
    timeout_sec = $TimeoutSec
    overrides = $effectiveOverrides
    telemetry_tier = $TelemetryTier
    deposit = $Deposit
    leverage = $Leverage
    spread = $effectiveSpread
    git_commit = $gitSnapshot.Commit
    git_status = @($gitSnapshot.Status)
    git_status_sha256 = $gitSnapshot.StatusSha256
    required_sidecars = @(
        $packetResult.RequiredSidecars |
            Where-Object { $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_) }
    )
    required_manifest_hashes = @(
        $packetResult.RequiredManifestHashes |
            Where-Object { $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_) }
    )
    broker_fingerprint = $binding.BrokerFingerprint
    server_fingerprint = $binding.ServerFingerprint
    account_fingerprint = $binding.AccountFingerprint
    data_fingerprint = $binding.DataFingerprint
    validation_stage = $ValidationStage
    cost_evidence_tier = $packetResult.CostEvidenceTier
    allow_research_cost_proxy = [bool]$AllowResearchCostProxy
    economic_window = [ordered]@{
        from = $packetResult.EconomicFrom
        to = $packetResult.EconomicTo
    }
    baseline_acceptance_contract = $packetResult.BaselineAcceptanceContract
    holding_contract = $HoldingContract
    cost_source_manifest = Resolve-EvidencePath $CostSourceManifest
    wfa_artifact = Resolve-EvidencePath $WfaArtifact
    variants_dir = Resolve-EvidencePath $VariantsDir
    matched_control_run_id = $MatchedControlRunId
    matched_control = if ($null -eq $packetResult.MatchedControl) { $null } else {
        [ordered]@{
            hypothesis_id = $packetResult.MatchedControl.HypothesisId
            run_dir = $packetResult.MatchedControl.RunDir
            manifest_path = $packetResult.MatchedControl.ManifestPath
            manifest_sha256 = $packetResult.MatchedControl.ManifestSha256
            report_path = $packetResult.MatchedControl.ReportPath
            report_sha256 = $packetResult.MatchedControl.ReportSha256
        }
    }
    orchestration_mode = if ($RunRole -ceq 'control') { "strict_control_bootstrap" } else { "challenger_against_preexisting_control" }
    compile_enforced_by_alpha_backtest = $true
    verified_cost_builder = $costBuilderPath
    nonrepaint_auditor = $nonRepaintToolPath
    execution_allowed = $executionAllowed
    execution_blockers = @($executionBlockers | ForEach-Object { $_ })
    execute = [bool]$Execute
}

if (-not $Execute) {
    if ($executionAllowed) {
        Write-Status "DRY RUN. Execution contract is ready; add -Execute to run." "WARN"
    } else {
        Write-Status "DRY RUN. EXECUTION BLOCKED by $($executionBlockers.Count) contract issue(s)." "WARN"
        foreach ($blocker in $executionBlockers) { Write-Host "  - $blocker" -ForegroundColor Yellow }
    }
    $plan | ConvertTo-Json -Depth 14
    exit 0
}

if (-not $executionAllowed) {
    throw "Execution blocked:`n - $([string]::Join("`n - ", $executionBlockers.ToArray()))"
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$transitionDir = Join-Path $runtimeRoot "ea_research_transitions"
New-Item -ItemType Directory -Path $transitionDir -Force | Out-Null
$sessionId = "{0}_{1}_{2}" -f (Get-Date -Format "yyyyMMdd_HHmmss"), $PID, ([guid]::NewGuid().ToString("N").Substring(0, 8))
$script:transitionLogPath = Join-Path $transitionDir "$sessionId.jsonl"
$researchLock = $null
$steps = New-Object System.Collections.Generic.List[object]
$runDir = $null
$runId = $null
$report = $null
$analysisDir = $null
$evidence = [ordered]@{}
$receiptRecord = $null
$launchClaimRecord = $null
$economicAttemptRecord = $null
$validationLock = $null
$evidenceReadLocks = New-Object System.Collections.Generic.List[object]

try {
    $researchLock = Enter-ResearchLock $plan
    $immutableEvidencePaths = New-Object System.Collections.Generic.List[string]
    foreach ($path in @(
        $contract.RegistryPath,
        $contract.CanonicalSourceAbsolute,
        $contract.PreregPath,
        $contract.EaContractAbsolutePath,
        $packetResult.PacketPath,
        $packetResult.CostSourceManifestPath,
        $packetResult.WfaArtifactPath
    )) {
        if (-not [string]::IsNullOrWhiteSpace([string]$path)) { [void]$immutableEvidencePaths.Add([string]$path) }
    }
    foreach ($item in @($packetResult.IncludeClosure)) { [void]$immutableEvidencePaths.Add([string]$item.Path) }
    foreach ($item in @($binding.IndicatorDependencies)) { [void]$immutableEvidencePaths.Add([string]$item.source_absolute_path) }
    foreach ($item in @($packetResult.CostEvidence)) { [void]$immutableEvidencePaths.Add([string]$item.Path) }
    if (-not [string]::IsNullOrWhiteSpace([string]$packetResult.VariantsDir)) {
        foreach ($item in @(Get-ChildItem -LiteralPath $packetResult.VariantsDir -Recurse -File -ErrorAction Stop)) {
            [void]$immutableEvidencePaths.Add($item.FullName)
        }
    }
    if ($null -ne $packetResult.MatchedControl) {
        foreach ($path in @($packetResult.MatchedControl.ManifestPath, $packetResult.MatchedControl.ReportPath)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$path)) { [void]$immutableEvidencePaths.Add([string]$path) }
        }
        foreach ($item in @($packetResult.MatchedControl.Artifacts)) { [void]$immutableEvidencePaths.Add([string]$item.Path) }
        foreach ($item in @($packetResult.MatchedControl.Sidecars)) { [void]$immutableEvidencePaths.Add([string]$item.Path) }
    }
    if ([string]$packetResult.Authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        foreach ($item in @(Get-Model4ExecutionDependencyBindings $PSCommandPath)) {
            [void]$immutableEvidencePaths.Add([string]$item.absolute_path)
        }
        $model4ControlPlane = Get-Model4ControlPlaneBinding $PSCommandPath
        [void]$immutableEvidencePaths.Add([string]$model4ControlPlane.RunnerPath)
        [void]$immutableEvidencePaths.Add([string]$model4ControlPlane.ValidatorPath)
        $model4Validation = Get-ObjectProperty $contract.LatestRow 'validation'
        foreach ($rowBoundPath in @(
            (Get-ObjectProperty $model4Validation 'execute_gate_hardening_receipt_path'),
            (Get-ObjectProperty $model4Validation 'packet_set_dry_run_receipt_path')
        )) {
            if (-not [string]::IsNullOrWhiteSpace([string]$rowBoundPath)) {
                [void]$immutableEvidencePaths.Add((Resolve-EvidencePath $rowBoundPath))
            }
        }
        foreach ($testBinding in @((Get-ObjectProperty $model4Validation 'bound_tests'))) {
            $testPath = [string](Get-ObjectProperty $testBinding 'path')
            if (-not [string]::IsNullOrWhiteSpace($testPath)) {
                [void]$immutableEvidencePaths.Add((Resolve-EvidencePath $testPath))
            }
        }
    }
    Enter-ImmutableEvidenceReadLocks $immutableEvidencePaths $evidenceReadLocks
    if ([string]$packetResult.Authority -ceq 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE') {
        $postLockBlockers = New-Object System.Collections.Generic.List[string]
        Add-Model4PostLockRevalidationBlockers `
            $contract $binding $packetResult $PSCommandPath $postLockBlockers
        if ($postLockBlockers.Count -gt 0) {
            throw (
                "Post-lock Model4 execution revalidation failed:`n - " +
                [string]::Join("`n - ", $postLockBlockers.ToArray())
            )
        }
    }
    $launchClaimRecord = New-Model4CollectionLaunchClaim $contract $binding $packetResult $PSCommandPath
    if ($null -eq $launchClaimRecord) {
        $economicAttemptRecord = New-Model0EconomicLaunchClaim $contract $binding $packetResult
        $launchClaimRecord = $economicAttemptRecord
    }
    if ($null -ne $launchClaimRecord) {
        if ($contract.HypothesisId -ceq 'HYP-STBS-XAUUSD-M15-026') {
            $packetValidation = Get-ObjectProperty $contract.LatestRow 'validation'
            $packetChainPaths = @(
                (Resolve-EvidencePath ([string](Get-ObjectProperty $packetValidation 'packet_build_attempt_start_path'))),
                (Resolve-EvidencePath ([string](Get-ObjectProperty $packetValidation 'packet_build_attempt_terminal_path'))),
                (Resolve-EvidencePath ([string](Get-ObjectProperty $packetValidation 'gitignore_path'))),
                (Resolve-EvidencePath ([string](Get-ObjectProperty $packetValidation 'independent_post_packet_review_path')))
            )
            foreach ($governancePathField in @(
                'parent_hyp025_failure_path',
                'parent_hyp025_post_failure_review_path',
                'journal_budget_tester_projection_path',
                'journal_budget_agent_projection_path',
                'journal_budget_addendum_path',
                'pre_execution_harness_addendum_path',
                'independent_pre_run_review_path',
                'bounded_diff_proof_path',
                'source_contract_test_path'
            )) {
                $packetChainPaths += Resolve-EvidencePath ([string](Get-ObjectProperty $packetValidation $governancePathField))
            }
            Enter-ImmutableEvidenceReadLocks $packetChainPaths $evidenceReadLocks
            Assert-Hyp026PacketBuildChain $contract $packetResult $launchClaimRecord
        }
        $evidence.launch_claim_path = $launchClaimRecord.Path
        $evidence.launch_claim_sha256 = $launchClaimRecord.Sha256
        $postClaimGitSnapshot = Get-GitSnapshot $contract.CanonicalSourceAbsolute
        $binding.GitCommit = $postClaimGitSnapshot.Commit
        $binding.GitStatus = @($postClaimGitSnapshot.Status)
        $binding.GitStatusSha256 = $postClaimGitSnapshot.StatusSha256
    }
    # A normal user terminal from another MT5 installation is safe and remains
    # completely outside runner ownership. Only the executable AlphaFactory is
    # about to launch (or a process whose identity cannot be resolved) blocks.
    $alphaMt5ExecutablePath = Resolve-AlphaMt5ExecutablePath -AlphaRoot $alphaRoot
    Assert-NoConflictingAlphaTerminal -ExpectedExecutablePath $alphaMt5ExecutablePath
    Add-StateTransition "execution_started" "Registry, source, prereg, task packet, and cost-source contract validated." | Out-Null

    $receiptPath = Join-Path $runtimeRoot "ea_execution_receipt_$sessionId.json"
    $receiptRecord = New-ExecutionReceipt $receiptPath $contract $packetResult $binding $launchClaimRecord $PSCommandPath
    $evidence.execution_receipt_path = $receiptRecord.Path
    $evidence.execution_receipt_sha256 = $receiptRecord.Sha256

    $backtestParameters = @{
        HypothesisId = $HypothesisId
        RunRole = $RunRole
        Symbol = $Symbol
        Period = $Period
        From = $From
        To = $To
        Model = $Model
        ExecutionMode = $ExecutionMode
        FixedDelayMs = $FixedDelayMs
        TimeoutSec = $TimeoutSec
        Overrides = $effectiveOverrides
        TelemetryTier = $TelemetryTier
        Deposit = $Deposit
        Leverage = $Leverage
        ContractReceipt = $receiptRecord.Path
        ContractReceiptSha256 = $receiptRecord.Sha256
        RequiredSidecars = [string]::Join(';', @($packetResult.RequiredSidecars))
    }
    if (-not [string]::IsNullOrWhiteSpace($Spread)) { $backtestParameters.Spread = $Spread }
    $backtest = Invoke-RequiredStep "Backtest $EaName $Symbol $Period $From-$To Model=$Model" { & $alphaPs1 backtest $EaName @backtestParameters } $steps
    $runDir = Resolve-ExactRunDir (Parse-RunDir $backtest.Output) $EaName $HypothesisId
    $runId = Split-Path -Leaf $runDir
    $report = Join-Path $runDir "report.html"
    $analysisDir = Join-Path $runDir "analysis"
    New-Item -ItemType Directory -Path $analysisDir -Force | Out-Null
    [void](Assert-RunManifestMatchesPacket (Join-Path $runDir 'run_manifest.json') $packetResult $binding $contract $receiptRecord.Sha256)
    Add-StateTransition "backtest_succeeded" "run_id=$runId; alpha backtest enforced compile." | Out-Null
    if ($RunRole -ceq 'challenger') {
        $evidence.matched_control_run_id = $packetResult.MatchedControl.RunId
        $evidence.matched_control_hypothesis_id = $packetResult.MatchedControl.HypothesisId
        $evidence.matched_control_manifest_path = $packetResult.MatchedControl.ManifestPath
        $evidence.matched_control_manifest_sha256 = $packetResult.MatchedControl.ManifestSha256
        $evidence.matched_control_report_path = $packetResult.MatchedControl.ReportPath
        $evidence.matched_control_report_sha256 = $packetResult.MatchedControl.ReportSha256
    }

    $runManifestPath = Join-Path $runDir 'run_manifest.json'
    $runManifestShaForAudit = Get-Sha256IfExists $runManifestPath
    $nonRepaintRunManifestPath = New-Hyp026NonRepaintAuditManifest $runManifestPath $runManifestShaForAudit $analysisDir
    $nonRepaintRunManifestShaForAudit = Get-Sha256IfExists $nonRepaintRunManifestPath
    $nonRepaintAuditorShaForAudit = Get-Sha256IfExists $nonRepaintToolPath
    if ($nonRepaintAuditorShaForAudit -cne $hyp026NonRepaintAuditorSha256) {
        throw "HYP026 non-repaint auditor hash drifted before execution."
    }
    $nonRepaintArtifact = Join-Path $analysisDir 'nonrepaint_audit.json'
    [void](Invoke-RequiredStep "Non-repaint audit $runId" {
        & python $nonRepaintToolPath --manifest $nonRepaintRunManifestPath --out $nonRepaintArtifact --receipt $receiptRecord.Path
    } $steps)
    if (-not (Test-Path -LiteralPath $nonRepaintArtifact -PathType Leaf)) {
        throw "Non-repaint auditor succeeded without creating: $nonRepaintArtifact"
    }
    try {
        $nonRepaintResult = Get-Content -LiteralPath $nonRepaintArtifact -Raw | ConvertFrom-Json
    } catch {
        throw "Non-repaint artifact is not valid JSON: $nonRepaintArtifact"
    }
    $expectedSnapshotSourcePath = [System.IO.Path]::GetFullPath((Join-Path $runDir ("snapshot\source\{0}.mq5" -f $EaName)))
    if (-not (Test-ExactObjectKeys $nonRepaintResult @(
            'schema_version', 'status', 'hypothesis_id', 'run_id', 'manifest',
            'manifest_sha256', 'collection_authority_verified', 'audited_files',
            'findings', 'allowed_new_bar_gates', 'generated_at_utc'
        )) -or
        [string]$nonRepaintResult.schema_version -cne 'alphafactory_nonrepaint_audit.v1' -or
        [string]$nonRepaintResult.status -cne 'PASS' -or
        [string]$nonRepaintResult.run_id -cne $runId -or
        [string]$nonRepaintResult.hypothesis_id -cne $HypothesisId -or
        -not [string]::Equals([System.IO.Path]::GetFullPath([string]$nonRepaintResult.manifest), [System.IO.Path]::GetFullPath($nonRepaintRunManifestPath), [System.StringComparison]::OrdinalIgnoreCase) -or
        [string]$nonRepaintResult.manifest_sha256 -cne $nonRepaintRunManifestShaForAudit -or
        $nonRepaintResult.collection_authority_verified -ne $false) {
        throw "Non-repaint audit identity/status contract failed for run '$runId'."
    }
    $auditedFiles = @($nonRepaintResult.audited_files)
    $findings = @($nonRepaintResult.findings)
    $allowedGates = @($nonRepaintResult.allowed_new_bar_gates)
    if ($auditedFiles.Count -ne 1 -or
        -not (Test-ExactObjectKeys $auditedFiles[0] @('path', 'sha256')) -or
        -not [string]::Equals([System.IO.Path]::GetFullPath([string]$auditedFiles[0].path), $expectedSnapshotSourcePath, [System.StringComparison]::OrdinalIgnoreCase) -or
        [string]$auditedFiles[0].sha256 -cne $hyp026SourceSha256 -or
        $findings.Count -ne 0 -or
        $allowedGates.Count -ne 1 -or
        -not (Test-ExactObjectKeys $allowedGates[0] @('path', 'line', 'rule', 'function', 'disposition')) -or
        -not [string]::Equals([System.IO.Path]::GetFullPath([string]$allowedGates[0].path), $expectedSnapshotSourcePath, [System.StringComparison]::OrdinalIgnoreCase) -or
        [int]$allowedGates[0].line -ne $hyp026CopyTimeLine -or
        [string]$allowedGates[0].rule -cne 'collection_first_date_copytime' -or
        [string]$allowedGates[0].function -cne 'CopyTime' -or
        [string]$allowedGates[0].disposition -cne 'allowed_collection_provenance_read') {
        throw "Non-repaint audit semantic allowlist contract failed for run '$runId'."
    }
    $nonRepaintArtifactSha = Get-Sha256IfExists $nonRepaintArtifact
    if ((Get-Sha256IfExists $nonRepaintToolPath) -cne $nonRepaintAuditorShaForAudit -or
        (Get-Sha256IfExists $nonRepaintRunManifestPath) -cne $nonRepaintRunManifestShaForAudit -or
        (Get-Sha256IfExists $nonRepaintArtifact) -cne $nonRepaintArtifactSha) {
        throw "HYP026 non-repaint auditor, derivative manifest or audit artifact drifted during validation."
    }
    $evidence.nonrepaint_audit_path = $nonRepaintArtifact
    $evidence.nonrepaint_audit_sha256 = $nonRepaintArtifactSha
    $evidence.nonrepaint_run_manifest_path = $nonRepaintRunManifestPath
    $evidence.nonrepaint_run_manifest_sha256 = $nonRepaintRunManifestShaForAudit
    $evidence.nonrepaint_original_manifest_sha256 = $runManifestShaForAudit
    $evidence.nonrepaint_auditor_path = $nonRepaintToolPath
    $evidence.nonrepaint_auditor_sha256 = $nonRepaintAuditorShaForAudit
    $evidence.nonrepaint_audited_source_path = $expectedSnapshotSourcePath
    $evidence.nonrepaint_audited_source_sha256 = $hyp026SourceSha256
    $evidence.nonrepaint_allowed_gate = [ordered]@{
        path = $expectedSnapshotSourcePath
        line = $hyp026CopyTimeLine
        rule = 'collection_first_date_copytime'
        function = 'CopyTime'
        disposition = 'allowed_collection_provenance_read'
    }
    Add-StateTransition "nonrepaint_audit_passed" $nonRepaintArtifact | Out-Null

    if ([string]$packetResult.Authority -in @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )) {
        $collectionSummaryPath = Join-Path $analysisDir 'enhanced_summary.json'
        [void](Assert-ZeroTradeCollectionSummary $collectionSummaryPath ([string]$packetResult.Authority))
        $evidence.zero_trade_collection_summary_path = $collectionSummaryPath
        $evidence.zero_trade_collection_summary_sha256 = Get-Sha256IfExists $collectionSummaryPath
        Add-StateTransition "data_acquisition_verified" "Zero trades; frozen history-quality gate and no-performance authority verified." | Out-Null
        Add-StateTransition "completed" "Data acquisition, post-run history-quality verification, and non-repaint audit succeeded; economic validation was forbidden." | Out-Null

        $collectionLoopSummary = [ordered]@{
            schema_version = "alphafactory_research_loop.v1"
            hypothesis_id = $HypothesisId
            registry_state_at_start = $contract.RegistryState
            registry_line_at_start = $contract.RegistryLine
            task_packet_path = $packetResult.PacketPath
            task_packet_sha256 = $packetResult.PacketSha256
            run_id = $runId
            run_dir = $runDir
            report = $report
            plan = $plan
            evidence = $evidence
            state_transitions = @($script:transitions | ForEach-Object { $_ })
            transition_log = $script:transitionLogPath
            steps = @($steps | ForEach-Object {
                [ordered]@{ label = $_.Label; exit_code = $_.ExitCode; error = $_.Error }
            })
            finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        }
        $collectionLoopSummaryPath = Join-Path $analysisDir "ea_research_loop_summary.json"
        Write-JsonAtomically $collectionLoopSummary $collectionLoopSummaryPath 16
        $evidence.research_loop_summary_path = $collectionLoopSummaryPath
        $evidence.research_loop_summary_sha256 = Get-Sha256IfExists $collectionLoopSummaryPath
        Copy-Item -LiteralPath $script:transitionLogPath -Destination (Join-Path $analysisDir "ea_research_state_transitions.jsonl") -Force
        Update-RunManifestResearch (Join-Path $runDir "run_manifest.json") $contract $packetResult $plan $script:transitions $script:transitionLogPath $evidence
        Write-JsonAtomically $collectionLoopSummary (Join-Path $runtimeRoot "last_ea_research_loop.json") 16
        Write-Status "Data-acquisition research loop complete: $collectionLoopSummaryPath" "OK"
        return
    }

    $costArtifact = Join-Path $analysisDir "verified_cost_artifact.json"
    $costBuildArgs = @(
        $costBuilderPath,
        "--report", $report,
        "--cost-source-manifest", $packetResult.CostSourceManifestPath,
        "--economic-from", $packetResult.EconomicFrom,
        "--economic-to", $packetResult.EconomicTo,
        "--out", $costArtifact
    )
    [void](Invoke-RequiredStep "Build report-bound execution cost artifact $runId" { & python @costBuildArgs } $steps)
    if (-not (Test-Path -LiteralPath $costArtifact -PathType Leaf)) {
        throw "Verified cost builder succeeded without creating required artifact: $costArtifact"
    }
    $evidence.cost_source_manifest_path = $packetResult.CostSourceManifestPath
    $evidence.cost_source_manifest_sha256 = Get-Sha256IfExists $packetResult.CostSourceManifestPath
    $evidence.cost_artifact_path = $costArtifact
    $evidence.cost_artifact_sha256 = Get-Sha256IfExists $costArtifact
    Add-StateTransition $(if ($AllowResearchCostProxy) { "research_cost_proxy_artifact_built" } else { "verified_cost_artifact_built" }) $costArtifact | Out-Null

    # Evidence revalidation before validation: close the backtest-to-validator
    # TOCTOU window for packet/source/cost/WFA/variants/control and run outputs.
    $validationLock = Enter-GlobalValidationLock $receiptRecord
    [void](Assert-EvidenceUnchanged $receiptRecord.Path $receiptRecord.Sha256 $binding)
    [void](Assert-RunManifestMatchesPacket (Join-Path $runDir 'run_manifest.json') $packetResult $binding $contract $receiptRecord.Sha256)

    $validationArgs = @(
        $validatorPath,
        "--report", $report,
        "--out", $analysisDir,
        "--stage", $packetResult.ValidationStage,
        "--holding-contract", $packetResult.HoldingContract,
        "--cost-artifact", $costArtifact
    )
    if ($null -ne $packetResult.BaselineAcceptanceContract) {
        $validationArgs += @(
            "--economic-from", $packetResult.EconomicFrom,
            "--economic-to", $packetResult.EconomicTo,
            "--min-completed-trades", [string]$packetResult.BaselineAcceptanceContract.min_completed_trades,
            "--min-direction-share", [string]$packetResult.BaselineAcceptanceContract.min_direction_share,
            "--max-year-trade-share", [string]$packetResult.BaselineAcceptanceContract.max_year_trade_share,
            "--require-positive-cost-expectancy",
            "--require-all-calendar-years-positive"
        )
    }
    $validationArgs += @(
        "--min-pf", [string]$packetResult.AcceptanceContract.min_profit_factor,
        "--min-trades-per-week", [string]$packetResult.AcceptanceContract.min_trades_per_week,
        "--max-trades-per-week", [string]$packetResult.AcceptanceContract.max_trades_per_week,
        "--max-dd-pct", [string]$packetResult.AcceptanceContract.max_drawdown_pct,
        "--min-cost-pf-x1-5", [string]$packetResult.AcceptanceContract.min_cost_pf_x1_5,
        "--min-cost-pf-x2", [string]$packetResult.AcceptanceContract.min_cost_pf_x2,
        "--max-mc-p95-dd-pct", [string]$packetResult.AcceptanceContract.max_monte_carlo_p95_dd_pct
    )
    if (-not [string]::IsNullOrWhiteSpace($packetResult.WfaArtifactPath)) {
        $validationArgs += @("--wfa-artifact", $packetResult.WfaArtifactPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($packetResult.VariantsDir)) {
        $validationArgs += @("--variants-dir", $packetResult.VariantsDir)
    }
    if ($AllowResearchCostProxy) {
        $validationArgs += @("--allow-research-cost-proxy")
    }
    $validationLabel = "Unified validation $runId stage=$($packetResult.ValidationStage)"
    if ($AllowResearchCostProxy) {
        $validationResult = Invoke-Logged $validationLabel { & python @validationArgs }
        $steps.Add($validationResult)
        if ($validationResult.ExitCode -notin @(0, 1)) {
            throw "Research-proxy validation failed operationally: $validationLabel (exit code $($validationResult.ExitCode))"
        }
    } else {
        [void](Invoke-RequiredStep $validationLabel { & python @validationArgs } $steps)
    }
    $validationSummary = Join-Path $analysisDir "validation_summary.json"
    if (-not (Test-Path -LiteralPath $validationSummary -PathType Leaf)) {
        throw "Unified validator succeeded without creating validation_summary.json."
    }
    $evidence.validation_summary_path = $validationSummary
    $evidence.validation_summary_sha256 = Get-Sha256IfExists $validationSummary
    if ($AllowResearchCostProxy) {
        $validationPayload = Get-Content -LiteralPath $validationSummary -Raw | ConvertFrom-Json
        if ($validationPayload.research_cost_proxy -ne $true -or $validationPayload.promotion_eligible -ne $false) {
            throw "Research-proxy validation summary lost its non-promotion contract."
        }
        if ($null -eq $packetResult.BaselineAcceptanceContract -or
            [string]::IsNullOrWhiteSpace([string]$validationPayload.baseline_falsification_verdict) -or
            [string]$validationPayload.baseline_falsification_verdict -notin @('PASS', 'FAIL', 'BLOCKED')) {
            throw "Research-proxy validation summary lacks the frozen baseline falsification verdict."
        }
        Add-StateTransition "unified_research_validation_completed" (
            "full=$([string]$validationPayload.verdict); baseline=$([string]$validationPayload.baseline_falsification_verdict)"
        ) | Out-Null
    } else {
        Add-StateTransition "unified_validation_succeeded" | Out-Null
    }

    if (-not $SkipMarketPhase -and $contract.MarketPhaseAdapter -ceq 'sonic') {
        $phaseTool = Join-Path $toolsRoot "sonic_market_phase_attribution.py"
        if (-not (Test-Path -LiteralPath $phaseTool -PathType Leaf)) { throw "Required market-phase tool is missing: $phaseTool" }
        [void](Invoke-RequiredStep "Market phase attribution $runId" { & python $phaseTool $runDir --ea $EaName --out $analysisDir } $steps)
        Add-StateTransition "market_phase_succeeded" | Out-Null
    } elseif (-not $SkipMarketPhase) {
        Add-StateTransition "market_phase_not_applicable" "EA telemetry profile '$($contract.TelemetryProfile)' has no Sonic phase sidecars." | Out-Null
    }

    if ($RunRole -ceq 'challenger') {
        $useSonicComparator = $contract.ComparisonAdapter -ceq 'sonic-v1'
        $compareTool = Join-Path $toolsRoot $(if ($useSonicComparator) { 'candidate_compare_engine.py' } else { 'alpha_candidate_compare.py' })
        if (-not (Test-Path -LiteralPath $compareTool -PathType Leaf)) { throw "Required candidate-compare tool is missing: $compareTool" }
        $compareOut = Join-Path $analysisDir $(if ($useSonicComparator) { 'sonic_candidate_compare.json' } else { 'candidate_compare.json' })
        [void](Invoke-RequiredStep "Candidate compare $runId vs $($packetResult.MatchedControlRunId)" {
            & python $compareTool $runDir --baseline $packetResult.MatchedControlRunId --ea $EaName --out $compareOut
        } $steps)
        if (-not (Test-Path -LiteralPath $compareOut -PathType Leaf)) { throw "Candidate compare did not create: $compareOut" }
        try {
            $compareResult = Get-Content -LiteralPath $compareOut -Raw | ConvertFrom-Json
        } catch {
            throw "Candidate compare artifact is not valid JSON: $compareOut"
        }
        $expectedCompareSchema = if ($useSonicComparator) { 'sonic_candidate_compare.v1' } else { 'alphafactory_candidate_compare.v1' }
        if ([string]$compareResult.schema_version -cne $expectedCompareSchema -or
            [string]$compareResult.verdict -cne 'RESEARCH_PASS' -or
            [string]$compareResult.candidate.run_id -cne $runId -or
            [string]$compareResult.baseline.run_id -cne $packetResult.MatchedControlRunId) {
            throw "Candidate comparison did not return an identity-bound RESEARCH_PASS for '$runId' against '$($packetResult.MatchedControlRunId)'."
        }
        $evidence.candidate_compare_path = $compareOut
        $evidence.candidate_compare_sha256 = Get-Sha256IfExists $compareOut
        Add-StateTransition "candidate_compare_succeeded" | Out-Null
    } else {
        Add-StateTransition "strict_control_bootstrap_succeeded" "run_id=$runId" | Out-Null
    }

    $runsDb = Join-Path $toolsRoot "runs_db.py"
    if (-not (Test-Path -LiteralPath $runsDb -PathType Leaf)) { throw "Required runs database tool is missing: $runsDb" }
    [void](Invoke-RequiredStep "Refresh runs database" {
        # runs_db intentionally logs INFO to stderr. Windows PowerShell turns
        # redirected native stderr into ErrorRecord objects and, under the
        # fail-closed Invoke-Logged EAP=Stop wrapper, used to misclassify an
        # exit-0 database refresh as a failed required step.
        $nativeErrorAction = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $nativeOutput = @(& python $runsDb build 2>&1)
            $nativeExitCode = [int]$LASTEXITCODE
        } finally {
            $ErrorActionPreference = $nativeErrorAction
        }
        $nativeOutput | ForEach-Object { Write-Output $_.ToString() }
        $global:LASTEXITCODE = $nativeExitCode
        if ($nativeExitCode -ne 0) {
            throw "runs_db.py build failed with exit code $nativeExitCode."
        }
    } $steps)
    Add-StateTransition "runs_database_succeeded" | Out-Null

    if ($CleanupCommonFiles) {
        $cleanupTerminals = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
        if ($cleanupTerminals.Count -gt 0) {
            $cleanupPids = ($cleanupTerminals | ForEach-Object { $_.Id }) -join ','
            throw "Common Files cleanup refused because terminal64 is active (PID(s): $cleanupPids)."
        }
        $archiveTool = Join-Path $toolsRoot "archive_backtest_artifacts.ps1"
        if (-not (Test-Path -LiteralPath $archiveTool -PathType Leaf)) { throw "Requested archive tool is missing: $archiveTool" }
        [void](Invoke-RequiredStep "Archive Common Files telemetry" { & $archiveTool -IncludeCommonFiles -Execute } $steps)
        Add-StateTransition "common_files_archive_succeeded" | Out-Null
    }

    Exit-GlobalValidationLock $validationLock
    $validationLock = $null

    $completionDetail = if ($RunRole -ceq 'control') {
        "Strict control bootstrap, report-bound cost evidence, and unified validation succeeded."
    } else {
        "Backtest, report-bound cost evidence, unified validation, and matched comparison succeeded."
    }
    Add-StateTransition "completed" $completionDetail | Out-Null
    $summary = [ordered]@{
        schema_version = "alphafactory_research_loop.v1"
        hypothesis_id = $HypothesisId
        registry_state_at_start = $contract.RegistryState
        registry_line_at_start = $contract.RegistryLine
        task_packet_path = $packetResult.PacketPath
        task_packet_sha256 = $packetResult.PacketSha256
        run_id = $runId
        run_dir = $runDir
        report = $report
        plan = $plan
        evidence = $evidence
        state_transitions = @($script:transitions | ForEach-Object { $_ })
        transition_log = $script:transitionLogPath
        steps = @($steps | ForEach-Object {
            [ordered]@{ label = $_.Label; exit_code = $_.ExitCode; error = $_.Error }
        })
        finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $summaryPath = Join-Path $analysisDir "ea_research_loop_summary.json"
    Write-JsonAtomically $summary $summaryPath 16
    $evidence.research_loop_summary_path = $summaryPath
    $evidence.research_loop_summary_sha256 = Get-Sha256IfExists $summaryPath
    Copy-Item -LiteralPath $script:transitionLogPath -Destination (Join-Path $analysisDir "ea_research_state_transitions.jsonl") -Force
    Update-RunManifestResearch (Join-Path $runDir "run_manifest.json") $contract $packetResult $plan $script:transitions $script:transitionLogPath $evidence
    Write-JsonAtomically $summary (Join-Path $runtimeRoot "last_ea_research_loop.json") 16
    $economicTerminal = Write-Model0EconomicAttemptTerminal $economicAttemptRecord 'COMPLETE' $runId $runDir
    if ($null -ne $economicTerminal) {
        $evidence.model0_economic_attempt_terminal_path = $economicTerminal.Path
        $evidence.model0_economic_attempt_terminal_sha256 = $economicTerminal.Sha256
    }
    Write-Status "Research loop complete: $summaryPath" "OK"
} catch {
    $failureMessage = $_.Exception.Message
    Add-StateTransition "failed" $failureMessage | Out-Null
    $failure = [ordered]@{
        schema_version = "alphafactory_research_loop_failure.v1"
        hypothesis_id = $HypothesisId
        task_packet_path = $packetResult.PacketPath
        run_id = $runId
        run_dir = $runDir
        error = $failureMessage
        state_transitions = @($script:transitions | ForEach-Object { $_ })
        transition_log = $script:transitionLogPath
        steps = @($steps | ForEach-Object {
            [ordered]@{ label = $_.Label; exit_code = $_.ExitCode; error = $_.Error }
        })
        failed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    try {
        Write-JsonAtomically $failure (Join-Path $runtimeRoot "last_failed_ea_research_loop.json") 14
    } catch {
        Write-Status "Could not write failure summary: $($_.Exception.Message)" "ERR"
    }
    try {
        [void](Write-Model0EconomicAttemptTerminal $economicAttemptRecord 'FAILED' $runId $runDir $failureMessage)
    } catch {
        Write-Status "Could not write Model0 economic attempt terminal: $($_.Exception.Message)" "ERR"
    }
    throw "Research loop failed: $failureMessage"
} finally {
    Exit-GlobalValidationLock $validationLock
    Exit-ImmutableEvidenceReadLocks $evidenceReadLocks
    Exit-ResearchLock $researchLock
}
