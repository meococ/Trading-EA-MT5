from __future__ import annotations

import ast
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR))

import evaluate_round_cascade_009_design_economics as sut


UTC = timezone.utc


def producer_schema(*, time_utc_type=None, metadata=None, extra_field: bool = False):
    import pyarrow as pa

    fields = [
        ("time_server", pa.timestamp("ns")),
        ("time_utc", time_utc_type or pa.timestamp("ns")),
        ("utc_offset_h", pa.int8()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("tick_volume", pa.uint64()),
        ("spread", pa.int32()),
        ("real_volume", pa.uint64()),
    ]
    if extra_field:
        fields.append(("unexpected", pa.int8()))
    return pa.schema(fields, metadata=metadata)


def parquet_payload(rows: list[dict], *, schema=None, row_group_size: int | None = None) -> bytes:
    import pyarrow as pa
    import pyarrow.parquet as pq

    selected_schema = schema or producer_schema()
    table = pa.Table.from_pylist(rows, schema=selected_schema)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, row_group_size=row_group_size)
    return sink.getvalue().to_pybytes()


def manifest_entry(payload: bytes, rows: int, *, date_text: str = "2016-01-05") -> dict:
    return {
        "date": date_text,
        "relative_path": f"public/DESIGN/{date_text}/m1.parquet",
        "sha256": sut.sha256_bytes(payload),
        "bytes": len(payload),
        "rows": rows,
    }


def producer_row(
    at: datetime,
    *,
    tz_aware: bool = False,
    extra_field: bool = False,
    open_: float = 1.1000,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
) -> dict:
    stored = at.replace(tzinfo=UTC) if tz_aware else at.replace(tzinfo=None)
    row = {
        "time_server": stored,
        "time_utc": stored,
        "utc_offset_h": 0,
        "open": open_,
        "high": open_ if high is None else high,
        "low": open_ if low is None else low,
        "close": open_ if close is None else close,
        "tick_volume": 1,
        "spread": 1,
        "real_volume": 0,
    }
    if extra_field:
        row["unexpected"] = 1
    return row


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
        "hypothesis_id": sut.SOURCE_SIGNAL_HYPOTHESIS_ID,
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
        entry_time_utc=at,
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


def detail_and_eligible(at: datetime, *, arm: str = "TRUE_0050") -> tuple[dict, dict, str]:
    detail = signal(at, arm=arm)
    raw = sut.canonical_json_bytes(detail)
    lf_hash = sut.lf_row_sha256(raw)
    eligible = {
        "arm": arm,
        "complete_m5_starts": 12,
        "planned_entry_time_utc": iso(at),
        "reserved_exit_time_utc": iso(at + timedelta(minutes=60)),
        "source_identity": f"{arm}|{iso(at)}",
        "source_lf_row_sha256": lf_hash,
        "status": sut.ELIGIBLE_STATUS,
    }
    return detail, eligible, lf_hash


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


def hyp008_sealed_permissions() -> dict:
    return {
        "charting_authorized": False,
        "economics_authorized": False,
        "holdout_authorized": False,
        "live_trading_authorized": False,
        "model0_authorized": False,
        "model4_authorized": False,
        "mq5_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
        "network_authorized": False,
        "optimization_authorized": False,
        "outcome_prices_authorized": False,
        "paid_authorized": False,
        "paid_requests_authorized": False,
        "paper_trading_authorized": False,
        "performance_metrics_authorized": False,
        "post_entry_ohlc_authorized": False,
        "post_entry_price_projection_authorized": False,
        "private_custody_authorized": False,
        "promotion_authorized": False,
        "promotion_eligible": False,
        "registry_mutation_allowed": False,
        "research_holdout_access_authorized": False,
        "research_validation_access_authorized": False,
        "sealed_access_authorized": False,
        "source_build_authorized": False,
        "validation_authorized": False,
    }


def hyp008_source_only_counters() -> dict:
    return {
        "economics_executed": False,
        "model0_runs": 0,
        "model4_runs": 0,
        "mql5_files_created": 0,
        "mt5_launches": 0,
        "network_calls": 0,
        "outcome_fields_emitted": 0,
        "paid_requests_made": 0,
        "performance_trials_executed": 0,
        "post_entry_ohlc_rows_read": 0,
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "returns_computed": 0,
        "source_feasibility_attempts_consumed": 1,
        "source_runs_executed": 1,
        "trades_simulated": 0,
    }


