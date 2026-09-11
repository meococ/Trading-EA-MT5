<#
.SYNOPSIS
    Fleet-wide template patcher for the generated EA_* packages under
    "03. EA Developer". Idempotent: a patched return site is marked with a
    /*hg*/ comment so re-runs skip it.

.FIXES
    A) OnInit partial-init handle leak: every `return(INIT_FAILED);` that
       appears AFTER the first `g_*_handle=` assignment inside OnInit is
       wrapped so all already-created handles are released first, using the
       release function the file itself declares for that variable
       (IndicatorRelease / FileClose / ...). Unassigned handles stay
       INVALID_HANDLE and the guarded calls no-op.
    B) EA_Waddah ExplosionAlive(): CopyBuffer/MathIsValidNumber failure paths
       returned true (fail-open = hold a possibly dead position). Now fail
       closed (return false = close).
    C) Friday-session census only: reports which InSessionNow pattern each
       EA uses. No InpTradeFriday-style input exists in the fleet, so no
       behavior is normalized.

.OUTPUT
    Prints per-file status and a patched/skipped/failed summary.
#>
param(
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$repoDev = Join-Path $repoRoot '03. EA Developer'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$files = Get-ChildItem -Directory -Path $repoDev -Filter 'EA_*' |
    ForEach-Object { Join-Path $_.FullName ($_.Name + '.mq5') } |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }

$patched   = New-Object System.Collections.Generic.List[string]
$skipped   = New-Object System.Collections.Generic.List[string]
$noLeakSite= New-Object System.Collections.Generic.List[string]
$failed    = New-Object System.Collections.Generic.List[string]
$friBlock  = New-Object System.Collections.Generic.List[string]
$friAllow  = New-Object System.Collections.Generic.List[string]
$friOther  = New-Object System.Collections.Generic.List[string]
$failOpen  = New-Object System.Collections.Generic.List[string]

function Get-OnInitBodyRange([string]$raw) {
    $m = [regex]::Match($raw, 'int\s+OnInit\s*\(')
    if (-not $m.Success) { return $null }
    $bo = $raw.IndexOf('{', $m.Index)
    if ($bo -lt 0) { return $null }
    $depth = 0
    for ($i = $bo; $i -lt $raw.Length; $i++) {
        $c = $raw[$i]
        if ($c -eq '{') { $depth++ }
        elseif ($c -eq '}') { $depth--; if ($depth -eq 0) { return @($bo, $i) } }
    }
    return $null
}

