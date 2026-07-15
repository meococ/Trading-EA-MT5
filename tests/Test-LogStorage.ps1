[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = Split-Path -Parent $PSScriptRoot
$module = Join-Path $repo '02. AlphaFactory\tools\log_storage.ps1'
$dedupe = Join-Path $repo '02. AlphaFactory\tools\dedupe_backtest_log_mirrors.ps1'
. $module

$root = Join-Path $repo '02. AlphaFactory\runtime\test_log_storage'
if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
New-Item -ItemType Directory -Path $root -Force | Out-Null
$assertions = 0
try {
    $source = Join-Path $root 'source.csv'
    Set-Content -LiteralPath $source -Value @('header','row1','row2') -Encoding UTF8
    $primaryDir = Join-Path $root 'primary'
    $mirrorDir = Join-Path $root 'mirror'
    $copy = Copy-AlphaLogWithMirror -Source $source -PrimaryDirectory $primaryDir -MirrorDirectory $mirrorDir -AllowCopyFallback $false
    if ($copy.mode -ne 'hardlink' -or $copy.physical_duplicate_bytes -ne 0) { throw 'New mirror was not a hardlink.' }
    if (-not $copy.same_physical_file -or -not (Test-AlphaSamePhysicalFile -First $copy.primary -Second $copy.mirror)) { throw 'New mirror file identity differs.' }
    $assertions += 4
    Add-Content -LiteralPath $copy.primary -Value 'hardlink_probe'
    if (-not ((Get-Content -LiteralPath $copy.mirror -Raw).Contains('hardlink_probe'))) { throw 'Mirror does not share hardlink content.' }
    $assertions++

    $runDir = Join-Path $root 'runs\FixtureEA\RUN-001'
    $logs = Join-Path $runDir 'logs'
    $analysisLogs = Join-Path $runDir 'analysis\logs'
    New-Item -ItemType Directory -Path $logs,$analysisLogs -Force | Out-Null
    $primary = Join-Path $logs 'fixture.csv'
    $mirror = Join-Path $analysisLogs 'fixture.csv'
    Set-Content -LiteralPath $primary -Value @('a','b','c') -Encoding UTF8
    Copy-Item -LiteralPath $primary -Destination $mirror
    $dry = Convert-AlphaDuplicateLogMirror -Primary $primary -Mirror $mirror
    if ($dry.mode -ne 'dry_run' -or $dry.converted -or $dry.reclaimable_bytes -le 0) { throw 'Dry-run conversion contract failed.' }
    $assertions += 3
    $executed = Convert-AlphaDuplicateLogMirror -Primary $primary -Mirror $mirror -Execute
    if (-not $executed.converted) { throw 'Execute conversion did not report success.' }
    if (-not (Test-AlphaSamePhysicalFile -First $primary -Second $mirror)) { throw 'Converted mirror file identity differs.' }
    Add-Content -LiteralPath $primary -Value 'converted_probe'
    if (-not ((Get-Content -LiteralPath $mirror -Raw).Contains('converted_probe'))) { throw 'Converted mirror is not a hardlink.' }
    $assertions += 3

    $idempotentPlan = Join-Path $root 'dedupe_plan_idempotent.json'
    & $dedupe -RunsRoot (Join-Path $root 'runs') -EaName 'FixtureEA' -RunId 'RUN-001' -PlanPath $idempotentPlan | Out-Null
    $idempotentPayload = Get-Content -LiteralPath $idempotentPlan -Raw | ConvertFrom-Json
    if ($idempotentPayload.candidate_count -ne 0 -or $idempotentPayload.reclaimable_bytes -ne 0) { throw 'Hardlinked pair was offered for dedupe again.' }
    if ($idempotentPayload.already_hardlinked_skipped -ne 1) { throw 'Hardlinked pair skip count is invalid.' }
    $assertions += 3

    # Recreate a byte-identical physical duplicate for the CLI dry-run contract.
    Remove-Item -LiteralPath $mirror -Force
    Copy-Item -LiteralPath $primary -Destination $mirror
    $plan = Join-Path $root 'dedupe_plan.json'
    $output = & $dedupe -RunsRoot (Join-Path $root 'runs') -EaName 'FixtureEA' -RunId 'RUN-001' -PlanPath $plan
    if (-not (Test-Path -LiteralPath $plan)) { throw 'Dedupe CLI dry-run failed.' }
    $payload = Get-Content -LiteralPath $plan -Raw | ConvertFrom-Json
    if ($payload.mode -ne 'dry_run' -or $payload.candidate_count -ne 1 -or $payload.reclaimable_bytes -le 0) { throw 'Dedupe plan payload is invalid.' }
    if (-not (Test-AlphaFilesIdentical -First $primary -Second $mirror)) { throw 'Dedupe dry-run mutated fixture files.' }
    $assertions += 4
    Write-Output "LOG_STORAGE_TEST_PASS assertions=$assertions receipt=$output"
} finally {
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
}
