from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "profile_sge_shau_auction.py"


def load_module():
    spec = importlib.util.spec_from_file_location("profile_sge_shau_auction", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(day: str, session: int, round_number: int, bid: float, ask: float) -> dict:
    return {
        "trade_date": day,
        "session": str(session),
        "round": str(round_number),
        "bid_kg": str(bid),
        "ask_kg": str(ask),
        "supplemental_balance_kg": "1",
        "source_url": "https://official",
    }


def test_profile_selects_unique_final_pm_and_marks_missing_session() -> None:
    module = load_module()
    rows = [
        row("2017-01-03", 1, 1, 10, 0),
        row("2017-01-03", 2, 1, 0, 10),
        row("2017-01-03", 2, 2, 5, 1),
        row("2022-01-04", 1, 1, 2, 1),
    ]
    payload = module.build_profile(rows)
    assert payload["valid_final_pm_count"] == 1
    assert payload["session_anomalies"][0]["trade_date"] == "2022-01-04"
    assert payload["temporal_provenance_gate"]["pass"] is False
    assert payload["source_gate"]["pass"] is False
    assert payload["holdout_2024_2025_loaded"] is False
    assert payload["price_outcomes_accessed"] is False
