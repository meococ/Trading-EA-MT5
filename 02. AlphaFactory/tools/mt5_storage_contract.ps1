<#
.SYNOPSIS
    Shared fail-closed MT5 launch and storage-path contract.
.DESCRIPTION
    Keeps portable-mode argument construction and storage-drive validation in
    one place so compile, terminal launch, relaunch and evidence collection use
    the same machine-local contract.
#>

function Get-Mt5LaunchArguments {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ConfigPath,
        [bool]$PortableMode = $false
    )

    $arguments = New-Object System.Collections.Generic.List[string]
    if ($PortableMode) {
        $arguments.Add('/portable')
    }
    $arguments.Add(('/config:"{0}"' -f $ConfigPath))
    return @($arguments)
}

function Get-MetaEditorCompileArguments {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$LogPath,
        [bool]$PortableMode = $false
    )

    $arguments = New-Object System.Collections.Generic.List[string]
    if ($PortableMode) {
        $arguments.Add('/portable')
    }
    $arguments.Add(('/compile:"{0}"' -f $SourcePath))
    $arguments.Add(('/log:"{0}"' -f $LogPath))
    return @($arguments)
}

function Get-Mt5PathRootName {
    param([Parameter(Mandatory = $true)][string]$Path)
    $root = [System.IO.Path]::GetPathRoot([System.IO.Path]::GetFullPath($Path))
    if ([string]::IsNullOrWhiteSpace($root)) {
        throw "MT5 storage path has no drive root: $Path"
    }
    return $root.TrimEnd([char[]]'\/').ToUpperInvariant()
}

function Test-Mt5PathUnderRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]'\/')
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    if ($fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    return $fullPath.StartsWith(
        $fullRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Assert-Mt5StorageContract {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [Parameter(Mandatory = $true)][string]$CommonFilesRoot,
        [Parameter(Mandatory = $true)][string]$TesterRoot,
        [bool]$PortableMode = $false,
        [bool]$AllowCommonFiles = $true,
        [string]$RequiredDrive = ''
    )

    $install = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd([char[]]'\/')
    $data = [System.IO.Path]::GetFullPath($DataRoot).TrimEnd([char[]]'\/')
    $common = [System.IO.Path]::GetFullPath($CommonFilesRoot).TrimEnd([char[]]'\/')
    $tester = [System.IO.Path]::GetFullPath($TesterRoot).TrimEnd([char[]]'\/')

    if ($PortableMode -and -not $install.Equals($data, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Portable MT5 requires InstallRoot and DataRoot to be the same directory. Install='$install' Data='$data'."
    }
    if ($PortableMode -and -not (Test-Mt5PathUnderRoot -Path $tester -Root $data)) {
        throw "Portable MT5 TesterRoot must stay under DataRoot. Tester='$tester' Data='$data'."
    }

    $required = $RequiredDrive.Trim().TrimEnd([char[]]'\/').ToUpperInvariant()
    if (-not [string]::IsNullOrWhiteSpace($required)) {
        if ($required -notmatch '^[A-Z]:$') {
            throw "RequiredDrive must look like 'D:'; got '$RequiredDrive'."
        }
        $paths = [ordered]@{
            InstallRoot = $install
            DataRoot = $data
            TesterRoot = $tester
        }
        if ($AllowCommonFiles) {
            $paths.CommonFilesRoot = $common
        }
        foreach ($label in $paths.Keys) {
            $drive = Get-Mt5PathRootName $paths[$label]
            if ($drive -cne $required) {
                throw "$label must be on ${required}; got '$($paths[$label])' ($drive)."
            }
        }
    }

    return [pscustomobject][ordered]@{
        schema_version = 'alphafactory_mt5_storage_contract.v1'
        portable_mode = [bool]$PortableMode
        required_drive = $required
        common_files_allowed = [bool]$AllowCommonFiles
        install_root = $install
        data_root = $data
        common_files_root = $common
        tester_root = $tester
    }
}

function Get-Mt5SidecarRoots {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$CommonFilesRoot,
        [Parameter(Mandatory = $true)][string]$TesterRoot,
        [bool]$IncludeCommonFiles = $true
    )

    $roots = New-Object System.Collections.Generic.List[string]
    if ($IncludeCommonFiles -and (Test-Path -LiteralPath $CommonFilesRoot -PathType Container)) {
        $roots.Add((Resolve-Path -LiteralPath $CommonFilesRoot).Path)
    }
    if (Test-Path -LiteralPath $TesterRoot -PathType Container) {
        Get-ChildItem -LiteralPath $TesterRoot -Directory -Filter 'Agent-*' -ErrorAction SilentlyContinue |
            ForEach-Object {
                $files = Join-Path $_.FullName 'MQL5\Files'
                if (Test-Path -LiteralPath $files -PathType Container) {
                    $roots.Add((Resolve-Path -LiteralPath $files).Path)
                }
            }
    }
    return @($roots | Sort-Object -Unique)
}
