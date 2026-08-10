from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH=Path(__file__).resolve().parents[1]/"analyze_vortex_source.py"
SPEC=importlib.util.spec_from_file_location("analyze_vortex_source",MODULE_PATH)
assert SPEC and SPEC.loader
MODULE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


def frame(prices: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"time_utc":pd.date_range("2018-01-01T00:00:00Z",periods=len(prices),freq="1h"),"high":prices+1.0,"low":prices-1.0,"close":prices})


def test_exact_vortex_components_and_unscaled_ratio() -> None:
    indicator=MODULE.calculate_vortex(frame(np.arange(30,dtype=float)))
    assert indicator["tr"].iloc[14]==pytest.approx(2.0)
    assert indicator["vm_plus"].iloc[14]==pytest.approx(3.0)
    assert indicator["vm_minus"].iloc[14]==pytest.approx(1.0)
    assert indicator["vi_plus"].iloc[14]==pytest.approx(1.5)
    assert indicator["vi_minus"].iloc[14]==pytest.approx(0.5)


def test_first_cross_usable_row_is_15() -> None:
    indicator=MODULE.calculate_vortex(frame(np.arange(30,dtype=float)))
    assert not bool(indicator["feature_valid"].iloc[14])
    assert bool(indicator["feature_valid"].iloc[15])


def test_invalid_oldest_dependency_row_blocks_15_not_16() -> None:
    data=frame(np.arange(40,dtype=float)); data.loc[0,"high"]=np.nan
    indicator=MODULE.calculate_vortex(data)
    assert not bool(indicator["feature_valid"].iloc[15])
    assert bool(indicator["feature_valid"].iloc[16])


@pytest.mark.parametrize(
    ("prices","direction"),
    [
        (np.r_[np.linspace(100.0,70.0,40),np.linspace(70.0,120.0,40)],"LONG"),
        (np.r_[np.linspace(70.0,120.0,40),np.linspace(120.0,70.0,40)],"SHORT"),
    ],
)
def test_exact_polarity_crossover(prices: np.ndarray,direction: str) -> None:
    events,report=MODULE.analyze_frame(frame(prices))
    assert [row["direction"] for row in events]==[direction]
    row=events[0]
    if direction=="LONG":
        assert row["prior_vi_plus"]<=row["prior_vi_minus"] and row["vi_plus"]>row["vi_minus"]
    else:
        assert row["prior_vi_plus"]>=row["prior_vi_minus"] and row["vi_plus"]<row["vi_minus"]
    assert report["funnel"]["raw_events"]==1


def test_raw_event_at_next_hour_gap_is_consumed() -> None:
    prices=np.r_[np.linspace(100.0,70.0,40),np.linspace(70.0,120.0,40)]; data=frame(prices); event_index=45
    data.loc[event_index+1:,"time_utc"]=data.loc[event_index+1:,"time_utc"]+pd.Timedelta(hours=1)
    events,report=MODULE.analyze_frame(data)
    assert events==[]
    assert report["funnel"]["raw_events"]==1
    assert report["funnel"]["gap_rejected_events"]==1


def test_market_closure_inside_window_is_bar_count_based() -> None:
    prices=np.r_[np.linspace(100.0,70.0,40),np.linspace(70.0,120.0,40)]; data=frame(prices)
    data.loc[20:,"time_utc"]=data.loc[20:,"time_utc"]+pd.Timedelta(days=2)
    events,_=MODULE.analyze_frame(data)
    assert len(events)==1


def test_event_ledger_exact_allowlist() -> None:
    prices=np.r_[np.linspace(100.0,70.0,40),np.linspace(70.0,120.0,40)]
    events,report=MODULE.analyze_frame(frame(prices)); MODULE.assert_outcome_blind(events,report)
    assert set(events[0])==MODULE.EVENT_KEYS


def test_selected_frame_requires_native_h1() -> None:
    prices=np.arange(MODULE.MIN_ROWS,dtype=float)+100.0; data=frame(prices)
    data.insert(0,"symbol","XAUUSD"); data.insert(1,"timeframe","M5"); data.insert(2,"source_epoch",np.arange(len(data))); data.insert(4,"utc_ambiguous",False)
    with pytest.raises(ValueError,match="H1"): MODULE.validate_selected_frame(data)


def test_registry_requires_explicit_source_permission(tmp_path: Path) -> None:
    registry=tmp_path/"registry.jsonl"; row={"hypothesis_id":MODULE.HYPOTHESIS_ID,"state":"probe","verdict":"FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN","prereg_sha256":MODULE.PREREG_SHA256,"metrics":{"source_feasibility_attempts_consumed":0},"validation":{"source_feasibility_attempt_id":MODULE.ATTEMPT_ID,"source_feasibility_attempt_limit":1,"source_run_authorized":False,"source_feasibility_only":True,"reviewed_analyzer_sha256":MODULE.sha256_file(MODULE_PATH),"outcome_prices_authorized":False,"economics_authorized":False,"research_validation_access_authorized":False,"research_holdout_access_authorized":False,"mt5_authorized":False,"mql5_authorized":False,"live_trading_authorized":False}}
    registry.write_text(json.dumps(row,separators=(",",":"))+"\n",encoding="utf-8")
    with pytest.raises(ValueError,match="source_run"): MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority={"registry_sha256":"A"*64,"latest_row_sha256":"B"*64}; _,marker=MODULE.claim_attempt(tmp_path/"attempt",authority)
    assert marker.exists()
    with pytest.raises(ValueError,match="already exists"): MODULE.claim_attempt(tmp_path/"attempt",authority)
