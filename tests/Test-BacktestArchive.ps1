[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = Split-Path -Parent $PSScriptRoot
$archiveTool = Join-Path $repo '02. AlphaFactory\tools\archive_backtest_artifacts.ps1'
$runsRoot = Join-Path $repo '02. AlphaFactory\runs'
$eaRoot = Join-Path $runsRoot 'FixtureCleanupEA'
$planRoot = Join-Path $repo '02. AlphaFactory\runtime\test_backtest_archive'
$archiveRoot = Join-Path 'C:\tmp' ("alpha_archive_test_{0}" -f [guid]::NewGuid().ToString('N'))
$sameVolumeRoot = Join-Path $repo '02. AlphaFactory\runtime\same_volume_archive_test'
$assertions = 0

foreach ($target in @($eaRoot,$planRoot,$sameVolumeRoot,$archiveRoot)) {
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
try {
    $oldRun = Join-Path $eaRoot 'RUN-OLD'
    $keepRun = Join-Path $eaRoot 'RUN-KEEP'
    $referencedRun = Join-Path $eaRoot '20260101_010101'
    New-Item -ItemType Directory -Path $oldRun,$keepRun,$referencedRun -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $oldRun 'report.html') -Value '<html>old</html>' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $oldRun 'run_manifest.json') -Value '{"run_id":"RUN-OLD"}' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $keepRun 'report.html') -Value '<html>keep</html>' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $referencedRun 'report.html') -Value '<html>referenced</html>' -Encoding UTF8
    (Get-Item -LiteralPath $oldRun).LastWriteTimeUtc = [datetime]::UtcNow.AddDays(-10)
    (Get-Item -LiteralPath $keepRun).LastWriteTimeUtc = [datetime]::UtcNow.AddDays(-10)
    (Get-Item -LiteralPath $referencedRun).LastWriteTimeUtc = [datetime]::UtcNow.AddDays(-10)

    New-Item -ItemType Directory -Path $planRoot -Force | Out-Null
    $referenceFile = Join-Path $planRoot 'reference.md'
    Set-Content -LiteralPath $referenceFile -Value 'Protected evidence run: 20260101_010101' -Encoding UTF8
    $dryPlan = Join-Path $planRoot 'dry_run.json'
    & $archiveTool -ArchiveRoot $archiveRoot -EaName 'FixtureCleanupEA' -KeepRunIds @('RUN-KEEP') `
        -ReferenceRoots @($referenceFile) -IncludeRuns -MinAgeDays 1 -PlanPath $dryPlan -ConsoleLimit 5
    $dry = Get-Content -LiteralPath $dryPlan -Raw | ConvertFrom-Json
    if ($dry.schema_version -ne 'alpha-backtest-cleanup-plan-v2' -or $dry.mode -ne 'dry_run') { throw 'Dry-run plan schema/mode failed.' }
    if ($dry.candidate_count -ne 1 -or $dry.items[0].Source -ne $oldRun) { throw 'Dry-run candidate set is incorrect.' }
    if (-not ($dry.referenced_run_ids -contains '20260101_010101')) { throw 'Referenced run id was not protected.' }
    if (-not (Test-Path -LiteralPath $oldRun) -or -not (Test-Path -LiteralPath $keepRun) -or -not (Test-Path -LiteralPath $referencedRun)) { throw 'Dry-run mutated fixture runs.' }
    $assertions += 6

    $samePlan = Join-Path $planRoot 'same_volume.json'
    $sameVolumeRejected = $false
    try {
        & $archiveTool -ArchiveRoot $sameVolumeRoot -EaName 'FixtureCleanupEA' -KeepRunIds @('RUN-KEEP') `
            -ReferenceRoots @($referenceFile) -IncludeRuns -MinAgeDays 1 -PlanPath $samePlan -ConsoleLimit 5 -Execute
    } catch {
        $sameVolumeRejected = $_.Exception.Message -match 'off-volume ArchiveRoot'
    }
    if (-not $sameVolumeRejected -or -not (Test-Path -LiteralPath $oldRun)) { throw 'Same-volume execute did not fail closed.' }
    $assertions += 2

    $executePlan = Join-Path $planRoot 'execute.json'
    & $archiveTool -ArchiveRoot $archiveRoot -EaName 'FixtureCleanupEA' -KeepRunIds @('RUN-KEEP') `
        -ReferenceRoots @($referenceFile) -IncludeRuns -MinAgeDays 1 -PlanPath $executePlan -ConsoleLimit 5 -Execute
    if (Test-Path -LiteralPath $oldRun) { throw 'Verified execute did not remove the archived source fixture.' }
    if (-not (Test-Path -LiteralPath $keepRun)) { throw 'Verified execute removed a keep-listed run.' }
    if (-not (Test-Path -LiteralPath $referencedRun)) { throw 'Verified execute removed a referenced run.' }
    $session = Get-ChildItem -LiteralPath $archiveRoot -Directory | Select-Object -First 1
    if (-not $session) { throw 'Archive session directory is missing.' }
    $manifestPath = Join-Path $session.FullName 'manifest.json'
    $archivedRun = Join-Path $session.FullName 'AlphaFactory_runs\FixtureCleanupEA\RUN-OLD'
    if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $archivedRun)) { throw 'Archive manifest or copied run is missing.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.total_items -ne 1 -or $manifest.items[0].FileInventory.Count -ne 2) { throw 'Archive hash inventory is incomplete.' }
    foreach ($entry in $manifest.items[0].FileInventory) {
        $path = Join-Path $archivedRun $entry.relative_path.Replace('/','\')
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Archived hash mismatch: $path" }
    }
    $assertions += 8
    Write-Output "BACKTEST_ARCHIVE_TEST_PASS assertions=$assertions manifest=$manifestPath"
} finally {
    foreach ($target in @($eaRoot,$planRoot,$sameVolumeRoot,$archiveRoot)) {
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    }
}
