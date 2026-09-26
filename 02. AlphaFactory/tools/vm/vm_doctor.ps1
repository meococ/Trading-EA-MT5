<#
.SYNOPSIS
    VM self-diagnosis for the AlphaFactory portable isolate (read-only).
.DESCRIPTION
    Checks: isolate presence + storage contract, demo authorization state,
    alpha.ps1 validate, free disk, running MT5 processes (isolate vs foreign),
    git HEAD vs origin + dirty files, hooksPath, terminal build.
    Exit code: 0 = PASS, 1 = WARN, 2 = FAIL. Never prints secret values.
#>
[CmdletBinding()]
param(
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Off

trap {
    $line = $_.InvocationInfo.ScriptLineNumber
    if ($Json) {
        [ordered]@{
            schema_version = 'alphafactory_vm_doctor.v1'
            verdict = 'FAIL'
            error = "line ${line}: $($_.Exception.Message)"
        } | ConvertTo-Json -Depth 4
    } else {
        Write-Host ("doctor FAIL line " + $line + ": " + $_.Exception.Message)
    }
    exit 2
}

$vmToolsRoot = $PSScriptRoot
. (Join-Path $vmToolsRoot 'vm_common.ps1')
$layout = Get-VmRepoLayout -VmToolsRoot $vmToolsRoot
$toolsRoot = $layout.ToolsRoot
$alphaRoot = $layout.AlphaRoot
$repoRoot = $layout.RepoRoot
$isolateRoot = $layout.IsolateRoot
if (-not $isolateRoot) { $isolateRoot = Join-Path $alphaRoot 'runtime\mt5-portable-mqdemo' }
$alphaCli = Join-Path $alphaRoot 'alpha.ps1'

$checks = New-Object System.Collections.Generic.List[object]
function Add-Check([string]$Name, [string]$Status, [string]$Detail) {
    $checks.Add([pscustomobject][ordered]@{
        name = $Name
        status = $Status   # PASS | WARN | FAIL
        detail = $Detail
    })
}

# --- isolate + storage contract -------------------------------------------
$contractOk = $false
$contractDetail = ''
try {
    $terminalExe = Join-Path $isolateRoot 'terminal64.exe'
    $editorExe = Join-Path $isolateRoot 'metaeditor64.exe'
    $mql5Dir = Join-Path $isolateRoot 'MQL5'
    if (-not (Test-Path -LiteralPath $terminalExe -PathType Leaf)) { throw "terminal64.exe missing in $isolateRoot" }
    if (-not (Test-Path -LiteralPath $editorExe -PathType Leaf)) { throw "metaeditor64.exe missing in $isolateRoot" }
    if (-not (Test-Path -LiteralPath $mql5Dir -PathType Container)) { throw "MQL5 dir missing in $isolateRoot" }

    $localPin = Join-Path $alphaRoot 'alpha.local.ps1'
    if (-not (Test-Path -LiteralPath $localPin -PathType Leaf)) { throw "alpha.local.ps1 missing; run tools/init_machine_paths.ps1" }
    . $localPin
    . (Join-Path $toolsRoot 'mt5_storage_contract.ps1')
    Assert-Mt5FactoryTargetIsolate `
        -InstallRoot $MT5InstallRoot -DataRoot $MT5DataRoot `
        -CommonFilesRoot $MT5CommonFilesRoot -TesterRoot $MT5TesterRoot `
        -PortableMode ([bool]$MT5PortableMode) -AllowCommonFiles ([bool]$MT5AllowCommonFiles) `
        -RuntimeRoot (Join-Path $alphaRoot 'runtime') | Out-Null
    Assert-Mt5StorageContract `
        -InstallRoot $MT5InstallRoot -DataRoot $MT5DataRoot `
        -CommonFilesRoot $MT5CommonFilesRoot -TesterRoot $MT5TesterRoot `
        -PortableMode ([bool]$MT5PortableMode) -AllowCommonFiles ([bool]$MT5AllowCommonFiles) `
        -RequiredDrive ([string]$MT5RequiredStorageDrive) | Out-Null
    $contractOk = $true
    $contractDetail = "isolate=$isolateRoot"
    Add-Check 'isolate_storage_contract' 'PASS' $contractDetail
} catch {
    Add-Check 'isolate_storage_contract' 'FAIL' $_.Exception.Message
}

# --- terminal build ---------------------------------------------------------
$terminalBuild = ''
try {
    $fv = (Get-Item -LiteralPath $terminalExe).VersionInfo.FileVersion
    $m = [regex]::Match([string]$fv, '(\d+)$')
    if ($m.Success) { $terminalBuild = $m.Groups[1].Value }
} catch { }
Add-Check 'terminal_build' $(if ($terminalBuild) { 'PASS' } else { 'WARN' }) ("build=" + $(if ($terminalBuild) { $terminalBuild } else { 'unknown' }) + " file_version=" + $fv)

# --- demo authorization state ------------------------------------------------
$authState = 'unknown'
$authDetail = ''
try {
    $logDir = Join-Path $isolateRoot 'logs'
    $latestLog = Get-ChildItem -LiteralPath $logDir -Filter '*.log' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d{8}\.log$' } |
        Sort-Object Name | Select-Object -Last 1
    if ($null -eq $latestLog) {
        $authState = 'never'; $authDetail = 'no terminal log'
    } else {
        $tail = Get-Content -LiteralPath $latestLog.FullName -Tail 400 -ErrorAction SilentlyContinue
        if (@($tail) -match 'authorized on MetaQuotes-Demo') {
            $authState = 'authorized'
            $authDetail = "log=$($latestLog.Name)"
        } elseif (@($tail) -match 'authorization .* failed') {
            $authState = 'failed'
            $authDetail = "log=$($latestLog.Name) shows failed auth"
        } else {
            $authState = 'not_observed'
            $authDetail = "log=$($latestLog.Name) has no auth line"
        }
    }
} catch { $authDetail = $_.Exception.Message }
Add-Check 'demo_authorization' $(switch ($authState) { 'authorized' { 'PASS' } 'never' { 'WARN' } 'not_observed' { 'WARN' } default { 'FAIL' } }) $authDetail

# --- alpha.ps1 validate -------------------------------------------------------
$validateStatus = 'FAIL'
$validateDetail = ''
try {
    if (-not (Test-Path -LiteralPath $alphaCli -PathType Leaf)) { throw "alpha.ps1 missing" }
    $pythonDir = 'C:\Python312'
    if (Test-Path -LiteralPath (Join-Path $pythonDir 'python.exe') -PathType Leaf) {
        if ($env:Path -notlike "*$pythonDir*") { $env:Path = "$pythonDir;$env:Path" }
    }
    Push-Location $repoRoot
    try {
        # alpha.ps1 reports via Write-Host, which bypasses stdout capture;
        # the exit code is the signal (non-zero on missing required packages).
        & $alphaCli validate *> $null
        $validateStatus = if ($LASTEXITCODE -eq 0) { 'PASS' } else { 'FAIL' }
        $validateDetail = "exit=$LASTEXITCODE"
    } finally { Pop-Location }
} catch { $validateDetail = $_.Exception.Message }
Add-Check 'alpha_validate' $validateStatus $validateDetail

# --- disk free ---------------------------------------------------------------
$diskFreeGB = 0.0
try {
    $driveLetter = [System.IO.Path]::GetPathRoot($repoRoot).TrimEnd('\')
    $driveName = $driveLetter.TrimEnd(':')
    $diskFreeGB = [math]::Round(((Get-PSDrive -Name $driveName -ErrorAction Stop).Free / 1GB), 1)
} catch { }
Add-Check 'disk_free' $(if ($diskFreeGB -ge 10) { 'PASS' } elseif ($diskFreeGB -gt 0) { 'WARN' } else { 'FAIL' }) ("free_gb=" + $diskFreeGB + " drive=" + $driveLetter)

# --- running MT5 processes ----------------------------------------------------
$mt5Procs = @()
try {
    $mt5Procs = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe' OR Name='metaeditor64.exe'" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $exePath = [string]$_.ExecutablePath
            [pscustomobject][ordered]@{
                pid = [int]$_.ProcessId
                name = $_.Name
                path = $exePath
                in_isolate = ($exePath -and $exePath.StartsWith($isolateRoot, [System.StringComparison]::OrdinalIgnoreCase))
            }
        })
} catch { }
$isolateCount = @($mt5Procs | Where-Object { $_.in_isolate }).Count
$foreignCount = @($mt5Procs | Where-Object { -not $_.in_isolate }).Count
$procDetail = "isolate=$isolateCount foreign=$foreignCount" + $(if ($mt5Procs.Count) { ' pids=' + (($mt5Procs | ForEach-Object { $_.pid }) -join ',') } else { '' })
Add-Check 'mt5_processes' $(if ($foreignCount -gt 0) { 'WARN' } else { 'PASS' }) $procDetail

