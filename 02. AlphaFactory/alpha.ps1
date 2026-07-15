<#
.SYNOPSIS
    AlphaFactory v4.2 - Centralized EA Development CLI
.DESCRIPTION
    Complete toolchain for MT5 EA development:
    - Compile, Backtest, Analyze EAs
    - Quick scan strategies with VectorBT
    - Monte Carlo & Walk-Forward validation
    - Git backup integration
.EXAMPLE
    .\alpha.ps1 status              # System status
    .\alpha.ps1 compile "EA Name"   # Compile EA
    .\alpha.ps1 backtest "EA Name"  # Full MT5 backtest
    .\alpha.ps1 analyze -Report "x" # Analyze report
    .\alpha.ps1 scan                # Quick VectorBT scan
    .\alpha.ps1 monte -Report "x"   # Monte Carlo simulation
    .\alpha.ps1 wfa -Report "x"     # Walk-Forward Analysis
    .\alpha.ps1 backup "message"    # Git commit + push
    .\alpha.ps1 help                # Show all commands
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("compile", "backtest", "analyze", "list", "status", "report", "git", "backup", "scan", "monte", "wfa", "help", "validate", "validate-full", "log", "robust", "param", "mt5data", "sensitivity")]
    [string]$Action = "status",
    
    [Parameter(Position=1)]
    [string]$Name = "",
    
    [string]$Report = "",
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
    [switch]$Charts
)

$ErrorActionPreference = "Stop"

# Config
$AdvisorsRoot = Split-Path -Parent $PSScriptRoot
$AlphaRoot = $PSScriptRoot
# Machine-specific MT5 paths live in alpha.local.ps1 (gitignored).
# Copy alpha.local.ps1.example or run: .\tools\init_machine_paths.ps1
$MT5InstallRoot = $null
$MT5DataRoot = $null
$script:Mt5ConfigSource = "unset"
$LocalConfigPath = Join-Path $AlphaRoot "alpha.local.ps1"
if (Test-Path -LiteralPath $LocalConfigPath -PathType Leaf) {
    . $LocalConfigPath
    $script:Mt5ConfigSource = "alpha.local.ps1"
}

function Resolve-Mt5InstallRoot {
    $candidates = @(
        "C:\Program Files\MetaTrader 5",
        "C:\Program Files (x86)\MetaTrader 5"
    )
    foreach ($root in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $root "terminal64.exe") -PathType Leaf) {
            return $root
        }
    }
    return $null
}

