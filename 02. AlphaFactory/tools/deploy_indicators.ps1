#requires -Version 5.1
<#
.SYNOPSIS
  Deploy iCustom indicator dependencies for an EA package into the portable
  isolate's MQL5\Indicators\Trading-EA-MT5\ folder.

.DESCRIPTION
  Fleet EAs resolve indicators via iCustom(_Symbol,_Period,"Trading-EA-MT5\\IND_X",...)
  with a bare "IND_X" fallback. The MT5 tester resolves that path relative to the
  isolate MQL5\Indicators root. This tool:

    1. Parses the EA source for iCustom("...IND_NAME" ...) dependencies.
    2. Compiles each IND_* package via alpha.ps1 (fresh 0 errors/0 warnings EX5).
    3. Copies the fresh EX5 to <isolate>\MQL5\Indicators\Trading-EA-MT5\IND_X.ex5
       and to the bare Indicators root (satisfies the fallback path).
    4. Writes a deploy receipt JSON next to the EA's research/ dir.

  Fail-closed: any compile failure or missing artifact aborts the run.

.EXAMPLE
  & ./tools/deploy_indicators.ps1 -EaName EA_CrsiR2
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$EaName
)

$ErrorActionPreference = 'Stop'
$ToolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AlphaRoot = Split-Path -Parent $ToolsDir
$RepoRoot = Split-Path -Parent $AlphaRoot
$EaDir = Join-Path $RepoRoot "03. EA Developer\$EaName"
$AlphaPs1 = Join-Path $AlphaRoot 'alpha.ps1'

# .NET SHA256, not Get-FileHash: PS 5.1 children of pwsh 7 inherit a foreign
# PSModulePath and lose Microsoft.PowerShell.Utility autoload.
function Get-Sha256Hex([string]$Path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $fs = [System.IO.File]::OpenRead($Path)
        try { return ([BitConverter]::ToString($sha.ComputeHash($fs))).Replace('-', '') }
        finally { $fs.Dispose() }
    } finally { $sha.Dispose() }
}

$IndicatorsRoot = Join-Path $AlphaRoot 'runtime\mt5-portable-mqdemo\MQL5\Indicators'
$DeploySubDir = Join-Path $IndicatorsRoot 'Trading-EA-MT5'

$main = Get-ChildItem -LiteralPath $EaDir -Filter "$EaName.mq5" -File -ErrorAction Stop |
        Select-Object -First 1
$src = Get-Content -LiteralPath $main.FullName -Raw

# iCustom(...,"Trading-EA-MT5\\NAME" or "IND_X", ...) -> unique dependency names.
# Fleet convention is IND_*, but legacy shelf indicators (e.g.
# Modern_Bollinger_Bands_GBB) are referenced under the Trading-EA-MT5\ prefix
# without the IND_ prefix; both shapes must deploy or the tester fails iCustom
# resolution at OnInit.
$depNames = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase)
foreach ($m in [regex]::Matches($src, 'iCustom\s*\([^,]+,[^,]+,\s*"(?:Trading-EA-MT5\\+([A-Za-z0-9_]+)|(IND_[A-Za-z0-9_]+))"')) {
    $name = if ($m.Groups[1].Success) { $m.Groups[1].Value } else { $m.Groups[2].Value }
    [void]$depNames.Add($name)
}

if ($depNames.Count -eq 0) {
    Write-Host "[deploy] $EaName has no iCustom IND_* dependencies." -ForegroundColor Cyan
    exit 0
}

New-Item -ItemType Directory -Path $DeploySubDir -Force | Out-Null

$receipt = [ordered]@{
    ea            = $EaName
    deployed_at   = (Get-Date).ToUniversalTime().ToString('o')
    indicators    = @()
}

foreach ($ind in ($depNames | Sort-Object)) {
    Write-Host "[deploy] compile $ind via alpha.ps1 ..." -ForegroundColor Cyan
    # MetaEditor exit code 1 is a successful CLI compile on this build and any
    # child stderr text can flip $? — so gate on the success line + fresh EX5.
    # *>&1 is required: alpha.ps1 logs via Write-Host (stream 6), not stdout.
    $compileOut = & $AlphaPs1 compile $ind *>&1 | Out-String
    if ($compileOut -notmatch '0 errors, 0 warnings' -or $compileOut -match 'Compile failed') {
        throw "[deploy] compile failed for $ind`n$compileOut"
    }

    $ex5 = Join-Path $RepoRoot "03. EA Developer\$ind\$ind.ex5"
    if (-not (Test-Path -LiteralPath $ex5 -PathType Leaf)) {
        throw "[deploy] EX5 missing after compile: $ex5"
    }
    $hash = Get-Sha256Hex $ex5

    $dstNested = Join-Path $DeploySubDir "$ind.ex5"
    $dstBare = Join-Path $IndicatorsRoot "$ind.ex5"
    Copy-Item -LiteralPath $ex5 -Destination $dstNested -Force
    Copy-Item -LiteralPath $ex5 -Destination $dstBare -Force
    foreach ($d in @($dstNested, $dstBare)) {
        if ((Get-Sha256Hex $d) -ne $hash) {
            throw "[deploy] copy hash mismatch for $d"
        }
    }
    $receipt.indicators += [ordered]@{
        name = $ind; ex5_sha256 = $hash; nested = $dstNested; bare = $dstBare
    }
    Write-Host "[deploy] $ind -> Indicators\Trading-EA-MT5\ + Indicators\ (sha256 $($hash.Substring(0,12))...)" -ForegroundColor Green
}

$researchDir = Join-Path $EaDir 'research'
if (Test-Path -LiteralPath $researchDir) {
    $receiptPath = Join-Path $researchDir 'indicator_deploy_receipt.json'
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    Write-Host "[deploy] receipt -> $receiptPath" -ForegroundColor Green
}
exit 0
