from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("validate_public_evidence.py")
SPEC = importlib.util.spec_from_file_location("validate_public_evidence", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def frozen_candidate(number: int) -> dict:
    return {
        "candidate_id": f"EA-CANDIDATE-{number:02d}",
        "name": f"Candidate {number}",
        "primary_url": f"https://example.test/{number}",
        "product_type": "MT5_EA",
        "instrument_scope": "FX",
        "discovery_basis": ["FVG"],
    }


def freeze() -> dict:
    return {
        "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
        "frozen_at_utc": "2026-07-18T01:00:00Z",
        "pass2_started_at_utc": "2026-07-18T02:00:00Z",
        "candidates": [frozen_candidate(i) for i in range(10)],
    }


def ledger_row(number: int, grade: str = "C") -> dict:
    eligible = grade == "A"
    return {
        "candidate_id": f"EA-CANDIDATE-{number:02d}",
        "access_date": "2026-07-18",
        "source_grade": grade,
        "evidence_urls": [f"https://example.test/{number}"],
        "months_observed": 36 if eligible else 0,
        "closed_trades": 200 if eligible else 0,
        "history_complete": eligible,
        "custom_start_absent": eligible,
        "cashflows_observable": eligible,
        "verification": {
            "myfxbook_track_record": eligible,
            "myfxbook_trading_privileges": eligible,
            "mql5_real_monitored": False,
            "mql5_full_history": False,
        },
        "reproducibility": {
            "source_or_demo_available": False,
            "data_hash_bound": False,
            "procedure_reproducible": False,
        },
        "delisted_or_terminated": False,
        "decision": "PERFORMANCE_ELIGIBLE" if eligible else "FEATURE_ONLY",
        "rejection_reasons": [] if eligible else [
            "GRADE_C_FEATURE_ONLY",
            "LT_36_MONTHS",
            "LT_200_CLOSED_TRADES",
            "HISTORY_NOT_COMPLETE",
            "CUSTOM_START_OR_UNKNOWN",
            "CASHFLOWS_NOT_OBSERVABLE",
        ],
        "confidence": "high",
    }


def test_freeze_rejects_performance_leak() -> None:
    payload = freeze()
    payload["candidates"][0]["profit_factor"] = 2.5
    with pytest.raises(MODULE.EvidenceError, match="performance fields leaked"):
        MODULE.validate_freeze(payload)


def test_ledger_preserves_every_rejected_entity() -> None:
    index = MODULE.validate_freeze(freeze())
    ledger = {
        "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
        "entities": [ledger_row(i) for i in range(10)],
    }
    eligible, rows = MODULE.validate_ledger(index, ledger)
    assert eligible == []
    assert len(rows) == 10


def test_five_verified_live_accounts_unlock_comparison() -> None:
    index = MODULE.validate_freeze(freeze())
    ledger = {
        "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
        "entities": [ledger_row(i, "A" if i < 5 else "C") for i in range(10)],
    }
    eligible, _ = MODULE.validate_ledger(index, ledger)
    assert len(eligible) == 5

