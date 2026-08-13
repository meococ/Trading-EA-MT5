from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_pvpr_m15_source_v2.py"
SPEC = importlib.util.spec_from_file_location("pvpr_m15_source_v2", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


PROFILE = {"poc": 1.0615, "val": 1.0612, "vah": 1.0618}


def classify(source_open: float, source_close: float):
    return MOD.classify_reentry(source_open, source_close, PROFILE)


def test_exact_val_and_vah_open_equality_never_emit() -> None:
    assert classify(1.0612, 1.0613)[0] is None
    assert classify(1.0618, 1.0617)[0] is None


def test_one_broker_point_outside_emits_inward_reentry() -> None:
    long_direction, long_fields = classify(1.06119, 1.0612)
    short_direction, short_fields = classify(1.06181, 1.0618)
    assert long_direction == "LONG"
    assert long_fields["source_open_points"] == long_fields["val_points"] - 1
    assert short_direction == "SHORT"
    assert short_fields["source_open_points"] == short_fields["vah_points"] + 1


def test_close_value_area_boundaries_are_inclusive() -> None:
    assert classify(1.06119, 1.0612)[0] == "LONG"
    assert classify(1.06181, 1.0618)[0] == "SHORT"


def test_decimal_noise_rounds_to_same_broker_point() -> None:
    assert classify(1.0611999999999999, 1.0613)[0] is None
    assert classify(1.0612000000000001, 1.0613)[0] is None


def test_point_fields_are_integer_and_replayable() -> None:
    direction, fields = classify(1.06119, 1.0612)
    assert direction == "LONG"
    assert set(fields) == {"poc_points", "val_points", "vah_points", "source_open_points", "source_close_points"}
    assert all(isinstance(value, int) for value in fields.values())
    assert fields == {
        "poc_points": 106150,
        "val_points": 106120,
        "vah_points": 106180,
        "source_open_points": 106119,
        "source_close_points": 106120,
    }


def test_formula_dependency_and_no_paid_or_economic_access() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    lower = text.lower()
    assert 'FORMULA_DEPENDENCY = Path(__file__).resolve().with_name("analyze_pvpr_m15_source.py")' in text
    assert '"formula_dependency": FORMULA_DEPENDENCY.resolve()' in text
    assert '"outcomes_read": False' in text
    assert '"economic_fields_read": False' in text
    assert '"paid_data_used": False' in text
    for forbidden in ("profit_factor", "net_profit", "expectancy", "next_open", "next_close", "pnl"):
        assert forbidden not in lower


def test_one_shot_claim_and_failure_terminal() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "output.mkdir(parents=True, exist_ok=False)" in text
    assert 'stage = "ROOT_CLAIMED"' in text
    assert "try:\n        write_json(output / \"attempt_started.json\"" in text
    assert 'if not terminal.exists()' in text
    assert '"same_id_retry_allowed": False' in text


def test_frozen_identity_and_data_contract() -> None:
    assert MOD.HYPOTHESIS_ID == "HYP-PVPR-EURUSD-M15-002"
    assert MOD.ATTEMPT_ID == "PVPR002-SOURCE-001"
    assert MOD.POINT == 0.00001
    assert MOD.SOURCE_SHA256 == "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
    prereg = MOD.PREREG.read_text(encoding="utf-8")
    assert "exact equality never emits" in prereg
    assert "No paid/external data" in prereg
