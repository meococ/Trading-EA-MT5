param(
    [Parameter(Mandatory = $true)]
    [string]$RunDir,
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
$repoRoot = Split-Path -Parent $alphaRoot
$runsRoot = [System.IO.Path]::GetFullPath((Join-Path $alphaRoot 'runs')).TrimEnd('\', '/')
$resolvedRun = if ([System.IO.Path]::IsPathRooted($RunDir)) {
    [System.IO.Path]::GetFullPath($RunDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $RunDir))
}
if (-not $resolvedRun.StartsWith("$runsRoot\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "RunDir must resolve below the AlphaFactory runs root: $resolvedRun"
}

$manifestPath = Join-Path $resolvedRun 'run_manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Run manifest is missing: $manifestPath"
}
$alphaPath = Join-Path $alphaRoot 'alpha.ps1'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

# Reuse production functions directly from alpha.ps1 without executing its CLI
# main block.  This keeps historical revalidation on the same parser and gate
# semantics as a fresh AlphaFactory run.
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $alphaPath,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -gt 0) {
    throw ($parseErrors | ForEach-Object { $_.Message } | Out-String)
}
$requiredFunctions = @(
    'Get-Sha256Required',
    'Get-ObjectPropertyValue',
    'ConvertTo-ResearchDate',
    'ConvertTo-FiniteInvariantDouble',
    'Get-DataQualityHistoryRange',
    'Get-DataQualitySeriesProof',
    'Get-ReportLabeledValue',
    'Assert-DataQualityRunEvidence'
)
foreach ($name in $requiredFunctions) {
    $functionAst = $ast.Find({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -ceq $name
    }, $true)
    if ($null -eq $functionAst) {
        throw "Production data-quality helper is missing from alpha.ps1: $name"
    }
    Invoke-Expression $functionAst.Extent.Text
}

$gate = Assert-DataQualityRunEvidence $manifest
if ($null -eq $gate) {
    throw 'Run manifest has no data_quality_contract and cannot be revalidated.'
}

$target = if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    Join-Path $resolvedRun 'analysis\data_quality_revalidation.json'
} elseif ([System.IO.Path]::IsPathRooted($OutputPath)) {
    [System.IO.Path]::GetFullPath($OutputPath)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputPath))
}
$analysisRoot = [System.IO.Path]::GetFullPath((Join-Path $resolvedRun 'analysis')).TrimEnd('\', '/')
if (-not $target.StartsWith("$analysisRoot\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputPath must stay below the run analysis directory: $target"
}
New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
$journalPath = [System.IO.Path]::GetFullPath((Join-Path $resolvedRun ([string]$manifest.data_quality_journal_delta.path)))

$receipt = [ordered]@{
    schema_version = 'alphafactory_data_quality_revalidation.v1'
    generated_at_utc = [datetime]::UtcNow.ToString('o')
    run_id = [string]$manifest.run_id
    hypothesis_id = [string]$manifest.hypothesis_id
    run_dir = $resolvedRun
    revalidation_mode = 'ARTIFACT_ONLY_NO_MT5_RELAUNCH'
    original_manifest_path = $manifestPath
    original_manifest_sha256 = Get-Sha256Required $manifestPath 'Run manifest'
    production_validator_path = $alphaPath
    production_validator_sha256 = Get-Sha256Required $alphaPath 'AlphaFactory production validator'
    report_path = [string]$manifest.report_path
    report_sha256 = Get-Sha256Required ([string]$manifest.report_path) 'Run report'
    journal_path = $journalPath
    journal_sha256 = Get-Sha256Required $journalPath 'Run journal delta'
    verdict = 'PASS'
    data_quality_gate = $gate
}

$json = $receipt | ConvertTo-Json -Depth 16
[System.IO.File]::WriteAllText($target, $json + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Output $target
Write-Output (Get-Sha256Required $target 'Data-quality revalidation receipt')
