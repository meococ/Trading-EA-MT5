"""Generate the outcome-blind DOL UI TRAIN compile-time table."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer/EA_DOLUISeasonalResidual"
SOURCE = (
    ROOT
    / "02. AlphaFactory/data/dol_ui/HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001"
    / "dol_ui_seasonal_residual_2018_20260806.csv"
)
OUTPUT = PACKAGE / "resources/dolui_001_train_table.mqh"
MANIFEST = PACKAGE / "research/HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_TRAIN_TABLE_MANIFEST.json"
CLOCK_MODULE = ROOT / "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
EXPECTED_SOURCE_SHA256 = "3CD5D03DC85309724C5E3E616223657ACBA8DF86D4722F4A7EDAAB068C9009BA"
SOURCE_RECEIPT_SHA256 = "58AF5CC103F8CFC2CD8D906818736C562E090EC3D3CD361C13903E01E06DB65C"
EXPECTED_COUNTS = {"events": 260, "buy": 101, "sell": 157, "flat": 2}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_clock_module():
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", CLOCK_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical FivePercent clock module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"release timestamp lacks UTC offset: {value}")
    return parsed.astimezone(timezone.utc)


def utc_to_server(utc: datetime, clock) -> tuple[datetime, int]:
    candidates: list[tuple[datetime, int]] = []
    for offset in (2, 3):
        server = (utc + timedelta(hours=offset)).replace(tzinfo=None)
        if clock.server_to_utc(server).replace(tzinfo=timezone.utc) == utc:
            candidates.append((server, offset))
    if len(candidates) != 1:
        raise ValueError(f"ambiguous FivePercent UTC->server mapping: {utc.isoformat()}")
    return candidates[0]


def naive_epoch_seconds(value: datetime) -> int:
    return int(value.replace(tzinfo=timezone.utc).timestamp())


def ceil_next_hour(value: datetime) -> datetime:
    if value.tzinfo is not None:
        raise ValueError("server time must be naive")
    floor = value.replace(minute=0, second=0, microsecond=0)
    return floor + timedelta(hours=1)


def load_rows() -> list[dict[str, int | str]]:
    actual_hash = sha256_file(SOURCE)
    if actual_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError(f"source SHA256 mismatch: {actual_hash}")
    clock = load_clock_module()
    rows: list[dict[str, int | str]] = []
    with SOURCE.open("r", encoding="utf-8", newline="") as stream:
        for raw in csv.DictReader(stream):
            if raw["stage"] != "TRAIN_SOURCE":
                continue
            utc = parse_utc(raw["release_utc"])
            server, offset = utc_to_server(utc, clock)
            decision_open = ceil_next_hour(server)
            entry_target = decision_open + timedelta(hours=1)
            exit_target = entry_target + timedelta(hours=4)
            direction = {"BUY_EURUSD": 1, "SELL_EURUSD": -1, "FLAT": 0}[raw["direction"]]
            residual = int(raw["seasonal_residual"]) if raw["seasonal_residual"] else 0
            availability = 1 if raw["source_availability"] == "SIGNAL_USABLE" else 0
            rows.append(
                {
                    "event_id": f"DOLUI{len(rows) + 1:04d}",
                    "release_utc": int(utc.timestamp()),
                    "release_server": naive_epoch_seconds(server),
                    "decision_open": naive_epoch_seconds(decision_open),
                    "entry_target": naive_epoch_seconds(entry_target),
                    "exit_target": naive_epoch_seconds(exit_target),
                    "offset_h": offset,
                    "residual": residual,
                    "direction": direction,
                    "availability": availability,
                }
            )
    validate_rows(rows)
    return rows


def validate_rows(rows: list[dict[str, int | str]]) -> None:
    directions = [int(row["direction"]) for row in rows]
    counts = {
        "events": len(rows),
        "buy": sum(value > 0 for value in directions),
        "sell": sum(value < 0 for value in directions),
        "flat": sum(value == 0 for value in directions),
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"frozen TRAIN counts changed: {counts}")
    if [row["event_id"] for row in rows] != [f"DOLUI{i:04d}" for i in range(1, 261)]:
        raise ValueError("event identity sequence mismatch")
    if any(int(rows[i]["release_server"]) >= int(rows[i + 1]["release_server"]) for i in range(259)):
        raise ValueError("server release clocks are not strictly increasing")
    for row in rows:
        if int(row["release_server"]) + 1800 != int(row["decision_open"]):
            raise ValueError("release-to-decision geometry changed")
        if int(row["decision_open"]) + 3600 != int(row["entry_target"]):
            raise ValueError("decision-to-entry geometry changed")
        if int(row["entry_target"]) + 14400 != int(row["exit_target"]):
            raise ValueError("entry-to-exit geometry changed")
        if int(row["offset_h"]) not in (2, 3):
            raise ValueError("invalid FivePercent offset")
        release_server = datetime.fromtimestamp(int(row["release_server"]), tz=timezone.utc)
        if release_server.weekday() not in (2, 3):
            raise ValueError("TRAIN source contains a non-Wednesday/Thursday release")
        if int(row["availability"]) == 0 and (int(row["direction"]) != 0 or int(row["residual"]) != 0):
            raise ValueError("unavailable source row is not frozen FLAT")


def canonical_table(rows: list[dict[str, int | str]]) -> bytes:
    return "".join(
        f"{row['event_id']},{row['release_utc']},{row['release_server']},"
        f"{row['decision_open']},{row['entry_target']},{row['exit_target']},"
        f"{row['residual']},{row['direction']},{row['availability']}\n"
        for row in rows
    ).encode("utf-8")


def mql_array(name: str, kind: str, values: list[str]) -> str:
    return f"const {kind} {name}[AF_DOLUI_EVENT_COUNT]={{\n   " + ",\n   ".join(values) + "\n};\n"


def render(rows: list[dict[str, int | str]]) -> str:
    table_hash = sha256_bytes(canonical_table(rows))
    return "".join(
        [
            "// Generated by research/generate_dolui_train_table.py; do not hand-edit.\n",
            "#ifndef DOLUI_001_TRAIN_TABLE_MQH\n#define DOLUI_001_TRAIN_TABLE_MQH\n\n",
            "#define AF_DOLUI_EVENT_COUNT 260\n",
            f'const string AF_DOLUI_SOURCE_SHA256="{EXPECTED_SOURCE_SHA256}";\n',
            f'const string AF_DOLUI_SOURCE_RECEIPT_SHA256="{SOURCE_RECEIPT_SHA256}";\n',
            f'const string AF_DOLUI_TABLE_SHA256="{table_hash}";\n\n',
            mql_array("AF_DOLUI_EVENT_ID", "string", [f'"{row["event_id"]}"' for row in rows]),
            "\n",
            mql_array("AF_DOLUI_RELEASE_UTC", "long", [str(row["release_utc"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_RELEASE_SERVER", "long", [str(row["release_server"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_DECISION_OPEN", "long", [str(row["decision_open"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_ENTRY_TARGET", "long", [str(row["entry_target"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_EXIT_TARGET", "long", [str(row["exit_target"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_RESIDUAL", "long", [str(row["residual"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_DIRECTION", "int", [str(row["direction"]) for row in rows]),
            "\n",
            mql_array("AF_DOLUI_AVAILABLE", "int", [str(row["availability"]) for row in rows]),
            "\n#endif\n",
        ]
    )


def main() -> None:
    rows = load_rows()
    rendered = render(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    manifest = {
        "schema_version": "alphafactory.dol_ui_train_table_manifest.v1",
        "hypothesis_id": "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001",
        "source_csv": SOURCE.relative_to(ROOT).as_posix(),
        "source_csv_sha256": EXPECTED_SOURCE_SHA256,
        "source_receipt_sha256": SOURCE_RECEIPT_SHA256,
        "table_include": OUTPUT.relative_to(ROOT).as_posix(),
        "table_include_sha256": sha256_file(OUTPUT),
        "canonical_table_sha256": sha256_bytes(canonical_table(rows)),
        "counts": EXPECTED_COUNTS,
        "price_outcomes_read": 0,
        "economic_metrics_computed": 0,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "DOLUI001_TRAIN_TABLE_OK "
        f"events={len(rows)} source_sha256={EXPECTED_SOURCE_SHA256} "
        f"table_sha256={manifest['canonical_table_sha256']}"
    )


if __name__ == "__main__":
    main()
