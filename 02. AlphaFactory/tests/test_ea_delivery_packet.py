from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
VALIDATOR = ALPHA_ROOT / "tools" / "validate_ea_delivery_packet.py"
ALPHA = ALPHA_ROOT / "alpha.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
TEMPLATE = ALPHA_ROOT / "templates" / "research" / "EA_DELIVERY_PACKET.template.json"
LOGIC_TEMPLATE = ALPHA_ROOT / "templates" / "research" / "LOGIC_TO_CODE_MATRIX.template.md"
SCHEMA = ALPHA_ROOT / "schemas" / "ea_delivery_packet.v1.schema.json"
ANALYSIS_DIMENSIONS = {
    "economics", "cost_stress", "cadence", "time_stability",
    "session_breakdown", "direction_breakdown", "regime_breakdown",
    "execution_quality", "funnel", "winning_trade_causes",
    "losing_trade_causes", "logic_conflicts", "limitations",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write(path: Path, data: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")
    return path


def _binding(workspace: Path, role: str, path: Path) -> dict:
    return {
        "role": role,
        "path": path.relative_to(workspace).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha(path),
    }


def _casebook(
    workspace: Path,
    *,
    outcome: str = "trades",
    mode: str = "anatomy",
    root: Path | None = None,
) -> Path:
    root = (root or workspace) / ("decision_casebook" if mode == "asof" else "casebook")
    results = []
    labels = ["WIN", "WIN", "LOSS", "LOSS"] if outcome == "trades" else ["REJECTION", "REJECTION"]
    for i, label in enumerate(labels, 1):
        png = _write(root / f"case_{i}.png", b"PNG" + bytes([i]) * 128)
        results.append(
            {
                "case_id": f"case_{i}",
                "status": "RENDERED",
                "mode": mode,
                "label": label,
                "direction": 1 if i % 2 else -1,
                "png": png.name,
                "sha256": _sha(png),
                "entry_marker_rendered": True,
                "sl_line_rendered": outcome == "trades",
                "tp_line_rendered": outcome == "trades",
                "exit_marker_rendered": outcome == "trades" and mode == "anatomy",
                "cutoff_enforced": True,
                "outcome_hidden": mode == "asof",
                "net_r_hidden": mode == "asof",
                "label_hidden_in_image": mode == "asof",
                "context": {
                    "timeframe": "H1",
                    "entry_position": "center",
                    "future_region_hidden": mode == "asof",
                    "post_entry_outcome_region": mode == "anatomy",
                    "post_entry_bars_drawn": 0 if mode == "asof" else 4,
                    "decision_state_cutoff_enforced": True,
                },
            }
        )
    manifest = {
        "schema_version": "chart_case_render.v2",
        "mode": mode,
        "context_timeframe": "H1",
        "context_entry_position": "center",
        "context_post_bars": 4,
        "results": results,
    }
    path = root / "cases_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def _packet(
    workspace: Path, *, delivery_class: str = "economic_run", root: Path | None = None
) -> Path:
    root = root or workspace
    artifacts = {
        "preregistration": _write(root / "research" / "plan.md", "# frozen prereg\n"),
        "logic_matrix": _write(root / "research" / "logic_matrix.md", "# logic to code\n"),
        "source": _write(root / "EA_Demo.mq5", "#property strict\n"),
        "compiled_binary": _write(root / "EA_Demo.ex5", b"EX5-DEMO"),
        "compile_log": _write(root / "compile.log", "Result: 0 errors, 0 warnings\n"),
        "test_receipt": _write(root / "test_receipt.json", '{"passed":12,"failed":0}\n'),
        "nonrepaint_audit": _write(root / "nonrepaint.json", '{"status":"PASS"}\n'),
        "run_manifest": _write(root / "run" / "run_manifest.json", '{"run_id":"RUN-001","model":0}\n'),
        "tester_report": _write(root / "run" / "report.html", "<html>report</html>\n"),
        "lifecycle_trades": _write(root / "run" / "LifecycleTrades.csv", "event\nOPEN\nCLOSE\n"),
        "run_meta": _write(root / "run" / "RunMeta.json", '{"schema_version":"alphafactory_run_meta.v1"}\n'),
        "log_triage": _write(root / "run" / "log_triage.json", '{"schema_version":"log_triage.v1","clean":true,"battery":{}}\n'),
        "readout": _write(root / "research" / "readout.md", "# verdict and limitations\n"),
        "casebook_manifest": _casebook(
            workspace,
            outcome="trades" if delivery_class == "economic_run" else "zero",
            root=root,
        ),
        "decision_casebook_manifest": _casebook(
            workspace,
            outcome="trades" if delivery_class == "economic_run" else "zero",
            mode="asof",
            root=root,
        ),
    }
    analysis_role = "economic_analysis" if delivery_class == "economic_run" else "funnel_analysis"
    artifacts[analysis_role] = _write(
        root / "run" / f"{analysis_role}.json", '{"verdict":"KILLED"}\n'
    )

    statuses = {
        "economics": "COMPLETE",
        "cost_stress": "COMPLETE",
        "cadence": "COMPLETE",
        "time_stability": "COMPLETE",
        "session_breakdown": "COMPLETE",
        "direction_breakdown": "COMPLETE",
        "regime_breakdown": "COMPLETE",
        "execution_quality": "COMPLETE",
        "funnel": "COMPLETE",
        "winning_trade_causes": "COMPLETE",
        "losing_trade_causes": "COMPLETE",
        "logic_conflicts": "COMPLETE",
        "limitations": "COMPLETE",
    }
    trades = 4
    sample_basis = "wins_and_losses"
    if delivery_class == "zero_trade_terminal":
        trades = 0
        sample_basis = "rejections"
        for key in ("economics", "cost_stress", "winning_trade_causes", "losing_trade_causes"):
            statuses[key] = "NOT_APPLICABLE_ZERO_TRADES"

    packet = {
        "schema_version": "alphafactory_ea_delivery_packet.v1",
        "created_at_utc": "2026-07-19T16:00:00Z",
        "hypothesis_id": "HYP-DEMO-001",
        "ea_name": "EA_Demo",
        "delivery_class": delivery_class,
        "completion_claim": True,
        "verdict": "KILLED",
        "bindings": [_binding(workspace, role, path) for role, path in artifacts.items()],
        "logic_contract": {
            "requirements_total": 8,
            "requirements_mapped_to_code": 8,
            "requirements_tested": 8,
            "closed_bar_decisions": True,
            "unresolved_material_ambiguities": 0,
        },
        "engineering_contract": {
            "tests_passed": 12,
            "tests_failed": 0,
            "compile_errors": 0,
            "compile_warnings": 0,
            "nonrepaint_status": "PASS",
        },
        "run_contract": {
            "run_id": "RUN-001",
            "model": 0,
            "trades": trades,
            "report_lifecycle_reconciled": True,
            "lifecycle_open_rows": trades,
            "lifecycle_final_rows": trades,
            "unresolved_log_errors": 0,
        },
        "analysis_contract": {
            "statuses": statuses,
            "exceptions": {
                "economics": "No economics exist when the exact run opens zero trades.",
                "cost_stress": "No realized trade set exists for a cost-stress calculation.",
                "winning_trade_causes": "There are no winning trades in a zero-trade run.",
                "losing_trade_causes": "There are no losing trades in a zero-trade run.",
            },
        },
        "chart_contract": {
            "sample_basis": sample_basis,
            "available_winners": 2 if trades else 0,
            "available_losers": 2 if trades else 0,
            "rendered_winners": 2 if trades else 0,
            "rendered_losers": 2 if trades else 0,
            "available_rejections": 0 if trades else 2,
            "rendered_rejections": 0 if trades else 2,
            "minimum_each": 2,
            "entry_sl_tp_exit_visible": bool(trades),
            "higher_timeframe_context": True,
            "higher_timeframe": "H1",
            "entry_candle_centered": True,
            "post_entry_bars_visible": True,
            "outcome_region_labeled": True,
            "decision_asof_separate": True,
            "decision_outcome_hidden": True,
            "decision_net_r_hidden": True,
            "decision_active_indicators_visible": True,
            "decision_indicator_provenance": "mt5_decision_telemetry",
        },
        "anti_overfit_contract": {
            "plan_frozen_pre_outcome": True,
            "one_change_one_run": True,
            "posthoc_rule_change_authorized": False,
        },
        "limitations": ["Synthetic validator fixture only."],
    }
    path = root / "delivery.json"
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _run(packet: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--packet", str(packet), "--workspace", str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_economic_delivery_packet_passes(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    result = _run(packet, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EA_DELIVERY_PACKET_OK" in result.stdout
    assert "class=economic_run" in result.stdout


def test_delivery_packet_rejects_missing_logic_binding(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["bindings"] = [b for b in payload["bindings"] if b["role"] != "logic_matrix"]
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "missing required binding roles: logic_matrix" in result.stderr


def test_delivery_packet_rejects_tampered_hash(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    source = next(b for b in payload["bindings"] if b["role"] == "source")
    source["sha256"] = "0" * 64
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "source SHA256 mismatch" in result.stderr


def test_delivery_packet_rejects_missing_failure_analysis(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    del payload["analysis_contract"]["statuses"]["losing_trade_causes"]
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "analysis status missing: losing_trade_causes" in result.stderr


def test_delivery_packet_rejects_chart_without_sl_tp_exit(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    manifest = tmp_path / "casebook" / "cases_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["results"][0]["sl_line_rendered"] = False
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    delivery = json.loads(packet.read_text(encoding="utf-8"))
    binding = next(b for b in delivery["bindings"] if b["role"] == "casebook_manifest")
    binding["bytes"] = manifest.stat().st_size
    binding["sha256"] = _sha(manifest)
    packet.write_text(json.dumps(delivery), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "casebook case_1 missing SL line" in result.stderr


def test_delivery_packet_rejects_missing_decision_casebook_binding(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["bindings"] = [
        row for row in payload["bindings"] if row["role"] != "decision_casebook_manifest"
    ]
    packet.write_text(json.dumps(payload), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "missing required binding roles: decision_casebook_manifest" in result.stderr


def test_delivery_packet_rejects_decision_chart_that_discloses_outcome(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    manifest = tmp_path / "decision_casebook" / "cases_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["results"][0]["outcome_hidden"] = False
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    delivery = json.loads(packet.read_text(encoding="utf-8"))
    binding = next(
        row for row in delivery["bindings"] if row["role"] == "decision_casebook_manifest"
    )
    binding["bytes"] = manifest.stat().st_size
    binding["sha256"] = _sha(manifest)
    packet.write_text(json.dumps(delivery), encoding="utf-8")
    result = _run(packet, tmp_path)
    assert result.returncode != 0
    assert "decision casebook case_1 outcome_hidden must be true" in result.stderr


def test_zero_trade_delivery_requires_funnel_and_rejection_cases(tmp_path: Path) -> None:
    packet = _packet(tmp_path, delivery_class="zero_trade_terminal")
    result = _run(packet, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "class=zero_trade_terminal" in result.stdout


def test_alpha_exposes_delivery_completion_gate() -> None:
    text = ALPHA.read_text(encoding="utf-8-sig")
    assert '"delivery"' in text
    assert "validate_ea_delivery_packet.py" in text
    assert "EA delivery packet required" in text


def test_alpha_delivery_command_runs_the_real_validator() -> None:
    assert POWERSHELL, "PowerShell is required"
    runtime = ALPHA_ROOT / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="delivery-gate-test-", dir=runtime) as temp:
        packet = _packet(WORKSPACE, root=Path(temp))
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ALPHA),
                "delivery",
                "-Packet",
                str(packet),
            ],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EA_DELIVERY_PACKET_OK" in result.stdout


def test_delivery_templates_cover_every_required_analysis_surface() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    roles = {row["role"] for row in template["bindings"]}
    assert {
        "logic_matrix", "source", "compiled_binary", "compile_log",
        "test_receipt", "nonrepaint_audit", "run_manifest", "tester_report",
        "lifecycle_trades", "run_meta", "log_triage", "economic_analysis",
        "casebook_manifest", "decision_casebook_manifest", "readout",
    } <= roles
    assert set(template["analysis_contract"]["statuses"]) == ANALYSIS_DIMENSIONS
    assert schema["$id"] == "alphafactory.ea_delivery_packet.v1"
    logic_text = LOGIC_TEMPLATE.read_text(encoding="utf-8")
    assert "Trader observation / intent" in logic_text
    assert "Context must not silently become the" in logic_text
