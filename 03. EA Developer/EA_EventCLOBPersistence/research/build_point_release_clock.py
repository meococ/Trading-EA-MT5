#!/usr/bin/env python3
"""Build the outcome-blind EUR/USD point-release clock for HYP-001.

This utility reads only event identity/time fields. It never opens price bars,
order-book records, trades, or any forward outcome. The Forex Factory calendar
is source-rank C and therefore diagnostic-only; an official point-in-time clock
ledger remains mandatory before any promotion claim.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "event_clob_point_release_clock.v1"
SOURCE_SHA256 = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
EXCLUSION_PATTERN = re.compile(r"(speaks|testifies|press conference)", re.IGNORECASE)
MIN_TOTAL_CLOCKS = 418
MIN_SPLIT_CLOCKS = 209
ELAPSED_WEEKS = 208.7143

WORKSPACE = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "forexfactory"
    / "EURUSD"
    / "news_events"
    / "forexfactory_high_impact_eurusd_2019_2022.csv"
)
OUTPUT_DIR = PACKAGE / "research" / "source"
OUTPUT = OUTPUT_DIR / "point_release_clocks_2019_2022.csv"
MANIFEST = OUTPUT_DIR / "point_release_clock_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_utc(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"event clock is timezone-naive: {value}")
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def relative(path: Path) -> str:
    return str(path.relative_to(WORKSPACE)).replace("\\", "/")


def main() -> int:
    if not SOURCE.is_file():
        raise SystemExit(f"missing source calendar: {SOURCE}")
    actual_source_sha = sha256_file(SOURCE)
    if actual_source_sha != SOURCE_SHA256:
        raise SystemExit(
            f"source SHA mismatch: expected {SOURCE_SHA256}, got {actual_source_sha}"
        )

    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "event_time_utc",
        "event_id",
        "currency",
        "impact",
        "event_name",
        "source_week",
        "source_url",
    }
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"calendar schema missing fields: {sorted(required)}")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    excluded_rows = 0
    for row in rows:
        if EXCLUSION_PATTERN.search(row["event_name"]):
            excluded_rows += 1
            continue
        grouped[canonical_utc(row["event_time_utc"])].append(row)

    output_rows: list[dict[str, str]] = []
    for index, event_time in enumerate(sorted(grouped), start=1):
        members = grouped[event_time]
        output_rows.append(
            {
                "event_clock_id": f"EVT{index:04d}",
                "event_time_utc": event_time,
                "currencies": "|".join(sorted({row["currency"] for row in members})),
                "event_ids": "|".join(
                    sorted({row["event_id"] for row in members}, key=int)
                ),
                "event_names": "|".join(sorted({row["event_name"] for row in members})),
                "source_weeks": "|".join(sorted({row["source_week"] for row in members})),
                "source_urls": "|".join(sorted({row["source_url"] for row in members})),
            }
        )

    split_counts = {
        "2019_2020": sum(row["event_time_utc"][:4] in {"2019", "2020"} for row in output_rows),
        "2021_2022": sum(row["event_time_utc"][:4] in {"2021", "2022"} for row in output_rows),
    }
    total = len(output_rows)
    if total < MIN_TOTAL_CLOCKS or any(
        value < MIN_SPLIT_CLOCKS for value in split_counts.values()
    ):
        raise SystemExit(
            f"fatal cadence gate: total={total}, split_counts={split_counts}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output_rows[0])
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)

    output_sha = sha256_file(OUTPUT)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "hypothesis_id": "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001",
        "status": "OUTCOME_BLIND_CLOCK_GATE_PASS_SOURCE_C_DIAGNOSTIC_ONLY",
        "source_rank": "C",
        "promotion_eligible": False,
        "outcome_fields_read": False,
        "price_data_read": False,
        "paid_request_made": False,
        "source": {"path": relative(SOURCE), "sha256": SOURCE_SHA256},
        "output": {"path": relative(OUTPUT), "sha256": output_sha},
        "exclusion_regex": EXCLUSION_PATTERN.pattern,
        "exclusion_reason": "remove speeches, testimony and press conferences; retain point-release clocks only",
        "source_rows": len(rows),
        "source_unique_clocks": len({canonical_utc(row["event_time_utc"]) for row in rows}),
        "excluded_rows": excluded_rows,
        "retained_source_rows": len(rows) - excluded_rows,
        "retained_unique_clocks": total,
        "split_counts": split_counts,
        "elapsed_weeks": ELAPSED_WEEKS,
        "raw_clock_cadence_per_week": total / ELAPSED_WEEKS,
        "gates": {
            "min_total_clocks": MIN_TOTAL_CLOCKS,
            "min_each_two_year_split": MIN_SPLIT_CLOCKS,
            "total_pass": total >= MIN_TOTAL_CLOCKS,
            "split_pass": all(value >= MIN_SPLIT_CLOCKS for value in split_counts.values()),
        },
        "limitations": [
            "Forex Factory calendar has no actual/forecast/revision lineage",
            "calendar is diagnostic source-rank C, not official point-in-time proof",
            "event supply is not eligible-trade cadence",
            "no CME MBP-10 coverage or economic outcome has been opened",
        ],
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        "EVENT_CLOB_CLOCK_GATE "
        f"status={manifest['status']} clocks={total} "
        f"split_2019_2020={split_counts['2019_2020']} "
        f"split_2021_2022={split_counts['2021_2022']} "
        f"cadence={manifest['raw_clock_cadence_per_week']:.6f} "
        "paid_request_made=false outcome_fields_read=false"
    )
    print(f"manifest={MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
