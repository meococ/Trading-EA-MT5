from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

import pandas as pd
import pytest


RESEARCH = Path(__file__).resolve().parents[1]
WORKSPACE = Path(__file__).resolve().parents[4]
MODULE_PATH = RESEARCH / "evaluate_euvix_eurusd_002_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_euvix_eurusd_002_train", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
euvix2 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = euvix2
SPEC.loader.exec_module(euvix2)


def test_v2_loads_exact_raw_valid_and_missing_contract() -> None:
    frame = euvix2.load_vix_v2(WORKSPACE)
    assert len(frame) == 1281
    assert frame["vix_close"].notna().all()
    assert frame["vix_date"].is_unique
    assert frame["vix_date"].is_monotonic_increasing


def test_v2_threshold_excludes_current_and_requires_sixty_prior_values() -> None:
    frame = euvix2.load_vix_v2(WORKSPACE)
    assert pd.isna(frame.iloc[59]["vix_threshold"])
    assert frame.iloc[60]["vix_threshold"] == pytest.approx(frame.iloc[:60]["vix_close"].median())
    expected = frame.iloc[:60]["vix_close"].median()
    assert frame.iloc[60]["vix_threshold"] == expected


def test_v1_evaluator_and_zero_outcome_abort_are_hash_bound() -> None:
    module = euvix2.load_v1(WORKSPACE)
    assert module.HYPOTHESIS_ID == "HYP-EUVIX-EURUSD-M1-001"
    assert euvix2.sha256_file(WORKSPACE / euvix2.V1_STARTED_REL) == euvix2.V1_STARTED_SHA256
    assert euvix2.sha256_file(WORKSPACE / euvix2.V1_ABORT_REL) == euvix2.V1_ABORT_SHA256


def test_v2_feature_population_selects_without_same_day_vix() -> None:
    v1 = euvix2.load_v1(WORKSPACE)
    parent = pd.DataFrame({"local_date": ["2020-01-06"], "trade_date": pd.to_datetime(["2020-01-06"]), "year": [2020], "weekday": [0], "direction": ["SHORT"], "entry_local_hhmm": ["07:59"], "exit_local_hhmm": ["14:14"], "gross_pips": [1.0]})
    vix = pd.DataFrame({"vix_date": pd.to_datetime(["2020-01-03", "2020-01-06"]), "vix_close": [20.0, 99.0], "vix_threshold": [18.0, 18.0]})
    selected, coverage = v1.select_high_vix(parent, vix)
    assert coverage == 1.0
    assert selected.iloc[0]["vix_date"] == pd.Timestamp("2020-01-03")


def test_normalized_hash_ignores_only_sentinel() -> None:
    base = MODULE_PATH.read_bytes()
    armed = re.sub(rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$', b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"', base, count=1, flags=re.MULTILINE)
    assert armed != base
    assert euvix2.normalized_evaluator_base_sha256(base) == euvix2.normalized_evaluator_base_sha256(armed)
    with pytest.raises(euvix2.ContractError, match="exactly one"):
        euvix2.normalized_evaluator_base_sha256(base + b"\n" + base)
