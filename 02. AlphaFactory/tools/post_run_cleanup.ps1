<#
.SYNOPSIS
    Fail-closed post-run hygiene for AlphaFactory staging, locks, and compile logs.
.DESCRIPTION
    Default is dry-run. -Execute deletes only contract-scoped leftovers after
    evidence is already in 02. AlphaFactory/runs/<EA>/<run_id>/. Never touches
    bases/, cache/, .hcc, canonical runs, or 00. Old File/.

    Scopes:
      safe     - AlphaTester, AlphaRuns copies, staged EX5, compile logs, orphan locks
      journals - scoped MT5/Tester/Agent logs directories only (never Tester tree)
      all      - safe + journals
#>
param(
    [switch]$Execute,
    [ValidateSet('safe', 'journals', 'all')]
    [string]$Scope = 'safe',
    [string]$EaName = '',
    [string]$RunId = '',
    [ValidateRange(0, 8760)]
    [int]$MinAgeHours = 1,
    [string]$RepoRoot = '',
    [string]$DataRoot = '',
    [string]$TesterRoot = '',
    [string]$PlanPath = ''
)

Set-StrictMode -Off
$ErrorActionPreference = 'Stop'

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $alphaRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd([char[]]'\/')
$alphaRoot = Join-Path $RepoRoot '02. AlphaFactory'
$runtimeRoot = Join-Path $alphaRoot 'runtime'
$runsRoot = Join-Path $alphaRoot 'runs'
$eaRoot = Join-Path $RepoRoot '03. EA Developer'
$alphaTesterRoot = Join-Path $RepoRoot 'AlphaTester'
$timestampPattern = '^\d{8}_\d{6}$'
$cutoff = [datetime]::UtcNow.AddHours(-1 * $MinAgeHours)

if (Test-Path -LiteralPath (Join-Path $alphaRoot 'alpha.local.ps1') -PathType Leaf) {
    . (Join-Path $alphaRoot 'alpha.local.ps1')
}
if ([string]::IsNullOrWhiteSpace($DataRoot) -and (Get-Variable -Name MT5DataRoot -ErrorAction SilentlyContinue)) {
    $DataRoot = [string]$MT5DataRoot
}
if ([string]::IsNullOrWhiteSpace($TesterRoot) -and (Get-Variable -Name MT5TesterRoot -ErrorAction SilentlyContinue)) {
    $TesterRoot = [string]$MT5TesterRoot
}
if ([string]::IsNullOrWhiteSpace($TesterRoot) -and -not [string]::IsNullOrWhiteSpace($DataRoot)) {
    $TesterRoot = Join-Path $DataRoot 'Tester'
}

$contractPath = Join-Path $toolsRoot 'mt5_storage_contract.ps1'
if (Test-Path -LiteralPath $contractPath -PathType Leaf) {
    . $contractPath
}

function Write-Status($Message, $Type = 'INFO') {
    $color = switch ($Type) {
        'OK' { 'Green' }
        'WARN' { 'Yellow' }
        'ERR' { 'Red' }
        default { 'Cyan' }
    }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Test-PathUnderRoot([string]$Path, [string]$Root) {
    if ([string]::IsNullOrWhiteSpace($Path) -or [string]::IsNullOrWhiteSpace($Root)) { return $false }
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]'\/')
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    if ($fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    return $fullPath.StartsWith(
        $fullRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Test-ForbiddenCleanupPath([string]$Path) {
    $normalized = $Path.Replace('/', '\')
    if ($normalized -match '(?i)\\bases(\\|$)') { return $true }
    if ($normalized -match '(?i)\\cache(\\|$)') { return $true }
    if ($normalized -match '(?i)\.hcc$') { return $true }
    if ($normalized -match '(?i)\\00\. Old File(\\|$)') { return $true }
    if (Test-PathUnderRoot $Path $runsRoot) { return $true }
    return $false
}

function Assert-PathUnderAnyRoot([string]$Path, [string[]]$Roots, [string]$Label) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (Test-ForbiddenCleanupPath $full) {
        throw "$Label is forbidden by cleanup contract: $full"
    }
    foreach ($root in @($Roots | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })) {
        if (Test-PathUnderRoot $full $root) { return $full }
    }
    throw "$Label escapes cleanup contract: $full"
}

function Assert-PinnedOrRepoPath([string]$Path, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    $full = [System.IO.Path]::GetFullPath($Path)
    if (Test-PathUnderRoot $full $RepoRoot) { return }
    throw "$Label must stay under the repo or a pinned portable root: $full"
}

function Get-ItemSizeBytes([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return 0L }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) { return [int64]$item.Length }
    $measured = Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum
    if ($null -eq $measured) { return 0L }
    $sumProperty = $measured.PSObject.Properties['Sum']
    if ($null -eq $sumProperty -or $null -eq $sumProperty.Value) { return 0L }
    return [int64]$sumProperty.Value
}

