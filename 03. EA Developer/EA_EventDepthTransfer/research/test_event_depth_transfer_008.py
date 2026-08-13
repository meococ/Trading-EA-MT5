from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATOR = Path(__file__).with_name("generate_event_depth_transfer_008_table.py")
EA_PATH = ROOT / "03. EA Developer/EA_EventDepthTransfer/EA_EventDepthTransfer.mq5"
PREREG_PATH = Path(__file__).with_name(
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009_FROZEN_ECONOMIC_PREREG.md"
)
MANIFEST_PATH = Path(__file__).with_name(
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009_COST_SOURCE_MANIFEST.json"
)
CONTRACT_PATH = ROOT / "03. EA Developer/EA_EventDepthTransfer/ALPHAFACTORY_EA_CONTRACT.json"
ANALYZER_PATH = Path(__file__).with_name("analyze_event_depth_transfer_009.py")
PRIMARY_TASK_PATH = Path(__file__).with_name(
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009_PRIMARY_TASK.json"
)
REVERSE_TASK_PATH = Path(__file__).with_name(
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009_REVERSE_TASK.json"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("depth_table_generator", GENERATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_source_counts_and_table_hash() -> None:
    module = load_generator()
    rows = module.load_rows()
    directions = [int(row["direction"]) for row in rows]
    assert len(rows) == 329
    assert (directions.count(1), directions.count(-1), directions.count(0)) == (162, 156, 11)
    assert hashlib.sha256(module.canonical_table(rows)).hexdigest().upper() in module.render(rows)
    assert module.EXPECTED_SOURCE_SHA256 == "3B3B0F4CF85FD733B26DE0CA84F890265C94693DC7A58170507491985B2687B8"


def test_server_clock_offsets_and_ordering() -> None:
    rows = load_generator().load_rows()
    assert {int(row["offset_h"]) for row in rows} == {2, 3}
    assert all(
        int(row["server_msc"]) - int(row["utc_msc"]) == int(row["offset_h"]) * 3_600_000
        for row in rows
    )
    assert all(int(rows[i]["server_msc"]) < int(rows[i + 1]["server_msc"]) for i in range(328))


def test_mql_contract_is_tick_exact_and_has_no_rescue_inputs() -> None:
    source = EA_PATH.read_text(encoding="utf-8")
    assert "tick.time_msc" in source
    assert "AF_ENTRY_DELAY_MSC=60000" in source
    assert "AF_EXIT_DELAY_MSC=120000" in source
    assert "InpReverseComparator" in source
    assert "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009" in source
    assert "DATA_EPOCH_D0_SERIES_PROOF symbol=%s" in source
    assert "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)" in source
    assert "InpRiskPercent" in source and "InpSizingStopPips" in source
    assert "trade.PositionClose" in source
    forbidden = ("InpSignalThreshold", "InpSession", "InpStopLoss", "InpTakeProfit", "InpTrailing")
    assert all(token not in source for token in forbidden)


def test_hyp009_package_identity_and_source_binding_are_consistent() -> None:
    prereg = PREREG_PATH.read_text(encoding="utf-8-sig")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert prereg.startswith("# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009")
    assert "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-007" in prereg
    assert manifest["hypothesis_id"] == "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009"
    assert manifest["source_ledger_sha256"] == load_generator().EXPECTED_SOURCE_SHA256
    assert contract["inputs"]["InpHypothesisId"] == "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009"
    assert contract["inputs"]["InpMagic"] == 8132609
    assert contract["execution_profile"]["economic_claims_authorized"] is False


def test_analyzer_handles_no_positive_profit_without_division_by_zero() -> None:
    source = ANALYZER_PATH.read_text(encoding="utf-8")
    assert "if positive_total > 0" in source
    assert "else math.inf" in source
    assert "positive_values[:top_count]" in source
    assert "731 / 7" in source


def test_ea_and_analyzer_fail_closed_on_position_cost_and_reverse_mismatch() -> None:
    ea = EA_PATH.read_text(encoding="utf-8")
    analyzer = ANALYZER_PATH.read_text(encoding="utf-8")
    assert "if(g_runtime_failed || position_count!=1 || ticket==0)" in ea
    assert "if(g_runtime_failed)\n         return;" in ea
    assert "complete cost mismatch" in analyzer
    assert "commission mismatch" in analyzer
    assert "PRIMARY/REVERSE sign mismatch" in analyzer
    assert "PRIMARY/REVERSE tick-boundary mismatch" in analyzer


def test_terminal_mapping_and_both_run_tasks_are_revoked() -> None:
    ea = EA_PATH.read_text(encoding="utf-8")
    primary = json.loads(PRIMARY_TASK_PATH.read_text(encoding="utf-8"))
    reverse = json.loads(REVERSE_TASK_PATH.read_text(encoding="utf-8"))
    assert "AF_MAPPING_TERMINAL=true" in ea
    assert "terminal frozen mapping; rerun forbidden" in ea
    assert primary["execution_authorized"] is False
    assert reverse["execution_authorized"] is False
