<#
.SYNOPSIS
    Fail if any live Python file attaches to MetaTrader 5 without pinning the
    factory isolate.

.DESCRIPTION
    `mt5.initialize()` with no arguments attaches to whichever terminal is
    already running. On the Owner machine that is the GUI terminal being traded
    from -- the same terminal the MT5 MCP server on 127.0.0.1:22346 drives.
    Research must never land there: it competes with live charts, reads the
    Owner's history instead of the pinned isolate, and produces numbers no
    other machine can reproduce.

    The contract: every attach passes `path=` (normally via
    tools/factory_paths.mt5_initialize_kwargs()).

    Detection runs through a small embedded Python `ast` scan (Python 3.12 is
    installed on this machine). A `mt5*.initialize(...)` call site is flagged
    when it has no `path=` argument, no positional path, and no `**` unpack --
    or when it uses `**init_args`/`**kwargs` in a file that never derives args
    from `mt5_initialize_kwargs`. If `python` is unavailable the script falls
    back to a broadened regex scan with the same rule.

.PARAMETER CriticalPathOnly
    Only check the modules alpha.ps1 / session_trader actually invoke plus the
    swept attach set. Other research probes are reported as warnings instead of
    failures.

.EXAMPLE
    & ".\02. AlphaFactory\tools\check_mt5_attach_contract.ps1" -CriticalPathOnly
#>
[CmdletBinding()]
param(
    [switch]$CriticalPathOnly
)

$ErrorActionPreference = 'Stop'

$alphaRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $alphaRoot

# Every file that opens an MT5 attach. A bare attach in one of these is a hard
# failure; the set covers the 2026-09 attach-contract sweep.
$criticalPath = @(
    'analysis/mt5_connector.py',
    'analysis/trade_chart_capture.py',
    'analysis/baseline_control.py',
    'analysis/debug_smc_logic.py',
    'analysis/phoenix_range_audit.py',
    'analysis/phase3a_ny_open_regime_discovery.py',
    'analysis/phase3b_router_simulation.py',
    'analysis/run_smc_grid.py',
    'analysis/run_smc_test.py',
    'analysis/smc_multi_asset_test.py',
    'analysis/test_smc_quick.py',
    'analysis/test_smc_v2.py',
    'analysis/verify_breakout.py',
    'session_trader/collector.py',
    'tools/execution_data_foundation.py',
    'tools/execution_data_qfsi_nolive_capture.py',
    'tools/import_owner_deal_history_qfsi.py',
    'tools/export_mt5_tick_spread_evidence.py',
    'tools/probe_mt5_storage.py',
    'tools/his_offline_gatecount_eurusd_m15.py',
    'tools/drat_onnx_ict_probe.py',
    'tools/impact_pressure_probe.py',
    'tools/wave3_offline_closedbar_probe.py',
    'tools/v8_vix_riskoff_usdjpy_offline_probe.py',
    'tools/v8_usuk_10y_diff_gbpusd_offline_probe.py',
    'tools/v8_usjp_10y_diff_usdjpy_offline_probe.py',
    'tools/v8_useu_10y_diff_eurusd_offline_probe.py',
    'tools/v8_usbill_slope_usd_basket_offline_probe.py',
    'tools/v8_ois_sofr_estr_diff_eurusd_offline_probe.py',
    'tools/v8_eu_curve_slope_eurusd_offline_probe.py',
    'tools/v8_equity_bond_diff_offline_probe.py',
    'tools/v8_cot_tff_spec_net_offline_probe.py',
    'tools/v8_cot_tff_offline_probe.py',
    'tools/v8_cot_tff_levmoney_h4_offline_probe.py',
    'tools/v8_carry_vol_regime_offline_probe.py',
    'tools/v8_carry_vol_offline_probe.py',
    'tools/v8_carry_differential_offline_probe.py',
    'tools/useu_yield_policy_shock_h4_probe.py',
    'tools/cot_tff_am_net_change_h4_probe.py',
    'tools/carry_rate_change_event_h4_probe.py',
    'tools/carry_level_h4_strip_probe.py',
    'tools/edge_variant_scanner.py',
    'tools/edge_scanner.py',
    'tools/edge_extended_scanner.py',
    'tools/grand_edge_scan.py',
    'tools/mec15_forex_scan.py',
    'tools/mec15_deep_iteration.py',
    'tools/mec15_multi_instrument.py',
    'tools/gap_fill_deep.py',
    'tools/gap_fill_optimize.py',
    'tools/research/setup_fivepercent_market_data.py'
)

# AST scan: flag every mt5*.initialize() call that carries no usable path.
# `**` unpacks are acceptable only when the file derives args from
# tools.factory_paths.mt5_initialize_kwargs.
$pyCheck = @'
import ast
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
findings = []
scanned = 0
for path in sorted(root.rglob("*.py")):
    lowered = [part.lower() for part in path.parts]
    if "runtime" in lowered or "00. old file" in lowered:
        continue
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        continue
    if "import MetaTrader5" not in text:
        continue
    scanned += 1
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue
    pinned = "mt5_initialize_kwargs" in text
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "initialize"):
            continue
        base = func.value
        if not (
            isinstance(base, ast.Name)
            and (base.id == "mt5" or base.id.startswith("mt5_"))
        ):
            continue
        has_path = bool(node.args)  # positional path argument
        star_unpack = False
        for kw in node.keywords:
            if kw.arg == "path":
                if not (
                    isinstance(kw.value, ast.Constant)
                    and kw.value.value in (None, "")
                ):
                    has_path = True
            elif kw.arg is None:
                star_unpack = True
        if has_path or (star_unpack and pinned):
            continue
        findings.append({"file": str(path), "line": node.lineno})
