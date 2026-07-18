param(
    [string]$ArchiveRoot = "",
    [string]$CommonFilesRoot = "",
    [string]$EaName = "",
    [string[]]$KeepRunIds = @(
        "20260501_000718",
        "20260501_151422",
        "20260501_150910",
        "20260501_150443",
        "20260501_145948",
        "20260501_144350",
        "20260501_000635",
        "20260430_235840",
        "20260430_145740",
        "20260430_234940",
        "20260430_234854",
        "20260430_234641"
    ),
    [switch]$IncludeRuns,
    [switch]$IncludeCommonFiles,
    [switch]$IncludeRootSamples,
    [ValidateRange(0, 3650)][int]$MinAgeDays = 7,
    [ValidateRange(1, 500)][int]$ConsoleLimit = 50,
    [string]$PlanPath = "",
    [string[]]$ReferenceRoots = @(),
    [switch]$AllowSameVolumeArchive,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
$repoRoot = Split-Path -Parent $alphaRoot
if ([string]::IsNullOrWhiteSpace($CommonFilesRoot)) {
    $localConfigPath = Join-Path $alphaRoot 'alpha.local.ps1'
    if (Test-Path -LiteralPath $localConfigPath -PathType Leaf) {
        . $localConfigPath
        if (Get-Variable -Name MT5CommonFilesRoot -ErrorAction SilentlyContinue) {
            $CommonFilesRoot = [string]$MT5CommonFilesRoot
        }
    }
}
if ([string]::IsNullOrWhiteSpace($CommonFilesRoot) -and -not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
    $CommonFilesRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
}
$commonFilesRoot = $CommonFilesRoot

if ($ReferenceRoots.Count -eq 0) {
    $ReferenceRoots = @(
        (Join-Path $repoRoot '01. GOAL'),
        (Join-Path $repoRoot '04. Memory'),
        (Join-Path $repoRoot '05. Playbook'),
        (Join-Path $repoRoot '03. EA Developer'),
        (Join-Path $repoRoot 'INDEX.md'),
        (Join-Path $repoRoot 'AGENTS.md'),
        (Join-Path $repoRoot 'CLAUDE.md'),
        (Join-Path $alphaRoot 'STRATEGY_LOG.md'),
        (Join-Path $repoRoot '00. Old File\hot_details\hot_ledger_details.json')
    )
}

$commonFilesKeep = @(
    "SNR_FX_EVENTS.csv",
    "news_events.csv",
    "event_surprises.csv",
    "XSP_XAU_US_EVENTS.csv"
)

function Write-Status($Message, $Type = "INFO") {
    $color = switch ($Type) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERR" { "Red" }
        default { "Cyan" }
    }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Assert-PathUnderRoot($Path, $Root, $Label) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    if ($fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $fullPath
    }
    $prefix = $fullRoot + [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must stay under ${fullRoot}: $fullPath"
    }
    return $fullPath
}

function Write-JsonAtomically($Value, $Path, [int]$Depth = 8) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $parent = Split-Path -Parent $fullPath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $tempPath = Join-Path $parent (".{0}.{1}.{2}.tmp" -f ([System.IO.Path]::GetFileName($fullPath)), $PID, ([guid]::NewGuid().ToString('N')))
    try {
        $Value | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $tempPath -Encoding UTF8
        Move-Item -LiteralPath $tempPath -Destination $fullPath -Force
    } finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Resolve-DefaultArchiveRoot {
    if (-not [string]::IsNullOrWhiteSpace($ArchiveRoot)) {
        return $ArchiveRoot
    }

    $gRoot = "G:\"
    if (Test-Path -LiteralPath $gRoot) {
        $driveFolder = Get-ChildItem -LiteralPath $gRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "Drive*" } |
            Select-Object -First 1
        if ($driveFolder) {
            return $driveFolder.FullName
        }
    }

    return (Join-Path $repoRoot "_archive")
}

function Get-ItemSizeBytes($Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) {
        return [int64]$item.Length
    }
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum).Sum
    if ($null -eq $sum) {
        return 0
    }
    return [int64]$sum
}

