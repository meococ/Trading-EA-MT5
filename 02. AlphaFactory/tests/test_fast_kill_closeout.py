from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
VALIDATOR = ALPHA_ROOT / "tools" / "validate_fast_kill_closeout.py"
SCHEMA = ALPHA_ROOT / "schemas" / "fast_kill_closeout.v1.schema.json"
TEMPLATE = ALPHA_ROOT / "templates" / "research" / "FAST_KILL_CLOSEOUT.template.json"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _binding(workspace: Path, role: str, path: Path) -> dict[str, object]:
    return {
        "role": role,
        "path": path.relative_to(workspace).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
    }


def _packet(workspace: Path, *, evidence_class: str = "offline_probe") -> Path:
    artifacts = {
        "preregistration": _write(workspace / "research" / "prereg.md", "# frozen\n"),
        "result_summary": _write(workspace / "research" / "summary.json", '{"pf":0.5}\n'),
        "readout": _write(workspace / "research" / "readout.md", "# killed\n"),
    }
    if evidence_class == "model0":
        artifacts.update(
            {
                "source": _write(workspace / "EA_Demo.mq5", "void OnTick(){}\n"),
                "compile_log": _write(workspace / "run" / "compile.log", "0 errors\n"),
                "nonrepaint_audit": _write(workspace / "run" / "nonrepaint.json", '{"status":"PASS"}\n'),
                "run_manifest": _write(workspace / "run" / "run_manifest.json", '{"run_id":"r1"}\n'),
                "tester_report": _write(workspace / "run" / "report.html", "<html>report</html>\n"),
                "summary_metrics": _write(workspace / "run" / "metrics.json", '{"pf":0.5}\n'),
                "log_triage": _write(workspace / "run" / "log_triage.json", '{"clean":true}\n'),
            }
        )
    payload = {
        "schema_version": "alphafactory_fast_kill_closeout.v1",
        "created_at_utc": "2026-07-26T06:00:00Z",
        "hypothesis_id": "HYP-DEMO-001",
        "ea_name": "EA_Demo",
        "evidence_class": evidence_class,
        "verdict": "KILLED",
        "kill_code": "gross_edge_fail",
        "cell_closeout_claim": True,
        "bindings": [_binding(workspace, role, path) for role, path in artifacts.items()],
        "frozen_kill_gate": {
            "name": "gross_profit_factor",
            "comparator": "lt",
            "threshold": 0.70,
            "actual": 0.50,
            "frozen_pre_outcome": True,
            "minimum_observations": 50,
            "observations_unit": "completed_trades",
            "sequential_early_stop": True,
            "sequential_boundary_frozen_pre_outcome": True,
            "sequential_method": "bayesian_predictive_futility",
            "sequential_parameters": {"minimum_predictive_pass_probability": 0.05},
            "maximum_looks": 4,
            "looks_evaluated": 1,
        },
        "metrics": {
            "trades": 50,
            "gross_profit_factor": 0.50,
            "cost_profit_factor_x1": 0.42,
            "expectancy_r": -0.20,
            "max_drawdown_pct": 4.0,
            "trades_per_elapsed_week": 2.5,
        },
        "anti_overfit_contract": {
            "plan_frozen_pre_outcome": True,
            "terminal_state_recorded": True,
            "posthoc_rule_change_authorized": False,
            "same_id_rerun_authorized": False,
        },
        "limitations": ["Synthetic test fixture."],
    }
    packet = workspace / "fast_kill.json"
    packet.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return packet


def _run(packet: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--packet", str(packet), "--workspace", str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_offline_probe_fast_kill_passes_without_chart_or_grok(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    result = _run(packet, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAST_KILL_CLOSEOUT_OK" in result.stdout
    payload = json.loads(packet.read_text(encoding="utf-8"))
    roles = {row["role"] for row in payload["bindings"]}
    assert roles == {"preregistration", "result_summary", "readout"}
    assert not any("casebook" in role or "grok" in role for role in roles)


def test_model0_fast_kill_requires_run_integrity_but_not_casebook(tmp_path: Path) -> None:
    packet = _packet(tmp_path, evidence_class="model0")
    result = _run(packet, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["bindings"] = [row for row in payload["bindings"] if row["role"] != "log_triage"]
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "missing required binding roles: log_triage" in result.stderr


def test_fast_kill_rejects_untriggered_or_posthoc_gate(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["frozen_kill_gate"]["actual"] = 0.90
    payload["anti_overfit_contract"]["posthoc_rule_change_authorized"] = True
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "frozen kill gate is not triggered" in result.stderr
    assert "posthoc_rule_change_authorized must be false" in result.stderr


def test_fast_kill_rejects_underpowered_or_unfrozen_early_stop(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["frozen_kill_gate"]["minimum_observations"] = 100
    payload["frozen_kill_gate"]["sequential_boundary_frozen_pre_outcome"] = False
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "has not reached its frozen minimum_observations" in result.stderr
    assert "sequential early-stop boundary must be frozen pre-outcome" in result.stderr


def test_fast_kill_schema_template_and_alpha_surface_are_registered() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    alpha = (ALPHA_ROOT / "alpha.ps1").read_text(encoding="utf-8-sig")
    assert schema["$id"] == "alphafactory.fast_kill_closeout.v1"
    assert template["schema_version"] == "alphafactory_fast_kill_closeout.v1"
    assert '"fast-kill"' in alpha
    assert "validate_fast_kill_closeout.py" in alpha
