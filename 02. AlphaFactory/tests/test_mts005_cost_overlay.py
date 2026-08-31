from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "research" / "mts005_cost_overlay.py"
CONTRACT = (
    ROOT.parent
    / "03. EA Developer"
    / "EA_MultiAssetTSMOMD1V5"
    / "research"
    / "HYP-MULTI-TSMOM-D1-005_COST_CONTRACT.json"
)
SPEC = importlib.util.spec_from_file_location("mts005_cost_overlay", TOOL)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


JOURNAL = """
MTS005_FINANCE_EXPOSURE epoch=1704153600 day=20240102 reason=daily_open fx_usd=100000.00 xau_usd=200000.00 btc_usd=0.00
MTS005_FINANCE_EXPOSURE epoch=1704240000 day=20240103 reason=daily_open fx_usd=100000.00 xau_usd=200000.00 btc_usd=0.00
MTS005_DEAL_COST epoch=1704153600 deal=1 symbol=AFD_EURUSD_DUKA_TSMOM_V5 class=FX entry=0 type=0 volume=1.00000000 price=1.10000000 spread_points=2 one_spread_cost_usd=10.00000000 native_profit=0.00000000 native_swap=0.00000000 native_commission=-2.00000000
MTS005_DEAL_COST epoch=1704240000 deal=2 symbol=AFD_XAUUSD_DUKA_TSMOM_V5 class=XAU entry=1 type=1 volume=1.00000000 price=2000.00000000 spread_points=20 one_spread_cost_usd=20.00000000 native_profit=100.00000000 native_swap=-1.00000000 native_commission=0.00000000
MTS005_ECON_TELEMETRY ticks=200 deal_profit=100.00 deal_swap=-1.00 deal_commission=-2.00 native_net=97.00
"""


def load_contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_and_bound_source_receipts_are_valid() -> None:
    contract = load_contract()
    module.validate_contract(contract)
    verified = module.verify_source_receipts(contract, CONTRACT)
    assert len(verified) == 5


def test_calculation_reconciles_native_costs_and_applies_frozen_base() -> None:
    result = module.calculate(
        JOURNAL,
        {"net_profit": 97.0},
        load_contract(),
        date(2024, 1, 1),
        date(2024, 1, 4),
    )
    costs = result["deal_costs"]
    assert costs["deal_count"] == 2
    assert costs["expected_base_commission_by_class_usd"]["fx"] == 2.0
    assert costs["expected_base_commission_by_class_usd"]["xau"] == 2.0
    base = result["scenarios"]["base"]
    assert base["commission_shortfall_usd"] == 2.0
    assert base["extra_slippage_usd"] == 7.5
    assert base["adjusted_net_usd"] < result["pre_controlled_financing_net_usd"]
    assert result["scenarios"]["severe"]["adjusted_net_usd"] < base["adjusted_net_usd"]


def test_conflicting_duplicate_deal_fails_closed() -> None:
    conflict = JOURNAL.replace(
        "MTS005_ECON_TELEMETRY",
        "MTS005_DEAL_COST epoch=1704153600 deal=1 symbol=AFD_EURUSD_DUKA_TSMOM_V5 class=FX entry=0 type=0 volume=2.00000000 price=1.10000000 spread_points=2 one_spread_cost_usd=20.00000000 native_profit=0.00000000 native_swap=0.00000000 native_commission=-4.00000000\nMTS005_ECON_TELEMETRY",
    )
    with pytest.raises(module.CostOverlayError, match="conflicting duplicate"):
        module.parse_deals(conflict)


def test_aggregate_mismatch_fails_closed() -> None:
    with pytest.raises(module.CostOverlayError, match="not reconcile"):
        module.calculate(
            JOURNAL.replace("deal_profit=100.00", "deal_profit=99.00"),
            {"net_profit": 96.0},
            load_contract(),
            date(2024, 1, 1),
            date(2024, 1, 4),
        )
