import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools" / "terminal_process_guard.ps1"
ALPHA = ROOT / "alpha.ps1"


def run_ps(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=ROOT.parent,
        text=True,
        capture_output=True,
        check=False,
    )


def test_allows_terminal_from_different_installation_and_blocks_managed_one():
    helper = str(HELPER).replace("'", "''")
    script = rf"""
. '{helper}'
$managed = [pscustomobject]@{{ Id = 101; Path = 'D:\Alpha\terminal64.exe' }}
$user = [pscustomobject]@{{ Id = 202; Path = 'C:\Program Files\MetaTrader 5\terminal64.exe' }}
$out = @(Get-ConflictingAlphaTerminalProcesses `
    -ExpectedExecutablePath 'D:\Alpha\terminal64.exe' `
    -Processes @($managed, $user))
@($out | ForEach-Object {{ [int]$_.Process.Id }}) | ConvertTo-Json -Compress
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip()) == 101


def test_unresolved_identity_fails_closed():
    helper = str(HELPER).replace("'", "''")
    script = rf"""
. '{helper}'
$unknown = [pscustomobject]@{{ Id = 2147483647; Path = $null }}
$out = @(Get-ConflictingAlphaTerminalProcesses `
    -ExpectedExecutablePath 'D:\Alpha\terminal64.exe' `
    -Processes @($unknown))
@{{ count = $out.Count; path = [string]$out[0].ExecutablePath }} | ConvertTo-Json -Compress
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload == {"count": 1, "path": ""}


def test_live_guard_identifies_configured_portable_terminal_without_claiming_user_terminal():
    helper = str(HELPER).replace("'", "''")
    alpha_root = str(ROOT).replace("'", "''")
    script = rf"""
. '{helper}'
$expected = Resolve-AlphaMt5ExecutablePath -AlphaRoot '{alpha_root}'
$all = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
$conflicts = @(Get-ConflictingAlphaTerminalProcesses -ExpectedExecutablePath $expected -Processes $all)
@{{
  expected = $expected
  all = @($all | ForEach-Object {{ @{{ id = $_.Id; path = Get-TerminalExecutablePath $_ }} }})
  conflicts = @($conflicts | ForEach-Object {{ [int]$_.Process.Id }})
}} | ConvertTo-Json -Depth 5 -Compress
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload["expected"].lower().endswith(
        r"02. alphafactory\runtime\mt5-portable-fivepercent\terminal64.exe"
    )
    for proc in payload["all"]:
        path = (proc.get("path") or "").lower()
        if path and path != payload["expected"].lower():
            assert proc["id"] not in payload["conflicts"]


def test_completed_report_cleanup_releases_reused_pid_without_stopping_it():
    source = ALPHA.read_text(encoding="utf-8-sig")
    function_start = source.index("function Stop-RunnerOwnedTerminal")
    function_end = source.index("function Stop-AllRunnerOwnedTerminals", function_start)
    function_body = source[function_start:function_end]

    assert "[switch]$AllowExitedOrReused" in function_body
    assert "if ($AllowExitedOrReused)" in function_body
    release_branch = function_body.split("if ($AllowExitedOrReused)", 1)[1]
    assert "replacement process was not stopped" in release_branch
    assert "OwnedTerminalIdentities.Remove($ProcessId)" in release_branch
    assert "Stop-Process" not in release_branch.split("return", 1)[0]

    assert "Stop-RunnerOwnedTerminal $mt5Pid -AllowExitedOrReused" in source
    assert "Stop-RunnerOwnedTerminal $mt5Pid\n        throw \"Backtest failed: timeout" in source
    assert "Stop-RunnerOwnedTerminal $mt5Relaunch.Id -AllowExitedOrReused:$reportFound" in source
