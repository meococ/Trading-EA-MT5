<#
.SYNOPSIS
    AlphaFactory v4.3 - Centralized EA Development CLI
.DESCRIPTION
    Complete toolchain for MT5 EA development:
    - Compile, Backtest, Analyze EAs
    - Monte Carlo & Walk-Forward validation
    - Post-run cleanup (staging/locks/compile logs)
    - Read-only Git status integration
    VectorBT scan is diagnostic-only and is not acceptance evidence.
.EXAMPLE
    .\alpha.ps1 status              # System status
    .\alpha.ps1 compile "EA Name"   # Compile EA
    .\alpha.ps1 backtest "EA Name"  # Full MT5 backtest
    .\alpha.ps1 analyze -Report "x" # Analyze report
    .\alpha.ps1 clean               # Dry-run post-run hygiene
    .\alpha.ps1 clean -Execute      # Safe cleanup after evidence is in runs/
    .\alpha.ps1 monte -Report "x"   # Monte Carlo simulation
    .\alpha.ps1 wfa -Report "x"     # Walk-Forward Analysis
    .\alpha.ps1 help                # Show all commands
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("compile", "backtest", "analyze", "list", "status", "git", "scan", "monte", "wfa", "help", "validate", "validate-full", "fast-kill", "delivery", "log", "robust", "param", "cpcv", "impact", "mt5data", "clean")]
    [string]$Action = "status",
    
    [Parameter(Position=1)]
    [string]$Name = "",
    
    [string]$Report = "",
    [string]$Packet = "",
    [string]$Symbol = "XAUUSD",
    [string]$Period = "M15",
    [string]$From = "2020.01.01",
    [string]$To = "2025.12.25",
    [ValidateSet(0, 1, 2, 4)]
    [int]$Model = 0,
    [int]$ExecutionMode = 0,
    [int]$TimeoutSec = 3600,
    [int]$FixedDelayMs = 0,
    [string]$Overrides = "",
    [string]$HypothesisId = "",
    [ValidateSet("control", "challenger")]
    [string]$RunRole = "challenger",
    [ValidateSet("off", "trade-only", "state-lite", "state-full", "snapshot-casebook")]
    [string]$TelemetryTier = "off",
    [int]$Deposit = 10000,
    [int]$Leverage = 100,
    [string]$Spread = "",
    [ValidateSet("challenger", "confirmed")]
    [string]$ValidationStage = "challenger",
    [ValidateSet("scalp", "non_scalp")]
    [string]$HoldingContract = "scalp",
    [string]$CostArtifact = "",
    [string]$WfaArtifact = "",
    [string]$VariantsDir = "",
    [string]$ContractReceipt = "",
    [string]$ContractReceiptSha256 = "",
    [string]$RequiredSidecars = "",
    [string]$Output = "",
    [string]$Param1 = "",
    [string]$Param2 = "",
    [string]$Metric = "Custom",
    [double]$PlateauFraction = 0.90,
    [int]$ExpectedTrials = 0,
    [string]$SelectedPass = "",
    [string]$SelectedReturns = "",
    [string]$ReturnsColumn = "net_r",
    [string]$SharpeColumn = "Custom",
    [switch]$LowerIsBetter,
    [ValidateSet("unspecified", "per_trade_net_r", "mt5_tester_sharpe")]
    [string]$SrSemantics = "unspecified",
    [switch]$SelectionFrozen,
    [int]$CpcvGroups = 8,
    [int]$CpcvTestGroups = 2,
    [double]$EmbargoPct = 0.01,
    [string]$TradesCsv = "",
    [ValidateSet("adv_proxy", "observed_depth")]
    [string]$LiquiditySource = "adv_proxy",
    [double]$ImpactEta = 0.5,
    [string]$Calibration = "",
    [switch]$Charts,
    [switch]$TradeCharts,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

# Config
$AdvisorsRoot = Split-Path -Parent $PSScriptRoot
$AlphaRoot = $PSScriptRoot
# Machine-specific MT5 paths live in alpha.local.ps1 (gitignored).
# Copy alpha.local.ps1.example or run: .\tools\init_machine_paths.ps1
$MT5InstallRoot = $null
$MT5DataRoot = $null
$MT5PortableMode = $false
$MT5CommonFilesRoot = $null
$MT5TesterRoot = $null
$MT5RequiredStorageDrive = ""
$MT5AllowCommonFiles = $true
$script:Mt5ConfigSource = "unset"
$LocalConfigPath = Join-Path $AlphaRoot "alpha.local.ps1"
if (Test-Path -LiteralPath $LocalConfigPath -PathType Leaf) {
    . $LocalConfigPath
    $script:Mt5ConfigSource = "alpha.local.ps1"
}

# Machine paths come from alpha.local.ps1 only. Auto-detect was removed
# 2026-08-31: Resolve-Mt5InstallRoot probed Program Files and
# Resolve-Mt5DataRoot walked %APPDATA%\MetaQuotes\Terminal\<32-hex>, so a
# missing local config silently retargeted the factory at the Owner GUI or at
# an AppData clone. Fail closed instead.
if ([string]::IsNullOrWhiteSpace($MT5InstallRoot) -or [string]::IsNullOrWhiteSpace($MT5DataRoot)) {
    throw @"
AlphaFactory has no machine paths. Auto-detect is disabled by contract.

Generate the pin:
    & ".\02. AlphaFactory\tools\init_machine_paths.ps1"

alpha.local.ps1 must set InstallRoot = DataRoot = a portable isolate under
'$(Join-Path $AlphaRoot 'runtime')' with PortableMode = true. Never Program
Files, never %APPDATA%\MetaQuotes\Terminal\<32-hex>, never the Owner GUI root
that holds the terminal you trade from.
"@
}

$Mt5StorageContractPath = Join-Path $AlphaRoot "tools\mt5_storage_contract.ps1"
if (-not (Test-Path -LiteralPath $Mt5StorageContractPath -PathType Leaf)) {
    throw "MT5 storage contract helper is missing: $Mt5StorageContractPath"
}
. $Mt5StorageContractPath

if ([string]::IsNullOrWhiteSpace($MT5CommonFilesRoot)) {
    $MT5CommonFilesRoot = if ($MT5PortableMode) {
        Join-Path $MT5DataRoot "Common\Files"
    } else {
        Join-Path (Split-Path -Parent $MT5DataRoot) "Common\Files"
    }
}
if ([string]::IsNullOrWhiteSpace($MT5TesterRoot)) {
    $MT5TesterRoot = Join-Path $MT5DataRoot "Tester"
}

if ([string]::IsNullOrWhiteSpace($MT5InstallRoot) -or -not (Test-Path -LiteralPath (Join-Path $MT5InstallRoot "terminal64.exe") -PathType Leaf)) {
    throw "MT5 install root not found. Pin a portable isolate in alpha.local.ps1 (copy alpha.local.ps1.example or run tools\init_machine_paths.ps1). Do not use Owner Program Files / AppData."
}
if ([string]::IsNullOrWhiteSpace($MT5DataRoot) -or -not (Test-Path -LiteralPath (Join-Path $MT5DataRoot "MQL5") -PathType Container)) {
    throw "MT5 data root not found. For AlphaFactory, DataRoot must equal the portable InstallRoot (not AppData\MetaQuotes\Terminal\<32-hex>)."
}

$script:Mt5StorageContract = Assert-Mt5StorageContract `
    -InstallRoot $MT5InstallRoot `
    -DataRoot $MT5DataRoot `
    -CommonFilesRoot $MT5CommonFilesRoot `
    -TesterRoot $MT5TesterRoot `
    -PortableMode ([bool]$MT5PortableMode) `
    -AllowCommonFiles ([bool]$MT5AllowCommonFiles) `
    -RequiredDrive ([string]$MT5RequiredStorageDrive)
$script:Mt5FactoryRuntimeRoot = Join-Path $AlphaRoot 'runtime'
$script:Mt5FactoryTargetIsolate = Assert-Mt5FactoryTargetIsolate `
    -InstallRoot $MT5InstallRoot `
    -DataRoot $MT5DataRoot `
    -CommonFilesRoot $MT5CommonFilesRoot `
    -TesterRoot $MT5TesterRoot `
    -PortableMode ([bool]$MT5PortableMode) `
    -AllowCommonFiles ([bool]$MT5AllowCommonFiles) `
    -RuntimeRoot $script:Mt5FactoryRuntimeRoot
if ([bool]$MT5PortableMode -and [bool]$MT5AllowCommonFiles) {
    if (Test-Mt5PathUnderRoot -Path $MT5CommonFilesRoot -Root $MT5DataRoot) {
        if (-not (Test-Path -LiteralPath $MT5CommonFilesRoot -PathType Container)) {
            New-Item -ItemType Directory -Path $MT5CommonFilesRoot -Force | Out-Null
        }
    }
}

$MT5Mql5Root = Join-Path $MT5DataRoot "MQL5"
$MT5 = Join-Path $MT5InstallRoot "terminal64.exe"
$MetaEditor = Join-Path $MT5InstallRoot "metaeditor64.exe"
$GlobalBacktestLockPath = Join-Path $AlphaRoot "runtime\alpha_backtest.lock"
$script:GlobalBacktestLockStream = $null
$script:GlobalBacktestLockPayload = $null
$script:OwnedTerminalIdentities = New-Object 'System.Collections.Generic.Dictionary[int,object]'
$EaContractResolverPath = Join-Path $AlphaRoot "tools\ea_contract.ps1"
if (-not (Test-Path -LiteralPath $EaContractResolverPath -PathType Leaf)) {
    throw "EA source contract resolver is missing: $EaContractResolverPath"
}
. $EaContractResolverPath
$LogStoragePath = Join-Path $AlphaRoot "tools\log_storage.ps1"
if (-not (Test-Path -LiteralPath $LogStoragePath -PathType Leaf)) {
    throw "Log storage helper is missing: $LogStoragePath"
}
. $LogStoragePath

function Write-Status($Msg, $Type = "INFO") {
    $color = switch ($Type) {
        "INFO" { "Cyan" }
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERR" { "Red" }
        default { "White" }
    }
    Write-Host "[$Type] $Msg" -ForegroundColor $color
}

function Test-PathSafe($Path) {
    try { return (Test-Path $Path) } catch { return $false }
}

function Get-FileLengthSafe($Path) {
    try {
        if (Test-PathSafe $Path) { return (Get-Item $Path).Length }
    } catch {}
    return 0
}

function Get-Mt5ReportHtml([string]$Path) {
    if (-not (Test-PathSafe $Path)) { return $null }
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        if ($null -eq $bytes -or $bytes.Length -lt 2) { return $null }
        if ($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
            return [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
        }
        if ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
            return [System.Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
        }
        $utf8Start = 0
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $utf8Start = 3
        }
        return [System.Text.Encoding]::UTF8.GetString($bytes, $utf8Start, $bytes.Length - $utf8Start)
    } catch {
        return $null
    }
}

