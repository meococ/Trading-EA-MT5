"""Isolate kill-scope safety for Stop-IsolateAttachTerminals (VMOPS-P1b).

The dispatch-finally reaper in alpha.ps1 runs on the Owner machine too, where
a real non-/portable MT5 GUI trades live. Kill law under test: only a process
whose fully-resolved exe path sits UNDER this run's isolate root may be
stopped — never by process name or a missing /portable flag, and a process
whose exe path cannot be resolved is logged, not killed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
ALPHA = ALPHA_ROOT / "alpha.ps1"
ISOLATE = ALPHA_ROOT / "runtime" / "mt5-portable-mqdemo"
BACKTEST_LOCK = ALPHA_ROOT / "runtime" / "alpha_backtest.lock"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def _alpha_harness(body: str) -> str:
    """Dot-source every function definition from alpha.ps1 (top-level script
    never runs) then evaluate `body`."""
    return (
        "$tokens=$null;$errs=$null;"
        f"$ast=[System.Management.Automation.Language.Parser]::ParseFile('{ALPHA}',[ref]$tokens,[ref]$errs);"
        "$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$true)"
        " | ForEach-Object { . ([ScriptBlock]::Create($_.Extent.Text)) };"
        + body
    )


def _run_powershell(command: str) -> subprocess.CompletedProcess:
    assert POWERSHELL, "PowerShell is required"
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )


def _backtest_lock_active() -> bool:
    """Exclusive-open probe on the global backtest lock, same semantics as
    post_run_cleanup.ps1 / Test-VmBacktestLockActive: the live run holds the
    file FileShare.None, so an open for writing fails while a run is active."""
    if not BACKTEST_LOCK.is_file():
        return False
    try:
        with open(BACKTEST_LOCK, "r+b"):
            pass
    except (PermissionError, OSError):
        return True
    return False


@pytest.mark.skipif(not (ISOLATE / "terminal64.exe").is_file() or not POWERSHELL,
                    reason="requires the mqdemo isolate + powershell")
def test_reap_kills_only_processes_under_isolate_root():
    # The sweep reaps EVERY process under the isolate root — running it while
    # a governed backtest is in-flight would kill that run's terminals.
    if _backtest_lock_active():
        pytest.skip("global backtest lock is active — a live run owns the isolate")
    # Fake terminal64/metatester64 stubs INSIDE the isolate must be reaped;
    # identical stubs OUTSIDE the root (no /portable, GUI-style) must survive.
    # Stubs are real executables (powershell.exe copies) so Win32_Process
    # reports real exe paths — containment, not the name, is what decides.
    body = r"""
$MT5 = '<ISOLATE_EXE>'
$insideDir = Join-Path (Split-Path -Parent $MT5) 'zreaptest'
$outsideDir = Join-Path $env:TEMP 'fakegui_zreaptest'
New-Item -ItemType Directory -Force -Path $insideDir, $outsideDir | Out-Null
$stub = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
Copy-Item $stub (Join-Path $insideDir 'terminal64.exe') -Force
Copy-Item $stub (Join-Path $insideDir 'metatester64.exe') -Force
Copy-Item $stub (Join-Path $outsideDir 'terminal64.exe') -Force
Copy-Item $stub (Join-Path $outsideDir 'metatester64.exe') -Force
$inProcs = @(
    Start-Process (Join-Path $insideDir 'terminal64.exe') -ArgumentList '-NoProfile','-Command','Start-Sleep 300' -PassThru
    Start-Process (Join-Path $insideDir 'metatester64.exe') -ArgumentList '-NoProfile','-Command','Start-Sleep 300' -PassThru
)
$outProcs = @(
    Start-Process (Join-Path $outsideDir 'terminal64.exe') -ArgumentList '-NoProfile','-Command','Start-Sleep 300' -PassThru
    Start-Process (Join-Path $outsideDir 'metatester64.exe') -ArgumentList '-NoProfile','-Command','Start-Sleep 300' -PassThru
)
Start-Sleep -Seconds 2
try {
    Stop-IsolateAttachTerminals
    Start-Sleep -Seconds 1
    "INSIDE_ALIVE=" + (($inProcs | Where-Object { -not $_.HasExited }).Count)
    "OUTSIDE_ALIVE=" + (($outProcs | Where-Object { -not $_.HasExited }).Count)
} finally {
    foreach ($p in @($outProcs + $inProcs)) {
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item -Recurse -Force $insideDir, $outsideDir -ErrorAction SilentlyContinue
}
"""
    body = body.replace("<ISOLATE_EXE>", str(ISOLATE / "terminal64.exe"))
    res = _run_powershell(_alpha_harness(body))
    out = res.stdout + res.stderr
    assert "INSIDE_ALIVE=0" in out, out    # both isolate stubs reaped
    assert "OUTSIDE_ALIVE=2" in out, out   # both foreign stubs untouched