print(json.dumps({"scanned": scanned, "findings": findings}))
'@

$offenders = @()
$scanned = 0
$engine = "regex-fallback"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    try {
        # Pipe the scan via stdin (`python -`): Windows PowerShell 5.1 mangles
        # embedded double quotes in `-c` arguments, which broke the AST scan and
        # silently dropped us to the regex fallback.
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $out = $pyCheck | & python - $alphaRoot 2>$null
        $ErrorActionPreference = $prevEap
        if ($LASTEXITCODE -eq 0 -and $out) {
            $scan = $out | ConvertFrom-Json
            $scanned = [int]$scan.scanned
            foreach ($f in $scan.findings) {
                $offenders += [pscustomobject]@{ Path = [string]$f.file; Line = [int]$f.line }
            }
            $engine = "python-ast"
        }
    } catch {
        $ErrorActionPreference = $prevEap
        $scan = $null
    }
}

if ($engine -eq "regex-fallback") {
    # Same rule without an AST: flag mt5*.initialize( calls whose argument
    # fragment (up to the first ')') has neither `path=` nor `**`; a `**`
    # unpack still needs the file to derive args from mt5_initialize_kwargs.
    Get-ChildItem -LiteralPath $alphaRoot -Recurse -Filter '*.py' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike '*\runtime\*' -and $_.FullName -notlike '*\00. Old File\*' } |
        ForEach-Object {
            $text = [System.IO.File]::ReadAllText($_.FullName)
            # Only files that actually attach can violate the contract. This also
            # skips factory_paths.py itself, whose docstring shows the pattern.
            if ($text -notmatch 'import\s+MetaTrader5') { return }
            $scanned++
            $pinned = $text -match 'mt5_initialize_kwargs'
            # Blank out string/docstring contents so mentions like the literal
            # "mt5.initialize()" in --help text or docstrings are not flagged.
            $stripped = [regex]::Replace(
                $text,
                '"""[\s\S]*?"""|''''''[\s\S]*?''''''|"(?:[^"\\\n]|\\.)*"|''(?:[^''\\\n]|\\.)*''',
                { param($m) ' ' * $m.Length })
            foreach ($m in [regex]::Matches($stripped, '(?<!\w)mt5\w*\.initialize\s*\((?<args>[^)]*)\)')) {
                $lineStart = $text.LastIndexOf("`n", $m.Index) + 1
                $lineText = $text.Substring($lineStart, $m.Index - $lineStart)
                if ($lineText -match '^\s*#') { continue }   # comments are not attaches
                $argsText = $m.Groups['args'].Value
                $hasPath = ($argsText -match 'path\s*=') -and ($argsText -notmatch 'path\s*=\s*(None|["'']{2})')
                if ($hasPath) { continue }
                if ($argsText -match '\*\*' -and $pinned) { continue }
                $offenders += [pscustomobject]@{
                    Path = $_.FullName
                    Line = ([regex]::Matches($text.Substring(0, $m.Index), "`n")).Count + 1
                }
            }
        }
}

$classified = @(
    $offenders | ForEach-Object {
        $rel = $_.Path.Substring($repoRoot.Length + 1).Replace('\', '/')
        [pscustomobject]@{
            Path     = $rel
            Line     = $_.Line
            Critical = ($criticalPath -contains ($rel -replace '^02\. AlphaFactory/', ''))
        }
    }
)

$critical = @($classified | Where-Object { $_.Critical })
$offPath = @($classified | Where-Object { -not $_.Critical })

"MT5 attach contract ($engine) - scanned $scanned Python files under '02. AlphaFactory'"
"  unpinned mt5.initialize() on the alpha.ps1 critical path : $($critical.Count)"
"  unpinned mt5.initialize() in off-path research probes     : $($offPath.Count)"

if ($critical.Count -gt 0) {
    ""
    "CRITICAL - these run as part of alpha.ps1 / the swept attach set and would attach to the Owner GUI:"
    $critical | ForEach-Object { "  {0}:{1}" -f $_.Path, $_.Line }
}

if ($offPath.Count -gt 0) {
    ""
    "WARNING - off-path probes still using an unpinned attach:"
    $offPath | Select-Object -First 50 | ForEach-Object { "  {0}:{1}" -f $_.Path, $_.Line }
    if ($offPath.Count -gt 50) { "  ... and $($offPath.Count - 50) more" }
    ""
    "Fix pattern:"
    "  from tools.factory_paths import mt5_initialize_kwargs"
    "  mt5.initialize(**mt5_initialize_kwargs())"
    "or require an explicit --terminal arg and call mt5.initialize(path=...)."
}

if ($critical.Count -gt 0) { exit 1 }
if (-not $CriticalPathOnly -and $offPath.Count -gt 0) { exit 1 }

""
"PASS"
exit 0