function Get-Sha256Required($Path, $Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label is missing and cannot be hashed: $Path"
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

function Assert-BacktestScalarContract($EAName, $Hypothesis, $Sym, $Per, $FromD, $ToD, $SpreadValue, $ExecutionModeValue, $FixedDelayValue) {
    $patterns = [ordered]@{
        EAName = '^[A-Za-z0-9][A-Za-z0-9 _.-]{0,127}$'
        HypothesisId = '^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$'
        Symbol = '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'
        Period = '^[A-Za-z0-9]{2,8}$'
    }
    $values = [ordered]@{
        EAName = [string]$EAName
        HypothesisId = [string]$Hypothesis
        Symbol = [string]$Sym
        Period = [string]$Per
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
    if (-not [datetime]::TryParseExact([string]$FromD, 'yyyy.MM.dd', $culture, $dateStyle, [ref]$fromDate)) {
        throw "From must use a real yyyy.MM.dd date with no control characters."
    }
    if (-not [datetime]::TryParseExact([string]$ToD, 'yyyy.MM.dd', $culture, $dateStyle, [ref]$toDate)) {
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
        if ($trimmed -notmatch '^[^=\r\n]+=[^=\r\n]*$') {
            throw "Malformed tester override '$trimmed'. Expected Name=Value."
        }
        $parts = $trimmed.Split('=', 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ([string]::IsNullOrWhiteSpace($name)) {
            throw "Malformed tester override '$trimmed': input name is empty."
        }
        if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            throw "Tester override input name '$name' is unsafe."
        }
        if ($value -match '[\x00-\x1F\x7F|]') {
            throw "Tester override '$name' contains unsafe control or delimiter characters."
        }
        if ($map.Contains($name)) {
            throw "Duplicate tester override '$name' is not deterministic."
        }
        $map[$name] = $value
    }
    return $map
}

function ConvertFrom-NormalizedOverrideMap($Map) {
    return [string]::Join(';', @($Map.Keys | Sort-Object | ForEach-Object { "$_=$($Map[$_])" }))
}

function Get-TelemetryInputNames {
    return @(
        'InpEnableTelemetry',
        'InpEnableOpportunityLogger',
        'InpEnableShadowNarrative',
        'InpEnableStateTelemetry',
        'InpEnableGoldRegimeTelemetry',
        'InpEnableSourceClassicDragonEdgeDistanceTelemetry',
        'InpEnableSourceH4TargetRunwayTelemetry',
        'InpEnableFxM15MtfPvaWeakeningTelemetry',
        'InpEnableFxClassicNearMissTelemetry'
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
        $declaration = '(?m)^\s*input\s+[^;\r\n]*\bInpEnableTelemetry\b\s*(?:=|;)'
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
        $declaration = '(?m)^\s*input\s+[^;\r\n]*\b' + [regex]::Escape($name) + '\b\s*(?:=|;)'
        if ($source -notmatch $declaration) {
            throw "EA input '$name' required for telemetry tier '$Tier' is absent from $MainFile."
        }
    }

    $enabled = @()
    switch ($Tier) {
        'off' { $enabled = @() }
        'trade-only' { $enabled = @('InpEnableTelemetry') }
        'state-lite' {
            $enabled = @('InpEnableTelemetry', 'InpEnableOpportunityLogger', 'InpEnableStateTelemetry')
        }
        'state-full' { $enabled = @($inputs) }
        'snapshot-casebook' { $enabled = @($inputs) }
    }

    $map = ConvertTo-NormalizedOverrideMap $OverrideText
    foreach ($name in $inputs) {
        $map[$name] = if ($name -in $enabled) { 'true' } else { 'false' }
    }
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

function ConvertTo-RequiredSidecarList([string]$Value, [string]$Tier, [string]$TelemetryProfile = 'sonic-strict') {
    $requested = @($Value -split ';' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($requested.Count -ne (@($requested | Select-Object -Unique)).Count) {
        throw "RequiredSidecars contains duplicate patterns."
    }
    foreach ($pattern in $requested) {
        if ($pattern -notmatch '^[A-Za-z0-9_.?*-]+$' -or $pattern -match '\.\.') {
            throw "Required sidecar pattern is unsafe: $pattern"
        }
    }
    foreach ($minimum in (Get-RequiredSidecarsForTier $Tier $TelemetryProfile)) {
        if ($minimum -notin $requested) {
            throw "RequiredSidecars is missing telemetry-tier minimum '$minimum' for tier '$Tier'."
        }
    }
    return @($requested | Sort-Object)
}

function Test-NoGitWorkspace {
    # Fail-closed NO-GIT: not a work tree, or empty .git placeholder (sandbox mount).
    # Native git stderr must not throw under $ErrorActionPreference=Stop.
    $gitDir = Join-Path $AdvisorsRoot ".git"
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $insideOutput = @(& git -C $AdvisorsRoot rev-parse --is-inside-work-tree 2>$null)
        $insideExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldEap
    }
    $inside = ""
    if ($null -ne $insideOutput -and @($insideOutput).Count -gt 0 -and $null -ne $insideOutput[0]) {
        $inside = ([string]$insideOutput[0]).Trim()
    }
    if (($insideExit -eq 0) -and ($inside -ceq 'true')) {
        return $false
    }
    if (Test-Path -LiteralPath $gitDir) {
        $entries = @(Get-ChildItem -LiteralPath $gitDir -Force -ErrorAction SilentlyContinue)
        if ($entries.Count -eq 0) { return $true }
        # Non-empty .git that is not a valid work tree: still NO-GIT provenance.
        return $true
    }
    return $true
}

function Get-NoGitProvenanceSnapshot {
    param([string]$ActiveSource = "")
    # Deterministic workspace provenance when root is intentionally not a Git repo.
    # Receipt validators only require non-empty git_commit + matching git_status_sha256.
    # ActiveSource (receipt-bound EA .mq5) is included when provided so concurrent
    # Model 0 screens do not collide on a hardcoded single-EA path.
    $agentsPath = Join-Path $AdvisorsRoot "AGENTS.md"
    $goalPath = Join-Path $AdvisorsRoot "01. GOAL\GOAL.md"
    $provenancePaths = @($agentsPath, $goalPath)
    foreach ($required in $provenancePaths) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "NO-GIT provenance file missing (fail-closed): $required"
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($ActiveSource)) {
        $activeFull = [System.IO.Path]::GetFullPath($ActiveSource)
        if (-not (Test-Path -LiteralPath $activeFull -PathType Leaf)) {
            throw "NO-GIT ActiveSource missing (fail-closed): $activeFull"
        }
        $provenancePaths += $activeFull
    }

    $records = New-Object System.Collections.Generic.List[string]
    foreach ($path in $provenancePaths) {
        $full = [System.IO.Path]::GetFullPath($path)
        $rootFull = [System.IO.Path]::GetFullPath($AdvisorsRoot).TrimEnd('\', '/')
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
    $statusLines = @(
        "nogit=true",
        "dirty=true",
        "provenance_sha256=$provSha"
    )
    return [pscustomobject]@{
        Commit = $commit
        Status = $statusLines
        StatusSha256 = Get-TextSha256 ([string]::Join("`n", $statusLines))
        NoGit = $true
        Dirty = $true
    }
}

function Get-GitSnapshot {
    param([string]$ActiveSource = "")
    if (Test-NoGitWorkspace) {
        return Get-NoGitProvenanceSnapshot -ActiveSource $ActiveSource
    }

    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $commitOutput = @(& git -C $AdvisorsRoot rev-parse HEAD 2>$null)
        $commitExitCode = $LASTEXITCODE
        $commit = $commitOutput | Select-Object -First 1
        if (($commitExitCode -ne 0) -or [string]::IsNullOrWhiteSpace([string]$commit)) {
            # Real work-tree identity missing: fall back to deterministic NO-GIT provenance
            # rather than hard-blocking backtest on an intentional no-Git root.
            return Get-NoGitProvenanceSnapshot -ActiveSource $ActiveSource
        }
        $status = @(& git -C $AdvisorsRoot status --short --untracked-files=all 2>$null)
        $statusExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldEap
    }
    if ($statusExitCode -ne 0) {
        throw "Git status is unavailable for run manifest."
    }
    $statusLines = @($status | ForEach-Object { [string]$_ })
    $statusPayload = [string]::Join("`n", $statusLines)
    return [pscustomobject]@{
        Commit = ([string]$commit).Trim()
        Status = $statusLines
        StatusSha256 = Get-TextSha256 $statusPayload
        NoGit = $false
        Dirty = ($statusLines.Count -gt 0)
    }
}

function Write-JsonAtomically($Value, $Path, $Depth = 10) {
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

function Write-BacktestLockPayload {
    if ($null -eq $script:GlobalBacktestLockStream) { return }
    $script:GlobalBacktestLockPayload.owned_terminal_identities = @(
        $script:OwnedTerminalIdentities.Values |
            Sort-Object Pid |
            ForEach-Object {
                [ordered]@{
                    pid = $_.Pid
                    start_time_utc = $_.StartTimeUtc
                    executable_path = $_.ExecutablePath
                }
            }
    )
    $json = $script:GlobalBacktestLockPayload | ConvertTo-Json -Depth 6
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $script:GlobalBacktestLockStream.Position = 0
    $script:GlobalBacktestLockStream.SetLength(0)
    $script:GlobalBacktestLockStream.Write($bytes, 0, $bytes.Length)
    $script:GlobalBacktestLockStream.Flush($true)
}

function Enter-GlobalBacktestLock($EAName, $Hypothesis) {
    $runtimeDir = Split-Path -Parent $GlobalBacktestLockPath
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    try {
        $stream = [System.IO.File]::Open(
            $GlobalBacktestLockPath,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    } catch [System.IO.IOException] {
        throw "Global AlphaFactory backtest lock already exists: $GlobalBacktestLockPath. Confirm the owning run before removing it."
    }

    $script:GlobalBacktestLockStream = $stream
    $script:GlobalBacktestLockPayload = [ordered]@{
        schema_version = "alphafactory_backtest_lock.v1"
        owner_token = [guid]::NewGuid().ToString("N")
        runner_pid = $PID
        ea_name = $EAName
        hypothesis_id = $Hypothesis
        started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        owned_terminal_identities = @()
    }
    try {
        Write-BacktestLockPayload
    } catch {
        $script:GlobalBacktestLockStream.Dispose()
        $script:GlobalBacktestLockStream = $null
        Remove-Item -LiteralPath $GlobalBacktestLockPath -Force -ErrorAction SilentlyContinue
        throw
    }
}

function Exit-GlobalBacktestLock {
    if ($null -ne $script:GlobalBacktestLockStream) {
        $script:GlobalBacktestLockStream.Dispose()
        $script:GlobalBacktestLockStream = $null
    }
    $script:GlobalBacktestLockPayload = $null
    if (Test-Path -LiteralPath $GlobalBacktestLockPath) {
        Remove-Item -LiteralPath $GlobalBacktestLockPath -Force
    }
}

function Invoke-AlphaPostRunCleanupSafe {
    param(
        [string]$EaName = '',
        [string]$RunId = '',
        [int]$MinAgeHours = 0
    )
    $tool = Join-Path $AlphaRoot 'tools\post_run_cleanup.ps1'
    if (-not (Test-Path -LiteralPath $tool -PathType Leaf)) {
        Write-Status "Post-run cleanup tool missing: $tool" "WARN"
        return
    }
    $global:LASTEXITCODE = 0
    if (-not [string]::IsNullOrWhiteSpace($EaName) -and -not [string]::IsNullOrWhiteSpace($RunId)) {
        & $tool -Scope safe -MinAgeHours $MinAgeHours -Execute -EaName $EaName -RunId $RunId
    } elseif (-not [string]::IsNullOrWhiteSpace($EaName)) {
        & $tool -Scope safe -MinAgeHours $MinAgeHours -Execute -EaName $EaName
    } elseif (-not [string]::IsNullOrWhiteSpace($RunId)) {
        & $tool -Scope safe -MinAgeHours $MinAgeHours -Execute -RunId $RunId
    } else {
        & $tool -Scope safe -MinAgeHours $MinAgeHours -Execute
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Post-run cleanup failed with exit code $LASTEXITCODE."
    }
}

function Get-RunnerTerminalProcessIdentity([int]$ProcessId) {
    $executablePath = $null
    $startTimeUtc = $null
    for ($attempt = 1; $attempt -le 15; $attempt++) {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        $startTimeUtc = $process.StartTime.ToUniversalTime().ToString('o')
        $rawPath = [string]$process.Path
        if ([string]::IsNullOrWhiteSpace($rawPath)) {
            $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
            if ($null -ne $cim -and -not [string]::IsNullOrWhiteSpace([string]$cim.ExecutablePath)) {
                $rawPath = [string]$cim.ExecutablePath
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($rawPath)) {
            $executablePath = [System.IO.Path]::GetFullPath($rawPath)
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if ([string]::IsNullOrWhiteSpace($executablePath)) {
        throw "Terminal PID $ProcessId executable path is unavailable."
    }
    return [pscustomobject]@{
        Pid = $ProcessId
        StartTimeUtc = $startTimeUtc
        ExecutablePath = $executablePath
    }
}

function Test-RunnerOwnedTerminalIdentity([int]$ProcessId, $ExpectedIdentity = $null) {
    if ($null -eq $ExpectedIdentity) {
        if (-not $script:OwnedTerminalIdentities.ContainsKey($ProcessId)) { return $false }
        $ExpectedIdentity = $script:OwnedTerminalIdentities[$ProcessId]
    }
    try {
        $actual = Get-RunnerTerminalProcessIdentity $ProcessId
    } catch {
        return $false
    }
    return ([string]$actual.StartTimeUtc -ceq [string]$ExpectedIdentity.StartTimeUtc) -and
        ([string]$actual.ExecutablePath -ieq [string]$ExpectedIdentity.ExecutablePath)
}

function Register-RunnerOwnedTerminal([int]$ProcessId) {
    $identity = Get-RunnerTerminalProcessIdentity $ProcessId
    $expectedExecutable = [System.IO.Path]::GetFullPath($MT5)
    if ($identity.ExecutablePath -ine $expectedExecutable) {
        throw "Refusing to register PID ${ProcessId}: executable identity '$($identity.ExecutablePath)' does not match '$expectedExecutable'."
    }
    $script:OwnedTerminalIdentities[$ProcessId] = $identity
    Write-BacktestLockPayload
}

function Stop-RunnerOwnedTerminal([int]$ProcessId) {
    if (-not $script:OwnedTerminalIdentities.ContainsKey($ProcessId)) {
        throw "Refusing to stop terminal64 PID $ProcessId because it is not runner-owned."
    }
    $expectedIdentity = $script:OwnedTerminalIdentities[$ProcessId]
    $current = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $current) {
        [void]$script:OwnedTerminalIdentities.Remove($ProcessId)
        Write-BacktestLockPayload
        return
    }
    if (-not (Test-RunnerOwnedTerminalIdentity $ProcessId $expectedIdentity)) {
        throw "Refusing to stop terminal64 PID $ProcessId because its process identity changed (PID reuse or executable/start-time mismatch)."
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction Stop
    if (-not $current.WaitForExit(30000)) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        if (-not $current.WaitForExit(15000)) {
            throw "Runner-owned terminal64 PID $ProcessId did not exit after a verified stop request; ownership is retained."
        }
    }
    [void]$script:OwnedTerminalIdentities.Remove($ProcessId)
    Write-BacktestLockPayload
}

function Stop-AllRunnerOwnedTerminals {
    foreach ($processId in @($script:OwnedTerminalIdentities.Keys)) {
        Stop-RunnerOwnedTerminal $processId
    }
    Write-BacktestLockPayload
}

function Get-Terminal64ExecutablePath([int]$ProcessId) {
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    $rawPath = if ($null -ne $process) { [string]$process.Path } else { '' }
    if ([string]::IsNullOrWhiteSpace($rawPath)) {
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
        if ($null -ne $cim -and -not [string]::IsNullOrWhiteSpace([string]$cim.ExecutablePath)) {
            $rawPath = [string]$cim.ExecutablePath
        }
    }
    if ([string]::IsNullOrWhiteSpace($rawPath)) { return $null }
    return [System.IO.Path]::GetFullPath($rawPath)
}

function Test-RunnerPortableOrHarnessTerminal([int]$ProcessId) {
    $full = Get-Terminal64ExecutablePath $ProcessId
    if ([string]::IsNullOrWhiteSpace($full)) { return $true }
    $expected = [System.IO.Path]::GetFullPath($MT5)
    if ($full.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) { return $true }
    $runtime = [System.IO.Path]::GetFullPath((Join-Path $AlphaRoot 'runtime'))
    $prefix = $runtime + [IO.Path]::DirectorySeparatorChar
    return $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
}

function Assert-NoUnrelatedTerminal {
    $ownedPids = @(
        $script:OwnedTerminalIdentities.Keys |
            Where-Object { Test-RunnerOwnedTerminalIdentity $_ $script:OwnedTerminalIdentities[$_] } |
            ForEach-Object { [int]$_ }
    )
    Assert-Mt5FactoryProcessIsolate `
        -InstallRoot $MT5InstallRoot `
        -DataRoot $MT5DataRoot `
        -RuntimeRoot $script:Mt5FactoryRuntimeRoot `
        -OwnedPids $ownedPids `
        -AllowProgramFilesGui $true `
        -PortableMode ([bool]$MT5PortableMode)
}

function Get-ListeningPortProcessName([int]$Port) {
    $escaped = [regex]::Escape([string]$Port)
    foreach ($line in @(& netstat -ano)) {
        $text = [string]$line
        if ($text -notmatch "[:\]]$escaped\s+" -or $text -notmatch 'LISTENING') { continue }
        if ($text -notmatch '(\d+)\s*$') { continue }
        $procId = [int]$Matches[1]
        if ($procId -le 0) { continue }
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($null -ne $proc -and -not [string]::IsNullOrWhiteSpace($proc.ProcessName)) {
            return [string]$proc.ProcessName
        }
        return "pid$procId"
    }
    return ""
}

function Resolve-LocalTesterAgentPort {
    $name = Get-ListeningPortProcessName 3000
    if ([string]::IsNullOrWhiteSpace($name) -or $name -match '(?i)metatester') {
        return 3000
    }
    Write-Status "Local tester port 3000 is occupied by $name; routing agent to 3010" "WARN"
    return 3010
}

function Find-PortablePostUpdateTester([string]$ConfigPath) {
    $portableExe = [System.IO.Path]::GetFullPath($MT5)
    $cfg = [System.IO.Path]::GetFullPath($ConfigPath)
    foreach ($proc in @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue)) {
        $exe = [string]$proc.ExecutablePath
        $line = [string]$proc.CommandLine
        if ([string]::IsNullOrWhiteSpace($exe) -or [string]::IsNullOrWhiteSpace($line)) { continue }
        try { $exe = [System.IO.Path]::GetFullPath($exe) } catch { continue }
        if ($exe -ine $portableExe) { continue }
        if ($line -notmatch '(?i)/skipupdate' -or $line -notmatch '(?i)/portable') { continue }
        if ($line.IndexOf($cfg, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) { continue }
        return [int]$proc.ProcessId
    }
    return 0
}

function Stop-OrphanPortableTesters([string]$KeepConfigPath = '') {
    $portableExe = [System.IO.Path]::GetFullPath($MT5)
    $keep = ''
    if (-not [string]::IsNullOrWhiteSpace($KeepConfigPath)) {
        $keep = [System.IO.Path]::GetFullPath($KeepConfigPath)
    }
    foreach ($proc in @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue)) {
        $exe = [string]$proc.ExecutablePath
        $line = [string]$proc.CommandLine
        if ([string]::IsNullOrWhiteSpace($exe)) { continue }
        try { $exe = [System.IO.Path]::GetFullPath($exe) } catch { continue }
        if ($exe -ine $portableExe) { continue }
        if ($line -notmatch '(?i)/portable') { continue }
        if ($keep -and $line.IndexOf($keep, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { continue }
        Write-Status "Closing orphan portable tester PID $($proc.ProcessId)" "WARN"
        Stop-Process -Id ([int]$proc.ProcessId) -Force -ErrorAction SilentlyContinue
    }
}

function Wait-PortableLiveUpdate {
    $portable = [System.IO.Path]::GetFullPath($MT5InstallRoot).TrimEnd([char[]]'\/')
    $deadline = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $deadline) {
        $live = @(
            Get-CimInstance Win32_Process -Filter "Name='terminal64.exe' OR Name='metaeditor64.exe'" -ErrorAction SilentlyContinue |
                Where-Object {
                    $exe = [string]$_.ExecutablePath
                    $line = [string]$_.CommandLine
                    $exe -match '(?i)[\\/]liveupdate[\\/](terminal64|metaeditor64)\.exe$' -and
                    $line -match '(?i)/update(\s|$)' -and
                    $line.IndexOf($portable, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                }
        )
        if ($live.Count -eq 0) { return }
        Write-Status "Waiting for MetaQuotes liveupdate of portable isolate..." "WARN"
        Start-Sleep -Seconds 5
    }
    throw "Portable liveupdate still running after 180s. Retry Model-0 after it exits; do not kill Owner Program Files GUI."
}

function Get-RelativePathUnderRoot($Path, $Root) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $prefix = "$fullRoot\"
    if (-not $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $null
    }
    return $fullPath.Substring($prefix.Length)
}

function Assert-NonArchiveInclude($Path) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $forbiddenRoots = @(
        (Join-Path $AdvisorsRoot "00. Old File"),
        (Join-Path $AlphaRoot "archive")
    )
    foreach ($root in $forbiddenRoots) {
        if ($null -ne (Get-RelativePathUnderRoot $fullPath $root)) {
            throw "Archived include dependency is forbidden in active evidence: $fullPath"
        }
    }
}

function Resolve-IncludeDependency($Reference, $CurrentFile, $IncludeKind) {
    $candidate = switch ($IncludeKind) {
        "terminal" { Join-Path (Join-Path $MT5Mql5Root "Include") $Reference }
        "local" { Join-Path (Split-Path -Parent $CurrentFile) $Reference }
        default { throw "Unsupported include delimiter kind '$IncludeKind' for '$Reference'." }
    }
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
        Assert-NonArchiveInclude $resolved
        return $resolved
    }
    return $null
}

function Get-IncludeDependencyClosure($MainFile) {
    $pending = New-Object 'System.Collections.Generic.Queue[string]'
    $visited = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    $includes = New-Object System.Collections.Generic.List[string]
    $pending.Enqueue((Resolve-Path -LiteralPath $MainFile).Path)

    while ($pending.Count -gt 0) {
        $current = $pending.Dequeue()
        if (-not $visited.Add($current)) { continue }
        foreach ($line in (Get-Content -LiteralPath $current)) {
            $match = [regex]::Match($line, '^\s*#include\s*(?:<(?<terminal>[^>]+)>|"(?<local>[^"]+)")')
            if (-not $match.Success) { continue }
            $includeKind = if ($match.Groups['terminal'].Success) { 'terminal' } else { 'local' }
            $reference = $match.Groups[$includeKind].Value.Trim()
            $resolved = Resolve-IncludeDependency $reference $current $includeKind
            if ([string]::IsNullOrWhiteSpace($resolved)) {
                throw "Include dependency cannot be resolved for snapshot: '$reference' ($includeKind) referenced by '$current'."
            }
            if (-not $includes.Contains($resolved)) {
                $includes.Add($resolved)
            }
            if (-not $visited.Contains($resolved)) {
                $pending.Enqueue($resolved)
            }
        }
    }
    return @($includes)
}

function Get-MqlInputTypeMap([string]$MainFile) {
    if (-not (Test-Path -LiteralPath $MainFile -PathType Leaf)) {
        throw "MQL input preflight source is missing: $MainFile"
    }
    $typeMap = [ordered]@{}
    $files = @((Resolve-Path -LiteralPath $MainFile).Path) + @(Get-IncludeDependencyClosure $MainFile)
    $declaration = '(?m)^\s*(?:sinput|input)\s+(?!group\b)(?<type>[A-Za-z_][A-Za-z0-9_]*)\s+(?<name>[A-Za-z_][A-Za-z0-9_]*)\b'
    foreach ($file in $files) {
        $source = Get-Content -LiteralPath $file -Raw
        foreach ($match in [regex]::Matches($source, $declaration)) {
            $name = $match.Groups['name'].Value
            $type = $match.Groups['type'].Value.ToLowerInvariant()
            if ($typeMap.Contains($name)) {
                throw "MQL tester input '$name' is declared more than once across the include closure."
            }
            $typeMap[$name] = $type
        }
    }
    return $typeMap
}

function ConvertTo-TesterInputLines([string]$MainFile, [string]$OverrideText) {
    $overrideMap = ConvertTo-NormalizedOverrideMap $OverrideText
    if ($overrideMap.Count -eq 0) { return @() }
    $typeMap = Get-MqlInputTypeMap $MainFile
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($name in @($overrideMap.Keys | Sort-Object)) {
        if (-not $typeMap.Contains($name)) {
            throw "Tester override '$name' does not match a declared input/sinput in the canonical MQL include closure."
        }
        $value = [string]$overrideMap[$name]
        if ([string]$typeMap[$name] -ceq 'string') {
            $lines.Add("$name=$value")
        } else {
            $lines.Add("$name=$value||$value||0||$value||N")
        }
    }
    return @($lines)
}

function New-RunSnapshot($RunDir, $MainFile, $Ex5File, $ConfigPath) {
    foreach ($required in @($MainFile, $Ex5File, $ConfigPath)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Run snapshot input is missing: $required"
        }
    }

    $snapshotRoot = Join-Path $RunDir "snapshot"
    $sourceDir = Join-Path $snapshotRoot "source"
    $includesDir = Join-Path $snapshotRoot "includes"
    $buildDir = Join-Path $snapshotRoot "build"
    $configDir = Join-Path $snapshotRoot "config"
    @($sourceDir, $includesDir, $buildDir, $configDir) | ForEach-Object {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }

    $sourceSnapshot = Join-Path $sourceDir (Split-Path -Leaf $MainFile)
    $ex5Snapshot = Join-Path $buildDir (Split-Path -Leaf $Ex5File)
    $configSnapshot = Join-Path $configDir "config.ini"
    Copy-Item -LiteralPath $MainFile -Destination $sourceSnapshot -Force
    Copy-Item -LiteralPath $Ex5File -Destination $ex5Snapshot -Force
    Copy-Item -LiteralPath $ConfigPath -Destination $configSnapshot -Force

    $eaRoot = Split-Path -Parent $MainFile
    $terminalIncludeRoot = Join-Path $MT5Mql5Root "Include"
    $includeArtifacts = New-Object System.Collections.Generic.List[object]
    foreach ($include in (Get-IncludeDependencyClosure $MainFile)) {
        $relative = Get-RelativePathUnderRoot $include $eaRoot
        $namespace = "ea"
        if ($null -eq $relative) {
            $relative = Get-RelativePathUnderRoot $include $terminalIncludeRoot
            $namespace = "terminal"
        }
        if ($null -eq $relative) {
            $namespace = "external"
            $relative = "{0}_{1}" -f ((Get-Sha256Required $include "Include").Substring(0, 12)), (Split-Path -Leaf $include)
        }
        $destination = Join-Path (Join-Path $includesDir $namespace) $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $include -Destination $destination -Force
        $includeArtifacts.Add([ordered]@{
            original_path = $include
            snapshot_path = $destination
            sha256 = Get-Sha256Required $destination "Include snapshot"
        })
    }

    return [pscustomobject]@{
        Root = $snapshotRoot
        SourcePath = $sourceSnapshot
        Ex5Path = $ex5Snapshot
        ConfigPath = $configSnapshot
        Includes = $includeArtifacts.ToArray()
    }
}

function Get-SnapshotIncludeSetSha256($Snapshot) {
    # Sort final relative-path records (not raw snapshot_path) so Write-RunManifest
    # and Complete-RunManifest stay identical after JSON round-trip.
    $records = @(
        @($Snapshot.Includes) | ForEach-Object {
            $path = [string]$_.snapshot_path
            $relative = Get-RelativePathUnderRoot $path ([string]$Snapshot.Root)
            if ([string]::IsNullOrWhiteSpace($relative)) {
                throw "Include snapshot escapes snapshot root: $path"
            }
            $actual = Get-Sha256Required $path "Include snapshot"
            if ([string]$_.sha256 -ine $actual) {
                throw "Include snapshot hash changed: $path"
            }
            "$($relative.Replace('\', '/'))`t$actual"
        } | Sort-Object
    )
    return Get-TextSha256 ([string]::Join("`n", $records))
}

function Get-EAs {
    # Only canonical packages under the active shelf are discoverable. Run
    # snapshots and archive trees may contain .mq5 files but are never valid
    # compile/backtest entrypoints.
    $activeRoot = Join-Path $AdvisorsRoot "03. EA Developer"
    if (-not (Test-Path -LiteralPath $activeRoot -PathType Container)) { return @() }

    $eaDirs = New-Object System.Collections.Generic.List[object]
    foreach ($directory in @(Get-ChildItem -LiteralPath $activeRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'EA_*' } |
        Sort-Object Name)) {
        try {
            [void](Resolve-EaSourceContract -RepoRoot $AdvisorsRoot -EaName $directory.Name)
            $eaDirs.Add($directory)
        } catch {
            # Research-only packages (no canonical .mq5, but a research/ dir)
            # are a normal terminal state, not an error. Warn only when a
            # package looks like it should compile but fails the contract.
            $hasSource = Test-Path -LiteralPath (Join-Path $directory.FullName ("{0}.mq5" -f $directory.Name)) -PathType Leaf
            $hasResearch = Test-Path -LiteralPath (Join-Path $directory.FullName "research") -PathType Container
            if ($hasSource -or -not $hasResearch) {
                Write-Warning "Ignoring invalid active EA package '$($directory.Name)': $($_.Exception.Message)"
            }
        }
    }
    return @($eaDirs.ToArray())
}

function Find-MainFile($EAName) {
    return (Resolve-EaSourceContract -RepoRoot $AdvisorsRoot -EaName $EAName).AbsoluteSource
}


function Get-DirectoryTreeSha256($Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Directory evidence is missing and cannot be hashed: $Path"
    }
    $root = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $records = @(
        Get-ChildItem -LiteralPath $root -Recurse -File | Sort-Object FullName | ForEach-Object {
            $relative = $_.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
            "$relative`t$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)"
        }
    )
    return Get-TextSha256 ([string]::Join("`n", $records))
}

function Assert-ContractReceipt($ReceiptPath, $ExpectedReceiptSha256, $Binding) {
    if ([string]::IsNullOrWhiteSpace($ReceiptPath)) {
        throw "ContractReceipt is required for backtest evidence."
    }
    $resolvedReceipt = [System.IO.Path]::GetFullPath($ReceiptPath)
    $actualReceiptHash = Get-Sha256Required $resolvedReceipt "Contract receipt"
    if ($ExpectedReceiptSha256 -notmatch '^[A-Fa-f0-9]{64}$' -or $actualReceiptHash -ine $ExpectedReceiptSha256) {
        throw "Contract receipt SHA256 mismatch: expected '$ExpectedReceiptSha256', got '$actualReceiptHash'."
    }
    try {
        $receipt = Get-Content -LiteralPath $resolvedReceipt -Raw | ConvertFrom-Json
    } catch {
        throw "Contract receipt JSON is malformed: $($_.Exception.Message)"
    }
    $receiptSchema = [string]$receipt.schema_version
    if ($receiptSchema -notin @('alphafactory_execution_receipt.v1', 'sonic_execution_receipt.v1')) {
        throw "Contract receipt schema_version must be 'alphafactory_execution_receipt.v1'."
    }

    $authorityProperties = @($receipt.PSObject.Properties | Where-Object { $_.Name -ieq 'authority' })
    $exactAuthorityProperties = @($receipt.PSObject.Properties | Where-Object { $_.Name -ceq 'authority' })
    if ($authorityProperties.Count -gt 0 -and $exactAuthorityProperties.Count -ne 1) {
        throw "Contract receipt authority field must be exactly case-sensitive 'authority'."
    }
    $receiptAuthority = if ($exactAuthorityProperties.Count -eq 1) { [string]$exactAuthorityProperties[0].Value } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($receiptAuthority) -and
        $receiptAuthority -notin @(
            'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
            'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
        )) {
        throw "Unsupported contract receipt authority '$receiptAuthority'."
    }
    if ($receiptAuthority -in @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )) {
        $dataQualityContract = $receipt.binding.data_quality_contract
        $expectedModel = if ($receiptAuthority -ceq 'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE') { 0 } else { 4 }
        if ($receiptSchema -cne 'alphafactory_execution_receipt.v1' -or
            [string]$receipt.binding.run_role -cne 'control' -or
            [int]$receipt.binding.model -ne $expectedModel -or
            [string]$receipt.binding.telemetry_profile -cne 'none' -or
            [string]$receipt.binding.telemetry_tier -cne 'off' -or
            @($receipt.binding.required_sidecars).Count -ne 0) {
            throw "Data-acquisition receipt authority '$receiptAuthority' requires AlphaFactory control/Model$expectedModel/telemetry-none/off with no sidecars."
        }
        if ($null -eq $dataQualityContract -or
            [string]$dataQualityContract.history_quality.operator -cne 'gt' -or
            [double]$dataQualityContract.history_quality.value -lt 97.0 -or
            [string]$dataQualityContract.coverage_mode -cne 'all_available_asof' -or
            [string]$dataQualityContract.requested_from -cne '1970.01.01' -or
            $dataQualityContract.require_tester_journal_bounds -ne $true) {
            throw "Data-acquisition receipt lacks the required all-available History Quality >97 contract."
        }
    }

    $evidenceByLabel = @{}
    foreach ($item in @($receipt.evidence)) {
        $label = [string]$item.label
        if ([string]::IsNullOrWhiteSpace($label) -or $evidenceByLabel.ContainsKey($label)) {
            throw "Contract receipt has a missing or duplicate evidence label '$label'."
        }
        $path = [System.IO.Path]::GetFullPath([string]$item.path)
        $expected = [string]$item.sha256
        $actual = if ([string]$item.kind -ceq 'directory') {
            Get-DirectoryTreeSha256 $path
        } elseif ([string]$item.kind -ceq 'file') {
            Get-Sha256Required $path "Receipt evidence '$label'"
        } else {
            throw "Contract receipt evidence '$label' has unsupported kind '$($item.kind)'."
        }
        if ($expected -notmatch '^[A-Fa-f0-9]{64}$' -or $actual -ine $expected) {
            throw "Contract receipt evidence '$label' changed: expected '$expected', got '$actual'."
        }
        $evidenceByLabel[$label] = $item
    }
    $requiredReceiptLabels = @('task_packet', 'source', 'prereg', 'cost_source_manifest')
    if ($receiptSchema -ceq 'alphafactory_execution_receipt.v1') {
        $requiredReceiptLabels += 'candidate_registry'
        if ([string]$receipt.binding.telemetry_profile -cne 'none') {
            $requiredReceiptLabels += 'ea_capability_contract'
        }
    }
    if ([string]$receipt.binding.run_role -ceq 'challenger') {
        $requiredReceiptLabels += @('matched_control_manifest', 'matched_control_report')
    } elseif ([string]$receipt.binding.run_role -cne 'control') {
        throw "Contract receipt run_role must be 'control' or 'challenger'."
    }
    foreach ($requiredLabel in $requiredReceiptLabels) {
        if (-not $evidenceByLabel.ContainsKey($requiredLabel)) {
            throw "Contract receipt is missing required evidence '$requiredLabel'."
        }
    }
    $taskPacketPath = [System.IO.Path]::GetFullPath([string]$evidenceByLabel['task_packet'].path)
    try {
        $receiptTaskPacket = Get-Content -LiteralPath $taskPacketPath -Raw | ConvertFrom-Json
    } catch {
        throw "Contract receipt task_packet evidence is malformed JSON: $($_.Exception.Message)"
    }
    $packetAuthorityProperties = @($receiptTaskPacket.PSObject.Properties | Where-Object { $_.Name -ieq 'authority' })
    $packetExactAuthorityProperties = @($receiptTaskPacket.PSObject.Properties | Where-Object { $_.Name -ceq 'authority' })
    if ($packetAuthorityProperties.Count -gt 0 -and $packetExactAuthorityProperties.Count -ne 1) {
        throw "Task packet authority field must be exactly case-sensitive 'authority'."
    }
    $taskPacketAuthority = if ($packetExactAuthorityProperties.Count -eq 1) { [string]$packetExactAuthorityProperties[0].Value } else { '' }
    if ($taskPacketAuthority -cne $receiptAuthority) {
        throw "Contract receipt authority does not match its hash-bound task packet."
    }
    $includeEvidence = @($receipt.evidence | Where-Object { [string]$_.label -like 'include_*' })
    $includeRecords = @(
        $includeEvidence | Sort-Object path | ForEach-Object {
            $path = [System.IO.Path]::GetFullPath([string]$_.path).ToLowerInvariant()
            $hash = ([string]$_.sha256).ToUpperInvariant()
            "$path`t$hash"
        }
    )
    $includeClosureHash = Get-TextSha256 ([string]::Join("`n", $includeRecords))
    if ($includeClosureHash -ine [string]$receipt.binding.include_closure_sha256) {
        throw "Contract receipt include closure does not match its bound hash."
    }

    $receiptBinding = $receipt.binding
    $scalarFields = @('hypothesis_id', 'run_role', 'ea_name', 'symbol', 'period', 'from', 'to', 'overrides', 'telemetry_tier', 'spread')
    if ($receiptSchema -ceq 'alphafactory_execution_receipt.v1') {
        $scalarFields += 'telemetry_profile'
    }
    foreach ($field in $scalarFields) {
        if ([string]$receiptBinding.$field -cne [string]$Binding.$field) {
            throw "Contract receipt binding '$field' does not match the alpha invocation."
        }
    }
    foreach ($field in @('model', 'execution_mode', 'fixed_delay_ms', 'deposit', 'leverage')) {
        if ([int64]$receiptBinding.$field -ne [int64]$Binding.$field) {
            throw "Contract receipt binding '$field' does not match the alpha invocation."
        }
    }
    $geometry = $receiptBinding.symbol_geometry
    if ($null -eq $geometry -or
        $null -eq $geometry.digits -or
        $null -eq $geometry.point -or
        $null -eq $geometry.pip_size) {
        throw "Contract receipt binding 'symbol_geometry' must contain digits, point, and pip_size."
    }
    $digits = 0L
    $point = 0.0
    $pipSize = 0.0
    if (-not [int64]::TryParse([string]$geometry.digits, [ref]$digits) -or $digits -lt 0 -or $digits -gt 12 -or
        -not [double]::TryParse([string]$geometry.point, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$point) -or $point -le 0 -or
        -not [double]::TryParse([string]$geometry.pip_size, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$pipSize) -or $pipSize -le 0) {
        throw "Contract receipt binding 'symbol_geometry' contains invalid numeric geometry."
    }
    $receiptSidecars = @($receiptBinding.required_sidecars | ForEach-Object { [string]$_ } | Sort-Object)
    $bindingSidecars = @($Binding.required_sidecars | ForEach-Object { [string]$_ } | Sort-Object)
    if ([string]::Join("`n", $receiptSidecars) -cne [string]::Join("`n", $bindingSidecars)) {
        throw "Contract receipt binding 'required_sidecars' does not match the alpha invocation."
    }
    $dataQualityContract = Resolve-DataQualityContract $receipt $Binding

    $sourceForNogit = ""
    $sourceEvidenceForNogit = @($receipt.evidence | Where-Object { [string]$_.label -ceq 'source' })
    if ($sourceEvidenceForNogit.Count -eq 1) {
        $sourceForNogit = [string]$sourceEvidenceForNogit[0].path
    }
    $git = Get-GitSnapshot -ActiveSource $sourceForNogit
    if ([string]$receipt.git_commit -cne $git.Commit -or [string]$receipt.git_status_sha256 -ine $git.StatusSha256) {
        throw ("Contract receipt git identity changed before compile/backtest. receipt_commit='{0}' live_commit='{1}' receipt_status='{2}' live_status='{3}' nogit={4}" -f [string]$receipt.git_commit, [string]$git.Commit, [string]$receipt.git_status_sha256, [string]$git.StatusSha256, [string]$git.NoGit)
    }
    return [pscustomobject]@{
        Receipt = $receipt
        ReceiptPath = $resolvedReceipt
        ReceiptSha256 = $actualReceiptHash
        Git = $git
        DataQualityContract = $dataQualityContract
    }
}

