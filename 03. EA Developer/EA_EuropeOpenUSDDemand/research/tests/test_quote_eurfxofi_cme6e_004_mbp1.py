from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


RESEARCH = Path(__file__).resolve().parents[1]
PATH = RESEARCH / "quote_eurfxofi_cme6e_004_mbp1.py"
SPEC = importlib.util.spec_from_file_location("quote_eurfxofi_cme6e_004_mbp1", PATH)
assert SPEC is not None and SPEC.loader is not None
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def test_contract_is_mbp1_full_population_and_same_ceiling() -> None:
    assert sut.SCHEMA == "mbp-1"
    assert sut.EXPECTED_DATES == 1359
    assert sut.OWNER_CEILING_USD == 2.25


def test_quote_delegate_uses_mbp1_and_restores_parent() -> None:
    class Parent:
        SCHEMA = "mbp-10"

        @staticmethod
        def quote_all(factory, windows, workers):
            assert Parent.SCHEMA == "mbp-1"
            return [{"estimated_usd": 0.1, "billable_bytes": 1, "metadata_attempt": 1}]

    result = sut.quote_all(Parent, lambda: object(), [{}], 1)
    assert result[0]["estimated_usd"] == 0.1
    assert Parent.SCHEMA == "mbp-10"