def test_import_is_inert_and_workspace_root_is_required() -> None:
    assert sut.REVIEWED_RUN_PACKET_SHA256 is None
    assert sut.HYPOTHESIS_ID == "HYP-ROUND-CASCADE-EURUSD-M5-009"
    assert sut.PARENT_CANDIDATE == "HYP-ROUND-CASCADE-EURUSD-M5-008"
    assert sut.ATTEMPT_ID == "HYP009-DESIGN-ECON-001"
    assert sut.EXPECTED_SIGNAL_COUNTS == {"TRUE_0050": 1220, "SHIFTED_0025": 1214}
    assert sut.ELAPSED_WEEKS == 260.5714285714
    assert sut.COST_TIERS_PIPS == [1.50, 2.25, 3.00]
    assert sut.RISK_FRACTION == 0.0025
    assert sut.PLAN_REL.endswith("HYP-ROUND-CASCADE-EURUSD-M5-009_DESIGN_ECONOMICS_PLAN.md")
    assert sut.sha256_file(RESEARCH_DIR / Path(sut.PLAN_REL).name) == sut.FROZEN_PLAN_SHA256
    assert all(field in sut.FORBIDDEN_AUTHORITY_FIELDS for field in (
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "private_custody_authorized",
        "mql5_authorized",
        "mt5_authorized",
        "network_authorized",
        "paid_authorized",
        "promotion_authorized",
        "live_trading_authorized",
    ))
    assert sut.main([]) == 2
    assert sut.main(["--run-reviewed-design-economics"]) == 1


