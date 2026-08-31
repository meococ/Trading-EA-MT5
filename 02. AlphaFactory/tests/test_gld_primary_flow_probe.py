from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]

# EA_GLDFlowPulse was parked to 00. Old File/EA_Archive/ on 2026-08-31 (Owner
# directive: keep only the essential core). Look for the probe on the live
# shelf first, then in the graveyard, and skip rather than fail if it is gone
# entirely -- a parked package is a housekeeping state, not a test regression.
_REL = Path("EA_GLDFlowPulse") / "research" / "gld_primary_flow_offline_probe.py"
_CANDIDATES = (
    ROOT / "03. EA Developer" / _REL,
    ROOT / "00. Old File" / "EA_Archive" / _REL,
)
MODULE_PATH = next((p for p in _CANDIDATES if p.is_file()), None)

if MODULE_PATH is None:
    pytest.skip(
        "gld_primary_flow_offline_probe.py not found on the shelf or in "
        "00. Old File/EA_Archive/; EA_GLDFlowPulse is parked.",
        allow_module_level=True,
    )

SPEC = importlib.util.spec_from_file_location("gld_primary_flow_probe", MODULE_PATH)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)

def test_derived_shares_snap_to_official_basket() -> None:
    assert probe.derive_shares(10_000.0, 0.001) == 10_000_000
    assert probe.derive_shares(999.96, 0.01) == 100_000


def test_flow_events_ignore_zero_and_use_pretrain_warmup() -> None:
    rows = [
        probe.FlowRow(date(2021, 12, 31), 100_000_000),
        probe.FlowRow(date(2022, 1, 3), 100_000_000),
        probe.FlowRow(date(2022, 1, 4), 100_100_000),
        probe.FlowRow(date(2022, 1, 5), 100_000_000),
    ]
    assert probe.build_flow_events(rows) == [
        (date(2022, 1, 4), 100_000, 1),
        (date(2022, 1, 5), -100_000, -1),
    ]


def test_bind_events_uses_strict_next_trading_day() -> None:
    entries = {date(2022, 1, 7): 10, date(2022, 1, 10): 20}
    events = [(date(2022, 1, 7), 100_000, 1)]
    bound = probe.bind_events(events, entries)
    assert len(bound) == 1
    assert bound[0].signal_date == date(2022, 1, 10)
    assert bound[0].entry_idx == 20


def test_scenario_cost_stress_is_monotone() -> None:
    trades = [
        probe.Trade("challenger", "2022-01-01", "2022-01-03", 1, 100_000, "a", "b", 1000.0, 1.5, 0.1, "TARGET"),
        probe.Trade("challenger", "2022-01-02", "2022-01-04", -1, -100_000, "a", "b", 1000.0, -1.0, 0.1, "STOP"),
    ]
    x1 = probe.scenario_values(trades, 1.0)
    x15 = probe.scenario_values(trades, 1.5)
    x2 = probe.scenario_values(trades, 2.0)
    assert np.all(x1 > x15)
    assert np.all(x15 > x2)


def test_workbook_hash_and_holdout_payload_guard() -> None:
    rows, audit = probe.load_flow_rows(probe.WORKBOOK)
    assert rows
    assert max(row.archive_date for row in rows) <= date(2024, 12, 31)
    assert audit["holdout_payload_cells_accessed"] == 0