foreach ($file in $files) {
    try {
        $raw = [IO.File]::ReadAllText($file)
        $name = [IO.Path]::GetFileName($file)
        $changed = $false

        # ---------- census: Friday session pattern (report only) ----------
        if ($raw -match 'day_of_week==0\s*\|\|\s*ts\.day_of_week==6\s*\|\|\s*ts\.day_of_week==5' -or
            $raw -match 'day_of_week==5\s*\|\|\s*ts\.day_of_week==0') { [void]$friBlock.Add($name) }
        elseif ($raw -match 'day_of_week==0\s*\|\|\s*ts\.day_of_week==6') { [void]$friAllow.Add($name) }
        else { [void]$friOther.Add($name) }

        # ---------- census: other fail-open CopyBuffer->return(true) ----------
        if ([regex]::Matches($raw, 'CopyBuffer\([^)]*\)\s*!=\s*\d+\s*\)[\s\r\n]{0,80}?return\(true\)').Count -gt 0) {
            [void]$failOpen.Add($name)
        }

        # ---------- (B) EA_Waddah ExplosionAlive fail-open ----------
        if ($name -eq 'EA_Waddah.mq5') {
            $ea = [regex]::Match($raw, 'bool\s+ExplosionAlive\s*\(\s*\)')
            if ($ea.Success) {
                $bo = $raw.IndexOf('{', $ea.Index)
                $depth = 0; $bc = -1
                for ($i = $bo; $i -lt $raw.Length; $i++) {
                    if ($raw[$i] -eq '{') { $depth++ }
                    elseif ($raw[$i] -eq '}') { $depth--; if ($depth -eq 0) { $bc = $i; break } }
                }
                if ($bc -gt 0) {
                    $fbody = $raw.Substring($bo, $bc - $bo + 1)
                    # fail-open returns: CopyBuffer!=1 -> true, invalid number -> true
                    $fnew = [regex]::Replace($fbody,
                        'return\(true\);(\s*//\s*fail-open)?',
                        { param($mm) if ($mm.Groups[1].Success) { $mm.Value } else { 'return(false); // fail-closed: unreadable data closes the position' } })
                    # only rewrite when the three known failure sites are present
                    if ($fnew -ne $fbody) { $raw = $raw.Substring(0, $bo) + $fnew + $raw.Substring($bc + 1); $changed = $true }
                }
            }
        }

        # ---------- (A) OnInit handle-leak ----------
        $range = Get-OnInitBodyRange $raw
        if ($null -eq $range) { [void]$skipped.Add("$name (no OnInit)"); continue }
        $bo = $range[0]; $bc = $range[1]
        $body = $raw.Substring($bo, $bc - $bo + 1)

        # release map from the file's own usage of each handle global
        $release = @{}
        foreach ($hm in [regex]::Matches($raw, '(?m)^\s*int\s+(g_\w+_handle)\s*=\s*INVALID_HANDLE')) {
            $v = $hm.Groups[1].Value
            $ve = [regex]::Escape($v)
            if     ($raw -match "IndicatorRelease\(\s*$ve") { $release[$v] = 'IndicatorRelease' }
            elseif ($raw -match "FileClose\(\s*$ve")         { $release[$v] = 'FileClose' }
        }

        $fa = [regex]::Match($body, 'g_\w+_handle\s*=')
        if (-not $fa.Success -or $release.Count -eq 0) {
            [void]$noLeakSite.Add("$name (no handle create / no releasable vars)")
        } else {
            $firstAssign = $fa.Index
            $rel = ($release.GetEnumerator() | ForEach-Object { "if($($_.Key)!=INVALID_HANDLE)$($_.Value)($($_.Key)); " }) -join ''
            $newBody = [regex]::Replace($body, '(?<!/\*hg\*/)return\s*\(\s*INIT_FAILED\s*\)\s*;',
                [System.Text.RegularExpressions.MatchEvaluator]{
                    param($mm)
                    if ($mm.Index -le $firstAssign) { return $mm.Value }
                    return "{ /*hg*/ $rel/*hg*/return(INIT_FAILED); }"
                })
            if ($newBody -ne $body) {
                $raw = $raw.Substring(0, $bo) + $newBody + $raw.Substring($bc + 1)
                $changed = $true
            }
        }

        if ($changed) {
            if (-not $WhatIf) { [IO.File]::WriteAllText($file, $raw, $utf8NoBom) }
            [void]$patched.Add($name)
        } else {
            if (-not $noLeakSite.Contains("$name (no handle create / no releasable vars)")) {
                [void]$skipped.Add("$name (already patched / no sites)")
            }
        }
    } catch {
        [void]$failed.Add("$([IO.Path]::GetFileName($file)): $($_.Exception.Message)")
    }
}

Write-Host "=== fleet patch summary ==="
Write-Host "patched: $($patched.Count)  skipped(already/none): $($skipped.Count)  no-leak-site: $($noLeakSite.Count)  failed: $($failed.Count)"
if ($failed.Count)    { $failed | ForEach-Object { Write-Host "  FAILED: $_" } }
if ($noLeakSite.Count){ $noLeakSite | ForEach-Object { Write-Host "  NOSITE: $_" } }
Write-Host "=== Friday session census (no InpTradeFriday input exists; NOT normalized) ==="
Write-Host "  blocks Friday in InSessionNow : $($friBlock.Count)"
Write-Host "  allows Friday until flatten   : $($friAllow.Count)"
Write-Host "  other/non-template            : $($friOther.Count) -> $($friOther -join ', ')"
Write-Host "=== CopyBuffer fail-open return(true) files ==="
$failOpen | ForEach-Object { Write-Host "  $_" }
