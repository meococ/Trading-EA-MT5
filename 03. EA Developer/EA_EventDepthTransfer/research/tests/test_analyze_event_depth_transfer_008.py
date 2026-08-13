from __future__ import annotations

import csv
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_event_depth_transfer_009.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_009_analyzer", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


FIELDS = [
    "status", "role", "event_id", "event_utc_msc", "entry_target_msc",
    "exit_target_msc", "entry_tick_msc", "exit_tick_msc", "lots",
    "net_base_usd", "net_x1_5_usd", "net_x2_usd", "source_direction", "direction",
    "raw_mid_pnl_usd", "executable_pnl_usd", "commission_usd",
    "dynamic_slippage_pips", "pip_value_per_lot", "entry_spread_pips",
    "prior_10_entry_spread_median_pips", "complete_cost_usd",
]


def write_ledger(path: Path, role: str, *, all_negative: bool = False) -> None:
    start = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index in range(329):
            zero = index >= 318
            entry_target = start + index * 86_400_000
            value = -1.0 if all_negative or index % 3 == 0 else 2.0
            raw = value + 0.4
            writer.writerow({
                "status": "SKIP_ZERO" if zero else "CLOSED", "role": role,
                "event_id": f"EVT{index + 1:04d}", "event_utc_msc": entry_target,
                "entry_target_msc": entry_target, "exit_target_msc": entry_target + 60_000,
                "entry_tick_msc": 0 if zero else entry_target,
                "exit_tick_msc": 0 if zero else entry_target + 60_000,
                "lots": 0 if zero else 0.1,
                "net_base_usd": 0 if zero else value,
                "net_x1_5_usd": 0 if zero else value - 0.2,
                "net_x2_usd": 0 if zero else value - 0.4,
                "source_direction": 0 if zero else 1,
                "direction": 0 if zero else (1 if role == "PRIMARY" else -1),
                "raw_mid_pnl_usd": 0 if zero else raw,
                "executable_pnl_usd": 0 if zero else raw,
                "commission_usd": 0 if zero else 0.4,
                "dynamic_slippage_pips": 0,
                "pip_value_per_lot": 10,
                "entry_spread_pips": 1,
                "prior_10_entry_spread_median_pips": 1,
                "complete_cost_usd": 0 if zero else 0.4,
            })


def test_role_summary_accepts_exact_329_accounting_and_boundaries(tmp_path: Path) -> None:
    path = tmp_path / "primary.csv"
    write_ledger(path, "PRIMARY")
    result = MODULE.role_summary(path, "PRIMARY")
    assert result["status_counts"] == {"CLOSED": 318, "SKIP_ZERO": 11}
    assert result["base"]["trades"] == 318
    assert result["top_5pct"]["count"] == 16


def test_all_negative_ledger_fails_concentration_without_crashing(tmp_path: Path) -> None:
    path = tmp_path / "primary.csv"
    write_ledger(path, "PRIMARY", all_negative=True)
    result = MODULE.role_summary(path, "PRIMARY")
    assert result["top_5pct"]["gross_profit_share"] == float("inf")


def test_meta_requires_source_table_counts_and_runtime_integrity(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    payload = {
        "role": "PRIMARY", "source_sha256": MODULE.EXPECTED_SOURCE_HASH,
        "table_sha256": MODULE.EXPECTED_TABLE_HASH, "events": 329,
        "accounted": 329, "completed": 318, "zero_source": 11,
        "runtime_failed": False, "max_concurrent": 1,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert MODULE.validate_meta(path, "PRIMARY")["payload"]["completed"] == 318
    payload["zero_source"] = 10
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        MODULE.validate_meta(path, "PRIMARY")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid zero-source count was accepted")
