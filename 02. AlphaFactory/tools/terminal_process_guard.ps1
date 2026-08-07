Set-StrictMode -Version Latest

function Resolve-AlphaMt5ExecutablePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AlphaRoot
    )

    $alphaRootFull = [System.IO.Path]::GetFullPath($AlphaRoot)
    $localConfigPath = Join-Path $alphaRootFull 'alpha.local.ps1'
    $installRoot = $null

    if (Test-Path -LiteralPath $localConfigPath -PathType Leaf) {
        # Evaluate machine-local configuration in a child scope so its variables do
        # not leak into the research-loop contract state.
        $installRoot = & {
            $MT5InstallRoot = $null
            . $localConfigPath
            if (-not [string]::IsNullOrWhiteSpace([string]$MT5InstallRoot)) {
                [string]$MT5InstallRoot
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$installRoot)) {
        foreach ($candidate in @(
            'C:\Program Files\MetaTrader 5',
            'C:\Program Files (x86)\MetaTrader 5'
        )) {
            if (Test-Path -LiteralPath (Join-Path $candidate 'terminal64.exe') -PathType Leaf) {
                $installRoot = $candidate
                break
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$installRoot)) {
        throw 'Cannot resolve the AlphaFactory MT5 executable. Configure MT5InstallRoot in alpha.local.ps1.'
    }

    $terminalPath = [System.IO.Path]::GetFullPath((Join-Path ([string]$installRoot) 'terminal64.exe'))
    if (-not (Test-Path -LiteralPath $terminalPath -PathType Leaf)) {
        throw "Configured AlphaFactory MT5 executable does not exist: $terminalPath"
    }
    return $terminalPath
}

function Get-TerminalExecutablePath {
    param(
        [Parameter(Mandatory = $true)]
        $Process
    )

    $rawPath = $null
    try {
        $rawPath = [string]$Process.Path
    } catch {
        $rawPath = $null
    }

    if ([string]::IsNullOrWhiteSpace([string]$rawPath)) {
        try {
            $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$Process.Id)" -ErrorAction SilentlyContinue
            if ($null -ne $cim) {
                $rawPath = [string]$cim.ExecutablePath
            }
        } catch {
            $rawPath = $null
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$rawPath)) {
        return $null
    }
    return [System.IO.Path]::GetFullPath([string]$rawPath)
}

function Get-ConflictingAlphaTerminalProcesses {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExpectedExecutablePath,
        [object[]]$Processes = $null
    )

    $expected = [System.IO.Path]::GetFullPath($ExpectedExecutablePath)
    $candidates = if ($null -eq $Processes) {
        @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    } else {
        @($Processes)
    }

    $conflicts = New-Object System.Collections.Generic.List[object]
    foreach ($process in $candidates) {
        $actual = Get-TerminalExecutablePath $process
        # Unknown identity is deliberately blocking. A process is allowed only when
        # it is positively identified as a different MT5 installation.
        if ([string]::IsNullOrWhiteSpace([string]$actual) -or $actual -ieq $expected) {
            [void]$conflicts.Add([pscustomobject]@{
                Process = $process
                ExecutablePath = $actual
            })
        }
    }
    return @($conflicts.ToArray())
}

function Assert-NoConflictingAlphaTerminal {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExpectedExecutablePath
    )

    $conflicts = @(Get-ConflictingAlphaTerminalProcesses -ExpectedExecutablePath $ExpectedExecutablePath)
    if ($conflicts.Count -eq 0) {
        return
    }

    $details = @($conflicts | ForEach-Object {
        $pathText = if ([string]::IsNullOrWhiteSpace([string]$_.ExecutablePath)) { '<unresolved>' } else { [string]$_.ExecutablePath }
        "PID=$([int]$_.Process.Id) path=$pathText"
    }) -join '; '
    throw "Conflicting AlphaFactory terminal64 process already running ($details). Research loop failed closed before backtest; no process was stopped."
}
