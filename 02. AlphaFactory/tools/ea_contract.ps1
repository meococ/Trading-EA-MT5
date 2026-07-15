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

    $pinnedSources = @{
        'EA_SilverBullet'         = '03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5'
        'EA_OpenHalfMom'          = '03. EA Developer/EA_OpenHalfMom/EA_OpenHalfMomentum.mq5'
        'EA_H1LowVolDonchianMR'   = '03. EA Developer/EA_H1LowVolDonchianMR/EA_H1LowVolDonchianMR.mq5'
    }

    $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd([char[]]'\/')
    $eaRoot = [System.IO.Path]::GetFullPath((Join-Path $repoFull "03. EA Developer\$EaName"))
    $eaRootPrefix = $eaRoot.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
    $isPinned = $pinnedSources.ContainsKey($EaName)
    $relativeSource = if ($isPinned) {
        [string]$pinnedSources[$EaName]
    } else {
        "03. EA Developer/$EaName/$EaName.mq5"
    }
    $absoluteSource = [System.IO.Path]::GetFullPath((Join-Path $repoFull ($relativeSource.Replace('/', '\'))))

    if (-not $absoluteSource.StartsWith($eaRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "EA source contract escapes the active EA root: $relativeSource"
    }
    if ([System.IO.Path]::GetExtension($absoluteSource) -ine '.mq5') {
        throw "EA source contract must resolve to an .mq5 file: $relativeSource"
    }
    if (-not (Test-Path -LiteralPath $absoluteSource -PathType Leaf)) {
        if ($isPinned) {
            throw "Pinned EA source is missing for ${EaName}: $absoluteSource"
        }
        throw "EA not found: canonical source is missing for ${EaName}: $absoluteSource"
    }

    return [pscustomobject]@{
        EaName = $EaName
        RepoRelativeSource = $relativeSource.Replace('\', '/')
        AbsoluteSource = $absoluteSource
        TelemetryProfile = if ([string]::Equals($EaName, 'EA_SonicR', [System.StringComparison]::OrdinalIgnoreCase)) { 'sonic-strict' } else { 'none' }
        IsPinned = $isPinned
    }
}
