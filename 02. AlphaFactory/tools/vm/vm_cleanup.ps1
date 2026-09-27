<#
.SYNOPSIS
    VM hygiene: delegate repo cleanup to post_run_cleanup.ps1, kill only
    isolate-owned MT5 processes, delete temp credential files.
.DESCRIPTION
    Default is dry-run (WhatIf). -Execute actually kills/removes.
    A terminal64/metaeditor64 is only a target when its ExecutablePath lives
    under the isolate root; any MT5 process outside the isolate is left alone.
    Exit code: 0 = PASS, 1 = WARN (nothing removed / dry-run leftovers), 2 = FAIL.
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [switch]$Json,
    [ValidateSet('safe', 'journals', 'all')]
    [string]$Scope = 'safe'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Off

$vmToolsRoot = $PSScriptRoot
. (Join-Path $vmToolsRoot 'vm_common.ps1')
$layout = Get-VmRepoLayout -VmToolsRoot $vmToolsRoot
$toolsRoot = $layout.ToolsRoot
$alphaRoot = $layout.AlphaRoot
$repoRoot = $layout.RepoRoot
$isolateRoot = $layout.IsolateRoot
if (-not $isolateRoot) { $isolateRoot = Join-Path $alphaRoot 'runtime\mt5-portable-mqdemo' }
$mode = if ($Execute) { 'EXECUTE' } else { 'WHATIF' }

$actions = New-Object System.Collections.Generic.List[object]
function Add-Action([string]$Kind, [string]$Target, [string]$Done) {
    $actions.Add([pscustomobject][ordered]@{ kind = $Kind; target = $Target; result = $Done })
}
$exitCode = 0
function Bump([int]$Code) { if ($Code -gt $script:exitCode) { $script:exitCode = $Code } }

# --- 1. delegate scoped file cleanup ------------------------------------------
try {
    $postRun = Join-Path $toolsRoot 'post_run_cleanup.ps1'
    $postArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $postRun, '-Scope', $Scope)
    if ($Execute) { $postArgs += '-Execute' }
    $postOut = & powershell @postArgs 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Add-Action 'post_run_cleanup' $postRun "FAILED exit=$LASTEXITCODE"
        Bump 2
    } else {
        Add-Action 'post_run_cleanup' $postRun "ok scope=$Scope mode=$mode"
    }
} catch {
    Add-Action 'post_run_cleanup' $postRun "ERROR $($_.Exception.Message)"
    Bump 2
}

# --- 2. isolate-owned process kill ---------------------------------------------
# A live alpha.ps1 backtest owns its isolate terminals and holds
# runtime\alpha_backtest.lock; while that lock is active we never kill.
$killed = 0
$skippedForeign = 0
$skippedLocked = 0
try {
    $lockActive = Test-VmBacktestLockActive -AlphaRoot $alphaRoot
    $mt5 = @(Get-VmMt5Processes -IsolateRoot $isolateRoot)
    foreach ($p in $mt5) {
        if ($p.in_isolate) {
            if ($lockActive) {
                $skippedLocked++
                Add-Action 'skip_isolate_process' ("pid=" + $p.pid + " " + $p.path) 'active backtest lock'
            } elseif ($Execute) {
                Stop-Process -Id $p.pid -Force -ErrorAction SilentlyContinue
                $killed++
                Add-Action 'kill_isolate_process' ("pid=" + $p.pid + " " + $p.path) 'killed'
            } else {
                Add-Action 'kill_isolate_process' ("pid=" + $p.pid + " " + $p.path) 'would-kill'
            }
        } else {
            $skippedForeign++
            Add-Action 'skip_foreign_process' ("pid=" + $p.pid + " " + $p.path) 'untouched'
        }
    }
} catch {
    Add-Action 'process_scan' 'Win32_Process' "ERROR $($_.Exception.Message)"
    Bump 2
}

# --- 3. temp credential files ----------------------------------------------------
$removed = 0
$tempPatterns = @(
    (Join-Path $env:TEMP 'mt5_login.ini'),
    (Join-Path $repoRoot 'login.ini'),
    (Join-Path $env:USERPROFILE 'secret_to_upload_*')
)
foreach ($pat in $tempPatterns) {
    foreach ($f in @(Get-Item $pat -Force -ErrorAction SilentlyContinue)) {
        if ($Execute) {
            Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
            $removed++
            Add-Action 'remove_temp_cred_file' $f.FullName 'removed'
        } else {
            Add-Action 'remove_temp_cred_file' $f.FullName 'would-remove'
        }
    }
}

$result = [ordered]@{
    schema_version = 'alphafactory_vm_cleanup.v1'
    mode = $mode
    isolate_root = $isolateRoot
    processes_killed = $killed
    foreign_processes_untouched = $skippedForeign
    isolate_processes_skipped_lock = $skippedLocked
    temp_cred_files_removed = $removed
    actions = $actions.ToArray()
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
} else {
    Write-Host ("cleanup: " + $mode)
    foreach ($a in $actions) {
        Write-Host ("  [" + $a.kind + "] " + $a.target + " -> " + $a.result)
    }
}
exit $exitCode
