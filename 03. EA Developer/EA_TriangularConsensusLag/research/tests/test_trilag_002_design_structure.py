from __future__ import annotations

import ast
import importlib.util
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest


RESEARCH = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, RESEARCH / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exporter = load_module("trilag002_exporter", "export_trilag_002_design_m1.py")
evaluator = load_module(
    "trilag002_evaluator", "evaluate_trilag_002_design_structure.py"
)


def row(symbol: str, stamp: str, close: float) -> dict[str, object]:
    return {"symbol": symbol, "time_utc": stamp, "close": close}


def test_import_is_inert_and_sentinels_are_disarmed() -> None:
    assert exporter.REVIEWED_REGISTRY_ROW_SHA256 is None
    assert evaluator.REVIEWED_REGISTRY_ROW_SHA256 is None
    assert "MetaTrader5" not in sys.modules


def test_ast_has_no_static_mt5_or_network_import_and_no_negative_shift() -> None:
    for filename in (
        "export_trilag_002_design_m1.py",
        "evaluate_trilag_002_design_structure.py",
    ):
        text = (RESEARCH / filename).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "MetaTrader5" not in imports
        assert not ({"requests", "urllib", "socket", "httpx"} & imports)
        assert ".shift(-" not in text
        assert "FILE_COMMON" not in text


def test_normalized_hashes_ignore_only_the_single_sentinel() -> None:
    for module, filename, helper in (
        (exporter, "export_trilag_002_design_m1.py", exporter.normalized_exporter_base_sha256),
        (evaluator, "evaluate_trilag_002_design_structure.py", evaluator.normalized_evaluator_base_sha256),
    ):
        payload = (RESEARCH / filename).read_bytes()
        disarmed = helper(payload)
        armed = payload.replace(
            b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
            b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
            1,
        )
        assert helper(armed) == disarmed
        assert len(disarmed) == 64
        assert module.normalized_base_sha256(payload) == disarmed


def test_default_production_paths_are_disarmed() -> None:
    with pytest.raises(exporter.ContractError, match="production"):
        exporter.run_production(workspace_root=RESEARCH.parents[2], production=False)
    with pytest.raises(evaluator.ContractError, match="production"):
        evaluator.run_production(workspace_root=RESEARCH.parents[2], production=False)


def test_exact_design_bounds_and_2021_rejection() -> None:
    exporter.assert_design_request(exporter.DESIGN_START, exporter.DESIGN_END)
    with pytest.raises(exporter.ContractError, match="end drift|2021"):
        exporter.assert_design_request(
            exporter.DESIGN_START, datetime(2021, 1, 1, tzinfo=timezone.utc)
        )
    epoch_2020 = int(datetime(2020, 12, 31, 23, 59, tzinfo=timezone.utc).timestamp())
    assert exporter.epoch_to_utc(epoch_2020) == "2020-12-31T23:59:00Z"
    epoch_2021 = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp())
    with pytest.raises(exporter.ContractError, match="outside DESIGN"):
        exporter.epoch_to_utc(epoch_2021)


def test_export_schema_is_close_only_and_strict() -> None:
    rows = [
        row("EURUSD", "2016-01-01T00:00:00Z", 1.1),
        row("USDJPY", "2016-01-01T00:00:00Z", 120.0),
        row("EURJPY", "2016-01-01T00:00:00Z", 132.0),
    ]
    coverage = exporter.validate_close_rows(rows)
    assert set(coverage) == set(exporter.SYMBOLS)
    assert exporter.SCHEMA_COLUMNS == ("symbol", "time_utc", "close")
    bad = [{"symbol": "EURUSD", "time_utc": "2016-01-01T00:00:00Z", "close": 1.1, "high": 1.2}]
    with pytest.raises(exporter.ContractError, match="schema"):
        exporter.validate_close_rows(bad)


def test_duplicate_and_nonpositive_close_are_rejected() -> None:
    duplicate = [
        row("EURUSD", "2016-01-01T00:00:00Z", 1.1),
        row("EURUSD", "2016-01-01T00:00:00Z", 1.1),
        row("USDJPY", "2016-01-01T00:00:00Z", 120.0),
        row("EURJPY", "2016-01-01T00:00:00Z", 132.0),
    ]
    with pytest.raises(exporter.ContractError, match="duplicate"):
        exporter.validate_close_rows(duplicate)
    invalid = [
        row("EURUSD", "2016-01-01T00:00:00Z", 0.0),
        row("USDJPY", "2016-01-01T00:00:00Z", 120.0),
        row("EURJPY", "2016-01-01T00:00:00Z", 132.0),
    ]
    with pytest.raises(exporter.ContractError, match="invalid close"):
        exporter.validate_close_rows(invalid)


