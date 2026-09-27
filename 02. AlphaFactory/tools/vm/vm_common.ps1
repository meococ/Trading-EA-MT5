<#
.SYNOPSIS
    Shared helpers for tools/vm scripts (dot-source, not standalone).
#>

function Resolve-VmIsolateRoot {
    # VM only ever uses the MetaQuotes-Demo isolate. Never falls back to
    # Program Files / AppData; fivepercent isolate belongs to the Owner plane.
    param([Parameter(Mandatory = $true)][string]$AlphaRoot)
    foreach ($leaf in @('mt5-portable-mqdemo')) {
        $root = Join-Path $AlphaRoot ('runtime\' + $leaf)
        if ((Test-Path -LiteralPath (Join-Path $root 'terminal64.exe') -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $root 'MQL5') -PathType Container)) {
            return ([System.IO.Path]::GetFullPath($root)).TrimEnd([char[]]'\/')
        }
    }
    return $null
}

function Get-VmRepoLayout {
    param([Parameter(Mandatory = $true)][string]$VmToolsRoot)
    $toolsRoot = Split-Path -Parent $VmToolsRoot
    $alphaRoot = Split-Path -Parent $toolsRoot
    $repoRoot = Split-Path -Parent $alphaRoot
    return [ordered]@{
        VmToolsRoot = $VmToolsRoot
        ToolsRoot   = $toolsRoot
        AlphaRoot   = $alphaRoot
        RepoRoot    = $repoRoot
        IsolateRoot = (Resolve-VmIsolateRoot -AlphaRoot $alphaRoot)
    }
}

function Get-VmIsolateProcessPrefix {
    # Sibling dirs sharing the isolate's name prefix (e.g. mt5-portable-mqdemo.bak)
    # are foreign, not isolate — the trailing separator is the boundary.
    param([Parameter(Mandatory = $true)][string]$IsolateRoot)
    return (([System.IO.Path]::GetFullPath($IsolateRoot)).TrimEnd([char[]]'\/') + '\')
}

function Get-VmMt5Processes {
    # Every MT5 host process (incl. metatester64 agents), classified by whether
    # its exe lives under the isolate prefix.
    param([Parameter(Mandatory = $true)][string]$IsolateRoot)
    $prefix = Get-VmIsolateProcessPrefix -IsolateRoot $IsolateRoot
    return @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe' OR Name='metaeditor64.exe' OR Name='metatester64.exe'" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $exePath = [string]$_.ExecutablePath
            [pscustomobject][ordered]@{
                pid        = [int]$_.ProcessId
                name       = [string]$_.Name
                path       = $exePath
                in_isolate = ($exePath -and $exePath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase))
            }
        })
}

function Test-VmBacktestLockActive {
    # runtime\alpha_backtest.lock is held open FileShare.None by a live
    # alpha.ps1 backtest; an exclusively-openable file means no live run.
    param([Parameter(Mandatory = $true)][string]$AlphaRoot)
    $lockPath = Join-Path $AlphaRoot 'runtime\alpha_backtest.lock'
    if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) { return $false }
    try {
        $probe = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $probe.Dispose()
        return $false
    } catch [System.IO.IOException] {
        return $true
    } catch {
        return $false
    }
}
