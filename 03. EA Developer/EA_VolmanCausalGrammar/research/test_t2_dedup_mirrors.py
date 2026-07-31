from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

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
    IdentityContractError,
    NewsCalendar,
    assert_full_ledger_manifest,
    compare_full_ledgers,
    compare_identities,
    ecrs_er_cross,
    ecrs_v1_gate_trace,
    emit_ecrs_v1_identities,
    emit_scc_challenger_identities,
    emit_scc_control_identities,
    emit_t2_pbp_like_identities,
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


def _full_manifest(kind: str, count: int = 1) -> dict:
    is_d7 = kind.upper() in {"D7", "ECRS", "D7_ECRS", "D7_ECRS_V1_EXACT", "D7_ECRS_V1", "ECRS_V1_EXACT"}
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
    }


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
    assert emit_ecrs_v1_identities(bars, symbol="EURUSD", news_calendar=verified)


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


def _scc_record(**overrides):
    base = {
        "symbol": "EURUSD",
        "timeframe": "M5",
        "pivot_side": "HIGH",
        "pivot_index": 20,
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


def test_scc_control_and_challenger_identity_helpers_are_strict():
    control = emit_scc_control_identities([_scc_record()])
    challenger = emit_scc_challenger_identities([_scc_record()])
    assert control[0]["namespace"] == "D8_SCC_CONTROL_BREAK"
    assert challenger[0]["namespace"] == "D8_SCC_CHALLENGER_RETEST"
    assert control[0]["barrier_price_in_symbol_ticks"] == 123456
    assert challenger[0]["decision_time_utc"] == "2020-01-06T08:20:00Z"
    compare_identities(control, control, key_fields=SCC_CONTROL_FIELDS, allowed_fields=set(control[0]))
    compare_identities(challenger, challenger, key_fields=SCC_CHALLENGER_FIELDS, allowed_fields=set(challenger[0]))
    with pytest.raises(IdentityContractError, match="unknown field"):
        emit_scc_control_identities([_scc_record(extra_context="forbidden")])


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
    scc = emit_scc_control_identities([_scc_record()])
    result = compare_full_ledgers(
        t2,
        scc,
        key_fields=NORMALIZED_OVERLAP_FIELDS,
        left_manifest=_full_manifest("t2_pbp", len(t2)),
        right_manifest=_full_manifest("scc_control", len(scc)),
        allowed_fields=set(t2[0]) | set(scc[0]),
    )
    assert result.jaccard == pytest.approx(1.0)
    with pytest.raises(IdentityContractError, match="empty/empty"):
        compare_full_ledgers(
            [],
            [],
            key_fields=("symbol",),
            left_manifest=_full_manifest("left", 0),
            right_manifest=_full_manifest("right", 0),
        )