def test_manifest_contains_hard_zero_outcome_surface() -> None:
    rows = [
        row("EURUSD", "2016-01-01T00:00:00Z", 1.1),
        row("USDJPY", "2016-01-01T00:00:00Z", 120.0),
        row("EURJPY", "2016-01-01T00:00:00Z", 132.0),
    ]
    manifest = exporter.build_manifest(
        rows=rows,
        parquet_sha256="A" * 64,
        terminal_metadata={"server": exporter.EXPECTED_SERVER},
    )
    assert manifest["schema"] == list(exporter.SCHEMA_COLUMNS)
    assert manifest["requested_end_utc"].startswith("2020-")
    counters = manifest["outcome_blind_counters"]
    assert counters["post_decision_bars_read"] == 0
    assert counters["trades_simulated"] == 0
    assert counters["economics_executed"] is False
    assert counters["validation_opened"] is False


def synthetic_panel() -> pd.DataFrame:
    count = 1660
    start = datetime(2016, 1, 4, tzinfo=timezone.utc)
    stamps = [start + timedelta(minutes=index) for index in range(count)]
    eu_returns = [1e-5 if index % 2 == 0 else -1e-5 for index in range(count)]
    uj_returns = [1e-5 if index % 3 == 0 else -1e-5 for index in range(count)]
    ej_returns = [1e-5 if index % 5 == 0 else -1e-5 for index in range(count)]
    for index, sign in ((1450, 1.0), (1510, -1.0), (1511, 1.0), (1600, -1.0)):
        eu_returns[index] = sign * 5e-4
        uj_returns[index] = sign * 5e-4
        ej_returns[index] = 0.0

    def closes(initial: float, returns: list[float]) -> list[float]:
        values = [initial]
        for value in returns[1:]:
            values.append(values[-1] * math.exp(value))
        return values

    series = {
        "EURUSD": closes(1.10, eu_returns),
        "USDJPY": closes(120.0, uj_returns),
        "EURJPY": closes(132.0, ej_returns),
    }
    records: list[dict[str, object]] = []
    for symbol in exporter.SYMBOLS:
        for stamp, close in zip(stamps, series[symbol]):
            records.append(row(symbol, stamp.strftime("%Y-%m-%dT%H:%M:%SZ"), close))
    return pd.DataFrame(records, columns=list(exporter.SCHEMA_COLUMNS))


def test_exact_inner_join_and_completed_bar_event_geometry() -> None:
    panel = evaluator.validate_panel(synthetic_panel())
    assert panel["common_rows"] == 1660
    assert all(value == 1.0 for value in panel["inner_join_ratio"].values())
    raw = evaluator.build_raw_events(panel["common"])
    raw_times = {event["bar_time_utc"] for event in raw}
    assert "2016-01-05T00:10:00Z" in raw_times  # index 1450
    assert "2016-01-05T01:10:00Z" in raw_times  # exactly 60 minutes later
    event = next(event for event in raw if event["bar_time_utc"] == "2016-01-05T00:10:00Z")
    assert event["decision_time_utc"] == "2016-01-05T00:11:00Z"
    assert event["direction"] == "LONG"
    assert event["z"] >= evaluator.Z_MIN
    assert event["gap_pips"] > 5.0


