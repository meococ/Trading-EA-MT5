from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATOR = Path(__file__).with_name("generate_event_depth_transfer_006_table.py")
EA_PATH = ROOT / "03. EA Developer/EA_EventDepthTransfer/EA_EventDepthTransfer.mq5"


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
    assert "InpRiskPercent" in source and "InpSizingStopPips" in source
    assert "trade.PositionClose" in source
    forbidden = ("InpSignalThreshold", "InpSession", "InpStopLoss", "InpTakeProfit", "InpTrailing")
    assert all(token not in source for token in forbidden)

