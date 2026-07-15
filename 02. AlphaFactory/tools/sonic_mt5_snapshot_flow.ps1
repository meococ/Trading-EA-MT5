param(
    [Parameter(Mandatory = $true)]
    [string]$RunDir,
    [string]$SampleReason = "top_loss,top_win",
    [int]$MaxCases = 6,
    [switch]$SkipPrepare,
    [switch]$SkipCompile,
    [switch]$SkipCollect,
    [switch]$CleanupStaging,
    [switch]$SkipIndex,
    [int]$CompileTimeoutSec = 45,
    [switch]$RunMt5Startup,
    [int]$Mt5TimeoutSec = 180,
    [string]$TerminalPath = "C:\Program Files\MetaTrader 5\terminal64.exe"
)

$ErrorActionPreference = "Stop"

function Get-UtcNowIso {
    return (Get-Date).ToUniversalTime().ToString("o")
}

function Read-JsonLoose([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }
    try {
        return ($Text | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Invoke-JsonCommand([string]$Exe, [string[]]$ArgumentList) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $raw = & $Exe @ArgumentList 2>&1
        $exit = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    $text = ($raw | ForEach-Object { $_.ToString() }) -join "`n"
    $tail = @($text -split "`n" | Select-Object -Last 30)
    $parsed = Read-JsonLoose $text
    return [ordered]@{
        exit_code = $exit
        ok = ($exit -eq 0)
        output_tail = $tail
        json = $parsed
    }
}

function Get-CompileStatus([string]$LogPath) {
    $status = [ordered]@{
        log = $LogPath
        exists = (Test-Path -LiteralPath $LogPath)
        ok = $false
        errors = $null
        warnings = $null
        tail = @()
    }
    if (-not $status.exists) {
        return $status
    }
    $lines = @((Get-Content -LiteralPath $LogPath -Tail 40) | ForEach-Object { $_.ToString() })
    $status.tail = $lines
    foreach ($line in $lines) {
        $match = [regex]::Match($line, "Result:\s+(?<errors>\d+)\s+errors,\s+(?<warnings>\d+)\s+warnings")
        if ($match.Success) {
            $status.errors = [int]$match.Groups["errors"].Value
            $status.warnings = [int]$match.Groups["warnings"].Value
            $status.ok = ($status.errors -eq 0 -and $status.warnings -eq 0)
        }
    }
    return $status
}

function Invoke-Mt5StartupScript([string]$TerminalPath, [string]$ConfigPath, [int]$TimeoutSec) {
    $status = [ordered]@{
        terminal = $TerminalPath
        config = $ConfigPath
        ok = $false
        timed_out = $false
        exit_code = $null
        error = ""
    }
    if (-not (Test-Path -LiteralPath $TerminalPath)) {
        $status.error = "MT5 terminal not found: $TerminalPath"
        return $status
    }
    $existing = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
    if ($existing.Count -gt 0) {
        $status.error = "MT5 terminal is already running; close it or run collection after the script finishes."
        $status.existing_process_ids = @($existing | ForEach-Object { $_.Id })
        return $status
    }

    $proc = Start-Process -FilePath $TerminalPath -ArgumentList "/config:`"$ConfigPath`"" -PassThru
    if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
        $status.timed_out = $true
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        return $status
    }
    $status.exit_code = $proc.ExitCode
    $status.ok = $true
    return $status
}

function Clear-SnapshotStaging([string]$Mql5Root) {
    $filesRoot = Join-Path $Mql5Root "Files"
    $requestDir = Join-Path $filesRoot "SonicR_CaseSnapshot"
    $result = [ordered]@{
        files_root = $filesRoot
        request_dir = $requestDir
        removed_shots_csv = $false
        removed_pngs = 0
    }
    if (-not (Test-Path -LiteralPath $filesRoot)) {
        return $result
    }

    $resolvedFiles = (Resolve-Path -LiteralPath $filesRoot).Path
    $resolvedMql5 = (Resolve-Path -LiteralPath $Mql5Root).Path
    if (-not $resolvedFiles.StartsWith($resolvedMql5, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean snapshot staging outside MQL5 root: $resolvedFiles"
    }

    $shotsCsv = Join-Path $requestDir "shots.csv"
    if (Test-Path -LiteralPath $shotsCsv) {
        Remove-Item -LiteralPath $shotsCsv -Force
        $result.removed_shots_csv = $true
    }

    $pngs = @(Get-ChildItem -LiteralPath $filesRoot -Filter "SonicR_CaseSnapshot_*.png" -File -ErrorAction SilentlyContinue)
    foreach ($png in $pngs) {
        Remove-Item -LiteralPath $png.FullName -Force
        $result.removed_pngs += 1
    }
    return $result
}

function Clear-RunSnapshotArtifacts([string]$NativeDir) {
    $result = [ordered]@{
        native_dir = $NativeDir
        removed_sha256 = $false
        removed_screenshots = 0
    }
    if (-not (Test-Path -LiteralPath $NativeDir)) {
        return $result
    }

    $resolvedNative = (Resolve-Path -LiteralPath $NativeDir).Path
    $shaCsv = Join-Path $resolvedNative "sha256.csv"
    if (Test-Path -LiteralPath $shaCsv) {
        Remove-Item -LiteralPath $shaCsv -Force
        $result.removed_sha256 = $true
    }

    $screenshotsDir = Join-Path $resolvedNative "screenshots"
    if (Test-Path -LiteralPath $screenshotsDir) {
        $pngs = @(Get-ChildItem -LiteralPath $screenshotsDir -Filter "*.png" -File -ErrorAction SilentlyContinue)
        foreach ($png in $pngs) {
            Remove-Item -LiteralPath $png.FullName -Force
            $result.removed_screenshots += 1
        }
    }
    return $result
}

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$alphaRoot = Split-Path -Parent $toolsRoot
$advisorsRoot = Split-Path -Parent $alphaRoot
$mql5Root = Split-Path -Parent (Split-Path -Parent $advisorsRoot)
$runPath = (Resolve-Path -LiteralPath $RunDir).Path
$analysisDir = Join-Path $runPath "analysis"
$nativeDir = Join-Path $analysisDir "native_mt5_casebook"
$scriptSource = Join-Path $advisorsRoot "03. EA Developer\EA_SonicR\research\mt5_snapshot\SonicR_CaseSnapshot.mq5"
$scriptDest = Join-Path $mql5Root "Scripts\SonicR_CaseSnapshot.mq5"
$scriptBinary = Join-Path $mql5Root "Scripts\SonicR_CaseSnapshot.ex5"
$metaEditor = "C:\Program Files\MetaTrader 5\metaeditor64.exe"
$started = Get-UtcNowIso

if (-not (Test-Path -LiteralPath $scriptSource)) {
    throw "MT5 snapshot script source not found: $scriptSource"
}
if (-not (Test-Path -LiteralPath $analysisDir)) {
    New-Item -ItemType Directory -Force -Path $analysisDir | Out-Null
}
if (-not (Test-Path -LiteralPath $nativeDir)) {
    New-Item -ItemType Directory -Force -Path $nativeDir | Out-Null
}

$steps = [ordered]@{}

if (-not $SkipPrepare) {
    $steps.staging_clear = Clear-SnapshotStaging $mql5Root
    $steps.run_artifact_clear = Clear-RunSnapshotArtifacts $nativeDir
    $prepareArgs = @(
        (Join-Path $toolsRoot "sonic_prepare_mt5_snapshot_cases.py"),
        "--run-dir", $runPath,
        "--sample-reason", $SampleReason,
        "--max-cases", [string]$MaxCases
    )
    $steps.prepare = Invoke-JsonCommand "python" $prepareArgs
}

if (-not $SkipCompile) {
    $scriptDir = Split-Path -Parent $scriptDest
    if (-not (Test-Path -LiteralPath $scriptDir)) {
        New-Item -ItemType Directory -Force -Path $scriptDir | Out-Null
    }
    Copy-Item -LiteralPath $scriptSource -Destination $scriptDest -Force

    $compileLog = Join-Path $nativeDir "SonicR_CaseSnapshot_compile.log"
    Remove-Item -LiteralPath $compileLog -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $metaEditor) {
        $proc = Start-Process -FilePath $metaEditor -ArgumentList "/compile:`"$scriptDest`" /log:`"$compileLog`"" -PassThru -WindowStyle Hidden
        if (-not $proc.WaitForExit($CompileTimeoutSec * 1000)) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            $steps.compile = [ordered]@{
                log = $compileLog
                exists = (Test-Path -LiteralPath $compileLog)
                ok = $false
                timed_out = $true
                timeout_sec = $CompileTimeoutSec
                tail = if (Test-Path -LiteralPath $compileLog) { @((Get-Content -LiteralPath $compileLog -Tail 40) | ForEach-Object { $_.ToString() }) } else { @() }
            }
        } else {
            $steps.compile = Get-CompileStatus $compileLog
            $steps.compile["exit_code"] = $proc.ExitCode
        }
    } else {
        $steps.compile = [ordered]@{
            log = $compileLog
            exists = $false
            ok = $false
            error = "MetaEditor not found: $metaEditor"
        }
    }
}

