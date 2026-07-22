#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot frozen operator for MZMS HYP-008/009/010 via ea_research_loop.ps1.

.DESCRIPTION
  Fail-closed campaign runner. Accepts only HYP-MZMS-XAU-M5-008|009|010.
  Always dry-runs once and requires execution_allowed=true. With -Execute,
  invokes the identical ea_research_loop command exactly once and never
  self-retries. Does not modify EA source, packets, registry, prereg, or harness.

  Lesson from HYP-007: a completed or partial AlphaFactory run_manifest that
  already binds the hypothesis ID consumes the single economic outcome; retrying
  the same ID is forbidden.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010"
    )]
    [string]$HypothesisId,

    [Parameter(Mandatory = $true)]
    [string]$ReceiptPath,

    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$script:startedAtUtc = (Get-Date).ToUniversalTime().ToString("o")

function Get-WorkspaceRoot {
    # research/run_frozen_hyp_once.ps1 -> research -> EA package -> EA Developer -> workspace
    $here = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($here)) {
        $here = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    return (Resolve-Path (Join-Path $here "..\..\..")).Path
}

function Write-OperatorReceipt {
    param(
        [hashtable]$Payload,
        [string]$Path
    )
    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $Payload["finished_at_utc"] = (Get-Date).ToUniversalTime().ToString("o")
    $json = ($Payload | ConvertTo-Json -Depth 8)
    Set-Content -LiteralPath $Path -Value $json -Encoding UTF8
}

function Find-BoundHypothesisRunDirs {
    param(
        [string]$RunsRoot,
        [string]$HypothesisId
    )
    $hits = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path -LiteralPath $RunsRoot -PathType Container)) {
        return @()
    }
    $manifests = Get-ChildItem -LiteralPath $RunsRoot -Filter "run_manifest.json" -Recurse -File -ErrorAction SilentlyContinue
    foreach ($manifest in $manifests) {
        try {
            $obj = Get-Content -LiteralPath $manifest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            continue
        }
        $boundId = [string]$obj.hypothesis_id
        if ($boundId -ceq $HypothesisId) {
            [void]$hits.Add($manifest.Directory.FullName)
        }
    }
    return @($hits | Sort-Object -Unique)
}

function Test-ExecutionAllowedFromDryRunText {
    param([string]$Text)
    # PowerShell ConvertTo-Json may emit 0+ spaces after the colon.
    if ($Text -match '"execution_allowed"\s*:\s*true') { return $true }
    if ($Text -match '"execution_allowed"\s*:\s*false') { return $false }
    return $null
}

function Invoke-ResearchLoopOnce {
    param(
        [string]$LoopScript,
        [string[]]$ArgumentList,
        [switch]$WithExecute
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $argParts = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $LoopScript)
    )
    foreach ($a in $ArgumentList) {
        if ($null -eq $a) { continue }
        if ($a -match '\s') {
            $argParts += ('"{0}"' -f ($a -replace '"', '\"'))
        } else {
            $argParts += $a
        }
    }
    if ($WithExecute) {
        $argParts += "-Execute"
    }
    $psi.Arguments = [string]::Join(" ", $argParts)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    return [pscustomobject]@{
        ExitCode = $proc.ExitCode
        StdOut   = $stdout
        StdErr   = $stderr
        Combined = ($stdout + "`n" + $stderr)
    }
}

$workspaceRoot = Get-WorkspaceRoot
$alphaRoot = Join-Path $workspaceRoot "02. AlphaFactory"
$runtimeRoot = Join-Path $alphaRoot "runtime"
$runsRoot = Join-Path $alphaRoot "runs"
$loopScript = Join-Path $alphaRoot "tools\ea_research_loop.ps1"
$researchLoopLock = Join-Path $runtimeRoot "ea_research_loop.lock"

