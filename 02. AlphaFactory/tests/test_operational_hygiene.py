from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def run_powershell(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required for AlphaFactory contract tests"
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *args,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def copy_tool_into_temp_repo(tmp_path: Path, tool_name: str) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    tools = repo / "02. AlphaFactory" / "tools"
    tools.mkdir(parents=True)
    script = tools / tool_name
    shutil.copy2(ALPHA_ROOT / "tools" / tool_name, script)
    return repo, script


def write_reference(repo: Path, relative_path: str, run_id: str) -> None:
    path = repo / Path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"protected run {run_id}\n", encoding="utf-8")


def test_workspace_hygiene_is_dry_run_by_default_and_execute_is_explicit(tmp_path: Path) -> None:
    repo, script = copy_tool_into_temp_repo(tmp_path, "workspace_hygiene.ps1")
    sample = repo / "ExpertCanary.mq5"
    worktree_marker = repo / "agent_worktrees" / "sentinel.txt"
    sample.write_text("canary", encoding="utf-8")
    worktree_marker.parent.mkdir(parents=True)
    worktree_marker.write_text("canary", encoding="utf-8")

    dry_run = run_powershell(script, cwd=repo)
    assert dry_run.returncode == 0, dry_run.stderr
    assert "DRY-RUN" in dry_run.stdout
    assert sample.exists()
    assert worktree_marker.exists()

    execute = run_powershell(script, "-Execute", cwd=repo)
    assert execute.returncode == 0, execute.stderr
    assert not sample.exists()
    assert not worktree_marker.parent.exists()


def test_archive_default_reference_roots_cover_current_control_surfaces(tmp_path: Path) -> None:
    repo, script = copy_tool_into_temp_repo(tmp_path, "archive_backtest_artifacts.ps1")
    expected_ids = {
        "20260716_010101",
        "20260716_010102",
        "20260716_010103",
        "20260716_010104",
        "20260716_010105",
        "20260716_010106",
        "20260716_010107",
        "20260716_010108",
        "20260716_010109",
    }
    references = [
        ("04. Memory/hot.md", "20260716_010101"),
        ("05. Playbook/tool_runbook.md", "20260716_010102"),
        ("01. GOAL/GOAL.md", "20260716_010103"),
        ("03. EA Developer/EA_Current/research/readout.md", "20260716_010104"),
        ("INDEX.md", "20260716_010105"),
        ("AGENTS.md", "20260716_010106"),
        ("CLAUDE.md", "20260716_010107"),
        ("02. AlphaFactory/STRATEGY_LOG.md", "20260716_010108"),
        ("00. Old File/hot_details/hot_ledger_details.json", "20260716_010109"),
    ]
    for relative_path, run_id in references:
        write_reference(repo, relative_path, run_id)
    (repo / "02. AlphaFactory" / "runs").mkdir(parents=True)
    plan_path = repo / "02. AlphaFactory" / "runtime" / "test_plan.json"

    result = run_powershell(
        script,
        "-IncludeRuns",
        "-EaName",
        "EA_None",
        "-MinAgeDays",
        "0",
        "-PlanPath",
        str(plan_path),
        cwd=repo,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    assert expected_ids <= set(payload["referenced_run_ids"])


def test_archive_runs_requires_explicit_ea_name(tmp_path: Path) -> None:
    repo, script = copy_tool_into_temp_repo(tmp_path, "archive_backtest_artifacts.ps1")
    (repo / "02. AlphaFactory" / "runs").mkdir(parents=True)
    plan_path = repo / "02. AlphaFactory" / "runtime" / "test_plan.json"

    result = run_powershell(
        script,
        "-IncludeRuns",
        "-PlanPath",
        str(plan_path),
        cwd=repo,
    )
    assert result.returncode != 0
    assert "explicit -EaName" in (result.stdout + result.stderr)
    assert not plan_path.exists()


def test_archive_plan_path_must_stay_inside_workspace(tmp_path: Path) -> None:
    repo, script = copy_tool_into_temp_repo(tmp_path, "archive_backtest_artifacts.ps1")
    (repo / "02. AlphaFactory" / "runs").mkdir(parents=True)
    outside_plan = tmp_path / "outside-plan.json"

    result = run_powershell(
        script,
        "-IncludeRuns",
        "-EaName",
        "EA_None",
        "-PlanPath",
        str(outside_plan),
        cwd=repo,
    )
    assert result.returncode != 0
    assert "PlanPath" in (result.stdout + result.stderr)
    assert not outside_plan.exists()


def test_source_of_truth_failure_is_printable_under_cp1252() -> None:
    validator = WORKSPACE / "04. Memory" / "validate_source_of_truth.py"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252:strict"
    result = subprocess.run(
        [sys.executable, str(validator)],
        cwd=WORKSPACE,
        env=env,
        capture_output=True,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert b"SOURCE_OF_TRUTH_FAIL" in combined
    assert b"UnicodeEncodeError" not in combined


def test_registry_narrative_matches_live_active_pins() -> None:
    registry = json.loads(
        (WORKSPACE / "04. Memory" / "source_of_truth.json").read_text(encoding="utf-8-sig")
    )
    root_rule = registry["root_hygiene"]["rule"]
    assert "EA_FVGConfluence" in root_rule
    assert "EA_HybridICT_Sonic" in root_rule
    assert "Owner-opened active trading lane pin" not in root_rule

    ea_contract_reason = next(
        entry["reason"]
        for entry in registry["entries"]
        if entry["path"] == "02. AlphaFactory/tools/ea_contract.ps1"
    )
    assert "EA_FVGConfluence" in ea_contract_reason
    assert "EA_HybridICT_Sonic" in ea_contract_reason
    assert "SilverBullet" not in ea_contract_reason
    assert "OpenHalfMom" not in ea_contract_reason


def test_runbook_uses_live_alpha_entrypoints() -> None:
    runbook = (WORKSPACE / "05. Playbook" / "tool_runbook.md").read_text(encoding="utf-8")
    assert '-File "02. AlphaFactory/tools/alpha_json.ps1"' not in runbook
    assert "Run evidence audit" not in runbook
    assert '-File "02. AlphaFactory/alpha.ps1"' in runbook