def test_module_ast_parses_and_sentinel_is_disarmed() -> None:
    source = Path(sut.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert isinstance(tree, ast.Module)
    assert "REVIEWED_RUN_PACKET_SHA256: str | None = None" in source
    assert sut.REVIEWED_RUN_PACKET_SHA256 is None
    assert sut.ELIGIBLE_LEDGER_SHA256 == "B84EF3925B5CC998A88D224BCF8B4A66D5A6076DFED87C4287325F369AAFF16B"
    assert sut.HYP008_REPORT_SHA256 == "5F74F6A33FA66D05D131D5727CC6CC31929C748A8B223A820986FD62CD180EEA"
    assert sut.HYP008_RECEIPT_SHA256 == "A06E602222E20C7B1800F3E92FFA51679A6DDB06D9DE81FC41CF737C9D0B8DF9"
    assert sut.HYP008_TERMINAL_SHA256 == "9EFA0811D46286A2B5FCBBADB814785BA5EC24EC83A90DC73CD998394EBD8E10"
    assert sut.SOURCE_LEDGER_SHA256 == "8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE"


def test_strict_json_rejects_malformed_duplicate_and_nonfinite() -> None:
    with pytest.raises(sut.EngineeringInvalid, match="invalid packet JSON"):
        sut.strict_json_loads(b"{", label="packet")
    with pytest.raises(sut.EngineeringInvalid, match="duplicate JSON key"):
        sut.strict_json_loads(b'{"a":1,"a":2}', label="packet")
    with pytest.raises(sut.EngineeringInvalid, match="non-finite JSON value"):
        sut.strict_json_loads(b'{"a":NaN}', label="packet")


def test_exact_entry_no_delay_or_next_bar_fallback() -> None:
    planned = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    exact = sut.build_observed_market_index(minute_window(planned))
    mapped = sut.map_signal_to_market(signal(planned), exact)
    assert mapped.entry_time_utc == planned
    assert mapped.exit_time_utc == planned + timedelta(minutes=60)
    assert mapped.reserved_exit_time_utc == planned + timedelta(minutes=60)

    delayed_start = planned + timedelta(minutes=5)
    delayed_market = sut.build_observed_market_index(minute_window(delayed_start))
    with pytest.raises(sut.EngineeringInvalid, match="no exact complete observed M5 entry"):
        sut.map_signal_to_market(signal(planned), delayed_market)

    # Incomplete entry bin is not an exact complete M5 start.
    incomplete = minute_window(planned)
    incomplete.pop(1)
    incomplete_market = sut.build_observed_market_index(incomplete)
    with pytest.raises(sut.EngineeringInvalid, match="no exact complete observed M5 entry"):
        sut.map_signal_to_market(signal(planned), incomplete_market)


def test_reserved_exit_equals_twelfth_start_plus_five_minutes() -> None:
    planned = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    market = sut.build_observed_market_index(minute_window(planned))
    reserved = planned + timedelta(minutes=60)
    mapped = sut.map_signal_to_market(signal(planned), market, reserved_exit_time_utc=reserved)
    assert mapped.exit_time_utc == reserved
    with pytest.raises(sut.EngineeringInvalid, match="reserved_exit_time_utc mismatch"):
        sut.map_signal_to_market(
            signal(planned),
            market,
            reserved_exit_time_utc=planned + timedelta(minutes=55),
        )


def test_right_censored_observed_horizon_is_rejected() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    eleven = sut.build_observed_market_index(minute_window(start)[:55])
    with pytest.raises(sut.EngineeringInvalid, match="right-censored observed M5 horizon"):
        sut.map_signal_to_market(signal(start), eleven)


def test_adverse_stop_precedence_and_time_exit_preserved() -> None:
    entry = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    rows = minute_window(entry, open_=1.1000, close=1.1015)
    timed = sut.simulate_signal(signal(entry, direction="LONG", atr20_pips=10.0), rows)
    assert timed.exit_reason == "TIME"
    assert timed.entry_time_utc == entry
    assert timed.gross_R == pytest.approx(1.5)

    stop_rows = [m1(entry + timedelta(minutes=i), open_=1.1000, high=1.1005, low=1.0989 if i == 2 else 1.0995, close=1.1000) for i in range(60)]
    stopped = sut.simulate_signal(signal(entry, direction="LONG", atr20_pips=10.0), stop_rows)
    assert stopped.exit_reason == "STOP"
    assert stopped.gross_R == pytest.approx(-1.0)


def test_fixed_eligible_population_counts_and_dsr_n_obs() -> None:
    assert sut.EXPECTED_SIGNAL_COUNTS == {"TRUE_0050": 1220, "SHIFTED_0025": 1214}
    exemplar = trade(datetime(2019, 1, 2, 10, 0, tzinfo=UTC), 0.1)
    exact = {
        "TRUE_0050": [exemplar] * 1220,
        "SHIFTED_0025": [exemplar] * 1214,
    }
    sut.validate_trade_counts(exact)
    with pytest.raises(sut.EngineeringInvalid, match="TRUE_0050 trade count 1219 != 1220"):
        sut.validate_trade_counts({**exact, "TRUE_0050": exact["TRUE_0050"][:-1]})
    assert sut.cadence_per_elapsed_week(1220) == pytest.approx(1220 / 260.5714285714)


def test_eleven_gates_and_verdict_meanings_are_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_dsr_tool(tmp_path, monkeypatch, value=0.96)
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE_0050": 5, "SHIFTED_0025": 5})
    # Build a population that passes all eleven gates under synthetic counts.
    true_trades = [
        trade(datetime(year, 1, 2, tzinfo=UTC), 2.0 if year < 2020 else 1.0)
        for year in sut.DESIGN_YEARS
    ]
    shifted_trades = [trade(datetime(year, 6, 2, tzinfo=UTC), 0.2, arm="SHIFTED_0025") for year in sut.DESIGN_YEARS]
    report = sut.evaluate_gates({"TRUE_0050": true_trades, "SHIFTED_0025": shifted_trades}, tmp_path)
    assert len(report["gates"]) == 11
    assert report["dsr"]["n_trials"] == 2
    assert report["dsr"]["n_obs"] == 5
    gate_names = [row["name"] for row in report["gates"]]
    assert gate_names == [
        "TRUE cadence",
        "TRUE PF at 1.50 pips",
        "TRUE PF at 2.25 pips",
        "TRUE PF at 3.00 pips",
        "TRUE mean net R at 1.50 pips",
        "TRUE total net R at 1.50 pips",
        "TRUE positive DESIGN years at 1.50 pips",
        "TRUE max compounding DD",
        "TRUE DSR at 1.50 pips",
        "TRUE PF minus SHIFTED PF",
        "TRUE mean net R minus SHIFTED mean net R",
    ]
    # Fail one gate -> KILL, not ENGINEERING_INVALID.
    loser = [
        trade(datetime(2016, 1, 2, tzinfo=UTC) + timedelta(hours=i * 2), -1.0)
        for i in range(5)
    ]
    kill = sut.evaluate_gates({"TRUE_0050": loser, "SHIFTED_0025": shifted_trades}, tmp_path)
    assert kill["status"] == "KILL_DESIGN_ECONOMICS_NO_EDGE"


def test_dsr_n_obs_uses_true_eligible_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_dsr_tool(tmp_path, monkeypatch, value=0.99)
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE_0050": 3, "SHIFTED_0025": 2})
    true_net = [0.2, 0.1, -0.05]
    shifted_net = [0.0, -0.1]
    report = sut.dsr_inputs_and_value(true_net, shifted_net, tmp_path)
    assert report["n_obs"] == 3
    assert report["n_trials"] == 2
    with pytest.raises(sut.EngineeringInvalid, match="TRUE DSR observation count mismatch"):
        sut.dsr_inputs_and_value(true_net[:-1], shifted_net, tmp_path)


def test_overlap_before_prior_exit_is_invalid_but_equality_is_allowed() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    sut.assert_no_overlap([trade(start, 0.1), trade(start + timedelta(minutes=60), 0.1)])
    with pytest.raises(sut.EngineeringInvalid, match="overlapping"):
        sut.assert_no_overlap([trade(start, 0.1), trade(start + timedelta(minutes=59), 0.1)])

    s1 = {"planned_entry_time_utc": start, "reserved_exit_time_utc": start + timedelta(minutes=60)}
    s2 = {"planned_entry_time_utc": start + timedelta(minutes=60), "reserved_exit_time_utc": start + timedelta(minutes=120)}
    sut.assert_reserved_nonoverlap([s1, s2])
    bad = {"planned_entry_time_utc": start + timedelta(minutes=59), "reserved_exit_time_utc": start + timedelta(minutes=119)}
    with pytest.raises(sut.EngineeringInvalid, match="overlapping eligible"):
        sut.assert_reserved_nonoverlap([s1, bad])


def test_exact_join_and_lf_hash_binding(tmp_path: Path) -> None:
    base_true = datetime(2016, 1, 4, 10, 0, tzinfo=UTC)
    base_shifted = datetime(2016, 1, 4, 12, 0, tzinfo=UTC)
    # Full detail counts for this synthetic world.
    details = [
        signal(base_true + timedelta(minutes=5 * i), arm="TRUE_0050")
        for i in range(1229)
    ] + [
        signal(base_shifted + timedelta(minutes=5 * i), arm="SHIFTED_0025")
        for i in range(1220)
    ]

    detail_path = tmp_path / "detail.jsonl"
    detail_sha = write_jsonl(detail_path, details)
    index = sut.load_hyp002_detail_index(detail_path, detail_sha)
    assert len(index) == 1229 + 1220

    eligible_seed = [details[0], details[1], details[1229]]
    eligible_rows = []
    for row in eligible_seed:
        raw = sut.canonical_json_bytes(row)
        lf_hash = sut.lf_row_sha256(raw)
        planned = sut.parse_utc(row["planned_entry_time_utc"])
        eligible_rows.append({
            "arm": row["arm"],
            "complete_m5_starts": 12,
            "planned_entry_time_utc": row["planned_entry_time_utc"],
            "reserved_exit_time_utc": iso(planned + timedelta(minutes=60)),
            "source_identity": f"{row['arm']}|{row['planned_entry_time_utc']}",
            "source_lf_row_sha256": lf_hash,
            "status": sut.ELIGIBLE_STATUS,
        })

    # Temporarily shrink expected eligible counts for the join unit test.
    old = sut.EXPECTED_SIGNAL_COUNTS
    try:
        sut.EXPECTED_SIGNAL_COUNTS = {"TRUE_0050": 2, "SHIFTED_0025": 1}
        eligible_path = tmp_path / "eligible.jsonl"
        eligible_sha = write_jsonl(eligible_path, eligible_rows)
        joined = sut.load_and_join_eligible_signals(eligible_path, eligible_sha, index)
        assert {arm: len(rows) for arm, rows in joined.items()} == {"TRUE_0050": 2, "SHIFTED_0025": 1}
        assert joined["TRUE_0050"][0]["direction"] in {"LONG", "SHORT"}
        assert joined["TRUE_0050"][0]["source_lf_row_sha256"] == eligible_rows[0]["source_lf_row_sha256"]

        # Missing join.
        bad = list(eligible_rows)
        bad[0] = {**bad[0], "source_lf_row_sha256": "A" * 64}
        bad_path = tmp_path / "eligible_missing.jsonl"
        bad_sha = write_jsonl(bad_path, bad)
        with pytest.raises(sut.EngineeringInvalid, match="missing HYP002 detail join"):
            sut.load_and_join_eligible_signals(bad_path, bad_sha, index)

        # Duplicate eligible identity.
        dup = eligible_rows + [eligible_rows[0]]
        dup_path = tmp_path / "eligible_dup.jsonl"
        # Adjust expected so length check is not first failure path for SHIFTED.
        sut.EXPECTED_SIGNAL_COUNTS = {"TRUE_0050": 3, "SHIFTED_0025": 1}
        dup_sha = write_jsonl(dup_path, dup)
        with pytest.raises(sut.EngineeringInvalid, match="duplicate eligible identity"):
            sut.load_and_join_eligible_signals(dup_path, dup_sha, index)
    finally:
        sut.EXPECTED_SIGNAL_COUNTS = old


def test_hyp008_chain_binding_before_price(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sut, "ELIGIBLE_LEDGER_REL", "hyp008/eligible.jsonl")
    monkeypatch.setattr(sut, "HYP008_REPORT_REL", "hyp008/report.json")
    monkeypatch.setattr(sut, "HYP008_RECEIPT_REL", "hyp008/receipt.json")
    monkeypatch.setattr(sut, "HYP008_TERMINAL_REL", "hyp008/terminal.json")

    eligible_sha = write_jsonl(tmp_path / "hyp008/eligible.jsonl", [])
    monkeypatch.setattr(sut, "ELIGIBLE_LEDGER_SHA256", eligible_sha)

    report = {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP008_ATTEMPT_ID,
        "verdict": sut.HYP008_PASS_STATUS,
        "hyp009_drafting_authorized": True,
        "classification_sha256": sut.HYP008_CLASSIFICATION_SHA256,
        "actual_counts": {
            sut.ELIGIBLE_STATUS: {"TRUE_0050": 1220, "SHIFTED_0025": 1214},
        },
        "source_only_counters": hyp008_source_only_counters(),
        "sealed_permissions": hyp008_sealed_permissions(),
    }
    report_sha = write_json(tmp_path / "hyp008/report.json", report)
    monkeypatch.setattr(sut, "HYP008_REPORT_SHA256", report_sha)

    receipt = {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP008_ATTEMPT_ID,
        "verdict": sut.HYP008_PASS_STATUS,
        "hyp009_drafting_authorized": True,
        "classification_sha256": sut.HYP008_CLASSIFICATION_SHA256,
        "artifact_sha256": {
            "attempt_started.json": sut.HYP008_STARTED_SHA256,
            "round_cascade_008_eligible_source_ledger.jsonl": eligible_sha,
            "round_cascade_008_execution_source_report.json": report_sha,
            "round_cascade_008_ineligible_source_ledger.jsonl": sut.HYP008_INELIGIBLE_LEDGER_SHA256,
        },
        "source_only_counters": hyp008_source_only_counters(),
        "sealed_permissions": hyp008_sealed_permissions(),
    }
    receipt_sha = write_json(tmp_path / "hyp008/receipt.json", receipt)
    monkeypatch.setattr(sut, "HYP008_RECEIPT_SHA256", receipt_sha)

    terminal = {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP008_ATTEMPT_ID,
        "status": sut.HYP008_PASS_STATUS,
        "hyp009_drafting_authorized": True,
        "classification_sha256": sut.HYP008_CLASSIFICATION_SHA256,
        "promotion_evidence": False,
        "artifact_sha256": {
            "attempt_started.json": sut.HYP008_STARTED_SHA256,
            "execution_source_receipt.json": receipt_sha,
            "round_cascade_008_eligible_source_ledger.jsonl": eligible_sha,
            "round_cascade_008_execution_source_report.json": report_sha,
            "round_cascade_008_ineligible_source_ledger.jsonl": sut.HYP008_INELIGIBLE_LEDGER_SHA256,
        },
        "source_only_counters": hyp008_source_only_counters(),
        "sealed_permissions": hyp008_sealed_permissions(),
    }
    terminal_sha = write_json(tmp_path / "hyp008/terminal.json", terminal)
    monkeypatch.setattr(sut, "HYP008_TERMINAL_SHA256", terminal_sha)

    packet = {
        "eligible_ledger_path": sut.ELIGIBLE_LEDGER_REL,
        "hyp008_report_path": sut.HYP008_REPORT_REL,
        "hyp008_receipt_path": sut.HYP008_RECEIPT_REL,
        "hyp008_terminal_path": sut.HYP008_TERMINAL_REL,
    }
    out = sut.validate_hyp008_chain_before_price(tmp_path, packet)
    assert out["eligible_ledger_sha256"] == eligible_sha
    assert out["hyp008_terminal_sha256"] == terminal_sha

    # Tamper report verdict.
    report["verdict"] = "KILL"
    write_json(tmp_path / "hyp008/report.json", report)
    # SHA no longer matches expected constant after rewrite without monkeypatch update.
    with pytest.raises(sut.EngineeringInvalid, match="SHA256 mismatch"):
        sut.validate_hyp008_chain_before_price(tmp_path, packet)


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


def test_parquet_boundary_rejects_schema_and_hardlink_escape(tmp_path: Path) -> None:
    import pyarrow as pa

    naive = datetime(2016, 1, 5, 0, 0)
    payload = parquet_payload([producer_row(naive)], schema=producer_schema(time_utc_type=pa.timestamp("ms")))
    with pytest.raises(sut.EngineeringInvalid, match="producer schema mismatch"):
        sut.decode_manifest_bound_public_design_parquet(
            tmp_path, manifest_entry(payload, 1), payload
        )
    with pytest.raises(sut.EngineeringInvalid, match="manifest-bound"):
        sut.read_m1_shard(payload, Path("missing.parquet"), label="parquet")


def test_one_use_authority_and_disarmed_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert sut.REVIEWED_RUN_PACKET_SHA256 is None
    packet = minimal_packet(tmp_path)
    with pytest.raises(sut.EngineeringInvalid, match="sentinel is not armed"):
        sut.validate_run_packet(packet, "A" * 64)
    monkeypatch.setattr(sut, "REVIEWED_RUN_PACKET_SHA256", "A" * 64)
    with pytest.raises(sut.EngineeringInvalid, match="reviewed sentinel"):
        sut.validate_run_packet(packet, "B" * 64)
    packet_extra = dict(packet)
    packet_extra["unexpected"] = True
    with pytest.raises(sut.EngineeringInvalid, match="schema keys mismatch"):
        sut.validate_run_packet(packet_extra, "A" * 64)
    packet_alias = dict(packet)
    packet_alias["research_validation_access_authorized"] = True
    packet_alias["review_receipt_sha256"] = "C" * 64
    with pytest.raises(sut.EngineeringInvalid, match="forbidden authority"):
        sut.validate_run_packet(packet_alias, "A" * 64)


def test_registry_tamper_is_fail_closed(tmp_path: Path) -> None:
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
            "attempt_limit": 1,
            "evaluator_path": sut.EVALUATOR_REL,
            "test_path": sut.TEST_REL,
            "run_packet_path": sut.RUN_PACKET_REL,
            "review_receipt_path": sut.REVIEW_RECEIPT_REL,
            "hyp008_terminal_path": sut.HYP008_TERMINAL_REL,
            "hyp008_terminal_sha256": sut.HYP008_TERMINAL_SHA256,
            "eligible_ledger_path": sut.ELIGIBLE_LEDGER_REL,
            "eligible_ledger_sha256": sut.ELIGIBLE_LEDGER_SHA256,
            "collection_plan_path": sut.COLLECTION_PLAN_REL,
            "collection_plan_sha256": sut.COLLECTION_PLAN_SHA256,
            "custodian_tool_path": sut.CUSTODIAN_TOOL_REL,
            "custodian_tool_sha256": sut.CUSTODIAN_TOOL_SHA256,
            "evaluator_base_sha256": "E" * 64,
            "test_sha256": "T" * 64,
            "review_receipt_sha256": "R" * 64,
            "economics_authorized": True,
            "post_entry_ohlc_authorized": True,
            "performance_metrics_authorized": True,
            "public_design_m1_authorized": True,
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


def test_sentinel_normalization_rejects_multiple_or_noncanonical_assignments() -> None:
    armed = b'REVIEWED_RUN_PACKET_SHA256: str | None = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"\n'
    assert sut.normalize_reviewer_bound_source(armed) == b"REVIEWED_RUN_PACKET_SHA256: str | None = None\n"
    with pytest.raises(sut.EngineeringInvalid, match="exactly once"):
        sut.normalize_reviewer_bound_source(armed + armed)


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
        "eligible_ledger_path": sut.ELIGIBLE_LEDGER_REL,
        "eligible_ledger_sha256": sut.ELIGIBLE_LEDGER_SHA256,
        "hyp008_report_path": sut.HYP008_REPORT_REL,
        "hyp008_report_sha256": sut.HYP008_REPORT_SHA256,
        "hyp008_receipt_path": sut.HYP008_RECEIPT_REL,
        "hyp008_receipt_sha256": sut.HYP008_RECEIPT_SHA256,
        "hyp008_terminal_path": sut.HYP008_TERMINAL_REL,
        "hyp008_terminal_sha256": sut.HYP008_TERMINAL_SHA256,
        "design_manifest_path": sut.DESIGN_MANIFEST_REL,
        "design_manifest_sha256": sut.DESIGN_MANIFEST_SHA256,
        "design_receipt_path": sut.DESIGN_RECEIPT_REL,
        "design_receipt_sha256": sut.DESIGN_RECEIPT_SHA256,
        "public_m1_source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        "collection_plan_path": sut.COLLECTION_PLAN_REL,
        "collection_plan_sha256": sut.COLLECTION_PLAN_SHA256,
        "custodian_tool_path": sut.CUSTODIAN_TOOL_REL,
        "custodian_tool_sha256": sut.CUSTODIAN_TOOL_SHA256,
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
        "review_receipt_sha256": "D" * 64,
        "economics_authorized": True,
        "post_entry_ohlc_authorized": True,
        "performance_metrics_authorized": True,
        "public_design_m1_authorized": True,
        "attempt_limit": 1,
        **{field: False for field in sut.FORBIDDEN_AUTHORITY_FIELDS},
    }


