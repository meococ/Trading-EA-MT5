from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "compare_stbs028_semantic_validation_adapter.py"
SPEC = importlib.util.spec_from_file_location("stbs028", MODULE_PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def authority_fixture() -> dict:
    validation = {key: False for key in M.REQUIRED_FALSE}
    validation.update({key: True for key in M.REQUIRED_TRUE})
    validation.update(
        {
            "authority": "EXISTING_RUN_ECONOMIC_RECOVERY_ONLY",
            "comparator_attempt_id": M.ATTEMPT_ID,
            "comparator_attempt_limit": 1,
            "target_hypothesis_id": M.TARGET_ID,
            "target_run_id": M.RUN_ID,
            "parent_terminal_row_sha256": M.PARENT_TERMINAL_ROW_SHA,
            "run_manifest_sha256": M.RUN_MANIFEST_SHA,
            "run_report_sha256": M.REPORT_SHA,
            "run_journal_sha256": M.JOURNAL_SHA,
            "run_lifecycle_sha256": M.LIFECYCLE_SHA,
            "runmeta_sha256": M.RUNMETA_SHA,
            "run_source_snapshot_sha256": M.SOURCE_SHA,
            "run_ex5_snapshot_sha256": M.EX5_SHA,
            "run_config_snapshot_sha256": M.CONFIG_SHA,
            "parent_attempt_started_sha256": M.PARENT_START_SHA,
            "parent_attempt_terminal_sha256": M.PARENT_TERMINAL_SHA,
            "parent_failure_sha256": M.PARENT_FAILURE_SHA,
            "parent_failure_review_sha256": M.PARENT_REVIEW_SHA,
            "parent_prereg_sha256": M.PARENT_TASK_SHA,
            "parent_authority_row_sha256": M.PARENT_AUTHORITY_ROW_SHA,
            "parent_nonrepaint_artifact_sha256": M.PARENT_NR_ARTIFACT_SHA,
            "parent_verified_cost_artifact_sha256": M.PARENT_COST_ARTIFACT_SHA,
            "parent_derived_run_manifest_sha256": M.PARENT_DERIVED_RUN_MANIFEST_SHA,
            "parent_derived_cost_manifest_sha256": M.PARENT_DERIVED_COST_MANIFEST_SHA,
            "cost_source_manifest_sha256": M.PARENT_COST_SHA,
            "parent_execution_receipt_sha256": M.PARENT_EXECUTION_RECEIPT_SHA,
            "hyp013_preoutcome_task_sha256": M.HYP013_TASK_SHA,
            "historical_spread_source_sha256": M.SPREAD_SOURCE_SHA,
            "commission_source_sha256": M.COMMISSION_SOURCE_SHA,
            "slippage_source_sha256": M.SLIPPAGE_SOURCE_SHA,
            "cost_lineage_receipt_sha256": M.LINEAGE_RECEIPT_SHA,
            "raw_tick_failure_receipt_sha256": M.RAW_TICK_FAILURE_SHA,
            "reviewed_auditor_sha256": M.AUDITOR_SHA,
            "reviewed_cost_builder_sha256": M.COST_BUILDER_SHA,
            "reviewed_unified_validator_sha256": M.UNIFIED_SHA,
            "reviewed_quant_analyzer_sha256": M.QUANT_SHA,
        }
    )
    metrics = dict(M.ZERO_METRICS)
    metrics["comparator_attempt_limit"] = 1
    return {
        "state": "screened",
        "parent_candidate": M.PARENT_ID,
        "evidence_contract_kind": "economic",
        "model": 0,
        "source_hash": M.SOURCE_SHA,
        "acceptance_contract": dict(M.ACCEPTANCE),
        "validation": validation,
        "metrics": metrics,
    }


def synthetic_manifest(sealed_run: Path) -> dict:
    sidecars = [
        {"path": "logs/tester_journal_delta.log", "sha256": M.JOURNAL_SHA, "length": 1, "row_count": None},
        {"path": "logs/XAUUSD_LifecycleTrades_HYP-STBS-XAUUSD-M15-026_5604126.csv", "sha256": M.LIFECYCLE_SHA, "length": 1, "row_count": 928},
        {"path": "logs/XAUUSD_RunMeta_HYP-STBS-XAUUSD-M15-026_5604126.json", "sha256": M.RUNMETA_SHA, "length": 1, "row_count": None},
    ]
    return {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": M.TARGET_ID,
        "run_id": M.RUN_ID,
        "run_role": "control",
        "ea_name": M.EA_NAME,
        "symbol": "XAUUSD",
        "period": "M15",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 900,
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "telemetry_tier": "trade-only",
        "telemetry_profile": "lifecycle-v3",
        "visual_mode": False,
        "source_sha256": M.SOURCE_SHA,
        "ex5_sha256": M.EX5_SHA,
        "tester_ex5_sha256": M.EX5_SHA,
        "config_sha256": M.CONFIG_SHA,
        "report_sha256": M.REPORT_SHA,
        "contract_receipt_sha256": M.PARENT_EXECUTION_RECEIPT_SHA,
        "data_fingerprint": M.DATA_SHA,
        "broker_fingerprint": M.BROKER_SHA,
        "server_fingerprint": M.SERVER_SHA,
        "account_fingerprint": M.ACCOUNT_SHA,
        "report_path": str((sealed_run / "old-report.html").resolve()),
        "snapshot_root": str((sealed_run / "old-snapshot").resolve()),
        "source_snapshot": str((sealed_run / "old-source.mq5").resolve()),
        "ex5_snapshot": str((sealed_run / "old.ex5").resolve()),
        "config_snapshot": str((sealed_run / "old.ini").resolve()),
        "tester_ex5_path": str((sealed_run / "old-tester.ex5").resolve()),
        "config_file": str((sealed_run / "old-config.ini").resolve()),
        "include_snapshots": [],
        "sidecars": sidecars,
        "data_quality_journal_delta": {
            "path": "logs/tester_journal_delta.log",
            "sha256": M.JOURNAL_SHA,
            "bytes_read": 1753472,
            "files_read": 3,
            "truncated": False,
        },
    }


def test_attempt_root_absent_before_authority():
    assert not M.ATTEMPT_ROOT.exists()


def test_current_parent_terminal_row_is_exact():
    rows = M.registry_rows(M.REGISTRY.read_bytes())
    parent = [item for item in rows if item[0].get("hypothesis_id") == M.PARENT_ID][-1]
    assert parent[1] == M.PARENT_TERMINAL_ROW_SHA
    assert parent[0]["state"] == "killed"
    assert parent[0]["verdict"] == M.PARENT_TERMINAL_VERDICT


def test_bound_tools_and_parent_controls_match():
    assert M.sha256_file(M.AUDITOR) == M.AUDITOR_SHA
    assert M.sha256_file(M.COST_BUILDER) == M.COST_BUILDER_SHA
    assert M.sha256_file(M.UNIFIED) == M.UNIFIED_SHA
    assert M.sha256_file(M.QUANT) == M.QUANT_SHA
    assert M.sha256_file(M.PARENT_FAILURE) == M.PARENT_FAILURE_SHA
    assert M.sha256_file(M.PARENT_REVIEW) == M.PARENT_REVIEW_SHA
    assert M.sha256_file(M.PARENT_TASK) == M.PARENT_TASK_SHA
    assert M.sha256_file(M.PARENT_ATTEMPT_ROOT / "analysis/nonrepaint_audit.json") == M.PARENT_NR_ARTIFACT_SHA
    assert M.sha256_file(M.PARENT_ATTEMPT_ROOT / "analysis/verified_cost_artifact.json") == M.PARENT_COST_ARTIFACT_SHA
    assert M.sha256_file(M.PARENT_ATTEMPT_ROOT / "sealed_run/run_manifest.json") == M.PARENT_DERIVED_RUN_MANIFEST_SHA
    assert M.sha256_file(M.PARENT_ATTEMPT_ROOT / "controls/derived_cost_manifest.json") == M.PARENT_DERIVED_COST_MANIFEST_SHA
    assert M.sha256_file(M.PARENT_COST) == M.PARENT_COST_SHA
    assert M.sha256_file(M.PARENT_EXECUTION_RECEIPT) == M.PARENT_EXECUTION_RECEIPT_SHA
    assert M.sha256_file(M.HYP013_TASK) == M.HYP013_TASK_SHA


@pytest.mark.parametrize(
    "field",
    [
        "parent_terminal_row_sha256",
        "parent_attempt_started_sha256",
        "parent_attempt_terminal_sha256",
        "parent_failure_sha256",
        "parent_failure_review_sha256",
        "parent_prereg_sha256",
        "parent_authority_row_sha256",
        "parent_nonrepaint_artifact_sha256",
        "parent_verified_cost_artifact_sha256",
        "parent_derived_run_manifest_sha256",
        "parent_derived_cost_manifest_sha256",
    ],
)
@pytest.mark.parametrize("mutation", ["missing", "wrong"])
def test_every_parent_chain_authority_binding_is_required(field: str, mutation: str):
    row = authority_fixture()
    if mutation == "missing":
        row["validation"].pop(field)
    else:
        row["validation"][field] = "0" * 64
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)


