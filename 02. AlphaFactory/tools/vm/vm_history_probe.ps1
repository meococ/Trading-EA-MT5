<#
.SYNOPSIS
    Probe true history depth of the VM isolate's MetaQuotes-Demo feed by
    running the Strategy Tester on a fixed one-week June window per year.
.DESCRIPTION
    The copy_rates_* attach API only sees the terminal's downloaded cache
    (fresh terminal ~= 3 months). The tester syncs what the window needs,
    so "history synchronized from X to Y" + the "no real ticks" warning
    reveal the server-side floor. Uses stock Advisors\ExpertMACD.ex5 —
    no repo EA staging needed. One week of ticks per probe year only.
    Kills only terminal64/metatester64 whose exe is inside the isolate.
    Exit code: 0 = PASS (probe ran), 1 = WARN (some windows had no data),
    2 = FAIL (harness error).
#>
[CmdletBinding()]
param(
    [string[]]$Symbols = @('EURUSD', 'XAUUSD'),
    [int[]]$Years = @(2026, 2025, 2024, 2020, 2015, 2010, 2005, 2000),
    [string]$ExpertRel = 'Advisors\ExpertMACD.ex5',
    [int]$Model = 4,
    [string]$Period = 'H1',
    [string]$OutDir = '',
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Off
. (Join-Path $PSScriptRoot 'vm_common.ps1')

$layout = Get-VmRepoLayout -VmToolsRoot $PSScriptRoot
$isolate = $layout.IsolateRoot
if (-not $isolate) {
    if ($Json) { (@{ error = 'isolate not found' } | ConvertTo-Json -Depth 4) }
    exit 2
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $layout.AlphaRoot 'runtime\vm_inventory'
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Stop-IsolateTerminal {
    param([string]$Root)
    # Never murder an in-flight governed run: a live alpha.ps1 backtest owns
    # its isolate processes and holds runtime\alpha_backtest.lock.
    if (Test-VmBacktestLockActive -AlphaRoot $layout.AlphaRoot) { return }
    foreach ($p in @(Get-VmMt5Processes -IsolateRoot $Root)) {
        if ($p.in_isolate) {
            Stop-Process -Id $p.pid -Force -ErrorAction SilentlyContinue
        }
    }
}

function Get-LogDelta {
    param([string]$Path, [long]$Offset)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return @() }
    $fs = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
    try {
        # MT5 terminal/tester logs are UTF-16LE; decode explicitly or every
        # byte is interleaved with NUL and patterns never match.
        $fs.Seek($Offset, [System.IO.SeekOrigin]::Begin) | Out-Null
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::Unicode)
        $text = $sr.ReadToEnd()
        $sr.Close()
        return @($text -split "`r?`n" | Where-Object { $_ -match '\S' })
    } finally { $fs.Close() }
}

if (Test-VmBacktestLockActive -AlphaRoot $layout.AlphaRoot) {
    if ($Json) { (@{ error = 'alpha_backtest.lock active - governed run in flight' } | ConvertTo-Json -Depth 4) }
    else { Write-Host 'probe refused: alpha_backtest.lock active - governed run in flight' }
    exit 2
}

$rows = New-Object System.Collections.Generic.List[object]
$dateTag = (Get-Date).ToString('yyyyMMdd')
$agentLog = Join-Path $isolate "Tester\Agent-127.0.0.1-3000\logs\$dateTag.log"
$mgrLog = Join-Path $isolate "Tester\logs\$dateTag.log"
$exe = Join-Path $isolate 'terminal64.exe'

