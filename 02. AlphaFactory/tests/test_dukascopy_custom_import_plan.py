from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "dukascopy_custom_import_plan.py"
)
SPEC = importlib.util.spec_from_file_location("dukascopy_custom_import_plan", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
plan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plan
SPEC.loader.exec_module(plan)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_build_one_day_hash_bound_plan(tmp_path: Path) -> None:
    contract = {
        "schema_version": "alphafactory_dukascopy_source_contract.v2",
        "authority": "SOURCE_DATA_ONLY_NO_PERFORMANCE",
        "economics_authorized": False,
        "symbols": [
            {
                "source_symbol": "EURUSD",
                "origin_symbol": "EURUSD",
                "custom_symbol": "AFD_EURUSD_TEST",
                "digits": 5,
                "history_from": "2018-01-08",
                "history_to_exclusive": "2018-01-09",
            }
        ],
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract) + "\n", encoding="utf-8")
    contract_sha = sha(contract_path)
    data = tmp_path / "data"
    binary = data / "EURUSD" / "decoded" / "2018" / "01" / "2018-01-08.afdticks"
    binary.parent.mkdir(parents=True)
    ticks = [
        (1_515_427_200_001, 1.20, 1.2001),
        (1_515_427_260_001, 1.21, 1.2101),
    ]
    binary.write_bytes(
        struct.pack("<QQ", plan.AFD_MAGIC, len(ticks))
        + b"".join(struct.pack("<qdd", *tick) for tick in ticks)
    )
    binary_sha = sha(binary)
    receipt_path = data / "EURUSD" / "receipts" / "2018" / "01" / "2018-01-08.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": "alphafactory_dukascopy_bi5_day.v2",
                "authority": "SOURCE_DATA_ONLY_NO_PERFORMANCE",
                "status": "PASS",
                "symbol": "EURUSD",
                "date_utc": "2018-01-08",
                "source_contract": {"sha256": contract_sha},
                "binary": {
                    "count": 2,
                    "sha256": binary_sha,
                    "first_time_msc": ticks[0][0],
                    "last_time_msc": ticks[-1][0],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    terminal = tmp_path / "terminal"
    output_receipt = tmp_path / "plan_receipt.json"
    args = argparse.Namespace(
        contract=contract_path,
        contract_sha256=contract_sha,
        data_root=data,
        terminal_data_root=terminal,
        symbol="EURUSD",
        receipt=output_receipt,
    )
    assert plan.build(args) == 0
    result = json.loads(output_receipt.read_text(encoding="utf-8"))
    assert result["day_count"] == 1
    assert result["tick_count"] == 2
    assert result["m1_bar_count"] == 2
    active_plan = Path(result["active_plan_path"])
    lines = active_plan.read_text(encoding="ascii").splitlines()
    assert lines[0].startswith("META;alphafactory_custom_tick_import_plan.v1;AFD_EURUSD_TEST")
    assert lines[1].startswith("DAY;2018-01-08;")
    assert lines[-1] == "END"
    linked = terminal / "MQL5" / "Files" / "AlphaFactoryCustomImport" / "HYP-MTS004-EURUSD" / "2018-01-08.afdticks"
    assert linked.is_file()
    assert sha(linked) == binary_sha
