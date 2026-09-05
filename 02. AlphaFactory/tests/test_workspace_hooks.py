from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ALPHA_ROOT = Path(__file__).resolve().parents[1]
REPO = ALPHA_ROOT.parent
HOOK_BIN = REPO / ".grok" / "hooks" / "bin"
PRETOOL = HOOK_BIN / "pretool.ps1"
POSTTOOL = HOOK_BIN / "posttool.ps1"
SESSION_START = HOOK_BIN / "session-start.ps1"
HYGIENE = HOOK_BIN / "hygiene.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def run_ps(script: Path, payload: dict | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    merged = os.environ.copy()
    if env:
        merged.update(env)
    stdin = json.dumps(payload) if payload is not None else ""
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        input=stdin,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=merged,
    )


def run_ps_command(command: str) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def parse_json_line(stdout: str) -> dict:
    text = stdout.strip()
    assert text, "expected JSON on stdout, got empty"
    # PowerShell may emit a UTF-8 BOM.
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return json.loads(text)


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_mcp_trade() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "mt5__trade_send_market_order",
            "toolInput": {"symbol": "EURUSD", "type": "buy", "volume": 0.1},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"
    assert "Risk Gateway" in payload["reason"]


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_allows_account_info_with_no_stdout() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "mt5__get_trading_account_info",
            "toolInput": {},
        },
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_trade_via_use_tool_dispatcher() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "use_tool",
            "toolInput": {"tool_name": "mt5__trade_close_single_position", "tool_input": {}},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_asks_mcp_tester_backtest() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "mt5__tester_run_backtest",
            "toolInput": {"symbol": "EURUSD"},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 0
    assert payload["decision"] == "ask"
    assert "alpha.ps1 backtest" in payload["reason"]


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_bare_terminal() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {"command": r"D:\Meta 5\terminal64.exe"},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"
    assert "2026-08-31" in payload["reason"]


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_allows_alpha_ps1_backtest() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {
                "command": r".\02. AlphaFactory\alpha.ps1 backtest EA_LiquiditySweep"
            },
        },
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_git_add_all() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {"command": "git add -A"},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_asks_git_commit() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {"command": 'git commit -m "wip"'},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 0
    assert payload["decision"] == "ask"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_worktree_add() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {"command": "git worktree add ../wt feature"},
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_spawn_worktree_isolation() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "spawn_subagent",
            "toolInput": {
                "prompt": "explore the EA",
                "description": "explore",
                "subagent_type": "explore",
                "isolation": "worktree",
            },
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"
    assert "OWNER_APPROVED_WORKTREE" in payload["reason"]


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_rewrites_subagent_prompt() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "spawn_subagent",
            "toolInput": {
                "prompt": "read GOAL.md",
                "description": "read goal",
                "subagent_type": "explore",
            },
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 0
    updated = payload["hookSpecificOutput"]["updatedInput"]
    assert "read GOAL.md" in updated["prompt"]
    assert "[workspace-hook]" in updated["prompt"]
    assert "mt5__trade_" in updated["prompt"]
    assert updated["subagent_type"] == "explore"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_write_alpha_local() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "write",
            "toolInput": {
                "file_path": str(ALPHA_ROOT / "alpha.local.ps1"),
                "content": "ignored",
            },
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_denies_owner_path_initialize() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {
                "command": r'python -c "import MetaTrader5 as mt5; mt5.initialize(path=r\'D:\Meta 5\terminal64.exe\')"'
            },
        },
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 2
    assert payload["decision"] == "deny"


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_pretool_allows_session_trader_probe() -> None:
    result = run_ps(
        PRETOOL,
        {
            "hookEventName": "pre_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {
                "command": r'python -m session_trader probe --symbol EURUSD --terminal "D:\Meta 5\terminal64.exe"'
            },
        },
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_hygiene_flags_secret_and_forbidden_name() -> None:
    command = (
        f". '{HYGIENE}'; "
        "$n = Test-ForbiddenRelativePath '02. AlphaFactory/alpha.local.ps1'; "
        "$s = Test-SecretContent ('pass' + 'word=demo'); "
        "$ok = Test-SecretContent 'ordinary text'; "
        "Write-Output ([pscustomobject]@{name=[bool]$n; secret=[bool]$s; clean=[bool]$ok} | ConvertTo-Json -Compress)"
    )
    result = run_ps_command(command)
    assert result.returncode == 0, result.stderr
    payload = parse_json_line(result.stdout)
    assert payload["name"] is True
    assert payload["secret"] is True
    assert payload["clean"] is False


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_posttool_compile_without_evidence_adds_context() -> None:
    result = run_ps(
        POSTTOOL,
        {
            "hookEventName": "post_tool_use",
            "toolName": "run_terminal_command",
            "toolInput": {"command": r".\02. AlphaFactory\alpha.ps1 compile EA_X"},
            "toolResult": "exit code 0\ncompiled maybe",
        },
        env={"HOOK_AUDIT_PATH": str(REPO / ".grok" / "hooks" / "logs" / "test-audit.jsonl")},
    )
    payload = parse_json_line(result.stdout)
    assert result.returncode == 0
    assert "0 errors, 0 warnings" in payload["hookSpecificOutput"]["additionalContext"]


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell not on PATH")
def test_session_start_skip_live_writes_status(tmp_path: Path) -> None:
    status = tmp_path / "mcp_session_status.json"
    result = run_ps(
        SESSION_START,
        {},
        env={"HOOK_SKIP_LIVE": "1", "HOOK_STATUS_PATH": str(status)},
    )
    assert result.returncode == 0, result.stderr
    assert status.is_file()
    payload = json.loads(status.read_text(encoding="utf-8-sig"))
    assert payload["ok"] is False
    assert payload["authority"] is False
    assert payload["plane"] == "observation"
