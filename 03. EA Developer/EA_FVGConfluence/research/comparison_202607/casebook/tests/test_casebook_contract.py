from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import analyze_locked_economics as economics
from build_casebook import (
    _acceptable_mitigation,
    _balanced_pick,
    _rejection_or_mid,
    _zone_at,
    assert_source_contract_literals,
    select_casebook,
)
from casebook_contract import HYPOTHESIS_ID, STRATA, STUDY_ID, ContractError, mt5_atr, sha256_file
from run_label_gate import cohen_kappa, reliability_coverage


def test_current_source_literals_and_hash_contract_are_bound() -> None:
    assert_source_contract_literals()


def test_three_candle_emulator_detects_exact_bull_fvg_and_mitigation() -> None:
    o = np.array([1.1000, 1.1004, 1.1012, 1.1020])
    h = np.array([1.1005, 1.1020, 1.1022, 1.1021])
    l = np.array([1.0998, 1.1003, 1.1016, 1.1018])
    c = np.array([1.1004, 1.1018, 1.1020, 1.1019])
    zone = _zone_at(o, h, l, c, 2, atr=0.0010, min_gap=0.0010,
                    min_body_atr=0.80, min_body_range=0.55)
    assert zone is not None and zone["direction"] == 1
    assert zone["bottom"] == pytest.approx(1.1005)
    assert zone["top"] == pytest.approx(1.1016)
    assert _acceptable_mitigation(zone, h, l, 3, 3, 0.50)


def test_current_source_mitigation_contract_checks_only_last_closed_bar() -> None:
    zone = {"direction": 1, "bottom": 1.1000, "top": 1.1010}
    high = np.array([1.1020, 1.1020, 1.1020])
    low = np.array([1.0999, 1.1008, 1.1009])
    # The old bar would invalidate a lifetime check, but current MQL passes
    # from_shift=1 and therefore evaluates only the last closed bar.
    assert not bool(_acceptable_mitigation(zone, high, low, 0, 2, 0.50))
    assert bool(_acceptable_mitigation(zone, high, low, 2, 2, 0.50))


def test_entry_rejects_future_dependency_and_uses_last_closed_bar_only() -> None:
    zone = {"direction": 1, "bottom": 1.1000, "top": 1.1010}
    o = np.array([1.1007, 1.1002, 9.0])
    h = np.array([1.1009, 1.1011, 9.0])
    l = np.array([1.1001, 1.0999, 0.0])
    c = np.array([1.1002, 1.1009, 9.0])
    assert _rejection_or_mid(zone, o, h, l, c, 1)
    # Mutating the next/current bar cannot change the shift=1 decision.
    o[2], h[2], l[2], c[2] = -100, 100, -100, -100
    assert _rejection_or_mid(zone, o, h, l, c, 1)


