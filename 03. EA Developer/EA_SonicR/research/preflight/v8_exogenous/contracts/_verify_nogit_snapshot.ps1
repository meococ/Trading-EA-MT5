$ErrorActionPreference = "Stop"
$AdvisorsRoot = "d:\Trading EA MT5"

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes([string]$Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "")
    } finally {
        $sha.Dispose()
    }
}

function Test-NoGitWorkspace {
    $gitDir = Join-Path $AdvisorsRoot ".git"
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $insideOutput = @(& git -C $AdvisorsRoot rev-parse --is-inside-work-tree 2>$null)
        $insideExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldEap
    }
    $inside = ""
    if ($null -ne $insideOutput -and @($insideOutput).Count -gt 0 -and $null -ne $insideOutput[0]) {
        $inside = ([string]$insideOutput[0]).Trim()
    }
    if (($insideExit -eq 0) -and ($inside -ceq "true")) { return $false }
    if (Test-Path -LiteralPath $gitDir) {
        $entries = @(Get-ChildItem -LiteralPath $gitDir -Force -ErrorAction SilentlyContinue)
        if ($entries.Count -eq 0) { return $true }
        return $true
    }
    return $true
}

function Get-NoGitProvenanceSnapshot {
    $agentsPath = Join-Path $AdvisorsRoot "AGENTS.md"
    $goalPath = Join-Path $AdvisorsRoot "01. GOAL\GOAL.md"
    $provenancePaths = @($agentsPath, $goalPath)
    foreach ($required in $provenancePaths) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "NO-GIT provenance file missing (fail-closed): $required"
        }
    }
    $activeEa = Join-Path $AdvisorsRoot "03. EA Developer\EA_CarryPublicRates\EA_CarryPublicRates.mq5"
    if (Test-Path -LiteralPath $activeEa -PathType Leaf) {
        $provenancePaths += $activeEa
    }
    $records = New-Object System.Collections.Generic.List[string]
    foreach ($path in $provenancePaths) {
        $full = [System.IO.Path]::GetFullPath($path)
        $rootFull = [System.IO.Path]::GetFullPath($AdvisorsRoot).TrimEnd("\", "/")
        $rel = if ($full.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            $full.Substring($rootFull.Length).TrimStart("\", "/").Replace("\", "/")
        } else {
            $full.Replace("\", "/")
        }
        $fileHash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToUpperInvariant()
        $records.Add(("$rel`t$fileHash"))
    }
    $payload = [string]::Join("`n", @($records))
    $provSha = (Get-TextSha256 $payload).ToUpperInvariant()
    $commit = "NOGIT-$provSha"
    $statusLines = @("nogit=true", "dirty=true", "provenance_sha256=$provSha")
    return [pscustomobject]@{
        Commit = $commit
        Status = $statusLines
        StatusSha256 = Get-TextSha256 ([string]::Join("`n", $statusLines))
        NoGit = $true
        Dirty = $true
    }
}

$alpha = Get-Content -LiteralPath (Join-Path $AdvisorsRoot "02. AlphaFactory\alpha.ps1") -Raw
if ($alpha -notmatch "function Get-NoGitProvenanceSnapshot") { throw "alpha.ps1 missing Get-NoGitProvenanceSnapshot" }
if ($alpha -notmatch "function Test-NoGitWorkspace") { throw "alpha.ps1 missing Test-NoGitWorkspace" }
Write-Output "PATCH_OK=true"

if (-not (Test-NoGitWorkspace)) { throw "Expected NO-GIT workspace" }
$s = Get-NoGitProvenanceSnapshot
Write-Output ("PS_COMMIT=" + $s.Commit)
Write-Output ("PS_STATUS_SHA=" + $s.StatusSha256)

$receiptPath = Join-Path $AdvisorsRoot "03. EA Developer\EA_SonicR\research\preflight\v8_exogenous\contracts\20260713_HYP_CARRY_PUBLIC_RATES_D1_001_CONTRACT_RECEIPT.json"
$r = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
Write-Output ("RECEIPT_COMMIT=" + $r.git_commit)
Write-Output ("RECEIPT_STATUS_SHA=" + $r.git_status_sha256)
Write-Output ("MATCH_COMMIT=" + ($r.git_commit -ceq $s.Commit))
Write-Output ("MATCH_STATUS=" + ($r.git_status_sha256 -ieq $s.StatusSha256))
Write-Output ("RECEIPT_FILE_SHA=" + (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash)