if ($RunMt5Startup) {
    $startupConfig = Join-Path $nativeDir "SonicR_CaseSnapshot_startup.ini"
    $startupText = @(
        "[Charts]",
        "MaxBars=1000000",
        "",
        "[Experts]",
        "Enabled=1",
        "",
        "[StartUp]",
        "Script=SonicR_CaseSnapshot",
        "Symbol=XAUUSD",
        "Period=M5",
        "ShutdownTerminal=1",
        ""
    ) -join "`r`n"
    $startupText | Set-Content -LiteralPath $startupConfig -Encoding ASCII
    $steps.mt5_startup = Invoke-Mt5StartupScript $TerminalPath $startupConfig $Mt5TimeoutSec
}

if (-not $SkipCollect) {
    $collectArgs = @(
        (Join-Path $toolsRoot "sonic_collect_mt5_snapshots.py"),
        "--run-dir", $runPath
    )
    if ($CleanupStaging) {
        $collectArgs += "--cleanup-staging"
    }
    $steps.collect = Invoke-JsonCommand "python" $collectArgs
}

if (-not $SkipIndex) {
    $indexArgs = @(
        (Join-Path $toolsRoot "sonic_casebook_index.py"),
        "--run-dir", $runPath
    )
    $steps.index = Invoke-JsonCommand "python" $indexArgs
}

