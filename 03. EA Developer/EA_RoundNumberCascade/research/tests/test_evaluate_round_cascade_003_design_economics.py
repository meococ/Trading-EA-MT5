from __future__ import annotations

import json
import math
import sys
import types
from io import BytesIO
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR))

import evaluate_round_cascade_003_design_economics as sut


UTC = timezone.utc


def iso(at: datetime) -> str:
    return at.astimezone(UTC).isoformat().replace("+00:00", "Z")


def m1(at: datetime, *, open_: float = 1.1000, high: float | None = None, low: float | None = None, close: float | None = None) -> dict:
    return {
        "time_utc": iso(at),
        "open": open_,
        "high": open_ if high is None else high,
        "low": open_ if low is None else low,
        "close": open_ if close is None else close,
    }


def minute_window(start: datetime, *, open_: float = 1.1000, close: float = 1.1000) -> list[dict]:
    rows = []
    for i in range(60):
        value = open_ if i == 0 else close
        rows.append(m1(start + timedelta(minutes=i), open_=value, high=value, low=value, close=value))
    return rows


def signal(at: datetime, *, arm: str = "TRUE_0050", direction: str = "LONG", atr20_pips: float = 10.0) -> dict:
    return {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "arm": arm,
        "direction": direction,
        "level_pips": 11000,
        "decision_bar_start_utc": iso(at - timedelta(minutes=5)),
        "decision_time_utc": iso(at),
        "planned_entry_time_utc": iso(at),
        "atr20_pips": atr20_pips,
        "cost_to_stop_ratio_1p5": 1.5 / atr20_pips,
    }


def trade(at: datetime, gross_r: float, *, arm: str = "TRUE_0050", year: int | None = None, atr20_pips: float = 10.0) -> sut.TradeResult:
    return sut.TradeResult(
        arm=arm,
        planned_entry_time_utc=at,
        exit_time_utc=at + timedelta(minutes=60),
        direction="LONG",
        entry_bid=1.1000,
        exit_bid=1.1000 + gross_r * atr20_pips * 0.0001,
        stop_bid=1.0990,
        atr20_pips=atr20_pips,
        gross_R=gross_r,
        exit_reason="TIME",
        year=at.year if year is None else year,
    )


