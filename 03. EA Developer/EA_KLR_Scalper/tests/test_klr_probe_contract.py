from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pandas as pd


PACKAGE = Path(__file__).resolve().parents[1]
PROBE = PACKAGE / "research" / "klr_usd_pdraid_offline_probe.py"
PREREG = PACKAGE / "research" / "HYP-KLR-USD-PDLRAID-M5-XAU-001_FROZEN_PREREG.md"
USD_DATA = PACKAGE / "research" / "data" / "DTWEXBGS.csv"


def load_probe():
    spec = importlib.util.spec_from_file_location("klr_probe", PROBE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_frozen_inputs_and_external_data_hash() -> None:
    assert PREREG.is_file()
    assert USD_DATA.is_file()
    assert hashlib.sha256(USD_DATA.read_bytes()).hexdigest().upper() == (
        "15B46514271F0E8D5D721CFEE2FA5A994DB56982E042B55F66F23750B70E8951"
    )


def test_usd_gate_uses_two_business_day_lag() -> None:
    probe = load_probe()
    data = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(["2024-01-04", "2024-01-05", "2024-01-08"]),
            "usd_change": [-0.2, 0.3, 9.9],
        }
    )
    # Monday 2024-01-08 may only use Thursday 2024-01-04.
    assert probe.usd_change_for_trade_date(data, pd.Timestamp("2024-01-08").date()) == -0.2
    # Wednesday may use Monday; no same-day observation is visible.
    assert probe.usd_change_for_trade_date(data, pd.Timestamp("2024-01-10").date()) == 9.9


def test_probe_surface_is_single_frozen_variant_and_no_file_common() -> None:
    probe = load_probe()
    source = PROBE.read_text(encoding="utf-8")
    assert probe.DISPLACEMENT_ATR == 1.0
    assert probe.DISPLACEMENT_BARS == 4
    assert probe.RETEST_BARS == 6
    assert probe.TARGET_R == 2.0
    assert probe.COST_POINTS == 35.0
    assert probe.LONDON == (120, 300)
    assert probe.NEW_YORK == (510, 660)
    assert '"file_common_allowed": False' in source
    assert "parameter grid" not in source.lower()
