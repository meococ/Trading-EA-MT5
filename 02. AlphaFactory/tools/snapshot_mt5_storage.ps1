<#
.SYNOPSIS
    Hash a bounded metadata inventory of MT5 storage roots.
.DESCRIPTION
    Records relative path, size and UTC mtime for every file without reading
    file contents. This is intended for before/after proof that a portable
    smoke test did not mutate protected C-drive MT5 storage.
#>
param(
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [Parameter(Mandatory = $true)][string[]]$Roots
)

$ErrorActionPreference = 'Stop'

function Get-MetadataDigest([string]$Root) {
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    $hash = [System.Security.Cryptography.IncrementalHash]::CreateHash(
        [System.Security.Cryptography.HashAlgorithmName]::SHA256
    )
    $count = 0L
    $bytes = 0L
    $latest = [datetime]::MinValue
    try {
        if (Test-Path -LiteralPath $fullRoot -PathType Container) {
            $prefix = $fullRoot + [System.IO.Path]::DirectorySeparatorChar
            Get-ChildItem -LiteralPath $fullRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
                Sort-Object FullName |
                ForEach-Object {
                    $relative = $_.FullName.Substring($prefix.Length).Replace('\', '/')
                    $record = '{0}|{1}|{2}' -f $relative, [long]$_.Length, $_.LastWriteTimeUtc.Ticks
                    $recordBytes = [System.Text.Encoding]::UTF8.GetBytes($record + "`n")
                    $hash.AppendData($recordBytes)
                    $count++
                    $bytes += [long]$_.Length
                    if ($_.LastWriteTimeUtc -gt $latest) { $latest = $_.LastWriteTimeUtc }
                }
        }
        $digest = [System.BitConverter]::ToString($hash.GetHashAndReset()).Replace('-', '')
    } finally {
        $hash.Dispose()
    }
    return [pscustomobject][ordered]@{
        root = $fullRoot
        exists = Test-Path -LiteralPath $fullRoot -PathType Container
        file_count = $count
        total_bytes = $bytes
        latest_file_write_utc = $(if ($latest -eq [datetime]::MinValue) { $null } else { $latest.ToString('o') })
        metadata_sha256 = $digest
    }
}

$payload = [pscustomobject][ordered]@{
    schema_version = 'alphafactory_mt5_storage_snapshot.v1'
    generated_at_utc = [datetime]::UtcNow.ToString('o')
    roots = @($Roots | ForEach-Object { Get-MetadataDigest $_ })
}

$fullOutput = [System.IO.Path]::GetFullPath($OutputPath)
$parent = Split-Path -Parent $fullOutput
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$temp = Join-Path $parent ('.{0}.{1}.tmp' -f (Split-Path -Leaf $fullOutput), [guid]::NewGuid().ToString('N'))
$payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temp -Encoding UTF8
Move-Item -LiteralPath $temp -Destination $fullOutput -Force
Write-Host "MT5_STORAGE_SNAPSHOT=$fullOutput"
