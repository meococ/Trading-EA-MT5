Set-StrictMode -Version Latest

function Get-AlphaFileSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "File is missing: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-AlphaFileId {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $output = & fsutil.exe file queryfileid $resolved 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $match = [regex]::Match(($output -join ' '), '0x[0-9a-fA-F]+')
    if (-not $match.Success) { return $null }
    return $match.Value.ToLowerInvariant()
}

function Test-AlphaSamePhysicalFile {
    param(
        [Parameter(Mandatory = $true)][string]$First,
        [Parameter(Mandatory = $true)][string]$Second
    )
    if (-not (Test-Path -LiteralPath $First -PathType Leaf) -or
        -not (Test-Path -LiteralPath $Second -PathType Leaf)) {
        return $false
    }
    $firstPath = (Resolve-Path -LiteralPath $First).Path
    $secondPath = (Resolve-Path -LiteralPath $Second).Path
    if ([IO.Path]::GetPathRoot($firstPath) -ine [IO.Path]::GetPathRoot($secondPath)) { return $false }
    $firstId = Get-AlphaFileId $firstPath
    $secondId = Get-AlphaFileId $secondPath
    return $null -ne $firstId -and $null -ne $secondId -and $firstId -eq $secondId
}

function Test-AlphaFilesIdentical {
    param(
        [Parameter(Mandatory = $true)][string]$First,
        [Parameter(Mandatory = $true)][string]$Second
    )
    if (-not (Test-Path -LiteralPath $First -PathType Leaf) -or
        -not (Test-Path -LiteralPath $Second -PathType Leaf)) {
        return $false
    }
    $firstItem = Get-Item -LiteralPath $First
    $secondItem = Get-Item -LiteralPath $Second
    if ($firstItem.Length -ne $secondItem.Length) { return $false }
    return (Get-AlphaFileSha256 $First) -eq (Get-AlphaFileSha256 $Second)
}

function Copy-AlphaLogWithMirror {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$PrimaryDirectory,
        [Parameter(Mandatory = $true)][string]$MirrorDirectory,
        [bool]$AllowCopyFallback = $true
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Log source is missing: $Source"
    }
    New-Item -ItemType Directory -Path $PrimaryDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $MirrorDirectory -Force | Out-Null
    $name = Split-Path -Leaf $Source
    $primary = Join-Path $PrimaryDirectory $name
    $mirror = Join-Path $MirrorDirectory $name
    Copy-Item -LiteralPath $Source -Destination $primary -Force
    if (Test-Path -LiteralPath $mirror) { Remove-Item -LiteralPath $mirror -Force }

    $mode = 'hardlink'
    try {
        New-Item -ItemType HardLink -Path $mirror -Target $primary -ErrorAction Stop | Out-Null
    } catch {
        if (-not $AllowCopyFallback) { throw }
        Copy-Item -LiteralPath $primary -Destination $mirror -Force
        $mode = 'copy_fallback'
    }
    if (-not (Test-AlphaFilesIdentical -First $primary -Second $mirror)) {
        throw "Log mirror verification failed: $mirror"
    }
    $samePhysicalFile = Test-AlphaSamePhysicalFile -First $primary -Second $mirror
    if ($mode -eq 'hardlink' -and -not $samePhysicalFile) {
        throw "Log mirror hardlink identity verification failed: $mirror"
    }
    $item = Get-Item -LiteralPath $primary
    return [pscustomobject][ordered]@{
        mode = $mode
        source = (Resolve-Path -LiteralPath $Source).Path
        primary = (Resolve-Path -LiteralPath $primary).Path
        mirror = (Resolve-Path -LiteralPath $mirror).Path
        size_bytes = [long]$item.Length
        sha256 = Get-AlphaFileSha256 $primary
        same_physical_file = $samePhysicalFile
        physical_duplicate_bytes = $(if ($mode -eq 'hardlink') { 0 } else { [long]$item.Length })
    }
}

function Convert-AlphaDuplicateLogMirror {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Primary,
        [Parameter(Mandatory = $true)][string]$Mirror,
        [switch]$Execute
    )

    $primaryPath = (Resolve-Path -LiteralPath $Primary).Path
    $mirrorPath = (Resolve-Path -LiteralPath $Mirror).Path
    if ([IO.Path]::GetPathRoot($primaryPath) -ine [IO.Path]::GetPathRoot($mirrorPath)) {
        throw "Hardlink conversion requires the same volume."
    }
    $item = Get-Item -LiteralPath $mirrorPath
    if (Test-AlphaSamePhysicalFile -First $primaryPath -Second $mirrorPath) {
        return [pscustomobject][ordered]@{
            mode = $(if ($Execute) { 'execute' } else { 'dry_run' })
            primary = $primaryPath
            mirror = $mirrorPath
            size_bytes = [long]$item.Length
            sha256 = Get-AlphaFileSha256 $primaryPath
            reclaimable_bytes = 0L
            converted = $false
            already_hardlinked = $true
        }
    }
    if (-not (Test-AlphaFilesIdentical -First $primaryPath -Second $mirrorPath)) {
        throw "Primary and mirror are not byte-identical: $primaryPath :: $mirrorPath"
    }
    $receipt = [ordered]@{
        mode = $(if ($Execute) { 'execute' } else { 'dry_run' })
        primary = $primaryPath
        mirror = $mirrorPath
        size_bytes = [long]$item.Length
        sha256 = Get-AlphaFileSha256 $primaryPath
        reclaimable_bytes = [long]$item.Length
        converted = $false
        already_hardlinked = $false
    }
    if (-not $Execute) { return [pscustomobject]$receipt }

    $backup = "$mirrorPath.dedupe.$([guid]::NewGuid().ToString('N')).bak"
    Move-Item -LiteralPath $mirrorPath -Destination $backup
    try {
        New-Item -ItemType HardLink -Path $mirrorPath -Target $primaryPath -ErrorAction Stop | Out-Null
        if (-not (Test-AlphaFilesIdentical -First $primaryPath -Second $mirrorPath)) {
            throw "Converted hardlink failed hash verification."
        }
        if (-not (Test-AlphaSamePhysicalFile -First $primaryPath -Second $mirrorPath)) {
            throw "Converted hardlink failed physical file identity verification."
        }
        Remove-Item -LiteralPath $backup -Force
        $receipt.converted = $true
        return [pscustomobject]$receipt
    } catch {
        if (Test-Path -LiteralPath $mirrorPath) { Remove-Item -LiteralPath $mirrorPath -Force }
        if (Test-Path -LiteralPath $backup) { Move-Item -LiteralPath $backup -Destination $mirrorPath }
        throw
    }
}
