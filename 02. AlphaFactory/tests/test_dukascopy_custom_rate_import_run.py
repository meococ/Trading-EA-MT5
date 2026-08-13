from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


TOOL = Path(__file__).resolve().parents[1] / "tools" / "research" / "dukascopy_custom_rate_import_run.py"
SPEC = importlib.util.spec_from_file_location("mts005_import_run", TOOL)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_parse_pass_receipt(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.csv"
    receipt.write_text(
        "\n".join(
            [
                "RECEIPT;alphafactory_custom_rate_import_receipt.v1;SOURCE_DATA_ONLY_NO_PERFORMANCE",
                "META;PASS;AFD_EURUSD_DUKA_TSMOM_V5",
                "SPEC;PASS;AFD_EURUSD_DUKA_TSMOM_V5;EURUSD;EUR;USD;EUR;0;100000.00000000",
                "MONTH;2017-01;PASS;530;2120;1;2;HASH",
                "SUMMARY;PASS;AFD_EURUSD_DUKA_TSMOM_V5;1;530;2120;22;1483315200;SOURCE;RANGE;PLAN",
            ]
        ),
        encoding="cp1252",
    )
    parsed = module.parse_receipt(receipt)
    assert parsed["custom_symbol"] == "AFD_EURUSD_DUKA_TSMOM_V5"
    assert parsed["month_pass_count"] == 1
    assert parsed["imported_h1"] == 530
    assert parsed["import_plan_sha256"] == "PLAN"
    assert parsed["trade_spec"] == {
        "custom_symbol": "AFD_EURUSD_DUKA_TSMOM_V5",
        "origin_symbol": "EURUSD",
        "currency_base": "EUR",
        "currency_profit": "USD",
        "currency_margin": "EUR",
        "trade_calc_mode": 0,
        "contract_size": 100000.0,
    }


def test_fatal_receipt_fails_closed(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.csv"
    receipt.write_text(
        "RECEIPT;alphafactory_custom_rate_import_receipt.v1;SOURCE_DATA_ONLY_NO_PERFORMANCE\n"
        "FATAL;H1_READBACK_MISMATCH;2017-01\n",
        encoding="cp1252",
    )
    with pytest.raises(module.ImportRunError, match="H1_READBACK_MISMATCH"):
        module.parse_receipt(receipt)


def test_parse_plan_identity(tmp_path: Path) -> None:
    plan = tmp_path / "plan.csv"
    identity = "A" * 64
    plan.write_text(
        f"META;alphafactory_custom_rate_import_plan.v1;CUSTOM;ORIGIN;5;0.00001;SOURCE;RANGE;{identity}\n",
        encoding="cp1252",
    )
    assert module.parse_plan_identity(plan) == identity