# --- git state -----------------------------------------------------------------
$gitDetail = ''
$gitStatus = 'WARN'
try {
    $head = (& git -C $repoRoot rev-parse HEAD 2>$null).Trim()
    $originRef = & git -C $repoRoot rev-parse --verify --quiet 'origin/main'
    if ($originRef) {
        $origin = $originRef.Trim()
        $counts = (& git -C $repoRoot rev-list --left-right --count "HEAD...$origin" 2>$null) -split '\s+'
        $ahead = [int]$counts[0]; $behind = [int]$counts[1]
    } else { $ahead = 0; $behind = -1 }
    $dirty = @(& git -C $repoRoot status --porcelain 2>$null).Count
    $hooksPath = (& git -C $repoRoot config --get core.hooksPath 2>$null)
    $gitDetail = "head=$($head.Substring(0,8)) ahead=$ahead behind=$behind dirty=$dirty hooksPath=$hooksPath"
    $gitStatus = if ($behind -gt 0 -or [string]::IsNullOrWhiteSpace($hooksPath)) { 'WARN' } else { 'PASS' }
} catch { $gitDetail = "git probe failed: $($_.Exception.Message)"; $gitStatus = 'FAIL' }
Add-Check 'git_state' $gitStatus $gitDetail

# --- aggregate -----------------------------------------------------------------
$worst = 'PASS'
foreach ($c in $checks) {
    if ($c.status -eq 'FAIL') { $worst = 'FAIL' }
    elseif ($c.status -eq 'WARN' -and $worst -ne 'FAIL') { $worst = 'WARN' }
}
$exitCode = switch ($worst) { 'PASS' { 0 } 'WARN' { 1 } default { 2 } }

$result = [ordered]@{
    schema_version = 'alphafactory_vm_doctor.v1'
    verdict = $worst
    checked_at_utc = [datetime]::UtcNow.ToString('o')
    repo_root = $repoRoot
    isolate_root = $isolateRoot
    checks = $checks.ToArray()
}

if ($Json) {
    $result | ConvertTo-Json -Depth 6
} else {
    Write-Host ("doctor: " + $worst)
    foreach ($c in $checks) {
        Write-Host ("  [" + $c.status + "] " + $c.name + " :: " + $c.detail)
    }
}
exit $exitCode
