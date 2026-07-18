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
$eaContractResolverPath = Join-Path $toolsRoot "ea_contract.ps1"
if (-not (Test-Path -LiteralPath $eaContractResolverPath -PathType Leaf)) {
    throw "EA source contract resolver is missing: $eaContractResolverPath"
}
. $eaContractResolverPath

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

function Get-ObjectProperty($Object, $Name) {
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
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
        AcceptanceContract = Get-ObjectProperty $latestRow 'acceptance_contract'
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
        SourceContractPinned = $sourceContract.IsPinned
    }
}

function Get-ResearchContractBlockers($Contract, $RequestedModel, $RequestedTelemetryTier) {
    $blockers = New-Object System.Collections.Generic.List[string]
    if ($Contract.RegistryState -in @('killed', 'parked')) {
        $blockers.Add("Latest registry row is terminal state '$($Contract.RegistryState)'; execution is rejected.")
    }
    if ($Contract.RegistryState -notin @('screened', 'challenger')) {
        $blockers.Add("Latest registry state '$($Contract.RegistryState)' is not execution-eligible; freeze the prereg and append state 'screened' before Model 0.")
    }
    if ($Contract.TelemetryProfile -ceq 'none') {
        $blockers.Add("EA has no AlphaFactory lifecycle telemetry contract; meaningful execution would fail verified-cost validation. Add ALPHAFACTORY_EA_CONTRACT.json and implement lifecycle-v3 telemetry before Model 0.")
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

function Resolve-TaskPacket($TaskPacketPath, $Contract, $Binding) {
    $blockers = New-Object System.Collections.Generic.List[string]
    $costEvidence = New-Object System.Collections.Generic.List[object]
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
            MatchedControlRunId = $null
            MatchedControl = $null
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
            MatchedControl = $null
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
            MatchedControl = $null
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
    Add-PacketMismatch $blockers $packet 'registry_sha256' $Contract.RegistrySha256 -Hash
    Add-PacketMismatch $blockers $packet 'registry_row_sha256' $Contract.RegistryRowSha256 -Hash
    Add-PacketMismatch $blockers $packet 'prereg_path' $Contract.RegisteredPreregPath
    Add-PacketMismatch $blockers $packet 'prereg_sha256' $Contract.PreregSha256 -Hash
    Add-PacketMismatch $blockers $packet 'telemetry_profile' $Contract.TelemetryProfile
    Add-PacketMismatch $blockers $packet 'comparison_adapter' $Contract.ComparisonAdapter
    $acceptanceFields = @(
        'min_profit_factor', 'min_trades_per_week', 'max_trades_per_week',
        'max_drawdown_pct', 'min_cost_pf_x1_5', 'min_cost_pf_x2',
        'max_monte_carlo_p95_dd_pct'
    )
    $packetAcceptance = Get-ObjectProperty $packet 'acceptance_contract'
    $registeredAcceptance = $Contract.AcceptanceContract
    if (-not (Test-ProvenanceObject $registeredAcceptance)) {
        $blockers.Add("Latest registry row has no structured acceptance_contract.")
    }
    if (-not (Test-ProvenanceObject $packetAcceptance)) {
        $blockers.Add("Task packet field 'acceptance_contract' is required and must be an object.")
    } else {
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
    Add-PacketMismatch $blockers $packet 'symbol' $Binding.Symbol
    Add-PacketMismatch $blockers $packet 'period' $Binding.Period
    Add-PacketMismatch $blockers $packet 'from' $Binding.From
    Add-PacketMismatch $blockers $packet 'to' $Binding.To
    Add-PacketMismatch $blockers $packet 'model' $Binding.Model -Integer
    Add-PacketMismatch $blockers $packet 'execution_mode' $Binding.ExecutionMode -Integer
    Add-PacketMismatch $blockers $packet 'fixed_delay_ms' $Binding.FixedDelayMs -Integer
    Add-PacketMismatch $blockers $packet 'overrides' $Binding.Overrides
    Add-PacketMismatch $blockers $packet 'telemetry_tier' $Binding.TelemetryTier
    Add-PacketMismatch $blockers $packet 'deposit' $Binding.Deposit -Integer
    Add-PacketMismatch $blockers $packet 'leverage' $Binding.Leverage -Integer
    Add-PacketMismatch $blockers $packet 'spread' $Binding.Spread
    Add-PacketMismatch $blockers $packet 'validation_stage' $Binding.ValidationStage
    Add-PacketMismatch $blockers $packet 'holding_contract' $Binding.HoldingContract
    Add-PacketMismatch $blockers $packet 'git_commit' $Binding.GitCommit
    Add-PacketMismatch $blockers $packet 'git_status_sha256' $Binding.GitStatusSha256 -Hash

    $packetGitStatusProperty = $packet.PSObject.Properties['git_status']
    if ($null -eq $packetGitStatusProperty) {
        $blockers.Add("Task packet field 'git_status' is required.")
    } else {
        $packetGitStatus = @($packetGitStatusProperty.Value | ForEach-Object { [string]$_ })
        if ([string]::Join("`n", $packetGitStatus) -cne [string]::Join("`n", @($Binding.GitStatus))) {
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
    if ([int]$Binding.Model -ne 0) {
        $blockers.Add("Strict challenger/confirmed research requires MT5 Model=0 (real ticks); got '$($Binding.Model)'.")
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
                if ($costFrom -cne $Binding.From -or $costTo -cne $Binding.To) {
                    $blockers.Add("Cost source manifest window '$costFrom' to '$costTo' does not match task packet window '$($Binding.From)' to '$($Binding.To)'.")
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
                        if ($coverageFrom -cne $Binding.From -or $coverageTo -cne $Binding.To) {
                            $blockers.Add("historical_spread_provenance.coverage window '$coverageFrom' to '$coverageTo' does not match task packet window '$($Binding.From)' to '$($Binding.To)'.")
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
                            $contractFromValid = $contractFrom -ceq $Binding.From
                            if (-not $contractFromValid) {
                                $blockers.Add("commission_provenance.broker_contract.from '$contractFrom' does not match task packet from '$($Binding.From)'.")
                            }
                            $contractTo = [string](Get-ObjectProperty $brokerContract 'to')
                            $contractToValid = $contractTo -ceq $Binding.To
                            if (-not $contractToValid) {
                                $blockers.Add("commission_provenance.broker_contract.to '$contractTo' does not match task packet to '$($Binding.To)'.")
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
        HoldingContract = $holdingContract
        AcceptanceContract = $registeredAcceptance
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

function New-ExecutionReceipt($ReceiptPath, $Contract, $PacketResult, $Binding) {
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
            model = $Binding.Model
            execution_mode = $Binding.ExecutionMode
            fixed_delay_ms = $Binding.FixedDelayMs
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
        }
        evidence = @($evidence | ForEach-Object { $_ })
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    Write-JsonAtomically $receipt $ReceiptPath 16
    return [pscustomobject]@{
        Path = (Resolve-Path -LiteralPath $ReceiptPath).Path
        Sha256 = Get-Sha256IfExists $ReceiptPath
        Receipt = $receipt
    }
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
        if ($field -in @('model', 'execution_mode', 'fixed_delay_ms', 'deposit', 'leverage')) {
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

if ([string]::IsNullOrWhiteSpace($EaName)) {
    throw "EaName is required before dry-run or execution."
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
}

$executionBlockers = New-Object System.Collections.Generic.List[string]
foreach ($blocker in (Get-ResearchContractBlockers $contract $Model $TelemetryTier)) { $executionBlockers.Add($blocker) }
$packetResult = Resolve-TaskPacket $TaskPacket $contract $binding
foreach ($blocker in $packetResult.Blockers) { $executionBlockers.Add([string]$blocker) }
if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
    $executionBlockers.Add("Unified validator is missing: $validatorPath")
}
if (-not (Test-Path -LiteralPath $costBuilderPath -PathType Leaf)) {
    $executionBlockers.Add("Verified cost builder is missing: $costBuilderPath")
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
    include_closure_sha256 = $packetResult.IncludeClosureSha256
    include_closure_count = @($packetResult.IncludeClosure | Where-Object { $null -ne $_ }).Count
    task_packet_path = $packetResult.PacketPath
    task_packet_sha256 = $packetResult.PacketSha256
    symbol = $Symbol
    period = $Period
    from = $From
    to = $To
    model = $Model
    execution_mode = $ExecutionMode
    fixed_delay_ms = $FixedDelayMs
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
    Enter-ImmutableEvidenceReadLocks $immutableEvidencePaths $evidenceReadLocks
    $existingTerminals = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
    if ($existingTerminals.Count -gt 0) {
        $terminalPids = ($existingTerminals | ForEach-Object { $_.Id }) -join ","
        throw "Unrelated terminal64 process already running (PID(s): $terminalPids). Research loop failed closed before backtest."
    }
    Add-StateTransition "execution_started" "Registry, source, prereg, task packet, and cost-source contract validated." | Out-Null

    $receiptPath = Join-Path $runtimeRoot "ea_execution_receipt_$sessionId.json"
    $receiptRecord = New-ExecutionReceipt $receiptPath $contract $packetResult $binding
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
    $nonRepaintArtifact = Join-Path $analysisDir 'nonrepaint_audit.json'
    [void](Invoke-RequiredStep "Non-repaint audit $runId" {
        & python $nonRepaintToolPath --manifest $runManifestPath --out $nonRepaintArtifact
    } $steps)
    if (-not (Test-Path -LiteralPath $nonRepaintArtifact -PathType Leaf)) {
        throw "Non-repaint auditor succeeded without creating: $nonRepaintArtifact"
    }
    try {
        $nonRepaintResult = Get-Content -LiteralPath $nonRepaintArtifact -Raw | ConvertFrom-Json
    } catch {
        throw "Non-repaint artifact is not valid JSON: $nonRepaintArtifact"
    }
    if ([string]$nonRepaintResult.schema_version -cne 'alphafactory_nonrepaint_audit.v1' -or
        [string]$nonRepaintResult.status -cne 'PASS' -or
        [string]$nonRepaintResult.run_id -cne $runId -or
        [string]$nonRepaintResult.hypothesis_id -cne $HypothesisId) {
        throw "Non-repaint audit identity/status contract failed for run '$runId'."
    }
    $evidence.nonrepaint_audit_path = $nonRepaintArtifact
    $evidence.nonrepaint_audit_sha256 = Get-Sha256IfExists $nonRepaintArtifact
    Add-StateTransition "nonrepaint_audit_passed" $nonRepaintArtifact | Out-Null

    $costArtifact = Join-Path $analysisDir "verified_cost_artifact.json"
    $costBuildArgs = @(
        $costBuilderPath,
        "--report", $report,
        "--cost-source-manifest", $packetResult.CostSourceManifestPath,
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
        Add-StateTransition "unified_research_validation_completed" ([string]$validationPayload.verdict) | Out-Null
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
    throw "Research loop failed: $failureMessage"
} finally {
    Exit-GlobalValidationLock $validationLock
    Exit-ImmutableEvidenceReadLocks $evidenceReadLocks
    Exit-ResearchLock $researchLock
}