$packetRel = ("03. EA Developer/EA_MZMS_Scalper/research/preflight/{0}/task_packet.control.json" -f $HypothesisId)
$packetAbs = Join-Path $workspaceRoot ($packetRel -replace "/", "\")

$receipt = [ordered]@{
    schema_version          = "mzms_frozen_hyp_once_receipt.v1"
    hypothesis_id           = $HypothesisId
    started_at_utc          = $script:startedAtUtc
    finished_at_utc         = $null
    task_packet_path        = $packetRel
    cost_source_manifest_path = $null
    dry_run_status          = "not_started"
    execution_allowed       = $null
    execute_requested       = [bool]$Execute
    execute_attempted       = $false
    execute_exit_code       = $null
    error                   = $null
    discovered_run_dirs     = @()
    # Intentionally omit economic outcomes (PF/N/DD/R).
}

try {
    if (-not (Test-Path -LiteralPath $loopScript -PathType Leaf)) {
        throw "ea_research_loop.ps1 missing: $loopScript"
    }
    if (-not (Test-Path -LiteralPath $packetAbs -PathType Leaf)) {
        throw "Task packet missing: $packetRel"
    }

    # Fail closed: active research-loop lock (owning process not inspected).
    if (Test-Path -LiteralPath $researchLoopLock -PathType Leaf) {
        throw "Active research-loop lock exists: $researchLoopLock"
    }

    # Fail closed: any terminal64 process (research loop treats these as unrelated).
    $terminals = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
    if ($terminals.Count -gt 0) {
        $pids = ($terminals | ForEach-Object { $_.Id }) -join ","
        throw "Unrelated terminal64 process exists (PID(s): $pids)"
    }

    # Fail closed: any completed or partial run_manifest already binding this ID.
    $existing = Find-BoundHypothesisRunDirs -RunsRoot $runsRoot -HypothesisId $HypothesisId
    $receipt.discovered_run_dirs = @($existing)
    if ($existing.Count -gt 0) {
        throw ("Hypothesis already has AlphaFactory run_manifest binding(s); second economic outcome forbidden: {0}" -f ($existing -join "; "))
    }

    $packet = Get-Content -LiteralPath $packetAbs -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$packet.hypothesis_id -cne $HypothesisId) {
        throw "Packet hypothesis_id mismatch: packet='$($packet.hypothesis_id)' expected='$HypothesisId'"
    }
    if ([string]::IsNullOrWhiteSpace([string]$packet.overrides)) {
        throw "Packet overrides are empty for $HypothesisId"
    }
    if ([string]::IsNullOrWhiteSpace([string]$packet.cost_source_manifest_path)) {
        throw "Packet cost_source_manifest_path is empty for $HypothesisId"
    }

    $costRel = ([string]$packet.cost_source_manifest_path).Replace("\", "/")
    $receipt.cost_source_manifest_path = $costRel
    $overrides = [string]$packet.overrides
    $spread = [string]$packet.spread

    # Fixed campaign surface (packet must agree on symbol/window/model where present).
    $loopArgs = @(
        "-EaName", "EA_MZMS_Scalper",
        "-HypothesisId", $HypothesisId,
        "-RunRole", "control",
        "-Symbol", "XAUUSD",
        "-Period", "M5",
        "-From", "2018.01.01",
        "-To", "2026.07.22",
        "-Model", "0",
        "-ExecutionMode", "0",
        "-FixedDelayMs", "0",
        "-Overrides", $overrides,
        "-TelemetryTier", "trade-only",
        "-Deposit", "100000",
        "-Leverage", "100",
        "-ValidationStage", "challenger",
        "-HoldingContract", "scalp",
        "-TaskPacket", $packetRel,
        "-CostSourceManifest", $costRel,
        "-AllowResearchCostProxy"
    )
    # packet spread=current => omit -Spread (do not pass empty/current token).
    if ($spread -and ($spread -cne "current")) {
        throw "Unexpected packet spread '$spread'; campaign requires omit -Spread for spread=current"
    }

    # --- Always one dry-run first ---
    $dry = Invoke-ResearchLoopOnce -LoopScript $loopScript -ArgumentList $loopArgs
    $allowed = Test-ExecutionAllowedFromDryRunText -Text $dry.Combined
    if ($null -eq $allowed) {
        $receipt.dry_run_status = "parse_error"
        $receipt.execution_allowed = $false
        throw "Dry-run did not emit parseable execution_allowed (exit=$($dry.ExitCode))"
    }
    $receipt.execution_allowed = [bool]$allowed
    if (-not $allowed) {
        $receipt.dry_run_status = "blocked"
        throw "Dry-run execution_allowed=false; refusing -Execute and stopping"
    }
    if ($dry.ExitCode -ne 0) {
        $receipt.dry_run_status = "failed"
        throw "Dry-run exit code $($dry.ExitCode) despite execution_allowed=true"
    }
    $receipt.dry_run_status = "allowed"

    if (-not $Execute) {
        Write-OperatorReceipt -Payload $receipt -Path $ReceiptPath
        Write-Host ("[OK] Dry-run allowed for {0}; stop without -Execute. Receipt: {1}" -f $HypothesisId, $ReceiptPath)
        exit 0
    }

    # Re-check guards immediately before the single economic invocation.
    if (Test-Path -LiteralPath $researchLoopLock -PathType Leaf) {
        throw "Active research-loop lock appeared before execute: $researchLoopLock"
    }
    $terminals2 = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
    if ($terminals2.Count -gt 0) {
        $pids2 = ($terminals2 | ForEach-Object { $_.Id }) -join ","
        throw "Unrelated terminal64 process appeared before execute (PID(s): $pids2)"
    }
    $existing2 = Find-BoundHypothesisRunDirs -RunsRoot $runsRoot -HypothesisId $HypothesisId
    if ($existing2.Count -gt 0) {
        $receipt.discovered_run_dirs = @($existing2)
        throw ("Hypothesis gained run_manifest binding(s) before execute; aborting: {0}" -f ($existing2 -join "; "))
    }

    # --- Exactly one synchronous -Execute; never self-retry regardless of exit code ---
    $receipt.execute_attempted = $true
    $exec = Invoke-ResearchLoopOnce -LoopScript $loopScript -ArgumentList $loopArgs -WithExecute
    $receipt.execute_exit_code = [int]$exec.ExitCode
    $receipt.discovered_run_dirs = @(Find-BoundHypothesisRunDirs -RunsRoot $runsRoot -HypothesisId $HypothesisId)

    Write-OperatorReceipt -Payload $receipt -Path $ReceiptPath
    if ($exec.ExitCode -ne 0) {
        Write-Host ("[ERR] Single execute finished with exit {0}. No retry. Receipt: {1}" -f $exec.ExitCode, $ReceiptPath) -ForegroundColor Red
        exit $exec.ExitCode
    }
    Write-Host ("[OK] Single execute finished exit 0 for {0}. Receipt: {1}" -f $HypothesisId, $ReceiptPath)
    exit 0
}
catch {
    $receipt.error = [string]$_.Exception.Message
    if ($receipt.dry_run_status -eq "not_started") {
        $receipt.dry_run_status = "error"
    }
    try {
        $receipt.discovered_run_dirs = @(Find-BoundHypothesisRunDirs -RunsRoot $runsRoot -HypothesisId $HypothesisId)
    } catch {}
    Write-OperatorReceipt -Payload $receipt -Path $ReceiptPath
    Write-Host ("[ERR] {0}" -f $receipt.error) -ForegroundColor Red
    exit 1
}