function Assert-ReceiptSourceMatchesMain($ReceiptCheck, [string]$MainFile) {
    $sourceEvidence = @($ReceiptCheck.Receipt.evidence | Where-Object { [string]$_.label -ceq 'source' })
    if ($sourceEvidence.Count -ne 1) {
        throw "Contract receipt must contain exactly one source evidence item."
    }
    $receiptSource = [System.IO.Path]::GetFullPath([string]$sourceEvidence[0].path)
    $resolvedMain = [System.IO.Path]::GetFullPath($MainFile)
    if (-not [string]::Equals($receiptSource, $resolvedMain, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Contract receipt source '$receiptSource' does not match resolved EA main '$resolvedMain'."
    }
}

function Get-ObjectPropertyValue($Object, [string[]]$Names, [switch]$Required, [string]$Label = "") {
    if ($null -eq $Object) {
        if ($Required) { throw "$Label is required." }
        return $null
    }
    foreach ($name in $Names) {
        $prop = $Object.PSObject.Properties[$name]
        if ($null -ne $prop) { return $prop.Value }
    }
    if ($Required) {
        $fieldLabel = if ([string]::IsNullOrWhiteSpace($Label)) { [string]::Join("/", $Names) } else { $Label }
        throw "$fieldLabel is required."
    }
    return $null
}

function ConvertTo-ResearchDate([string]$Value, [string]$Label) {
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $styles = [System.Globalization.DateTimeStyles]::None
    $parsed = [datetime]::MinValue
    if (-not [datetime]::TryParseExact($Value, 'yyyy.MM.dd', $culture, $styles, [ref]$parsed)) {
        throw "$Label must use a real yyyy.MM.dd date."
    }
    return $parsed.Date
}

function ConvertTo-FiniteInvariantDouble($Value, [string]$Label) {
    $text = ([string]$Value).Trim()
    if ($text.EndsWith('%')) { $text = $text.Substring(0, $text.Length - 1).Trim() }
    $parsed = 0.0
    if (-not [double]::TryParse($text, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed) -or
        [double]::IsNaN($parsed) -or [double]::IsInfinity($parsed)) {
        throw "$Label must be a finite invariant-culture number."
    }
    return $parsed
}

function Resolve-DataQualityContract($Receipt, $Binding) {
    $bindingObject = $Receipt.binding
    $contractCandidates = @(
        if ($null -ne $bindingObject) {
            $bindingObject.PSObject.Properties | Where-Object { $_.Name -ieq 'data_quality_contract' }
        }
    )
    $contractExact = @($contractCandidates | Where-Object { $_.Name -ceq 'data_quality_contract' })
    if ($contractCandidates.Count -eq 0) {
        return $null
    }
    if ($contractCandidates.Count -ne 1 -or $contractExact.Count -ne 1 -or $null -eq $contractExact[0].Value) {
        throw "Receipt binding optional field name must be exactly case-sensitive 'data_quality_contract'."
    }
    $contractProperty = $contractExact[0]
    $contract = $contractProperty.Value
    $contractKeys = @($contract.PSObject.Properties.Name | Sort-Object)
    $expectedKeys = @('availability_asof_utc', 'coverage_mode', 'history_quality', 'requested_from', 'requested_to', 'require_tester_journal_bounds')
    $expectedKeys = @($expectedKeys | Sort-Object)
    if ([string]::Join("`n", $contractKeys) -cne [string]::Join("`n", $expectedKeys)) {
        throw "data_quality_contract must contain exactly: $([string]::Join(', ', $expectedKeys))."
    }
    $symbol = [string]$Binding.symbol
    if ($symbol -notmatch '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$') {
        throw "alpha invocation symbol contains unsupported characters for data_quality_contract."
    }

    $requestedFrom = [string](Get-ObjectPropertyValue $contract @('requested_from') -Required -Label "data_quality_contract.requested_from")
    $requestedTo = [string](Get-ObjectPropertyValue $contract @('requested_to') -Required -Label "data_quality_contract.requested_to")
    if ($requestedFrom -cne [string]$Binding.from -or $requestedTo -cne [string]$Binding.to) {
        throw "data_quality_contract requested_from/requested_to must match the alpha invocation range."
    }
    $fromDate = ConvertTo-ResearchDate $requestedFrom "data_quality_contract.requested_from"
    $toDate = ConvertTo-ResearchDate $requestedTo "data_quality_contract.requested_to"
    if ($fromDate -gt $toDate) {
        throw "data_quality_contract requested_from must not be later than requested_to."
    }

    $hq = Get-ObjectPropertyValue $contract @('history_quality') -Required -Label "data_quality_contract.history_quality"
    $hqKeys = @($hq.PSObject.Properties.Name | Sort-Object)
    $expectedHqKeys = @('operator', 'value')
    $expectedHqKeys = @($expectedHqKeys | Sort-Object)
    if ([string]::Join("`n", $hqKeys) -cne [string]::Join("`n", $expectedHqKeys)) {
        throw "data_quality_contract.history_quality must contain exactly operator and value."
    }
    if ([string]$hq.operator -cne 'gt') {
        throw "data_quality_contract.history_quality.operator must be 'gt'."
    }
    $threshold = ConvertTo-FiniteInvariantDouble $hq.value "data_quality_contract.history_quality.value"
    if ($threshold -lt 97 -or $threshold -ge 100) {
        throw "data_quality_contract.history_quality.value must be >= 97 and < 100."
    }
    if ([string]$contract.coverage_mode -cne 'all_available_asof') {
        throw "data_quality_contract.coverage_mode must be 'all_available_asof'."
    }
    $asofText = [string]$contract.availability_asof_utc
    $asof = [datetimeoffset]::MinValue
    if ($asofText -notmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$' -or
        -not [datetimeoffset]::TryParse($asofText, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::RoundtripKind, [ref]$asof) -or
        $asof.Offset -ne [timespan]::Zero) {
        throw "data_quality_contract.availability_asof_utc must be a valid Z timestamp."
    }
    if ($asof.UtcDateTime -gt (Get-Date).ToUniversalTime()) {
        throw "data_quality_contract.availability_asof_utc must not be in the future at preflight."
    }
    if ($requestedFrom -cne '1970.01.01') {
        throw "data_quality_contract all_available_asof requested_from must equal the frozen sentinel '1970.01.01'."
    }
    $asofDate = $asof.UtcDateTime.ToString('yyyy.MM.dd')
    if ($requestedTo -cne $asofDate) {
        throw "data_quality_contract.requested_to must equal the UTC calendar date of availability_asof_utc '$asofDate'."
    }
    $journalBounds = $contract.require_tester_journal_bounds
    if ($journalBounds -isnot [bool] -or (-not [bool]$journalBounds)) {
        throw "data_quality_contract.require_tester_journal_bounds must be true."
    }

    return [pscustomobject]@{
        schema_version = "alphafactory_data_quality_contract.v1"
        symbol = $symbol
        requested_from = $requestedFrom
        requested_to = $requestedTo
        history_quality_threshold = $threshold
        coverage_mode = [string]$contract.coverage_mode
        availability_asof_utc = $asof.UtcDateTime.ToString('o')
        require_tester_journal_bounds = $true
        max_journal_delta_bytes = 1048576L
    }
}

function Get-Mt5JournalLogFiles([string[]]$Roots) {
    $resolvedRoots = @(
        $Roots |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) -and (Test-Path -LiteralPath $_ -PathType Container) } |
            ForEach-Object { [System.IO.Path]::GetFullPath([string]$_).TrimEnd('\', '/') } |
            Sort-Object -Unique
    )
    $filesByPath = @{}
    foreach ($root in $resolvedRoots) {
        $basesChild = Join-Path $root 'bases'
        $cacheChild = Join-Path $root 'cache'
        if ((Test-Path -LiteralPath $basesChild -PathType Container) -or (Test-Path -LiteralPath $cacheChild -PathType Container)) {
            throw "Journal root must be a logs directory, not a Tester/data tree: $root"
        }
        Get-ChildItem -LiteralPath $root -Recurse -Filter "*.log" -File -ErrorAction SilentlyContinue |
            ForEach-Object {
                $full = [System.IO.Path]::GetFullPath($_.FullName)
                if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
                    $filesByPath[$full.ToLowerInvariant()] = $_
                }
            }
    }
    return @($filesByPath.Values | Sort-Object FullName)
}

