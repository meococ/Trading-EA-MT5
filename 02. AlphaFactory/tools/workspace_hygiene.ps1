param(
    [switch]$BuildRunsDb,
    [switch]$ShowSize,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
$repoRoot = Split-Path -Parent $alphaRoot

function Write-Status($Message, $Type = "INFO") {
    $color = switch ($Type) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERR" { "Red" }
        default { "Cyan" }
    }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Assert-PathUnderRoot($Path, $Root, $Label) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    $prefix = $fullRoot + [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label escapes the workspace root: $fullPath"
    }
    return $fullPath
}

function Get-SampleExperts {
    return @(foreach ($pattern in @("Expert*.mq5", "Expert*.ex5")) {
        Get-ChildItem -LiteralPath $repoRoot -Filter $pattern -File -Force -ErrorAction SilentlyContinue
    })
}

function Get-StaleWorktrees {
    $candidateRoots = @(
        (Join-Path $repoRoot "agent_worktrees"),
        (Join-Path $repoRoot ".agent\worktrees")
    )
    return @($candidateRoots | Where-Object { Test-Path -LiteralPath $_ -PathType Container })
}

function Show-WorkspaceSizes {
    $targets = @(
        (Join-Path $alphaRoot "runs"),
        (Join-Path $repoRoot "00. Old File"),
        (Join-Path $repoRoot "03. EA Developer")
    )

    foreach ($path in $targets) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $size = (Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $sizeGb = [math]::Round(($size / 1GB), 2)
        Write-Host ("{0}  {1} GB" -f $path, $sizeGb)
    }

    $runtime = Join-Path $alphaRoot "runtime"
    if (Test-Path -LiteralPath $runtime) {
        Write-Host ("{0}  (not recursed; use Explorer or Owner reclaim for portable/Tester)" -f $runtime)
    }
}

function Build-RunDatabase {
    $script = Join-Path $toolsRoot "runs_db.py"
    Write-Status "Rebuilding local runs database..." "INFO"
    python $script build
    if ($LASTEXITCODE -ne 0) {
        throw "runs_db.py build failed"
    }
    Write-Status "Runs database refreshed" "OK"
}

$sampleExperts = @(Get-SampleExperts)
$staleWorktrees = @(Get-StaleWorktrees)
$mode = if ($Execute) { "EXECUTE" } else { "DRY-RUN" }
Write-Status "Mode: $mode" $(if ($Execute) { "WARN" } else { "INFO" })
Write-Status "Root sample candidates: $($sampleExperts.Count)" "INFO"
Write-Status "Stale worktree candidates: $($staleWorktrees.Count)" "INFO"

$candidateRows = @(
    $sampleExperts | ForEach-Object { [pscustomobject]@{ Kind = 'RootSample'; FullName = $_.FullName } }
    $staleWorktrees | ForEach-Object { [pscustomobject]@{ Kind = 'StaleWorktree'; FullName = $_ } }
)
if ($candidateRows.Count -gt 0) {
    $candidateRows | Format-Table -AutoSize | Out-Host
}

if ($Execute) {
    foreach ($sample in $sampleExperts) {
        $safePath = Assert-PathUnderRoot $sample.FullName $repoRoot "Root sample"
        Remove-Item -LiteralPath $safePath -Force -ErrorAction Stop
    }
    foreach ($worktree in $staleWorktrees) {
        $safePath = Assert-PathUnderRoot $worktree $repoRoot "Stale worktree"
        Remove-Item -LiteralPath $safePath -Recurse -Force -ErrorAction Stop
    }
    Write-Status "Removed $($sampleExperts.Count) root sample file(s) and $($staleWorktrees.Count) stale worktree folder(s)" "OK"
} else {
    Write-Status "Dry-run only. Re-run with -Execute after reviewing the exact candidates." "OK"
}

if ($ShowSize) {
    Show-WorkspaceSizes
}

if ($BuildRunsDb) {
    if (-not $Execute) {
        throw "BuildRunsDb mutates the local SQLite catalog and requires -Execute."
    }
    Build-RunDatabase
}