function Assert-SourceAllowed($Path) {
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $allowedRoots = @($repoRoot, $commonFilesRoot) | Where-Object { Test-Path -LiteralPath $_ }
    foreach ($root in $allowedRoots) {
        $resolvedRoot = (Resolve-Path -LiteralPath $root).Path.TrimEnd([char[]]'\/')
        $rootPrefix = $resolvedRoot + [System.IO.Path]::DirectorySeparatorChar
        if ($resolved.Equals($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
            $resolved.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return
        }
    }
    throw "Refusing to archive source outside allowed roots: $resolved"
}

function New-ArchiveCandidate($Kind, $Source, $Destination) {
    $item = Get-Item -LiteralPath $Source -Force
    $fileCount = $(if ($item.PSIsContainer) {
        @(Get-ChildItem -LiteralPath $Source -Recurse -File -Force -ErrorAction SilentlyContinue).Count
    } else { 1 })
    [pscustomobject]@{
        Kind = $Kind
        Source = $Source
        Destination = $Destination
        SizeBytes = Get-ItemSizeBytes $Source
        FileCount = $fileCount
        SourceLastWriteUtc = $item.LastWriteTimeUtc.ToString('o')
    }
}

function Join-ArchivePath {
    param([Parameter(Mandatory = $true)][string[]]$Parts)
    return [IO.Path]::Combine($Parts)
}

function Get-ReferencedRunIds {
    $ids = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($root in $ReferenceRoots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $item = Get-Item -LiteralPath $root -Force
        $files = $(if ($item.PSIsContainer) {
            @(Get-ChildItem -LiteralPath $item.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension -in @('.md','.json','.jsonl','.txt') })
        } else { @($item) })
        foreach ($file in $files) {
            $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
            if ([string]::IsNullOrEmpty([string]$text)) { continue }
            foreach ($match in [regex]::Matches($text, '\b20\d{6}_\d{6}\b')) {
                [void]$ids.Add($match.Value)
            }
        }
    }
    return @($ids | Sort-Object)
}

function Get-ArchiveCandidates($SessionDir) {
    $items = New-Object System.Collections.Generic.List[object]

    if ($IncludeRootSamples) {
        foreach ($pattern in @("Expert*.mq5", "Expert*.ex5")) {
            Get-ChildItem -LiteralPath $repoRoot -Filter $pattern -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
                $dest = Join-ArchivePath @($SessionDir, 'root_samples', $_.Name)
                $items.Add((New-ArchiveCandidate "RootSample" $_.FullName $dest))
            }
        }
    }

    if ($IncludeCommonFiles -and (Test-Path -LiteralPath $commonFilesRoot)) {
        Get-ChildItem -LiteralPath $commonFilesRoot -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
            if (-not ($commonFilesKeep -contains $_.Name)) {
                $dest = Join-ArchivePath @($SessionDir, 'Common_Files', $_.Name)
                $items.Add((New-ArchiveCandidate "CommonFile" $_.FullName $dest))
            }
        }
        Get-ChildItem -LiteralPath $commonFilesRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $dest = Join-ArchivePath @($SessionDir, 'Common_Files', $_.Name)
            $items.Add((New-ArchiveCandidate "CommonDir" $_.FullName $dest))
        }
    }

    if ($IncludeRuns) {
        $allRunsRoot = Join-Path $alphaRoot 'runs'
        $cutoff = [datetime]::UtcNow.AddDays(-$MinAgeDays)
        $eaRoots = $(if ($EaName -eq '*') {
            @(Get-ChildItem -LiteralPath $allRunsRoot -Directory -Force -ErrorAction SilentlyContinue)
        } else {
            $exact = Join-Path $allRunsRoot $EaName
            if (Test-Path -LiteralPath $exact -PathType Container) { @(Get-Item -LiteralPath $exact) } else { @() }
        })
        foreach ($eaRoot in $eaRoots) {
            Get-ChildItem -LiteralPath $eaRoot.FullName -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
                if (-not ($script:EffectiveKeepRunIds -contains $_.Name) -and $_.LastWriteTimeUtc -le $cutoff) {
                    $dest = Join-ArchivePath @($SessionDir, 'AlphaFactory_runs', $eaRoot.Name, $_.Name)
                    $items.Add((New-ArchiveCandidate "RunFolder" $_.FullName $dest))
                }
            }
        }
    }

    return $items
}

