from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "audit_foundation_bar_real_volume.py"
SPEC = importlib.util.spec_from_file_location("audit_foundation_bar_real_volume", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_summary(share: float = 0.99, recent_distinct: int = 1000, equality: float = 0.1):
    year = {
        "rows": 10_000,
        "positive_share": share,
    }
    return {
        "full": {
            "rows": 90_000,
            "positive_real_volume_rows": int(90_000 * share),
            "zero_real_volume_rows": 90_000 - int(90_000 * share),
            "real_volume_equals_tick_volume_share": equality,
        },
        "recent": {
            "rows": 5_000,
            "positive_share": share,
            "distinct_positive": recent_distinct,
        },
        "years": {str(year_number): dict(year) for year_number in MODULE.YEARS},
    }


def test_all_payload_gates_pass_for_covered_nontrivial_field():
    assert all(MODULE.evaluate_symbol_gates(make_summary()).values())


def test_yearly_coverage_gate_fails_closed():
    summary = make_summary()
    summary["years"]["2020"]["positive_share"] = 0.949
    gates = MODULE.evaluate_symbol_gates(summary)
    assert not gates["every_year_positive_share_at_least_0p95"]


def test_recent_distinct_gate_fails_closed():
    gates = MODULE.evaluate_symbol_gates(make_summary(recent_distinct=99))
    assert not gates["recent_distinct_positive_at_least_100"]


def test_tick_identity_gate_fails_closed():
    gates = MODULE.evaluate_symbol_gates(make_summary(equality=0.995))
    assert not gates["full_exact_tick_identity_below_0p99"]


def test_canonical_json_is_deterministic():
    left = MODULE.canonical_json_bytes({"b": 2, "a": 1})
    right = MODULE.canonical_json_bytes({"a": 1, "b": 2})
    assert left == right == b'{"a":1,"b":2}\n'
