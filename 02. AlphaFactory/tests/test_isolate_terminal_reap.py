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
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")

PS_EXE = r"$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"


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


@pytest.mark.skipif(not (ISOLATE / "terminal64.exe").is_file() or not POWERSHELL,
                    reason="requires the mqdemo isolate + powershell")
def test_reap_kills_only_processes_under_isolate_root():
    # A fake terminal64.exe INSIDE the isolate root must be reaped; a fake
    # terminal64.exe OUTSIDE the root (no /portable, GUI-style) must survive.
    # Stubs are real executables (powershell.exe copies) so Win32_Process
    # reports real exe paths — no name-only or missing-path trickery.
    body = r"""
$MT5 = '<ISOLATE_EXE>'
$insideDir = Join-Path (Split-Path -Parent $MT5) 'zreaptest'
$outsideDir = Join-Path $env:TEMP 'fakegui_zreaptest'
New-Item -ItemType Directory -Force -Path $insideDir, $outsideDir | Out-Null
$stub = '<PS_STUB>'
Copy-Item $stub (Join-Path $insideDir 'terminal64.exe') -Force
Copy-Item $stub (Join-Path $outsideDir 'terminal64.exe') -Force
$inProc = Start-Process (Join-Path $insideDir 'terminal64.exe') -ArgumentList '-NoProfile','-Command','Start-Sleep 300' -PassThru
$outProc = Start-Process (Join-Path $outsideDir 'terminal64.exe') -ArgumentList '-NoProfile','-Command','Start-Sleep 300' -PassThru
Start-Sleep -Seconds 2
try {
    Stop-IsolateAttachTerminals
    Start-Sleep -Seconds 1
    "INSIDE_ALIVE=" + (-not $inProc.HasExited)
    "OUTSIDE_ALIVE=" + (-not $outProc.HasExited)
} finally {
    if (-not $outProc.HasExited) { Stop-Process -Id $outProc.Id -Force -ErrorAction SilentlyContinue }
    if (-not $inProc.HasExited) { Stop-Process -Id $inProc.Id -Force -ErrorAction SilentlyContinue }
    Remove-Item -Recurse -Force $insideDir, $outsideDir -ErrorAction SilentlyContinue
}
"""
    body = body.replace("<ISOLATE_EXE>", str(ISOLATE / "terminal64.exe"))
    body = body.replace("<PS_STUB>", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    res = _run_powershell(_alpha_harness(body))
    out = res.stdout + res.stderr
    assert "INSIDE_ALIVE=False" in out, out   # isolate process reaped
    assert "OUTSIDE_ALIVE=True" in out, out   # foreign process untouched
