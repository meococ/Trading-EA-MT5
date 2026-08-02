from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import t2_dedup_mirrors as dedup
import run_t2_p3_dedup as runner

from t2_grammar_reference import PbpAuditEvent, PRODUCER_SPEC_SHA256
from t2_dedup_mirrors import (
    BOUND_ECRS_NEWS_COVERAGE_END_UTC,
    BOUND_ECRS_NEWS_COVERAGE_START_UTC,
    BOUND_ECRS_NEWS_CSV_SHA256,
    BOUND_ECRS_NEWS_MANIFEST_SHA256,
    BOUND_ECRS_NEWS_SOURCE,
    CONTRACT_SHA256,
    ECRS_IDENTITY_FIELDS,
    NORMALIZED_OVERLAP_FIELDS,
    SCC_CHALLENGER_FIELDS,
    SCC_CONTROL_FIELDS,
    EcrsBar,
    SccPathBar,
    IdentityContractError,
    NewsCalendar,
    assert_full_ledger_manifest,
    compare_full_ledgers,
    compare_d7_primary_full_ledgers,
    compare_identities,
    ecrs_er_cross,
    ecrs_v1_gate_trace,
    emit_ecrs_v1_identities,
    emit_scc_challenger_identities,
    emit_scc_control_identities,
    emit_t2_pbp_like_identities,
    identity_ledger_sha256,
    identity_time_range,
    load_contract,
    load_bound_news_calendar,
    price_to_ticks,
    reject_outcome_fields,
    synthetic_news_calendar,
    utc_key,
    verify_contract_bindings,
    verify_contract_file,
    verify_sha256,
)


def _ecrs_fixture(side: str = "LONG") -> list[EcrsBar]:
    t0 = datetime(2020, 1, 6, 5, 0, tzinfo=timezone.utc)
    closes = [1.1000 + (0.00005 if i % 2 else 0.0) for i in range(35)]
    closes.append(1.1030)
    closes.append(1.1031)
    bars: list[EcrsBar] = []
    for i, close in enumerate(closes):
        if i < 20:
            high, low = close + 0.0020, close - 0.0020
        elif i < 35:
            high, low = close + 0.00025, close - 0.00025
        elif i == 35:
            high, low = close + 0.00010, close - 0.00050
        else:
            high, low = close + 0.00010, close - 0.00010
        volume = 250.0 if i == 35 else 100.0
        bars.append(EcrsBar(t0 + timedelta(minutes=5 * i), close - 0.00003, high, low, close, volume, 5.0))
    if side == "SHORT":
        return [
            EcrsBar(b.time_utc, -b.open, -b.low, -b.high, -b.close, b.tick_volume, b.spread)
            for b in bars
        ]
    return bars


def _full_manifest(kind: str, records_or_count=1) -> dict:
    records = None if isinstance(records_or_count, int) else list(records_or_count)
    count = records_or_count if isinstance(records_or_count, int) else len(records)
    is_d7 = kind.upper() in {"D7", "ECRS", "D7_ECRS", "D7_ECRS_V1_EXACT", "D7_ECRS_V1", "ECRS_V1_EXACT"}
    is_t2_d7 = "T2" in kind.upper() and "STRUCTURAL" in kind.upper()
    if records is not None:
        identity_first, identity_last = identity_time_range(records)
        ledger_sha = identity_ledger_sha256(records)
    else:
        identity_first = "2020-01-06T08:00:00Z" if count else None
        identity_last = identity_first
        ledger_sha = "3" * 64
    if is_d7 or is_t2_d7:
        source_sha = dedup.BOUND_D7_STAGE0_BARS_SHA256
        source_count = dedup.BOUND_D7_STAGE0_RECORD_COUNT
        source_first = dedup.BOUND_D7_STAGE0_FIRST_UTC
        source_last = dedup.BOUND_D7_STAGE0_LAST_UTC
        producer_sha = (
            dedup.sha256_file(
                Path(__file__).resolve().parent / "t2_grammar_reference.py"
            )
            if is_t2_d7
            else dedup.sha256_file(Path(dedup.__file__))
        )
    else:
        source_sha = "1" * 64
        source_count = max(count, 1)
        source_first = "2019-01-01T00:00:00Z"
        source_last = "2022-12-31T23:59:59Z"
        producer_sha = "2" * 64
    return {
        "source": f"{kind}_full_ledger",
        "producer": "synthetic_unit_test",
        "population_kind": kind,
        "complete_population": True,
        "sampled_casebook": False,
        "contract_sha256": CONTRACT_SHA256,
        "record_count": count,
        "news_calendar_source": "bound_v2_forexfactory_eurusd_high_impact" if is_d7 else "not_applicable",
        "fatal_gate_kind": "D7_ECRS_PRIMARY" if is_d7 else "NONE",
        "ledger_sha256": ledger_sha,
        "source_sha256": source_sha,
        "producer_sha256": producer_sha,
        "source_record_count": source_count,
        "source_first_utc": source_first,
        "source_last_utc": source_last,
        "identity_first_utc": identity_first,
        "identity_last_utc": identity_last,
        "generation_mode": "BOUND_FULL_REPLAY",
    }