@pytest.mark.parametrize(
    "source,expected_sha",
    [
        (M.PARENT_ATTEMPT_ROOT / "attempt_started.json", M.PARENT_START_SHA),
        (M.PARENT_ATTEMPT_ROOT / "attempt_terminal.json", M.PARENT_TERMINAL_SHA),
        (M.PARENT_ATTEMPT_ROOT / "analysis/nonrepaint_audit.json", M.PARENT_NR_ARTIFACT_SHA),
        (M.PARENT_ATTEMPT_ROOT / "analysis/verified_cost_artifact.json", M.PARENT_COST_ARTIFACT_SHA),
        (M.PARENT_ATTEMPT_ROOT / "sealed_run/run_manifest.json", M.PARENT_DERIVED_RUN_MANIFEST_SHA),
        (M.PARENT_ATTEMPT_ROOT / "controls/derived_cost_manifest.json", M.PARENT_DERIVED_COST_MANIFEST_SHA),
    ],
)
def test_parent_chain_byte_tamper_fails_closed(tmp_path: Path, source: Path, expected_sha: str):
    tampered = tmp_path / source.name
    tampered.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(RuntimeError):
        M.capture_to("tampered-parent", tampered, expected_sha, tmp_path / "captured.bin")


@pytest.mark.parametrize("field", sorted(M.REQUIRED_TRUE))
def test_every_true_permission_is_required(field: str):
    row = authority_fixture()
    row["validation"][field] = False
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)


