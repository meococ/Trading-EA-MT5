<#
.SYNOPSIS
    Session-start readiness routine for the AlphaFactory VM.
.DESCRIPTION
    1. git fetch + fast-forward only (never reset/clean/discard).
    2. Refresh PATH (C:\Python312).
    3. Authorize MetaQuotes-Demo when needed (3 branches):
         profile already authorized -> skip
         $env:MT5_DEMO_* present     -> blueprint-style ini authorize
         neither                     -> WARN "can sua repo secret"
    4. Run vm_doctor.ps1 -Json and print a <=10-line status.
    Idempotent. Exit code: 0 = PASS, 1 = WARN, 2 = FAIL. Prints no secret values.
#>
[CmdletBinding()]
param(
    [switch]$Json
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
$doctor = Join-Path $vmToolsRoot 'vm_doctor.ps1'

$lines = New-Object System.Collections.Generic.List[string]
$exitCode = 0
function Note([string]$Tag, [string]$Msg) {
    $script:lines.Add("[$Tag] $Msg")
}
function Bump([int]$Code) { if ($Code -gt $script:exitCode) { $script:exitCode = $Code } }

# --- 1. git fetch + fast-forward only ---------------------------------------
try {
    & git -C $repoRoot fetch origin --quiet 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git fetch exit=$LASTEXITCODE" }
    $origin = (& git -C $repoRoot rev-parse --verify --quiet 'origin/main')
    if (-not $origin) {
        Note 'WARN' "git: origin/main khong ton tai, bo qua ff"
        Bump 1
    } else {
        $counts = (& git -C $repoRoot rev-list --left-right --count "HEAD...origin/main") -split '\s+'
        $ahead = [int]$counts[0]; $behind = [int]$counts[1]
        if ($behind -gt 0 -and $ahead -eq 0) {
            & git -C $repoRoot merge --ff-only 'origin/main' --quiet 2>$null
            if ($LASTEXITCODE -ne 0) { throw "ff-only merge exit=$LASTEXITCODE" }
            Note 'OK' "git: fast-forward $behind commit"
        } elseif ($behind -gt 0 -and $ahead -gt 0) {
            Note 'WARN' "git: diverged (ahead=$ahead behind=$behind), khong tu merge"
            Bump 1
        } else {
            Note 'OK' "git: da cap nhat (ahead=$ahead behind=$behind)"
        }
    }
} catch {
    Note 'FAIL' "git: $($_.Exception.Message)"
    Bump 2
}

# --- 2. refresh PATH -----------------------------------------------------------
$machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
$env:Path = "$machinePath;$userPath"
foreach ($p in @('C:\Python312', 'C:\Python312\Scripts')) {
    if ((Test-Path -LiteralPath $p -PathType Container) -and ($env:Path -notlike "*$p*")) {
        $env:Path = "$p;$env:Path"
    }
}
Note 'OK' 'PATH refreshed'

# --- 3. authorize demo ---------------------------------------------------------
$authBranch = ''
try {
    $logDir = Join-Path $isolateRoot 'logs'
    $latestLog = Get-ChildItem -LiteralPath $logDir -Filter '*.log' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d{8}\.log$' } |
        Sort-Object Name | Select-Object -Last 1
    $profileAuthorized = $false
    if ($null -ne $latestLog) {
        $tail = Get-Content -LiteralPath $latestLog.FullName -Tail 400 -ErrorAction SilentlyContinue
        if (@($tail) -match 'authorized on MetaQuotes-Demo') { $profileAuthorized = $true }
    }

    $hasEnv = -not ([string]::IsNullOrEmpty($env:MT5_DEMO_LOGIN) -or [string]::IsNullOrEmpty($env:MT5_DEMO_PASSWORD))

    if ($profileAuthorized) {
        $authBranch = 'profile-authorized'
        Note 'OK' 'authorize: profile da authorized, bo qua'
    } elseif ($hasEnv) {
        $authBranch = 'env-authorize'
        $iniPath = Join-Path $env:TEMP 'mt5_login.ini'
        $ini = "[Common]`r`nLogin=$env:MT5_DEMO_LOGIN`r`nPassword=$env:MT5_DEMO_PASSWORD`r`nServer=MetaQuotes-Demo`r`n"
        Set-Content -LiteralPath $iniPath -Value $ini -Encoding Unicode
        $todayLog = Join-Path $logDir ((Get-Date -Format 'yyyyMMdd') + '.log')
        $ok = $false
        $sawRejection = $false
        $p = $null
        try {
            $p = Start-Process -FilePath (Join-Path $isolateRoot 'terminal64.exe') `
                -ArgumentList '/portable', ('/config:' + $iniPath) `
                -WorkingDirectory $isolateRoot -PassThru
            for ($j = 0; $j -lt 12; $j++) {
                Start-Sleep -Seconds 10
                if ((Test-Path $todayLog) -and ((Get-Content $todayLog -Raw -ErrorAction SilentlyContinue) -match 'authorized on MetaQuotes-Demo')) {
                    $ok = $true; break
                }
                if ((Test-Path $todayLog) -and ((Get-Content $todayLog -Raw -ErrorAction SilentlyContinue) -match 'authorization .* failed')) {
                    $sawRejection = $true; break
                }
            }
        } finally {
            if ($null -ne $p) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
            Remove-Item $iniPath -Force -ErrorAction SilentlyContinue
        }
        if ($ok) {
            Note 'OK' 'authorize: env creds authorized'
        } elseif ($sawRejection) {
            Note 'FAIL' 'authorize: env creds bi tu choi (Invalid account) - can sua repo secret values'
            Bump 2
        } else {
            # No auth line within 120 s: network/server reachability or a hung
            # terminal — distinct fault from credential rejection.
            Note 'FAIL' 'authorize: khong thay ket qua auth sau 120s (timeout/network, khong phai Invalid account)'
            Bump 2
        }
    } else {
        $authBranch = 'no-creds'
        Note 'WARN' 'authorize: khong co profile authorized va khong co $env:MT5_DEMO_* - can sua repo secret'
        Bump 1
    }
} catch {
    Note 'FAIL' "authorize: $($_.Exception.Message)"
    Bump 2
}

# --- 4. doctor ------------------------------------------------------------------
$doctorJson = $null
try {
    $doctorRaw = & powershell -NoProfile -ExecutionPolicy Bypass -File $doctor -Json
    $doctorJson = $doctorRaw | ConvertFrom-Json
    $doctorCode = $LASTEXITCODE
    Bump $doctorCode
} catch {
    Note 'FAIL' "doctor: $($_.Exception.Message)"
    Bump 2
}

if ($Json) {
    [ordered]@{
        schema_version = 'alphafactory_vm_start.v1'
        verdict = $(switch ($exitCode) { 0 { 'PASS' } 1 { 'WARN' } default { 'FAIL' } })
        auth_branch = $authBranch
        lines = $lines.ToArray()
        doctor = $doctorJson
    } | ConvertTo-Json -Depth 8
} else {
    $shown = 0
    foreach ($l in $lines) {
        if ($shown -ge 9) { break }
        Write-Host $l
        $shown++
    }
    if ($null -ne $doctorJson) {
        Write-Host ("[doctor] " + $doctorJson.verdict)
    }
}
exit $exitCode