function Resolve-Mt5DataRoot([string]$InstallRoot) {
    $termRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    if (-not (Test-Path -LiteralPath $termRoot -PathType Container)) {
        return $null
    }
    $dirs = @(Get-ChildItem -LiteralPath $termRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[A-F0-9]{32}$' -and (Test-Path -LiteralPath (Join-Path $_.FullName "MQL5") -PathType Container) })
    if ($dirs.Count -eq 0) { return $null }
    if (-not [string]::IsNullOrWhiteSpace($InstallRoot)) {
        $matched = @($dirs | Where-Object {
            $origin = Join-Path $_.FullName "origin.txt"
            if (-not (Test-Path -LiteralPath $origin -PathType Leaf)) { return $false }
            $originVal = (Get-Content -LiteralPath $origin -Raw).Trim()
            return ($originVal -ieq $InstallRoot)
        })
        if ($matched.Count -eq 1) { return $matched[0].FullName }
        if ($matched.Count -gt 1) { return $matched[0].FullName }
    }
    if ($dirs.Count -gt 1) {
        Write-Host "[WARN] Multiple MT5 terminal data folders found; using first. Pin the correct one in alpha.local.ps1." -ForegroundColor Yellow
    }
    return $dirs[0].FullName
}

if ([string]::IsNullOrWhiteSpace($MT5InstallRoot)) {
    $MT5InstallRoot = Resolve-Mt5InstallRoot
    if ($script:Mt5ConfigSource -eq "unset") { $script:Mt5ConfigSource = "auto-detect" }
    elseif ($script:Mt5ConfigSource -eq "alpha.local.ps1") { $script:Mt5ConfigSource = "alpha.local.ps1+auto-detect" }
}
if ([string]::IsNullOrWhiteSpace($MT5DataRoot)) {
    $MT5DataRoot = Resolve-Mt5DataRoot $MT5InstallRoot
    if ($script:Mt5ConfigSource -eq "unset") { $script:Mt5ConfigSource = "auto-detect" }
    elseif ($script:Mt5ConfigSource -eq "alpha.local.ps1") { $script:Mt5ConfigSource = "alpha.local.ps1+auto-detect" }
}

if ([string]::IsNullOrWhiteSpace($MT5InstallRoot) -or -not (Test-Path -LiteralPath (Join-Path $MT5InstallRoot "terminal64.exe") -PathType Leaf)) {
    throw "MT5 install root not found. Create machine config: copy '02. AlphaFactory/alpha.local.ps1.example' to 'alpha.local.ps1' (or run tools\init_machine_paths.ps1) and set `$MT5InstallRoot."
}
if ([string]::IsNullOrWhiteSpace($MT5DataRoot) -or -not (Test-Path -LiteralPath (Join-Path $MT5DataRoot "MQL5") -PathType Container)) {
    throw "MT5 data root not found. Create machine config: copy '02. AlphaFactory/alpha.local.ps1.example' to 'alpha.local.ps1' (or run tools\init_machine_paths.ps1) and set `$MT5DataRoot to the Terminal\<32-hex>\ folder."
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

function Get-RequiredSidecarsForTier([string]$Tier) {
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

function ConvertTo-RequiredSidecarList([string]$Value, [string]$Tier) {
    $requested = @($Value -split ';' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($requested.Count -ne (@($requested | Select-Object -Unique)).Count) {
        throw "RequiredSidecars contains duplicate patterns."
    }
    foreach ($pattern in $requested) {
        if ($pattern -notmatch '^[A-Za-z0-9_.?*-]+$' -or $pattern -match '\.\.') {
            throw "Required sidecar pattern is unsafe: $pattern"
        }
    }
    foreach ($minimum in (Get-RequiredSidecarsForTier $Tier)) {
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
    if (-not $current.WaitForExit(5000)) {
        throw "Runner-owned terminal64 PID $ProcessId did not exit after a verified stop request; ownership is retained."
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

function Assert-NoUnrelatedTerminal {
    $unrelated = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Where-Object {
        (-not $script:OwnedTerminalIdentities.ContainsKey([int]$_.Id)) -or
            (-not (Test-RunnerOwnedTerminalIdentity ([int]$_.Id) $script:OwnedTerminalIdentities[[int]$_.Id]))
    })
    if ($unrelated.Count -gt 0) {
        $unrelatedPids = ($unrelated | ForEach-Object { $_.Id }) -join ","
        throw "Unrelated terminal64 process already running (PID(s): $unrelatedPids). Backtest failed closed; no process was stopped."
    }
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
	# Tìm tất cả thư mục chứa file .mq5 (EA roots), bao gồm cả trong subfolders
	# Loại bỏ các thư mục hệ thống/toolchain
	$excludeNames = @("02. AlphaFactory", "01. vectorbt", "AlphaFactory", "vectorbt", ".windsurf")
	
	$eaDirs = Get-ChildItem -Path $AdvisorsRoot -Directory -Recurse | Where-Object {
	    $_.Name -notin $excludeNames -and
	    (Get-ChildItem -Path $_.FullName -Filter "*.mq5" -File -ErrorAction SilentlyContinue)
	}
	
	return $eaDirs
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
    if ([string]$receipt.schema_version -cne 'sonic_execution_receipt.v1') {
        throw "Contract receipt schema_version must be 'sonic_execution_receipt.v1'."
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
    $includeEvidence = @($receipt.evidence | Where-Object { [string]$_.label -like 'include_*' })
    if ($includeEvidence.Count -eq 0) {
        throw "Contract receipt is missing packet-bound include closure evidence."
    }
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

function Get-ReportIdentity($ReportPath, $Manifest) {
    $html = Get-Content -LiteralPath $ReportPath -Raw
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

    $identity = Get-ReportIdentity ([string]$manifest.report_path) $manifest
    $manifest.broker_fingerprint = $identity.BrokerFingerprint
    $manifest.server_fingerprint = $identity.ServerFingerprint
    $manifest.account_fingerprint = $identity.AccountFingerprint
    $manifest.data_fingerprint = $identity.DataFingerprint
    $manifest.sidecars = @($sidecars)
    $manifest | Add-Member -MemberType NoteProperty -Name fingerprint_basis -Value $identity.Basis -Force
    $manifest.generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    Write-JsonAtomically $manifest $ManifestPath 16
    return $ManifestPath
}

function Write-RunManifest($RunDir, $RunId, $EAName, $Sym, $Per, $FromD, $ToD, $Model, $ExecutionMode, $FixedDelayMs, $TimeoutSec, $Overrides, $MainFile, $CompiledEx5File, $Ex5File, $ReportPath, $ConfigPath, $Snapshot, $HypothesisId, $RunRole, $Deposit, $Leverage, $Spread, $TelemetryTier, $RunStartUtc, $GitSnapshot, $RequiredSidecarList, $ReceiptSha256, $SymbolGeometry) {
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
        required_sidecars = @($RequiredSidecarList)
        sidecars = @()
        contract_receipt_sha256 = $ReceiptSha256
        contract_symbol_geometry = [ordered]@{
            digits = [int]$SymbolGeometry.digits
            point = [double]$SymbolGeometry.point
            pip_size = [double]$SymbolGeometry.pip_size
        }
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
    
    $compileArgs = "/compile:`"$main`" /log:`"$log`""
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

    Write-Status "SUCCESS: $($artifact.Length) bytes (MetaEditor exit $($compiler.ExitCode), log 0 errors)" "OK"
    return $ex5
}

function Do-Backtest($EAName, $Sym, $Per, $FromD, $ToD, $TimeoutSec, $Overrides = "", $Model = 0, $ExecutionMode = 0, $FixedDelayMs = 0, $Spread = "", $HypothesisId = "", $RunRole = "challenger", $TelemetryTier = "off", $Deposit = 10000, $Leverage = 100, $ContractReceiptPath = "", $ExpectedReceiptSha256 = "", $RequiredSidecarPatterns = "") {
    Write-Status "Backtest: $EAName on $Sym $Per"
    $testerExecutionMode = if ($ExecutionMode -gt 0) { $ExecutionMode } elseif ($FixedDelayMs -gt 0) { $FixedDelayMs } else { $ExecutionMode }
    
    $sourceContract = Resolve-EaSourceContract -RepoRoot $AdvisorsRoot -EaName $EAName
    $main = $sourceContract.AbsoluteSource
    $effectiveOverrides = Resolve-TelemetryTierOverrides $TelemetryTier $main $Overrides $sourceContract.TelemetryProfile
    $requiredSidecarList = ConvertTo-RequiredSidecarList $RequiredSidecarPatterns $TelemetryTier
    $effectiveSpread = if ([string]::IsNullOrWhiteSpace($Spread)) { 'current' } else { $Spread }
    $receiptBinding = [pscustomobject]@{
        hypothesis_id = $HypothesisId; run_role = $RunRole; ea_name = $EAName; symbol = $Sym; period = $Per
        from = $FromD; to = $ToD; model = $Model; execution_mode = $ExecutionMode
        fixed_delay_ms = $FixedDelayMs; overrides = $effectiveOverrides; telemetry_tier = $TelemetryTier
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
"@

    if ($Spread) {
        $iniContent += "`r`nSpread=$Spread"
    }

    # v11.3: ALWAYS write [TesterInputs] to override MT5 cached .set files
    # Without this, MT5 ignores compiled defaults and uses stale cached params
    $iniContent += "`r`n[TesterInputs]`r`n"
    if ($effectiveOverrides) {
        $pairs = $effectiveOverrides.Split(';') | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_.Contains('=') }
        foreach ($p in $pairs) {
            $kv = $p.Split('=', 2)
            $k = $kv[0].Trim()
            $v = $kv[1].Trim()
            if ($k) {
                $iniContent += "$k=$v||$v||0||$v||N`r`n"
            }
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
    Write-Status "Starting MT5..."
    $mt5Process = Start-Process -FilePath $MT5 -ArgumentList "/config:`"$iniPath`"" -WorkingDirectory $localRunDir -PassThru
    $mt5Pid = $mt5Process.Id
    Register-RunnerOwnedTerminal $mt5Pid
    Write-Status "MT5 started (PID: $mt5Pid)"
    
    # v11.0 Fix: Wait loop - check report BEFORE process status
    # With ShutdownTerminal=1, MT5 writes report then exits. If MT5 exits quickly,
    # we must check the report file first to avoid false failure detection.
    $timeout = [Math]::Max(60, $TimeoutSec)
    $reportFound = $false
    for ($i = 0; $i -lt $timeout; $i += 5) {
        Start-Sleep -Seconds 5
        
        # v11.0: Check report existence FIRST (before process status)
        if ((Test-PathSafe $reportAbsPath) -and ((Get-FileLengthSafe $reportAbsPath) -gt 1000)) {
            $reportFound = $true
            break
        }
        
        # Only the PID returned by Start-Process is runner-owned.
        $mt5Running = Get-Process -Id $mt5Pid -ErrorAction SilentlyContinue
        if (-not $mt5Running) {
            # v14.0: Extended grace period + retry loop for report flush after MT5 exit
            # MT5 build 5679+ may need longer to finalize report file on disk
            for ($grace = 1; $grace -le 6; $grace++) {
                Start-Sleep -Seconds 5
                if ((Test-PathSafe $reportAbsPath) -and ((Get-FileLengthSafe $reportAbsPath) -gt 1000)) {
                    $reportFound = $true
                    break
                }
                Write-Status "Waiting for report flush... ($($grace * 5)s)" "INFO"
            }
            if ($reportFound) { break }

            # v14.0: Last resort - relaunch MT5 briefly to force report generation.
            # Refuse if another terminal appeared; it is not runner-owned.
            $unexpectedTerminals = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
            if ($unexpectedTerminals.Count -gt 0) {
                $unexpectedPids = ($unexpectedTerminals | ForEach-Object { $_.Id }) -join ","
                throw "Backtest failed: unrelated terminal64 process appeared during report flush (PID(s): $unexpectedPids)."
            }
            Write-Status "Report not flushed. Relaunching MT5 to force report export..." "WARN"
            $mt5Relaunch = Start-Process -FilePath $MT5 -ArgumentList "/config:`"$iniPath`"" -WorkingDirectory $localRunDir -PassThru
            Register-RunnerOwnedTerminal $mt5Relaunch.Id
            for ($retry = 1; $retry -le 12; $retry++) {
                Start-Sleep -Seconds 5
                if ((Test-PathSafe $reportAbsPath) -and ((Get-FileLengthSafe $reportAbsPath) -gt 1000)) {
                    $reportFound = $true
                    break
                }
                Write-Status "Waiting for report (relaunch $retry/12)..." "INFO"
            }
            # Stop only the PID created and registered by this invocation.
            Stop-RunnerOwnedTerminal $mt5Relaunch.Id
            Start-Sleep -Seconds 2
            if ($reportFound) { break }

            throw "Backtest failed: MT5 PID $mt5Pid exited without producing report. Config: $iniPath"
        }
        
        if ($i % 30 -eq 0) { Write-Status "Waiting... ($i s)" }
    }
    
    if (-not $reportFound) {
        Stop-RunnerOwnedTerminal $mt5Pid
        throw "Backtest failed: timeout after ${timeout}s. Config: $iniPath"
    }

    # Freeze process-owned output before collecting evidence. PID ownership is
    # checked against PID + start time + executable before any stop request.
    Stop-RunnerOwnedTerminal $mt5Pid
    if ((Get-Sha256Required $stagedEx5Path "Staged EX5") -ine $stagedEx5Hash) {
        throw "Staged EX5 changed during MT5 execution."
    }
    
    # --- Report found - process results ---
    Write-Status "Report ready!" "OK"
    $localReportPath = Join-Path $localRunDir "report.html"
    Copy-Item $reportAbsPath $localReportPath -Force
    Copy-Item $reportAbsPath (Join-Path $buildDir "report.html") -Force
    Copy-Item $iniPath (Join-Path $localRunDir "config.ini") -Force
    Copy-Item $iniPath (Join-Path $configDir "config.ini") -Force
    $manifestPath = Write-RunManifest -RunDir $localRunDir -RunId $ts -EAName $EAName -Sym $Sym -Per $Per -FromD $FromD -ToD $ToD -Model $Model -ExecutionMode $ExecutionMode -FixedDelayMs $FixedDelayMs -TimeoutSec $TimeoutSec -Overrides $effectiveOverrides -MainFile $main -CompiledEx5File $ex5 -Ex5File $stagedEx5Path -ReportPath $localReportPath -ConfigPath $iniPath -Snapshot $snapshot -HypothesisId $HypothesisId -RunRole $RunRole -Deposit $Deposit -Leverage $Leverage -Spread $Spread -TelemetryTier $TelemetryTier -RunStartUtc $runStartUtc -GitSnapshot $receiptCheck.Git -RequiredSidecarList $requiredSidecarList -ReceiptSha256 $receiptCheck.ReceiptSha256 -SymbolGeometry $receiptCheck.Receipt.binding.symbol_geometry
    Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $configDir "run_manifest.json") -Force

    if ($effectiveOverrides) {
        $effectiveOverrides | Set-Content (Join-Path $localRunDir "overrides.txt") -Encoding UTF8
        $effectiveOverrides | Set-Content (Join-Path $configDir "overrides.txt") -Encoding UTF8
    }

    $terminalData = Split-Path -Parent $mql5Root
    $terminalRoot = Split-Path -Parent $terminalData
    $commonFilesDir = Join-Path $terminalRoot "Common\Files"
    if (Test-PathSafe $commonFilesDir) {
        try {
            $patterns = @("${Sym}_*Signals_*.csv", "${Sym}_*Trades_*.csv", "${Sym}_*PX6_*.csv", "${Sym}_*Ghost_*.csv", "${Sym}_*Shadow_*.csv", "${Sym}_*Observers_*.csv", "${Sym}_*Activity_*.csv", "${Sym}_*EngineAudit_*.csv", "${Sym}_*PVSRA_SR_*.csv", "${Sym}_*Opportunities_*.csv", "${Sym}_*Regime_*.csv", "${Sym}_*StateTelemetry_*.csv", "${Sym}_*FxClassicNearMiss_*.csv", "${Sym}_*GoldRegimeContext_*.csv", "${Sym}_*RunMeta_*.json")
            foreach ($pat in $patterns) {
                Get-ChildItem -Path $commonFilesDir -Filter $pat -File -ErrorAction SilentlyContinue |
                    Where-Object { $_.LastWriteTimeUtc -ge $runStartUtc } | ForEach-Object {
                        $mirrorReceipt = Copy-AlphaLogWithMirror `
                            -Source $_.FullName `
                            -PrimaryDirectory $logsDir `
                            -MirrorDirectory $analysisLogsDir
                        if ($mirrorReceipt.mode -eq 'copy_fallback') {
                            Write-Status "Hardlink unavailable; retained physical log mirror for $($_.Name)" "WARN"
                        }
                    }
            }
        } catch {
            Write-Status "Skip Common\\Files copy (access denied): $commonFilesDir" "WARN"
        }
    }

    Complete-RunManifest $manifestPath | Out-Null
    Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $configDir "run_manifest.json") -Force

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
    Write-Status "Backtest complete: $localRunDir" "OK"
    Write-Output "ALPHA_RUN_DIR=$localRunDir"
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

function Show-Status {
    Write-Host "`n==============================" -ForegroundColor Cyan
    Write-Host "  ALPHAFACTORY" -ForegroundColor Cyan
    Write-Host "==============================`n" -ForegroundColor Cyan
    
    # MT5 status
    $mt5On = Get-Process terminal64 -ErrorAction SilentlyContinue
    Write-Host "MT5: $(if ($mt5On) { 'RUNNING' } else { 'STOPPED' })" -ForegroundColor $(if ($mt5On) { "Green" } else { "Yellow" })
    Write-Host "Config source: $script:Mt5ConfigSource" -ForegroundColor DarkGray
    Write-Host "Install: $MT5InstallRoot"
    Write-Host "Data:    $MT5DataRoot"
    Write-Host "Editor:  $MetaEditor"
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
    Write-Host "  .\tools\init_machine_paths.ps1   # generate alpha.local.ps1"
    Write-Host ""
}

# Main
Write-Host "`n  ALPHAFACTORY v4.2`n" -ForegroundColor Cyan

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
    # Auto-logs results to STRATEGY_LOG.md
    # ================================================================
    "analyze" { 
        if (-not $Report) { throw "Report path required" }
        Do-Analyze $Report 
    }
    "git" {
        & "$AlphaRoot\tools\git_sync.ps1" status
    }
    # ================================================================
    # BACKUP - Git commit + push to GitHub
    # Luôn backup sau mỗi thay đổi quan trọng
    # ================================================================
    "backup" {
        $msg = if ($Name) { $Name } else { "Auto backup: $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
        Push-Location $AdvisorsRoot
        git add -A
        git commit -m $msg
        $remote = git remote -v 2>$null
        if ($remote) { git push origin main }
        Pop-Location
        Write-Status "Backup complete!" "OK"
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
    # PARAM - Parameter Sensitivity Analysis & Heatmap
    # Kiểm tra stability của parameters
    # ================================================================
    "param" {
        if (-not $Report) { throw "Report path required. Use: .\alpha.ps1 param -Report 'path'" }
        Write-Status "Running Parameter Sensitivity Analysis..."
        $param = Join-Path $AlphaRoot "analysis\param_optimizer.py"
        if ($Name -eq "heatmap") {
            python $param --report "$Report" --heatmap
        } else {
            python $param --report "$Report" --param "SL"
        }
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
  ║          ALPHAFACTORY v4.2 - EA DEVELOPMENT CLI              ║
  ╚═══════════════════════════════════════════════════════════════╝

  CORE COMMANDS:
  ─────────────────────────────────────────────────────────────────
  status                    System overview, list EAs
  compile "EA Name"         Compile EA with MetaEditor
  backtest "EA Name"        Full MT5 backtest + auto-analysis
  list                      List all available EAs

  ANALYSIS COMMANDS:
  ─────────────────────────────────────────────────────────────────
  analyze -Report "path"    Full analysis of backtest report
  validate-full -Report "p" ALL gates parallel (analyze+equity+MC+WFA+robust)
  scan                      Quick VectorBT strategy scan (all)
  scan "sma"               Scan specific strategy (sma/ema/rsi/macd)
  monte -Report "path"      Monte Carlo simulation (1000 runs)
  wfa -Report "path"        Walk-Forward Analysis (5 windows)
  robust -Report "path"     Robustness Suite (7 tests)

  GIT COMMANDS:
  ─────────────────────────────────────────────────────────────────
  git                       Show git status
  backup                    Auto commit + push to GitHub
  backup "message"          Commit with custom message

  UTILITY:
  ─────────────────────────────────────────────────────────────────
  validate                  Check Python dependencies
  help                      Show this help

  PARAMETERS:
  ─────────────────────────────────────────────────────────────────
  -Symbol     Trading symbol (default: XAUUSD)
  -Period     Timeframe (default: M15)
  -From       Backtest start date (default: 2020.01.01)
  -To         Backtest end date (default: 2025.12.25)
  -Charts     Generate visual charts
  -Report     Path to HTML report file

  EXAMPLES:
  ─────────────────────────────────────────────────────────────────
  .\alpha.ps1 compile "EA_SMC_Confluence"
  .\alpha.ps1 backtest "EA_SMC_Confluence" -Symbol XAUUSD -Period M15
  .\alpha.ps1 analyze -Report "runs/test/report.html" -Charts
  .\alpha.ps1 monte -Report "report.html"
  .\alpha.ps1 wfa -Report "report.html"
  .\alpha.ps1 backup "Fixed entry logic"

"@ -ForegroundColor Cyan
    }
    default { Show-Status }
}
