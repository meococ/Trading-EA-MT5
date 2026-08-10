from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH=Path(__file__).resolve().parents[1]/"analyze_supertrend_source.py"
SPEC=importlib.util.spec_from_file_location("analyze_supertrend_source",MODULE_PATH)
assert SPEC and SPEC.loader
MODULE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


def frame(prices: np.ndarray,start: str="2018-01-01T00:00:00Z") -> pd.DataFrame:
    return pd.DataFrame({"time_utc":pd.date_range(start,periods=len(prices),freq="1h"),"high":prices+1.0,"low":prices-1.0,"close":prices})


def flip_prices() -> np.ndarray:
    return np.r_[np.full(20,100.0),np.linspace(100.0,150.0,20),np.linspace(150.0,80.0,30)]


def test_exact_tr_seed_and_wilder_rma() -> None:
    data=frame(np.full(20,100.0)); indicator=MODULE.calculate_supertrend(data)
    assert indicator["tr"][0]==pytest.approx(2.0)
    assert np.isnan(indicator["atr"][8])
    assert indicator["atr"][9]==pytest.approx(2.0)
    assert indicator["atr"][19]==pytest.approx(2.0)


def test_initial_atr_ready_state_is_down_and_not_a_flip() -> None:
    indicator=MODULE.calculate_supertrend(frame(np.full(20,100.0)))
    assert indicator["state"][8]==0
    assert indicator["state"][9]==MODULE.DOWN
    assert not bool(indicator["feature_valid"][9])
    assert bool(indicator["feature_valid"][10])
    assert indicator["supertrend"][9]==indicator["upper"][9]


def test_exact_direction_flip_sequence() -> None:
    indicator=MODULE.calculate_supertrend(frame(flip_prices()))
    flips=[(i,int(indicator["state"][i])) for i in range(1,len(indicator["state"])) if indicator["state"][i-1]!=0 and indicator["state"][i]!=indicator["state"][i-1]]
    assert flips==[(23,MODULE.UP),(45,MODULE.DOWN)]
    assert indicator["supertrend"][23]==indicator["lower"][23]
    assert indicator["supertrend"][45]==indicator["upper"][45]


def test_final_band_update_uses_prior_close_and_strict_comparisons() -> None:
    data=frame(flip_prices()); indicator=MODULE.calculate_supertrend(data); index=24
    basic_upper=(data.at[index,"high"]+data.at[index,"low"])/2+MODULE.FACTOR*indicator["atr"][index]
    expected=basic_upper if basic_upper<indicator["upper"][index-1] or data.at[index-1,"close"]>indicator["upper"][index-1] else indicator["upper"][index-1]
    assert indicator["upper"][index]==pytest.approx(expected)


def test_scored_events_are_only_semantic_state_changes() -> None:
    events,report=MODULE.analyze_frame(frame(flip_prices()))
    assert [row["direction"] for row in events]==["LONG","SHORT"]
    assert [(row["prior_state"],row["state"]) for row in events]==[("DOWN","UP"),("UP","DOWN")]
    assert report["funnel"]["raw_events"]==2


def test_raw_gap_flip_is_consumed() -> None:
    data=frame(flip_prices()); data.loc[24:,"time_utc"]=data.loc[24:,"time_utc"]+pd.Timedelta(hours=1)
    events,report=MODULE.analyze_frame(data)
    assert [row["direction"] for row in events]==["SHORT"]
    assert report["funnel"]["raw_events"]==2
    assert report["funnel"]["gap_rejected_events"]==1


def test_normal_closure_does_not_reset_recursive_state() -> None:
    data=frame(flip_prices()); data.loc[15:,"time_utc"]=data.loc[15:,"time_utc"]+pd.Timedelta(days=2)
    indicator=MODULE.calculate_supertrend(data)
    flips=[i for i in range(1,len(indicator["state"])) if indicator["state"][i-1]!=0 and indicator["state"][i]!=indicator["state"][i-1]]
    assert flips==[23,45]


def test_event_ledger_exact_source_allowlist() -> None:
    events,report=MODULE.analyze_frame(frame(flip_prices())); MODULE.assert_outcome_blind(events,report)
    assert set(events[0])==MODULE.EVENT_KEYS


def test_selected_frame_requires_manifest_inception_and_valid_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE,"MIN_ROWS",0)
    prices=np.full(20,100.0); data=frame(prices, MODULE.SOURCE_START.isoformat())
    data.insert(0,"symbol","XAUUSD"); data.insert(1,"timeframe","H1"); data.insert(2,"source_epoch",np.arange(len(data))); data.insert(4,"utc_ambiguous",False)
    assert len(MODULE.validate_selected_frame(data))==20
    data.loc[3,"high"]=data.loc[3,"low"]
    with pytest.raises(ValueError,match="geometrically"): MODULE.validate_selected_frame(data)


def test_registry_requires_prehistory_authority(tmp_path: Path) -> None:
    registry=tmp_path/"registry.jsonl"; row={"hypothesis_id":MODULE.HYPOTHESIS_ID,"state":"probe","verdict":"FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN","prereg_sha256":MODULE.PREREG_SHA256,"metrics":{"source_feasibility_attempts_consumed":0},"validation":{"source_feasibility_attempt_id":MODULE.ATTEMPT_ID,"source_feasibility_attempt_limit":1,"source_run_authorized":True,"source_feasibility_only":True,"reviewed_analyzer_sha256":MODULE.sha256_file(MODULE_PATH),"prehistory_source_access_authorized":False,"outcome_prices_authorized":False,"economics_authorized":False,"research_validation_access_authorized":False,"research_holdout_access_authorized":False,"mt5_authorized":False,"mql5_authorized":False,"live_trading_authorized":False}}
    registry.write_text(json.dumps(row,separators=(",",":"))+"\n",encoding="utf-8")
    with pytest.raises(ValueError,match="prehistory"): MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority={"registry_sha256":"A"*64,"latest_row_sha256":"B"*64}; _,marker=MODULE.claim_attempt(tmp_path/"attempt",authority)
    assert marker.exists()
    with pytest.raises(ValueError,match="already exists"): MODULE.claim_attempt(tmp_path/"attempt",authority)
