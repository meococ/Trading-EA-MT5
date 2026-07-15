param(
    [switch]$BuildRunsDb,
    [switch]$ShowSize
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

function Remove-SampleExperts {
    $removed = 0
    foreach ($pattern in @("Expert*.mq5", "Expert*.ex5")) {
        Get-ChildItem -LiteralPath $repoRoot -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            $removed++
        }
    }
    Write-Status "Removed $removed root MT5 sample expert file(s)" "OK"
}

function Remove-StaleWorktrees {
    $candidateRoots = @(
        (Join-Path $repoRoot "agent_worktrees"),
        (Join-Path $repoRoot ".agent\\worktrees")
    )
    $removed = 0
    foreach ($worktrees in $candidateRoots) {
        if (Test-Path $worktrees) {
            Remove-Item -LiteralPath $worktrees -Recurse -Force -ErrorAction SilentlyContinue
            $removed++
        }
    }
    if ($removed -gt 0) {
        Write-Status "Removed $removed stale agent worktree folder(s)" "OK"
    } else {
        Write-Status "No stale agent worktree directory found" "INFO"
    }
}

function Show-WorkspaceSizes {
    $targets = @(
        (Join-Path $alphaRoot "runs"),
        (Join-Path $alphaRoot "runtime"),
        (Join-Path $repoRoot "00. Old File"),
        (Join-Path $repoRoot "03. EA Developer")
    )

    foreach ($path in $targets) {
        if (-not (Test-Path $path)) { continue }
        $size = (Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $sizeGb = [math]::Round(($size / 1GB), 2)
        Write-Host ("{0}  {1} GB" -f $path, $sizeGb)
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

Remove-SampleExperts
Remove-StaleWorktrees

if ($ShowSize) {
    Show-WorkspaceSizes
}

if ($BuildRunsDb) {
    Build-RunDatabase
}
