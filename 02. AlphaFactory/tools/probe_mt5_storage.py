#!/usr/bin/env python3
"""Read back MT5 terminal storage paths without placing orders."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5


def drive(path: str) -> str:
    return os.path.splitdrive(os.path.abspath(path))[0].upper()


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--required-drive", default="D:")
    parser.add_argument("--process-appdata", type=Path)
    args = parser.parse_args()

    terminal = args.terminal.resolve()
    output = args.output.resolve()
    required_drive = args.required_drive.rstrip("\\/").upper()

    process_appdata = args.process_appdata.resolve() if args.process_appdata else None
    if process_appdata:
        process_appdata.mkdir(parents=True, exist_ok=True)
        os.environ["APPDATA"] = str(process_appdata)

    if drive(str(terminal)) != required_drive:
        raise SystemExit(f"terminal is not on required drive {required_drive}: {terminal}")

    initialized = mt5.initialize(path=str(terminal), timeout=60_000, portable=True)
    if not initialized:
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        info = mt5.terminal_info()
        if info is None:
            raise SystemExit(f"MT5 terminal_info failed: {mt5.last_error()}")

        data_path = str(info.data_path)
        commondata_path = str(info.commondata_path)
        checks = {
            "terminal_on_required_drive": drive(str(terminal)) == required_drive,
            "data_path_on_required_drive": drive(data_path) == required_drive,
            "commondata_path_on_required_drive": drive(commondata_path) == required_drive,
        }
        payload = {
            "schema_version": "alphafactory_mt5_storage_readback.v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "terminal": str(terminal),
            "required_drive": required_drive,
            "portable": True,
            "process_appdata": str(process_appdata) if process_appdata else None,
            "terminal_info": {
                "build": int(info.build),
                "name": str(info.name),
                "company": str(info.company),
                "connected": bool(info.connected),
                "trade_allowed": bool(info.trade_allowed),
                "data_path": data_path,
                "commondata_path": commondata_path,
            },
            "checks": checks,
            "passed": all(checks.values()),
        }
        write_json_atomic(output, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0 if payload["passed"] else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
