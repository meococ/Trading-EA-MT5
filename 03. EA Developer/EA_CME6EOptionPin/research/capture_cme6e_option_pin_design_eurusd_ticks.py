"""Retired HYP001 capture draft retained as forensic evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-EURUSD-001"
FUTURES_ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/CME6EOPTPIN001-DESIGN-SOURCE-001/"
    "phase_01_definitions_batch_r2/phase_03_futures_reference"
)
OUTPUT_REL = Path(
    "02. AlphaFactory/data/fivepercent/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}"
)
PREREG_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    f"{HYPOTHESIS_ID}_DESIGN_ECONOMIC_PREREG.md"
)
DIRECTIONS_FILE = "futures_reference_directions.csv"
FUTURES_RECEIPT = "futures_reference_analysis_receipt.json"
OUTPUT_DIR = "ticks_once"
MANIFEST_FILE = "eurusd_tick_capture_manifest.json"
RECEIPT_FILE = "eurusd_tick_capture_receipt.json"
EXPECTED_EVENTS = 508
SYMBOL = "EURUSD"
EXPECTED_SERVER = "FivePercentOnline-Real"
WINDOW_SECONDS = 60
RETIRED_REASON = (
    "RETIRED_NO_USE: HYP001 was terminally killed for an invalid source "
    "contract before this target-capture draft was created"
)


class CaptureError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise CaptureError(f"timestamp is not UTC: {value}")
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    os.replace(temporary, path)


def select_first_valid_tick(ticks: Any, clock: datetime) -> dict[str, Any] | None:
    if ticks is None:
        return None
    threshold_msc = int(clock.timestamp() * 1000)
    for tick in ticks:
        bid = float(tick["bid"])
        ask = float(tick["ask"])
        time_msc = int(tick["time_msc"])
        if (
            time_msc >= threshold_msc
            and math.isfinite(bid)
            and math.isfinite(ask)
            and bid > 0
            and ask > 0
            and bid < ask
        ):
            return {
                "time": int(tick["time"]),
                "time_msc": time_msc,
                "time_utc": datetime.fromtimestamp(
                    time_msc / 1000, tz=timezone.utc
                ).isoformat().replace("+00:00", "Z"),
                "bid": bid,
                "ask": ask,
                "last": float(tick["last"]),
                "volume": int(tick["volume"]),
                "flags": int(tick["flags"]),
                "volume_real": float(tick["volume_real"]),
            }
    return None


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    futures_root = (workspace / FUTURES_ROOT_REL).resolve()
    output_root = (workspace / OUTPUT_REL).resolve()
    prereg_path = (workspace / PREREG_REL).resolve()
    for path in (futures_root, output_root, prereg_path):
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise CaptureError("capture path escaped workspace") from exc
    directions_path = futures_root / DIRECTIONS_FILE
    futures_receipt_path = futures_root / FUTURES_RECEIPT
    if not all(path.is_file() for path in (directions_path, futures_receipt_path, prereg_path)):
        raise CaptureError("directions, futures receipt, or economic prereg is missing")
    futures_receipt = json.loads(futures_receipt_path.read_text(encoding="ascii"))
    if (
        futures_receipt.get("verdict") != "FUTURES_REFERENCE_PASS"
        or futures_receipt.get("directional_events") != EXPECTED_EVENTS
        or futures_receipt.get("eurusd_target_authorized") is not True
        or futures_receipt.get("target_price_fields_used") != []
        or futures_receipt.get("outcome_fields_used") != []
    ):
        raise CaptureError("futures gate did not authorize the target")

    import pandas as pd

    directions = pd.read_csv(directions_path, dtype={"event_id": str})
    if len(directions) != EXPECTED_EVENTS or directions["event_id"].duplicated().any():
        raise CaptureError("frozen direction population drifted")
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / OUTPUT_DIR
    if output.exists():
        raise CaptureError("exclusive EURUSD tick root exists; rerun is forbidden")
    output.mkdir()

    import MetaTrader5 as mt5

    terminal = (
        workspace
        / "02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe"
    ).resolve()
    if not terminal.is_file() or not mt5.initialize(path=str(terminal)):
        raise CaptureError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        symbol = mt5.symbol_info(SYMBOL)
        if (
            account is None
            or account.server != EXPECTED_SERVER
            or int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO)
            or symbol is None
            or float(symbol.trade_contract_size) != 100000.0
            or not mt5.symbol_select(SYMBOL, True)
        ):
            raise CaptureError("MT5 account or EURUSD symbol identity mismatch")
        rows: list[dict[str, Any]] = []
        for event in directions.to_dict(orient="records"):
            entry_clock = parse_utc(str(event["decision_utc"]))
            exit_clock = parse_utc(str(event["expiration_utc"]))
            if exit_clock - entry_clock != timedelta(minutes=15):
                raise CaptureError(f"non-15-minute event: {event['event_id']}")
            entry_ticks = mt5.copy_ticks_range(
                SYMBOL,
                entry_clock,
                entry_clock + timedelta(seconds=WINDOW_SECONDS),
                mt5.COPY_TICKS_ALL,
            )
            exit_ticks = mt5.copy_ticks_range(
                SYMBOL,
                exit_clock,
                exit_clock + timedelta(seconds=WINDOW_SECONDS),
                mt5.COPY_TICKS_ALL,
            )
            entry_tick = select_first_valid_tick(entry_ticks, entry_clock)
            exit_tick = select_first_valid_tick(exit_ticks, exit_clock)
            rows.append(
                {
                    "event_id": event["event_id"],
                    "underlying": event["underlying"],
                    "expiration_utc": event["expiration_utc"],
                    "decision_utc": event["decision_utc"],
                    "pin_strike": float(event["pin_strike"]),
                    "reference_mid": float(event["reference_mid"]),
                    "primary_direction": event["primary_direction"],
                    "reverse_direction": event["reverse_direction"],
                    "entry_tick_count": 0 if entry_ticks is None else len(entry_ticks),
                    "exit_tick_count": 0 if exit_ticks is None else len(exit_ticks),
                    "entry_tick": entry_tick,
                    "exit_tick": exit_tick,
                    "target_valid": bool(entry_tick and exit_tick),
                }
            )
    finally:
        mt5.shutdown()

    rows_path = output / "eurusd_event_ticks.jsonl"
    with rows_path.open("x", encoding="ascii", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
    valid = sum(bool(row["target_valid"]) for row in rows)
    manifest = {
        "schema_version": "cme6e_option_pin_eurusd_tick_capture.v1",
        "created_at_utc": utc_now(),
        "status": "TICKS_CAPTURED_ANALYSIS_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "server": EXPECTED_SERVER,
        "account_trade_mode": "DEMO",
        "symbol": SYMBOL,
        "contract_size": 100000.0,
        "window_seconds": WINDOW_SECONDS,
        "frozen_events": EXPECTED_EVENTS,
        "target_valid_events": valid,
        "target_coverage": valid / EXPECTED_EVENTS,
        "bindings": {
            "prereg_sha256": sha256_file(prereg_path),
            "directions_sha256": sha256_file(directions_path),
            "futures_receipt_sha256": sha256_file(futures_receipt_path),
            "event_ticks_sha256": sha256_file(rows_path),
        },
        "target_price_fields_used": ["time", "time_msc", "bid", "ask", "last", "volume", "flags", "volume_real"],
        "outcome_fields_used": [],
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    manifest_path = output / MANIFEST_FILE
    write_json(manifest_path, manifest)
    receipt = {
        "schema_version": "cme6e_option_pin_eurusd_tick_capture_receipt.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "status": "TICKS_CAPTURED_ANALYSIS_PENDING",
        "frozen_events": EXPECTED_EVENTS,
        "target_valid_events": valid,
        "target_coverage": valid / EXPECTED_EVENTS,
        "manifest_sha256": sha256_file(manifest_path),
        "event_ticks_sha256": sha256_file(rows_path),
        "economics_authorized": valid / EXPECTED_EVENTS >= 0.95,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    receipt_path = output_root / RECEIPT_FILE
    write_json(receipt_path, receipt)
    return receipt_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    # Fail closed even if an operator invokes the retired script directly.
    print(RETIRED_REASON)
    return 2

    # Unreachable forensic implementation retained to preserve the exact draft.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        path = execute(args.workspace)
        receipt = json.loads(path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN_EURUSD_TICKS_CAPTURED "
            f"valid={receipt['target_valid_events']}/{receipt['frozen_events']} "
            f"economics_authorized={receipt['economics_authorized']}"
        )
        print(f"RECEIPT {path}")
        return 0
    except CaptureError as exc:
        print(f"CME6EOPTPIN_EURUSD_TICK_CAPTURE_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