$manifestPath = Join-Path $nativeDir "manifest.json"
$manifest = $null
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $manifest = $null
    }
}

$captureStatus = if ($manifest) { [string]$manifest.capture_status } else { "NO_MANIFEST" }
$compileOk = $true
if ($steps.Contains("compile")) {
    $compileOk = [bool]$steps.compile.ok
}
$status = "ok"
if (-not $compileOk) {
    $status = "compile_failed"
} elseif ($steps.Contains("mt5_startup") -and -not [bool]$steps.mt5_startup.ok) {
    $status = "mt5_startup_failed"
} elseif ($steps.Contains("collect") -and -not [bool]$steps.collect.ok) {
    $status = "collect_failed"
} elseif ($captureStatus -eq "PENDING_MT5_SCRIPT_RUN") {
    $status = "pending_mt5_script_run"
} elseif ($captureStatus -eq "COLLECTED") {
    $status = "collected"
}

$result = [ordered]@{
    schema_version = "sonic_mt5_snapshot_flow.v1"
    generated_at_utc = Get-UtcNowIso
    started_at_utc = $started
    status = $status
    run_dir = $runPath
    sample_reason = $SampleReason
    max_cases = $MaxCases
    native_manifest = $manifestPath
    capture_status = $captureStatus
    mt5_script = [ordered]@{
        source = $scriptSource
        installed = $scriptDest
        binary = $scriptBinary
        binary_exists = (Test-Path -LiteralPath $scriptBinary)
    }
    next_manual_step = if ($status -eq "pending_mt5_script_run") {
        "Run MT5 Navigator -> Scripts -> SonicR_CaseSnapshot, then rerun this wrapper with -SkipPrepare -SkipCompile to collect PNGs."
    } else {
        ""
    }
    steps = $steps
}

$json = $result | ConvertTo-Json -Depth 10
$outPath = Join-Path $nativeDir "snapshot_flow_status.json"
Write-Utf8NoBom $outPath $json
$json