def write_json(path: Path, value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sut.sha256_bytes(payload)


def write_jsonl(path: Path, rows: list[dict]) -> str:
    payload = b"".join(sut.canonical_json_bytes(row) + b"\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sut.sha256_bytes(payload)


def make_dsr_tool(root: Path, monkeypatch: pytest.MonkeyPatch, value: float = 0.96) -> str:
    rel = "tools/dsr.py"
    payload = (
        "def dsr(sr, n_obs, skew, kurt, var_sr_trials, n_trials):\n"
        "    assert n_trials == 2\n"
        "    return " + repr(value) + "\n"
    ).encode()
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    monkeypatch.setattr(sut, "DSR_REL", rel)
    monkeypatch.setattr(sut, "DSR_SHA256", sut.sha256_bytes(payload))
    return sut.sha256_bytes(payload)


def test_import_is_inert_and_workspace_root_is_required() -> None:
    assert sut.REVIEWED_RUN_PACKET_SHA256 is None
    assert sut.main([]) == 2
    assert sut.main(["--run-reviewed-design-economics"]) == 1


def test_strict_json_rejects_malformed_duplicate_and_nonfinite() -> None:
    with pytest.raises(sut.EngineeringInvalid, match="invalid packet JSON"):
        sut.strict_json_loads(b"{", label="packet")
    with pytest.raises(sut.EngineeringInvalid, match="duplicate JSON key"):
        sut.strict_json_loads(b'{"a":1,"a":2}', label="packet")
    with pytest.raises(sut.EngineeringInvalid, match="non-finite JSON value"):
        sut.strict_json_loads(b'{"a":NaN}', label="packet")


def test_verified_dsr_bytes_are_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dsr_sha = make_dsr_tool(tmp_path, monkeypatch)
    assert sut.load_verified_dsr(tmp_path)[1] == dsr_sha
    (tmp_path / "tools/dsr.py").write_text("def dsr(*_args):\n    return 0.1\n", encoding="utf-8")
    with pytest.raises(sut.EngineeringInvalid, match="SHA256 mismatch"):
        sut.load_verified_dsr(tmp_path)


def test_verified_dsr_executes_exact_payload_without_path_reread(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"def dsr(*_args):\n    return 0.97\n"

    def fake_read_verified(path: Path, expected_sha256: str | None = None) -> bytes:
        assert path == (tmp_path / sut.DSR_REL).resolve()
        assert expected_sha256 == sut.DSR_SHA256
        return payload

    monkeypatch.setattr(sut, "DSR_REL", "missing/dsr.py")
    monkeypatch.setattr(sut, "DSR_SHA256", sut.sha256_bytes(payload))
    monkeypatch.setattr(sut, "read_verified_bytes_once", fake_read_verified)
    dsr_func, dsr_sha = sut.load_verified_dsr(tmp_path)
    assert dsr_sha == sut.sha256_bytes(payload)
    assert dsr_func(0, 0, 0, 0, 0, 2) == 0.97


def test_sentinel_normalization_rejects_multiple_or_noncanonical_assignments() -> None:
    armed = b'REVIEWED_RUN_PACKET_SHA256: str | None = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"\n'
    assert sut.normalize_reviewer_bound_source(armed) == b"REVIEWED_RUN_PACKET_SHA256: str | None = None\n"
    with pytest.raises(sut.EngineeringInvalid, match="exactly once"):
        sut.normalize_reviewer_bound_source(armed + armed)
    with pytest.raises(sut.EngineeringInvalid, match="exactly once"):
        sut.normalize_reviewer_bound_source(b"REVIEWED_RUN_PACKET_SHA256 = None\n")


def test_design_shard_paths_are_dataset_rooted_and_cannot_escape(tmp_path: Path) -> None:
    relative = "public/DESIGN/2016-01-04/m1.parquet"
    expected = (tmp_path / Path(sut.DESIGN_MANIFEST_REL).parent.parent / relative).resolve()
    assert sut.resolve_design_shard_file(tmp_path, relative) == expected
    for bad in (
        "public/DESIGN/../VALIDATION/2016-01-04/m1.parquet",
        "public/VALIDATION/2016-01-04/m1.parquet",
        "design/public/DESIGN/2016-01-04/m1.parquet",
    ):
        with pytest.raises(sut.EngineeringInvalid):
            sut.resolve_design_shard_file(tmp_path, bad)


def test_project_twelve_m5_bars_requires_exact_schema_geometry_and_contiguity() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    rows = minute_window(start, open_=1.1000, close=1.1010)
    bars = sut.project_twelve_m5_bars(rows, start)
    assert len(bars) == 12
    assert bars[0].open == pytest.approx(1.1000)
    assert bars[-1].close == pytest.approx(1.1010)

    with pytest.raises(sut.EngineeringInvalid, match="missing M1 minute"):
        sut.project_twelve_m5_bars(rows[:17] + rows[18:], start)
    with pytest.raises(sut.EngineeringInvalid, match="duplicate M1 minute"):
        sut.project_twelve_m5_bars(rows + [rows[0]], start)
    with pytest.raises(sut.EngineeringInvalid, match="outside required window"):
        sut.project_twelve_m5_bars(rows + [m1(start + timedelta(minutes=60))], start)
    bad = dict(rows[0])
    bad["low"] = bad["high"] + 0.1
    with pytest.raises(sut.EngineeringInvalid, match="OHLC geometry"):
        sut.project_twelve_m5_bars([bad] + rows[1:], start)


def test_parquet_shard_decodes_verified_payload_without_path_reread(monkeypatch: pytest.MonkeyPatch) -> None:
    at = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)

    class FakeTable:
        def to_pylist(self) -> list[dict]:
            return [m1(at)]

    parquet_mod = types.ModuleType("pyarrow.parquet")

    def read_table(source, columns):
        assert isinstance(source, BytesIO)
        assert source.getvalue() == b"verified parquet bytes"
        assert set(columns) == sut.M1_KEYS
        return FakeTable()

    parquet_mod.read_table = read_table
    pyarrow_mod = types.ModuleType("pyarrow")
    pyarrow_mod.parquet = parquet_mod
    monkeypatch.setitem(sys.modules, "pyarrow", pyarrow_mod)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", parquet_mod)
    rows = sut.read_m1_shard(b"verified parquet bytes", Path("missing.parquet"), label="parquet")
    assert rows[0]["time_utc"] == at


def test_stop_touch_has_adverse_precedence_and_time_exit_uses_twelfth_close() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    stopped_rows = minute_window(start, open_=1.1000, close=1.1015)
    stopped_rows[11]["low"] = 1.0989
    stopped = sut.simulate_signal(signal(start, direction="LONG", atr20_pips=10.0), stopped_rows)
    assert stopped.exit_reason == "STOP"
    assert stopped.exit_time_utc == start + timedelta(minutes=15)
    assert stopped.gross_R == pytest.approx(-1.0)

    timed = sut.simulate_signal(signal(start, direction="LONG", atr20_pips=10.0), minute_window(start, open_=1.1000, close=1.1015))
    assert timed.exit_reason == "TIME"
    assert timed.exit_time_utc == start + timedelta(minutes=60)
    assert timed.gross_R == pytest.approx(1.5)


def test_overlap_before_prior_exit_is_invalid_but_equality_is_allowed() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    sut.assert_no_overlap([trade(start, 0.1), trade(start + timedelta(minutes=60), 0.1)])
    with pytest.raises(sut.EngineeringInvalid, match="overlapping"):
        sut.assert_no_overlap([trade(start, 0.1), trade(start + timedelta(minutes=59), 0.1)])


def test_profit_factor_and_relative_pf_truth_table_are_explicit() -> None:
    finite = sut.profit_factor([2.0, -1.0])
    no_loss = sut.profit_factor([1.0, 2.0])
    assert finite == {"status": "FINITE", "value": 2.0}
    assert no_loss == {"status": "NO_LOSS", "value": None}
    assert sut.relative_pf(no_loss, no_loss) == {"status": "ZERO_BOTH_NO_LOSS", "value": None}
    assert sut.relative_pf(finite, no_loss)["status"] == "NEGATIVE_INFINITY"
    assert sut.relative_pf(no_loss, finite)["status"] == "POSITIVE_INFINITY"
    with pytest.raises(sut.EngineeringInvalid, match="non-finite PF input"):
        sut.profit_factor([math.inf])


def test_cost_metrics_cadence_years_and_drawdown_use_frozen_denominators() -> None:
    rows = [trade(datetime(year, 1, 2, tzinfo=UTC), 2.0) for year in sut.DESIGN_YEARS[:4]]
    rows.append(trade(datetime(2020, 1, 2, tzinfo=UTC), -0.5))
    metrics = sut.arm_cost_metrics(rows, 1.50)
    assert metrics["net_R"][0] == pytest.approx(1.85)
    assert sut.cadence_per_elapsed_week(1229) == pytest.approx(1229 / 260.5714285714)
    yearly = sut.fixed_year_totals(rows, 1.50)
    assert list(yearly["year_totals"]) == ["2016", "2017", "2018", "2019", "2020"]
    assert yearly["positive_year_count"] == 4
    assert sut.compounding_drawdown_pct(rows, 1.50) > 0
    with pytest.raises(sut.EngineeringInvalid, match="outside DESIGN years"):
        sut.fixed_year_totals([trade(datetime(2021, 1, 2, tzinfo=UTC), 1.0)], 1.50)


def test_packet_and_registry_tamper_are_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sut, "REVIEWED_RUN_PACKET_SHA256", "A" * 64)
    packet = minimal_packet(tmp_path)
    with pytest.raises(sut.EngineeringInvalid, match="reviewed sentinel"):
        sut.validate_run_packet(packet, "B" * 64)
    packet_extra = dict(packet)
    packet_extra["unexpected"] = True
    with pytest.raises(sut.EngineeringInvalid, match="schema keys mismatch"):
        sut.validate_run_packet(packet_extra, "A" * 64)

    registry = {
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "parent_candidate": sut.PARENT_CANDIDATE,
        "state": "probe",
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.FROZEN_PLAN_SHA256,
        "validation": {
            "design_economics_run_authorized": True,
            "run_packet_sha256": "B" * 64,
            "attempt_id": sut.ATTEMPT_ID,
            "evidence_root": sut.EVIDENCE_ROOT_REL,
            "attempts_consumed": 0,
            "evaluator_path": sut.EVALUATOR_REL,
            "test_path": sut.TEST_REL,
            "evaluator_base_sha256": "E" * 64,
            "test_sha256": "T" * 64,
            "review_receipt_sha256": "R" * 64,
            **{field: False for field in sut.FORBIDDEN_AUTHORITY_FIELDS},
        },
    }
    write_jsonl(tmp_path / sut.REGISTRY_REL, [registry])
    with pytest.raises(sut.EngineeringInvalid, match="registry run packet hash mismatch"):
        sut.validate_latest_registry_authority(tmp_path, "A" * 64)


def test_input_hash_tamper_is_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "input.jsonl"
    original = write_jsonl(path, [{"a": 1}])
    path.write_text('{"a":2}\n', encoding="utf-8")
    with pytest.raises(sut.EngineeringInvalid, match="SHA256 mismatch"):
        sut.load_jsonl_file(path, original, label="input")


def test_design_receipt_requires_actual_keys_without_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sut, "DESIGN_MANIFEST_REL", "manifest.jsonl")
    manifest_sha = write_jsonl(tmp_path / "manifest.jsonl", [])
    monkeypatch.setattr(sut, "DESIGN_MANIFEST_SHA256", manifest_sha)
    monkeypatch.setattr(sut, "DESIGN_RECEIPT_REL", "receipt.json")
    receipt_sha = write_json(tmp_path / "receipt.json", {
        "design_manifest_sha256": manifest_sha,
        "public_m1_source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
    })
    monkeypatch.setattr(sut, "DESIGN_RECEIPT_SHA256", receipt_sha)
    with pytest.raises(sut.EngineeringInvalid, match="schema mismatch"):
        sut.validate_design_receipt(tmp_path)


