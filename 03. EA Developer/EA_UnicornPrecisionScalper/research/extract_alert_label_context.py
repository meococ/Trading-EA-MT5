#!/usr/bin/env python3
"""Build bounded, no-future MTF review packets for Unicorn alert labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import MetaTrader5 as mt5


TIMEFRAMES = {
    "m5": (mt5.TIMEFRAME_M5, 48, timedelta(minutes=5)),
    "m15": (mt5.TIMEFRAME_M15, 32, timedelta(minutes=15)),
    "h4": (mt5.TIMEFRAME_H4, 16, timedelta(hours=4)),
    "d1": (mt5.TIMEFRAME_D1, 12, timedelta(days=1)),
}
LABEL_COLUMNS = {
    "label_true_sweep_liquidity",
    "label_true_displacement",
    "label_true_mss_bos_close",
    "label_true_breaker_valid",
    "label_fvg_fresh_unfilled",
    "label_micro_confirm_present",
    "label_trade_quality_accept",
    "reject_reason",
    "reviewer_id",
    "label_time_utc",
}
FORBIDDEN_OUTPUT_KEYS = {
    "pnl",
    "profit",
    "loss",
    "mfe",
    "mae",
    "forward_return",
    "fill_result",
    "trade_result",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def storage_inventory(root: Path) -> dict[str, object]:
    resolved = root.resolve()
    digest = hashlib.sha256()
    files = [] if not root.is_dir() else sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: str(path).lower(),
    )
    total_bytes = 0
    for path in files:
        stat = path.stat()
        total_bytes += stat.st_size
        relative = path.relative_to(root).as_posix()
        digest.update(f"{relative}|{stat.st_size}|{stat.st_mtime_ns}\n".encode())
    return {
        "root": str(resolved),
        "exists": root.is_dir(),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "metadata_sha256": digest.hexdigest().upper(),
    }


def parse_decision_time(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%Y.%m.%d %H:%M:%S")
    return parsed.replace(tzinfo=timezone.utc)


def read_casebook(path: Path, expected_source_sha256: str) -> list[dict[str, str]]:
    expected_source_sha256 = expected_source_sha256.strip().upper()
    if not re.fullmatch(r"[A-F0-9]{64}", expected_source_sha256):
        raise ValueError("expected source SHA256 must be exactly 64 hex characters")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {
            "schema_version",
            "source_contract_id",
            "source_sha256",
            "event_id",
            "decision_time_utc",
            *LABEL_COLUMNS,
        }
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "casebook missing required columns: " + ", ".join(sorted(missing))
            )
        rows = list(reader)
    if len(rows) != 200:
        raise ValueError(f"expected exactly 200 sealed rows; found {len(rows)}")
    event_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if row.get("schema_version") != "alert_first_casebook.v1":
            raise ValueError(f"row {index} schema mismatch")
        if row.get("source_contract_id") != "UPS_ALERT_FIRST_CASEBOOK_V1_3":
            raise ValueError(f"row {index} source contract mismatch")
        if (row.get("source_sha256") or "").strip().upper() != expected_source_sha256:
            raise ValueError(f"row {index} source SHA256 mismatch")
        if any((row.get(column) or "").strip() for column in LABEL_COLUMNS):
            raise ValueError(f"row {index} contains a label before review")
        event_id = (row.get("event_id") or "").strip()
        if not event_id or event_id in event_ids:
            raise ValueError(f"row {index} has missing or duplicate event_id")
        event_ids.add(event_id)
        parse_decision_time(row["decision_time_utc"])
    return rows


def compact_bars(
    rates: object,
    server_information_cutoff: datetime,
    bar_duration: timedelta,
    expected: int,
    server_utc_offset: timedelta,
) -> list[dict[str, object]]:
    if rates is None:
        raise RuntimeError(f"MT5 rates unavailable: {mt5.last_error()}")
    bars: list[dict[str, object]] = []
    for rate in rates:
        server_stamp = datetime.fromtimestamp(int(rate["time"]), tz=timezone.utc)
        if server_stamp + bar_duration > server_information_cutoff:
            raise ValueError(
                f"future/incomplete bar {server_stamp.isoformat()} exceeds "
                f"server information cutoff {server_information_cutoff.isoformat()}"
            )
        utc_stamp = server_stamp - server_utc_offset
        bars.append(
            {
                "t": utc_stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "o": float(rate["open"]),
                "h": float(rate["high"]),
                "l": float(rate["low"]),
                "c": float(rate["close"]),
                "spread": int(rate["spread"]),
            }
        )
    if len(bars) != expected:
        raise ValueError(f"expected {expected} completed bars; found {len(bars)}")
    return bars


def detector_view(row: dict[str, str]) -> dict[str, object]:
    return {
        "event_id": row["event_id"],
        "source_sha256": row["source_sha256"].upper(),
        "decision_time_utc": parse_decision_time(row["decision_time_utc"])
        .isoformat()
        .replace("+00:00", "Z"),
        "decision_time_server": row["decision_time_server"],
        "server_utc_offset_hours": int(row["server_utc_offset_hours"]),
        "direction": "long" if row["direction"] == "1" else "short",
        "detector_score": int(row["detector_score"]),
        "sweep_extreme": float(row["sweep_extreme"]),
        "sweep_age_bars": int(row["sweep_age_bars"]),
        "displacement_atr": float(row["displacement_atr"]),
        "fvg_low": float(row["fvg_low"]),
        "fvg_mid": float(row["fvg_mid"]),
        "fvg_high": float(row["fvg_high"]),
        "overlap_ratio": float(row["overlap_ratio"]),
        "h4_bias": int(row["h4_bias"]),
        "d1_bias": int(row["d1_bias"]),
        "pd_ok": row["pd_ok"] == "1",
        "spread_points": float(row["spread_points"]),
    }


def assert_no_forbidden_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden outcome key in packet: {key}")
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)


def chunks(rows: list[dict[str, object]], size: int) -> Iterable[list[dict[str, object]]]:
    for offset in range(0, len(rows), size):
        yield rows[offset : offset + size]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--casebook", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--protected-root", action="append", type=Path, default=[])
    args = parser.parse_args()

    expected_source_sha256 = args.expected_source_sha256.strip().upper()
    rows = read_casebook(args.casebook, expected_source_sha256)
    common_before = [storage_inventory(root) for root in args.protected_root]
    if not mt5.initialize(path=str(args.terminal), timeout=60_000, portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected:
            raise RuntimeError("MT5 terminal is not connected")
        data_path = Path(terminal.data_path).resolve()
        if data_path.drive.upper() != "D:":
            raise RuntimeError(f"portable MT5 data path must be on D:, got {data_path}")

        packets: list[dict[str, object]] = []
        for row in rows:
            detector = detector_view(row)
            information_cutoff_utc = datetime.fromisoformat(
                str(detector["decision_time_utc"]).replace("Z", "+00:00")
            )
            server_information_cutoff = parse_decision_time(
                str(detector["decision_time_server"])
            )
            server_utc_offset = timedelta(
                hours=int(detector["server_utc_offset_hours"])
            )
            if server_information_cutoff - server_utc_offset != information_cutoff_utc:
                raise ValueError(
                    f"server/UTC decision mismatch for {detector['event_id']}"
                )
            context: dict[str, object] = {}
            for name, (timeframe, count, duration) in TIMEFRAMES.items():
                last_completed_open_cutoff = server_information_cutoff - duration
                rates = mt5.copy_rates_from(
                    args.symbol, timeframe, last_completed_open_cutoff, count
                )
                context[name] = compact_bars(
                    rates,
                    server_information_cutoff,
                    duration,
                    count,
                    server_utc_offset,
                )
            expected_final_m5_open = (
                information_cutoff_utc - timedelta(minutes=5)
            ).isoformat().replace("+00:00", "Z")
            if context["m5"][-1]["t"] != expected_final_m5_open:
                raise ValueError(
                    f"M5 decision identity mismatch for {detector['event_id']}"
                )
            packets.append(
                {
                    "detector": detector,
                    "information_cutoff_utc": information_cutoff_utc.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "completed_bar_context": context,
                }
            )
    finally:
        mt5.shutdown()

    common_after = [storage_inventory(root) for root in args.protected_root]
    for before, after in zip(common_before, common_after, strict=True):
        if before["metadata_sha256"] != after["metadata_sha256"]:
            raise RuntimeError(f"protected C root changed: {before['root']}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    batch_paths: list[Path] = []
    for number, batch in enumerate(chunks(packets, args.batch_size), start=1):
        payload = {
            "schema_version": "unicorn_alert_label_context.v2",
            "authority": "PRE_OUTCOME_LABEL_CONTEXT_ONLY",
            "outcomes_included": False,
            "source_sha256": expected_source_sha256,
            "rubric_sha256": sha256_file(args.rubric),
            "casebook_sha256": sha256_file(args.casebook),
            "batch_number": number,
            "row_count": len(batch),
            "rows": batch,
        }
        assert_no_forbidden_keys(payload)
        path = args.output_dir / f"label_context_batch_{number:02d}.json"
        path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
        batch_paths.append(path)

    manifest = {
        "schema_version": "unicorn_alert_label_context_manifest.v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authority": "PRE_OUTCOME_LABEL_CONTEXT_ONLY",
        "outcomes_included": False,
        "review_rows": len(packets),
        "batch_size": args.batch_size,
        "casebook": {
            "path": str(args.casebook.resolve()),
            "sha256": sha256_file(args.casebook),
            "source_sha256": expected_source_sha256,
            "source_contract_id": "UPS_ALERT_FIRST_CASEBOOK_V1_3",
        },
        "rubric": {"path": str(args.rubric.resolve()), "sha256": sha256_file(args.rubric)},
        "extractor_sha256": sha256_file(Path(__file__)),
        "terminal": {
            "company": terminal.company,
            "build": terminal.build,
            "portable": True,
            "data_path": str(data_path),
        },
        "context_counts": {name: count for name, (_, count, _) in TIMEFRAMES.items()},
        "time_axis": "MT5 server timestamps normalized by each row server_utc_offset_hours",
        "future_bar_violations": 0,
        "protected_storage": {
            "before": common_before,
            "after": common_after,
            "unchanged": True,
        },
        "batches": [
            {"path": str(path.resolve()), "sha256": sha256_file(path)} for path in batch_paths
        ],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
