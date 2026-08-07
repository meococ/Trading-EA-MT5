param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-[0-9]{3}(-C0[1-7])?$')]
    [string]$HypothesisId,
    [ValidatePattern('^HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-[0-9]{3}$')]
    [string]$PreregHypothesisId = ''
)

$ErrorActionPreference = 'Stop'

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = New-Object System.Text.UTF8Encoding($false)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes.GetBytes($Text)))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-Evidence([string]$Label, [string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "Missing receipt evidence ${Label}: $full"
    }
    return [ordered]@{
        label = $Label
        kind = 'file'
        path = $full
        sha256 = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
    }
}

$repo = $PSScriptRoot
for ($i = 0; $i -lt 4; $i++) { $repo = Split-Path -Parent $repo }
$packetPath = Join-Path $PSScriptRoot ("{0}_TASK_PACKET.json" -f $HypothesisId)
$receiptPath = Join-Path $PSScriptRoot ("{0}_CONTRACT_RECEIPT.json" -f $HypothesisId)
$packet = Get-Content -Raw -LiteralPath $packetPath | ConvertFrom-Json

$sourcePath = Join-Path $repo '03. EA Developer\EA_RegimeStructureFusionForensics\EA_RegimeStructureFusionForensics.mq5'
$parentPath = Join-Path $repo '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$contractPath = Join-Path $repo '03. EA Developer\EA_RegimeStructureFusionForensics\ALPHAFACTORY_EA_CONTRACT.json'
$preregId = if ([string]::IsNullOrWhiteSpace($PreregHypothesisId)) { $HypothesisId } else { $PreregHypothesisId }
$preregPath = Join-Path $repo ("03. EA Developer\EA_RegimeStructureFusionForensics\research\{0}_FROZEN_PREREG.md" -f $preregId)
$costPath = Join-Path $repo '03. EA Developer\EA_RegimeStructureFusion\research\evidence\HYP-RSF-EURUSD-M5-FORENSICS-001\COST_SOURCE_MANIFEST.json'
$registryPath = Join-Path $repo '04. Memory\research\CANDIDATE_REGISTRY.jsonl'

$evidence = @(
    Get-Evidence 'task_packet' $packetPath
    Get-Evidence 'candidate_registry' $registryPath
    Get-Evidence 'source' $sourcePath
    Get-Evidence 'include_parent_ea' $parentPath
    Get-Evidence 'ea_capability_contract' $contractPath
    Get-Evidence 'prereg' $preregPath
    Get-Evidence 'cost_source_manifest' $costPath
)
foreach ($dep in @($packet.indicator_dependencies)) {
    $evidence += Get-Evidence ("indicator_{0}_source" -f ([string]$dep.name).ToLowerInvariant()) (Join-Path $repo ([string]$dep.source))
}

$includeRecords = @($evidence | Where-Object { $_.label -like 'include_*' } | Sort-Object path | ForEach-Object {
    ([IO.Path]::GetFullPath([string]$_.path).ToLowerInvariant()) + "`t" + ([string]$_.sha256).ToUpperInvariant()
})
$includeClosure = Get-TextSha256 ([string]::Join("`n", $includeRecords))

$gitCommit = (& git -C $repo rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repo status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))

$binding = [ordered]@{
    hypothesis_id = [string]$packet.hypothesis_id
    run_role = [string]$packet.run_role
    ea_name = [string]$packet.ea_name
    symbol = [string]$packet.symbol
    period = [string]$packet.period
    from = [string]$packet.from
    to = [string]$packet.to
    model = [int]$packet.model
    execution_mode = [int]$packet.execution_mode
    fixed_delay_ms = [int]$packet.fixed_delay_ms
    overrides = [string]$packet.overrides
    telemetry_tier = [string]$packet.telemetry_tier
    telemetry_profile = [string]$packet.telemetry_profile
    deposit = [int]$packet.deposit
    leverage = [int]$packet.leverage
    spread = [string]$packet.spread
    visual_mode = $true
    required_sidecars = @($packet.required_sidecars)
    indicator_dependencies = @($packet.indicator_dependencies)
    symbol_geometry = [ordered]@{ digits = 5; point = 0.00001; pip_size = 0.0001 }
    include_closure_sha256 = $includeClosure
}

$receipt = [ordered]@{
    schema_version = 'alphafactory_execution_receipt.v1'
    hypothesis_id = [string]$packet.hypothesis_id
    task_packet_sha256 = (Get-FileHash -LiteralPath $packetPath -Algorithm SHA256).Hash
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
    binding = $binding
    evidence = $evidence
    generated_at_utc = [datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    note = 'Frozen seven-case post-exit native MT5 visual replay. Model 1 and all generated performance numbers have no economic authority.'
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 16), $utf8)
$receiptSha = (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash
Write-Host "NATIVE_OUTCOME_RECEIPT_OK path=$receiptPath sha256=$receiptSha git_status_sha256=$gitStatusSha"
