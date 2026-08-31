[CmdletBinding()]
param(
    [string]$RunsRoot = "",
    [string]$EaName = "",
    [string]$RunId = "",
    [ValidateRange(1, 500)][int]$ConsoleLimit = 50,
    [ValidateRange(0, 100000)][int]$MaxPairs = 0,
    [string]$PlanPath = "",
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
$repoRoot = Split-Path -Parent $alphaRoot
. (Join-Path $toolsRoot 'log_storage.ps1')

if ([string]::IsNullOrWhiteSpace($RunsRoot)) { $RunsRoot = Join-Path $alphaRoot 'runs' }
$runsResolved = (Resolve-Path -LiteralPath $RunsRoot).Path
$repoResolved = (Resolve-Path -LiteralPath $repoRoot).Path.TrimEnd('\') + '\'
if (-not ($runsResolved.TrimEnd('\') + '\').StartsWith($repoResolved,[StringComparison]::OrdinalIgnoreCase)) {
    throw "RunsRoot must stay under the workspace: $runsResolved"
}

$scanRoots = [System.Collections.Generic.List[string]]::new()
if (-not [string]::IsNullOrWhiteSpace($RunId)) {
    if ([string]::IsNullOrWhiteSpace($EaName)) { throw '-RunId requires -EaName.' }
    $exact = Join-Path (Join-Path $runsResolved $EaName) $RunId
    if (-not (Test-Path -LiteralPath $exact -PathType Container)) { throw "Run directory not found: $exact" }
    $scanRoots.Add($exact)
} elseif (-not [string]::IsNullOrWhiteSpace($EaName)) {
    $eaRoot = Join-Path $runsResolved $EaName
    if (-not (Test-Path -LiteralPath $eaRoot -PathType Container)) { throw "EA run root not found: $eaRoot" }
    Get-ChildItem -LiteralPath $eaRoot -Directory -Force | ForEach-Object { $scanRoots.Add($_.FullName) }
} else {
    Get-ChildItem -LiteralPath $runsResolved -Directory -Force | ForEach-Object {
        Get-ChildItem -LiteralPath $_.FullName -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { $scanRoots.Add($_.FullName) }
    }
}

$candidates = [System.Collections.Generic.List[object]]::new()
$alreadyHardlinkedSkipped = 0
foreach ($runDir in $scanRoots) {
    $primaryDir = Join-Path $runDir 'logs'
    $mirrorDir = Join-Path $runDir 'analysis\logs'
    if (-not (Test-Path -LiteralPath $primaryDir -PathType Container) -or
        -not (Test-Path -LiteralPath $mirrorDir -PathType Container)) { continue }
    foreach ($primary in Get-ChildItem -LiteralPath $primaryDir -File -Force) {
        $mirror = Join-Path $mirrorDir $primary.Name
        if (-not (Test-Path -LiteralPath $mirror -PathType Leaf)) { continue }
        if (Test-AlphaSamePhysicalFile -First $primary.FullName -Second $mirror) {
            $alreadyHardlinkedSkipped++
            continue
        }
        if (Test-AlphaFilesIdentical -First $primary.FullName -Second $mirror) {
            $candidates.Add((Convert-AlphaDuplicateLogMirror -Primary $primary.FullName -Mirror $mirror -Execute:$Execute))
            if ($MaxPairs -gt 0 -and $candidates.Count -ge $MaxPairs) { break }
        }
    }
    if ($MaxPairs -gt 0 -and $candidates.Count -ge $MaxPairs) { break }
}

$total = 0L
foreach ($candidate in $candidates) { $total += [long]$candidate.reclaimable_bytes }
if ([string]::IsNullOrWhiteSpace($PlanPath)) {
    $planDir = Join-Path $alphaRoot 'runtime\cleanup_plans'
    New-Item -ItemType Directory -Path $planDir -Force | Out-Null
    $PlanPath = Join-Path $planDir ("dedupe_log_mirrors_{0}.json" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
}
$planResolved = [IO.Path]::GetFullPath($PlanPath)
if (-not $planResolved.StartsWith($repoResolved,[StringComparison]::OrdinalIgnoreCase)) {
    throw "PlanPath must stay under the workspace: $planResolved"
}
$plan = [pscustomobject][ordered]@{
    schema_version = 'alpha-log-mirror-dedupe-plan-v1'
    created_at_utc = [datetime]::UtcNow.ToString('o')
    mode = $(if ($Execute) { 'execute' } else { 'dry_run' })
    runs_root = $runsResolved
    ea_name = $EaName
    run_id = $RunId
    candidate_count = $candidates.Count
    already_hardlinked_skipped = $alreadyHardlinkedSkipped
    reclaimable_bytes = $total
    candidates = @($candidates)
}
$parent = Split-Path -Parent $planResolved
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$plan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $planResolved -Encoding UTF8
$planHash = (Get-FileHash -LiteralPath $planResolved -Algorithm SHA256).Hash.ToLowerInvariant()

$candidates | Sort-Object reclaimable_bytes -Descending | Select-Object -First $ConsoleLimit |
    Format-Table mode, @{Name='MB';Expression={[math]::Round($_.reclaimable_bytes / 1MB,2)}}, primary, mirror -AutoSize |
    Out-Host
if ($candidates.Count -gt $ConsoleLimit) { Write-Host "... $($candidates.Count - $ConsoleLimit) more candidate(s) only in plan JSON." }
Write-Output "LOG_MIRROR_DEDUPE_PLAN mode=$($plan.mode) candidates=$($candidates.Count) already_hardlinked_skipped=$alreadyHardlinkedSkipped reclaimable_bytes=$total plan=$planResolved sha256=$planHash"