function New-Candidate([string]$Kind, [string]$Path, [string]$AllowedRoot) {
    $safe = Assert-PathUnderAnyRoot $Path @($AllowedRoot) $Kind
    $item = Get-Item -LiteralPath $safe -Force
    $rel = if (Test-PathUnderRoot $safe $RepoRoot) {
        $safe.Substring($RepoRoot.Length).TrimStart('\')
    } else {
        $item.Name
    }
    return [pscustomobject][ordered]@{
        Kind = $Kind
        Path = $safe
        Relative = $rel
        SizeBytes = Get-ItemSizeBytes $safe
        IsContainer = [bool]$item.PSIsContainer
        ExecuteEligible = $true
    }
}

function Test-TimestampName([string]$Name) {
    return $Name -match $timestampPattern
}

function Test-AgeOrRunMatch([string]$Name, [datetime]$LastWriteUtc) {
    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        return $Name -eq $RunId
    }
    return $LastWriteUtc -le $cutoff
}

function Test-LockOrphan([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    $name = $item.Name
    if ($name -match '(?i)\.stale(\.|-)|stale-lock') { return $true }
    if ([int64]$item.Length -le 0) { return $true }
    try {
        $json = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop | ConvertFrom-Json
        $pidProperty = $json.PSObject.Properties['runner_pid']
        if ($null -eq $pidProperty) { return $true }
        $ownerPid = [int]$pidProperty.Value
        if ($ownerPid -le 0) { return $true }
        $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        return $null -eq $proc
    } catch {
        return $item.LastWriteTimeUtc -le $cutoff
    }
}

function Write-JsonAtomically($Value, [string]$Path, [int]$Depth = 6) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $parent = Split-Path -Parent $fullPath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $tempPath = Join-Path $parent ('.{0}.{1}.{2}.tmp' -f ([System.IO.Path]::GetFileName($fullPath)), $PID, ([guid]::NewGuid().ToString('N')))
    try {
        $Value | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $tempPath -Encoding UTF8
        Move-Item -LiteralPath $tempPath -Destination $fullPath -Force
    } finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
        }
    }
}

Assert-PinnedOrRepoPath $RepoRoot 'RepoRoot'
if (-not [string]::IsNullOrWhiteSpace($DataRoot)) { Assert-PinnedOrRepoPath $DataRoot 'DataRoot' }
if (-not [string]::IsNullOrWhiteSpace($TesterRoot)) { Assert-PinnedOrRepoPath $TesterRoot 'TesterRoot' }

$includeSafe = $Scope -in @('safe', 'all')
$includeJournals = $Scope -in @('journals', 'all')
$candidates = New-Object System.Collections.Generic.List[object]
$reclaimOnly = New-Object System.Collections.Generic.List[object]