def test_global_cooldown_accepts_equality_and_rejects_one_minute_cluster() -> None:
    base = datetime(2016, 1, 5, tzinfo=timezone.utc)
    times = (base, base + timedelta(minutes=59), base + timedelta(minutes=60))
    raw = [
        {
            "decision_time_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bar_time_utc": (stamp - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "direction": "LONG",
            "gap_pips": 6.0,
        }
        for stamp in times
    ]
    accepted = evaluator.decluster_events(raw)
    assert [event["decision_time_utc"] for event in accepted] == [
        times[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
        times[2].strftime("%Y-%m-%dT%H:%M:%SZ"),
    ]
    assert accepted[0]["event_id"] == "TRILAG002-E000001"


def test_elapsed_week_cadence_and_all_structural_gates() -> None:
    summary = {
        "inner_join_ratio": {symbol: 0.995 for symbol in evaluator.SYMBOLS},
        "events_per_elapsed_week": 3.0,
        "accepted_event_count": 1000,
        "direction_count": {"LONG": 500, "SHORT": 500},
        "direction_share": {"LONG": 0.5, "SHORT": 0.5},
        "max_year_share": 0.2,
        "median_gap_pips": 6.0,
        "p25_gap_pips": 3.0,
    }
    gates = evaluator.build_gates(summary)
    assert len(gates) == 8
    assert all(gate["pass"] for gate in gates)
    summary["events_per_elapsed_week"] = 5.0001
    assert not next(
        gate for gate in evaluator.build_gates(summary)
        if gate["gate"] == "elapsed_week_cadence"
    )["pass"]


def test_event_ledger_is_canonical_and_replay_stable() -> None:
    events = [
        {
            "event_id": "TRILAG002-E000001",
            "bar_time_utc": "2016-01-01T00:00:00Z",
            "decision_time_utc": "2016-01-01T00:01:00Z",
            "direction": "LONG",
            "gap_pips": 5.5,
        }
    ]
    first = evaluator.canonical_event_ledger(events)
    second = evaluator.canonical_event_ledger(events)
    assert first == second
    assert evaluator.sha256_bytes(first) == evaluator.sha256_bytes(second)
    assert json.loads(first) == events[0]


def test_dataset_loader_rejects_hash_and_sealed_counter_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(evaluator, "require_d_side", lambda path, label: Path(path))
    frame = synthetic_panel().iloc[:30].copy()
    parquet_path = tmp_path / evaluator.PARQUET_NAME
    frame.to_parquet(parquet_path, index=False)
    parquet_sha = evaluator.sha256_file(parquet_path)
    manifest = {
        "schema_version": "trilag_002_design_m1_manifest.v1",
        "hypothesis_id": evaluator.HYPOTHESIS_ID,
        "attempt_id": evaluator.EXPORT_ATTEMPT_ID,
        "split": "DESIGN",
        "requested_start_utc": evaluator.DESIGN_START_TEXT,
        "requested_end_utc": evaluator.DESIGN_END_TEXT,
        "plan_sha256": evaluator.PLAN_SHA256,
        "parquet_sha256": parquet_sha,
        "symbols": list(evaluator.SYMBOLS),
        "schema": list(evaluator.SCHEMA_COLUMNS),
        "design_years": list(evaluator.DESIGN_YEARS),
        "row_count": len(frame),
        "outcome_blind_counters": {
            "bars_requested_2021plus": 0,
            "bars_exported_2021plus": 0,
            "post_decision_bars_read": 0,
            "future_path_labels": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "pf_computed": 0,
            "pnl_computed": 0,
            "orders_submitted": 0,
            "network_calls": 0,
            "paid_requests_made": 0,
            "economics_executed": False,
            "validation_opened": False,
            "research_holdout_opened": False,
        },
    }
    manifest_path = tmp_path / evaluator.MANIFEST_NAME
    manifest_path.write_bytes(evaluator.canonical_json(manifest) + b"\n")
    loaded, _, hashes = evaluator.validate_manifest_and_load(dataset_root=tmp_path)
    assert len(loaded) == len(frame)
    assert hashes["parquet_sha256"] == parquet_sha
    manifest["outcome_blind_counters"]["post_decision_bars_read"] = 1
    manifest_path.write_bytes(evaluator.canonical_json(manifest) + b"\n")
    with pytest.raises(evaluator.ContractError, match="forbidden nonzero"):
        evaluator.validate_manifest_and_load(dataset_root=tmp_path)


def test_registry_authority_is_one_use_and_stage_specific() -> None:
    export_validation = {
        "design_export_run_authorized": True,
        "design_structure_evaluation_authorized": False,
        "one_use": True,
        "reviewed_exporter_base_sha256": "A" * 64,
        "reviewed_evaluator_base_sha256": "B" * 64,
        "reviewed_test_sha256": "C" * 64,
        "independent_review_receipt_sha256": "D" * 64,
    }
    export_row = {
        "hypothesis_id": exporter.HYPOTHESIS_ID,
        "state": "probe",
        "run_ids": [],
        "metrics": {"design_export_attempts_consumed": 0},
        "validation": export_validation,
    }
    line = exporter.canonical_json(export_row) + b"\n"
    assert exporter.validate_registry_authority(line, exporter.sha256_bytes(line)) == export_row
    export_row["metrics"]["design_export_attempts_consumed"] = 1
    consumed = exporter.canonical_json(export_row) + b"\n"
    with pytest.raises(exporter.ContractError, match="consumed"):
        exporter.validate_registry_authority(consumed, exporter.sha256_bytes(consumed))


def test_evaluate_frame_emits_no_economic_outputs() -> None:
    result = evaluator.evaluate_frame(synthetic_panel())
    assert result["verdict"] in {evaluator.VERDICT_PASS, evaluator.VERDICT_KILL}
    serialized = evaluator.canonical_json(
        {key: value for key, value in result.items() if key != "event_ledger_payload"}
    ).decode("utf-8")
    for forbidden in ("entry_price", "exit_price", "trade_return", "profit_factor", "expectancy", "drawdown"):
        assert forbidden not in serialized
