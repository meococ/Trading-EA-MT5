from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import math
import os
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "research" / "evaluate_trendstack_002_design.py"
BUILDER_PATH = ROOT / "research" / "build_trendstack_002_design_request_plan.py"
DSR_PATH = ROOT.parents[1] / "02. AlphaFactory" / "tools" / "research" / "dsr.py"
CLOCK_PATH = ROOT.parents[1] / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
STAGE0_LEDGER_PATH = ROOT / "research" / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_eligibility_ledger.jsonl"


def load_tool():
    spec = importlib.util.spec_from_file_location("evaluate_trendstack_002_design", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_builder():
    spec = importlib.util.spec_from_file_location("test_build_trendstack_002_design_request_plan", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def bars(entry: float = 1.1000) -> list[dict[str, object]]:
    start = datetime(2016, 1, 4, 12, 1, tzinfo=timezone.utc)
    result = []
    for index in range(360):
        price = entry + index * 0.000001
        result.append(
            {
                "time_utc": (start + timedelta(minutes=index)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "bid_open": price,
                "bid_high": price + 0.00005,
                "bid_low": price - 0.00005,
                "bid_close": price,
            }
        )
    return result


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def valid_run_packet(tool, output_root: Path, **overrides) -> dict[str, object]:
    packet = {
        "schema_version": "trendstack_002_design_run_packet.v1",
        "hypothesis_id": tool.HYPOTHESIS_ID,
        "verdict": "FROZEN_DESIGN_M1_PROXY_ONE_RUN_AUTHORIZED",
        "source_plan_sha256": tool.SOURCE_PLAN_SHA256,
        "design_plan_sha256": tool.DESIGN_PLAN_SHA256,
        "design_plan_v2_path": tool.DESIGN_PLAN_V2_RELATIVE_PATH,
        "design_plan_v2_sha256": tool.DESIGN_PLAN_V2_SHA256,
        "design_date_set_sha256": tool.DESIGN_DATE_SET_SHA256,
        "stage0_eligibility_ledger_sha256": tool.STAGE0_LEDGER_SHA256,
        "stage0_receipt_sha256": tool.STAGE0_RECEIPT_SHA256,
        "stage0_access_trace_sha256": tool.STAGE0_ACCESS_TRACE_SHA256,
        "stage0_reconciliation_sha256": tool.STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": tool.PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": tool.PACKET_RECEIPT_SHA256,
        "decision_packet_set_sha256": tool.PACKET_SET_SHA256,
        "request_plan_sha256": "1" * 64,
        "request_plan_receipt_sha256": "2" * 64,
        "request_count": 1297,
        "expected_m1_rows": 466_920,
        "first_design_date": "2016-01-04",
        "last_design_date": "2020-12-31",
        "request_plan_builder_sha256": "3" * 64,
        "acquisition_tool_sha256": "4" * 64,
        "evaluator_tool_sha256": sha256(TOOL_PATH.read_bytes()),
        "clock_tool_sha256": sha256(CLOCK_PATH.read_bytes()),
        "dsr_tool_sha256": sha256(DSR_PATH.read_bytes()),
        "design_m1_output_root": str(output_root.resolve()),
        "design_m1_authorized": True,
        "validation_m1_authorized": False,
        "holdout_authorized": False,
        "model0_authorized": False,
        "promotion_authorized": False,
    }
    packet.update(overrides)
    return packet


def accepted_dates() -> list[str]:
    return [
        row["opportunity_id"]
        for row in (json.loads(line) for line in STAGE0_LEDGER_PATH.read_text(encoding="utf-8").splitlines())
        if row["split"] == "DESIGN"
    ]


def wrong_interior_dates() -> list[str]:
    accepted = accepted_dates()
    accepted_set = set(accepted)
    cursor = date(2016, 1, 4)
    absent = []
    while cursor <= date(2020, 12, 31):
        value = cursor.isoformat()
        if value not in accepted_set and value not in {accepted[0], accepted[-1]}:
            absent.append(value)
        cursor += timedelta(days=1)
    wrong = sorted((accepted_set - set(accepted[1:375])) | set(absent[:374]))
    assert len(wrong) == 1297 and len(set(wrong) - accepted_set) == 374
    return wrong


def write_run_packet(path: Path, packet: dict[str, object], *, canonical_bytes: bool = True) -> str:
    payload = canonical(packet) + b"\n"
    if not canonical_bytes:
        payload = json.dumps(packet, indent=2).encode("utf-8") + b"\n"
    path.write_bytes(payload)
    return sha256(payload)


def write_m1_shard(path: Path, day: str, request_id: str = "M1-DESIGN-0001-20160104") -> str:
    start = datetime.fromisoformat(day).replace(hour=12, minute=1, tzinfo=timezone.utc)
    records = []
    for index in range(360):
        moment = start + timedelta(minutes=index)
        price = 1.1 + index * 0.000001
        records.append(
            {
                "request_id": request_id,
                "opportunity_id": day,
                "time_server": (moment + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                "time_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "utc_offset_h": 2,
                "bid_open": price,
                "bid_high": price + 0.00005,
                "bid_low": price - 0.00005,
                "bid_close": price,
                "tick_volume": 10,
                "spread_points": 12,
                "real_volume": 0,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(records), path, row_group_size=360)
    return sha256(path.read_bytes())


def valid_runtime_provenance(tool, packet: dict[str, object], run_packet_sha: str) -> dict[str, object]:
    return {
        "terminal_executable_label": "terminal64.exe",
        "terminal_executable_sha256": "A" * 64,
        "python_executable_label": "python.exe",
        "python_executable_sha256": "B" * 64,
        "metatrader5_version": "5.test",
        "metatrader5_native_module_label": "_core.pyd",
        "metatrader5_native_module_sha256": "C" * 64,
        "clock_tool_label": "fivepercent_server_clock.py",
        "clock_tool_sha256": packet["clock_tool_sha256"],
        "acquisition_tool_label": "acquire_trendstack_002_design_m1.py",
        "acquisition_tool_sha256": packet["acquisition_tool_sha256"],
        "source_plan_sha256": tool.SOURCE_PLAN_SHA256,
        "design_plan_sha256": tool.DESIGN_PLAN_SHA256,
        "run_packet_sha256": run_packet_sha,
        "pandas_version": "2.test",
        "pyarrow_version": "20.test",
        "account_guard": {
            "terminal_build": 9999,
            "terminal_trade_allowed": False,
            "terminal_connected": True,
            "account_mode": "DEMO",
            "server": "FivePercentOnline-Real",
            "company": "Five Percent Online Ltd",
            "symbol": "EURUSD",
            "symbol_digits": 5,
            "symbol_point": 0.00001,
            "symbol_selected": True,
            "symbol_visible": True,
        },
    }


def valid_m1_receipt(tool, packet: dict[str, object], run_packet_sha: str) -> dict[str, object]:
    return {
        "schema_version": tool.M1_RECEIPT_SCHEMA,
        "hypothesis_id": tool.HYPOTHESIS_ID,
        "source_plan_sha256": tool.SOURCE_PLAN_SHA256,
        "design_plan_sha256": tool.DESIGN_PLAN_SHA256,
        "request_plan_sha256": packet["request_plan_sha256"],
        "request_plan_receipt_sha256": packet["request_plan_receipt_sha256"],
        "run_packet_sha256": run_packet_sha,
        "design_m1_manifest_sha256": "D" * 64,
        "request_count": 1297,
        "shard_file_count": 1297,
        "m1_rows": 466_920,
        "first_design_date": "2016-01-04",
        "last_design_date": "2020-12-31",
        "runtime_provenance": valid_runtime_provenance(tool, packet, run_packet_sha),
        "all_shard_hashes_verified": True,
        "design_m1_opened": True,
        "validation_m1_opened": False,
        "holdout_opened": False,
        "economics_computed": False,
        "physical_partition_status": "PASS",
        "verdict": "DESIGN_M1_SOURCE_READY_FOR_OFFLINE_EVALUATION",
    }


@pytest.mark.parametrize(
    ("direction", "case", "expected_reason", "expected_exit"),
    [
        (1, "entry-touch", "STOP_TOUCH_ENTRY", 1.0990),
        (-1, "entry-touch", "STOP_TOUCH_ENTRY", 1.1010),
        (1, "later-gap", "STOP_GAP", 1.0988),
        (-1, "later-gap", "STOP_GAP", 1.1012),
        (1, "later-touch", "STOP_TOUCH", 1.0990),
        (-1, "later-touch", "STOP_TOUCH", 1.1010),
        (1, "time-exit", "TIME_EXIT_1800", 1.0985),
        (-1, "time-exit", "TIME_EXIT_1800", 1.1015),
    ],
)
def test_every_long_short_exit_case(direction, case, expected_reason, expected_exit) -> None:
    tool = load_tool()
    frame = bars()
    stop = 1.0990 if direction == 1 else 1.1010
    if case == "entry-touch":
        frame[0]["bid_low" if direction == 1 else "bid_high"] = stop
    elif case == "later-gap":
        frame[10]["bid_open"] = 1.0988 if direction == 1 else 1.1012
        frame[10]["bid_low"] = min(float(frame[10]["bid_low"]), float(frame[10]["bid_open"]))
        frame[10]["bid_high"] = max(float(frame[10]["bid_high"]), float(frame[10]["bid_open"]))
    elif case == "later-touch":
        frame[10]["bid_low" if direction == 1 else "bid_high"] = stop
    else:
        frame[-1]["bid_open"] = expected_exit
        frame[-1]["bid_low"] = stop - 0.0100
        frame[-1]["bid_high"] = stop + 0.0100
    result = tool.simulate_trade(frame, direction=direction, atr20=0.0010)
    assert result["exit_reason"] == expected_reason
    assert result["exit_bid"] == pytest.approx(expected_exit)
    if case == "time-exit":
        assert result["exit_time_utc"].endswith("18:00:00Z")


def test_cost_arithmetic_and_profit_factor_statuses() -> None:
    tool = load_tool()
    assert tool.apply_cost(0.50, atr20=0.0010, round_trip_cost_pips=1.50) == pytest.approx(0.35)
    finite = tool.profit_factor([1.0, -0.5, 0.5])
    assert finite == {"status": "FINITE", "value": 3.0}
    assert tool.profit_factor([1.0, 0.0]) == {"status": "NO_LOSS", "value": None}
    assert tool.profit_factor([0.0, 0.0]) == {"status": "NO_WIN_NO_LOSS", "value": None}
    with pytest.raises(ValueError):
        tool.canonical_json_bytes({"bad": math.nan})


def test_evaluator_requires_strict_canonical_run_packet_and_no_caller_hash_authority(tmp_path: Path) -> None:
    tool = load_tool()
    signature = inspect.signature(tool.evaluate_design)
    assert "run_packet_path" in signature.parameters
    assert "expected_request_plan_sha256" not in signature.parameters
    assert "expected_m1_receipt_sha256" not in signature.parameters
    packet = valid_run_packet(tool, tmp_path / "m1")
    packet_path = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    expected_sha = write_run_packet(packet_path, packet)
    observed, observed_sha = tool.read_run_packet(packet_path)
    assert observed == packet and observed_sha == expected_sha
    extra = tmp_path / "extra.json"
    write_run_packet(extra, {**packet, "extra": True})
    with pytest.raises(tool.InvalidEngineering):
        tool.read_run_packet(extra)
    unauthorized = tmp_path / "unauthorized.json"
    write_run_packet(unauthorized, {**packet, "verdict": "KILL"})
    with pytest.raises(tool.InvalidEngineering):
        tool.read_run_packet(unauthorized)


def test_self_consistent_wrong_interior_date_set_stops_before_m1_or_economics(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    builder = load_builder()
    wrong_rows = builder.build_request_rows(wrong_interior_dates(), builder.load_clock(CLOCK_PATH))
    m1_root = tmp_path / "m1"
    m1_root.mkdir()
    request_plan = m1_root / "design_request_plan.jsonl"
    plan_payload = b"".join(canonical(row) + b"\n" for row in wrong_rows)
    request_plan.write_bytes(plan_payload)
    request_receipt = m1_root / "design_request_plan_receipt.json"
    request_receipt.write_bytes(b"{}\n")
    packet = valid_run_packet(tool, m1_root, request_plan_sha256=sha256(plan_payload))
    run_packet = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    run_packet.write_bytes(canonical(packet) + b"\n")
    monkeypatch.setattr(tool, "read_run_packet", lambda _: (packet, sha256(run_packet.read_bytes())))
    monkeypatch.setattr(tool, "_verify_authority_files", lambda *args, **kwargs: None)
    monkeypatch.setattr(tool, "read_request_receipt", lambda *args, **kwargs: {})
    touched = {"m1": 0, "economics": 0}

    def forbidden_m1(*args, **kwargs):
        touched["m1"] += 1
        raise AssertionError("M1 must remain unopened")

    def forbidden_economics(*args, **kwargs):
        touched["economics"] += 1
        raise AssertionError("economics must remain unopened")

    monkeypatch.setattr(tool, "_load_frozen_inputs", forbidden_m1)
    monkeypatch.setattr(tool, "_economic_result", forbidden_economics)
    output = tmp_path / "evaluation"
    monkeypatch.setattr(tool, "DEFAULT_EVALUATION_ROOT", output)
    with pytest.raises(tool.InvalidEngineering, match="date-set"):
        tool.evaluate_design(
            run_packet_path=run_packet,
            stage0_ledger_path=tool.DEFAULT_STAGE0_ROOT / "stage0_eligibility_ledger.jsonl",
            stage0_receipt_path=tool.DEFAULT_STAGE0_ROOT / "stage0_receipt.json",
            decision_packet_root=tool.DEFAULT_DECISION_PACKET_ROOT,
            request_plan_path=request_plan,
            request_receipt_path=request_receipt,
            m1_root=m1_root,
            output_root=output,
            dsr_path=DSR_PATH,
        )
    assert touched == {"m1": 0, "economics": 0}


@pytest.mark.parametrize("bad_day", ["2021-01-04", "2023-01-04"])
def test_shard_loader_rejects_validation_holdout_or_cross_day_grid_even_when_self_hashed(tmp_path: Path, bad_day: str) -> None:
    tool = load_tool()
    shard = tmp_path / "1201_1800.parquet"
    shard_sha = write_m1_shard(shard, bad_day)
    request = {"opportunity_id": "2016-01-04", "request_id": "M1-DESIGN-0001-20160104"}
    with pytest.raises(tool.InvalidEngineering):
        tool._read_day_from_shard(shard, shard_sha, expected_day="2016-01-04", expected_request=request)


def test_shard_loader_rejects_request_identity_mismatch_and_accepts_exact_design_day(tmp_path: Path) -> None:
    tool = load_tool()
    shard = tmp_path / "1201_1800.parquet"
    shard_sha = write_m1_shard(shard, "2016-01-04")
    bad_request = {"opportunity_id": "2016-01-04", "request_id": "M1-DESIGN-0002-20160104"}
    with pytest.raises(tool.InvalidEngineering):
        tool._read_day_from_shard(shard, shard_sha, expected_day="2016-01-04", expected_request=bad_request)
    good_request = {"opportunity_id": "2016-01-04", "request_id": "M1-DESIGN-0001-20160104"}
    loaded = tool._read_day_from_shard(shard, shard_sha, expected_day="2016-01-04", expected_request=good_request)
    assert len(loaded) == 360
    assert all(row["time_utc"].startswith("2016-01-04T") for row in loaded)


def test_evaluator_rejects_fake_or_extra_m1_receipt_and_manifest_provenance(tmp_path: Path) -> None:
    tool = load_tool()
    m1_root = tmp_path / "m1"
    m1_root.mkdir()
    run_packet_sha = "E" * 64
    packet = valid_run_packet(tool, m1_root, acquisition_tool_sha256="F" * 64)
    receipt = valid_m1_receipt(tool, packet, run_packet_sha)
    receipt_path = m1_root / "design_m1_source_receipt.json"
    receipt_path.write_bytes(canonical(receipt) + b"\n")
    observed, _, runtime_hashes = tool._read_m1_receipt(m1_root, packet, run_packet_sha)
    assert observed == receipt
    assert runtime_hashes["run_packet_sha256"] == run_packet_sha

    receipt_path.write_bytes(canonical({**receipt, "extra": "forbidden"}) + b"\n")
    with pytest.raises(tool.InvalidEngineering, match="schema"):
        tool._read_m1_receipt(m1_root, packet, run_packet_sha)
    receipt_path.write_bytes(canonical(receipt) + b"\n")
    fake_packet = {**packet, "acquisition_tool_sha256": "0" * 64}
    with pytest.raises(tool.InvalidEngineering, match="acquisition_tool_sha256"):
        tool._read_m1_receipt(m1_root, fake_packet, run_packet_sha)

    request = {"opportunity_id": "2016-01-04", "request_id": "M1-DESIGN-0001-20160104"}
    manifest_row = {
        "schema_version": tool.M1_MANIFEST_SCHEMA,
        "hypothesis_id": tool.HYPOTHESIS_ID,
        "request_id": request["request_id"],
        "opportunity_id": request["opportunity_id"],
        "split": "DESIGN",
        "shard_path": "raw_m1/DESIGN/2016-01-04/1201_1800.parquet",
        "rows": 360,
        "row_groups": 1,
        "first_utc_time": "2016-01-04T12:01:00Z",
        "last_utc_time": "2016-01-04T18:00:00Z",
        "canonical_row_content_sha256": "1" * 64,
        "shard_sha256": "2" * 64,
        "shard_bytes": 123,
        "geometry_status": "PASS",
        "unique_chronological_grid_status": "PASS",
        "holdout_rows_received": 0,
        "request_plan_sha256": packet["request_plan_sha256"],
        "request_plan_receipt_sha256": packet["request_plan_receipt_sha256"],
        "run_packet_sha256": run_packet_sha,
        "source_plan_sha256": tool.SOURCE_PLAN_SHA256,
        "design_plan_sha256": tool.DESIGN_PLAN_SHA256,
        "runtime_hashes": runtime_hashes,
    }
    tool._validate_manifest_row(manifest_row, request, runtime_hashes, packet, run_packet_sha)
    with pytest.raises(tool.InvalidEngineering, match="schema"):
        tool._validate_manifest_row({**manifest_row, "extra": True}, request, runtime_hashes, packet, run_packet_sha)
    with pytest.raises(tool.InvalidEngineering, match="run_packet_sha256"):
        tool._validate_manifest_row({**manifest_row, "run_packet_sha256": "0" * 64}, request, runtime_hashes, packet, run_packet_sha)


@pytest.mark.parametrize("extra_relative", ["raw_m1/VALIDATION", "raw_m1/DESIGN/2021-01-04", "raw_m1/HOLDOUT/2023-01-04"])
def test_physical_m1_tree_rejects_empty_validation_holdout_or_2021_directories(tmp_path: Path, extra_relative: str) -> None:
    tool = load_tool()
    root = tmp_path / "m1"
    shard = root / "raw_m1" / "DESIGN" / "2016-01-04" / "1201_1800.parquet"
    write_m1_shard(shard, "2016-01-04")
    expected = ["raw_m1/DESIGN/2016-01-04/1201_1800.parquet"]
    tool._validate_physical_shard_tree(root, expected)
    (root / Path(*PurePosixPath(extra_relative).parts)).mkdir(parents=True)
    with pytest.raises(tool.InvalidEngineering, match="directory set"):
        tool._validate_physical_shard_tree(root, expected)


def passing_gate_values() -> dict[str, object]:
    return {
        "cadence": 2.0,
        "pf_1_50": {"status": "FINITE", "value": 1.3000001},
        "pf_2_25": {"status": "FINITE", "value": 1.25},
        "pf_3_00": {"status": "FINITE", "value": 1.00},
        "mean_net_r_1_50": 0.08,
        "total_net_r_1_50": 0.000001,
        "positive_years": 4,
        "dsr_1_50": 0.95,
        "stack_pf_delta_vs_best_standalone": 0.15,
        "stack_mean_delta_vs_best_standalone": 0.05,
        "stack_pf_delta_vs_disagree": 0.15,
        "stack_mean_delta_vs_disagree": 0.05,
    }


def test_all_twelve_gate_boundaries_are_strict_or_inclusive_as_frozen() -> None:
    tool = load_tool()
    baseline = passing_gate_values()
    result = tool.evaluate_gate_values(baseline)
    assert result["all_pass"] is True
    assert len(result["gates"]) == 12

    failures = {
        "cadence": 1.999999,
        "pf_1_50": {"status": "FINITE", "value": 1.30},
        "pf_2_25": {"status": "FINITE", "value": 1.249999},
        "pf_3_00": {"status": "FINITE", "value": 0.999999},
        "mean_net_r_1_50": 0.079999,
        "total_net_r_1_50": 0.0,
        "positive_years": 3,
        "dsr_1_50": 0.949999,
        "stack_pf_delta_vs_best_standalone": 0.149999,
        "stack_mean_delta_vs_best_standalone": 0.049999,
        "stack_pf_delta_vs_disagree": 0.149999,
        "stack_mean_delta_vs_disagree": 0.049999,
    }
    for field, failing_value in failures.items():
        candidate = dict(baseline)
        candidate[field] = failing_value
        assert tool.evaluate_gate_values(candidate)["all_pass"] is False, field
    high_cadence = dict(baseline)
    high_cadence["cadence"] = 5.0
    assert tool.evaluate_gate_values(high_cadence)["all_pass"] is True
    high_cadence["cadence"] = 5.000001
    assert tool.evaluate_gate_values(high_cadence)["all_pass"] is False


def test_exact_arm_expansion_freezes_stage0_directions_and_packet_atr() -> None:
    tool = load_tool()
    stage = {
        "opportunity_id": "2016-01-04",
        "split": "DESIGN",
        "packet_file_sha256": "A" * 64,
        "control_m252_only_eligible": True,
        "control_m252_only_direction": 1,
        "control_m6_only_eligible": True,
        "control_m6_only_direction": -1,
        "challenger_stack_eligible": False,
        "challenger_stack_direction": None,
        "negative_disagree_eligible": True,
        "negative_disagree_direction": -1,
    }
    packet = {
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-002",
        "opportunity_id": "2016-01-04",
        "split": "DESIGN",
        "atr20": 0.0012,
        "packet_file_sha256": "A" * 64,
    }
    expanded = tool.expand_arms(stage, packet)
    assert [(row["arm"], row["direction"]) for row in expanded] == [
        ("CONTROL_M252_ONLY", 1),
        ("CONTROL_M6_ONLY", -1),
        ("NEGATIVE_DISAGREE", -1),
    ]
    assert all(row["atr20"] == 0.0012 for row in expanded)
    stage["control_m252_only_direction"] = True
    with pytest.raises(tool.InvalidEngineering):
        tool.expand_arms(stage, packet)


def test_arm_count_contract_is_exact() -> None:
    tool = load_tool()
    counts = {
        "CONTROL_M252_ONLY": 1297,
        "CONTROL_M6_ONLY": 1292,
        "CHALLENGER_STACK": 661,
        "NEGATIVE_DISAGREE": 631,
    }
    tool.validate_arm_counts(counts)
    with pytest.raises(tool.InvalidEngineering):
        tool.validate_arm_counts({**counts, "CHALLENGER_STACK": 660})


def test_dsr_uses_sample_variance_and_exactly_four_trials() -> None:
    tool = load_tool()
    returns = {
        "CONTROL_M252_ONLY": [0.2, -0.1, 0.3, 0.1, -0.05],
        "CONTROL_M6_ONLY": [0.1, -0.2, 0.4, 0.2, -0.1],
        "CHALLENGER_STACK": [0.4, -0.1, 0.5, 0.3, -0.05],
        "NEGATIVE_DISAGREE": [-0.2, 0.1, -0.3, 0.05, -0.1],
    }
    result = tool.compute_dsr(returns, DSR_PATH)
    assert result["n_trials"] == 4
    assert result["var_sr_trials"] == pytest.approx(statistics.variance(result["arm_sharpes"].values()))
    assert 0.0 <= result["dsr"] <= 1.0
    assert result["dsr_tool_sha256"] == sha256(DSR_PATH.read_bytes())
    with pytest.raises(tool.InvalidEngineering):
        tool.compute_dsr({key: value for key, value in list(returns.items())[:3]}, DSR_PATH)


def test_common_daily_book_has_exactly_1824_days_and_explicit_zero_days() -> None:
    tool = load_tool()
    trades = [
        {
            "opportunity_id": "2016-01-04",
            "arm": "CHALLENGER_STACK",
            "net_R_1_50": 0.5,
            "net_R_2_25": 0.4,
            "net_R_3_00": 0.3,
        }
    ]
    book = tool.build_daily_book(trades)
    assert len(book) == 1824
    assert book[0]["date_utc"] == "2016-01-04"
    assert book[-1]["date_utc"] == "2020-12-31"
    assert book[0]["CHALLENGER_STACK_net_R_1_50"] == 0.5
    assert book[1]["CHALLENGER_STACK_net_R_1_50"] == 0.0


def test_invalid_inputs_create_no_economic_verdict(tmp_path: Path) -> None:
    tool = load_tool()
    output = tmp_path / "economic"
    with pytest.raises(tool.InvalidEngineering):
        tool.evaluate_design(
            run_packet_path=tmp_path / "missing-run-packet.json",
            stage0_ledger_path=tmp_path / "missing-ledger.jsonl",
            stage0_receipt_path=tmp_path / "missing-receipt.json",
            decision_packet_root=tmp_path / "missing-packets",
            request_plan_path=tmp_path / "missing-plan.jsonl",
            request_receipt_path=tmp_path / "missing-plan-receipt.json",
            m1_root=tmp_path / "missing-m1",
            output_root=output,
            dsr_path=DSR_PATH,
        )
    assert not (output / "design_economic_result.json").exists()


def test_evaluator_source_is_offline_and_has_no_raw_h1_or_decision_recomputation() -> None:
    source = TOOL_PATH.read_text(encoding="utf-8")
    forbidden = ("MetaTrader5", "copy_rates_range", "requests", "urllib", "socket", "raw_h1", "m252(", "m6(")
    assert not any(token in source for token in forbidden)


def test_create_new_evaluation_outputs_are_deterministic_and_false_validation(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    monkeypatch.setattr(tool, "EXPECTED_TOTAL_ARM_ROWS", 1)
    trade_rows = [{"opportunity_id": "2016-01-04", "arm": "CHALLENGER_STACK", "net_R_1_50": 0.5}]
    daily = tool.build_daily_book(
        [{**trade_rows[0], "net_R_2_25": 0.4, "net_R_3_00": 0.3}]
    )
    result = {
        "schema_version": "trendstack_002_design_economic_result.v1",
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-002",
        "engineering_status": "PASS",
        "verdict": "KILL",
        "trial_count": 4,
    }
    evaluator_sha = sha256(TOOL_PATH.read_bytes())
    upstream = {field: "A" * 64 for field in tool.EVALUATION_UPSTREAM_FIELDS}
    upstream["evaluator_tool_sha256"] = evaluator_sha
    upstream["run_packet_sha256"] = "B" * 64
    first = tool.persist_evaluation(tmp_path / "a", trade_rows, daily, result, upstream, evaluator_sha)
    second = tool.persist_evaluation(tmp_path / "b", trade_rows, daily, result, upstream, evaluator_sha)
    assert first == second
    for name in (
        "design_trade_ledger.jsonl",
        "design_daily_book.jsonl",
        "design_economic_result.json",
        "design_evaluation_receipt.json",
    ):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert first["validation_m1_opened"] is False
    assert first["holdout_opened"] is False
    assert first["run_packet_sha256"] == "B" * 64
    with pytest.raises((tool.InvalidEngineering, FileExistsError)):
        tool.persist_evaluation(tmp_path / "a", trade_rows, daily, result, upstream, evaluator_sha)


def test_evaluator_rejects_hardlinked_input(tmp_path: Path) -> None:
    tool = load_tool()
    source = tmp_path / "input.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    linked = tmp_path / "linked.jsonl"
    os.link(source, linked)
    with pytest.raises(tool.InvalidEngineering):
        tool.read_stable_file(source)