def minimal_packet(root: Path) -> dict:
    return {
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "parent_candidate": sut.PARENT_CANDIDATE,
        "plan_path": sut.PLAN_REL,
        "plan_sha256": sut.FROZEN_PLAN_SHA256,
        "attempt_id": sut.ATTEMPT_ID,
        "evidence_root": sut.EVIDENCE_ROOT_REL,
        "registry_path": sut.REGISTRY_REL,
        "source_ledger_path": sut.SOURCE_LEDGER_REL,
        "source_ledger_sha256": sut.SOURCE_LEDGER_SHA256,
        "source_started_path": sut.SOURCE_STARTED_REL,
        "source_started_sha256": sut.SOURCE_STARTED_SHA256,
        "source_report_path": sut.SOURCE_REPORT_REL,
        "source_report_sha256": sut.SOURCE_REPORT_SHA256,
        "source_receipt_path": sut.SOURCE_RECEIPT_REL,
        "source_receipt_sha256": sut.SOURCE_RECEIPT_SHA256,
        "source_terminal_path": sut.SOURCE_TERMINAL_REL,
        "source_terminal_sha256": sut.SOURCE_TERMINAL_SHA256,
        "design_manifest_path": sut.DESIGN_MANIFEST_REL,
        "design_manifest_sha256": sut.DESIGN_MANIFEST_SHA256,
        "design_receipt_path": sut.DESIGN_RECEIPT_REL,
        "design_receipt_sha256": sut.DESIGN_RECEIPT_SHA256,
        "public_m1_source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        "dsr_path": sut.DSR_REL,
        "dsr_sha256": sut.DSR_SHA256,
        "expected_true_signals": sut.EXPECTED_SIGNAL_COUNTS["TRUE_0050"],
        "expected_shifted_signals": sut.EXPECTED_SIGNAL_COUNTS["SHIFTED_0025"],
        "registry_authority": True,
        "evaluator_path": sut.EVALUATOR_REL,
        "test_path": sut.TEST_REL,
        "reviewed_evaluator_base_sha256": sut.reviewer_base_sha256(Path(sut.__file__).read_bytes()),
        "reviewed_test_sha256": sut.sha256_file(Path(__file__)),
        "review_receipt_path": sut.REVIEW_RECEIPT_REL,
        "review_receipt_sha256": "",
        "economics_authorized": True,
        "post_entry_ohlc_authorized": True,
        "attempt_limit": 1,
        **{field: False for field in sut.FORBIDDEN_AUTHORITY_FIELDS},
    }


