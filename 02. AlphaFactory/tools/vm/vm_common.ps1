<#
.SYNOPSIS
    Shared helpers for tools/vm scripts (dot-source, not standalone).
#>

function Resolve-VmIsolateRoot {
    # Same candidate list as tools/init_machine_paths.ps1: first portable
    # isolate present wins. Never falls back to Program Files / AppData.
    param([Parameter(Mandatory = $true)][string]$AlphaRoot)
    foreach ($leaf in @('mt5-portable-mqdemo', 'mt5-portable-fivepercent')) {
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
