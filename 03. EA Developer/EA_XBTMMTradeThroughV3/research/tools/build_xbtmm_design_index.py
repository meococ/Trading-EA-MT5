#!/usr/bin/env python3
"""Normalize daily DESIGN archives and emit a deterministic MT5 index.

No strategy metric is calculated here.  Missing or rejected calendar days stop
index creation, so an economic run cannot silently select around source gaps.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
BUILDER_PATH = HERE / "build_xbtmm_event_stream.py"
SPEC = importlib.util.spec_from_file_location("xbtmm_event_builder_v3", BUILDER_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)

DESIGN_START = date(2018, 1, 1)
DESIGN_END = date(2021, 12, 31)
INDEX_FIELDS = [
    "utc_day",
    "event_file_common",
    "event_sha256",
    "event_bytes",
    "records",
    "quote_records",
    "trade_records",
    "first_time_us",
    "last_time_us",
    "tick_size",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def days_between(start: date, end: date) -> list[date]:
    if start < DESIGN_START or end > DESIGN_END or start > end:
        raise ValueError("normalization window must stay inside sealed DESIGN bounds")
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def paths_for(root: Path, utc_day: date) -> dict[str, Path]:
    token = utc_day.strftime("%Y%m%d")
    year = f"{utc_day.year:04d}"
    month = f"{utc_day.month:02d}"
    return {
        "quote": root / "raw" / year / month / f"quote-{token}.csv.gz",
        "trade": root / "raw" / year / month / f"trade-{token}.csv.gz",
        "event": root / "events" / year / month / f"{token}.xbtmm",
        "manifest": root / "manifests" / year / month / f"{token}.event_manifest.json",
    }


def verified_existing(paths: dict[str, Path], token: str) -> dict | None:
    if not paths["event"].exists() or not paths["manifest"].exists():
        return None
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != "xbtmm_event_stream_manifest.v3"
        or manifest.get("utc_day") != token
        or manifest.get("integrity", {}).get("source_gate_pass") is not True
    ):
        return None
    bindings = (
        (paths["quote"], manifest.get("quote_archive", {})),
        (paths["trade"], manifest.get("trade_archive", {})),
        (paths["event"], manifest.get("output", {})),
    )
    for path, binding in bindings:
        if not path.exists():
            return None
        if path.stat().st_size != binding.get("bytes") or sha256(path) != binding.get("sha256"):
            return None
    return manifest


def normalize_one(root: Path, utc_day: date) -> dict:
    token = utc_day.strftime("%Y%m%d")
    paths = paths_for(root, utc_day)
    if not paths["quote"].exists() or not paths["trade"].exists():
        raise FileNotFoundError(f"missing required archive pair for {token}")
    manifest = verified_existing(paths, token)
    if manifest is None:
        manifest = builder.build(
            paths["quote"],
            paths["trade"],
            paths["event"],
            paths["manifest"],
            "XBTUSD",
        )
    if manifest["integrity"]["source_gate_pass"] is not True:
        raise RuntimeError(f"daily source gate failed for {token}")
    return manifest


def index_row(root: Path, manifest: dict) -> dict[str, object]:
    token = manifest["utc_day"]
    event = Path(manifest["output"]["path"])
    relative = event.resolve().relative_to(root.resolve())
    return {
        "utc_day": token,
        "event_file_common": str(Path("xbtmm") / relative).replace("/", "\\"),
        "event_sha256": manifest["output"]["sha256"],
        "event_bytes": manifest["output"]["bytes"],
        "records": manifest["output"]["records"],
        "quote_records": manifest["output"]["quote_records"],
        "trade_records": manifest["output"]["trade_records"],
        "first_time_us": manifest["output"]["first_time_us"],
        "last_time_us": manifest["output"]["last_time_us"],
        "tick_size": manifest["instrument_schedule"]["tick_size"],
    }


def write_index(root: Path, start: date, end: date, manifests: list[dict], pilot: bool) -> dict:
    rows = [index_row(root, manifest) for manifest in sorted(manifests, key=lambda m: m["utc_day"])]
    expected_days = days_between(start, end)
    if [row["utc_day"] for row in rows] != [day.strftime("%Y%m%d") for day in expected_days]:
        raise RuntimeError("daily manifests are not an exact contiguous population")
    prefix = f"pilot_{start:%Y%m%d}_{end:%Y%m%d}" if pilot else "design_2018_2021"
    index_path = root / f"{prefix}_index.csv"
    temporary = index_path.with_suffix(index_path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(index_path)
    index_sha = sha256(index_path)
    root_payload = "\n".join(
        f"{row['utc_day']}|{row['event_sha256']}|{row['records']}" for row in rows
    )
    daily_root_sha = hashlib.sha256(root_payload.encode("ascii")).hexdigest().upper()
    summary = {
        "schema_version": "xbtmm_design_index_manifest.v1",
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "hypothesis_id": "HYP-XBT-MM-TRADETHROUGH-003",
        "population": "PILOT" if pilot else "DESIGN",
        "requested_from": start.isoformat(),
        "requested_to": end.isoformat(),
        "calendar_days": len(rows),
        "index_path": str(index_path.resolve()),
        "index_bytes": index_path.stat().st_size,
        "index_sha256": index_sha,
        "daily_event_root_sha256": daily_root_sha,
        "events": sum(int(row["records"]) for row in rows),
        "quotes": sum(int(row["quote_records"]) for row in rows),
        "trades": sum(int(row["trade_records"]) for row in rows),
        "tick_size": 0.5,
        "source_gate_pass": len(rows) == len(expected_days),
        "economic_use_forbidden": True,
    }
    manifest_path = root / f"{prefix}_index_manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["manifest_path"] = str(manifest_path.resolve())
    summary["manifest_sha256"] = sha256(manifest_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--from", dest="start", type=parse_day, default=DESIGN_START)
    parser.add_argument("--to", dest="end", type=parse_day, default=DESIGN_END)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        parser.error("--workers must be between 1 and 8")
    days = days_between(args.start, args.end)
    full_design = args.start == DESIGN_START and args.end == DESIGN_END
    if not full_design and not args.pilot:
        parser.error("partial normalization requires --pilot")
    if full_design and args.pilot:
        parser.error("--pilot is not allowed for the full DESIGN population")

    manifests: list[dict] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(normalize_one, args.root, day): day for day in days}
        for future in as_completed(future_map):
            day = future_map[future]
            try:
                manifest = future.result()
                manifests.append(manifest)
                print(f"NORMALIZED {day:%Y%m%d} {manifest['output']['sha256']}", flush=True)
            except Exception as exc:  # noqa: BLE001 - collect exact source failures
                failures.append(f"{day:%Y%m%d}: {exc}")
                print(f"FAILED {failures[-1]}", flush=True)
    if failures:
        print(json.dumps({"source_gate_pass": False, "failures": failures}, indent=2))
        return 2
    summary = write_index(args.root, args.start, args.end, manifests, args.pilot)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