@pytest.mark.parametrize("field", sorted(M.REQUIRED_FALSE))
def test_every_false_permission_is_required(field: str):
    row = authority_fixture()
    row["validation"].pop(field)
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)


@pytest.mark.parametrize("field", sorted(M.ZERO_METRICS))
def test_every_zero_metric_is_required(field: str):
    row = authority_fixture()
    row["metrics"][field] = 1 if isinstance(row["metrics"][field], int) else True
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)


def test_valid_authority_fixture_passes():
    M.validate_authority_row(authority_fixture())


def test_strict_json_rejects_duplicate_and_nonfinite():
    with pytest.raises(RuntimeError):
        M.strict_json(b'{"x":1,"x":2}', "fixture")
    with pytest.raises(RuntimeError):
        M.strict_json(b'{"x":NaN}', "fixture")


def test_claim_is_exclusive_and_precedes_reads(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(M, "ATTEMPT_ROOT", tmp_path / "attempt")
    start, digest = M.claim()
    assert start.is_file()
    assert M.sha256_file(start) == digest
    with pytest.raises(FileExistsError):
        M.claim()


def test_derived_manifest_places_snapshot_below_manifest_parent(tmp_path: Path, monkeypatch):
    sealed = tmp_path / "sealed_run"
    monkeypatch.setattr(M, "STATIC_NR_MANIFEST", tmp_path / "static.json")
    payload = synthetic_manifest(sealed)
    path, digest = M.build_derived_manifest(M.canonical(payload), sealed)
    derived = json.loads(path.read_text(encoding="utf-8"))
    assert M.sha256_file(path) == digest
    assert Path(derived["snapshot_root"]).resolve().is_relative_to(path.parent.resolve())
    assert Path(derived["source_snapshot"]).resolve().is_relative_to(Path(derived["snapshot_root"]).resolve())
    assert derived["report_path"] == str((sealed / "report.html").resolve())
    assert derived["nondecision_provenance_copytime_authorized"] is True
    assert derived["nondecision_provenance_authority_source"]["original_run_manifest_sha256"] == M.RUN_MANIFEST_SHA


def test_original_manifest_rejects_existing_permission(tmp_path: Path):
    payload = synthetic_manifest(tmp_path)
    payload["nondecision_provenance_copytime_authorized"] = True
    with pytest.raises(RuntimeError):
        M.validate_original_manifest(payload)


def test_derived_cost_manifest_changes_only_reference_paths(tmp_path: Path):
    original_raw = M.PARENT_COST.read_bytes()
    original = json.loads(original_raw.decode("utf-8-sig"))
    target, digest = M.build_derived_cost_manifest(original_raw, tmp_path / "controls")
    derived = json.loads(target.read_text(encoding="utf-8"))
    assert M.sha256_file(target) == digest
    assert derived["hypothesis_id"] == original["hypothesis_id"] == M.TARGET_ID
    assert derived["run_meta_contract"] == original["run_meta_contract"]
    assert derived["historical_spread_provenance"]["source_sha256"] == M.SPREAD_SOURCE_SHA
    assert derived["commission_provenance"]["source_sha256"] == M.COMMISSION_SOURCE_SHA
    assert derived["slippage_provenance"]["source_sha256"] == M.SLIPPAGE_SOURCE_SHA
    assert Path(derived["historical_spread_provenance"]["source"]).is_relative_to((tmp_path / "controls").resolve())


def test_nonrepaint_semantics_are_exact(tmp_path: Path):
    manifest = tmp_path / "run_manifest.json"
    source = tmp_path / "snapshot/source" / f"{M.EA_NAME}.mq5"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fixture")
    manifest.write_text("{}", encoding="utf-8")
    manifest_sha = M.sha256_file(manifest)
    payload = {
        "schema_version": "alphafactory_nonrepaint_audit.v1",
        "status": "PASS",
        "hypothesis_id": M.TARGET_ID,
        "run_id": M.RUN_ID,
        "manifest": str(manifest.resolve()),
        "manifest_sha256": manifest_sha,
        "collection_authority_verified": False,
        "audited_files": [{"path": str(source.resolve()), "sha256": M.SOURCE_SHA}],
        "findings": [],
        "allowed_new_bar_gates": [{
            "path": str(source.resolve()), "line": M.COPYTIME_LINE,
            "rule": "collection_first_date_copytime", "function": "CopyTime",
            "disposition": "allowed_collection_provenance_read",
        }],
        "generated_at_utc": "2026-08-10T00:00:00Z",
    }
    audit = tmp_path / "audit.json"
    audit.write_bytes(M.canonical(payload))
    M.validate_nonrepaint(audit, manifest, manifest_sha, source)
    payload["allowed_new_bar_gates"][0]["line"] = M.COPYTIME_LINE + 1
    audit.write_bytes(M.canonical(payload))
    with pytest.raises(RuntimeError):
        M.validate_nonrepaint(audit, manifest, manifest_sha, source)



def cost_fixture(report: Path) -> dict:
    return {
        "schema_version": "research_execution_cost_proxy.v1",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "promotion_eligible": False,
        "hypothesis_id": M.TARGET_ID,
        "run_id": M.RUN_ID,
        "report": str(report.resolve()),
        "report_sha256": M.REPORT_SHA,
        "economic_window": {
            "from": M.ECONOMIC_FROM,
            "to": M.ECONOMIC_TO,
            "boundary": "inclusive_calendar_dates",
            "trade_deal_count": 928,
            "first_trade_deal_time": "2018.01.02 00:00:00",
            "last_trade_deal_time": "2022.12.30 00:00:00",
        },
        "lifecycle_evidence": {"completed_positions": 464},
        "run_meta_evidence": {
            "hypothesis_id": M.TARGET_ID,
            "semantic_validation": {
                "runtime_failed": False,
                "declared_lifecycle_rows": 928,
                "actual_lifecycle_rows": 928,
                "row_count_reconciled": True,
            },
        },
        "trade_repricing": [{} for _ in range(464)],
        "scenarios": [
            {"scenario": "cost_x1_00"},
            {"scenario": "cost_x1_50"},
            {"scenario": "cost_x2_00"},
        ],
    }


def test_exact_semantic_validation_golden_path(tmp_path: Path):
    report = tmp_path / "report.html"
    M.validate_cost(cost_fixture(report), report)


@pytest.mark.parametrize(
    "field,value",
    [
        ("runtime_failed", True),
        ("declared_lifecycle_rows", 927),
        ("actual_lifecycle_rows", 927),
        ("row_count_reconciled", False),
        ("extra", 1),
    ],
)
def test_semantic_validation_value_mutations_fail(tmp_path: Path, field: str, value: object):
    report = tmp_path / "report.html"
    payload = cost_fixture(report)
    payload["run_meta_evidence"]["semantic_validation"][field] = value
    with pytest.raises(RuntimeError):
        M.validate_cost(payload, report)


def test_missing_legacy_only_and_dual_semantic_fields_fail(tmp_path: Path):
    report = tmp_path / "report.html"
    missing = cost_fixture(report)
    semantic = missing["run_meta_evidence"].pop("semantic_validation")
    with pytest.raises(RuntimeError):
        M.validate_cost(missing, report)
    legacy = cost_fixture(report)
    legacy["run_meta_evidence"].pop("semantic_validation")
    legacy["run_meta_evidence"]["semantic"] = semantic
    with pytest.raises(RuntimeError):
        M.validate_cost(legacy, report)
    dual = cost_fixture(report)
    dual["run_meta_evidence"]["semantic"] = dict(dual["run_meta_evidence"]["semantic_validation"])
    with pytest.raises(RuntimeError):
        M.validate_cost(dual, report)


def summary_fixture(baseline_status: str = "PASS") -> dict:
    names = sorted(M.ENGINEERING_GATES | M.ADDITIONAL_ECONOMIC_GATES | {"profit_factor"})
    gates = {name: {"status": "PASS", "actual": 1, "required": 1, "reason": ""} for name in names}
    gates["profit_factor"]["status"] = baseline_status
    baseline_names = sorted(M.ENGINEERING_GATES | {"profit_factor"})
    baseline_nonpassing = [name for name in baseline_names if gates[name]["status"] != "PASS"]
    baseline_verdict = "BLOCKED" if any(gates[name]["status"] == "BLOCKED" for name in baseline_names) else "FAIL" if baseline_nonpassing else "PASS"
    nonpassing = [name for name in gates if gates[name]["status"] != "PASS"]
    return {
        "schema_version": "alphafactory_validation_summary.v2",
        "stage": "challenger",
        "holding_contract": "scalp",
        "research_cost_proxy": True,
        "research_falsification_eligible": True,
        "promotion_eligible": False,
        "economic_window": {"from": M.ECONOMIC_FROM, "to": M.ECONOMIC_TO, "boundary": "inclusive_calendar_dates"},
        "gates": gates,
        "non_passing_gates": nonpassing,
        "verdict": "PASS" if not nonpassing else "REVIEW",
        "baseline_falsification_gate_names": baseline_names,
        "baseline_falsification_non_passing_gates": baseline_nonpassing,
        "baseline_falsification_verdict": baseline_verdict,
    }


def test_economic_verdict_mapping_is_exact():
    passed = M.classify_summary(summary_fixture("PASS"))
    failed = M.classify_summary(summary_fixture("FAIL"))
    blocked = M.classify_summary(summary_fixture("BLOCKED"))
    assert str(passed["verdict"]).startswith("PASS_ECONOMIC")
    assert str(failed["verdict"]).startswith("FAIL_ECONOMIC")
    assert str(blocked["verdict"]).startswith("KILL_ENGINEERING")


def test_baseline_pass_with_operational_blocker_is_engineering_kill():
    summary = summary_fixture("PASS")
    summary["gates"]["execution_reconciliation"]["status"] = "BLOCKED"
    summary["non_passing_gates"] = ["execution_reconciliation"]
    summary["verdict"] = "REVIEW"
    summary["baseline_falsification_non_passing_gates"] = ["execution_reconciliation"]
    summary["baseline_falsification_verdict"] = "BLOCKED"
    result = M.classify_summary(summary)
    assert result["economic_verdict_created"] is False
    assert str(result["verdict"]).startswith("KILL_ENGINEERING")


def test_baseline_fail_plus_operational_blocker_is_not_economic_fail():
    summary = summary_fixture("FAIL")
    summary["gates"]["equity_audit"]["status"] = "BLOCKED"
    summary["non_passing_gates"] = ["equity_audit", "profit_factor"]
    summary["verdict"] = "REVIEW"
    summary["baseline_falsification_non_passing_gates"] = ["equity_audit", "profit_factor"]
    summary["baseline_falsification_verdict"] = "BLOCKED"
    result = M.classify_summary(summary)
    assert result["economic_verdict_created"] is False
    assert result["economic_failed_gates"] == ["profit_factor"]


def test_validate_summary_rejects_exit_verdict_mismatch():
    passed = summary_fixture("PASS")
    M.validate_summary(passed, 0)
    with pytest.raises(RuntimeError):
        M.validate_summary(passed, 1)
    reviewed = summary_fixture("FAIL")
    M.validate_summary(reviewed, 1)
    with pytest.raises(RuntimeError):
        M.validate_summary(reviewed, 0)


def test_replay_projection_changes_with_operational_gate():
    left = summary_fixture("PASS")
    right = summary_fixture("PASS")
    right["gates"]["runner_invocation_success"]["status"] = "BLOCKED"
    assert M.canonical(M.validation_projection(left)) != M.canonical(M.validation_projection(right))


def test_execute_claim_is_before_authority_and_tools():
    source = MODULE_PATH.read_text(encoding="utf-8")
    body = source.split("def execute()", 1)[1]
    assert body.index("claim()") < body.index("authority()")
    assert body.index("validate_nonrepaint") < body.index("verified cost builder") < body.index("unified validation")
    assert "alpha.ps1" not in source
    assert "backtest" not in body.lower()