@lru_cache(maxsize=1)
def _bound_stage0_module():
    source = (
        Path(__file__).resolve().parents[3]
        / "03. EA Developer/EA_ECRS_CompressionReleaseScalper/research/preflight/stage0_scan.py"
    )
    spec = importlib.util.spec_from_file_location("bound_ecrs_stage0_for_parity", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bound_ecrs_gate_tuple(bars, signal_index, news_times=()):
    module = _bound_stage0_module()
    frame = pd.DataFrame([bar.__dict__ for bar in bars])
    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    volume = frame["tick_volume"].astype(float)
    er = (close - close.shift(10)).abs() / close.diff().abs().rolling(10).sum().replace(0.0, np.nan)
    atr14 = module.atr_mt5(frame, 14)
    atr_sma20 = module.sma(atr14, 20)
    ema20 = module.ema(close, 20)
    tv_sma20 = module.sma(volume, 20)
    i = signal_index
    entry = bars[i + 1]
    g1 = bool(er.iloc[i - 1] < 0.28 and er.iloc[i] >= 0.38)
    g2 = bool(atr14.iloc[i - 1] <= 0.70 * atr_sma20.iloc[i - 1])
    g3_long = bool(close.iloc[i] > high.shift(1).rolling(12).max().iloc[i])
    g3_short = bool(close.iloc[i] < low.shift(1).rolling(12).min().iloc[i])
    g3 = g3_long or g3_short
    g4 = bool(volume.iloc[i] >= 1.7 * tv_sma20.shift(1).iloc[i])
    g5_long = bool(close.iloc[i] > ema20.iloc[i] and ema20.iloc[i] > ema20.shift(3).iloc[i])
    g5_short = bool(close.iloc[i] < ema20.iloc[i] and ema20.iloc[i] < ema20.shift(3).iloc[i])
    direction = "LONG" if g3_long and g5_long else "SHORT" if g3_short and g5_short else None
    entry_minute = entry.time_utc.hour * 60 + entry.time_utc.minute
    g6 = bool(
        entry.time_utc - bars[i].time_utc == timedelta(minutes=5)
        and 7 * 60 <= entry_minute < 16 * 60 + 30
    )
    entry_ns = np.array([np.datetime64(entry.time_utc.replace(tzinfo=None), "ns")])
    news_ns = np.sort(
        np.array(
            [np.datetime64(value.replace(tzinfo=None), "ns") for value in news_times],
            dtype="datetime64[ns]",
        )
    )
    g7 = not bool(module.news_blocked_vec(entry_ns, news_ns, module.NEWS_WINDOW_NS)[0])
    spread_pips = entry.spread / 10.0
    g8 = bool(np.isfinite(spread_pips) and 0.0 < spread_pips <= 0.8)
    return (g1, g2, g3, g4, bool(direction), g6, g7, g8), direction


def test_contract_file_and_real_bound_sources_verify_from_repo_paths():
    assert verify_contract_file() == CONTRACT_SHA256
    contract = load_contract()
    verified = verify_contract_bindings(contract)
    assert verified["ecrs_v1_reference"] == contract["bindings"]["ecrs_v1_reference"]["sha256"]
    assert verified["indicator_reference"] == contract["bindings"]["indicator_reference"]["sha256"]
    assert verified["ecrs_news_csv"] == contract["bindings"]["ecrs_news_csv"]["sha256"]
    calendar = load_bound_news_calendar(contract)
    assert calendar.source == "bound_v2_forexfactory_eurusd_high_impact"
    assert calendar.csv_sha256 == contract["bindings"]["ecrs_news_csv"]["sha256"]
    assert calendar.event_times_utc


def test_p3_runner_schedule_and_atomic_packet_are_bound(tmp_path):
    bindings = runner.verify_execution_bindings(require_committed=False)
    assert bindings["stage0_bars"] == runner.STAGE0_BARS_SHA256
    schedule = runner.load_d7_schedule()
    assert schedule.schedule_sha256 == runner.SCHEDULE_SHA256
    assert schedule.weekend_coverage_only

    common = {
        "symbol": "EURUSD",
        "timeframe": "M5",
        "signal_time_utc": "2020-01-06T07:55:00Z",
        "entry_time_utc": "2020-01-06T08:00:00Z",
        "direction": "LONG",
    }
    event_key = "EURUSD|M5|2020-01-06T07:55:00Z|2020-01-06T08:00:00Z|LONG"
    t2_events = [
        {
            "namespace": "T2_STRUCTURAL_A0_A3",
            **common,
            "arms": ["A0_LOCKED_BARRIER_BREAK"],
            "barrier_ids": ["B1"],
            "producer_spec_sha256": PRODUCER_SPEC_SHA256,
            "event_key": event_key,
        }
    ]
    ecrs_events = [{"namespace": "D7_ECRS_V1_EXACT", **common, "event_key": event_key}]
    packet = {
        "schema_version": "synthetic_writer_fixture",
        "artifacts": {
            "t2_events": t2_events,
            "t2_rejects": [],
            "t2_pbp_audits": [],
            "ecrs_events": ecrs_events,
            "pbp_events": [],
            "pbp_break_events": [],
            "pbp_contact_events": [],
            "scc_control": [],
            "scc_challenger": [],
            "t2_manifest": _full_manifest("T2_STRUCTURAL_A0_A3", t2_events),
            "ecrs_manifest": _full_manifest("D7_ECRS_V1_EXACT", ecrs_events),
            "d8_break_t2_manifest": _full_manifest("T2_PBP_BREAK_WINDOW", []),
            "d8_break_scc_manifest": _full_manifest("SCC_CONTROL_BREAK", []),
            "d8_contact_t2_manifest": _full_manifest("T2_PBP_TOMBSTONE_CONTACT", []),
            "d8_contact_scc_manifest": _full_manifest("SCC_CHALLENGER_RETEST", []),
        },
    }
    output = tmp_path / "packet"
    receipt = runner.write_result_packet(packet, output)
    assert Path(receipt["result_path"]).is_file()
    assert receipt["artifacts"]["t2_manifest"]["records"] == 1
    for key in (
        "t2_manifest",
        "ecrs_manifest",
        "d8_break_t2_manifest",
        "d8_break_scc_manifest",
        "d8_contact_t2_manifest",
        "d8_contact_scc_manifest",
    ):
        assert Path(receipt["artifacts"][key]["path"]).is_file()
        assert len(receipt["artifacts"][key]["sha256"]) == 64
    with pytest.raises(IdentityContractError, match="refusing to overwrite"):
        runner.write_result_packet(packet, output)


def test_execution_freeze_fails_closed_on_tampered_binding(tmp_path):
    verified = runner.verify_execution_freeze(require_committed=False)
    assert verified["bindings"]["runner"] == runner.sha256_file(Path(runner.__file__))
    document = json.loads(runner.EXECUTION_FREEZE_PATH.read_text(encoding="utf-8"))
    document["bindings"]["runner"]["sha256"] = "0" * 64
    tampered = tmp_path / "freeze.json"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(IdentityContractError, match="SHA256 mismatch"):
        runner.verify_execution_freeze(tampered, require_committed=False)


def test_scc_challenger_origin_must_be_strict_subset():
    def origin(index: int):
        return {
            "symbol": "EURUSD",
            "timeframe": "M5",
            "pivot_side": "HIGH",
            "pivot_index": index,
            "pivot_confirm_time_utc": datetime(2020, 1, 1, 8, index, tzinfo=timezone.utc),
            "break_time_utc": datetime(2020, 1, 1, 9, index, tzinfo=timezone.utc),
            "direction": "LONG",
        }

    control = [origin(1), origin(2)]
    runner.assert_scc_challenger_strict_subset(control, [origin(1)])
    with pytest.raises(IdentityContractError, match="strict subset"):
        runner.assert_scc_challenger_strict_subset(control, control)
    with pytest.raises(IdentityContractError, match="strict subset"):
        runner.assert_scc_challenger_strict_subset(control, [origin(3)])


def test_sha_verify_helper_accepts_and_rejects(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("frozen\n", encoding="utf-8")
    assert verify_sha256(f, "7DF47F7B246FEA3FFD24D7156553888A9B1D0FA1C52211D2955052A55E9C77C3")
    with pytest.raises(IdentityContractError, match="SHA256 mismatch"):
        verify_sha256(f, "0" * 64)


def test_recursive_outcome_rejection_and_strict_bar_schema():
    with pytest.raises(IdentityContractError, match="outcome field"):
        reject_outcome_fields({"safe": [{"nested": {"target_result": 1.0}}]})
    bad = _ecrs_fixture()[0].__dict__ | {"unused": 1}
    with pytest.raises(IdentityContractError, match="unknown field"):
        emit_ecrs_v1_identities(
            [bad],
            symbol="EURUSD",
            news_calendar=synthetic_news_calendar([]),
            allow_synthetic_calendar=True,
        )


def test_ecrs_v1_exact_gates_news_scope_and_long_short_mirror():
    bars = _ecrs_fixture("LONG")
    calendar = synthetic_news_calendar([])
    trace = ecrs_v1_gate_trace(
        bars,
        35,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    assert (trace.G1, trace.G2, trace.G3, trace.G4, trace.G5, trace.G6, trace.G7, trace.G8) == (
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )
    assert trace.final and trace.direction == "LONG"
    assert not ecrs_er_cross(0.28, 0.38)
    assert ecrs_er_cross(0.279999, 0.38)

    long_events = emit_ecrs_v1_identities(
        bars,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    short_events = emit_ecrs_v1_identities(
        _ecrs_fixture("SHORT"),
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    assert len(long_events) == len(short_events) == 1
    assert long_events[0]["namespace"] == "D7_ECRS_V1_EXACT"
    assert long_events[0]["direction"] == "LONG"
    assert short_events[0]["direction"] == "SHORT"
    assert long_events[0]["signal_time_utc"] == short_events[0]["signal_time_utc"]
    assert long_events[0]["entry_time_utc"] == "2020-01-06T08:00:00Z"

    blocked = emit_ecrs_v1_identities(
        bars,
        symbol="EURUSD",
        news_calendar=synthetic_news_calendar(["2020-01-06T07:15:00Z"]),
        allow_synthetic_calendar=True,
    )
    assert blocked == []
    out_of_scope = emit_ecrs_v1_identities(
        bars,
        symbol="GBPUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    assert out_of_scope == []

    with pytest.raises(IdentityContractError, match="NewsCalendar"):
        emit_ecrs_v1_identities(bars, symbol="EURUSD", news_calendar=[])
    with pytest.raises(IdentityContractError, match="synthetic news calendar"):
        emit_ecrs_v1_identities(bars, symbol="EURUSD", news_calendar=calendar)


def test_ecrs_every_gate_and_final_identity_match_bound_stage0_semantics():
    bars = _ecrs_fixture("LONG")
    calendar = synthetic_news_calendar([])
    trace = ecrs_v1_gate_trace(
        bars,
        35,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    expected_gates, expected_direction = _bound_ecrs_gate_tuple(bars, 35)
    actual_gates = (trace.G1, trace.G2, trace.G3, trace.G4, trace.G5, trace.G6, trace.G7, trace.G8)
    assert actual_gates == expected_gates
    assert trace.direction == expected_direction
    events = emit_ecrs_v1_identities(
        bars,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    assert events == [
        {
            "namespace": "D7_ECRS_V1_EXACT",
            "symbol": "EURUSD",
            "timeframe": "M5",
            "signal_time_utc": "2020-01-06T07:55:00Z",
            "entry_time_utc": "2020-01-06T08:00:00Z",
            "direction": "LONG",
            "event_key": "EURUSD|M5|2020-01-06T07:55:00Z|2020-01-06T08:00:00Z|LONG",
        }
    ]

    short = _ecrs_fixture("SHORT")
    short_trace = ecrs_v1_gate_trace(
        short,
        35,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    short_expected, short_direction = _bound_ecrs_gate_tuple(short, 35)
    assert (
        short_trace.G1,
        short_trace.G2,
        short_trace.G3,
        short_trace.G4,
        short_trace.G5,
        short_trace.G6,
        short_trace.G7,
        short_trace.G8,
    ) == short_expected
    assert short_trace.direction == short_direction == "SHORT"


def test_ecrs_false_and_boundary_vectors_match_every_bound_gate():
    base = _ecrs_fixture("LONG")
    cases = []

    g1 = list(base)
    g1[35] = replace(
        g1[35],
        open=base[34].close - 0.00003,
        close=base[34].close,
    )
    cases.append(("G1", g1, (), 0))

    g2 = list(base)
    g2[34] = replace(g2[34], high=g2[34].close + 0.01, low=g2[34].close - 0.01)
    cases.append(("G2", g2, (), 1))

    g3 = list(base)
    g3[34] = replace(g3[34], high=base[35].close + 0.0001)
    cases.append(("G3", g3, (), 2))

    g4 = list(base)
    g4[35] = replace(g4[35], tick_volume=100.0)
    cases.append(("G4", g4, (), 3))

    g5 = list(base)
    for index, close in zip((32, 33, 34), (1.1040, 1.1035, 1.1030)):
        g5[index] = replace(
            g5[index],
            open=close - 0.00003,
            high=close + 0.00025,
            low=close - 0.00025,
            close=close,
        )
    cases.append(("G5", g5, (), 4))

    g6 = list(base)
    g6[36] = replace(g6[36], time_utc=g6[35].time_utc + timedelta(minutes=10))
    cases.append(("G6", g6, (), 5))

    cases.append(("G7", base, (base[36].time_utc + timedelta(minutes=45),), 6))

    g8 = list(base)
    g8[36] = replace(g8[36], spread=9.0)
    cases.append(("G8", g8, (), 7))

    for name, bars, news_times, target_index in cases:
        calendar = synthetic_news_calendar(news_times)
        trace = ecrs_v1_gate_trace(
            bars,
            35,
            symbol="EURUSD",
            news_calendar=calendar,
            allow_synthetic_calendar=True,
        )
        actual = (trace.G1, trace.G2, trace.G3, trace.G4, trace.G5, trace.G6, trace.G7, trace.G8)
        expected, _ = _bound_ecrs_gate_tuple(bars, 35, news_times)
        assert actual == expected, name
        assert actual[target_index] is False, name


def test_ecrs_primary_rejects_forged_non_synthetic_bound_calendar():
    bars = _ecrs_fixture("LONG")
    forged = NewsCalendar(
        event_times_utc=(datetime(2020, 1, 1, tzinfo=timezone.utc),),
        source=BOUND_ECRS_NEWS_SOURCE,
        coverage_start_utc=BOUND_ECRS_NEWS_COVERAGE_START_UTC,
        coverage_end_utc=BOUND_ECRS_NEWS_COVERAGE_END_UTC,
        csv_sha256=None,
        manifest_sha256=None,
        synthetic_only=False,
    )

    with pytest.raises(IdentityContractError, match="bound news calendar"):
        emit_ecrs_v1_identities(bars, symbol="EURUSD", news_calendar=forged)

    verified = replace(
        forged,
        csv_sha256=BOUND_ECRS_NEWS_CSV_SHA256,
        manifest_sha256=BOUND_ECRS_NEWS_MANIFEST_SHA256,
    )
    with pytest.raises(IdentityContractError, match="bound news calendar"):
        emit_ecrs_v1_identities(bars, symbol="EURUSD", news_calendar=verified)

    bound = load_bound_news_calendar()
    assert emit_ecrs_v1_identities(bars, symbol="EURUSD", news_calendar=bound)
    with pytest.raises(IdentityContractError, match="verified CSV"):
        emit_ecrs_v1_identities(
            bars,
            symbol="EURUSD",
            news_calendar=replace(bound, event_times_utc=bound.event_times_utc[1:]),
        )


def test_ecrs_prefix_invariance_and_duplicate_identity_rejection():
    bars = _ecrs_fixture("LONG")
    calendar = synthetic_news_calendar([])
    events = emit_ecrs_v1_identities(
        bars,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    future = bars + [
        EcrsBar(datetime(2020, 1, 6, 8, 5, tzinfo=timezone.utc), 1.103, 1.104, 1.102, 1.1035, 100, 5)
    ]
    assert emit_ecrs_v1_identities(
        future,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )[:1] == events
    with pytest.raises(IdentityContractError, match="duplicate"):
        compare_identities(events * 2, [], key_fields=ECRS_IDENTITY_FIELDS, allowed_fields=set(events[0]))


def test_ecrs_full_emitter_builds_indicator_state_once(monkeypatch):
    bars = _ecrs_fixture("LONG")
    calls = 0
    original = dedup._ecrs_state

    def counted(rows):
        nonlocal calls
        calls += 1
        return original(rows)

    monkeypatch.setattr(dedup, "_ecrs_state", counted)
    dedup.emit_ecrs_v1_identities(
        bars,
        symbol="EURUSD",
        news_calendar=synthetic_news_calendar([]),
        allow_synthetic_calendar=True,
    )
    assert calls == 1


def test_timezone_tick_and_full_ledger_manifest_contracts():
    assert utc_key("2020-01-06T15:00:00+07:00") == "2020-01-06T08:00:00Z"
    assert price_to_ticks(1.23456, 0.00001) == 123456
    with pytest.raises(IdentityContractError):
        price_to_ticks(1.2, 0.0)

    assert_full_ledger_manifest(_full_manifest("d7", 1), expected_count=1)
    with pytest.raises(IdentityContractError, match="complete_population"):
        assert_full_ledger_manifest({**_full_manifest("d7"), "complete_population": False})
    with pytest.raises(IdentityContractError, match="sampled_casebook"):
        assert_full_ledger_manifest({**_full_manifest("d7"), "sampled_casebook": True})
    with pytest.raises(IdentityContractError, match="sampled/casebook"):
        assert_full_ledger_manifest({**_full_manifest("sample_casebook"), "source": "stage0_candidate_casebook"})
    with pytest.raises(IdentityContractError, match="synthetic or unbound news calendar"):
        assert_full_ledger_manifest({**_full_manifest("D7_ECRS_V1_EXACT"), "news_calendar_source": "synthetic_only"})
    with pytest.raises(IdentityContractError, match="exact fields required"):
        bad = _full_manifest("D7_ECRS_V1_EXACT")
        del bad["news_calendar_source"]
        assert_full_ledger_manifest(bad)
    with pytest.raises(IdentityContractError, match="contract SHA"):
        assert_full_ledger_manifest({**_full_manifest("D7_ECRS_V1_EXACT"), "contract_sha256": None})
    with pytest.raises(IdentityContractError, match="record_count must be"):
        assert_full_ledger_manifest({**_full_manifest("D7_ECRS_V1_EXACT"), "record_count": None})
    with pytest.raises(IdentityContractError, match="requires fatal_gate_kind"):
        assert_full_ledger_manifest({**_full_manifest("D7_ECRS_V1_EXACT"), "fatal_gate_kind": "NONE"})
    with pytest.raises(IdentityContractError, match="record_count does not match"):
        assert_full_ledger_manifest(_full_manifest("D7_ECRS_V1_EXACT", 2), expected_count=1)
    ledger = [
        {
            "symbol": "EURUSD",
            "timeframe": "M5",
            "direction": "LONG",
            "decision_time_utc": "2020-01-06T08:00:00Z",
        }
    ]
    sealed = _full_manifest("generic_identity", ledger)
    assert_full_ledger_manifest(sealed, records=ledger)
    with pytest.raises(IdentityContractError, match="content SHA"):
        assert_full_ledger_manifest(
            {**sealed, "ledger_sha256": "F" * 64},
            records=ledger,
        )


def _scc_record(**overrides):
    base = {
        "symbol": "EURUSD",
        "timeframe": "M5",
        "pivot_side": "HIGH",
        "pivot_index": 2,
        "pivot_confirm_time_utc": "2020-01-06T07:30:00Z",
        "pivot_price": 1.23456,
        "break_time_utc": "2020-01-06T08:00:00Z",
        "hold_time_utc": "2020-01-06T08:05:00Z",
        "retest_time_utc": "2020-01-06T08:20:00Z",
        "passage_lag": 3,
        "direction": "LONG",
        "tick_size": 0.00001,
    }
    base.update(overrides)
    return base


def _scc_path(*, early_retest: bool = False):
    pivot = 1.23456
    start = datetime(2020, 1, 6, 7, 10, tzinfo=timezone.utc)
    values = []
    for index in range(15):
        when = start + timedelta(minutes=5 * index)
        high, low, close = 1.23440, 1.23400, 1.23430
        if when == datetime(2020, 1, 6, 7, 20, tzinfo=timezone.utc):
            high = pivot
        if when == datetime(2020, 1, 6, 8, 0, tzinfo=timezone.utc):
            high, low, close = 1.23520, 1.23450, 1.23500
        elif when == datetime(2020, 1, 6, 8, 5, tzinfo=timezone.utc):
            high, low, close = 1.23530, 1.23480, 1.23510
        elif when == datetime(2020, 1, 6, 8, 10, tzinfo=timezone.utc):
            high, low, close = 1.23520, pivot if early_retest else 1.23470, 1.23500
        elif when == datetime(2020, 1, 6, 8, 15, tzinfo=timezone.utc):
            high, low, close = 1.23520, 1.23470, 1.23500
        elif when == datetime(2020, 1, 6, 8, 20, tzinfo=timezone.utc):
            high, low, close = 1.23520, 1.23450, 1.23500
        values.append((when, high, low, close))
    return [
        SccPathBar(value[0], *value[1:])
        for value in values
    ]


def test_scc_control_and_challenger_identity_helpers_are_strict():
    control = emit_scc_control_identities([_scc_record()], source_bars=_scc_path())
    challenger = emit_scc_challenger_identities([_scc_record()], source_bars=_scc_path())
    assert control[0]["namespace"] == "D8_SCC_CONTROL_BREAK"
    assert challenger[0]["namespace"] == "D8_SCC_CHALLENGER_RETEST"
    assert control[0]["barrier_price_in_symbol_ticks"] == 123456
    assert challenger[0]["decision_time_utc"] == "2020-01-06T08:20:00Z"
    compare_identities(control, control, key_fields=SCC_CONTROL_FIELDS, allowed_fields=set(control[0]))
    compare_identities(challenger, challenger, key_fields=SCC_CHALLENGER_FIELDS, allowed_fields=set(challenger[0]))
    with pytest.raises(IdentityContractError, match="unknown field"):
        emit_scc_control_identities(
            [_scc_record(extra_context="forbidden")],
            source_bars=_scc_path(),
        )
    with pytest.raises(IdentityContractError, match="not the first passage"):
        emit_scc_challenger_identities(
            [_scc_record()],
            source_bars=_scc_path(early_retest=True),
        )
    broken_path = list(_scc_path())
    broken_path[10] = replace(broken_path[10], close=1.23450)
    with pytest.raises(IdentityContractError, match="claimed close break"):
        emit_scc_control_identities([_scc_record()], source_bars=broken_path)
    with pytest.raises(IdentityContractError, match="one UTC date"):
        emit_scc_challenger_identities(
            [
                _scc_record(
                    break_time_utc="2020-01-06T23:55:00Z",
                    hold_time_utc="2020-01-07T00:00:00Z",
                    retest_time_utc="2020-01-07T00:15:00Z",
                )
            ],
            source_bars=_scc_path(),
        )


def test_t2_pbp_requires_exact_typed_audit_event_and_producer_sha():
    audit = PbpAuditEvent(
        "PBP_BREAK_WINDOW",
        "EURUSD",
        "M5",
        "LONG",
        34,
        datetime(2020, 1, 6, 7, 55, tzinfo=timezone.utc),
        35,
        datetime(2020, 1, 6, 8, 0, tzinfo=timezone.utc),
        28,
        "LONG",
        1.23456,
        123456,
        0.00001,
        "B1",
        datetime(2020, 1, 6, 7, 0, tzinfo=timezone.utc),
        34,
        datetime(2020, 1, 6, 7, 55, tzinfo=timezone.utc),
        None,
        None,
        None,
        None,
    )
    events = emit_t2_pbp_like_identities([audit])
    assert events[0]["subset"] == "PBP_BREAK_WINDOW"
    assert events[0]["economic_authority"] == "NONE"
    assert events[0]["producer_spec_sha256"] == PRODUCER_SPEC_SHA256
    assert events[0]["source_barrier_id"] == "B1"
    assert events[0]["break_time_utc"] == "2020-01-06T07:55:00Z"

    with pytest.raises(IdentityContractError, match="exact PbpAuditEvent"):
        emit_t2_pbp_like_identities([{"event_type": "PBP_BREAK_WINDOW"}])
    with pytest.raises(IdentityContractError, match="producer spec SHA"):
        emit_t2_pbp_like_identities([replace(audit, producer_spec_sha256="0" * 64)])
    with pytest.raises(IdentityContractError, match="barrier_price_ticks"):
        emit_t2_pbp_like_identities([replace(audit, barrier_price_ticks=999)])
    with pytest.raises(IdentityContractError, match="missing PBP_TOMBSTONE_CONTACT"):
        emit_t2_pbp_like_identities([replace(audit, event_type="PBP_TOMBSTONE_CONTACT")])


def test_full_ledger_jaccard_overlap_and_empty_empty_invalidity():
    t2 = [
        {
            "namespace": "D8_T2_PBP_BREAK_WINDOW",
            "subset": "PBP_BREAK_WINDOW",
            "economic_authority": "NONE",
            "producer_spec_sha256": PRODUCER_SPEC_SHA256,
            "symbol": "EURUSD",
            "timeframe": "M5",
            "direction": "LONG",
            "decision_time_utc": "2020-01-06T08:00:00Z",
            "barrier_side": "HIGH",
            "barrier_price_in_symbol_ticks": 123456,
            "event_key": "x",
        }
    ]
    scc = emit_scc_control_identities([_scc_record()], source_bars=_scc_path())
    result = compare_full_ledgers(
        t2,
        scc,
        key_fields=NORMALIZED_OVERLAP_FIELDS,
        left_manifest=_full_manifest("t2_pbp", t2),
        right_manifest=_full_manifest("scc_control", scc),
        allowed_fields=set(t2[0]) | set(scc[0]),
    )
    assert result.jaccard == pytest.approx(1.0)
    with pytest.raises(IdentityContractError, match="empty/empty"):
        compare_full_ledgers(
            [],
            [],
            key_fields=("symbol",),
            left_manifest=_full_manifest("left", []),
            right_manifest=_full_manifest("right", []),
        )


def test_d7_primary_wrapper_enforces_scope_population_and_causal_unmatched_codes():
    common = {
        "symbol": "EURUSD",
        "timeframe": "M5",
        "signal_time_utc": "2020-01-06T07:55:00Z",
        "entry_time_utc": "2020-01-06T08:00:00Z",
        "direction": "LONG",
    }
    first_key = "EURUSD|M5|2020-01-06T07:55:00Z|2020-01-06T08:00:00Z|LONG"
    ecrs = [{"namespace": "D7_ECRS_V1_EXACT", **common, "event_key": first_key}]
    t2 = [
        {
            "namespace": "T2_STRUCTURAL_A0_A3",
            **common,
            "arms": ["A0_LOCKED_BARRIER_BREAK"],
            "barrier_ids": ["B1"],
            "producer_spec_sha256": PRODUCER_SPEC_SHA256,
            "event_key": first_key,
        },
        {
            "namespace": "T2_STRUCTURAL_A0_A3",
            **common,
            "signal_time_utc": "2020-01-06T08:00:00Z",
            "entry_time_utc": "2020-01-06T08:05:00Z",
            "arms": ["A3_PULLBACK_REVERSAL"],
            "barrier_ids": [],
            "producer_spec_sha256": PRODUCER_SPEC_SHA256,
            "event_key": "EURUSD|M5|2020-01-06T08:00:00Z|2020-01-06T08:05:00Z|LONG",
        },
    ]
    result = compare_d7_primary_full_ledgers(
        t2,
        ecrs,
        left_manifest=_full_manifest("T2_STRUCTURAL_A0_A3", t2),
        right_manifest=_full_manifest("D7_ECRS_V1_EXACT", ecrs),
    )
    assert result.jaccard == pytest.approx(0.5)
    assert result.left_count == 2 and result.intersection_count == 1
    assert result.unmatched_reason_codes[0][2] == "T2_PRESSURE_CORRECTION_EVENT_ORDER_ONLY"

    with pytest.raises(IdentityContractError, match="outside the frozen"):
        compare_d7_primary_full_ledgers(
            [
                {
                    **t2[0],
                    "signal_time_utc": "2023-01-02T07:55:00Z",
                    "entry_time_utc": "2023-01-02T08:00:00Z",
                    "event_key": "EURUSD|M5|2023-01-02T07:55:00Z|2023-01-02T08:00:00Z|LONG",
                }
            ],
            ecrs,
            left_manifest=_full_manifest(
                "T2_STRUCTURAL_A0_A3",
                [
                    {
                        **t2[0],
                        "signal_time_utc": "2023-01-02T07:55:00Z",
                        "entry_time_utc": "2023-01-02T08:00:00Z",
                        "event_key": "EURUSD|M5|2023-01-02T07:55:00Z|2023-01-02T08:00:00Z|LONG",
                    }
                ],
            ),
            right_manifest=_full_manifest("D7_ECRS_V1_EXACT", ecrs),
        )
