from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SOURCE = Path(__file__).resolve().parents[1] / "evaluate_eurfxmom_eurusd_004_validation.py"
SPEC = importlib.util.spec_from_file_location("eurfxmom004_validation", SOURCE)
assert SPEC is not None and SPEC.loader is not None
mom4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mom4
SPEC.loader.exec_module(mom4)


def test_wrapper_sentinel_shape_is_fail_closed() -> None:
    sentinel = mom4.REVIEWED_REGISTRY_ROW_SHA256
    assert sentinel is None or (
        isinstance(sentinel, str)
        and len(sentinel) == 64
        and set(sentinel).issubset(set("0123456789ABCDEF"))
    )


def test_wrapper_normalized_hash_ignores_only_sentinel_value() -> None:
    payload = SOURCE.read_bytes()
    base = mom4.normalized_evaluator_base_sha256(payload)
    lines = payload.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if mom4._SENTINEL_RE.match(line.rstrip(b"\n"))]
    assert len(matches) == 1
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n"
    lines[index] = b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"' + newline
    armed = b"".join(lines)
    assert mom4.normalized_evaluator_base_sha256(armed) == base


def test_configure_binds_fresh_identity_without_changing_contract() -> None:
    module = mom4.configure()
    assert module.HYPOTHESIS_ID == "HYP-EURFXMOM-EURUSD-M1-004"
    assert module.ATTEMPT_ID == "EURFXMOM004-VALIDATION-001"
    assert module.PLAN_SHA256 == mom4.PLAN_SHA256
    assert module.EXPECTED_DATES == 526
    assert module.COSTS == {"x1": 1.50, "x1_5": 2.25, "x2": 3.00}
    assert module.VALIDATION_START == pd.Timestamp("2021-01-01T00:00:00Z")
    assert module.VALIDATION_END_EXCLUSIVE == pd.Timestamp("2025-01-01T00:00:00Z")


def test_foundation_and_plan_hashes_are_exact() -> None:
    root = mom4.workspace()
    assert mom4.sha256_file(root / mom4.FOUNDATION_REL) == mom4.FOUNDATION_SHA256
    assert mom4.sha256_file(root / mom4.PLAN_REL) == mom4.PLAN_SHA256


def test_configured_foundation_uses_continuation_direction() -> None:
    module = mom4.configure()
    signal = pd.DataFrame(
        {
            "local_date": ["2021-01-04", "2021-01-05"],
            "pre_fix_pressure_pips": [30.0, -30.0],
            "pressure_threshold_pips": [20.0, 20.0],
            "ledger_reversal_direction": [-1, 1],
        }
    )
    targets = pd.DataFrame(
        {
            "local_date": ["2021-01-04", "2021-01-05"],
            "entry": [1.10, 1.10],
            "exit": [1.1010, 1.0990],
            "post_fix_move_pips": [10.0, -10.0],
        }
    )
    trades, _ = module.build_trades(signal, targets)
    np.testing.assert_array_equal(trades["pressure_continuation_primary_direction"], [1, -1])
    assert np.allclose(trades["pressure_continuation_primary_gross_pips"], 10.0)
    assert np.allclose(trades["primary_net_x1_pips"], 8.5)


def test_configured_authority_rejects_disarmed_wrapper() -> None:
    if mom4.REVIEWED_REGISTRY_ROW_SHA256 is None:
        module = mom4.configure()
        with pytest.raises(module.ContractError, match="not armed"):
            module.validate_authority(mom4.workspace())


