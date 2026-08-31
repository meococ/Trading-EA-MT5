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
    if ($PortableMode -and $AllowCommonFiles -and -not (Test-Mt5PathUnderRoot -Path $common -Root $data)) {
        throw "Portable MT5 CommonFilesRoot must stay under DataRoot (not AppData Common). Common='$common' Data='$data'."
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

function Get-Mt5JournalLogRoots {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [Parameter(Mandatory = $true)][string]$TesterRoot
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($DataRoot)) {
        $candidates.Add((Join-Path $DataRoot 'logs'))
    }
    if (-not [string]::IsNullOrWhiteSpace($TesterRoot)) {
        $candidates.Add((Join-Path $TesterRoot 'logs'))
        if (Test-Path -LiteralPath $TesterRoot -PathType Container) {
            Get-ChildItem -LiteralPath $TesterRoot -Directory -Filter 'Agent-*' -ErrorAction SilentlyContinue |
                ForEach-Object { $candidates.Add((Join-Path $_.FullName 'logs')) }
        }
    }

    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($path in $candidates) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (-not (Test-Path -LiteralPath $path -PathType Container)) { continue }
        $full = [System.IO.Path]::GetFullPath($path).TrimEnd([char[]]'\/')
        $leaf = [System.IO.Path]::GetFileName($full)
        if ($leaf -ine 'logs') { continue }
        if ($full -match '(?i)[\\/](bases|cache)([\\/]|$)') { continue }
        $roots.Add($full)
    }
    return @($roots | Sort-Object -Unique)
}

function Get-Mt5ProgramFilesInstallRoots {
    return @(
        'C:\Program Files\MetaTrader 5',
        'C:\Program Files (x86)\MetaTrader 5'
    )
}

function Test-Mt5PathIsOwnerProgramFilesGui {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    $full = [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]'\/')
    foreach ($root in @(Get-Mt5ProgramFilesInstallRoots)) {
        $fullRoot = [System.IO.Path]::GetFullPath($root).TrimEnd([char[]]'\/')
        if ($full.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
        if (Test-Mt5PathUnderRoot -Path $full -Root $fullRoot) { return $true }
    }
    return $false
}

function Get-Mt5AppDataTerminalRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $env:APPDATA 'MetaQuotes\Terminal')).TrimEnd([char[]]'\/')
}

function Get-Mt5AppDataOriginClones {
    [CmdletBinding()]
    param(
        [string]$InstallRoot = '',
        [string]$RuntimeRoot = ''
    )

    $wanted = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($InstallRoot)) {
        $wanted.Add([System.IO.Path]::GetFullPath($InstallRoot).TrimEnd([char[]]'\/'))
    }
    if (-not [string]::IsNullOrWhiteSpace($RuntimeRoot) -and (Test-Path -LiteralPath $RuntimeRoot -PathType Container)) {
        Get-ChildItem -LiteralPath $RuntimeRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'terminal64.exe') -PathType Leaf } |
            ForEach-Object { $wanted.Add([System.IO.Path]::GetFullPath($_.FullName).TrimEnd([char[]]'\/')) }
    }
    $wantedPaths = @($wanted | Sort-Object -Unique)
    if ($wantedPaths.Count -eq 0) { return @() }

    $termRoot = Get-Mt5AppDataTerminalRoot
    if (-not (Test-Path -LiteralPath $termRoot -PathType Container)) { return @() }

    $clones = New-Object System.Collections.Generic.List[string]
    Get-ChildItem -LiteralPath $termRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[A-F0-9]{32}$' } |
        ForEach-Object {
            $origin = Join-Path $_.FullName 'origin.txt'
            if (-not (Test-Path -LiteralPath $origin -PathType Leaf)) { return }
            $originVal = (Get-Content -LiteralPath $origin -Raw -ErrorAction SilentlyContinue)
            if ([string]::IsNullOrWhiteSpace($originVal)) { return }
            $originFull = [System.IO.Path]::GetFullPath($originVal.Trim()).TrimEnd([char[]]'\/')
            foreach ($root in $wantedPaths) {
                if ($originFull.Equals($root, [System.StringComparison]::OrdinalIgnoreCase)) {
                    $clones.Add([System.IO.Path]::GetFullPath($_.FullName).TrimEnd([char[]]'\/'))
                    return
                }
            }
        }
    return @($clones | Sort-Object -Unique)
}

