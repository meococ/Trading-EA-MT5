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

# 2026-09-11: warn on untracked files with forbidden names (alpha.local.ps1,
# .mcp.json, *.parquet, keys, credentials). They cannot enter this commit, but
# they are one blanket `git add` away — surface them instead of staying quiet.
$untracked = @(Get-GitUntrackedForbidden -RepoRoot $repo)
if ($untracked.Count -gt 0) {
    [Console]::Error.WriteLine('pre-commit warning: forbidden-name files are untracked (not committed, but one blanket git add away):')
    foreach ($item in $untracked) {
        [Console]::Error.WriteLine("  $item")
    }
}
exit 0
