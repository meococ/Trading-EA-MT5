# Git pre-commit: same hygiene regex as the Grok git/secret hook.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
. (Join-Path $here '..\.grok\hooks\bin\hygiene.ps1')

$repo = (git rev-parse --show-toplevel).Trim()
if (-not $repo) {
    Write-Error 'git rev-parse --show-toplevel failed'
    exit 1
}

$violations = @(Get-GitStagedViolations -RepoRoot $repo)
if ($violations.Count -gt 0) {
    [Console]::Error.WriteLine('pre-commit blocked:')
    foreach ($item in $violations) {
        [Console]::Error.WriteLine("  $item")
    }
    [Console]::Error.WriteLine('Stage named files only. Do not commit secrets, parquet, alpha.local.ps1, MCP config, deal dumps, or machine-local profile paths.')
    exit 1
}
exit 0