function New-Mt5JournalLogSnapshot([string[]]$Roots) {
    return @(
        Get-Mt5JournalLogFiles $Roots | ForEach-Object {
            [pscustomobject]@{
                path = [System.IO.Path]::GetFullPath($_.FullName)
                length = [int64]$_.Length
            }
        }
    )
}

function ConvertFrom-Mt5LogBytes([byte[]]$Bytes) {
    if ($null -eq $Bytes -or $Bytes.Length -eq 0) { return "" }
    if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 0xFF -and $Bytes[1] -eq 0xFE) {
        return [System.Text.Encoding]::Unicode.GetString($Bytes, 2, $Bytes.Length - 2)
    }
    if ($Bytes.Length -ge 3 -and $Bytes[0] -eq 0xEF -and $Bytes[1] -eq 0xBB -and $Bytes[2] -eq 0xBF) {
        return [System.Text.UTF8Encoding]::new($false, $false).GetString($Bytes, 3, $Bytes.Length - 3)
    }
    $sample = [Math]::Min($Bytes.Length, 200)
    $oddNulls = 0
    for ($i = 1; $i -lt $sample; $i += 2) {
        if ($Bytes[$i] -eq 0) { $oddNulls++ }
    }
    if ($sample -ge 20 -and $oddNulls -ge [Math]::Max(5, [int]($sample / 6))) {
        return [System.Text.Encoding]::Unicode.GetString($Bytes)
    }
    return [System.Text.UTF8Encoding]::new($false, $false).GetString($Bytes)
}

function Export-Mt5JournalLogDelta($Snapshot, [string[]]$Roots, [string]$OutputPath, [int64]$MaxBytes = 1048576) {
    if ($MaxBytes -le 0) { throw "MT5 journal delta MaxBytes must be positive." }
    $offsetByPath = @{}
    foreach ($entry in @($Snapshot)) {
        $path = [System.IO.Path]::GetFullPath([string]$entry.path)
        $offsetByPath[$path.ToLowerInvariant()] = [int64]$entry.length
    }
    $currentFiles = @(Get-Mt5JournalLogFiles $Roots)
    $fileSlices = New-Object System.Collections.Generic.List[object]
    $totalAvailable = 0L
    foreach ($file in $currentFiles) {
        $full = [System.IO.Path]::GetFullPath($file.FullName)
        $key = $full.ToLowerInvariant()
        $offset = if ($offsetByPath.ContainsKey($key)) { [int64]$offsetByPath[$key] } else { 0L }
        if ([int64]$file.Length -lt $offset) { $offset = 0L }
        $available = [int64]$file.Length - $offset
        if ($available -le 0) { continue }
        $fileSlices.Add([pscustomobject]@{ path = $full; offset = $offset; available = $available })
        $totalAvailable += $available
    }
    $remaining = [int64]$MaxBytes
    $segments = New-Object System.Collections.Generic.List[string]
    $filesRead = 0
    $bytesRead = 0L
    foreach ($slice in $fileSlices) {
        if ($remaining -le 0) { break }
        $take = [int64][Math]::Min([int64]$slice.available, $remaining)
        $buffer = New-Object byte[] $take
        $stream = [System.IO.File]::Open([string]$slice.path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try {
            [void]$stream.Seek([int64]$slice.offset, [System.IO.SeekOrigin]::Begin)
            $read = 0
            while ($read -lt $take) {
                $chunk = $stream.Read($buffer, $read, [int]($take - $read))
                if ($chunk -le 0) { break }
                $read += $chunk
            }
        } finally {
            $stream.Dispose()
        }
        if ($read -gt 0) {
            if ($read -ne $buffer.Length) {
                $actual = New-Object byte[] $read
                [Array]::Copy($buffer, $actual, $read)
                $buffer = $actual
            }
            $segments.Add((ConvertFrom-Mt5LogBytes $buffer))
            $filesRead++
            $bytesRead += $read
            $remaining -= $read
        }
    }
    $outDir = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($OutputPath, [string]::Join("`n", @($segments)), [System.Text.UTF8Encoding]::new($false))
    return [pscustomobject]@{
        path = $OutputPath
        sha256 = Get-Sha256Required $OutputPath "MT5 journal delta"
        bytes_read = $bytesRead
        files_read = $filesRead
        truncated = ($totalAvailable -gt $MaxBytes -or $bytesRead -lt [Math]::Min($totalAvailable, $MaxBytes))
    }
}

function Get-DataQualityHistoryRange([string]$JournalText, [string]$Symbol) {
    $symbolPattern = [regex]::Escape($Symbol)
    $exactPattern = '(?im)(?<![A-Za-z0-9._+-])' + $symbolPattern + ':\s+history synchronized from (?<from>\d{4}\.\d{2}\.\d{2}) to (?<to>\d{4}\.\d{2}\.\d{2})'
    $exactMatches = @([regex]::Matches($JournalText, $exactPattern))
    $ranges = @(
        $exactMatches | ForEach-Object {
            "{0}|{1}" -f $_.Groups['from'].Value, $_.Groups['to'].Value
        } | Sort-Object -Unique
    )
    if ($ranges.Count -eq 0) {
        throw "MT5 journal delta has no exact-symbol history synchronization line for '$Symbol'."
    }
    if ($ranges.Count -gt 1) {
        throw "MT5 journal delta has ambiguous history synchronization ranges for '$Symbol': $([string]::Join(', ', $ranges))"
    }
    $parts = $ranges[0].Split('|', 2)
    return [pscustomobject]@{
        actual_from = $parts[0]
        actual_to = $parts[1]
        exact_match_count = $exactMatches.Count
        distinct_range_count = $ranges.Count
    }
}

function Get-DataQualitySeriesProof([string]$JournalText, [string]$Symbol, [string]$ActualFrom) {
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
        throw "MT5 journal delta requires one distinct D0 series proof for '$Symbol'; found $($records.Count)."
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
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: D0 series proof has unsynchronized, empty, failed-copy, or invalid first-date fields."
    }

    $actualFromDate = ConvertTo-ResearchDate $ActualFrom "journal actual_from"
    $m5FirstDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m5_first_epoch).UtcDateTime.Date
    $m5TerminalDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m5_terminal_first_epoch).UtcDateTime.Date
    $m1ServerDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m1_server_first_epoch).UtcDateTime.Date
    $m1TerminalDate = [datetimeoffset]::FromUnixTimeSeconds($proof.m1_terminal_first_epoch).UtcDateTime.Date
    $copyFirstDate = [datetimeoffset]::FromUnixTimeSeconds($proof.copytime_first_epoch).UtcDateTime.Date
    if ($actualFromDate -ne $m5FirstDate -or $m5FirstDate -ne $m5TerminalDate -or $m5FirstDate -ne $copyFirstDate) {
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: journal, M5 series, terminal series, and CopyTime first dates disagree."
    }
    if ($m1TerminalDate -ne $m1ServerDate -or $m1ServerDate -gt $m5FirstDate) {
        throw "INVALID_TRUNCATED_TERMINAL_CACHE: terminal M1 first date does not match the server or begins after M5 history."
    }

    $reportingFloor = [datetime]::new(2018, 1, 1)
    $coverageClass = 'FULL_2018_PLUS'
    if ($actualFromDate -gt $reportingFloor) {
        if ($m1ServerDate -le $reportingFloor -or ($m5FirstDate - $m1ServerDate).TotalDays -gt 7) {
            throw "INVALID_TRUNCATED_TERMINAL_CACHE: post-2018 M5 start is not justified by the MT5 server first date."
        }
        $coverageClass = 'BROKER_LIMITED_START'
    }
    return [pscustomobject]@{
        coverage_class = $coverageClass
        series_proof = [pscustomobject]$proof
    }
}

