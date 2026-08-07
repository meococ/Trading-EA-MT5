param()

$ErrorActionPreference = 'Stop'
$hypothesisId = 'HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-FIX-007'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$packetPath = Join-Path $PSScriptRoot "$hypothesisId`_TASK_PACKET.json"
$receiptPath = Join-Path $PSScriptRoot "$hypothesisId`_CONTRACT_RECEIPT.json"
$sourcePath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5'
$contractPath = Join-Path $repoRoot '03. EA Developer\EA_RegimeStructureFusion\ALPHAFACTORY_EA_CONTRACT.json'
$preregPath = Join-Path $PSScriptRoot "$hypothesisId`_FROZEN_PREREG.md"
$costPath = Join-Path $PSScriptRoot "$hypothesisId`_COST_SOURCE_MANIFEST.json"
$registryPath = Join-Path $repoRoot '04. Memory\research\CANDIDATE_REGISTRY.jsonl'

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

$packet = Get-Content -Raw -LiteralPath $packetPath | ConvertFrom-Json
if ([string]$packet.hypothesis_id -cne $hypothesisId) {
    throw "Task packet hypothesis mismatch: '$($packet.hypothesis_id)'"
}
if ([string]$packet.run_role -cne 'control') {
    throw "Development falsification packet must use run_role=control."
}

$evidence = @(
    Get-Evidence 'task_packet' $packetPath
    Get-Evidence 'candidate_registry' $registryPath
    Get-Evidence 'source' $sourcePath
    Get-Evidence 'ea_capability_contract' $contractPath
    Get-Evidence 'prereg' $preregPath
    Get-Evidence 'cost_source_manifest' $costPath
)
foreach ($dependency in @($packet.indicator_dependencies)) {
    $dependencyPath = Join-Path $repoRoot (([string]$dependency.source).Replace('/', '\'))
    $evidence += Get-Evidence ("indicator_{0}_source" -f ([string]$dependency.name).ToLowerInvariant()) $dependencyPath
}

$gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
$gitStatus = @(& git -C $repoRoot status --short --untracked-files=all | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) {
    throw 'git status failed'
}
$gitStatusSha = Get-TextSha256 ([string]::Join("`n", $gitStatus))

$binding = [ordered]@{
    hypothesis_id = $hypothesisId
    run_role = 'control'
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
    # AlphaFactory normalizes an omitted CLI spread to the explicit tester value
    # "current" before receipt validation.
    spread = [string]$packet.spread
    visual_mode = $false
    required_sidecars = @($packet.required_sidecars)
    indicator_dependencies = @($packet.indicator_dependencies)
    symbol_geometry = [ordered]@{
        digits = [int]$packet.symbol_geometry.digits
        point = [double]$packet.symbol_geometry.point
        pip_size = [double]$packet.symbol_geometry.pip_size
    }
    include_closure_sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
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
    note = 'Exactly one EURUSD M5 2018-2022 Model0 development falsification run for the frozen causal liquidity pool after the optional-buffer read correction. No optimization, validation, holdout or promotion authority.'
}

$json = $receipt | ConvertTo-Json -Depth 16
[System.IO.File]::WriteAllText($receiptPath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Output ("LIQUIDITY_POOL_FIX_RECEIPT_OK path={0} sha256={1} git_status_sha256={2}" -f `
    $receiptPath,
    (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash,
    $gitStatusSha)