foreach ($sym in $Symbols) {
    foreach ($year in $Years) {
        $row = [ordered]@{
            symbol = $sym; year = $year
            window_from = "$year.06.10"; window_to = "$year.06.14"
            tester_ran = $false; report_exists = $false
            history_sync_from = $null; history_sync_to = $null
            ticks_begin_from = $null; bars_in_test = $null; ticks_in_test = $null
            real_ticks = $false; no_real_ticks_flag = $false
            history_quality = $null; error = $null
        }

        $reportRel = "MQL5\Profiles\Tester\AlphaProbe\${sym}_$year\report.htm"
        $reportAbs = Join-Path $isolate ($reportRel -replace '/', '\')
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportAbs) | Out-Null
        if (Test-Path $reportAbs) { Remove-Item $reportAbs -Force }

        $iniPath = Join-Path $env:TEMP "vm_probe_${sym}_$year.ini"
        $ini = @"
[Tester]
Expert=$ExpertRel
Symbol=$sym
Period=$Period
Optimization=0
Model=$Model
ExecutionMode=0
Dates=2
FromDate=$($row.window_from -replace '\.', '.')
ToDate=$($row.window_to -replace '\.', '.')
Report=$reportRel
ReplaceReport=1
ShutdownTerminal=1
Deposit=10000
Currency=USD
Leverage=100
UseLocal=1
UseRemote=0
UseCloud=0
Port=3000
"@
        $ini | Set-Content -LiteralPath $iniPath -Encoding Unicode

        $offA = 0L; $offM = 0L
        if (Test-Path $agentLog) { $offA = (Get-Item $agentLog).Length }
        if (Test-Path $mgrLog) { $offM = (Get-Item $mgrLog).Length }

        Stop-IsolateTerminal -Root $isolate
        # Wait for a fully clean state — a dying terminal swallows the next /config launch.
        $cleanDeadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 800
            $busy = @((Get-VmMt5Processes -IsolateRoot $isolate) | Where-Object { $_.in_isolate }).Count -gt 0
        } while ($busy -and (Get-Date) -lt $cleanDeadline)

        try {
            $p = Start-Process -FilePath $exe -WorkingDirectory $isolate -ArgumentList '/portable', "/config:$iniPath" -PassThru
            # /config launch may hand off and exit; wait on report file or no isolate procs
            # fresh symbols need a full history sync before the tester stage starts —
            # allow generous headroom; resume from tester store on retry
            $deadline = (Get-Date).AddSeconds(900)
            while ((Get-Date) -lt $deadline) {
                Start-Sleep -Seconds 5
                if (Test-Path $reportAbs) {
                    # give ShutdownTerminal a moment to exit cleanly
                    Start-Sleep -Seconds 3
                    break
                }
                $stillRunning = @((Get-VmMt5Processes -IsolateRoot $isolate) | Where-Object { $_.in_isolate }).Count -gt 0
                if (-not $stillRunning -and $p.HasExited) { break }
            }
            $delta = @(Get-LogDelta -Path $agentLog -Offset $offA) + @(Get-LogDelta -Path $mgrLog -Offset $offM)
            if ($delta.Count -gt 0) { $row.tester_ran = $true }
            $row.report_exists = Test-Path $reportAbs

            foreach ($line in $delta) {
                if ($line -match "$sym.*history synchronized from (\d{4}\.\d{2}\.\d{2}) to (\d{4}\.\d{2}\.\d{2})") {
                    $row.history_sync_from = $Matches[1]; $row.history_sync_to = $Matches[2]
                }
                if ($line -match 'history ticks synchronized from (\d{4}\.\d{2}\.\d{2}) to (\d{4}\.\d{2}\.\d{2})') {
                    $row.ticks_begin_from = $Matches[1]
                }
                if ($line -match 'real ticks begin from (\d{4}\.\d{2}\.\d{2})') {
                    $row.ticks_begin_from = $Matches[1]
                }
                if ($line -match "$sym[^\n]*no real ticks") { $row.no_real_ticks_flag = $true }
                if ($line -match 'testing of .* started') { $row.tester_ran = $true }
            }
            if ($row.report_exists) {
                try {
                    $rep = Get-Content $reportAbs -Raw -Encoding Unicode
                    if ($rep -match 'History Quality[\s\S]*?<b>([\d.]+)%\s*real ticks</b>') {
                        $row.history_quality = [double]$Matches[1]
                    } elseif ($rep -match 'History Quality[\s\S]*?<b>([\d.]+)%[^<]*</b>') {
                        $row.history_quality = [double]$Matches[1]
                    }
                    # 'real ticks' suffix means the % is real-tick share; >0 = window covered
                    $row.real_ticks = ($null -ne $row.history_quality -and $row.history_quality -gt 0 -and $rep -match 'real ticks')
                    if ($rep -match 'Bars:[\s\S]*?<b>(\d+)</b>') { $row.bars_in_test = [int]$Matches[1] }
                    if ($rep -match 'Ticks:[\s\S]*?<b>(\d+)</b>') { $row.ticks_in_test = [int]$Matches[1] }
                } catch { }
            }
            if (-not $row.tester_ran -and -not $row.report_exists) { $row.error = 'tester did not run' }
            # data_absent: report produced but no bars, or tester ran with no sync
            if ($row.report_exists -and $null -ne $row.bars_in_test -and $row.bars_in_test -eq 0) {
                $row.error = 'no_data_in_window'
            }
        } catch {
            $row.error = $_.Exception.Message
        } finally {
            Stop-IsolateTerminal -Root $isolate
            Remove-Item $iniPath -Force -ErrorAction SilentlyContinue
        }
        $rows.Add([pscustomobject]$row)
        Write-Host ("probe {0} {1}: ran={2} sync={3}..{4} real_ticks={5} hq={6} err={7}" -f $sym, $year, $row.tester_ran, $row.history_sync_from, $row.history_sync_to, $row.real_ticks, $row.history_quality, $row.error)
    }
}

# merge with prior runs keyed on (symbol, year) so ladders accumulate across invocations
$jsonPath = Join-Path $OutDir 'history_probe.json'
$csvPath = Join-Path $OutDir 'history_probe.csv'
$merged = @{}
if (Test-Path $jsonPath) {
    try {
        $prev = Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($p in @($prev.probes)) { $merged["$($p.symbol)|$($p.year)"] = $p }
    } catch { }
}
foreach ($p in $rows) { $merged["$($p.symbol)|$($p.year)"] = $p }
$allProbes = @($merged.Values | Sort-Object symbol, { -[int]$_.year })

$payload = [ordered]@{
    schema_version = 'alphafactory_vm_history_probe.v2'
    method = 'Strategy Tester probe: 1-week June window per year, Model=4; history_sync_from = terminal-synced M1 floor line; hq = report "N% real ticks" (>0 means window covered); ticks_begin_from = tick-store sync floor as extended by successive probes'
    plane = 'devin-vm-mqdemo'
    checked_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    expert = $ExpertRel
    model = $Model
    probes = $allProbes
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$allProbes | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

if ($Json) { $payload | ConvertTo-Json -Depth 5 } else { Write-Host "probe done -> $jsonPath / $csvPath" }

$anyFail = @($rows | Where-Object { -not $_.tester_ran -or ($_.error -and $_.error -ne 'no_data_in_window') }).Count -gt 0
exit ($(if ($anyFail) { 1 } else { 0 }))