if ($includeSafe) {
    if (Test-Path -LiteralPath $alphaTesterRoot -PathType Container) {
        Get-ChildItem -LiteralPath $alphaTesterRoot -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { (Test-TimestampName $_.Name) -and (Test-AgeOrRunMatch $_.Name $_.LastWriteTimeUtc) } |
            ForEach-Object { $candidates.Add((New-Candidate 'AlphaTesterStaging' $_.FullName $alphaTesterRoot)) }
    }

    if (-not [string]::IsNullOrWhiteSpace($DataRoot) -and (Test-Path -LiteralPath $DataRoot -PathType Container)) {
        $alphaRuns = Join-Path $DataRoot 'MQL5\Profiles\Tester\AlphaRuns'
        if (Test-Path -LiteralPath $alphaRuns -PathType Container) {
            Get-ChildItem -LiteralPath $alphaRuns -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { (Test-TimestampName $_.Name) -and (Test-AgeOrRunMatch $_.Name $_.LastWriteTimeUtc) } |
                ForEach-Object { $candidates.Add((New-Candidate 'AlphaRunsCopy' $_.FullName $alphaRuns)) }
        }

        $stagedRoot = Join-Path $DataRoot 'MQL5\Experts\AlphaFactoryRuns'
        if (Test-Path -LiteralPath $stagedRoot -PathType Container) {
            $eaDirs = @(Get-ChildItem -LiteralPath $stagedRoot -Directory -Force -ErrorAction SilentlyContinue)
            if (-not [string]::IsNullOrWhiteSpace($EaName)) {
                $eaDirs = @($eaDirs | Where-Object { $_.Name -eq $EaName })
            }
            foreach ($eaDir in $eaDirs) {
                Get-ChildItem -LiteralPath $eaDir.FullName -Directory -Force -ErrorAction SilentlyContinue |
                    Where-Object { (Test-TimestampName $_.Name) -and (Test-AgeOrRunMatch $_.Name $_.LastWriteTimeUtc) } |
                    ForEach-Object { $candidates.Add((New-Candidate 'StagedEx5' $_.FullName $stagedRoot)) }
            }
            Get-ChildItem -LiteralPath $stagedRoot -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { @(Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue).Count -eq 0 } |
                ForEach-Object { $candidates.Add((New-Candidate 'EmptyStagedParent' $_.FullName $stagedRoot)) }
        }

        Get-ChildItem -LiteralPath $DataRoot -File -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)compile.*\.log$' -and $_.LastWriteTimeUtc -le $cutoff } |
            ForEach-Object { $candidates.Add((New-Candidate 'PortableCompileLog' $_.FullName $DataRoot)) }
    }

    if (Test-Path -LiteralPath $eaRoot -PathType Container) {
        Get-ChildItem -LiteralPath $eaRoot -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like 'EA_*' } |
            ForEach-Object {
                $mq5 = Get-ChildItem -LiteralPath $_.FullName -File -Filter '*.mq5' -ErrorAction SilentlyContinue |
                    Select-Object -First 1
                if ($null -eq $mq5) { return }
                $log = [IO.Path]::ChangeExtension($mq5.FullName, '.log')
                if ((Test-Path -LiteralPath $log -PathType Leaf) -and ((Get-Item -LiteralPath $log).LastWriteTimeUtc -le $cutoff -or -not [string]::IsNullOrWhiteSpace($EaName))) {
                    if (-not [string]::IsNullOrWhiteSpace($EaName) -and $_.Name -ne $EaName) { return }
                    $candidates.Add((New-Candidate 'EaCompileLog' $log $_.FullName))
                }
            }
    }

    if (Test-Path -LiteralPath $runtimeRoot -PathType Container) {
        Get-ChildItem -LiteralPath $runtimeRoot -File -Force -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '(?i)(\.lock$|\.lock\.stale\.|stale-lock\.json$)' -and (Test-LockOrphan $_.FullName)
            } |
            ForEach-Object { $candidates.Add((New-Candidate 'OrphanLock' $_.FullName $runtimeRoot)) }
    }
}

if ($includeJournals) {
    if (Get-Command Get-Mt5JournalLogRoots -ErrorAction SilentlyContinue) {
        $journalRoots = @(Get-Mt5JournalLogRoots -DataRoot $DataRoot -TesterRoot $TesterRoot)
    } else {
        $journalRoots = @()
        foreach ($path in @((Join-Path $DataRoot 'logs'), (Join-Path $TesterRoot 'logs'))) {
            if (Test-Path -LiteralPath $path -PathType Container) { $journalRoots += ,([System.IO.Path]::GetFullPath($path)) }
        }
    }
    $terminalRunning = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    foreach ($journalRoot in $journalRoots) {
        Assert-PathUnderAnyRoot $journalRoot @($DataRoot, $TesterRoot) 'JournalRoot'
        $logs = @(Get-ChildItem -LiteralPath $journalRoot -File -Filter '*.log' -Force -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc)
        if ($logs.Count -eq 0) { continue }
        $newest = $logs[-1].FullName
        foreach ($log in $logs) {
            if ($log.FullName -eq $newest) { continue }
            if ($log.LastWriteTimeUtc -gt $cutoff) { continue }
            $row = New-Candidate 'JournalLog' $log.FullName $journalRoot
            if ($terminalRunning.Count -gt 0) {
                $row.ExecuteEligible = $false
            }
            $candidates.Add($row)
        }
    }
}

if ($includeSafe -and -not [string]::IsNullOrWhiteSpace($DataRoot)) {
    $dataParent = Split-Path -Parent $DataRoot
    $leftoverPortable = Join-Path $dataParent 'mt5-portable'
    if (($DataRoot -match 'fivepercent') -and (Test-Path -LiteralPath $leftoverPortable -PathType Container)) {
        $reclaimOnly.Add([pscustomobject][ordered]@{
            Kind = 'UnusedPortableTree'
            Relative = '02. AlphaFactory/runtime/mt5-portable'
            Note = 'Owner reclaim only. Default clean never deletes this tree or its bases/.'
            ExecuteEligible = $false
        })
    }
}

