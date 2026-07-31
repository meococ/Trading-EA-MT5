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

import evaluate_vcex_002_design_economics as sut


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
    open_: float = 1.1000,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
) -> dict:
    stored = at.replace(tzinfo=None)
    return {
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


def iso(at: datetime) -> str:
    return at.astimezone(UTC).isoformat().replace("+00:00", "Z")


def m1(
    at: datetime,
    *,
    open_: float = 1.1000,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
) -> dict:
    return {
        "time_utc": iso(at),
        "open": open_,
        "high": open_ if high is None else high,
        "low": open_ if low is None else low,
        "close": open_ if close is None else close,
    }


def m1_window(start: datetime, n: int = 120, *, open_: float = 1.1000, close: float = 1.1000) -> list[dict]:
    rows = []
    for i in range(n):
        value = open_ if i == 0 else close
        rows.append(m1(start + timedelta(minutes=i), open_=value, high=value, low=value, close=value))
    return rows


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


def classification_row(
    sid: str,
    decision: datetime,
    entry: datetime,
    *,
    status: str = sut.EXECUTABLE_STATUS,
    observed: int = 8,
) -> dict:
    return {
        "schema_version": sut.CLASSIFICATION_SCHEMA,
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP001_ATTEMPT_ID,
        "reviewed_registry_row_sha256": sut.SOURCE_REGISTRY_ROW_SHA256,
        "attempt_started_sha256": sut.SOURCE_ATTEMPT_STARTED_SHA256,
        "source_signal_id": sid,
        "status": status,
        "decision_utc": iso(decision),
        "entry_open_utc": iso(entry),
        "observed_horizon_bars": observed,
        "required_horizon_bars": 8,
    }


def ledger_row(
    sid: str,
    arm: str,
    direction: str,
    decision: datetime,
    entry: datetime,
    *,
    stop_distance_pips: float = 10.0,
    year: int | None = None,
    h: int = 3,
    tau: float = 0.23333333333333334,
    p_early: float = 0.001,
    p_late: float = -0.0002,
) -> dict:
    time_exit = entry + timedelta(minutes=120)
    return {
        "schema_version": sut.LEDGER_SCHEMA,
        "hypothesis_id": sut.PARENT_CANDIDATE,
        "attempt_id": sut.HYP001_ATTEMPT_ID,
        "reviewed_registry_row_sha256": sut.SOURCE_REGISTRY_ROW_SHA256,
        "attempt_started_sha256": sut.SOURCE_ATTEMPT_STARTED_SHA256,
        "candidate_id": f"VCEX001-{arm}-{sid[-16:]}",
        "source_signal_id": sid,
        "arm": arm,
        "decision_utc": iso(decision),
        "entry_open_utc": iso(entry),
        "time_exit_utc": iso(time_exit),
        "direction": direction,
        "year": entry.year if year is None else year,
        "slot": 1,
        "h": h,
        "tau": tau,
        "p_early": p_early,
        "p_late": p_late,
        "atr14_pips": stop_distance_pips,
        "stop_distance_pips": stop_distance_pips,
        "cost_to_stop_ratio": 1.5 / stop_distance_pips,
    }


def paired_population(
    n_exec: int,
    n_excl: int,
    *,
    base: datetime | None = None,
) -> tuple[list[dict], list[dict]]:
    base = base or datetime(2016, 1, 4, 10, 0, tzinfo=UTC)
    classifications: list[dict] = []
    ledger: list[dict] = []
    for i in range(n_exec):
        decision = base + timedelta(days=i)
        entry = decision + timedelta(minutes=15)
        sid = f"VCEX001-SRC-{i:016X}"
        classifications.append(classification_row(sid, decision, entry))
        # Alternate early impulse sign via TRUE direction.
        true_dir = "SHORT" if i % 2 == 0 else "LONG"
        follow_dir = "LONG" if true_dir == "SHORT" else "SHORT"
        ledger.append(ledger_row(sid, "TRUE", true_dir, decision, entry, year=2016 + (i % 5)))
        ledger.append(ledger_row(sid, "FOLLOW_CONTROL", follow_dir, decision, entry, year=2016 + (i % 5)))
    for j in range(n_excl):
        decision = base + timedelta(days=n_exec + j)
        entry = decision + timedelta(minutes=15)
        sid = f"VCEX001-SRC-EXCL-{j:012X}"
        classifications.append(
            classification_row(sid, decision, entry, status=sut.EXCLUDED_STATUS, observed=j % 7)
        )
    return classifications, ledger


def signal_dict(
    entry: datetime,
    *,
    arm: str = "TRUE",
    direction: str = "LONG",
    stop_distance_pips: float = 10.0,
    sid: str = "VCEX001-SRC-TEST",
    year: int | None = None,
) -> dict:
    decision = entry - timedelta(minutes=15)
    return {
        "arm": arm,
        "source_signal_id": sid,
        "direction": direction,
        "decision_utc": decision,
        "entry_open_utc": entry,
        "time_exit_utc": entry + timedelta(minutes=120),
        "stop_distance_pips": stop_distance_pips,
        "h": 3,
        "tau": 0.23,
        "p_early": 0.001,
        "p_late": -0.0002,
        "year": entry.year if year is None else year,
    }


def trade(
    at: datetime,
    gross_r: float,
    *,
    arm: str = "TRUE",
    year: int | None = None,
    stop_distance_pips: float = 10.0,
    sid: str = "SID",
) -> sut.TradeResult:
    return sut.TradeResult(
        arm=arm,
        source_signal_id=sid,
        decision_utc=at - timedelta(minutes=15),
        entry_open_utc=at,
        time_exit_utc=at + timedelta(minutes=120),
        entry_time_utc=at,
        exit_time_utc=at + timedelta(minutes=120),
        direction="LONG",
        entry_bid=1.1000,
        exit_bid=1.1000 + gross_r * stop_distance_pips * 0.0001,
        stop_bid=1.1000 - stop_distance_pips * 0.0001,
        tp_bid=1.1000 + stop_distance_pips * 0.0001,
        stop_distance_pips=stop_distance_pips,
        gross_R=gross_r,
        exit_reason="TIME",
        year=at.year if year is None else year,
    )


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
    assert sut.HYPOTHESIS_ID == "HYP-VCEX-EURUSD-M15-002"
    assert sut.PARENT_CANDIDATE == "HYP-VCEX-EURUSD-M15-001"
    assert sut.ATTEMPT_ID == "VCEX002-DESIGN-ECON-001"
    assert sut.EXPECTED_SIGNAL_COUNTS == {"TRUE": 807, "FOLLOW_CONTROL": 807}
    assert sut.ELAPSED_WEEKS == pytest.approx(260.42857142857144)
    assert sut.COST_TIERS_PIPS == [1.50, 2.25, 3.00]
    assert sut.RISK_PCT_POINTS == 0.5
    assert sut.INITIAL_EQUITY == 100.0
    assert sut.sha256_file(RESEARCH_DIR / Path(sut.PLAN_REL).name) == sut.FROZEN_PLAN_SHA256
    assert sut.main([]) == 2
    assert sut.main(["--run-reviewed-design-economics"]) == 1


def test_module_ast_parses_and_sentinel_is_disarmed() -> None:
    source = Path(sut.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert isinstance(tree, ast.Module)
    assert "REVIEWED_RUN_PACKET_SHA256: str | None = None" in source
    assert sut.REVIEWED_RUN_PACKET_SHA256 is None
    assert sut.SOURCE_TERMINAL_SHA256 == "74832896B42BEE53E4375069B56CFDEB5114BCA66A24E068DC7041F5612C1D49"
    assert sut.SOURCE_RECEIPT_SHA256 == "0D1911848896B9E4D30C21A32AF3720A9D4A0C9A2C231DEFAD2DF73F1E191425"
    assert sut.SOURCE_CLASSIFICATION_SHA256 == "FDD3D608A70D54634511A582E202D431D42F04EEEFBB0239233BB38D32407D06"
    assert sut.SOURCE_LEDGER_SHA256 == "EA608B72DBF146E45FD568BD5A1AA9EC2691D2AE1BF78F244C007F157BDD1978"
    assert sut.DSR_SHA256 == "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"


def test_strict_json_rejects_malformed_duplicate_and_nonfinite() -> None:
    with pytest.raises(sut.EngineeringInvalid, match="invalid packet JSON"):
        sut.strict_json_loads(b"{", label="packet")
    with pytest.raises(sut.EngineeringInvalid, match="duplicate JSON key"):
        sut.strict_json_loads(b'{"a":1,"a":2}', label="packet")
    with pytest.raises(sut.EngineeringInvalid, match="non-finite JSON value"):
        sut.strict_json_loads(b'{"a":NaN}', label="packet")


def test_exact_paired_source_validation_and_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE": 2, "FOLLOW_CONTROL": 2})
    monkeypatch.setattr(sut, "EXPECTED_CLASSIFICATION_TOTAL", 3)
    monkeypatch.setattr(sut, "EXPECTED_EXECUTABLE", 2)
    monkeypatch.setattr(sut, "EXPECTED_EXCLUDED", 1)
    classifications, ledger = paired_population(2, 1)
    c_path = tmp_path / "class.jsonl"
    l_path = tmp_path / "ledger.jsonl"
    c_sha = write_jsonl(c_path, classifications)
    l_sha = write_jsonl(l_path, ledger)
    by_arm = sut.load_and_validate_source_population(c_path, c_sha, l_path, l_sha)
    assert {arm: len(rows) for arm, rows in by_arm.items()} == {"TRUE": 2, "FOLLOW_CONTROL": 2}
    assert by_arm["TRUE"][0]["source_signal_id"] == by_arm["FOLLOW_CONTROL"][0]["source_signal_id"]
    assert by_arm["TRUE"][0]["direction"] != by_arm["FOLLOW_CONTROL"][0]["direction"]


def test_rejected_excluded_duplicate_fanout_mutation_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE": 1, "FOLLOW_CONTROL": 1})
    monkeypatch.setattr(sut, "EXPECTED_CLASSIFICATION_TOTAL", 2)
    monkeypatch.setattr(sut, "EXPECTED_EXECUTABLE", 1)
    monkeypatch.setattr(sut, "EXPECTED_EXCLUDED", 1)
    classifications, ledger = paired_population(1, 1)
    c_path = tmp_path / "class.jsonl"
    l_path = tmp_path / "ledger.jsonl"
    c_sha = write_jsonl(c_path, classifications)
    l_sha = write_jsonl(l_path, ledger)
    sut.load_and_validate_source_population(c_path, c_sha, l_path, l_sha)

    # Excluded ID mapped into ledger.
    bad_ledger = list(ledger)
    excl_sid = classifications[1]["source_signal_id"]
    decision = sut.parse_utc(classifications[1]["decision_utc"])
    entry = sut.parse_utc(classifications[1]["entry_open_utc"])
    bad_ledger.append(ledger_row(excl_sid, "TRUE", "LONG", decision, entry))
    bad_ledger.append(ledger_row(excl_sid, "FOLLOW_CONTROL", "SHORT", decision, entry))
    bad_path = tmp_path / "bad_ledger.jsonl"
    bad_sha = write_jsonl(bad_path, bad_ledger)
    with pytest.raises(sut.EngineeringInvalid, match="excluded source_signal_id"):
        sut.load_and_validate_source_population(c_path, c_sha, bad_path, bad_sha)

    # Duplicate classification id.
    dup_class = classifications + [classifications[0]]
    monkeypatch.setattr(sut, "EXPECTED_CLASSIFICATION_TOTAL", 3)
    d_path = tmp_path / "dup_class.jsonl"
    d_sha = write_jsonl(d_path, dup_class)
    with pytest.raises(sut.EngineeringInvalid, match="duplicate classification"):
        sut.load_and_validate_source_population(d_path, d_sha, l_path, l_sha)

    # Drop one TRUE arm (fanout / missing arm).
    monkeypatch.setattr(sut, "EXPECTED_CLASSIFICATION_TOTAL", 2)
    drop = [row for row in ledger if not (row["arm"] == "TRUE" and row == ledger[0])]
    drop_path = tmp_path / "drop.jsonl"
    drop_sha = write_jsonl(drop_path, drop)
    with pytest.raises(sut.EngineeringInvalid, match="missing matched arms|ledger count"):
        sut.load_and_validate_source_population(c_path, c_sha, drop_path, drop_sha)

    # Mutation of shared paired field.
    mutated = list(ledger)
    mutated[1] = dict(mutated[1])
    mutated[1]["stop_distance_pips"] = 99.0
    m_path = tmp_path / "mut.jsonl"
    m_sha = write_jsonl(m_path, mutated)
    with pytest.raises(sut.EngineeringInvalid, match="paired ledger field mismatch"):
        sut.load_and_validate_source_population(c_path, c_sha, m_path, m_sha)


def test_exact_120_minute_mapping_and_entry_time_exit_equality() -> None:
    entry = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    market = sut.build_observed_market_index(m1_window(entry, 120))
    mapped = sut.map_signal_to_market(signal_dict(entry), market)
    assert mapped.entry_open_utc == entry
    assert mapped.time_exit_utc == entry + timedelta(minutes=120)
    assert mapped.surveillance_end_index - mapped.entry_row_index == 120
    assert market.m1_times[mapped.exit_close_row_index] == entry + timedelta(minutes=119)


def test_missing_gap_right_censor_invalid() -> None:
    entry = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    incomplete = sut.build_observed_market_index(m1_window(entry, 119))
    with pytest.raises(sut.EngineeringInvalid, match="right-censored|gap|missing"):
        sut.map_signal_to_market(signal_dict(entry), incomplete)

    # 120 bars present but one internal minute missing and later minutes shifted.
    gapped = m1_window(entry, 121)
    gapped.pop(30)
    gapped_market = sut.build_observed_market_index(gapped)
    with pytest.raises(sut.EngineeringInvalid, match="gap|missing|non-contiguous|right-censored"):
        sut.map_signal_to_market(signal_dict(entry), gapped_market)

    delayed = sut.build_observed_market_index(m1_window(entry + timedelta(minutes=1), 120))
    with pytest.raises(sut.EngineeringInvalid, match="exact entry M1 bar missing"):
        sut.map_signal_to_market(signal_dict(entry), delayed)


def test_long_short_stop_tp_and_time_exit() -> None:
    entry = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    # Time exit LONG (0.5R; post-entry opens stay inside barriers).
    rows = m1_window(entry, 120, open_=1.1000, close=1.1005)
    timed = sut.simulate_signal(signal_dict(entry, direction="LONG", stop_distance_pips=10.0), rows)
    assert timed.exit_reason == "TIME"
    assert timed.gross_R == pytest.approx(0.5)

    # LONG stop.
    stop_rows = [
        m1(
            entry + timedelta(minutes=i),
            open_=1.1000,
            high=1.1005,
            low=1.0989 if i == 5 else 1.0995,
            close=1.1000,
        )
        for i in range(120)
    ]
    stopped = sut.simulate_signal(signal_dict(entry, direction="LONG", stop_distance_pips=10.0), stop_rows)
    assert stopped.exit_reason == "STOP"
    assert stopped.gross_R == pytest.approx(-1.0)

    # SHORT TP.
    tp_rows = [
        m1(
            entry + timedelta(minutes=i),
            open_=1.1000,
            high=1.1005,
            low=1.0989 if i == 4 else 1.0995,
            close=1.1000,
        )
        for i in range(120)
    ]
    tp = sut.simulate_signal(signal_dict(entry, direction="SHORT", stop_distance_pips=10.0), tp_rows)
    assert tp.exit_reason == "TP"
    assert tp.gross_R == pytest.approx(1.0)


def test_open_gap_adverse_favorable_cap_and_same_minute_adverse_precedence() -> None:
    entry = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    # Adverse open gap beyond stop for LONG.
    gap_stop = []
    for i in range(120):
        if i == 0:
            gap_stop.append(m1(entry, open_=1.1000, high=1.1000, low=1.1000, close=1.1000))
        elif i == 3:
            gap_stop.append(m1(entry + timedelta(minutes=i), open_=1.0985, high=1.0986, low=1.0984, close=1.0985))
        else:
            gap_stop.append(m1(entry + timedelta(minutes=i), open_=1.1000, high=1.1001, low=1.0999, close=1.1000))
    adverse = sut.simulate_signal(signal_dict(entry, direction="LONG", stop_distance_pips=10.0), gap_stop)
    assert adverse.exit_reason == "OPEN_GAP_STOP"
    assert adverse.gross_R <= -1.0

    # Favorable open gap beyond TP capped at +1.
    gap_tp = []
    for i in range(120):
        if i == 0:
            gap_tp.append(m1(entry, open_=1.1000, high=1.1000, low=1.1000, close=1.1000))
        elif i == 2:
            gap_tp.append(m1(entry + timedelta(minutes=i), open_=1.1025, high=1.1026, low=1.1024, close=1.1025))
        else:
            gap_tp.append(m1(entry + timedelta(minutes=i), open_=1.1000, high=1.1001, low=1.0999, close=1.1000))
    fav = sut.simulate_signal(signal_dict(entry, direction="LONG", stop_distance_pips=10.0), gap_tp)
    assert fav.exit_reason == "OPEN_GAP_TP"
    assert fav.gross_R == pytest.approx(1.0)

    # Same-minute both barriers: adverse wins.
    both = [
        m1(
            entry + timedelta(minutes=i),
            open_=1.1000,
            high=1.1015 if i == 6 else 1.1005,
            low=1.0985 if i == 6 else 1.0995,
            close=1.1000,
        )
        for i in range(120)
    ]
    both_hit = sut.simulate_signal(signal_dict(entry, direction="LONG", stop_distance_pips=10.0), both)
    assert both_hit.exit_reason == "STOP"
    assert both_hit.gross_R == pytest.approx(-1.0)


def test_cost_R_and_pf_edge_cases() -> None:
    t = trade(datetime(2019, 1, 2, 10, 0, tzinfo=UTC), 1.0, stop_distance_pips=10.0)
    assert sut.net_R(t, 1.50) == pytest.approx(0.85)
    finite = sut.profit_factor([2.0, -1.0])
    no_loss = sut.profit_factor([1.0, 2.0])
    no_win = sut.profit_factor([0.0, 0.0])
    assert finite == {"status": "FINITE", "value": 2.0}
    assert no_loss == {"status": "NO_LOSS", "value": None}
    assert no_win == {"status": "NO_WIN_NO_LOSS", "value": None}
    assert sut.relative_pf(no_loss, finite)["status"] == "POSITIVE_INFINITY"
    assert sut._relative_pf_gate(sut.relative_pf(no_loss, finite), 0.15) is True
    assert sut._relative_pf_gate({"status": "UNDEFINED", "value": None}, 0.15) is False
    assert sut._relative_pf_gate(sut.relative_pf(finite, no_loss), 0.15) is False


def test_fixed_initial_noncompounding_dd_and_years() -> None:
    # equity = 100 + 0.5 * cum_net_R; two losses of net_R after cost.
    # gross -1, cost 1.5/10=0.15 => net -1.15; cum after two = -2.3; equity=100-1.15=98.85 then 98.85... wait
    # equity_t = 100 + 0.5 * cum; after first cum=-1.15 equity=100-0.575=99.425; DD=(100-99.425)/100*100=0.575
    rows = [
        trade(datetime(2016, 1, 2, tzinfo=UTC), -1.0),
        trade(datetime(2017, 1, 2, tzinfo=UTC), -1.0),
        trade(datetime(2018, 1, 2, tzinfo=UTC), 2.0),
        trade(datetime(2019, 1, 2, tzinfo=UTC), 2.0),
        trade(datetime(2020, 1, 2, tzinfo=UTC), 0.5),
    ]
    dd = sut.fixed_initial_equity_drawdown_pct(rows, 1.50)
    assert math.isfinite(dd)
    assert dd == pytest.approx(0.575 + 0.575 * 100 / 99.425 * 0 + 0, abs=1e-9) or dd > 0
    # Explicit path:
    # trade1 net=-1.15 cum=-1.15 eq=99.425 peak=100 dd=0.575
    # trade2 net=-1.15 cum=-2.30 eq=98.85 peak=100 dd=1.15
    assert dd == pytest.approx(1.15, abs=1e-9)
    yearly = sut.fixed_year_totals(rows, 1.50)
    assert yearly["positive_year_count"] >= 3
    assert set(yearly["year_totals"]) == {"2016", "2017", "2018", "2019", "2020"}


def test_dsr_exact_n_obs_trials_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_dsr_tool(tmp_path, monkeypatch, value=0.99)
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE": 3, "FOLLOW_CONTROL": 3})
    true_net = [0.2, 0.1, -0.05]
    control_net = [0.0, -0.1, -0.05]
    report = sut.dsr_inputs_and_value(true_net, control_net, tmp_path)
    assert report["n_obs"] == 3
    assert report["n_trials"] == 2
    assert report["dsr_tool_sha256"] == sut.DSR_SHA256
    with pytest.raises(sut.EngineeringInvalid, match="TRUE DSR observation count mismatch"):
        sut.dsr_inputs_and_value(true_net[:-1], control_net, tmp_path)


def test_eleven_gates_boundaries_and_kill_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_dsr_tool(tmp_path, monkeypatch, value=0.96)
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE": 5, "FOLLOW_CONTROL": 5})
    monkeypatch.setattr(sut, "ELAPSED_WEEKS", 1.0)  # cadence = 5 within [2,5]
    true_trades = [
        trade(datetime(year, 1, 2, tzinfo=UTC), 2.0 if year < 2020 else 1.0)
        for year in sut.DESIGN_YEARS
    ]
    # Control must realize some losses so relative PF is FINITE (not both NO_LOSS).
    control_trades = [
        trade(
            datetime(year, 6, 2, tzinfo=UTC),
            -0.5 if year in {2016, 2017, 2018} else 0.1,
            arm="FOLLOW_CONTROL",
        )
        for year in sut.DESIGN_YEARS
    ]
    report = sut.evaluate_gates({"TRUE": true_trades, "FOLLOW_CONTROL": control_trades}, tmp_path)
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
        "TRUE fixed-initial-equity max DD",
        "TRUE DSR at 1.50 pips",
        "TRUE PF minus FOLLOW_CONTROL PF",
        "TRUE mean net R minus FOLLOW_CONTROL mean net R",
    ]
    assert report["status"] == "PASS_DESIGN_ECONOMICS_MAY_BUILD_EA"

    loser = [trade(datetime(2016, 1, 2, tzinfo=UTC) + timedelta(hours=i * 3), -1.0) for i in range(5)]
    kill = sut.evaluate_gates({"TRUE": loser, "FOLLOW_CONTROL": control_trades}, tmp_path)
    assert kill["status"] == "KILL_DESIGN_ECONOMICS_NO_EDGE"

    # Boundary: PF 3.00 must be strict >
    monkeypatch.setattr(sut, "EXPECTED_SIGNAL_COUNTS", {"TRUE": 2, "FOLLOW_CONTROL": 2})
    # Construct nets such that PF at 3.00 is exactly 1.00 if possible is hard; instead verify gate helper.
    assert sut._pf_gate({"status": "FINITE", "value": 1.0}, 1.0, strict=True) is False
    assert sut._pf_gate({"status": "FINITE", "value": 1.0}, 1.0, strict=False) is True
    assert sut._pf_gate({"status": "FINITE", "value": 1.30}, 1.30, strict=False) is True
    assert sut.fixed_initial_equity_drawdown_pct(
        [trade(datetime(2016, 1, 2, tzinfo=UTC), 0.0), trade(datetime(2016, 1, 3, tzinfo=UTC), 0.0)],
        1.50,
    ) < 8.0


def test_cadence_identity_constant() -> None:
    assert sut.cadence_per_elapsed_week(807) == pytest.approx(807 / 260.42857142857144)
    assert 2.0 <= sut.cadence_per_elapsed_week(807) <= 5.0


def test_finite_numeric_defense() -> None:
    with pytest.raises(sut.EngineeringInvalid, match="non-finite"):
        sut.profit_factor([float("nan")])
    with pytest.raises(sut.EngineeringInvalid):
        sut.net_R(
            sut.TradeResult(
                arm="TRUE",
                source_signal_id="x",
                decision_utc=datetime(2019, 1, 2, tzinfo=UTC),
                entry_open_utc=datetime(2019, 1, 2, 10, 0, tzinfo=UTC),
                time_exit_utc=datetime(2019, 1, 2, 12, 0, tzinfo=UTC),
                entry_time_utc=datetime(2019, 1, 2, 10, 0, tzinfo=UTC),
                exit_time_utc=datetime(2019, 1, 2, 12, 0, tzinfo=UTC),
                direction="LONG",
                entry_bid=1.1,
                exit_bid=1.1,
                stop_bid=1.0,
                tp_bid=1.2,
                stop_distance_pips=0.0,
                gross_R=1.0,
                exit_reason="TIME",
                year=2019,
            ),
            1.5,
        )


def test_parquet_boundary_rejects_schema_and_hardlink_escape(tmp_path: Path) -> None:
    import pyarrow as pa

    naive = datetime(2016, 1, 5, 0, 0)
    payload = parquet_payload([producer_row(naive)], schema=producer_schema(time_utc_type=pa.timestamp("ms")))
    with pytest.raises(sut.EngineeringInvalid, match="producer schema mismatch"):
        sut.decode_manifest_bound_public_design_parquet(tmp_path, manifest_entry(payload, 1), payload)
    with pytest.raises(sut.EngineeringInvalid, match="manifest-bound"):
        sut.read_m1_shard(payload, Path("missing.parquet"), label="parquet")


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


def test_run_packet_and_latest_registry_false_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert sut.REVIEWED_RUN_PACKET_SHA256 is None
    packet = minimal_packet()
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
            "source_terminal_path": sut.SOURCE_TERMINAL_REL,
            "source_terminal_sha256": sut.SOURCE_TERMINAL_SHA256,
            "source_ledger_path": sut.SOURCE_LEDGER_REL,
            "source_ledger_sha256": sut.SOURCE_LEDGER_SHA256,
            "source_classification_path": sut.SOURCE_CLASSIFICATION_REL,
            "source_classification_sha256": sut.SOURCE_CLASSIFICATION_SHA256,
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


def test_one_use_evidence_and_suspect_pass_recovery(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    # Create-new only once.
    created = sut.create_fresh_evidence_root(tmp_path, "evidence2")
    assert created.is_dir()
    with pytest.raises(sut.EngineeringInvalid, match="already exists"):
        sut.create_fresh_evidence_root(tmp_path, "evidence2")

    # Suspect PASS terminal is unlinked and replaced with ENGINEERING_INVALID.
    suspect = {
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "attempt_id": sut.ATTEMPT_ID,
        "status": "PASS_DESIGN_ECONOMICS_MAY_BUILD_EA",
        "sole_authoritative_completion": True,
    }
    write_json(root / "attempt_terminal.json", suspect)
    write_json(root / "attempt_started.json", {"status": "STARTED"})
    sut.write_failure_terminal(root, "post-write failure", {})
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert terminal["sole_authoritative_completion"] is True


def test_sentinel_normalization_rejects_multiple_or_noncanonical_assignments() -> None:
    armed = b'REVIEWED_RUN_PACKET_SHA256: str | None = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"\n'
    assert sut.normalize_reviewer_bound_source(armed) == b"REVIEWED_RUN_PACKET_SHA256: str | None = None\n"
    with pytest.raises(sut.EngineeringInvalid, match="exactly once"):
        sut.normalize_reviewer_bound_source(armed + armed)


def test_overlap_and_max_one_day() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    sut.assert_no_overlap([trade(start, 0.1), trade(start + timedelta(minutes=120), 0.1)])
    with pytest.raises(sut.EngineeringInvalid, match="overlapping"):
        sut.assert_no_overlap([trade(start, 0.1), trade(start + timedelta(minutes=119), 0.1)])
    s1 = signal_dict(start, sid="A")
    s2 = signal_dict(start + timedelta(days=1), sid="B")
    sut.assert_max_one_per_day([s1, s2])
    with pytest.raises(sut.EngineeringInvalid, match="more than one signal per UTC day"):
        sut.assert_max_one_per_day([s1, signal_dict(start + timedelta(hours=2), sid="C")])


def minimal_packet() -> dict:
    return {
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "parent_candidate": sut.PARENT_CANDIDATE,
        "plan_path": sut.PLAN_REL,
        "plan_sha256": sut.FROZEN_PLAN_SHA256,
        "attempt_id": sut.ATTEMPT_ID,
        "evidence_root": sut.EVIDENCE_ROOT_REL,
        "registry_path": sut.REGISTRY_REL,
        "source_terminal_path": sut.SOURCE_TERMINAL_REL,
        "source_terminal_sha256": sut.SOURCE_TERMINAL_SHA256,
        "source_receipt_path": sut.SOURCE_RECEIPT_REL,
        "source_receipt_sha256": sut.SOURCE_RECEIPT_SHA256,
        "source_classification_path": sut.SOURCE_CLASSIFICATION_REL,
        "source_classification_sha256": sut.SOURCE_CLASSIFICATION_SHA256,
        "source_ledger_path": sut.SOURCE_LEDGER_REL,
        "source_ledger_sha256": sut.SOURCE_LEDGER_SHA256,
        "source_report_path": sut.SOURCE_REPORT_REL,
        "source_report_sha256": sut.SOURCE_REPORT_SHA256,
        "source_attempt_started_sha256": sut.SOURCE_ATTEMPT_STARTED_SHA256,
        "source_registry_row_sha256": sut.SOURCE_REGISTRY_ROW_SHA256,
        "classification_digest_sha256": sut.CLASSIFICATION_DIGEST_SHA256,
        "canonical_digest_sha256": sut.CANONICAL_DIGEST_SHA256,
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
        "expected_true_signals": sut.EXPECTED_SIGNAL_COUNTS["TRUE"],
        "expected_follow_control_signals": sut.EXPECTED_SIGNAL_COUNTS["FOLLOW_CONTROL"],
        "registry_authority": True,
        "evaluator_path": sut.EVALUATOR_REL,
        "test_path": sut.TEST_REL,
        "reviewed_evaluator_base_sha256": "A" * 64,
        "reviewed_test_sha256": "B" * 64,
        "review_receipt_path": sut.REVIEW_RECEIPT_REL,
        "review_receipt_sha256": "C" * 64,
        "economics_authorized": True,
        "post_entry_ohlc_authorized": True,
        "performance_metrics_authorized": True,
        "public_design_m1_authorized": True,
        "attempt_limit": 1,
        **{field: False for field in sut.FORBIDDEN_AUTHORITY_FIELDS},
    }
