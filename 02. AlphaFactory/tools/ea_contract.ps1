function Resolve-EaSourceContract {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$EaName
    )

    if ($EaName -notmatch '^[A-Za-z0-9][A-Za-z0-9 _.-]{0,127}$') {
        throw "EA name '$EaName' contains unsupported path characters."
    }

    # Active-lane pins. Owner Path-C overrides 2026-07-15.
    # Compile/backtest from archive remains invalid evidence (AGENTS.md).
    $pinnedSources = @{
        'EA_HybridICT_Sonic' = '03. EA Developer/EA_HybridICT_Sonic/EA_HybridICT_Sonic.mq5'
        'EA_FVGConfluence'   = '03. EA Developer/EA_FVGConfluence/EA_FVGConfluence.mq5'
    }

    $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd([char[]]'\/')
    $eaDevRoot = [System.IO.Path]::GetFullPath((Join-Path $repoFull '03. EA Developer'))
    $eaRoot = [System.IO.Path]::GetFullPath((Join-Path $repoFull "03. EA Developer\$EaName"))
    $eaRootPrefix = $eaRoot.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
    $isPinned = $pinnedSources.ContainsKey($EaName)
    $relativeSource = if ($isPinned) {
        [string]$pinnedSources[$EaName]
    } else {
        "03. EA Developer/$EaName/$EaName.mq5"
    }
    $absoluteSource = [System.IO.Path]::GetFullPath((Join-Path $repoFull ($relativeSource.Replace('/', '\'))))

    if (-not (Test-Path -LiteralPath $eaDevRoot -PathType Container)) {
        throw "Active EA Developer root missing: $eaDevRoot"
    }

    $activePackages = @(Get-ChildItem -LiteralPath $eaDevRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'EA_*' } |
        Select-Object -ExpandProperty Name)

    if (-not $absoluteSource.StartsWith($eaRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "EA source contract escapes the active EA root: $relativeSource"
    }
    if ([System.IO.Path]::GetExtension($absoluteSource) -ine '.mq5') {
        throw "EA source contract must resolve to an .mq5 file: $relativeSource"
    }
    if (-not (Test-Path -LiteralPath $absoluteSource -PathType Leaf)) {
        $shelfNote = if ($activePackages.Count -eq 0) {
            'Active EA Developer shelf is empty (Owner archived packages to 00. Old File/EA_Archive/ on 2026-07-15). Restore an EA under 03. EA Developer/ and update hot.md before compile/backtest.'
        } else {
            "Active packages present: $($activePackages -join ', ')."
        }
        if ($isPinned) {
            throw "Pinned EA source is missing for ${EaName}: $absoluteSource. $shelfNote"
        }
        throw "EA not found: canonical source is missing for ${EaName}: $absoluteSource. $shelfNote Archive paths are not valid compile/evidence sources."
    }

    return [pscustomobject]@{
        EaName = $EaName
        RepoRelativeSource = $relativeSource.Replace('\', '/')
        AbsoluteSource = $absoluteSource
        TelemetryProfile = if ([string]::Equals($EaName, 'EA_SonicR', [System.StringComparison]::OrdinalIgnoreCase)) { 'sonic-strict' } else { 'none' }
        IsPinned = $isPinned
    }
}