$eligible = @($candidates | Where-Object { $_.ExecuteEligible })
$totalBytes = ($eligible | Measure-Object SizeBytes -Sum).Sum
if ($null -eq $totalBytes) { $totalBytes = 0 }
$byKind = @($eligible | Group-Object Kind | ForEach-Object {
    [pscustomobject][ordered]@{
        kind = $_.Name
        count = $_.Count
        bytes = [int64](($_.Group | Measure-Object SizeBytes -Sum).Sum)
    }
})

$mode = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }
Write-Status "Mode: $mode  Scope: $Scope" $(if ($Execute) { 'WARN' } else { 'INFO' })
Write-Status ("Candidates: {0}  bytes: {1}" -f $eligible.Count, $totalBytes) 'INFO'
foreach ($row in $byKind) {
    Write-Status ("  {0}: {1} ({2} bytes)" -f $row.kind, $row.count, $row.bytes) 'INFO'
}
if ($reclaimOnly.Count -gt 0) {
    Write-Status ("Reclaim-only notes: {0} (not deleted by -Execute)" -f $reclaimOnly.Count) 'WARN'
    foreach ($note in $reclaimOnly) {
        Write-Status ("  {0}: {1}" -f $note.Kind, $note.Note) 'WARN'
    }
}

$planRoot = Join-Path $runtimeRoot 'cleanup_plans'
if ([string]::IsNullOrWhiteSpace($PlanPath)) {
    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        $PlanPath = Join-Path $planRoot 'post_run_cleanup_latest.json'
    } else {
        $PlanPath = Join-Path $planRoot ('post_run_cleanup_{0}.json' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    }
}
$PlanPath = Assert-PathUnderAnyRoot $PlanPath @($RepoRoot) 'PlanPath'
$modeName = 'dry_run'
if ($Execute) { $modeName = 'execute' }
$reclaimNotes = @()
foreach ($note in $reclaimOnly) {
    $reclaimNotes += [string]$note.Kind
}
$kindNames = @()
foreach ($row in $byKind) {
    $kindNames += ([string]$row.kind + '=' + [string]$row.count)
}
$plan = [ordered]@{}
$plan['schema_version'] = 'alphafactory_post_run_cleanup.v1'
$plan['created_at_utc'] = [datetime]::UtcNow.ToString('o')
$plan['mode'] = $modeName
$plan['scope'] = $Scope
$plan['ea_name'] = $EaName
$plan['run_id'] = $RunId
$plan['min_age_hours'] = $MinAgeHours
$plan['candidate_count'] = @($eligible).Count
$plan['total_size_bytes'] = [int64]$totalBytes
$plan['by_kind'] = ($kindNames -join ',')
$plan['reclaim_only'] = ($reclaimNotes -join ',')
Write-JsonAtomically $plan $PlanPath 6
Write-Status ("Plan: {0}" -f $PlanPath) 'OK'

if (-not $Execute) {
    Write-Status 'Dry-run only. Re-run with -Execute after reviewing kind counts.' 'OK'
    exit 0
}

if ($includeJournals -and (@(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue).Count -gt 0)) {
    $blocked = @($candidates | Where-Object { $_.Kind -eq 'JournalLog' -and -not $_.ExecuteEligible })
    if ($blocked.Count -gt 0) {
        throw 'Journal rotate refused while terminal64 is running.'
    }
}

$removed = 0
$removedBytes = 0L
foreach ($candidate in $eligible) {
    $safe = Assert-PathUnderAnyRoot $candidate.Path @(
        $alphaTesterRoot,
        $eaRoot,
        $runtimeRoot,
        $(if ($DataRoot) { $DataRoot } else { $RepoRoot }),
        $(if ($TesterRoot) { $TesterRoot } else { $RepoRoot })
    ) $candidate.Kind
    if ($candidate.IsContainer) {
        Remove-Item -LiteralPath $safe -Recurse -Force -ErrorAction Stop
    } else {
        Remove-Item -LiteralPath $safe -Force -ErrorAction Stop
    }
    $removed++
    $removedBytes += [int64]$candidate.SizeBytes
}

if ($includeSafe -and -not [string]::IsNullOrWhiteSpace($DataRoot)) {
    $stagedRoot = Join-Path $DataRoot 'MQL5\Experts\AlphaFactoryRuns'
    if (Test-Path -LiteralPath $stagedRoot -PathType Container) {
        Get-ChildItem -LiteralPath $stagedRoot -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { @(Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue).Count -eq 0 } |
            ForEach-Object {
                $safe = Assert-PathUnderAnyRoot $_.FullName @($stagedRoot) 'EmptyStagedParent'
                Remove-Item -LiteralPath $safe -Force -ErrorAction Stop
                $removed++
            }
    }
}

Write-Status ("Removed {0} item(s), {1} bytes" -f $removed, $removedBytes) 'OK'
exit 0