def setup_synthetic_workspace(root: Path, monkeypatch: pytest.MonkeyPatch, *, bad_after_start: bool = False) -> Path:
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE_0050": 2, "SHIFTED_0025": 2})
    monkeypatch.setattr(sut, "SOURCE_LEDGER_REL", "hyp002/ledger.jsonl")
    monkeypatch.setattr(sut, "SOURCE_STARTED_REL", "hyp002/attempt_started.json")
    monkeypatch.setattr(sut, "SOURCE_REPORT_REL", "hyp002/report.json")
    monkeypatch.setattr(sut, "SOURCE_RECEIPT_REL", "hyp002/receipt.json")
    monkeypatch.setattr(sut, "SOURCE_TERMINAL_REL", "hyp002/terminal.json")
    monkeypatch.setattr(sut, "DESIGN_MANIFEST_REL", "design/manifest.jsonl")
    monkeypatch.setattr(sut, "DESIGN_RECEIPT_REL", "design/receipt.json")
    monkeypatch.setattr(sut, "REGISTRY_REL", "registry.jsonl")
    monkeypatch.setattr(sut, "RUN_PACKET_REL", "packet.json")
    monkeypatch.setattr(sut, "REVIEW_RECEIPT_REL", "review.json")
    monkeypatch.setattr(sut, "EVIDENCE_ROOT_REL", "evidence/HYP003-DESIGN-ECON-001")
    make_dsr_tool(root, monkeypatch)

    evaluator_copy = root / sut.EVALUATOR_REL
    evaluator_copy.parent.mkdir(parents=True, exist_ok=True)
    evaluator_copy.write_bytes(Path(sut.__file__).read_bytes())
    test_copy = root / sut.TEST_REL
    test_copy.parent.mkdir(parents=True, exist_ok=True)
    test_copy.write_bytes(Path(__file__).read_bytes())
    monkeypatch.setattr(sut, "__file__", str(evaluator_copy))

    plan_path = root / sut.PLAN_REL
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("frozen plan", encoding="utf-8")
    monkeypatch.setattr(sut, "FROZEN_PLAN_SHA256", sut.sha256_file(plan_path))

    starts = [
        datetime(2016, 1, 4, 10, 0, tzinfo=UTC),
        datetime(2016, 1, 4, 11, 0, tzinfo=UTC),
        datetime(2016, 1, 4, 12, 0, tzinfo=UTC),
        datetime(2016, 1, 4, 13, 0, tzinfo=UTC),
    ]
    signals = [
        signal(starts[0], arm="TRUE_0050"),
        signal(starts[1], arm="TRUE_0050"),
        signal(starts[2], arm="SHIFTED_0025"),
        signal(starts[3], arm="SHIFTED_0025"),
    ]
    ledger_sha = write_jsonl(root / sut.SOURCE_LEDGER_REL, signals)
    monkeypatch.setattr(sut, "SOURCE_LEDGER_SHA256", ledger_sha)

    shard_rows = []
    for start in starts:
        shard_rows.extend(minute_window(start, open_=1.1000, close=1.1020))
    if bad_after_start:
        shard_rows = shard_rows[:-1]
    dataset_root = root / Path(sut.DESIGN_MANIFEST_REL).parent.parent
    shard_path = dataset_root / "public/DESIGN/2016-01-04/m1.jsonl"
    shard_sha = write_jsonl(shard_path, shard_rows)
    manifest = [{
        "date": "2016-01-04",
        "relative_path": "public/DESIGN/2016-01-04/m1.jsonl",
        "sha256": shard_sha,
        "bytes": shard_path.stat().st_size,
        "rows": len(shard_rows),
    }]
    manifest_sha = write_jsonl(root / sut.DESIGN_MANIFEST_REL, manifest)
    monkeypatch.setattr(sut, "DESIGN_MANIFEST_SHA256", manifest_sha)
    receipt = {
        "design_manifest_sha256": manifest_sha,
        "source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }
    monkeypatch.setattr(sut, "DESIGN_RECEIPT_SHA256", write_json(root / sut.DESIGN_RECEIPT_REL, receipt))

    start_sha = write_json(root / "hyp002/attempt_started.json", {"status": "STARTED"})
    monkeypatch.setattr(sut, "SOURCE_STARTED_SHA256", start_sha)
    zero_counters = {
        "post_decision_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "performance_trials_executed": 0,
        "economic_simulation_executed": False,
        "mt5_launches": 0,
        "mql5_files_created": 0,
        "research_validation_opened": False,
        "research_holdout_opened": False,
        "network_calls": 0,
    }
    source_report_sha = write_json(root / "hyp002/report.json", {
        "verdict": "PASS_SOURCE_FEASIBILITY",
        "zero_counters": zero_counters,
        "source_contract": {
            "design_manifest_sha256": manifest_sha,
            "design_receipt_sha256": sut.DESIGN_RECEIPT_SHA256,
            "public_m1_source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        },
    })
    source_receipt_sha = write_json(root / "hyp002/receipt.json", {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "verdict": "PASS_SOURCE_FEASIBILITY",
        "zero_counters": zero_counters,
        "artifacts": {
            "attempt_started.json": start_sha,
            "round_cascade_source_report.json": source_report_sha,
            "round_cascade_source_ledger.jsonl": ledger_sha,
        }
    })
    source_terminal_sha = write_json(root / "hyp002/terminal.json", {
        "state": "SUCCEEDED",
        "verdict": "PASS_SOURCE_FEASIBILITY",
        "attempt_started_sha256": start_sha,
        "report_sha256": source_report_sha,
        "ledger_sha256": ledger_sha,
        "source_feasibility_receipt_sha256": source_receipt_sha,
        "economics_executed": False,
        "mt5_launches": 0,
        "mql5_files_created": 0,
    })
    monkeypatch.setattr(sut, "SOURCE_REPORT_SHA256", source_report_sha)
    monkeypatch.setattr(sut, "SOURCE_RECEIPT_SHA256", source_receipt_sha)
    monkeypatch.setattr(sut, "SOURCE_TERMINAL_SHA256", source_terminal_sha)

    packet = minimal_packet(root)
    packet.update({
        "source_ledger_path": sut.SOURCE_LEDGER_REL,
        "source_ledger_sha256": ledger_sha,
        "source_started_path": sut.SOURCE_STARTED_REL,
        "source_started_sha256": start_sha,
        "source_report_path": sut.SOURCE_REPORT_REL,
        "source_report_sha256": source_report_sha,
        "source_receipt_path": sut.SOURCE_RECEIPT_REL,
        "source_receipt_sha256": source_receipt_sha,
        "source_terminal_path": sut.SOURCE_TERMINAL_REL,
        "source_terminal_sha256": source_terminal_sha,
        "design_manifest_path": sut.DESIGN_MANIFEST_REL,
        "design_manifest_sha256": manifest_sha,
        "design_receipt_path": sut.DESIGN_RECEIPT_REL,
        "design_receipt_sha256": sut.DESIGN_RECEIPT_SHA256,
        "registry_path": sut.REGISTRY_REL,
        "evidence_root": sut.EVIDENCE_ROOT_REL,
        "dsr_path": sut.DSR_REL,
        "dsr_sha256": sut.DSR_SHA256,
        "expected_true_signals": 2,
        "expected_shifted_signals": 2,
    })
    review = {
        "schema": "round_cascade_design_economics_implementation_review_v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "review_status": "PASS_TO_PREPARE_AUTHORITY",
        "reviewed_plan_path": sut.PLAN_REL,
        "reviewed_plan_sha256": sut.FROZEN_PLAN_SHA256,
        "reviewed_evaluator_path": sut.EVALUATOR_REL,
        "reviewed_evaluator_base_sha256": packet["reviewed_evaluator_base_sha256"],
        "reviewed_test_path": sut.TEST_REL,
        "reviewed_test_sha256": packet["reviewed_test_sha256"],
        "authority_granted": False,
        "permissions_reviewed": {
            "economics_authorized": True,
            "post_entry_ohlc_authorized": True,
            **{field: False for field in sut.FORBIDDEN_AUTHORITY_FIELDS},
        },
    }
    packet["review_receipt_sha256"] = write_json(root / "review.json", review)
    packet_path = root / "packet.json"
    packet_sha = write_json(packet_path, packet)
    monkeypatch.setattr(sut, "REVIEWED_RUN_PACKET_SHA256", packet_sha)
    write_jsonl(root / sut.REGISTRY_REL, [{
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "parent_candidate": sut.PARENT_CANDIDATE,
        "state": "probe",
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.FROZEN_PLAN_SHA256,
        "validation": {
            "design_economics_run_authorized": True,
            "run_packet_sha256": packet_sha,
            "attempt_id": sut.ATTEMPT_ID,
            "evidence_root": sut.EVIDENCE_ROOT_REL,
            "attempts_consumed": 0,
            "attempt_limit": 1,
            "evaluator_path": sut.EVALUATOR_REL,
            "test_path": sut.TEST_REL,
            "run_packet_path": sut.RUN_PACKET_REL,
            "review_receipt_path": sut.REVIEW_RECEIPT_REL,
            "economics_authorized": True,
            "post_entry_ohlc_authorized": True,
            "evaluator_base_sha256": packet["reviewed_evaluator_base_sha256"],
            "test_sha256": packet["reviewed_test_sha256"],
            "review_receipt_sha256": packet["review_receipt_sha256"],
            **{field: False for field in sut.FORBIDDEN_AUTHORITY_FIELDS},
        },
    }])
    return packet_path


def test_full_synthetic_execution_writes_artifact_hash_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet_path = setup_synthetic_workspace(tmp_path, monkeypatch)
    assert sut.execute_reviewed_design_economics(tmp_path, packet_path) == 0
    root = tmp_path / sut.EVIDENCE_ROOT_REL
    for name in sut.ARTIFACT_ORDER:
        assert (root / name).is_file()
    receipt = json.loads((root / "design_economics_receipt.json").read_text(encoding="utf-8"))
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["receipt_sha256"] == sut.sha256_file(root / "design_economics_receipt.json")
    assert receipt["artifact_sha256"]["attempt_started.json"] == sut.sha256_file(root / "attempt_started.json")
    assert receipt["artifact_sha256"]["design_gate_report.json"] == sut.sha256_file(root / "design_gate_report.json")
    assert terminal["artifact_sha256"]["design_economics_receipt.json"] == sut.sha256_file(root / "design_economics_receipt.json")
    for name in (
        "attempt_started.json",
        "design_economics_trade_ledger.jsonl",
        "design_arm_cost_metrics.json",
        "design_yearly_metrics.json",
        "design_drawdown_metrics.json",
        "design_dsr_inputs.json",
        "design_gate_report.json",
        "design_economics_receipt.json",
    ):
        assert terminal["artifact_sha256"][name] == sut.sha256_file(root / name)


def test_failure_after_start_writes_failure_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet_path = setup_synthetic_workspace(tmp_path, monkeypatch, bad_after_start=True)
    with pytest.raises(sut.EngineeringInvalid, match="missing exact M1 entry window"):
        sut.execute_reviewed_design_economics(tmp_path, packet_path)
    terminal = json.loads((tmp_path / sut.EVIDENCE_ROOT_REL / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert terminal["artifact_sha256"]["attempt_started.json"] == sut.sha256_file(tmp_path / sut.EVIDENCE_ROOT_REL / "attempt_started.json")