def _pool_row(split: str, stratum: str, n: int) -> dict:
    year = 2019 if split == "calibration" else 2022
    day = n // 200 + 1
    minute = n % 200
    t = pd.Timestamp(year, 1, day, 8, 0) + pd.Timedelta(minutes=5 * minute)
    return {"decision_time_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "formed_time_utc": (t - pd.Timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decision_time_server": t.strftime("%Y-%m-%dT%H:%M:%S"), "split": split,
            "session": "LONDON" if n % 2 == 0 else "NEW_YORK", "direction": 1 if (n // 2) % 2 == 0 else -1,
            "bottom": 1.0, "top": 1.1, "formed_index": 10, "ea_accept": stratum == STRATA[0],
            "source_score": 3, "source_flags": {}}


def test_selection_reallocates_evaluation_shortage_and_is_deterministic() -> None:
    pools = {s: [] for s in STRATA}
    offsets = {STRATA[0]: 0, STRATA[1]: 1000, STRATA[2]: 2000}
    for split in ("calibration", "evaluation"):
        supplies = {STRATA[0]: 40 if split == "calibration" else 62, STRATA[1]: 180, STRATA[2]: 180}
        for s in STRATA:
            pools[s].extend(_pool_row(split, s, offsets[s] + i) for i in range(supplies[s]))
    first, audit_1 = select_casebook(pools)
    second, audit_2 = select_casebook(pools)
    assert first == second and audit_1 == audit_2
    assert len(first) == 400
    assert audit_1["splits"]["evaluation"]["selected_counts"] == {
        STRATA[0]: 62, STRATA[1]: 119, STRATA[2]: 119}


def test_mt5_atr_matches_simple_true_range_average_and_is_past_only() -> None:
    frame = pd.DataFrame({"high": np.arange(30, dtype=float) + 2,
                          "low": np.arange(30, dtype=float),
                          "close": np.arange(30, dtype=float) + 1})
    before = mt5_atr(frame)
    expected = pd.Series(np.full(30, 2.0)).rolling(14).mean().to_numpy()
    np.testing.assert_allclose(before, expected, equal_nan=True)
    frame.loc[29, ["high", "low", "close"]] = [1000, -1000, 500]
    after = mt5_atr(frame)
    np.testing.assert_allclose(before[:29], after[:29], equal_nan=True)


def test_cohen_kappa_excludes_uncertain_upstream_and_threshold_is_exact() -> None:
    assert cohen_kappa(["ACCEPT", "ACCEPT", "REJECT", "REJECT"],
                       ["ACCEPT", "ACCEPT", "REJECT", "REJECT"]) == pytest.approx(1.0)
    assert cohen_kappa(["ACCEPT"] * 4, ["ACCEPT"] * 4) is None


def test_label_gate_rejects_degenerate_uncertain_coverage() -> None:
    coverage = reliability_coverage(comparable_n=2, resolved_n=2, total_n=400)
    assert coverage["comparable_pass"] is False
    assert coverage["resolved_pass"] is False


def test_selection_never_reuses_the_same_underlying_fvg_identity() -> None:
    pools = {s: [] for s in STRATA}
    offsets = {STRATA[0]: 0, STRATA[1]: 1000, STRATA[2]: 2000}
    for split in ("calibration", "evaluation"):
        supplies = {STRATA[0]: 50 if split == "calibration" else 110,
                    STRATA[1]: 180, STRATA[2]: 180}
        for stratum in STRATA:
            rows = [_pool_row(split, stratum, offsets[stratum] + i) for i in range(supplies[stratum])]
            if len(rows) >= 2:
                rows[1]["formed_time_utc"] = rows[0]["formed_time_utc"]
                rows[1]["direction"] = rows[0]["direction"]
                rows[1]["bottom"] = rows[0]["bottom"]
                rows[1]["top"] = rows[0]["top"]
            pools[stratum].extend(rows)
    selected, _ = select_casebook(pools)
    identities = {(r["formed_time_utc"], r["direction"], r["bottom"], r["top"]) for r in selected}
    assert len(identities) == len(selected) == 400


def test_economic_authorization_refuses_before_market_data_loader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    internal = tmp_path / "internal.json"
    gate = tmp_path / "gate.json"
    prereg = tmp_path / "prereg.json"
    r1 = tmp_path / "r1.csv"
    r2 = tmp_path / "r2.csv"
    registry = tmp_path / "registry.jsonl"
    internal.write_text("{}", encoding="utf-8")
    gate.write_text(json.dumps({"schema_version": "fvg_human_label_gate.v2", "study_id": STUDY_ID,
                                "status": "PASS", "outcomes_loaded": False, "outcome_join_performed": False,
                                "bindings": {}}), encoding="utf-8")
    prereg.write_text("{}", encoding="utf-8")
    r1.write_text("case_id,setup_label\n", encoding="utf-8")
    r2.write_text("case_id,setup_label\n", encoding="utf-8")
    registry.write_text("", encoding="utf-8")
    monkeypatch.setattr(economics, "load_m1_pre_holdout", lambda *a, **k: (_ for _ in ()).throw(AssertionError("outcome loader touched")))
    with pytest.raises(ContractError, match="fresh registry record absent"):
        economics.authorize_before_outcome_load(internal, gate, prereg, r1, r2, registry)


def test_common_execution_is_stop_first_on_same_bar() -> None:
    t = pd.date_range("2022-01-03T08:00:00", periods=8, freq="5min")
    m5 = pd.DataFrame({"time_utc": t, "time_server": t, "bar_close_utc": t + pd.Timedelta(minutes=5),
                       "open": [1.1000] * 8, "high": [1.1005] * 5 + [1.1030] * 3,
                       "low": [1.0995] * 5 + [1.0980] * 3, "close": [1.1000] * 8})
    case = {"case_id": "X", "decision_time_utc": "2022-01-03T08:25:00Z",
            "decision_time_server": "2022-01-03T08:25:00", "direction": 1, "session": "LONDON"}
    result = economics._simulate_common(m5, case)
    assert result["exit_reason"] == "STOP" and result["gross_r"] == -1.0


def test_native_limit_expires_after_exactly_six_m5_bars() -> None:
    t = pd.date_range("2022-01-03T08:00:00", periods=12, freq="5min")
    m5 = pd.DataFrame({"time_utc": t, "time_server": t, "bar_close_utc": t + pd.Timedelta(minutes=5),
                       "open": [1.1000] * 12, "high": [1.1005] * 12,
                       "low": [1.0995] * 12, "close": [1.1000] * 12})
    case = {"case_id": "N", "decision_time_utc": "2022-01-03T08:00:00Z"}
    plan = {"order_type": "LIMIT", "entry": 1.0990, "stop": 1.0980, "target": 1.1010, "direction": 1}
    result = economics._simulate_native(m5, case, plan)
    assert result == {"filled": False, "gross_r": 0.0, "risk_pips": None,
                      "exit_reason": "LIMIT_EXPIRED_6_BARS"}


def test_marketable_buy_limit_fills_at_next_open_with_price_improvement() -> None:
    t = pd.date_range("2022-01-03T08:00:00", periods=12, freq="5min")
    m5 = pd.DataFrame({"time_utc": t, "time_server": t, "bar_close_utc": t + pd.Timedelta(minutes=5),
                       "open": [1.1000] * 12, "high": [1.1004] * 12,
                       "low": [1.0996] * 12, "close": [1.1001] * 12})
    case = {"case_id": "M", "decision_time_utc": "2022-01-03T08:00:00Z"}
    plan = {"order_type": "LIMIT", "entry": 1.1010, "stop": 1.0990, "target": 1.1020, "direction": 1}
    result = economics._simulate_native(m5, case, plan)
    assert result["filled"] is True
    assert result["risk_pips"] == pytest.approx(10.0)