function Assert-Mt5FactoryTargetIsolate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [Parameter(Mandatory = $true)][string]$CommonFilesRoot,
        [Parameter(Mandatory = $true)][string]$TesterRoot,
        [bool]$PortableMode = $false,
        [bool]$AllowCommonFiles = $true,
        [string]$RuntimeRoot = ''
    )

    $install = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd([char[]]'\/')
    $data = [System.IO.Path]::GetFullPath($DataRoot).TrimEnd([char[]]'\/')

    if (Test-Mt5PathIsOwnerProgramFilesGui $install) {
        throw "AlphaFactory refuses Owner Program Files MT5 as compile/backtest target. Pin a portable isolate in alpha.local.ps1 (InstallRoot=DataRoot, PortableMode=true, CommonFiles under that root)."
    }

    $appDataTerm = Get-Mt5AppDataTerminalRoot
    if (Test-Mt5PathUnderRoot -Path $data -Root $appDataTerm) {
        throw "AlphaFactory refuses AppData Terminal data root '$data'. That folder is the GUI/profile tree. Pin DataRoot to the portable InstallRoot."
    }

    # Hardened 2026-08-31. The factory target must live inside the AlphaFactory
    # runtime tree. Program Files and the AppData Terminal root were already
    # refused above, but an Owner GUI installed anywhere else (this machine
    # keeps one at 'D:\Meta 5') slipped through and would have compiled and
    # backtested inside the terminal the Owner trades from.
    if (-not [string]::IsNullOrWhiteSpace($RuntimeRoot)) {
        $runtime = [System.IO.Path]::GetFullPath($RuntimeRoot).TrimEnd([char[]]'\/')
        $installUnderRuntime = $install.Equals($runtime, [System.StringComparison]::OrdinalIgnoreCase) -or (Test-Mt5PathUnderRoot -Path $install -Root $runtime)
        if (-not $installUnderRuntime) {
            throw "AlphaFactory refuses InstallRoot '$install' as a compile/backtest target: it is outside the factory runtime '$runtime'. A terminal64.exe outside that tree is an Owner GUI or a foreign install. Pin a portable isolate under the runtime in alpha.local.ps1."
        }
        if (-not $PortableMode) {
            throw "InstallRoot under AlphaFactory runtime requires PortableMode=true so MT5 does not clone profiles into AppData. Install='$install'."
        }
        if (-not $data.Equals($install, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "DataRoot must equal the portable InstallRoot. Install='$install' Data='$data'."
        }
    }

    return [pscustomobject][ordered]@{
        schema_version = 'alphafactory_mt5_factory_target_isolate.v1'
        install_root = $install
        data_root = $data
        portable_mode = [bool]$PortableMode
        common_files_root = [System.IO.Path]::GetFullPath($CommonFilesRoot).TrimEnd([char[]]'\/')
        tester_root = [System.IO.Path]::GetFullPath($TesterRoot).TrimEnd([char[]]'\/')
        allow_common_files = [bool]$AllowCommonFiles
    }
}

