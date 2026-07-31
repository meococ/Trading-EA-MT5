from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_eurfxofi_016_train.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi016", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_disarmed_wrapper_hash_normalization_is_stable() -> None:
    assert MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_evaluator_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert MODULE.normalized_evaluator_base_sha256(armed) == base


def test_configure_sets_exact_hyp015_identity() -> None:
    foundation = MODULE.configure()
    assert foundation.HYPOTHESIS_ID == MODULE.HYPOTHESIS_ID
    assert foundation.ATTEMPT_ID == MODULE.ATTEMPT_ID
    assert foundation.RUN_ELIGIBLE_STATE == "probe"
    assert foundation.DISPLAY_TAG == "HYP016"
    assert foundation.ARTIFACT_PREFIX == "EURFXOFI016"
    assert foundation.SCHEMA_PREFIX == "eurfxofi016"
    assert foundation.ALLOWED_MISSING_TARGET_DATES == ("2017-09-28",)


def test_foundation_economic_primitives_remain_available() -> None:
    foundation = MODULE.configure()
    assert foundation.profit_factor([2.0, -1.0, 3.0, -1.0]) == pytest.approx(2.5)
    assert foundation.COSTS == {"x1": 1.5, "x1_5": 2.25, "x2": 3.0}
    assert len(foundation.ARMS) == 4


def test_foundation_authority_is_fail_closed_while_disarmed(tmp_path: Path) -> None:
    foundation = MODULE.configure()
    with pytest.raises(foundation.ContractError, match="not armed"):
        foundation.validate_authority(tmp_path)


def test_foundation_hash_binding_is_exact() -> None:
    assert MODULE.sha256_file(MODULE.workspace() / MODULE.FOUNDATION_REL) == MODULE.FOUNDATION_SHA256
