from __future__ import annotations

import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE / "EA_DOLUISeasonalResidual.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
TABLE = PACKAGE / "resources/dolui_001_train_table.mqh"


def test_contract_is_exact_train_model0_surface() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    profile = contract["execution_profile"]
    assert profile["timeframe"] == "H1"
    assert profile["expected_symbol"] == "EURUSD"
    assert profile["closed_bar_only"] is True
    assert profile["promotion_eligible"] is False
    assert contract["inputs"]["InpExposurePercent"] == 0.25
    assert contract["inputs"]["InpSizingPips"] == 40.0


def test_ea_has_one_horizon_no_price_filters_and_hard_source_binding() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "AF_DOLUI_ENTRY_TARGET[event_index]+14400" not in source
    assert "AF_DOLUI_ENTRY_TARGET" in source
    assert "AF_DOLUI_EXIT_TARGET" in source
    assert "ClosedDecisionBarMatches" in source
    assert "AF_DOLUI_TABLE_SHA256" in source
    assert "AF_DOLUI_SOURCE_SHA256" in source
    forbidden = ("InpStopLoss", "InpTakeProfit", "InpSpreadGate", "iATR(", "iRSI(")
    assert all(token not in source for token in forbidden)


def test_generated_table_is_train_only_and_hash_bound() -> None:
    table = TABLE.read_text(encoding="utf-8")
    assert "#define AF_DOLUI_EVENT_COUNT 260" in table
    assert "20377DAA5449E0C10D67620768FA127B8FAEF5F49DDC802AF78DD8848F8C5A05" in table
    assert "3CD5D03DC85309724C5E3E616223657ACBA8DF86D4722F4A7EDAAB068C9009BA" in table
