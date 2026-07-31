from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "build_lvor_002_source.py"
SPEC = importlib.util.spec_from_file_location("build_lvor_002_source", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)
UTC = timezone.utc


def utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def minute_rows(
    start: datetime,
    count: int,
    *,
    open_price: float = 1.1000,
    close_step: float = 0.00001,
    tick_volume: int = 10,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    price = open_price
    for index in range(count):
        close = price + close_step
        rows.append(
            {
                "time_utc": start + timedelta(minutes=index),
                "open": price,
                "high": max(price, close) + 0.00001,
                "low": min(price, close) - 0.00001,
                "close": close,
                "tick_volume": tick_volume,
            }
        )
        price = close
    return rows


def synthetic_bar(
    at: datetime,
    *,
    open_price: float = 1.1000,
    high: float = 1.1010,
    low: float = 1.0999,
    close: float = 1.1009,
    sum_tv: int = 100,
) -> dict[str, object]:
    return {
        "time_utc": at,
        "availability_utc": at + timedelta(minutes=15),
        "date": at.date(),
        "slot": (at.hour, at.minute),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "sum_tv": sum_tv,
    }


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def test_exact_m15_and_following_m5_formation() -> None:
    rows = minute_rows(utc(2020, 1, 6, 6), 20)
    m15, m5, quality = sut.build_complete_bars(rows)

    assert [bar["time_utc"] for bar in m15] == [utc(2020, 1, 6, 6)]
    assert utc(2020, 1, 6, 6, 15) in {bar["time_utc"] for bar in m5}
    assert sut.following_confirmation(m15[0], {bar["time_utc"]: bar for bar in m5})[
        "availability_utc"
    ] == utc(2020, 1, 6, 6, 20)
    assert quality["m15_complete"] == 1


@pytest.mark.parametrize("fault", ["gap", "duplicate", "unaligned"])
def test_incomplete_or_malformed_minutes_fail_closed(fault: str) -> None:
    rows = minute_rows(utc(2020, 1, 6, 6), 20)
    if fault == "gap":
        del rows[4]
        m15, _, _ = sut.build_complete_bars(rows)
        assert m15 == []
    elif fault == "duplicate":
        rows.insert(2, dict(rows[2]))
        with pytest.raises(sut.ContractError, match="duplicated|unordered"):
            sut.build_complete_bars(rows)
    else:
        rows[0]["time_utc"] = utc(2020, 1, 6, 6, 0).replace(second=1)
        with pytest.raises(sut.ContractError, match="aligned"):
            sut.build_complete_bars(rows)


def test_wilder_atr20_is_closed_shift1_and_no_lookahead() -> None:
    bars = []
    for index in range(21):
        at = utc(2020, 1, 1, 0) + timedelta(hours=index)
        bars.append(
            {
                "time_utc": at,
                "open": 1.0,
                "high": 1.001,
                "low": 0.999,
                "close": 1.0,
            }
        )
    values = sut.wilder_atr20_by_close(bars)
    assert values[0][0] == utc(2020, 1, 1, 20)
    assert sut.latest_wilder_atr20(bars, utc(2020, 1, 1, 19, 59)) is None
    assert sut.latest_wilder_atr20(bars, utc(2020, 1, 1, 20)) == pytest.approx(0.002)
    bars[-1]["high"] = 2.0
    assert sut.latest_wilder_atr20(bars, utc(2020, 1, 1, 20, 30)) == pytest.approx(0.002)


def test_same_slot_activity_uses_exact_prior_20_business_dates() -> None:
    days = tuple(date(2020, 1, 6) + timedelta(days=index) for index in range(29))
    days = tuple(day for day in days if day.weekday() < 5)[:21]
    bars = [synthetic_bar(utc(day.year, day.month, day.day, 6), sum_tv=100) for day in days]
    bars[-1]["sum_tv"] = 85

    assert sut.activity_ratio_for(bars[-1], bars, days) == pytest.approx(0.85)
    assert sut.activity_ratio_for(bars[19], bars, days) is None


def test_shifted_activity_is_exact_five_business_dates_and_fully_asof() -> None:
    calendar = [date(2020, 1, 1) + timedelta(days=index) for index in range(50)]
    days = tuple(day for day in calendar if day.weekday() < 5)[:26]
    bars = [synthetic_bar(utc(day.year, day.month, day.day, 7), sum_tv=100) for day in days]
    bars[20]["sum_tv"] = 80
    bars[25]["sum_tv"] = 999

    shifted = sut.shifted_activity_for(bars[25], bars, days)

    assert shifted is not None
    assert shifted["source_date"] == days[20]
    assert shifted["activity"] == pytest.approx(0.80)


@pytest.mark.parametrize(
    "impulse,confirmation,direction",
    [
        (
            synthetic_bar(utc(2020, 1, 6, 6), open_price=1.1000, high=1.1010, low=1.1000, close=1.1009),
            {"open": 1.1009, "high": 1.1010, "low": 1.1003, "close": 1.1003},
            "SHORT",
        ),
        (
            synthetic_bar(utc(2020, 1, 6, 6), open_price=1.1010, high=1.1010, low=1.1000, close=1.1001),
            {"open": 1.1001, "high": 1.1007, "low": 1.1000, "close": 1.1007},
            "LONG",
        ),
    ],
)
def test_long_short_rejection_logic(impulse: dict[str, object], confirmation: dict[str, float], direction: str) -> None:
    confirmation.update(
        {
            "time_utc": impulse["availability_utc"],
            "availability_utc": impulse["availability_utc"] + timedelta(minutes=5),
        }
    )
    result = sut.price_surface(impulse, confirmation, atr20=0.001)
    assert result is not None
    assert result["direction"] == direction


@pytest.mark.parametrize(
    "mutation",
    ["range_low", "range_high", "efficiency", "outer_close", "same_body", "no_midpoint_cross"],
)
def test_price_surface_thresholds_and_boundaries(mutation: str) -> None:
    m15 = synthetic_bar(
        utc(2020, 1, 6, 6), open_price=1.1000, high=1.1010, low=1.1000, close=1.1008
    )
    confirm = {
        "time_utc": utc(2020, 1, 6, 6, 15),
        "availability_utc": utc(2020, 1, 6, 6, 20),
        "open": 1.1008,
        "high": 1.1009,
        "low": 1.1003,
        "close": 1.1003,
    }
    atr = 0.001
    if mutation == "range_low":
        atr = 0.00201
    elif mutation == "range_high":
        atr = 0.00079
    elif mutation == "efficiency":
        m15["close"] = 1.10069
    elif mutation == "outer_close":
        m15["close"] = 1.10079
    elif mutation == "same_body":
        confirm["close"] = 1.1009
    else:
        confirm["close"] = 1.1005

    assert sut.price_surface(m15, confirm, atr20=atr) is None


@pytest.mark.parametrize(
    "atr20,open_price,close",
    [
        (0.002, 1.1000, 1.1008),
        (0.0008, 1.1000, 1.1008),
        (0.001, 1.1001, 1.1008),
    ],
)
def test_range_and_efficiency_inclusive_boundaries_pass(
    atr20: float, open_price: float, close: float
) -> None:
    m15 = synthetic_bar(
        utc(2020, 1, 6, 6),
        open_price=open_price,
        high=1.1010,
        low=1.1000,
        close=close,
    )
    confirmation = {
        "time_utc": utc(2020, 1, 6, 6, 15),
        "availability_utc": utc(2020, 1, 6, 6, 20),
        "open": close,
        "high": close + 0.0001,
        "low": 1.1002,
        "close": 1.1002,
    }
    assert sut.price_surface(m15, confirmation, atr20=atr20) is not None


def signal_candidate(at: datetime, *, activity: float = 0.8, shifted: float = 0.8) -> dict[str, object]:
    return {
        "time_utc": at,
        "availability_utc": at + timedelta(minutes=20),
        "direction": "SHORT",
        "year": at.year,
        "activity": activity,
        "shifted_activity": shifted,
        "shifted_source_date": at.date() - timedelta(days=7),
        "atr20": 0.001,
        "range_atr_ratio": 1.0,
        "impulse_efficiency": 0.8,
        "outer_close_fraction": 0.9,
        "confirmation_cross": True,
        "cost_to_sl_ratio": 0.15,
    }


def test_each_arm_has_independent_first_per_day_cap() -> None:
    first = signal_candidate(utc(2020, 1, 6, 6), activity=0.9)
    second = signal_candidate(utc(2020, 1, 6, 7), activity=0.8)
    features = [first, second]

    assert [row["time_utc"] for row in sut.select_daily_signals(features, arm="PRIMARY")] == [
        second["time_utc"]
    ]
    assert [row["time_utc"] for row in sut.select_daily_signals(features, arm="PRICE_ONLY")] == [
        first["time_utc"]
    ]
    assert [row["time_utc"] for row in sut.select_daily_signals(features, arm="SHIFTED_ACTIVITY")] == [
        first["time_utc"]
    ]


@pytest.mark.parametrize("activity,accepted", [(0.85, True), (0.8500001, False)])
def test_primary_activity_boundary(activity: float, accepted: bool) -> None:
    rows = sut.select_daily_signals(
        [signal_candidate(utc(2020, 1, 6, 6), activity=activity)], arm="PRIMARY"
    )
    assert bool(rows) is accepted


def test_timestamp_only_horizon_uses_first_m1_and_six_complete_m5() -> None:
    decision = utc(2020, 1, 6, 6, 20)
    observed_m1 = [decision + timedelta(minutes=2)]
    complete_m5 = [decision + timedelta(minutes=5 * index) for index in range(1, 7)]

    timestamp_index = sut.build_timestamp_index(observed_m1, complete_m5)
    mapped = sut.map_timestamp_horizon(decision, timestamp_index)

    assert mapped["entry_observed_m1_utc"] == decision + timedelta(minutes=2)
    assert mapped["entry_delay_minutes"] == 2.0
    assert mapped["m5_horizon_starts"] == tuple(complete_m5)
    assert mapped["exit_availability_utc"] == complete_m5[-1] + timedelta(minutes=5)
    assert mapped["source_executable"] is True
    assert not ({"open", "high", "low", "close"} & set(mapped))


@pytest.mark.parametrize("delay,accepted", [(60, True), (61, False)])
def test_entry_delay_boundary(delay: int, accepted: bool) -> None:
    decision = utc(2020, 1, 6, 6, 20)
    entry = decision + timedelta(minutes=delay)
    first_m5 = entry + timedelta(minutes=(-entry.minute) % 5)
    timestamp_index = sut.build_timestamp_index(
        [entry], [first_m5 + timedelta(minutes=5 * index) for index in range(6)]
    )
    mapped = sut.map_timestamp_horizon(decision, timestamp_index)
    assert mapped["source_executable"] is accepted


def test_right_censored_six_m5_horizon_is_explicit() -> None:
    decision = utc(2020, 1, 6, 6, 20)
    timestamp_index = sut.build_timestamp_index(
        [decision], [decision + timedelta(minutes=5 * index) for index in range(5)]
    )
    mapped = sut.map_timestamp_horizon(decision, timestamp_index)
    assert mapped["right_censored"] is True
    assert mapped["source_executable"] is False


class TraversalCountingSequence:
    def __init__(self, values: list[datetime]) -> None:
        self.values = values
        self.iterations = 0
        self.yields = 0

    def __iter__(self):
        self.iterations += 1
        for value in self.values:
            self.yields += 1
            yield value


def test_raw_timestamp_indexes_are_each_traversed_once_for_many_signals() -> None:
    decision = utc(2020, 1, 6, 6, 20)
    raw_m1 = TraversalCountingSequence(
        [decision + timedelta(minutes=index) for index in range(200)]
    )
    raw_m5 = TraversalCountingSequence(
        [decision + timedelta(minutes=5 * index) for index in range(40)]
    )
    timestamp_index = sut.build_timestamp_index(raw_m1, raw_m5)
    signals = {
        arm: [signal_candidate(utc(2020, 1, 6 + ordinal, 6)) for ordinal in range(3)]
        for arm in ("PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY")
    }

    sut.build_arm_ledgers(signals, timestamp_index)

    assert raw_m1.iterations == 1
    assert raw_m5.iterations == 1
    assert raw_m1.yields == len(raw_m1.values)
    assert raw_m5.yields == len(raw_m5.values)


@pytest.mark.parametrize("fault", ["m1_duplicate", "m1_unordered", "m5_unaligned"])
def test_timestamp_index_validation_is_one_time_and_fail_closed(fault: str) -> None:
    start = utc(2020, 1, 6, 6, 20)
    m1 = [start, start + timedelta(minutes=1)]
    m5 = [start, start + timedelta(minutes=5)]
    if fault == "m1_duplicate":
        m1[1] = m1[0]
    elif fault == "m1_unordered":
        m1.reverse()
    else:
        m5[0] += timedelta(minutes=1)
    with pytest.raises(sut.ContractError, match="timestamp|aligned|increasing"):
        sut.build_timestamp_index(m1, m5)


def test_ledgers_are_stable_timestamp_only_and_outcome_blind() -> None:
    at = utc(2020, 1, 6, 6)
    signals = {arm: [signal_candidate(at)] for arm in ("PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY")}
    decision = at + timedelta(minutes=20)
    observed_m1 = [decision]
    complete_m5 = [decision + timedelta(minutes=5 * index) for index in range(6)]
    ledgers = sut.build_arm_ledgers(signals, sut.build_timestamp_index(observed_m1, complete_m5))

    assert tuple(ledgers) == ("PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY")
    assert all(len(rows) == 1 for rows in ledgers.values())
    assert all("horizon" in rows[0] for rows in ledgers.values())
    sut.assert_outcome_blind(ledgers)
    encoded = canonical(ledgers)
    for forbidden in (b'"pnl"', b'"return"', b'"open"', b'"close"', b'"win"'):
        assert forbidden not in encoded


def primary_population(count: int = 1043) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows = []
    horizons = []
    for index in range(count):
        direction = "LONG" if index % 2 == 0 else "SHORT"
        year = 2016 + (index % 5)
        rows.append(
            {
                "direction": direction,
                "year": year,
                "cost_to_sl_ratio": 0.25,
            }
        )
        horizons.append({"source_executable": True})
    return rows, horizons


def test_all_stage0_gates_pass_at_inclusive_boundaries() -> None:
    rows, horizons = primary_population()
    result = sut.evaluate_stage0_gates(
        rows,
        elapsed_weeks=sut.ELAPSED_CALENDAR_WEEKS,
        formation_complete=990,
        formation_scheduled=1000,
        horizon_records=horizons,
    )
    assert all(result["gates"].values())
    assert result["verdict"] == "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY"


@pytest.mark.parametrize(
    "mutation,failed_gate",
    [
        ("cadence", "cadence_2_to_5_per_week"),
        ("long", "long_share_at_least_0_25"),
        ("short", "short_share_at_least_0_25"),
        ("year", "no_year_over_0_30"),
        ("formation", "formation_ratio_at_least_0_99"),
        ("horizon", "source_executable_horizon_ratio_at_least_0_99"),
        ("cost", "median_cost_to_sl_ratio_at_most_0_25"),
        ("per_side", "at_least_20_primary_per_side"),
    ],
)
def test_each_stage0_gate_can_fail_independently(mutation: str, failed_gate: str) -> None:
    rows, horizons = primary_population()
    formation = 990
    if mutation == "cadence":
        rows = rows[:520]
        horizons = horizons[:520]
    elif mutation == "long":
        for row in rows[:800]:
            row["direction"] = "SHORT"
    elif mutation == "short":
        for row in rows[:800]:
            row["direction"] = "LONG"
    elif mutation == "year":
        for row in rows[:400]:
            row["year"] = 2016
    elif mutation == "formation":
        formation = 989
    elif mutation == "horizon":
        horizons[:11] = [{"source_executable": False}] * 11
    elif mutation == "cost":
        for row in rows[:522]:
            row["cost_to_sl_ratio"] = 0.250001
    else:
        for index, row in enumerate(rows):
            row["direction"] = "LONG" if index < 19 else "SHORT"

    result = sut.evaluate_stage0_gates(
        rows,
        elapsed_weeks=sut.ELAPSED_CALENDAR_WEEKS,
        formation_complete=formation,
        formation_scheduled=1000,
        horizon_records=horizons,
    )
    assert result["gates"][failed_gate] is False
    assert result["verdict"] == "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"


def review_receipt_payload(builder: bytes, tests: bytes) -> bytes:
    return canonical(
        {
            "schema_version": sut.REVIEW_RECEIPT_SCHEMA,
            "hypothesis_id": sut.HYPOTHESIS_ID,
            "review_status": "PASS",
            "reviewed_builder": {
                "path": sut.BUILDER_REL,
                "base_sha256": sut.reviewed_base_source_sha256(builder),
            },
            "reviewed_tests": {"path": sut.TEST_REL, "sha256": sha(tests)},
            "v1_plan": {"path": sut.PLAN_REL, "sha256": sut.PLAN_SHA256},
            "permissions": {
                "source_feasibility_run": True,
                "performance_or_economics": False,
                "mt5_or_mql5": False,
            },
        }
    ) + b"\n"


def parent_terminal_payload() -> bytes:
    return canonical(
        {
            "artifact_hashes": {
                "attempt_started.json": sut.PARENT_ATTEMPT_STARTED_SHA256,
            },
            "attempt_id": "LVOR001-SOURCE-ATTEMPT-001",
            "hypothesis_id": sut.PARENT_HYPOTHESIS_ID,
            "reason": {
                "message": "forbidden outcome field: complete_m15_plus_following_m5",
                "type": "ContractError",
            },
            "reviewed_registry_row_sha256": sut.PARENT_REVIEWED_REGISTRY_ROW_SHA256,
            "schema_version": "lvor_001_attempt_terminal.v1",
            "sealed_permissions": sut._sealed_permissions(),
            "source_only_counters": sut._executed_source_only_counters(),
            "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
        }
    ) + b"\n"


def test_parent_false_positive_key_is_repaired_without_weakening_guard() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert '"formed_m15_plus_confirm_m5": formation_complete' in source
    assert '"complete_m15_plus_following_m5": formation_complete' not in source
    sut.assert_outcome_blind({"formed_m15_plus_confirm_m5": 1})
    with pytest.raises(sut.ContractError, match="forbidden outcome field"):
        sut.assert_outcome_blind({"complete_m15_plus_following_m5": 1})


def test_exact_parent_terminal_is_accepted() -> None:
    parsed = sut.validate_parent_terminal(parent_terminal_payload())
    assert parsed["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"


@pytest.mark.parametrize(
    "fault",
    ["hash", "missing", "reason", "chain", "status", "counter", "sealed"],
)
def test_parent_terminal_tamper_fails_closed(fault: str, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = parent_terminal_payload()
    if fault == "hash":
        monkeypatch.setattr(sut, "PARENT_TERMINAL_SHA256", "A" * 64)
    else:
        value = json.loads(payload)
        if fault == "missing":
            del value["reason"]
        elif fault == "reason":
            value["reason"]["message"] = "different failure"
        elif fault == "chain":
            value["artifact_hashes"]["unexpected.json"] = "B" * 64
        elif fault == "status":
            value["status"] = "PASS_SOURCE_FEASIBILITY"
        elif fault == "counter":
            value["source_only_counters"]["outcome_fields_emitted"] = 1
        else:
            value["sealed_permissions"]["economics_authorized"] = True
        payload = canonical(value) + b"\n"
        monkeypatch.setattr(sut, "PARENT_TERMINAL_SHA256", sha(payload))
    with pytest.raises(sut.ContractError, match="parent|terminal|binding|SHA"):
        sut.validate_parent_terminal(payload)


def registry_fixture(*, hypothesis_id: str | None = None) -> tuple[bytes, str, bytes, bytes]:
    builder = MODULE_PATH.read_bytes()
    tests = Path(__file__).read_bytes()
    receipt = review_receipt_payload(builder, tests)
    validation = {
        "source_feasibility_only": True,
        "source_run_authorized": True,
        "source_feasibility_attempt_limit": 1,
        "source_feasibility_attempt_id": sut.ATTEMPT_ID,
        "source_feasibility_evidence_root": sut.EVIDENCE_ROOT_REL,
        "probe_status": sut.PROBE_STATUS,
        "independent_implementation_review_status": "PASS",
        "independent_pre_run_review_status": "PASS",
        "independent_quant_prereg_review_status": "PASS",
        "reviewed_builder_path": sut.BUILDER_REL,
        "reviewed_builder_base_sha256": sut.reviewed_base_source_sha256(builder),
        "reviewed_test_path": sut.TEST_REL,
        "reviewed_test_sha256": sha(tests),
        "independent_review_receipt_path": sut.REVIEW_RECEIPT_REL,
        "independent_review_receipt_schema": sut.REVIEW_RECEIPT_SCHEMA,
        "independent_review_receipt_sha256": sha(receipt),
        "clock_path": sut.CLOCK_REL,
        "clock_sha256": sut.CLOCK_SHA256,
        "design_m1_manifest_path": sut.M1_MANIFEST_REL,
        "design_m1_manifest_sha256": sut.M1_MANIFEST_SHA256,
        "design_m1_receipt_path": sut.M1_RECEIPT_REL,
        "design_m1_receipt_sha256": sut.M1_RECEIPT_SHA256,
        "design_m1_source_sha256": sut.M1_SOURCE_SHA256,
        "design_h1_manifest_path": sut.H1_MANIFEST_REL,
        "design_h1_manifest_sha256": sut.H1_MANIFEST_SHA256,
        "design_h1_receipt_path": sut.H1_RECEIPT_REL,
        "design_h1_receipt_sha256": sut.H1_RECEIPT_SHA256,
        "design_h1_price_side": "BID",
        "registry_validator_path": sut.REGISTRY_VALIDATOR_REL,
        "registry_validator_sha256": sut.REGISTRY_VALIDATOR_SHA256,
        "registry_schema_path": sut.REGISTRY_SCHEMA_REL,
        "registry_schema_sha256": sut.REGISTRY_SCHEMA_SHA256,
        "parent_terminal_path": sut.PARENT_TERMINAL_REL,
        "parent_terminal_sha256": sut.PARENT_TERMINAL_SHA256,
    }
    validation.update({field: False for field in sut.SEALED_FALSE_FIELDS})
    row = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": hypothesis_id or sut.HYPOTHESIS_ID,
        "ea_name": sut.EA_NAME,
        "state": "probe",
        "parent_candidate": sut.PARENT_HYPOTHESIS_ID,
        "feature_family": sut.FAMILY,
        "lane": "source-feasibility",
        "symbol": "EURUSD",
        "timeframe": "M15",
        "window": {"from": "2016.01.04", "to": "2020.12.31"},
        "model": None,
        "source_provenance": "FivePercent public DESIGN M1 and H1 BID",
        "source_path": None,
        "source_hash": None,
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.PLAN_SHA256,
        "exact_overrides": "Source feasibility only; no economics",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2.0,
            "max_trades_per_week": 5.0,
            "max_drawdown_pct": 8.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "max_monte_carlo_p95_dd_pct": 8.0,
        },
        "verdict": sut.PROBE_STATUS,
        "reason": "Fresh LVOR source-feasibility authority",
        "updated_at_utc": "2026-07-29T00:00:00Z",
        "run_ids": [],
        "metrics": dict(sut.SOURCE_ONLY_ZERO_METRICS),
        "validation": validation,
    }
    selected = canonical(row) + b"\n"
    history = b'{ "hypothesis_id": "HYP-HISTORY-001" }\n'
    return history + selected, sha(selected), builder, tests


def test_exact_latest_registry_authority_and_bindings_are_accepted() -> None:
    registry, reviewed, builder, tests = registry_fixture()
    row = sut.validate_registry_authority(
        registry, reviewed, builder_payload=builder, test_payload=tests
    )
    assert row["hypothesis_id"] == sut.HYPOTHESIS_ID


def test_canonical_registry_validator_accepts_v1_plan_receipt_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator_path = (
        MODULE_PATH.parents[3] / "04. Memory/research/validate_candidate_registry.py"
    )
    spec = importlib.util.spec_from_file_location("canonical_candidate_validator", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    monkeypatch.setattr(validator, "WORKSPACE", tmp_path)

    registry, _, builder, tests = registry_fixture()
    successor = json.loads(registry.splitlines()[-1])
    receipt = review_receipt_payload(builder, tests)
    payloads = {
        sut.BUILDER_REL: builder,
        sut.TEST_REL: tests,
        sut.REVIEW_RECEIPT_REL: receipt,
    }
    for relative, payload in payloads.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    prior = json.loads(json.dumps(successor))
    for key in validator.SOURCE_ONLY_ALLOWED_VALIDATION_ADDITIONS:
        prior["validation"].pop(key)
    prior["validation"]["source_build_authorized"] = True
    prior["validation"]["source_run_authorized"] = False
    prior["validation"]["probe_status"] = "FROZEN_BUILD_ONLY"
    prior["reason"] = "Synthetic pre-review build authority"
    prior["verdict"] = "FROZEN_BUILD_ONLY"
    prior["updated_at_utc"] = "2026-07-28T23:59:59Z"

    errors = validator._generic_source_only_authority_transition_errors(
        prior, 2, successor
    )

    assert errors == []


def test_review_receipt_exact_object_and_real_hash_binding_are_accepted() -> None:
    registry, reviewed, builder, tests = registry_fixture()
    row = sut.validate_registry_authority(
        registry, reviewed, builder_payload=builder, test_payload=tests
    )
    receipt = review_receipt_payload(builder, tests)

    parsed = sut.validate_review_receipt(
        receipt,
        expected_sha256=row["validation"]["independent_review_receipt_sha256"],
        builder_payload=builder,
        test_payload=tests,
    )

    assert parsed["review_status"] == "PASS"


def test_source_plan_alias_is_rejected() -> None:
    _, _, builder, tests = registry_fixture()
    value = json.loads(review_receipt_payload(builder, tests))
    value["source_plan"] = value.pop("v1_plan")
    receipt = canonical(value) + b"\n"
    with pytest.raises(sut.ContractError, match="receipt|binding"):
        sut.validate_review_receipt(
            receipt,
            expected_sha256=sha(receipt),
            builder_payload=builder,
            test_payload=tests,
        )


@pytest.mark.parametrize(
    "fault", ["fake_hash", "extra", "duplicate", "noncanonical", "wrong_builder"]
)
def test_review_receipt_faults_fail_closed(fault: str) -> None:
    _, _, builder, tests = registry_fixture()
    receipt = review_receipt_payload(builder, tests)
    expected = sha(receipt)
    if fault == "fake_hash":
        expected = "A" * 64
    elif fault == "extra":
        value = json.loads(receipt)
        value["extra"] = False
        receipt = canonical(value) + b"\n"
        expected = sha(receipt)
    elif fault == "duplicate":
        receipt = receipt.replace(
            b'{"hypothesis_id":', b'{"hypothesis_id":"duplicate","hypothesis_id":', 1
        )
        expected = sha(receipt)
    elif fault == "noncanonical":
        receipt = receipt[:-1] + b" \n"
        expected = sha(receipt)
    else:
        builder += b"# drift\n"
    with pytest.raises(sut.ContractError, match="receipt|review|binding|canonical|SHA"):
        sut.validate_review_receipt(
            receipt,
            expected_sha256=expected,
            builder_payload=builder,
            test_payload=tests,
        )


@pytest.mark.parametrize("fault", ["sentinel", "nonlatest", "wrong_id", "economics", "builder"])
def test_authority_faults_fail_closed(fault: str) -> None:
    registry, reviewed, builder, tests = registry_fixture()
    if fault == "sentinel":
        reviewed = "F" * 64
    elif fault == "nonlatest":
        registry += registry.splitlines(keepends=True)[-1]
    elif fault == "wrong_id":
        registry, reviewed, builder, tests = registry_fixture(hypothesis_id="HYP-LVOR-WRONG")
    elif fault == "economics":
        row = json.loads(registry.splitlines()[-1])
        row["validation"]["economics_authorized"] = True
        selected = canonical(row) + b"\n"
        registry = registry.splitlines(keepends=True)[0] + selected
        reviewed = sha(selected)
    else:
        builder += b"# drift\n"
    with pytest.raises(sut.ContractError, match="authority|registry|binding|sealed"):
        sut.validate_registry_authority(
            registry, reviewed, builder_payload=builder, test_payload=tests
        )


def test_default_disarm_blocks_before_any_real_source_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("real source access attempted")

    monkeypatch.setattr(sut, "stable_read_regular", forbidden)
    with pytest.raises(sut.ContractError, match="disarmed|switch|sentinel"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=False)
    assert calls == []


def synthetic_source_report(verdict: str = "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY") -> dict[str, object]:
    return {
        "schema_version": "lvor_002_source_feasibility_report.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "ea_name": sut.EA_NAME,
        "feature_family": sut.FAMILY,
        "evidence_class": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
        "signal_ledgers": {
            "PRIMARY": [],
            "PRICE_ONLY": [],
            "SHIFTED_ACTIVITY": [],
        },
        "stage0": {"verdict": verdict, "gates": {}, "metrics": {}},
        "economics_authorized": False,
    }


def prepare_execute_probe_mocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
    *,
    omit_parent: bool = False,
) -> tuple[bytes, bytes]:
    builder = MODULE_PATH.read_bytes()
    tests = Path(__file__).read_bytes()
    receipt = review_receipt_payload(builder, tests)
    plan = (MODULE_PATH.parent / "HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_PLAN.md").read_bytes()
    parent_terminal = parent_terminal_payload()
    row = {
        "validation": {
            "independent_review_receipt_sha256": sha(receipt),
            "parent_terminal_path": sut.PARENT_TERMINAL_REL,
            "parent_terminal_sha256": sut.PARENT_TERMINAL_SHA256,
        }
    }
    payloads = {
        sut.BUILDER_REL: builder,
        sut.TEST_REL: tests,
        sut.PLAN_REL: plan,
        sut.REGISTRY_REL: b"synthetic-registry\n",
        sut.REGISTRY_VALIDATOR_REL: b"synthetic-validator\n",
        sut.REGISTRY_SCHEMA_REL: b"synthetic-schema\n",
        sut.REVIEW_RECEIPT_REL: receipt,
        sut.CLOCK_REL: b"synthetic-clock\n",
    }
    if not omit_parent:
        payloads[sut.PARENT_TERMINAL_REL] = parent_terminal

    def fake_read(path: Path, allowed_root: Path) -> bytes:
        relative = Path(path).absolute().relative_to(Path(allowed_root).absolute()).as_posix()
        if relative == sut.REVIEW_RECEIPT_REL:
            events.append("receipt_read")
        if relative == sut.PARENT_TERMINAL_REL:
            events.append("parent_read")
            if omit_parent:
                raise sut.ContractError("missing parent terminal")
        if relative not in payloads:
            raise AssertionError(f"unexpected stable read: {relative}")
        return payloads[relative]

    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", "B" * 64)
    monkeypatch.setattr(sut, "EVIDENCE_ROOT_REL", "evidence/LVOR002-SOURCE-ATTEMPT-001")
    monkeypatch.setattr(sut, "stable_read_regular", fake_read)
    monkeypatch.setattr(sut, "validate_registry_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(sut, "validate_registry_authority", lambda *args, **kwargs: row)
    monkeypatch.setattr(sut, "_load_clock_functions", lambda payload: (lambda value: 0, lambda value: value))
    return builder, tests


def test_receipt_precedes_design_and_attempt_is_durable_one_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    prepare_execute_probe_mocks(tmp_path, monkeypatch, events)
    design_calls = 0

    def fake_design(*args, **kwargs):
        nonlocal design_calls
        design_calls += 1
        events.append("design")
        return synthetic_source_report()

    monkeypatch.setattr(sut, "_read_and_scan_design", fake_design)
    report = sut.execute_probe(workspace_root=tmp_path, run_switch=True)

    root = tmp_path / sut.EVIDENCE_ROOT_REL
    assert report["stage0"]["verdict"] == "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"
    assert events.index("receipt_read") < events.index("design")
    assert events.index("parent_read") < events.index("receipt_read")
    assert design_calls == 1
    assert {path.name for path in root.iterdir()} == {
        "attempt_started.json",
        "lvor_002_source_report.json",
        "lvor_002_source_ledger.jsonl",
        "source_feasibility_receipt.json",
        "attempt_terminal.json",
    }
    terminal = json.loads((root / "attempt_terminal.json").read_bytes())
    assert terminal["status"] == "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"
    assert terminal["source_only_counters"]["outcome_fields_emitted"] == 0
    assert terminal["sealed_permissions"]["economics_authorized"] is False
    for name, digest in terminal["artifact_hashes"].items():
        assert sha((root / name).read_bytes()) == digest

    with pytest.raises(sut.ContractError, match="attempt|evidence|exists|reserved"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)
    assert design_calls == 1


def test_post_reservation_failure_writes_one_engineering_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    prepare_execute_probe_mocks(tmp_path, monkeypatch, events)

    def fail_design(*args, **kwargs):
        events.append("design")
        raise sut.ContractError("synthetic source failure")

    monkeypatch.setattr(sut, "_read_and_scan_design", fail_design)
    with pytest.raises(sut.ContractError, match="synthetic source failure"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)

    root = tmp_path / sut.EVIDENCE_ROOT_REL
    assert {path.name for path in root.iterdir()} == {
        "attempt_started.json",
        "attempt_terminal.json",
    }
    terminal_bytes = (root / "attempt_terminal.json").read_bytes()
    terminal = json.loads(terminal_bytes)
    assert terminal["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert terminal["artifact_hashes"] == {
        "attempt_started.json": sha((root / "attempt_started.json").read_bytes())
    }
    with pytest.raises(sut.ContractError, match="attempt|evidence|exists|reserved"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)
    assert (root / "attempt_terminal.json").read_bytes() == terminal_bytes


def test_missing_parent_terminal_fails_before_design_or_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    prepare_execute_probe_mocks(tmp_path, monkeypatch, events, omit_parent=True)
    design_calls = 0

    def fake_design(*args, **kwargs):
        nonlocal design_calls
        design_calls += 1
        return synthetic_source_report()

    monkeypatch.setattr(sut, "_read_and_scan_design", fake_design)
    with pytest.raises(sut.ContractError, match="missing parent terminal"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)
    assert design_calls == 0
    assert not (tmp_path / sut.EVIDENCE_ROOT_REL).exists()


def test_safe_reader_rejects_forbidden_research_branches(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    forbidden = root / "validation" / "shard.parquet"
    forbidden.parent.mkdir(parents=True)
    forbidden.write_bytes(b"sealed")
    with pytest.raises(sut.ContractError, match="forbidden|path alias"):
        sut.stable_read_regular(forbidden, root)


def test_safe_reader_rejects_receipt_hardlink_and_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    original = root / "receipt.json"
    original.write_bytes(b"{}\n")
    hardlink = root / "receipt-hardlink.json"
    hardlink.hardlink_to(original)
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"{}\n")
    with pytest.raises(sut.ContractError, match="alias|link|path"):
        sut.stable_read_regular(hardlink, root)
    with pytest.raises(sut.ContractError, match="alias|link|path"):
        sut.stable_read_regular(outside, root)


def test_plan_hash_binding_matches_exact_bytes() -> None:
    plan = MODULE_PATH.parent / "HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_PLAN.md"
    assert sha(plan.read_bytes()) == sut.PLAN_SHA256


def test_sentinel_is_exactly_disarmed_and_outcomes_are_rejected() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    for key in ("return", "pnl", "profit_factor", "post_entry_open", "trade_count", "win"):
        with pytest.raises(sut.ContractError, match="outcome|forbidden"):
            sut.assert_outcome_blind({key: 1})


def test_source_architecture_has_no_sequence_index_or_inner_full_rebuild() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "index":
            forbidden_calls.append(node.lineno)
    assert forbidden_calls == []
    scan = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_scan_source")
    nested_calls = {
        node.func.id
        for node in ast.walk(scan)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "build_complete_bars" in nested_calls
    assert "activity_ratio_for" not in nested_calls
    assert "shifted_activity_for" not in nested_calls
    mapper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "map_timestamp_horizon"
    )
    forbidden_mapper_nodes = (
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    assert not any(isinstance(node, forbidden_mapper_nodes) for node in ast.walk(mapper))
    mapper_calls = {
        node.func.id
        for node in ast.walk(mapper)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not ({"sorted", "set", "list"} & mapper_calls)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "tuple"
        and node.args
        for node in ast.walk(mapper)
    )


def test_plan_source_paths_and_forbidden_permissions_are_frozen() -> None:
    assert sut.PLAN_REL.endswith("HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_PLAN.md")
    assert sut.BUILDER_REL.endswith("build_lvor_002_source.py")
    assert sut.TEST_REL.endswith("test_build_lvor_002_source.py")
    assert {"network_authorized", "paid_authorized", "mql5_authorized", "mt5_authorized"} <= set(
        sut.SEALED_FALSE_FIELDS
    )
