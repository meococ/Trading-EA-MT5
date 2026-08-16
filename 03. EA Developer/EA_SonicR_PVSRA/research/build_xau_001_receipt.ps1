param(
    [string]$From = '2016.01.01',
    [string]$To = '2023.12.31',
    [string]$ReceiptName = 'contract_receipt.control.json',
    [string]$HypothesisId = 'HYP-SONICR-XAU-M15-BAND-001',
    [string]$Symbol = 'XAUUSD',
    [int]$Digits = 2,
    [double]$Point = 0.01,
    [double]$PipSize = 0.01,
    [string]$Overrides = 'InpHypothesisId=HYP-SONICR-XAU-M15-BAND-001;InpMagic=16081704;InpMaxSpreadPoints=500;InpMaxTradesPerWeek=3;InpMinTpPips=2000;InpNyEndHour=17;InpOffsetPoints=50;InpPipSize=0.01;InpRoundWhole=10.0;InpSlCapPips=2000;InpUseNySession=true;InpVariantTag=XAU_BAND_WHOLE'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package = Join-Path $repo '03. EA Developer\EA_SonicR_PVSRA'
$preflight = Join-Path $package "research\preflight\$HypothesisId"
$taskPath = if ($ReceiptName -eq 'contract_receipt.smoke.json') {
    Join-Path $package "research\${HypothesisId}_SMOKE_TASK.json"
} else {
    Join-Path $package "research\${HypothesisId}_BASELINE_TASK.json"
}
$receiptPath = Join-Path $preflight $ReceiptName
$sourcePath = Join-Path $package 'EA_SonicR_PVSRA.mq5'
$preregPath = Join-Path $package "research\${HypothesisId}_FROZEN_PREREG.md"
$costPath = Join-Path $package "research\${HypothesisId}_COST_SOURCE_MANIFEST.json"
$registryPath = Join-Path $repo '04. Memory\research\CANDIDATE_REGISTRY.jsonl'

function Get-TextSha256([string]$text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-FileSha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Write-Utf8Json($value, [string]$path) {
    $json = $value | ConvertTo-Json -Depth 16
    [IO.File]::WriteAllText($path, $json + "`n", [Text.UTF8Encoding]::new($false))
}

New-Item -ItemType Directory -Path $preflight -Force | Out-Null
if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
    [IO.File]::WriteAllText($receiptPath, "{}" + "`n", [Text.UTF8Encoding]::new($false))
}

foreach ($path in @($taskPath, $receiptPath, $sourcePath, $preregPath, $costPath, $registryPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing required path: $path"
    }
}

$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))
$emptyIncludeSha = Get-TextSha256 ''

$receipt = [ordered]@{
    schema_version = 'alphafactory_execution_receipt.v1'
    hypothesis_id = $HypothesisId
    task_packet_sha256 = Get-FileSha256 $taskPath
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
    binding = [ordered]@{
        hypothesis_id = $HypothesisId
        run_role = 'control'
        ea_name = 'EA_SonicR_PVSRA'
        symbol = $Symbol
        period = 'M15'
        from = $From
        to = $To
        model = 1
        execution_mode = 0
        fixed_delay_ms = 0
        overrides = $Overrides
        telemetry_tier = 'off'
        telemetry_profile = 'none'
        deposit = 10000
        leverage = 100
        spread = 'current'
        required_sidecars = @()
        symbol_geometry = [ordered]@{ digits = $Digits; point = $Point; pip_size = $PipSize }
        include_closure_sha256 = $emptyIncludeSha
        portable = '02. AlphaFactory/runtime/mt5-portable-mqdemo'
        server = 'MetaQuotes-Demo'
        cost_source = 'MetaQuotes-Demo'
        login = '5054517252'
    }
    evidence = @(
        [ordered]@{ label = 'task_packet'; kind = 'file'; path = $taskPath; sha256 = Get-FileSha256 $taskPath }
        [ordered]@{ label = 'source'; kind = 'file'; path = $sourcePath; sha256 = Get-FileSha256 $sourcePath }
        [ordered]@{ label = 'prereg'; kind = 'file'; path = $preregPath; sha256 = Get-FileSha256 $preregPath }
        [ordered]@{ label = 'cost_source_manifest'; kind = 'file'; path = $costPath; sha256 = Get-FileSha256 $costPath }
        [ordered]@{ label = 'candidate_registry'; kind = 'file'; path = $registryPath; sha256 = Get-FileSha256 $registryPath }
    )
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    note = 'XAUUSD M15 Dragon pull. Tester-only MQ Demo. Registry read-only. Not Classic first-break salvage.'
}
Write-Utf8Json $receipt $receiptPath

[ordered]@{
    receipt = $receiptPath
    receipt_sha256 = Get-FileSha256 $receiptPath
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
} | ConvertTo-Json -Depth 4
