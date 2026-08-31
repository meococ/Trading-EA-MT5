<#
.SYNOPSIS
    Fail if any live Python file attaches to MetaTrader 5 without pinning the
    factory isolate.

.DESCRIPTION
    `mt5.initialize()` with no arguments attaches to whichever terminal is
    already running. On the Owner machine that is the GUI terminal being traded
    from -- the same terminal the MT5 MCP server on 127.0.0.1:22346 drives.
    Research must never land there: it competes with live charts, reads the
    Owner's history instead of the pinned isolate, and produces numbers no
    other machine can reproduce.

    The contract: every attach passes `path=` (normally via
    tools/factory_paths.mt5_initialize_kwargs()).

    Written in PowerShell on purpose -- Python on this machine is the Microsoft
    Store stub, so a pytest version could not run today.

.PARAMETER CriticalPathOnly
    Only check the modules alpha.ps1 actually invokes. Off-path research probes
    are reported as warnings instead of failures.

.EXAMPLE
    & ".\02. AlphaFactory\tools\check_mt5_attach_contract.ps1" -CriticalPathOnly
#>
[CmdletBinding()]
param(
    [switch]$CriticalPathOnly
)

$ErrorActionPreference = 'Stop'

$alphaRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $alphaRoot

# Modules alpha.ps1 invokes. A bare attach in one of these is a hard failure.
$criticalPath = @(
    'analysis/mt5_connector.py',
    'analysis/trade_chart_capture.py'
)

$offenders = @()
$scanned = 0

Get-ChildItem -LiteralPath $alphaRoot -Recurse -Filter '*.py' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike '*\runtime\*' -and $_.FullName -notlike '*\00. Old File\*' } |
    ForEach-Object {
        $text = [System.IO.File]::ReadAllText($_.FullName)
        # Only files that actually attach can violate the contract. This also
        # skips factory_paths.py itself, whose docstring shows the bad pattern.
        if ($text -notmatch 'import\s+MetaTrader5') { return }
        $scanned++
        $rel = $_.FullName.Substring($repoRoot.Length + 1).Replace('\', '/')
        $lineNo = 0
        foreach ($line in [System.IO.File]::ReadAllLines($_.FullName)) {
            $lineNo++
            if ($line -match '^\s*#') { continue }   # comments are not attaches
            if ($line -match '(?<!\w)mt5\.initialize\(\s*\)') {
                $offenders += [pscustomobject]@{
                    Path     = $rel
                    Line     = $lineNo
                    Critical = ($criticalPath -contains ($rel -replace '^02\. AlphaFactory/', ''))
                }
            }
        }
    }

$critical = @($offenders | Where-Object { $_.Critical })
$offPath = @($offenders | Where-Object { -not $_.Critical })

"MT5 attach contract - scanned $scanned Python files under '02. AlphaFactory'"
"  bare mt5.initialize() on the alpha.ps1 critical path : $($critical.Count)"
"  bare mt5.initialize() in off-path research probes     : $($offPath.Count)"

if ($critical.Count -gt 0) {
    ""
    "CRITICAL - these run as part of alpha.ps1 and would attach to the Owner GUI:"
    $critical | ForEach-Object { "  {0}:{1}" -f $_.Path, $_.Line }
}

if ($offPath.Count -gt 0) {
    ""
    "WARNING - off-path probes still using a bare attach:"
    $offPath | Select-Object -First 50 | ForEach-Object { "  {0}:{1}" -f $_.Path, $_.Line }
    if ($offPath.Count -gt 50) { "  ... and $($offPath.Count - 50) more" }
    ""
    "Fix pattern:"
    "  from tools.factory_paths import mt5_initialize_kwargs"
    "  mt5.initialize(**mt5_initialize_kwargs())"
}

if ($critical.Count -gt 0) { exit 1 }
if (-not $CriticalPathOnly -and $offPath.Count -gt 0) { exit 1 }

""
"PASS"
exit 0