function Assert-DataQualityRunEvidence($Manifest) {
    $contract = $Manifest.data_quality_contract
    if ($null -eq $contract) { return $null }
    if ([string]$contract.requested_from -cne [string]$Manifest.from -or [string]$contract.requested_to -cne [string]$Manifest.to) {
        throw "data_quality_contract requested_from/requested_to must match run manifest from/to."
    }
    $journal = $Manifest.data_quality_journal_delta
    if ($null -eq $journal -or [string]::IsNullOrWhiteSpace([string]$journal.path)) {
        throw "data_quality_contract requires a run-local MT5 journal delta."
    }
    if ([string]$journal.path -cne 'logs/tester_journal_delta.log') {
        throw "MT5 journal delta path must be the fixed run-local path 'logs/tester_journal_delta.log'."
    }
    if ($journal.truncated -isnot [bool] -or [bool]$journal.truncated) {
        throw "MT5 journal delta must be present and complete; truncated or untyped evidence is invalid."
    }
    if ([int64]$journal.files_read -le 0 -or [int64]$journal.bytes_read -le 0) {
        throw "MT5 journal delta must bind positive files_read and bytes_read evidence."
    }
    $runRoot = [System.IO.Path]::GetFullPath([string]$Manifest.local_run_dir).TrimEnd('\', '/')
    $journalPath = [System.IO.Path]::GetFullPath((Join-Path $runRoot ([string]$journal.path)))
    $runPrefix = "$runRoot\"
    if (-not $journalPath.StartsWith($runPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "MT5 journal delta resolves outside the run-local root."
    }
    if (-not (Test-Path -LiteralPath $journalPath -PathType Leaf)) {
        throw "MT5 journal delta is missing: $journalPath"
    }
    $journalSha = Get-Sha256Required $journalPath "MT5 journal delta"
    if ([string]$journal.sha256 -ine $journalSha) {
        throw "MT5 journal delta SHA256 mismatch."
    }
    $journalText = Get-Content -LiteralPath $journalPath -Raw
    $range = Get-DataQualityHistoryRange $journalText ([string]$contract.symbol)
    $actualFrom = ConvertTo-ResearchDate ([string]$range.actual_from) "journal actual_from"
    $actualTo = ConvertTo-ResearchDate ([string]$range.actual_to) "journal actual_to"
    if ($actualFrom -gt $actualTo) {
        throw "MT5 synchronized history actual_from must not be later than actual_to."
    }
    $requestedTo = ConvertTo-ResearchDate ([string]$contract.requested_to) "data_quality_contract.requested_to"
    if ($actualTo -lt $requestedTo) {
        throw "MT5 synchronized history ends before requested_to: actual '$($range.actual_to)', requested '$($contract.requested_to)'."
    }
    $seriesProof = Get-DataQualitySeriesProof $journalText ([string]$contract.symbol) ([string]$range.actual_from)

    $rawHistoryQuality = Get-ReportLabeledValue (Get-Mt5ReportHtml ([string]$Manifest.report_path)) @('History Quality') 'history quality'
    $historyQuality = ConvertTo-FiniteInvariantDouble $rawHistoryQuality "Report History Quality"
    $threshold = ConvertTo-FiniteInvariantDouble $contract.history_quality_threshold "data_quality_contract.history_quality_threshold"
    if ($historyQuality -le $threshold) {
        throw "Report History Quality $historyQuality is not greater than threshold $threshold."
    }

    return [pscustomobject]@{
        contract = $contract
        history_quality = $historyQuality
        actual_from = [string]$range.actual_from
        actual_to = [string]$range.actual_to
        coverage_class = [string]$seriesProof.coverage_class
        series_proof = $seriesProof.series_proof
        journal_path = [string]$journal.path
        journal_sha256 = [string]$journal.sha256
        journal_bytes_read = [int64]$journal.bytes_read
        journal_files_read = [int]$journal.files_read
        journal_truncated = [bool]$journal.truncated
        exact_match_count = [int]$range.exact_match_count
        distinct_range_count = [int]$range.distinct_range_count
    }
}

function Get-ReportLabeledValue([string]$Html, [string[]]$Labels, [string]$FieldName) {
    foreach ($label in $Labels) {
        $pattern = '(?is)<td[^>]*>\s*' + [regex]::Escape($label) + '\s*:?\s*</td>\s*<td[^>]*>\s*(?:<b>)?\s*([^<]+)'
        $match = [regex]::Match($Html, $pattern)
        if ($match.Success) {
            return [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value).Trim()
        }
    }
    throw "Report identity field '$FieldName' is absent."
}

function Test-Mt5TesterReportComplete {
    param(
        [string]$Path,
        [string]$ExpertName,
        [string]$Symbol,
        [string]$Period,
        [string]$FromDate,
        [string]$ToDate
    )
    # Startup stubs from ReplaceReport=1 are full HTML (>1KB) with empty
    # Expert/Symbol and M0 (1970.01.01-1970.01.01). Size alone is not ready.
    if (-not (Test-PathSafe $Path)) { return $false }
    if ((Get-FileLengthSafe $Path) -le 1000) { return $false }
    $html = Get-Mt5ReportHtml $Path
    if ([string]::IsNullOrWhiteSpace($html)) { return $false }

    $expert = $null
    $symbolVal = $null
    try {
        $expert = Get-ReportLabeledValue $html @('Expert') 'expert'
        $symbolVal = Get-ReportLabeledValue $html @('Symbol') 'symbol'
    } catch {
        return $false
    }
    if ([string]::IsNullOrWhiteSpace($expert) -or [string]::IsNullOrWhiteSpace($symbolVal)) {
        return $false
    }
    $leaf = [IO.Path]::GetFileNameWithoutExtension($ExpertName)
    if ([string]::IsNullOrWhiteSpace($leaf) -or
        $expert.IndexOf($leaf, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        return $false
    }
    if ($symbolVal -cne $Symbol -and
        -not $symbolVal.StartsWith($Symbol, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    # Period label is localized (Period / Chu kỳ). Match the contract window
    # in the value so UTF-8 source encoding cannot drop the Vietnamese label.
    if ($html -match 'M0\s*\(\s*1970\.01\.01') { return $false }
    $periodNeedle = '{0} ({1} - {2})' -f $Period, $FromDate, $ToDate
    if ($html.IndexOf($periodNeedle, [System.StringComparison]::Ordinal) -lt 0) { return $false }
    return $true
}

function Get-ReportIdentity($ReportPath, $Manifest) {
    $html = Get-Mt5ReportHtml $ReportPath
    if ([string]::IsNullOrWhiteSpace($html)) { throw "Report HTML is unreadable: $ReportPath" }
    $serverMatch = [regex]::Match($html, '(?is)<b>\s*([^<]*\(Build\s+\d+\))\s*</b>')
    if (-not $serverMatch.Success) { throw "Report identity field 'server/build' is absent." }
    $serverIdentity = [System.Net.WebUtility]::HtmlDecode($serverMatch.Groups[1].Value).Trim()
    $historyAnchor = $html.IndexOf('History Quality', [System.StringComparison]::OrdinalIgnoreCase)
    if ($historyAnchor -lt 0) { throw "Report identity field 'history quality' is absent." }
    $contractHtml = $html.Substring(0, $historyAnchor)
    $contractRows = @([regex]::Matches(
        $contractHtml,
        '(?is)<tr\s+align="right">\s*<td[^>]*>\s*([^<]+?)\s*:?\s*</td>\s*<td[^>]*align="left"[^>]*>\s*<b>\s*([^<]+?)\s*</b>'
    ))
    if ($contractRows.Count -lt 4) {
        throw "Report account contract rows are absent; broker/currency/deposit/leverage cannot be fingerprinted."
    }
    if ($null -eq $Manifest.contract_symbol_geometry -or
        $null -eq $Manifest.contract_symbol_geometry.digits -or
        $null -eq $Manifest.contract_symbol_geometry.point -or
        $null -eq $Manifest.contract_symbol_geometry.pip_size) {
        throw "Run manifest contract_symbol_geometry is absent; report identity cannot be completed."
    }
    $accountRows = @($contractRows | Select-Object -Last 4)
    $basis = [ordered]@{
        broker = [System.Net.WebUtility]::HtmlDecode($accountRows[0].Groups[2].Value).Trim()
        server = $serverIdentity
        currency = [System.Net.WebUtility]::HtmlDecode($accountRows[1].Groups[2].Value).Trim()
        initial_deposit = [System.Net.WebUtility]::HtmlDecode($accountRows[2].Groups[2].Value).Trim()
        leverage = [System.Net.WebUtility]::HtmlDecode($accountRows[3].Groups[2].Value).Trim()
        history_quality = Get-ReportLabeledValue $html @('History Quality') 'history quality'
        bars = Get-ReportLabeledValue $html @('Bars', 'Thanh') 'bars'
        ticks = Get-ReportLabeledValue $html @('Ticks') 'ticks'
        digits = [int]$Manifest.contract_symbol_geometry.digits
        point = [double]$Manifest.contract_symbol_geometry.point
        pip_size = [double]$Manifest.contract_symbol_geometry.pip_size
        symbol_geometry_source = 'task_packet_bound_execution_receipt'
    }
    $accountPayload = [string]::Join('|', @($basis.currency, $basis.initial_deposit, $basis.leverage, [string]$Manifest.deposit, [string]$Manifest.leverage, [string]$Manifest.spread))
    $dataPayload = [string]::Join('|', @([string]$Manifest.symbol, [string]$Manifest.period, [string]$Manifest.from, [string]$Manifest.to, [string]$Manifest.model, $basis.history_quality, $basis.bars, $basis.ticks, [string]$basis.digits, [string]$basis.point, [string]$basis.pip_size))
    return [pscustomobject]@{
        BrokerFingerprint = Get-TextSha256 ([string]$basis.broker)
        ServerFingerprint = Get-TextSha256 ([string]$basis.server)
        AccountFingerprint = Get-TextSha256 $accountPayload
        DataFingerprint = Get-TextSha256 $dataPayload
        Basis = $basis
    }
}

function Get-CsvDataRowCount($Path) {
    $reader = [System.IO.File]::OpenText($Path)
    try {
        $lineCount = 0L
        while ($null -ne $reader.ReadLine()) { $lineCount++ }
        return [Math]::Max(0L, $lineCount - 1L)
    } finally {
        $reader.Dispose()
    }
}

function Complete-RunManifest($ManifestPath) {
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    $hashBindings = [ordered]@{
        source_sha256 = [string]$manifest.source_snapshot
        ex5_sha256 = [string]$manifest.ex5_snapshot
        config_sha256 = [string]$manifest.config_snapshot
        report_sha256 = [string]$manifest.report_path
    }
    foreach ($field in $hashBindings.Keys) {
        $actual = Get-Sha256Required $hashBindings[$field] "Run manifest $field artifact"
        if ([string]$manifest.$field -ine $actual) {
            throw "Run manifest $field mismatch: recorded '$($manifest.$field)', actual '$actual'."
        }
    }
    $actualTesterEx5Hash = Get-Sha256Required ([string]$manifest.tester_ex5_path) "Staged tester EX5"
    if ([string]$manifest.tester_ex5_sha256 -ine $actualTesterEx5Hash -or [string]$manifest.ex5_sha256 -ine $actualTesterEx5Hash) {
        throw "Run manifest staged tester EX5 does not match the executed/snapshotted binary identity."
    }
    $snapshotForIncludes = [pscustomobject]@{
        Root = [string]$manifest.snapshot_root
        Includes = @($manifest.include_snapshots)
    }
    $actualIncludesHash = Get-SnapshotIncludeSetSha256 $snapshotForIncludes
    if ([string]$manifest.includes_sha256 -ine $actualIncludesHash) {
        throw "Run manifest includes_sha256 mismatch: recorded '$($manifest.includes_sha256)', actual '$actualIncludesHash'."
    }

    $logsDir = Join-Path ([string]$manifest.local_run_dir) 'logs'
    $sidecars = @(
        Get-ChildItem -LiteralPath $logsDir -File -ErrorAction SilentlyContinue |
            Sort-Object Name |
            ForEach-Object {
                $rowCount = $null
                if ($_.Extension -ieq '.csv') {
                    $rowCount = Get-CsvDataRowCount $_.FullName
                }
                [ordered]@{
                    path = "logs/$($_.Name)"
                    sha256 = Get-Sha256Required $_.FullName "Sidecar"
                    length = $_.Length
                    row_count = $rowCount
                }
            }
    )
    foreach ($pattern in @($manifest.required_sidecars)) {
        if ([string]::IsNullOrWhiteSpace([string]$pattern)) { continue }
        $matches = @($sidecars | Where-Object { (Split-Path -Leaf ([string]$_.path)) -like [string]$pattern })
        if ($matches.Count -eq 0) {
            throw "Required sidecar '$pattern' is absent from $logsDir."
        }
    }
    if ([string]$manifest.telemetry_profile -ceq 'lifecycle-v3' -and
        [string]$manifest.telemetry_tier -cne 'off') {
        $lifecycleTrades = @($sidecars | Where-Object { (Split-Path -Leaf ([string]$_.path)) -like '*_LifecycleTrades_*.csv' })
        $runMetaFiles = @($sidecars | Where-Object { (Split-Path -Leaf ([string]$_.path)) -like '*_RunMeta_*.json' })
        if ($lifecycleTrades.Count -ne 1) {
            throw "lifecycle-v3 requires exactly one *_LifecycleTrades_*.csv; found $($lifecycleTrades.Count) in $logsDir."
        }
        if ($runMetaFiles.Count -ne 1) {
            throw "lifecycle-v3 requires exactly one *_RunMeta_*.json; found $($runMetaFiles.Count) in $logsDir."
        }
        $runMetaPath = Join-Path ([string]$manifest.local_run_dir) ([string]$runMetaFiles[0].path)
        try {
            $runMeta = Get-Content -LiteralPath $runMetaPath -Raw | ConvertFrom-Json
        } catch {
            throw "lifecycle-v3 RunMeta JSON is malformed: $runMetaPath ($($_.Exception.Message))"
        }
        if ([string]$runMeta.schema_version -cne 'alphafactory_run_meta.v1') {
            throw "lifecycle-v3 RunMeta schema_version must be 'alphafactory_run_meta.v1'."
        }
        if ([string]::IsNullOrWhiteSpace([string]$runMeta.run_id) -or
            -not ([System.IO.Path]::GetFileNameWithoutExtension($runMetaPath).Contains([string]$runMeta.run_id))) {
            throw "lifecycle-v3 RunMeta run_id is missing or is not bound to its filename."
        }
        if ([string]$runMeta.ea_name -cne [string]$manifest.ea_name -or
            [string]$runMeta.symbol -cne [string]$manifest.symbol -or
            [string]$runMeta.telemetry_profile -cne 'lifecycle-v3') {
            throw "lifecycle-v3 RunMeta identity does not match manifest EA/symbol/telemetry profile."
        }
    }

    $identity = Get-ReportIdentity ([string]$manifest.report_path) $manifest
    $manifest.broker_fingerprint = $identity.BrokerFingerprint
    $manifest.server_fingerprint = $identity.ServerFingerprint
    $manifest.account_fingerprint = $identity.AccountFingerprint
    $manifest.data_fingerprint = $identity.DataFingerprint
    $manifest.sidecars = @($sidecars)
    $manifest | Add-Member -MemberType NoteProperty -Name fingerprint_basis -Value $identity.Basis -Force
    $dataQuality = Assert-DataQualityRunEvidence $manifest
    if ($null -ne $dataQuality) {
        $manifest | Add-Member -MemberType NoteProperty -Name data_quality_gate -Value $dataQuality -Force
        $dataQualityFingerprintBasis = [ordered]@{
            schema_version = 'alphafactory_data_quality_fingerprint.v1'
            base_data_fingerprint = [string]$identity.DataFingerprint
            contract = $dataQuality.contract
            history_quality = [double]$dataQuality.history_quality
            actual_from = [string]$dataQuality.actual_from
            actual_to = [string]$dataQuality.actual_to
            coverage_class = [string]$dataQuality.coverage_class
            series_proof = $dataQuality.series_proof
            journal_sha256 = [string]$dataQuality.journal_sha256
            journal_bytes_read = [int64]$dataQuality.journal_bytes_read
            journal_files_read = [int]$dataQuality.journal_files_read
            journal_truncated = [bool]$dataQuality.journal_truncated
            exact_match_count = [int]$dataQuality.exact_match_count
            distinct_range_count = [int]$dataQuality.distinct_range_count
        }
        $manifest.fingerprint_basis | Add-Member -MemberType NoteProperty -Name data_quality_gate -Value $dataQualityFingerprintBasis -Force
        $manifest | Add-Member -MemberType NoteProperty -Name data_quality_fingerprint_basis -Value $dataQualityFingerprintBasis -Force
        $manifest | Add-Member -MemberType NoteProperty -Name data_quality_fingerprint -Value (Get-TextSha256 (($dataQualityFingerprintBasis | ConvertTo-Json -Depth 12 -Compress))) -Force
    }
    $manifest.generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    Write-JsonAtomically $manifest $ManifestPath 16
    return $ManifestPath
}

function Write-RunManifest($RunDir, $RunId, $EAName, $Sym, $Per, $FromD, $ToD, $Model, $ExecutionMode, $FixedDelayMs, $TimeoutSec, $Overrides, $MainFile, $CompiledEx5File, $Ex5File, $ReportPath, $ConfigPath, $Snapshot, $HypothesisId, $RunRole, $Deposit, $Leverage, $Spread, $TelemetryTier, $TelemetryProfile, $RunStartUtc, $GitSnapshot, $RequiredSidecarList, $ReceiptSha256, $SymbolGeometry, $DataQualityContract = $null, $DataQualityJournalDelta = $null) {
    $spreadValue = if ([string]::IsNullOrWhiteSpace($Spread)) { "current" } else { $Spread }
    $manifest = [ordered]@{
        schema_version = "alphafactory_run_manifest.v2"
        run_id = $RunId
        hypothesis_id = $HypothesisId
        run_role = $RunRole
        ea_name = $EAName
        symbol = $Sym
        period = $Per
        from = $FromD
        to = $ToD
        model = $Model
        execution_mode = $ExecutionMode
        fixed_delay_ms = $FixedDelayMs
        timeout_sec = $TimeoutSec
        execution_lane = "research"
        overrides = $Overrides
        deposit = $Deposit
        leverage = $Leverage
        spread = $spreadValue
        telemetry_tier = $TelemetryTier
        telemetry_profile = $TelemetryProfile
        mt5_storage_contract = $script:Mt5StorageContract
        main_file = $MainFile
        compiled_ex5_file = $CompiledEx5File
        ex5_file = $Ex5File
        tester_ex5_path = $Ex5File
        config_file = $ConfigPath
        local_run_dir = $RunDir
        report_path = $ReportPath
        snapshot_root = $Snapshot.Root
        source_snapshot = $Snapshot.SourcePath
        ex5_snapshot = $Snapshot.Ex5Path
        config_snapshot = $Snapshot.ConfigPath
        include_snapshots = @($Snapshot.Includes)
        source_sha256 = Get-Sha256Required $Snapshot.SourcePath "Source snapshot"
        ex5_sha256 = Get-Sha256Required $Snapshot.Ex5Path "EX5 snapshot"
        tester_ex5_sha256 = Get-Sha256Required $Ex5File "Staged tester EX5"
        config_sha256 = Get-Sha256Required $Snapshot.ConfigPath "Config snapshot"
        report_sha256 = Get-Sha256Required $ReportPath "Report"
        includes_sha256 = Get-SnapshotIncludeSetSha256 $Snapshot
        git_commit = $GitSnapshot.Commit
        git_status = @($GitSnapshot.Status)
        git_status_sha256 = $GitSnapshot.StatusSha256
        broker_fingerprint = $null
        server_fingerprint = $null
        account_fingerprint = $null
        data_fingerprint = $null
        required_sidecars = @(
            $RequiredSidecarList |
                Where-Object { $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_) }
        )
        sidecars = @()
        contract_receipt_sha256 = $ReceiptSha256
        contract_symbol_geometry = [ordered]@{
            digits = [int]$SymbolGeometry.digits
            point = [double]$SymbolGeometry.point
            pip_size = [double]$SymbolGeometry.pip_size
        }
        data_quality_contract = $DataQualityContract
        data_quality_journal_delta = $DataQualityJournalDelta
        artifact_collection_not_before_utc = $RunStartUtc.ToUniversalTime().ToString("o")
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        doctrine = [ordered]@{
            internal_working_language = "English"
            user_reply_language = "Vietnamese"
            canonical_test_symbols = @("XAUUSD", "EURUSD", "GBPUSD")
            artifact_truth_required = $true
        }
    }

    $manifestPath = Join-Path $RunDir "run_manifest.json"
    Write-JsonAtomically $manifest $manifestPath 12
    return $manifestPath
}

function Do-Compile($EAName) {
    Write-Status "Compiling $EAName..."
    Assert-NoUnrelatedTerminal
    $sourceContract = Resolve-EaSourceContract -RepoRoot $AdvisorsRoot -EaName $EAName
    $main = $sourceContract.AbsoluteSource
    $log = [IO.Path]::ChangeExtension($main, ".log")
    $eaDir = Split-Path -Parent $main
    if (-not (Test-Path -LiteralPath $MetaEditor -PathType Leaf)) {
        throw "Compile failed for ${EAName}: MetaEditor not found at $MetaEditor"
    }
    
    # v6.1 NUCLEAR FIX: Delete old .ex5 before compile to force fresh build
    $ex5Files = Get-ChildItem -Path $eaDir -Filter "*.ex5" -File -ErrorAction SilentlyContinue
    if ($ex5Files) {
        $ex5Files | Remove-Item -Force
        Write-Status "Deleted $(@($ex5Files).Count) .ex5 file(s)" "WARN"
    }
    $ex5 = [IO.Path]::ChangeExtension($main, ".ex5")
    if (Test-Path -LiteralPath $log) {
        Remove-Item -LiteralPath $log -Force
    }
    
    $compileArgs = @(Get-MetaEditorCompileArguments `
        -SourcePath $main `
        -LogPath $log `
        -PortableMode ([bool]$MT5PortableMode))
    # Resolve and reject archive dependencies before MetaEditor can compile.
    [void](Get-IncludeDependencyClosure $main)

    $compileStarted = (Get-Date).ToUniversalTime()
    $compiler = Start-Process -FilePath $MetaEditor -ArgumentList $compileArgs -Wait -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2

    if (-not (Test-Path -LiteralPath $log -PathType Leaf)) {
        throw "Compile failed for ${EAName}: compiler log was not created at $log"
    }
    $compileLog = Get-Content -LiteralPath $log -Raw
    if ($compileLog -notmatch '(?im)\b0\s+errors?\b') {
        throw "Compile failed for ${EAName}: compiler log does not prove zero errors. Log: $log"
    }
    if ($compileLog -notmatch '(?im)\b0\s+warnings?\b') {
        throw "Compile failed for ${EAName}: compiler log does not prove zero warnings. Log: $log"
    }
    if (-not (Test-Path -LiteralPath $ex5 -PathType Leaf)) {
        throw "Compile failed for ${EAName}: EX5 was not created. Log: $log"
    }
    $artifact = Get-Item -LiteralPath $ex5
    if (($artifact.Length -le 0) -or ($artifact.LastWriteTimeUtc -lt $compileStarted.AddSeconds(-2))) {
        throw "Compile failed for ${EAName}: EX5 is empty or stale. Artifact: $ex5"
    }
    # MetaEditor CLI uses exit code 1 for a successful command-line compile on
    # this installation (and commonly across MT5 builds). Accept only 0/1, and
    # only after the fresh log proves 0 errors and a fresh nonempty EX5 exists.
    if ($compiler.ExitCode -notin @(0, 1)) {
        throw "Compile failed for ${EAName}: unsupported MetaEditor exit code $($compiler.ExitCode). Log: $log"
    }

    Write-Status "SUCCESS: $($artifact.Length) bytes (MetaEditor exit $($compiler.ExitCode), log 0 errors, 0 warnings). Log: $log" "OK"
    return $ex5
}

function Do-Backtest($EAName, $Sym, $Per, $FromD, $ToD, $TimeoutSec, $Overrides = "", $Model = 0, $ExecutionMode = 0, $FixedDelayMs = 0, $Spread = "", $HypothesisId = "", $RunRole = "challenger", $TelemetryTier = "off", $Deposit = 10000, $Leverage = 100, $ContractReceiptPath = "", $ExpectedReceiptSha256 = "", $RequiredSidecarPatterns = "") {
    Write-Status "Backtest: $EAName on $Sym $Per"
    $testerExecutionMode = if ($ExecutionMode -gt 0) { $ExecutionMode } elseif ($FixedDelayMs -gt 0) { $FixedDelayMs } else { $ExecutionMode }
    
    $sourceContract = Resolve-EaSourceContract -RepoRoot $AdvisorsRoot -EaName $EAName
    $main = $sourceContract.AbsoluteSource
    $effectiveOverrides = Resolve-TelemetryTierOverrides $TelemetryTier $main $Overrides $sourceContract.TelemetryProfile
    $requiredSidecarList = ConvertTo-RequiredSidecarList $RequiredSidecarPatterns $TelemetryTier $sourceContract.TelemetryProfile
    $effectiveSpread = if ([string]::IsNullOrWhiteSpace($Spread)) { 'current' } else { $Spread }
    $receiptBinding = [pscustomobject]@{
        hypothesis_id = $HypothesisId; run_role = $RunRole; ea_name = $EAName; symbol = $Sym; period = $Per
        from = $FromD; to = $ToD; model = $Model; execution_mode = $ExecutionMode
        fixed_delay_ms = $FixedDelayMs; overrides = $effectiveOverrides; telemetry_tier = $TelemetryTier
        telemetry_profile = $sourceContract.TelemetryProfile
        deposit = $Deposit; leverage = $Leverage; spread = $effectiveSpread
        required_sidecars = @($requiredSidecarList)
    }
    # The caller enters the global backtest lock before this function. Rehash all
    # packet-bound evidence immediately before compile/backtest.
    $receiptCheck = Assert-ContractReceipt $ContractReceiptPath $ExpectedReceiptSha256 $receiptBinding
    Assert-ReceiptSourceMatchesMain $receiptCheck $main
    Assert-NoUnrelatedTerminal
    $ex5 = [IO.Path]::ChangeExtension($main, ".ex5")
    Do-Compile $EAName | Out-Null
    
    # Setup sandbox-writable tester staging for config handoff.
    # Keep config inside Advisors so sandboxed child processes can read it.
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $mql5Root = $MT5Mql5Root
    $testerRunsDir = Join-Path $AdvisorsRoot "AlphaTester\$ts"
    New-Item -ItemType Directory -Force -Path $testerRunsDir | Out-Null
    
    # Also create local tracking directory
    $localRunDir = Join-Path $AlphaRoot "runs\$EAName\$ts"
    New-Item -ItemType Directory -Force -Path $localRunDir | Out-Null
    
    # Report path relative from MT5 data folder.
    $reportRelPath = "MQL5\Profiles\Tester\AlphaRuns\$ts\report.html"
    $reportAbsPath = Join-Path $mql5Root "Profiles\Tester\AlphaRuns\$ts\report.html"
    $reportDir = Split-Path -Parent $reportAbsPath
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
    $iniPath = Join-Path $testerRunsDir "config.ini"
    
    # Stage the compiled binary to a run-unique tester path. The shared compile
    # output can be overwritten by standalone compiles; MT5 must never execute it.
    $expertsRoot = Join-Path $mql5Root "Experts"
    $stagedExpertDir = Join-Path $expertsRoot "AlphaFactoryRuns\$EAName\$ts"
    if (Test-Path -LiteralPath $stagedExpertDir) {
        throw "Run-unique tester EX5 directory already exists: $stagedExpertDir"
    }
    New-Item -ItemType Directory -Path $stagedExpertDir -Force | Out-Null
    $stagedEx5Path = Join-Path $stagedExpertDir (Split-Path -Leaf $ex5)
    Copy-Item -LiteralPath $ex5 -Destination $stagedEx5Path -ErrorAction Stop
    $compiledEx5Hash = Get-Sha256Required $ex5 "Compiled EX5"
    $stagedEx5Hash = Get-Sha256Required $stagedEx5Path "Staged EX5"
    if ($compiledEx5Hash -ine $stagedEx5Hash) {
        throw "Staged EX5 does not match the compile output."
    }
    $expertRelPath = Get-RelativePathUnderRoot $stagedEx5Path $expertsRoot
    if ([string]::IsNullOrWhiteSpace($expertRelPath)) {
        throw "Staged EX5 is outside the MT5 Experts root: $stagedEx5Path"
    }

    $testerAgentPort = Resolve-LocalTesterAgentPort
    
    $iniContent = @"
[Tester]
Expert=$expertRelPath
Symbol=$Sym
Period=$Per
Optimization=0
Model=$Model
ExecutionMode=$testerExecutionMode
Dates=2
FromDate=$FromD
ToDate=$ToD
Report=$reportRelPath
ReplaceReport=1
ShutdownTerminal=1
Deposit=$Deposit
Currency=USD
Leverage=$Leverage
UseLocal=1
UseRemote=0
UseCloud=0
Port=$testerAgentPort
"@

    if ($Spread) {
        $iniContent += "`r`nSpread=$Spread"
    }

    # v11.3: ALWAYS write [TesterInputs] to override MT5 cached .set files
    # Without this, MT5 ignores compiled defaults and uses stale cached params
    $iniContent += "`r`n[TesterInputs]`r`n"
    if ($effectiveOverrides) {
        foreach ($testerInputLine in @(ConvertTo-TesterInputLines $main $effectiveOverrides)) {
            $iniContent += "$testerInputLine`r`n"
        }
    }
    
    $iniContent | Set-Content -LiteralPath $iniPath -Encoding Unicode

    $buildDir = Join-Path $localRunDir "build"
    $configDir = Join-Path $localRunDir "config"
    $logsDir = Join-Path $localRunDir "logs"
    $reportsDir = Join-Path $localRunDir "reports"
    $chartsDir = Join-Path $localRunDir "charts"
    $analysisDir = Join-Path $localRunDir "analysis"
    $analysisLogsDir = Join-Path $analysisDir "logs"
    @($buildDir, $configDir, $logsDir, $reportsDir, $chartsDir, $analysisDir, $analysisLogsDir) | ForEach-Object {
        New-Item -ItemType Directory -Force -Path $_ | Out-Null
    }
    $snapshot = New-RunSnapshot $localRunDir $main $stagedEx5Path $iniPath

    # Shared tester cache, Tester profiles, and Common Files are evidence stores.
    # Leave all pre-existing artifacts untouched; post-run collection is bound by
    # this UTC lower bound and the run-local manifest/RunMeta identity.
    $runStartUtc = (Get-Date).ToUniversalTime()

    if ((Get-Sha256Required $stagedEx5Path "Staged EX5") -ine $stagedEx5Hash) {
        throw "Staged EX5 changed immediately before MT5 launch."
    }
    $dataQualityContract = $receiptCheck.DataQualityContract
    # Scoped journal directories only (terminal/tester/agent logs). Never the
    # whole Tester tree — bases/.hcc/cache are not journals.
    $journalRoots = @(Get-Mt5JournalLogRoots -DataRoot $MT5DataRoot -TesterRoot $MT5TesterRoot)
    $journalSnapshot = $null
    if ($null -ne $dataQualityContract) {
        $journalSnapshot = @(New-Mt5JournalLogSnapshot $journalRoots)
    }
    Stop-OrphanPortableTesters
    Write-Status "Starting MT5..."
    $mt5LaunchArgs = @(Get-Mt5LaunchArguments `
        -ConfigPath $iniPath `
        -PortableMode ([bool]$MT5PortableMode))
    $mt5Process = Start-Process -FilePath $MT5 -ArgumentList $mt5LaunchArgs -WorkingDirectory $localRunDir -PassThru
    $mt5Pid = $mt5Process.Id
    Register-RunnerOwnedTerminal $mt5Pid
    Write-Status "MT5 started (PID: $mt5Pid)"
    
    # Wait for a finished tester report, not the ReplaceReport startup stub.
    # Stub HTML is already >1KB with empty Expert/Symbol and 1970 dates.
    $timeout = [Math]::Max(60, $TimeoutSec)
    $reportFound = $false
    $readyHash = ''
    $readyStableHits = 0
    for ($i = 0; $i -lt $timeout; $i += 5) {
        Start-Sleep -Seconds 5

        $completeNow = Test-Mt5TesterReportComplete $reportAbsPath $EAName $Sym $Per $FromD $ToD
        $mt5Running = Get-Process -Id $mt5Pid -ErrorAction SilentlyContinue
        if ($completeNow) {
            try {
                $h = (Get-FileHash -LiteralPath $reportAbsPath -Algorithm SHA256).Hash
            } catch {
                $h = ''
            }
            if ($h -and $h -ceq $readyHash) { $readyStableHits++ }
            else { $readyHash = $h; $readyStableHits = 1 }
        } else {
            $readyHash = ''
            $readyStableHits = 0
        }

        if (-not $mt5Running) {
            if ($completeNow) {
                $reportFound = $true
                break
            }
            for ($grace = 1; $grace -le 6; $grace++) {
                Start-Sleep -Seconds 5
                if (Test-Mt5TesterReportComplete $reportAbsPath $EAName $Sym $Per $FromD $ToD) {
                    $reportFound = $true
                    break
                }
                Write-Status "Waiting for report flush... ($($grace * 5)s)" "INFO"
            }
            if ($reportFound) { break }

            Wait-PortableLiveUpdate
            $adopted = Find-PortablePostUpdateTester $iniPath
            if ($adopted -gt 0) {
                Register-RunnerOwnedTerminal $adopted
                $mt5Pid = $adopted
                Write-Status "Adopted post-liveupdate tester PID $mt5Pid" "WARN"
                continue
            }
            Assert-NoUnrelatedTerminal
            Write-Status "Report not flushed. Relaunching MT5 to force report export..." "WARN"
            $mt5RelaunchArgs = @(Get-Mt5LaunchArguments `
                -ConfigPath $iniPath `
                -PortableMode ([bool]$MT5PortableMode))
            $mt5Relaunch = Start-Process -FilePath $MT5 -ArgumentList $mt5RelaunchArgs -WorkingDirectory $localRunDir -PassThru
            Register-RunnerOwnedTerminal $mt5Relaunch.Id
            for ($retry = 1; $retry -le 12; $retry++) {
                Start-Sleep -Seconds 5
                if (Test-Mt5TesterReportComplete $reportAbsPath $EAName $Sym $Per $FromD $ToD) {
                    $reportFound = $true
                    break
                }
                Write-Status "Waiting for report (relaunch $retry/12)..." "INFO"
            }
            Stop-RunnerOwnedTerminal $mt5Relaunch.Id
            Start-Sleep -Seconds 2
            if ($reportFound) { break }

            throw "Backtest failed: MT5 PID $mt5Pid exited without producing a finished report. Config: $iniPath"
        }

        if ($completeNow -and $readyStableHits -ge 2) {
            $reportFound = $true
            break
        }

        if ($i % 30 -eq 0) { Write-Status "Waiting... ($i s)" }
    }

    if (-not $reportFound) {
        if (Test-Mt5TesterReportComplete $reportAbsPath $EAName $Sym $Per $FromD $ToD) {
            $reportFound = $true
        } else {
            Stop-RunnerOwnedTerminal $mt5Pid
            throw "Backtest failed: timeout after ${timeout}s. Config: $iniPath"
        }
    }

    # Prefer ShutdownTerminal=1 exit; force-stop only if the PID remains.
    $exitWait = 0
    while ((Get-Process -Id $mt5Pid -ErrorAction SilentlyContinue) -and $exitWait -lt 30) {
        Start-Sleep -Seconds 2
        $exitWait += 2
    }
    Stop-RunnerOwnedTerminal $mt5Pid
    if ((Get-Sha256Required $stagedEx5Path "Staged EX5") -ine $stagedEx5Hash) {
        throw "Staged EX5 changed during MT5 execution."
    }
    $dataQualityJournalDelta = $null
    if ($null -ne $dataQualityContract) {
        $deltaPath = Join-Path $logsDir "tester_journal_delta.log"
        $deltaReceipt = Export-Mt5JournalLogDelta `
            -Snapshot $journalSnapshot `
            -Roots $journalRoots `
            -OutputPath $deltaPath `
            -MaxBytes ([int64]$dataQualityContract.max_journal_delta_bytes)
        $dataQualityJournalDelta = [ordered]@{
            path = "logs/tester_journal_delta.log"
            sha256 = $deltaReceipt.sha256
            bytes_read = [int64]$deltaReceipt.bytes_read
            files_read = [int]$deltaReceipt.files_read
            truncated = [bool]$deltaReceipt.truncated
        }
    }
    
    # --- Report found - process results ---
    Write-Status "Report ready!" "OK"
    $localReportPath = Join-Path $localRunDir "report.html"
    Copy-Item $reportAbsPath $localReportPath -Force
    Copy-Item $reportAbsPath (Join-Path $buildDir "report.html") -Force
    Copy-Item $iniPath (Join-Path $localRunDir "config.ini") -Force
    Copy-Item $iniPath (Join-Path $configDir "config.ini") -Force
    $manifestPath = Write-RunManifest -RunDir $localRunDir -RunId $ts -EAName $EAName -Sym $Sym -Per $Per -FromD $FromD -ToD $ToD -Model $Model -ExecutionMode $ExecutionMode -FixedDelayMs $FixedDelayMs -TimeoutSec $TimeoutSec -Overrides $effectiveOverrides -MainFile $main -CompiledEx5File $ex5 -Ex5File $stagedEx5Path -ReportPath $localReportPath -ConfigPath $iniPath -Snapshot $snapshot -HypothesisId $HypothesisId -RunRole $RunRole -Deposit $Deposit -Leverage $Leverage -Spread $Spread -TelemetryTier $TelemetryTier -TelemetryProfile $sourceContract.TelemetryProfile -RunStartUtc $runStartUtc -GitSnapshot $receiptCheck.Git -RequiredSidecarList $requiredSidecarList -ReceiptSha256 $receiptCheck.ReceiptSha256 -SymbolGeometry $receiptCheck.Receipt.binding.symbol_geometry -DataQualityContract $dataQualityContract -DataQualityJournalDelta $dataQualityJournalDelta
    Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $configDir "run_manifest.json") -Force

    if ($effectiveOverrides) {
        $effectiveOverrides | Set-Content (Join-Path $localRunDir "overrides.txt") -Encoding UTF8
        $effectiveOverrides | Set-Content (Join-Path $configDir "overrides.txt") -Encoding UTF8
    }

    $sidecarRoots = @(Get-Mt5SidecarRoots `
        -CommonFilesRoot $MT5CommonFilesRoot `
        -TesterRoot $MT5TesterRoot `
        -IncludeCommonFiles ([bool]$MT5AllowCommonFiles))
    $defaultSidecarPatterns = @("${Sym}_*Signals_*.csv", "${Sym}_*Trades_*.csv", "*_LifecycleTrades_*.csv", "${Sym}_*PX6_*.csv", "${Sym}_*Ghost_*.csv", "${Sym}_*Shadow_*.csv", "${Sym}_*Observers_*.csv", "${Sym}_*Activity_*.csv", "${Sym}_*EngineAudit_*.csv", "${Sym}_*PVSRA_SR_*.csv", "${Sym}_*Opportunities_*.csv", "${Sym}_*Regime_*.csv", "${Sym}_*StateTelemetry_*.csv", "${Sym}_*FxClassicNearMiss_*.csv", "${Sym}_*GoldRegimeContext_*.csv", "*_RunMeta_*.json")
    # RequiredSidecars is part of the pre-run receipt binding. Include those
    # patterns in collection as well as validation so opt-in research artifacts
    # cannot be left behind in a tester-agent Files directory.
    $patterns = @(@($defaultSidecarPatterns) + @($requiredSidecarList) | Sort-Object -Unique)
    $sidecarSources = New-Object System.Collections.Generic.List[object]
    foreach ($sidecarRoot in $sidecarRoots) {
        foreach ($pat in $patterns) {
            Get-ChildItem -LiteralPath $sidecarRoot -Filter $pat -File -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTimeUtc -ge $runStartUtc } |
                ForEach-Object { $sidecarSources.Add($_) }
        }
    }
    foreach ($nameGroup in @($sidecarSources | Sort-Object FullName -Unique | Group-Object Name)) {
        if ($nameGroup.Count -ne 1) {
            $locations = @($nameGroup.Group | ForEach-Object { $_.FullName }) -join '; '
            throw "Ambiguous MT5 sidecar '$($nameGroup.Name)' exists in multiple storage roots: $locations"
        }
        $source = $nameGroup.Group[0]
        $mirrorReceipt = Copy-AlphaLogWithMirror `
            -Source $source.FullName `
            -PrimaryDirectory $logsDir `
            -MirrorDirectory $analysisLogsDir
        if ($mirrorReceipt.mode -eq 'copy_fallback') {
            Write-Status "Hardlink unavailable; retained physical log mirror for $($source.Name)" "WARN"
        }
        $commonFilesKeep = @('SNR_FX_EVENTS.csv', 'news_events.csv', 'event_surprises.csv', 'XSP_XAU_US_EVENTS.csv')
        if ($commonFilesKeep -notcontains $source.Name) {
            $sourceFull = [System.IO.Path]::GetFullPath($source.FullName)
            $underSidecar = $false
            foreach ($sidecarRoot in $sidecarRoots) {
                if (Test-Mt5PathUnderRoot -Path $sourceFull -Root $sidecarRoot) {
                    $underSidecar = $true
                    break
                }
            }
            if (-not $underSidecar) {
                throw "Sidecar source escaped collection roots: $sourceFull"
            }
            if ($sourceFull -match '(?i)\\(bases|cache)(\\|$)' -or $sourceFull -match '(?i)\.hcc$') {
                throw "Refusing to delete protected MT5 storage: $sourceFull"
            }
            Remove-Item -LiteralPath $sourceFull -Force
        }
    }

    Complete-RunManifest $manifestPath | Out-Null
    Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $configDir "run_manifest.json") -Force

    # Normal non-collection receipts omit authority; StrictMode must not crash on missing property.
    $receiptAuthorityProperty = $receiptCheck.Receipt.PSObject.Properties['authority']
    $receiptAuthority = if ($null -ne $receiptAuthorityProperty) { [string]$receiptAuthorityProperty.Value } else { '' }
    if ($receiptAuthority -in @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )) {
        Do-AnalyzeZeroTradeCollection (Join-Path $localRunDir "report.html") $analysisDir $receiptAuthority
        try {
            Invoke-AlphaPostRunCleanupSafe -EaName $EAName -RunId $ts -MinAgeHours 0
        } catch {
            Write-Status "Post-run cleanup skipped: $($_.Exception.Message)" "WARN"
        }
        Write-Status "Data collection complete: $localRunDir" "OK"
        Write-Output "ALPHA_RUN_DIR=$localRunDir"
        return
    }

    Do-Analyze (Join-Path $localRunDir "report.html") $analysisDir
    $datalogAnalyzer = Join-Path $AlphaRoot "analysis\datalog_analyzer.py"
    if ((Test-Path $datalogAnalyzer) -and (Test-Path $analysisLogsDir)) {
        python $datalogAnalyzer --logs-dir "$analysisLogsDir" --out "$(Join-Path $analysisDir 'datalog')"
        if ($LASTEXITCODE -ne 0) {
            throw "Backtest failed: datalog analyzer exit code $LASTEXITCODE."
        }
    }
    $tcaSummary = Join-Path $AlphaRoot "analysis\tca_summary.py"
    if ((Test-Path $tcaSummary) -and (Test-Path $analysisLogsDir)) {
        python $tcaSummary --logs-dir "$analysisLogsDir" --out-dir "$analysisDir"
        if ($LASTEXITCODE -ne 0) {
            throw "Backtest failed: TCA summary exit code $LASTEXITCODE."
        }
    }
    $xspBuilder = Join-Path $AlphaRoot "analysis\xsp_artifact_builder.py"
    if ((Test-Path $xspBuilder) -and ($EAName -eq "XAU_Scalp_Portfolio")) {
        python $xspBuilder --run-dir "$localRunDir" --analysis-dir "$analysisDir" --logs-dir "$logsDir"
        if ($LASTEXITCODE -ne 0) {
            throw "Backtest failed: XSP artifact builder exit code $LASTEXITCODE."
        }
    }
    Invoke-TradeChartCaptureSafe `
        -ReportPath (Join-Path $localRunDir "report.html") `
        -OutDir (Join-Path $analysisDir "trade_charts") `
        -RunDir $localRunDir `
        -LogsDir $analysisLogsDir `
        -Sym $Sym `
        -Per $Per
    try {
        Invoke-AlphaPostRunCleanupSafe -EaName $EAName -RunId $ts -MinAgeHours 0
    } catch {
        Write-Status "Post-run cleanup skipped: $($_.Exception.Message)" "WARN"
    }
    Write-Status "Backtest complete: $localRunDir" "OK"
    Write-Output "ALPHA_RUN_DIR=$localRunDir"
}

function Invoke-TradeChartCaptureSafe {
    param(
        [string]$ReportPath,
        [string]$OutDir = "",
        [string]$RunDir = "",
        [string]$LogsDir = "",
        [string]$Sym = "",
        [string]$Per = ""
    )
    $capture = Join-Path $AlphaRoot "analysis\trade_chart_capture.py"
    if (-not (Test-Path -LiteralPath $capture -PathType Leaf)) {
        Write-Status "Trade charts skipped: capture script missing" "WARN"
        return
    }
    if ([string]::IsNullOrWhiteSpace($ReportPath) -or -not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
        Write-Status "Trade charts skipped: report missing" "WARN"
        return
    }
    if ([string]::IsNullOrWhiteSpace($OutDir)) {
        $OutDir = Join-Path (Split-Path $ReportPath) "analysis\trade_charts"
    }
    try {
        New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    } catch {
        Write-Status "Trade charts skipped: cannot create $OutDir" "WARN"
        return
    }
    $pyArgs = @(
        $capture,
        "--report", "$ReportPath",
        "--out", "$OutDir",
        "--frames", "both"
    )
    if (-not [string]::IsNullOrWhiteSpace($RunDir)) { $pyArgs += @("--run-dir", "$RunDir") }
    if (-not [string]::IsNullOrWhiteSpace($LogsDir) -and (Test-Path -LiteralPath $LogsDir)) {
        $pyArgs += @("--logs-dir", "$LogsDir")
    }
    if (-not [string]::IsNullOrWhiteSpace($Sym)) { $pyArgs += @("--symbol", "$Sym") }
    if (-not [string]::IsNullOrWhiteSpace($Per)) { $pyArgs += @("--timeframe", "$Per") }
    if (-not [string]::IsNullOrWhiteSpace($MT5) -and (Test-Path -LiteralPath $MT5 -PathType Leaf)) {
        $pyArgs += @("--mt5-path", "$MT5")
    }
    Write-Status "Trade charts (fail-open)..."
    try {
        python @pyArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Status "Trade charts skipped: python exit $LASTEXITCODE" "WARN"
        }
    } catch {
        Write-Status "Trade charts skipped: $($_.Exception.Message)" "WARN"
    }
}

function Do-Analyze($ReportPath, $OutDir = "") {
    if (-not (Test-Path $ReportPath)) {
        throw "Analysis failed: report not found at $ReportPath"
    }
    
    if (-not $OutDir) { $OutDir = Join-Path (Split-Path $ReportPath) "analysis" }
    
    $analyzer = Join-Path $AlphaRoot "analysis\enhanced_analyzer.py"
    if (-not (Test-Path -LiteralPath $analyzer -PathType Leaf)) {
        throw "Analysis failed: analyzer not found at $analyzer"
    }
    $chartArg = if ($Charts) { "--charts" } else { "" }
    
    Write-Status "Analyzing..."
    python $analyzer --report "$ReportPath" --out "$OutDir" $chartArg
    if ($LASTEXITCODE -ne 0) {
        throw "Analysis failed: enhanced analyzer exit code $LASTEXITCODE."
    }

    $summaryFile = Join-Path $OutDir "enhanced_summary.json"
    if (-not (Test-Path -LiteralPath $summaryFile -PathType Leaf)) {
        throw "Analysis failed: required summary was not created at $summaryFile"
    }
    Write-Status "Done: $OutDir" "OK"

    $s = Get-Content -LiteralPath $summaryFile | ConvertFrom-Json
    Write-Host "`n=== RESULTS ===" -ForegroundColor Cyan
    Write-Host "Trades: $($s.n_trades)"
    Write-Host "PF:     $($s.profit_factor)"
    Write-Host "Net:    `$$($s.net_profit)"
    Write-Host "DD:     $($s.max_drawdown_pct)%"
}

function Do-AnalyzeZeroTradeCollection($ReportPath, $OutDir, $Authority) {
    if ([string]$Authority -notin @(
        'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE',
        'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    )) {
        throw "Unsupported zero-trade collection authority '$Authority'."
    }
    $html = Get-Mt5ReportHtml $ReportPath
    if ([string]::IsNullOrWhiteSpace($html)) { throw "Report HTML is unreadable: $ReportPath" }
    $localizedTotalTrades = [regex]::Unescape('T\u1ED5ng s\u1ED1 giao d\u1ECBch')
    $rawTrades = Get-ReportLabeledValue $html @('Total Trades', $localizedTotalTrades) 'total trades'
    $tradeMatch = [regex]::Match([string]$rawTrades, '^\s*(\d+)')
    if (-not $tradeMatch.Success) {
        throw "Data collection report total-trades value is not numeric: '$rawTrades'."
    }
    $tradeCount = [int64]$tradeMatch.Groups[1].Value
    if ($tradeCount -ne 0) {
        throw "Data acquisition authority requires exactly zero Strategy Tester trades; found $tradeCount."
    }
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    $summary = [ordered]@{
        schema_version = 'alphafactory_zero_trade_collection_summary.v1'
        analysis_mode = 'data_acquisition_only'
        authority = [string]$Authority
        n_trades = 0
        performance_metrics_authorized = $false
        generated_at_utc = [datetime]::UtcNow.ToString('o')
    }
    Write-JsonAtomically $summary (Join-Path $OutDir 'enhanced_summary.json') 5
    Write-Status "Zero-trade data collection verified; economic analysis skipped." "OK"
}

function Show-Status {
    Write-Host "`n==============================" -ForegroundColor Cyan
    Write-Host "  ALPHAFACTORY" -ForegroundColor Cyan
    Write-Host "==============================`n" -ForegroundColor Cyan
    
    # MT5 status
    $mt5On = Get-Process terminal64,metaeditor64 -ErrorAction SilentlyContinue
    Write-Host "MT5: $(if ($mt5On) { 'RUNNING' } else { 'STOPPED' })" -ForegroundColor $(if ($mt5On) { "Green" } else { "Yellow" })
    Write-Host "Config source: $script:Mt5ConfigSource" -ForegroundColor DarkGray
    Write-Host "Portable: $([bool]$MT5PortableMode)"
    Write-Host "Install: $MT5InstallRoot"
    Write-Host "Data:    $MT5DataRoot"
    Write-Host "Common:  $MT5CommonFilesRoot"
    Write-Host "FILE_COMMON allowed: $([bool]$MT5AllowCommonFiles)"
    Write-Host "Tester:  $MT5TesterRoot"
    Write-Host "Required storage drive: $(if ([string]::IsNullOrWhiteSpace($MT5RequiredStorageDrive)) { '(not pinned)' } else { $MT5RequiredStorageDrive })"
    Write-Host "Editor:  $MetaEditor"
    Write-Host "`n=== Live MT5 clients ===" -ForegroundColor Cyan
    $liveClients = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe' OR Name='metaeditor64.exe' OR Name='MetaEditor64.exe'" -ErrorAction SilentlyContinue)
    if ($liveClients.Count -eq 0) {
        Write-Host "  (none)"
    } else {
        foreach ($proc in $liveClients) {
            Write-Host ("  PID {0} {1}" -f $proc.ProcessId, $proc.Name)
            Write-Host ("    {0}" -f $proc.ExecutablePath)
            if (-not [string]::IsNullOrWhiteSpace([string]$proc.CommandLine)) {
                Write-Host ("    {0}" -f $proc.CommandLine)
            }
        }
    }
    $appDataClones = @(Get-Mt5AppDataOriginClones -InstallRoot $MT5InstallRoot -RuntimeRoot $script:Mt5FactoryRuntimeRoot)
    if ($appDataClones.Count -gt 0) {
        Write-Host "`n=== AppData clones of factory portables (do not launch these) ===" -ForegroundColor Yellow
        foreach ($clone in $appDataClones) {
            Write-Host "  $clone"
        }
    }
    if ($script:Mt5ConfigSource -notlike "alpha.local.ps1*") {
        Write-Host "Tip: pin this machine via alpha.local.ps1 (see alpha.local.ps1.example)" -ForegroundColor Yellow
    }
    
    # List EAs
    Write-Host "`n=== EAs ===" -ForegroundColor Cyan
    foreach ($ea in (Get-EAs)) {
        $ex5 = Get-ChildItem -Path $ea.FullName -Recurse -Filter "*.ex5" -ErrorAction SilentlyContinue
        $status = if ($ex5) { "[OK]" } else { "[--]" }
        $color = if ($ex5) { "Green" } else { "Gray" }
        Write-Host "  $status $($ea.Name)" -ForegroundColor $color
    }
    
    Write-Host "`n=== Commands ===" -ForegroundColor Yellow
    Write-Host "  .\alpha.ps1 compile `"EA Name`""
    Write-Host "  .\alpha.ps1 backtest `"EA Name`" -Symbol XAUUSD"
    Write-Host "  .\alpha.ps1 analyze -Report `"path`""
    Write-Host "  .\alpha.ps1 clean                 # dry-run post-run hygiene"
    Write-Host "  .\alpha.ps1 clean -Execute        # safe cleanup; journals/portable are Owner reclaim"
    Write-Host "  .\tools\init_machine_paths.ps1   # generate alpha.local.ps1"
    Write-Host ""
}

# Main
Write-Host "`n  ALPHAFACTORY v4.3`n" -ForegroundColor Cyan

switch ($Action.ToLower()) {
    "status" { Show-Status }
    "list" { Get-EAs | ForEach-Object { Write-Host $_.Name } }
    "compile" { 
        if (-not $Name) { throw "EA name required" }
        Do-Compile $Name 
    }
    "backtest" { 
        if (-not $Name) { throw "EA name required" }
        if ([string]::IsNullOrWhiteSpace($HypothesisId)) { throw "HypothesisId is required for backtest evidence." }
        if ($Deposit -le 0) { throw "Deposit must be greater than zero." }
        if ($Leverage -le 0) { throw "Leverage must be greater than zero." }
        Assert-BacktestScalarContract $Name $HypothesisId $Symbol $Period $From $To $Spread $ExecutionMode $FixedDelayMs
        Enter-GlobalBacktestLock $Name $HypothesisId
        try {
            Do-Backtest $Name $Symbol $Period $From $To $TimeoutSec $Overrides $Model $ExecutionMode $FixedDelayMs $Spread $HypothesisId $RunRole $TelemetryTier $Deposit $Leverage $ContractReceipt $ContractReceiptSha256 $RequiredSidecars
        } finally {
            try {
                Stop-AllRunnerOwnedTerminals
            } finally {
                Exit-GlobalBacktestLock
            }
        }
    }
    # ================================================================
    # ANALYZE - Parse và phân tích MT5 backtest report
    # Input: -Report "path/to/report.html"
    # Output: JSON summaries, CSV breakdowns, charts (if -Charts)
    # -Charts / -TradeCharts also render per-trade entry+exit PNGs (fail-open).
    # Auto-logs results to STRATEGY_LOG.md
    # ================================================================
    "analyze" { 
        if (-not $Report) { throw "Report path required" }
        Do-Analyze $Report
        if ($Charts -or $TradeCharts) {
            $reportFull = $Report
            try { $reportFull = (Resolve-Path -LiteralPath $Report).Path } catch { $reportFull = $Report }
            $runDir = Split-Path $reportFull
            $analysisDir = Join-Path $runDir "analysis"
            $logs = Join-Path $analysisDir "logs"
            if (-not (Test-Path -LiteralPath $logs)) { $logs = Join-Path $runDir "logs" }
            $sym = $Symbol
            $per = $Period
            $manifestPath = Join-Path $runDir "run_manifest.json"
            if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
                try {
                    $man = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
                    if ($man.symbol) { $sym = [string]$man.symbol }
                    if ($man.period) { $per = [string]$man.period }
                } catch {}
            }
            Invoke-TradeChartCaptureSafe `
                -ReportPath $reportFull `
                -OutDir (Join-Path $analysisDir "trade_charts") `
                -RunDir $runDir `
                -LogsDir $logs `
                -Sym $sym `
                -Per $per
        }
    }
    "git" {
        & "$AlphaRoot\tools\git_sync.ps1" status
    }
    # ================================================================
    # LOG - Ghi kết quả vào STRATEGY_LOG.md
    # Tự động hoặc manual entry
    # ================================================================
    "log" {
        $logger = Join-Path $AlphaRoot "analysis\strategy_logger.py"
        $env:PYTHONIOENCODING = "utf-8"
        if ($Report) {
            python $logger --results "$Report" --name "$Name"
        } elseif ($Name) {
            Write-Host "Manual log entry. Provide --pf, --dd, --trades" -ForegroundColor Yellow
            python $logger --name "$Name"
        } else {
            Write-Status "Usage: .\alpha.ps1 log -Report 'results.json'" "INFO"
            Write-Status "   or: .\alpha.ps1 log 'Strategy Name' (then edit STRATEGY_LOG.md)" "INFO"
        }
    }
    # ================================================================
    # SCAN - Quick strategy scan bằng VectorBT
    # Chạy trong vài giây, cho kết quả sơ bộ
    # CHÚ Ý: Kết quả VectorBT thường tốt hơn MT5 30-80%
    # ================================================================
    "scan" {
        Write-Status "Quick Strategy Scan (VectorBT)..."
        Write-Host "⚠️  Note: VectorBT results typically degrade 30-50% in MT5" -ForegroundColor Yellow
        $scanner = Join-Path $AlphaRoot "analysis\quick_scan.py"
        if ($Name) {
            python $scanner --strategy $Name --symbol $Symbol
        } else {
            python $scanner --all --symbol $Symbol
        }
    }
    # ================================================================
    # MONTE - Monte Carlo simulation (1000 runs)
    # Shuffle trade order để test worst-case scenarios
    # Output: P95 DD (expect this), Risk of Ruin
    # DIAGNOSTIC ONLY: P95 DD informs the risk gate; it never authorizes sizing or deployment.
    # ================================================================
    "monte" {
        if (-not $Report) { throw "Report path required. Use: .\alpha.ps1 monte -Report 'path'" }
        Write-Status "Running Monte Carlo Simulation (1000 sims)..."
        $mc = Join-Path $AlphaRoot "analysis\monte_carlo.py"
        $env:PYTHONIOENCODING = "utf-8"
        python $mc --report "$Report" --sims 1000
    }
    # ================================================================
    # WFA - Walk-Forward Analysis (5 windows, 70/30 IS/OOS)
    # Phát hiện overfitting bằng cách so sánh IS vs OOS
    # DIAGNOSTIC ONLY: this command is fixed-parameter temporal slicing, not promotion WFA.
    # ================================================================
    "wfa" {
        if (-not $Report) { throw "Report path required. Use: .\alpha.ps1 wfa -Report 'path'" }
        Write-Status "Running Walk-Forward Analysis (5 windows, 70/30 split)..."
        $wfa = Join-Path $AlphaRoot "analysis\walk_forward.py"
        $env:PYTHONIOENCODING = "utf-8"
        python $wfa --report "$Report" --windows 5
    }
    # ================================================================
    # ROBUST - Professional Robustness Suite (7 tests)
    # Sample Size, Noise, Parameter, Vs Random, Variance, Delayed, Shifted
    # DIAGNOSTIC ONLY: pass rate is one input to validate-full, never a live authorization.
    # ================================================================
    "robust" {
        if (-not $Report) { throw "Report path required. Use: .\alpha.ps1 robust -Report 'path'" }
        Write-Status "Running Professional Robustness Suite (7 tests)..."
        Write-Host "Tests: Sample Size, Noise, Parameter, Vs Random, Variance, Delayed, Shifted" -ForegroundColor Cyan
        $robust = Join-Path $AlphaRoot "analysis\robustness_suite.py"
        $env:PYTHONIOENCODING = "utf-8"
        python $robust --report "$Report" --test all
    }
    # ================================================================
    # PARAM - Full-pass MT5 optimization import, DSR, and real heatmap
    # A single-report Gaussian perturbation is forbidden as stability evidence.
    # ================================================================
    "param" {
        if (-not $Report) { throw "Full MT5 optimization XML/CSV required. Use: .\alpha.ps1 param -Report 'optimization.xml'" }
        Write-Status "Importing full MT5 optimization family and building real parameter surface..."
        $param = Join-Path $AlphaRoot "analysis\param_optimizer.py"
        $paramArgs = @($param, "--report", $Report, "--metric", $Metric, "--plateau-fraction", ([string]$PlateauFraction))
        if ($Output) { $paramArgs += @("--out", $Output) }
        if ($Param1) { $paramArgs += @("--param1", $Param1) }
        if ($Param2) { $paramArgs += @("--param2", $Param2) }
        if ($ExpectedTrials -gt 0) { $paramArgs += @("--expected-total-trials", ([string]$ExpectedTrials)) }
        if ($SelectedPass) { $paramArgs += @("--selected-pass", $SelectedPass) }
        if ($SelectedReturns) { $paramArgs += @("--selected-returns", $SelectedReturns) }
        if ($ReturnsColumn) { $paramArgs += @("--returns-column", $ReturnsColumn) }
        if ($SharpeColumn) { $paramArgs += @("--sharpe-column", $SharpeColumn) }
        if ($SrSemantics) { $paramArgs += @("--sr-semantics", $SrSemantics) }
        if ($LowerIsBetter) { $paramArgs += "--lower-is-better" }
        if ($SelectionFrozen) { $paramArgs += "--selection-frozen" }
        if ($Packet) { $paramArgs += @("--optimization-receipt", $Packet) }
        if (-not $Charts) { $paramArgs += "--no-plot" }
        & python @paramArgs
        if ($LASTEXITCODE -ne 0) { throw "Optimization audit failed with exit code $LASTEXITCODE" }
    }
    # ================================================================
    # CPCV - Event-level purged and embargoed combinatorial CV
    # ================================================================
    "cpcv" {
        if (-not $Report) { throw "Event CSV required. Use: .\alpha.ps1 cpcv -Report 'events.csv'" }
        Write-Status "Running event-level purged/embargoed CPCV..."
        $cpcv = Join-Path $AlphaRoot "analysis\purged_cpcv.py"
        if ($Metric -notin @("mean", "sharpe", "pf")) {
            throw "CPCV -Metric must be one of: mean, sharpe, pf."
        }
        $cpcvMetric = $Metric
        $cpcvArgs = @($cpcv, "--events-csv", $Report, "--groups", ([string]$CpcvGroups), "--test-groups", ([string]$CpcvTestGroups), "--embargo-pct", ([string]$EmbargoPct), "--metric", $cpcvMetric)
        if ($Output) { $cpcvArgs += @("--out", $Output) }
        if ($SelectionFrozen) { $cpcvArgs += "--frozen-pre-outcome" }
        & python @cpcvArgs
        if ($LASTEXITCODE -ne 0) { throw "Purged CPCV failed with exit code $LASTEXITCODE" }
    }
    # ================================================================
    # IMPACT - Conditional volume/liquidity/volatility cost stress
    # ================================================================
    "impact" {
        if (-not $Report) { throw "Fill CSV required. Use: .\alpha.ps1 impact -Report 'fills.csv' -TradesCsv 'trades.csv'" }
        if (-not $TradesCsv) { throw "TradesCsv is required for gross-to-adjusted PnL reconciliation." }
        if ($LiquiditySource -eq "observed_depth" -and -not $Calibration) {
            throw "observed_depth requires -Calibration; schema v1 remains diagnostic-only."
        }
        if ($LiquiditySource -eq "adv_proxy" -and $Calibration) {
            throw "adv_proxy does not accept an observed-depth -Calibration."
        }
        Write-Status "Running diagnostic-only dynamic market-impact cost audit..."
        $impact = Join-Path $AlphaRoot "analysis\dynamic_cost_model.py"
        $impactArgs = @($impact, "--fills-csv", $Report, "--trades-csv", $TradesCsv, "--source-kind", $LiquiditySource, "--eta", ([string]$ImpactEta))
        if ($Calibration) { $impactArgs += @("--calibration", $Calibration) }
        if ($Output) { $impactArgs += @("--out", $Output) }
        & python @impactArgs
        if ($LASTEXITCODE -ne 0) { throw "Dynamic cost audit failed with exit code $LASTEXITCODE" }
    }
    # ================================================================
    # MT5DATA - Export data từ MT5 terminal (native Python)
    # Dùng MetaTrader5 package
    # ================================================================
    "mt5data" {
        Write-Status "MT5 Native Data Export..."
        $mt5 = Join-Path $AlphaRoot "analysis\mt5_connector.py"
        if ($Name -eq "info") {
            python $mt5 --action info
        } elseif ($Name -eq "export") {
            python $mt5 --action export --symbol $Symbol --timeframe $Period
        } else {
            python $mt5 --action data --symbol $Symbol --timeframe $Period --bars 500
        }
    }
    # ================================================================
    # VALIDATE-FULL - Unified Validation (ALL gates, parallel)
    # Runs: analyze + equity audit + monte carlo + WFA + robustness
    # in parallel. Outputs validation_summary.json
    # Pattern: Vibe-Trading DAG orchestration
    # ================================================================
    "validate-full" {
        if (-not $Report) { throw "Report path required. Use: .\alpha.ps1 validate-full -Report 'path'" }
        Write-Status "Running FULL Validation Pipeline (5 tests, parallel)..."
        Write-Host "  Tests: Enhanced Analysis, Equity Audit, Monte Carlo, Walk-Forward, Robustness" -ForegroundColor Cyan
        $unified = Join-Path $AlphaRoot "analysis\unified_validation.py"
        if (-not (Test-Path -LiteralPath $unified -PathType Leaf)) {
            throw "Unified validator not found: $unified"
        }
        $resolvedReport = (Resolve-Path -LiteralPath $Report).Path
        $runManifest = Join-Path (Split-Path -Parent $resolvedReport) 'run_manifest.json'
        $analysisOut = Join-Path (Split-Path -Parent $resolvedReport) 'analysis'
        $nonRepaintTool = Join-Path $AlphaRoot 'tools\audit_mql5_nonrepaint.py'
        $nonRepaintOut = Join-Path $analysisOut 'nonrepaint_audit.json'
        if (-not (Test-Path -LiteralPath $runManifest -PathType Leaf)) {
            throw "Run manifest required for non-repaint validation: $runManifest"
        }
        if (-not (Test-Path -LiteralPath $nonRepaintTool -PathType Leaf)) {
            throw "Non-repaint auditor not found: $nonRepaintTool"
        }
        New-Item -ItemType Directory -Path $analysisOut -Force | Out-Null
        $global:LASTEXITCODE = 0
        & python $nonRepaintTool --manifest $runManifest --out $nonRepaintOut
        $nonRepaintExitCode = $LASTEXITCODE
        if ($nonRepaintExitCode -ne 0) {
            throw "Non-repaint audit failed with exit code $nonRepaintExitCode."
        }
        $env:PYTHONIOENCODING = "utf-8"
        $validationArgs = @(
            $unified,
            "--report", $resolvedReport,
            "--stage", $ValidationStage,
            "--holding-contract", $HoldingContract
        )
        if (-not [string]::IsNullOrWhiteSpace($CostArtifact)) {
            $validationArgs += @("--cost-artifact", $CostArtifact)
        }
        if (-not [string]::IsNullOrWhiteSpace($WfaArtifact)) {
            $validationArgs += @("--wfa-artifact", $WfaArtifact)
        }
        if (-not [string]::IsNullOrWhiteSpace($VariantsDir)) {
            $validationArgs += @("--variants-dir", $VariantsDir)
        }
        $global:LASTEXITCODE = 0
        & python @validationArgs
        $validationExitCode = $LASTEXITCODE
        if ($validationExitCode -ne 0) {
            throw "Unified validation failed with exit code $validationExitCode."
        }
    }
    "delivery" {
        if ([string]::IsNullOrWhiteSpace($Packet)) {
            throw "EA delivery packet required. Use: .\alpha.ps1 delivery -Packet '<EA_DELIVERY_PACKET.json>'"
        }
        $validator = Join-Path $AlphaRoot "tools\validate_ea_delivery_packet.py"
        if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) {
            throw "EA delivery validator not found: $validator"
        }
        $resolvedPacket = (Resolve-Path -LiteralPath $Packet).Path
        $global:LASTEXITCODE = 0
        & python $validator --packet $resolvedPacket
        $deliveryExitCode = $LASTEXITCODE
        if ($deliveryExitCode -ne 0) {
            throw "EA delivery validation failed with exit code $deliveryExitCode."
        }
    }
    "fast-kill" {
        if ([string]::IsNullOrWhiteSpace($Packet)) {
            throw "Fast-kill closeout packet required. Use: .\alpha.ps1 fast-kill -Packet '<FAST_KILL_CLOSEOUT.json>'"
        }
        $validator = Join-Path $AlphaRoot "tools\validate_fast_kill_closeout.py"
        if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) {
            throw "Fast-kill closeout validator not found: $validator"
        }
        $resolvedPacket = (Resolve-Path -LiteralPath $Packet).Path
        $global:LASTEXITCODE = 0
        & python $validator --packet $resolvedPacket
        $fastKillExitCode = $LASTEXITCODE
        if ($fastKillExitCode -ne 0) {
            throw "Fast-kill closeout validation failed with exit code $fastKillExitCode."
        }
    }
    "clean" {
        $scope = if ([string]::IsNullOrWhiteSpace($Name)) { 'safe' } else { $Name.ToLowerInvariant() }
        if ($scope -notin @('safe', 'journals', 'all')) {
            throw "clean scope must be safe, journals, or all. Got: $Name"
        }
        $cleanup = Join-Path $AlphaRoot 'tools\post_run_cleanup.ps1'
        if (-not (Test-Path -LiteralPath $cleanup -PathType Leaf)) {
            throw "Cleanup tool not found: $cleanup"
        }
        $global:LASTEXITCODE = 0
        if ($Execute) {
            & $cleanup -Scope $scope -MinAgeHours 1 -Execute
        } else {
            & $cleanup -Scope $scope -MinAgeHours 1
        }
        if ($LASTEXITCODE -ne 0) {
            throw "clean failed with exit code $LASTEXITCODE."
        }
        $hygiene = Join-Path $AlphaRoot 'tools\workspace_hygiene.ps1'
        if (Test-Path -LiteralPath $hygiene -PathType Leaf) {
            $global:LASTEXITCODE = 0
            if ($Execute) {
                & $hygiene -Execute
            } else {
                & $hygiene
            }
            if ($LASTEXITCODE -ne 0) {
                throw "workspace hygiene failed with exit code $LASTEXITCODE."
            }
        }
    }
    "validate" {
        Write-Status "Validating Python environment..."
        $required = @("numpy", "pandas", "matplotlib")
        foreach ($pkg in $required) {
            $check = python -c "import $pkg; print('OK')" 2>&1
            if ($check -eq "OK") {
                Write-Status "$pkg - installed" "OK"
            } else {
                Write-Status "$pkg - MISSING" "ERR"
            }
        }
        # Check vectorbt
        $vbtCheck = python -c "import vectorbt; print('OK')" 2>&1
        if ($vbtCheck -eq "OK") {
            Write-Status "vectorbt - installed" "OK"
        } else {
            Write-Status "vectorbt - MISSING (optional for scan)" "WARN"
        }
    }
    "help" {
        Write-Host @"

  ╔═══════════════════════════════════════════════════════════════╗
  ║          ALPHAFACTORY v4.3 - EA DEVELOPMENT CLI              ║
  ╚═══════════════════════════════════════════════════════════════╝

  CORE COMMANDS:
  ─────────────────────────────────────────────────────────────────
  status                    System overview, list EAs
  compile "EA Name"         Compile EA with MetaEditor
  backtest "EA Name"        Full MT5 backtest + auto-analysis
  list                      List all available EAs
  clean                     Dry-run post-run hygiene (safe default)
  clean -Execute            Delete staging/locks/compile logs; keep runs/
  clean journals            Dry-run scoped journal rotate (not Tester tree)
  clean journals -Execute   Rotate old scoped journals; refuses if MT5 running

  ANALYSIS COMMANDS:
  ─────────────────────────────────────────────────────────────────
  analyze -Report "path"    Full analysis of backtest report
  validate-full -Report "p" ALL gates parallel (analyze+equity+MC+WFA+robust)
  fast-kill -Packet "p"    Lean hash-bound closeout for an early-killed cell
  delivery -Packet "p"     Heavy survivor logic/run/log/chart completion gate
  scan                      Diagnostic VectorBT scan; not MT5 acceptance
  monte -Report "path"      Monte Carlo simulation (1000 runs)
  wfa -Report "path"        Walk-Forward Analysis (5 windows)
  robust -Report "path"     Robustness Suite (7 tests)
  param -Report "opt.xml"  Diagnostic full-pass DSR + real parameter surface
  cpcv -Report "events.csv" Diagnostic purged combinatorial split/PBO
  impact -Report "fills.csv" -TradesCsv "trades.csv" Diagnostic cost audit

  GIT COMMANDS:
  ─────────────────────────────────────────────────────────────────
  git                       Show git status

  UTILITY:
  ─────────────────────────────────────────────────────────────────
  validate                  Check Python dependencies
  mt5data                   Diagnostic native export; not acceptance
  help                      Show this help

  PARAMETERS:
  ─────────────────────────────────────────────────────────────────
  -Symbol     Trading symbol (default: XAUUSD)
  -Period     Timeframe (default: M15)
  -From       Backtest start date (default: 2020.01.01)
  -To         Backtest end date (default: 2025.12.25)
  -Charts     Equity/hour heatmap; on analyze also per-trade entry/exit PNGs
  -TradeCharts Per-trade entry (asof) + exit (SL/TP) PNGs; fail-open
  -Report     Path to HTML report file
  -Packet     Action-specific hash-bound packet/receipt
  -Output     Explicit analysis output directory
  -Param1/2   Actual MT5 optimization input columns
  -ExpectedTrials  Frozen total optimization pass count
  -SharpeColumn    Per-pass per_trade_net_r Sharpe column
  -LowerIsBetter   Select low metric values for the surface

  EXAMPLES:
  ─────────────────────────────────────────────────────────────────
  .\alpha.ps1 compile "EA_SMC_Confluence"
  .\alpha.ps1 backtest "EA_SMC_Confluence" -Symbol XAUUSD -Period M15
  .\alpha.ps1 clean
  .\alpha.ps1 clean -Execute
  .\alpha.ps1 analyze -Report "runs/test/report.html" -Charts
  .\alpha.ps1 analyze -Report "runs/EA_NAME/RUN_ID/report.html" -TradeCharts
  .\alpha.ps1 fast-kill -Packet "03. EA Developer/EA_Name/research/FAST_KILL_CLOSEOUT.json"
  .\alpha.ps1 delivery -Packet "03. EA Developer/EA_Name/research/EA_DELIVERY_PACKET.json"
  .\alpha.ps1 monte -Report "report.html"
  .\alpha.ps1 wfa -Report "report.html"

"@ -ForegroundColor Cyan
    }
    default { Show-Status }
}