function Get-CandidateFileInventory($Candidate) {
    $sourceItem = Get-Item -LiteralPath $Candidate.Source -Force
    $files = $(if ($sourceItem.PSIsContainer) {
        @(Get-ChildItem -LiteralPath $Candidate.Source -Recurse -File -Force | Sort-Object FullName)
    } else { @($sourceItem) })
    $sourcePrefix = $(if ($sourceItem.PSIsContainer) { $sourceItem.FullName.TrimEnd('\') + '\' } else { '' })
    return @($files | ForEach-Object {
        $relative = $(if ($sourceItem.PSIsContainer) { $_.FullName.Substring($sourcePrefix.Length).Replace('\','/') } else { '.' })
        [pscustomobject][ordered]@{
            relative_path = $relative
            size_bytes = [long]$_.Length
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
}

function Assert-CandidateCopy($Candidate, $Inventory) {
    $destinationItem = Get-Item -LiteralPath $Candidate.Destination -Force
    $actualFiles = $(if ($destinationItem.PSIsContainer) {
        @(Get-ChildItem -LiteralPath $Candidate.Destination -Recurse -File -Force)
    } else { @($destinationItem) })
    if ($actualFiles.Count -ne $Inventory.Count) {
        throw "Archive copy file-count mismatch: $($Candidate.Destination)"
    }
    foreach ($entry in $Inventory) {
        $target = $(if ($entry.relative_path -eq '.') { $Candidate.Destination } else { Join-Path $Candidate.Destination $entry.relative_path.Replace('/', '\') })
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Archive copy is missing: $target" }
        $item = Get-Item -LiteralPath $target
        $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ([long]$item.Length -ne [long]$entry.size_bytes -or $hash -ne [string]$entry.sha256) {
            throw "Archive copy hash/size mismatch: $target"
        }
    }
}

function CopyVerifyRemove-ArchiveCandidate($Candidate) {
    Assert-SourceAllowed $Candidate.Source
    $destParent = Split-Path -Parent $Candidate.Destination
    New-Item -ItemType Directory -Path $destParent -Force | Out-Null

    $target = $Candidate.Destination
    if (Test-Path -LiteralPath $target) {
        $suffix = Get-Date -Format "HHmmssfff"
        $target = "$target.$suffix"
    }
    $Candidate.Destination = $target
    $inventory = @(Get-CandidateFileInventory $Candidate)
    Copy-Item -LiteralPath $Candidate.Source -Destination $target -Recurse -Force
    try {
        Assert-CandidateCopy -Candidate $Candidate -Inventory $inventory
    } catch {
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
        throw
    }
    if ((Get-Item -LiteralPath $Candidate.Source -Force).PSIsContainer) {
        Remove-Item -LiteralPath $Candidate.Source -Recurse -Force
    } else {
        Remove-Item -LiteralPath $Candidate.Source -Force
    }
    $Candidate | Add-Member -NotePropertyName FileInventory -NotePropertyValue $inventory
}

function Format-Bytes($Bytes) {
    if ($Bytes -ge 1GB) {
        return ("{0:N2} GB" -f ($Bytes / 1GB))
    }
    if ($Bytes -ge 1MB) {
        return ("{0:N2} MB" -f ($Bytes / 1MB))
    }
    if ($Bytes -ge 1KB) {
        return ("{0:N2} KB" -f ($Bytes / 1KB))
    }
    return ("{0} B" -f $Bytes)
}

if (-not ($IncludeRuns -or $IncludeCommonFiles -or $IncludeRootSamples)) {
    Write-Status "No include switch was provided. Use -IncludeCommonFiles, -IncludeRuns, or -IncludeRootSamples." "WARN"
    return
}
if ($IncludeRuns -and [string]::IsNullOrWhiteSpace($EaName)) {
    throw "IncludeRuns requires an explicit -EaName (use '*' for inventory-only dry runs)."
}
if ($Execute -and $EaName -eq '*') {
    throw "Execute requires an exact -EaName. Use '*' for inventory/dry-run only."
}
$referencedRunIds = @(Get-ReferencedRunIds)
$script:EffectiveKeepRunIds = @($KeepRunIds + $referencedRunIds | Sort-Object -Unique)

$archiveBase = Resolve-DefaultArchiveRoot
$sessionName = "MT5_Backtest_Cleanup_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")
$sessionDir = Join-ArchivePath @($archiveBase, $sessionName)
$candidates = @(Get-ArchiveCandidates $sessionDir)
$totalBytes = ($candidates | Measure-Object SizeBytes -Sum).Sum
if ($null -eq $totalBytes) {
    $totalBytes = 0
}

Write-Status ("Archive root: {0}" -f $archiveBase) "INFO"
Write-Status ("Mode: {0}" -f ($(if ($Execute) { "EXECUTE" } else { "DRY-RUN" }))) $(if ($Execute) { "WARN" } else { "INFO" })
Write-Status ("Candidates: {0}, total: {1}" -f $candidates.Count, (Format-Bytes $totalBytes)) "INFO"
$candidates |
    Sort-Object SizeBytes -Descending |
    Select-Object -First $ConsoleLimit -Property Kind, @{Name = "Size"; Expression = { Format-Bytes $_.SizeBytes } }, FileCount, Source, Destination |
    Format-Table -AutoSize |
    Out-Host
if ($candidates.Count -gt $ConsoleLimit) {
    Write-Status ("Console capped; {0} additional candidate(s) are present only in the plan JSON." -f ($candidates.Count - $ConsoleLimit)) "INFO"
}

if ([string]::IsNullOrWhiteSpace($PlanPath)) {
    $planRoot = Join-Path $alphaRoot 'runtime\cleanup_plans'
    New-Item -ItemType Directory -Path $planRoot -Force | Out-Null
    $PlanPath = Join-Path $planRoot ("archive_backtests_{0}.json" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
}
$PlanPath = Assert-PathUnderRoot $PlanPath $repoRoot 'PlanPath'
$plan = [pscustomobject][ordered]@{
    schema_version = 'alpha-backtest-cleanup-plan-v2'
    created_at_utc = [datetime]::UtcNow.ToString('o')
    mode = $(if ($Execute) { 'execute' } else { 'dry_run' })
    repo_root = $repoRoot
    alpha_root = $alphaRoot
    archive_root = $archiveBase
    archive_session = $sessionDir
    ea_name = $EaName
    min_age_days = $MinAgeDays
    explicit_keep_run_ids = $KeepRunIds
    referenced_run_ids = $referencedRunIds
    effective_keep_run_ids = $script:EffectiveKeepRunIds
    candidate_count = $candidates.Count
    total_size_bytes = [long]$totalBytes
    items = $candidates
}
Write-JsonAtomically $plan $PlanPath 6
$planHash = (Get-FileHash -LiteralPath $PlanPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Status ("Plan: {0}" -f ([IO.Path]::GetFullPath($PlanPath))) "OK"
Write-Status ("Plan SHA256: {0}" -f $planHash) "OK"

if ($candidates.Count -eq 0) {
    Write-Status "Nothing to archive." "OK"
    return
}

if (-not $Execute) {
    Write-Status "Dry-run only. Review the plan; -Execute is a separate Owner-approved action." "OK"
    return
}

$archiveFull = [IO.Path]::GetFullPath($archiveBase)
$sourceVolume = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath($alphaRoot))
$archiveVolume = [IO.Path]::GetPathRoot($archiveFull)
if ($sourceVolume -ieq $archiveVolume -and -not $AllowSameVolumeArchive) {
    throw "Execute requires an off-volume ArchiveRoot to free disk space. Use -AllowSameVolumeArchive only for organization-only moves."
}

New-Item -ItemType Directory -Path $sessionDir -Force | Out-Null
foreach ($candidate in $candidates) {
    CopyVerifyRemove-ArchiveCandidate $candidate
}

$manifest = [pscustomobject]@{
    created_at = (Get-Date).ToString("o")
    repo_root = $repoRoot
    alpha_root = $alphaRoot
    common_files_root = $commonFilesRoot
    archive_session = $sessionDir
    ea_name = $EaName
    explicit_keep_run_ids = $KeepRunIds
    referenced_run_ids = $referencedRunIds
    effective_keep_run_ids = $script:EffectiveKeepRunIds
    min_age_days = $MinAgeDays
    total_items = $candidates.Count
    total_size_bytes = [int64]$totalBytes
    items = $candidates
}

$manifestPath = Join-Path $sessionDir "manifest.json"
Write-JsonAtomically $manifest $manifestPath 8
Write-Status ("Archived {0} item(s) to {1}" -f $candidates.Count, $sessionDir) "OK"
Write-Status ("Manifest: {0}" -f $manifestPath) "OK"
