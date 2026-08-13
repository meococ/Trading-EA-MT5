from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "research" / "dukascopy_custom_rate_import_plan.py"
spec = importlib.util.spec_from_file_location("dukascopy_custom_rate_import_plan", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_afrate_record_geometry_is_stable() -> None:
    assert module.AFRATE_HEADER.size == 16
    assert module.AFRATE_RECORD.size == 60


def test_inspect_rates_accepts_valid_binary(tmp_path: Path) -> None:
    path = tmp_path / "month.afrates"
    row = module.AFRATE_RECORD.pack(
        1_483_228_800,
        1.05,
        1.06,
        1.04,
        1.055,
        100,
        3,
        0,
    )
    path.write_bytes(module.AFRATE_HEADER.pack(module.AFRATE_MAGIC, 1) + row)
    assert module.inspect_rates(path, 1, 0.00001) == (1_483_228_800, 1_483_228_800)


def test_inspect_rates_rejects_bad_spread(tmp_path: Path) -> None:
    path = tmp_path / "month.afrates"
    row = module.AFRATE_RECORD.pack(
        1_483_228_800, 1.05, 1.06, 1.04, 1.055, 100, 0, 0
    )
    path.write_bytes(module.AFRATE_HEADER.pack(module.AFRATE_MAGIC, 1) + row)
    with pytest.raises(module.RateImportPlanError):
        module.inspect_rates(path, 1, 0.00001)


def test_custom_symbol_override_is_explicit_and_validated() -> None:
    assert (
        module.resolve_custom_symbol(
            "AFD_EURUSD_DUKA_TSMOM_V5", "AFD_EURUSD_DUKA_TSMOM_V6"
        )
        == "AFD_EURUSD_DUKA_TSMOM_V6"
    )
    assert (
        module.resolve_custom_symbol(
            "AFD_EURUSD_DUKA_TSMOM_V5", "EURUSD_AFD_TSMOM_V6"
        )
        == "EURUSD_AFD_TSMOM_V6"
    )
    with pytest.raises(module.RateImportPlanError, match="invalid custom symbol"):
        module.resolve_custom_symbol("AFD_EURUSD_DUKA_TSMOM_V5", "EURUSD")