def setup_synthetic_workspace(root: Path, monkeypatch: pytest.MonkeyPatch, *, bad_after_start: bool = False) -> Path:
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE_0050": 2, "SHIFTED_0025": 2})
    monkeypatch.setattr(sut, "SOURCE_DETAIL_COUNTS", {"TRUE_0050": 2, "SHIFTED_0025": 2})
    monkeypatch.setattr(sut, "SOURCE_LEDGER_REL", "hyp002/ledger.jsonl")
    monkeypatch.setattr(sut, "ELIGIBLE_LEDGER_REL", "hyp008/eligible.jsonl")
    monkeypatch.setattr(sut, "HYP008_REPORT_REL", "hyp008/report.json")
    monkeypatch.setattr(sut, "HYP008_RECEIPT_REL", "hyp008/receipt.json")
    monkeypatch.setattr(sut, "HYP008_TERMINAL_REL", "hyp008/terminal.json")
    monkeypatch.setattr(sut, "DESIGN_MANIFEST_REL", "design/manifest.jsonl")
    monkeypatch.setattr(sut, "DESIGN_RECEIPT_REL", "design/receipt.json")
    monkeypatch.setattr(sut, "COLLECTION_PLAN_REL", "design/collection_plan.md")
    monkeypatch.setattr(sut, "CUSTODIAN_TOOL_REL", "design/custodian.py")
    monkeypatch.setattr(sut, "REGISTRY_REL", "registry.jsonl")
    monkeypatch.setattr(sut, "RUN_PACKET_REL", "packet.json")
    monkeypatch.setattr(sut, "REVIEW_RECEIPT_REL", "review.json")
    monkeypatch.setattr(sut, "EVIDENCE_ROOT_REL", "evidence/HYP009-DESIGN-ECON-001")
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

    eligible_rows = []
    for row in signals:
        raw = sut.canonical_json_bytes(row)
        lf_hash = sut.lf_row_sha256(raw)
        planned = sut.parse_utc(row["planned_entry_time_utc"])
        eligible_rows.append({
            "arm": row["arm"],
            "complete_m5_starts": 12,
            "planned_entry_time_utc": row["planned_entry_time_utc"],
            "reserved_exit_time_utc": iso(planned + timedelta(minutes=60)),
            "source_identity": f"{row['arm']}|{row['planned_entry_time_utc']}",
            "source_lf_row_sha256": lf_hash,
            "status": sut.ELIGIBLE_STATUS,
        })
    eligible_sha = write_jsonl(root / sut.ELIGIBLE_LEDGER_REL, eligible_rows)
    monkeypatch.setattr(sut, "ELIGIBLE_LEDGER_SHA256", eligible_sha)

    shard_rows: list[dict] = []
    for start in starts:
        shard_rows.extend(
            producer_row(start + timedelta(minutes=i), open_=1.1000, high=1.1020, low=1.1000, close=1.1020)
            for i in range(60)
        )
    if bad_after_start:
        shard_rows = shard_rows[:-1]
    dataset_root = root / Path(sut.DESIGN_MANIFEST_REL).parent.parent
    shard_path = dataset_root / "public/DESIGN/2016-01-04/m1.parquet"
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    shard_payload = parquet_payload(shard_rows)
    shard_path.write_bytes(shard_payload)
    shard_sha = sut.sha256_bytes(shard_payload)
    manifest = [{
        "date": "2016-01-04",
        "relative_path": "public/DESIGN/2016-01-04/m1.parquet",
        "sha256": shard_sha,
        "bytes": shard_path.stat().st_size,
        "rows": len(shard_rows),
    }]
    manifest_sha = write_jsonl(root / sut.DESIGN_MANIFEST_REL, manifest)
    monkeypatch.setattr(sut, "DESIGN_MANIFEST_SHA256", manifest_sha)
    collection_path = root / sut.COLLECTION_PLAN_REL
    collection_path.parent.mkdir(parents=True, exist_ok=True)
    collection_path.write_text("frozen collection plan", encoding="utf-8")
    monkeypatch.setattr(sut, "COLLECTION_PLAN_SHA256", sut.sha256_file(collection_path))
    custodian_path = root / sut.CUSTODIAN_TOOL_REL
    custodian_path.parent.mkdir(parents=True, exist_ok=True)
    custodian_path.write_text("# frozen custodian\n", encoding="utf-8")
    monkeypatch.setattr(sut, "CUSTODIAN_TOOL_SHA256", sut.sha256_file(custodian_path))
    receipt = {
        "collection_plan_sha256": sut.COLLECTION_PLAN_SHA256,
        "custodian_tool_sha256": sut.CUSTODIAN_TOOL_SHA256,
        "design_manifest_sha256": manifest_sha,
        "source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }
    monkeypatch.setattr(sut, "DESIGN_RECEIPT_SHA256", write_json(root / sut.DESIGN_RECEIPT_REL, receipt))

    report = {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP008_ATTEMPT_ID,
        "verdict": sut.HYP008_PASS_STATUS,
        "hyp009_drafting_authorized": True,
        "classification_sha256": sut.HYP008_CLASSIFICATION_SHA256,
        "actual_counts": {
            sut.ELIGIBLE_STATUS: {"TRUE_0050": 1220, "SHIFTED_0025": 1214},
        },
        "source_only_counters": hyp008_source_only_counters(),
        "sealed_permissions": hyp008_sealed_permissions(),
    }
    # For synthetic small population, report counts still assert frozen HYP008 constants.
    # That would fail join path only if validate_hyp008 is called with production counts.
    # Keep production constants in report; synthetic execution uses monkeypatched join counts.
    report_sha = write_json(root / "hyp008/report.json", report)
    monkeypatch.setattr(sut, "HYP008_REPORT_SHA256", report_sha)
    source_receipt = {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP008_ATTEMPT_ID,
        "verdict": sut.HYP008_PASS_STATUS,
        "hyp009_drafting_authorized": True,
        "classification_sha256": sut.HYP008_CLASSIFICATION_SHA256,
        "artifact_sha256": {
            "attempt_started.json": sut.HYP008_STARTED_SHA256,
            "round_cascade_008_eligible_source_ledger.jsonl": eligible_sha,
            "round_cascade_008_execution_source_report.json": report_sha,
            "round_cascade_008_ineligible_source_ledger.jsonl": sut.HYP008_INELIGIBLE_LEDGER_SHA256,
        },
        "source_only_counters": hyp008_source_only_counters(),
        "sealed_permissions": hyp008_sealed_permissions(),
    }
    receipt_sha = write_json(root / "hyp008/receipt.json", source_receipt)
    monkeypatch.setattr(sut, "HYP008_RECEIPT_SHA256", receipt_sha)
    terminal = {
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP008_ATTEMPT_ID,
        "status": sut.HYP008_PASS_STATUS,
        "hyp009_drafting_authorized": True,
        "classification_sha256": sut.HYP008_CLASSIFICATION_SHA256,
        "promotion_evidence": False,
        "artifact_sha256": {
            "attempt_started.json": sut.HYP008_STARTED_SHA256,
            "execution_source_receipt.json": receipt_sha,
            "round_cascade_008_eligible_source_ledger.jsonl": eligible_sha,
            "round_cascade_008_execution_source_report.json": report_sha,
            "round_cascade_008_ineligible_source_ledger.jsonl": sut.HYP008_INELIGIBLE_LEDGER_SHA256,
        },
        "source_only_counters": hyp008_source_only_counters(),
        "sealed_permissions": hyp008_sealed_permissions(),
    }
    terminal_sha = write_json(root / "hyp008/terminal.json", terminal)
    monkeypatch.setattr(sut, "HYP008_TERMINAL_SHA256", terminal_sha)

    packet = minimal_packet(root)
    packet.update({
        "source_ledger_path": sut.SOURCE_LEDGER_REL,
        "source_ledger_sha256": ledger_sha,
        "eligible_ledger_path": sut.ELIGIBLE_LEDGER_REL,
        "eligible_ledger_sha256": eligible_sha,
        "hyp008_report_path": sut.HYP008_REPORT_REL,
        "hyp008_report_sha256": report_sha,
        "hyp008_receipt_path": sut.HYP008_RECEIPT_REL,
        "hyp008_receipt_sha256": receipt_sha,
        "hyp008_terminal_path": sut.HYP008_TERMINAL_REL,
        "hyp008_terminal_sha256": terminal_sha,
        "design_manifest_path": sut.DESIGN_MANIFEST_REL,
        "design_manifest_sha256": manifest_sha,
        "design_receipt_path": sut.DESIGN_RECEIPT_REL,
        "design_receipt_sha256": sut.DESIGN_RECEIPT_SHA256,
        "collection_plan_path": sut.COLLECTION_PLAN_REL,
        "collection_plan_sha256": sut.COLLECTION_PLAN_SHA256,
        "custodian_tool_path": sut.CUSTODIAN_TOOL_REL,
        "custodian_tool_sha256": sut.CUSTODIAN_TOOL_SHA256,
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
            "performance_metrics_authorized": True,
            "public_design_m1_authorized": True,
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
            "hyp008_terminal_path": sut.HYP008_TERMINAL_REL,
            "hyp008_terminal_sha256": terminal_sha,
            "eligible_ledger_path": sut.ELIGIBLE_LEDGER_REL,
            "eligible_ledger_sha256": eligible_sha,
            "collection_plan_path": sut.COLLECTION_PLAN_REL,
            "collection_plan_sha256": sut.COLLECTION_PLAN_SHA256,
            "custodian_tool_path": sut.CUSTODIAN_TOOL_REL,
            "custodian_tool_sha256": sut.CUSTODIAN_TOOL_SHA256,
            "economics_authorized": True,
            "post_entry_ohlc_authorized": True,
            "performance_metrics_authorized": True,
            "public_design_m1_authorized": True,
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
    gate_report = json.loads((root / "design_gate_report.json").read_text(encoding="utf-8"))
    trade_rows = [json.loads(line) for line in (root / "design_economics_trade_ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {arm: sum(row["arm"] == arm for row in trade_rows) for arm in ("TRUE_0050", "SHIFTED_0025")} == {
        "TRUE_0050": 2,
        "SHIFTED_0025": 2,
    }
    assert all(row["entry_time_utc"] == row["planned_entry_time_utc"] for row in trade_rows)
    assert gate_report["dsr"]["n_obs"] == 2
    assert gate_report["execution_evidence"] == {
        "class": "BROKER_OBSERVED_M1_PROXY_KILL_ONLY",
        "promotion_evidence": False,
        "tick_exact": False,
    }
    assert receipt["execution_evidence_class"] == sut.EXECUTION_EVIDENCE_CLASS
    assert terminal["receipt_sha256"] == sut.sha256_file(root / "design_economics_receipt.json")
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
    with pytest.raises(sut.EngineeringInvalid, match="right-censored observed M5 horizon"):
        sut.execute_reviewed_design_economics(tmp_path, packet_path)
    root = tmp_path / sut.EVIDENCE_ROOT_REL
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert terminal["hypothesis_id"] == sut.HYPOTHESIS_ID
    assert (root / "attempt_started.json").is_file()


def test_profit_factor_truth_table_and_cost_metrics() -> None:
    finite = sut.profit_factor([2.0, -1.0])
    no_loss = sut.profit_factor([1.0, 2.0])
    assert finite == {"status": "FINITE", "value": 2.0}
    assert no_loss == {"status": "NO_LOSS", "value": None}
    assert sut.relative_pf(no_loss, finite)["status"] == "POSITIVE_INFINITY"
    rows = [trade(datetime(year, 1, 2, tzinfo=UTC), 2.0) for year in sut.DESIGN_YEARS[:4]]
    rows.append(trade(datetime(2020, 1, 2, tzinfo=UTC), -0.5))
    metrics = sut.arm_cost_metrics(rows, 1.50)
    assert metrics["net_R"][0] == pytest.approx(1.85)
    yearly = sut.fixed_year_totals(rows, 1.50)
    assert yearly["positive_year_count"] == 4