function Resolve-Mt5ProcessIsolateDecision {
    [CmdletBinding()]
    param(
        [string]$ExecutablePath = '',
        [string]$CommandLine = '',
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [string]$RuntimeRoot = '',
        [string[]]$AppDataCloneRoots = @(),
        [bool]$AllowProgramFilesGui = $true,
        [bool]$PortableMode = $false
    )

    $exe = if ([string]::IsNullOrWhiteSpace($ExecutablePath)) {
        ''
    } else {
        [System.IO.Path]::GetFullPath($ExecutablePath)
    }
    $cmd = [string]$CommandLine
    $install = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd([char[]]'\/')
    $data = [System.IO.Path]::GetFullPath($DataRoot).TrimEnd([char[]]'\/')
    $installTerminal = Join-Path $install 'terminal64.exe'
    $installEditor = Join-Path $install 'metaeditor64.exe'

    if ([string]::IsNullOrWhiteSpace($exe)) {
        return [pscustomobject][ordered]@{
            Allowed = $false
            Reason = 'MT5 client executable path unavailable (fail-closed)'
        }
    }

    if ($exe -match '(?i)[\\/]liveupdate[\\/](terminal64|metaeditor64)\.exe$' -and $cmd -match '(?i)/update(\s|$)') {
        return [pscustomobject][ordered]@{
            Allowed = $true
            Reason = 'MetaQuotes liveupdate helper is allowed'
        }
    }

    $factoryNeedles = New-Object System.Collections.Generic.List[string]
    $factoryNeedles.Add($install)
    $factoryNeedles.Add($data)
    foreach ($clone in @($AppDataCloneRoots)) {
        if (-not [string]::IsNullOrWhiteSpace($clone)) {
            $factoryNeedles.Add([System.IO.Path]::GetFullPath($clone).TrimEnd([char[]]'\/'))
        }
    }

    $mentionsFactory = $false
    if (-not [string]::IsNullOrWhiteSpace($cmd)) {
        foreach ($needle in $factoryNeedles) {
            if ($cmd.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $mentionsFactory = $true
                break
            }
        }
    }

    if ($AllowProgramFilesGui -and (Test-Mt5PathIsOwnerProgramFilesGui $exe)) {
        if ($mentionsFactory) {
            return [pscustomobject][ordered]@{
                Allowed = $false
                Reason = ("Program Files MT5 command line targets factory data/profile: {0}" -f $cmd)
            }
        }
        return [pscustomobject][ordered]@{
            Allowed = $true
            Reason = 'Owner Program Files GUI is allowed'
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($RuntimeRoot)) {
        $runtime = [System.IO.Path]::GetFullPath($RuntimeRoot).TrimEnd([char[]]'\/')
        if ($exe.Equals($runtime, [System.StringComparison]::OrdinalIgnoreCase) -or (Test-Mt5PathUnderRoot -Path $exe -Root $runtime)) {
            if ($PortableMode -and ($exe.Equals($installTerminal, [System.StringComparison]::OrdinalIgnoreCase) -or $exe.Equals($installEditor, [System.StringComparison]::OrdinalIgnoreCase)) -and ($cmd -notmatch '(?i)/portable')) {
                return [pscustomobject][ordered]@{
                    Allowed = $false
                    Reason = ("factory executable running without /portable (AppData profile clone): {0}" -f $exe)
                }
            }
            return [pscustomobject][ordered]@{
                Allowed = $false
                Reason = ("runtime/portable MT5 client already running: {0}" -f $exe)
            }
        }
    }

    if ($exe.Equals($installTerminal, [System.StringComparison]::OrdinalIgnoreCase) -or $exe.Equals($installEditor, [System.StringComparison]::OrdinalIgnoreCase) -or (Test-Mt5PathUnderRoot -Path $exe -Root $install)) {
        if ($PortableMode -and ($cmd -notmatch '(?i)/portable')) {
            return [pscustomobject][ordered]@{
                Allowed = $false
                Reason = ("factory executable running without /portable (AppData profile clone): {0}" -f $exe)
            }
        }
        return [pscustomobject][ordered]@{
            Allowed = $false
            Reason = ("factory isolate already has an MT5 client: {0}" -f $exe)
        }
    }

    if ($mentionsFactory) {
        return [pscustomobject][ordered]@{
            Allowed = $false
            Reason = ("MT5 client command line targets factory data/profile: {0}" -f $cmd)
        }
    }

    return [pscustomobject][ordered]@{
        Allowed = $false
        Reason = ("non-factory MT5 client is not allowed during compile/backtest: {0}" -f $exe)
    }
}

function Assert-Mt5FactoryProcessIsolate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [string]$RuntimeRoot = '',
        [int[]]$OwnedPids = @(),
        [bool]$AllowProgramFilesGui = $true,
        [bool]$PortableMode = $false
    )

    $owned = @{}
    foreach ($pid in @($OwnedPids)) {
        if ($pid -gt 0) { $owned[$pid] = $true }
    }

    $clones = @(Get-Mt5AppDataOriginClones -InstallRoot $InstallRoot -RuntimeRoot $RuntimeRoot)
    $blocked = New-Object System.Collections.Generic.List[string]
    $filter = "Name='terminal64.exe' OR Name='metaeditor64.exe' OR Name='terminal.exe' OR Name='metaeditor.exe' OR Name='MetaEditor64.exe'"
    Get-CimInstance Win32_Process -Filter $filter -ErrorAction SilentlyContinue |
        ForEach-Object {
            $processId = [int]$_.ProcessId
            if ($owned.ContainsKey($processId)) { return }
            $decision = Resolve-Mt5ProcessIsolateDecision `
                -ExecutablePath ([string]$_.ExecutablePath) `
                -CommandLine ([string]$_.CommandLine) `
                -InstallRoot $InstallRoot `
                -DataRoot $DataRoot `
                -RuntimeRoot $RuntimeRoot `
                -AppDataCloneRoots $clones `
                -AllowProgramFilesGui $AllowProgramFilesGui `
                -PortableMode $PortableMode
            if (-not [bool]$decision.Allowed) {
                $blocked.Add(("PID {0} {1}: {2}" -f $processId, $_.Name, $decision.Reason))
            }
        }

    if ($blocked.Count -gt 0) {
        throw (
            "Factory isolate failed. Close runtime/portable terminal64 and metaeditor64 first. Owner Program Files GUI is allowed; no process was stopped.`n - " +
            [string]::Join("`n - ", $blocked.ToArray())
        )
    }
}
