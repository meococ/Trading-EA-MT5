param()

$ErrorActionPreference = 'Stop'
$hypothesisId = 'HYP-RSF-EURUSD-M5-ROLE-AWARE-VISUAL-004'

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Get-Evidence([string]$Label, [string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
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

$repoRoot = $PSScriptRoot
for ($i = 0; $i -lt 4; $i++) { $repoRoot = Split-Path -Parent $repoRoot }
$packetPath = Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$receiptPath = Join-Path $PSScriptRoot "$hypothesisId`_CONTRACT_RECEIPT.json"
$packet = Get-Content -Raw -LiteralPath $packetPath | ConvertFrom-Json

$sourcePath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusionForensics\EA_RegimeStructureFusionForensics.mq5'
$parentPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$contractPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusionForensics\ALPHAFACTORY_EA_CONTRACT.json'
$preregPath = Join-Path $repoRoot "03. EA Developer\EA_RegimeStructureFusionForensics\research\$hypothesisId`_FROZEN_PREREG.md"
$costPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\research\evidence\HYP-RSF-EURUSD-M5-FORENSICS-001\COST_SOURCE_MANIFEST.json'
$selectionPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\research\role_aware\HYP-RSF-EURUSD-M5-ROLE-AWARE-003_VISUAL_CASES.csv'
$registryPath = Join-Path $repoRoot '04. Memory\research\CANDIDATE_REGISTRY.jsonl'

$evidence = @(
    Get-Evidence 'task_packet' $packetPath
    Get-Evidence 'candidate_registry' $registryPath
    Get-Evidence 'source' $sourcePath
    Get-Evidence 'include_parent_ea' $parentPath
    Get-Evidence 'ea_capability_contract' $contractPath
    Get-Evidence 'prereg' $preregPath
    Get-Evidence 'cost_source_manifest' $costPath
    Get-Evidence 'selection_manifest' $selectionPath
)
foreach ($dependency in @($packet.indicator_dependencies)) {
    $evidence += Get-Evidence ("indicator_{0}_source" -f ([string]$dependency.name).ToLowerInvariant()) `
        (Join-Path $repoRoot ([string]$dependency.source))
}

$includeRecords = @($evidence | Where-Object { $_.label -like 'include_*' } | Sort-Object path | ForEach-Object {
    ([System.IO.Path]::GetFullPath([string]$_.path).ToLowerInvariant()) + "`t" + ([string]$_.sha256).ToUpperInvariant()
})
$includeClosure = Get-TextSha256 ([string]::Join("`n", $includeRecords))
$gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repoRoot status --short --untracked-files=all | ForEach-Object { [string]$_ })
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))

$binding = [ordered]@{
    hypothesis_id = $hypothesisId
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
    hypothesis_id = $hypothesisId
    task_packet_sha256 = (Get-FileHash -LiteralPath $packetPath -Algorithm SHA256).Hash
    git_commit = $gitCommit
    git_status_sha256 = $gitStatusSha
    binding = $binding
    evidence = $evidence
    generated_at_utc = [datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    note = 'Eight-case paired native MT5 visual replay. Diagnostic Model1 only; all generated performance numbers have no economic authority.'
}

$json = $receipt | ConvertTo-Json -Depth 16
[System.IO.File]::WriteAllText($receiptPath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Output ("ROLE_AWARE_VISUAL_RECEIPT_OK path={0} sha256={1} git_status_sha256={2}" -f `
    $receiptPath,
    (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash,
    $gitStatusSha)
