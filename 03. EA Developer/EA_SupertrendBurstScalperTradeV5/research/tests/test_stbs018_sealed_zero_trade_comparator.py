from __future__ import annotations

import importlib.util
import copy
import json
import shutil
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "compare_stbs018_sealed_zero_trade_audit.py"
SPEC = importlib.util.spec_from_file_location("stbs018", MODULE_PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def journal_text() -> str:
    raw = M.INVENTORY_ROOT.joinpath("logs/tester_journal_delta.log").read_text(encoding="utf-8", errors="replace")
    return raw


def test_real_journal_passes_exact_reason_one_contract():
    result = M.analyze_journal(journal_text())
    assert result["reason"] == 1
    assert result["unique_signals"] == 690
    assert result["executable"] == 683


@pytest.mark.parametrize("needle,replacement", [
    ("reason=1", "reason=0"),
    ("reason=1", "reason=2"),
    ("failed=false", "failed=true"),
    ("margin_ready=683", "margin_ready=682"),
    ("|raw=690|", "|raw=690|extra=1|"),
])
def test_summary_mutations_fail(needle: str, replacement: str):
    with pytest.raises(RuntimeError):
        M.analyze_journal(journal_text().replace(needle, replacement, 1))


def test_nonidentical_duplicate_signal_fails():
    text = journal_text()
    first = next(line for line in text.splitlines() if "STBS_SIGNAL|" in line)
    changed = first.replace("direction=LONG", "direction=SHORT") if "direction=LONG" in first else first.replace("direction=SHORT", "direction=LONG")
    with pytest.raises(RuntimeError):
        M.analyze_journal(text.replace(first, changed, 1))


@pytest.mark.parametrize("marker", ["STBS_FATAL|x=1", "STBS_ENTRY_REQUEST|x=1", "STBS_DEAL|x=1"])
def test_forbidden_trade_markers_fail(marker: str):
    with pytest.raises(RuntimeError):
        M.analyze_journal(journal_text() + "\n" + marker)


def test_manifest_exact_provenance_values():
    manifest = json.loads(M.INVENTORY_ROOT.joinpath("run_manifest.json").read_text(encoding="utf-8-sig"))
    basis = manifest["data_quality_fingerprint_basis"]
    assert manifest["data_fingerprint"] == M.DATA_SHA
    assert manifest["data_quality_journal_delta"] == {"path": "logs/tester_journal_delta.log", "sha256": M.JOURNAL_SHA, "bytes_read": 857818, "files_read": 3, "truncated": False}
    assert basis["exact_match_count"] == 2
    assert basis["distinct_range_count"] == 1


def test_hyp013_provenance_predates_hyp017_run():
    task = json.loads(M.HYP013_TASK.read_text(encoding="utf-8-sig"))
    assert task["data_fingerprint"] == M.DATA_SHA
    assert M.sha256_file(M.HYP013_TASK) == M.HYP013_TASK_SHA
    assert M.sha256_file(M.HYP013_PREREG) == M.HYP013_PREREG_SHA
    assert M.sha256_file(M.HYP013_COST) == M.HYP013_COST_SHA


def test_attempt_root_is_absent_before_authority():
    assert not M.ATTEMPT_ROOT.exists()


def test_orders_shape_rejects_malformed_colspan():
    assert M.parse_colspans([(' colspan="bad"', '')]) is None
    assert M.parse_colspans([(' colspan="1" colspan="1"', '')]) is None


def test_static_hash_constants_match_inventory():
    assert M.sha256_file(M.INVENTORY_ROOT / "run_manifest.json") == M.MANIFEST_SHA
    assert M.sha256_file(M.INVENTORY_ROOT / "report.html") == M.REPORT_SHA
    assert M.sha256_file(M.INVENTORY_ROOT / "logs/tester_journal_delta.log") == M.JOURNAL_SHA
    assert M.sha256_file(M.INVENTORY_ROOT / "snapshot/source/EA_SupertrendBurstScalperTradeV5.mq5") == M.SOURCE_SHA
    assert M.sha256_file(M.INVENTORY_ROOT / "snapshot/build/EA_SupertrendBurstScalperTradeV5.ex5") == M.EX5_SHA
    assert M.sha256_file(M.INVENTORY_ROOT / "snapshot/config/config.ini") == M.CONFIG_SHA


def captured_inputs(tmp_path: Path, monkeypatch) -> dict[str, bytes]:
    monkeypatch.setattr(M, "ATTEMPT_ROOT", tmp_path)
    captured = tmp_path / "captured"
    captured.mkdir()
    shutil.copy2(M.QUANT, captured / "quant_analyzer.py")
    shutil.copy2(M.INVENTORY_ROOT / "report.html", captured / "report.html")
    registry_rows = M.REGISTRY.read_bytes().splitlines()
    hyp013_raw = next(raw for raw in registry_rows if M.sha256_bytes(raw) == M.HYP013_AUTHORITY_ROW_SHA)
    return {
        "run_manifest.json": (M.INVENTORY_ROOT / "run_manifest.json").read_bytes(),
        "report.html": (M.INVENTORY_ROOT / "report.html").read_bytes(),
        "journal.log": (M.INVENTORY_ROOT / "logs/tester_journal_delta.log").read_bytes(),
        "hyp013_task.json": M.HYP013_TASK.read_bytes(),
        "hyp013_authority_row.json": hyp013_raw,
        "hyp017_start.json": M.HYP017_START.read_bytes(),
        "hyp017_terminal.json": M.HYP017_TERMINAL.read_bytes(),
    }


def test_full_sealed_analysis_passes_twice(tmp_path: Path, monkeypatch):
    captured = captured_inputs(tmp_path, monkeypatch)
    first = M.analyze(captured)
    second = M.analyze(captured)
    assert first == second
    assert first["verdict"] == "PASS_ENGINEERING_ZERO_TRADE_MODEL0_AUDIT"


@pytest.mark.parametrize("field,value", [
    ("files_read", 2),
    ("files_read", 4),
    ("bytes_read", 857817),
    ("truncated", True),
])
def test_manifest_journal_provenance_mutations_fail(tmp_path: Path, monkeypatch, field: str, value):
    captured = captured_inputs(tmp_path, monkeypatch)
    manifest = json.loads(captured["run_manifest.json"].decode("utf-8-sig"))
    manifest["data_quality_journal_delta"][field] = value
    captured["run_manifest.json"] = json.dumps(manifest).encode()
    with pytest.raises(RuntimeError):
        M.analyze(captured)


def test_stale_fingerprint_substitution_fails(tmp_path: Path, monkeypatch):
    captured = captured_inputs(tmp_path, monkeypatch)
    manifest = json.loads(captured["run_manifest.json"].decode("utf-8-sig"))
    manifest["data_fingerprint"] = "077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4"
    captured["run_manifest.json"] = json.dumps(manifest).encode()
    with pytest.raises(RuntimeError):
        M.analyze(captured)


def test_duplicate_json_key_fails_closed():
    with pytest.raises(RuntimeError):
        M.strict_json(b'{"x":1,"x":2}', "fixture")


def test_exact_inventory_and_compile_log_are_frozen():
    actual = {path.relative_to(M.INVENTORY_ROOT).as_posix() for path in M.INVENTORY_ROOT.rglob("*") if path.is_file()}
    assert actual == M.EXPECTED_INVENTORY_FILES
    assert M.sha256_file(M.RUN_COMPILE_LOG) == M.RUN_COMPILE_LOG_SHA


def authority_fixture() -> dict:
    validation = {key: False for key in M.REQUIRED_FALSE_PERMISSIONS}
    validation.update({key: True for key in M.REQUIRED_TRUE_PERMISSIONS})
    validation.update({
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "comparator_attempt_id": M.ATTEMPT_ID,
        "comparator_attempt_limit": 1,
        "parent_hyp017_terminal_row_sha256": M.HYP017_TERMINAL_ROW_SHA,
        "expected_data_fingerprint": M.DATA_SHA,
        "run_manifest_path": (M.INVENTORY_ROOT.relative_to(M.ROOT) / "run_manifest.json").as_posix(),
        "run_manifest_sha256": M.MANIFEST_SHA,
        "tester_report_path": (M.INVENTORY_ROOT.relative_to(M.ROOT) / "report.html").as_posix(),
        "tester_report_sha256": M.REPORT_SHA,
        "tester_journal_path": (M.INVENTORY_ROOT.relative_to(M.ROOT) / "logs/tester_journal_delta.log").as_posix(),
        "tester_journal_sha256": M.JOURNAL_SHA,
        "source_snapshot_sha256": M.SOURCE_SHA,
        "ex5_snapshot_sha256": M.EX5_SHA,
        "config_snapshot_sha256": M.CONFIG_SHA,
        "hyp017_attempt_started_sha256": M.START_SHA,
        "hyp017_attempt_terminal_sha256": M.TERMINAL_SHA,
        "hyp017_contract_receipt_sha256": M.RECEIPT_SHA,
        "hyp013_task_packet_sha256": M.HYP013_TASK_SHA,
        "hyp013_prereg_sha256": M.HYP013_PREREG_SHA,
        "hyp013_cost_manifest_sha256": M.HYP013_COST_SHA,
        "reviewed_quant_analyzer_sha256": M.QUANT_SHA,
        "hyp013_preoutcome_authority_row_sha256": M.HYP013_AUTHORITY_ROW_SHA,
        "run_compile_log_sha256": M.RUN_COMPILE_LOG_SHA,
    })
    metrics = dict(M.ZERO_METRICS)
    metrics.update({"comparator_attempt_limit": 1, "comparator_attempts_consumed": 0})
    return {"state": "screened", "evidence_contract_kind": "data_acquisition", "validation": validation, "metrics": metrics}


@pytest.mark.parametrize("field", sorted(M.REQUIRED_FALSE_PERMISSIONS))
def test_every_false_permission_is_required(field: str):
    row = authority_fixture()
    row["validation"].pop(field)
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)


@pytest.mark.parametrize("field", sorted(M.REQUIRED_TRUE_PERMISSIONS))
def test_every_true_permission_is_required(field: str):
    row = authority_fixture()
    row["validation"][field] = False
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)


@pytest.mark.parametrize("field", sorted(M.ZERO_METRICS))
def test_every_zero_metric_is_required(field: str):
    row = authority_fixture()
    row["metrics"][field] = 1 if isinstance(row["metrics"][field], int) else True
    with pytest.raises(RuntimeError):
        M.validate_authority_row(row)
