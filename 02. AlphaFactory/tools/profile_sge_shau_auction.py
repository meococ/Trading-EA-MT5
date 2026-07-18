#!/usr/bin/env python3
"""Profile outcome-blind SGE SHAU fixing-round coverage before preregistration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence


SCHEMA_VERSION = "sge_shau_auction_profile.v2"


# The public archive exposes the trade date, but not an official publication
# timestamp or an immutable first-publication/revision lineage.  Density alone
# therefore cannot authorize an outcome join: a T+1 buffer would be a research
# assumption rather than evidence that every historical detail table was
# public before entry.
TEMPORAL_PROVENANCE_AUDIT = {
    "official_published_at_with_time_and_timezone": False,
    "first_publication_lineage_available": False,
    "revision_lineage_available": False,
    "http_last_modified_or_etag_available_on_sampled_articles": False,
    "verdict": "FAIL_NO_POINT_IN_TIME_PUBLICATION_PROOF",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def elapsed_weeks(start: date, end: date) -> float:
    return (end - start).days / 7.0


def build_profile(rows: list[dict]) -> dict:
    by_date_session: dict[tuple[str, int], list[dict]] = defaultdict(list)
    duplicate_counter: Counter[tuple[str, int, int]] = Counter()
    for raw in rows:
        row = dict(raw)
        row["session"] = int(row["session"])
        row["round"] = int(row["round"])
        row["bid_kg"] = float(row["bid_kg"])
        row["ask_kg"] = float(row["ask_kg"])
        row["supplemental_balance_kg"] = float(row["supplemental_balance_kg"])
        by_date_session[(row["trade_date"], row["session"])].append(row)
        duplicate_counter[(row["trade_date"], row["session"], row["round"])] += 1

    dates = sorted({key[0] for key in by_date_session})
    sessions_by_date = {
        trade_date: sorted(session for date_key, session in by_date_session if date_key == trade_date)
        for trade_date in dates
    }
    anomalies = [
        {
            "trade_date": trade_date,
            "sessions": sessions_by_date[trade_date],
            "source_urls": sorted(
                {
                    row["source_url"]
                    for (date_key, _), group in by_date_session.items()
                    if date_key == trade_date
                    for row in group
                }
            ),
        }
        for trade_date in dates
        if sessions_by_date[trade_date] != [1, 2]
    ]

    final_pm: list[dict] = []
    for (trade_date, session), group in sorted(by_date_session.items()):
        if session != 2:
            continue
        max_round = max(row["round"] for row in group)
        candidates = [row for row in group if row["round"] == max_round]
        if len(candidates) == 1:
            final_pm.append(candidates[0])

    per_year = []
    for year in sorted({int(value[:4]) for value in dates}):
        year_dates = [value for value in dates if int(value[:4]) == year]
        year_pm = [row for row in final_pm if int(row["trade_date"][:4]) == year]
        per_year.append(
            {
                "year": year,
                "source_dates": len(year_dates),
                "valid_final_pm_dates": len(year_pm),
                "both_session_dates": sum(sessions_by_date[value] == [1, 2] for value in year_dates),
            }
        )

    split_bounds = {
        "train": (date(2017, 1, 3), date(2021, 12, 31)),
        "validation": (date(2022, 1, 1), date(2023, 12, 31)),
    }
    splits = {}
    for name, (start, end) in split_bounds.items():
        selected = [
            row for row in final_pm if start <= date.fromisoformat(row["trade_date"]) <= end
        ]
        weeks = elapsed_weeks(start, end)
        splits[name] = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "valid_final_pm_dates": len(selected),
            "elapsed_calendar_weeks": weeks,
            "max_one_signal_per_day_cadence": len(selected) / weeks,
            "nonzero_signed_imbalance_dates": sum(
                row["bid_kg"] != row["ask_kg"] for row in selected
            ),
            "positive_supplemental_dates": sum(
                row["supplemental_balance_kg"] > 0 for row in selected
            ),
        }

    cadence_pass = all(
        2.0 <= split["max_one_signal_per_day_cadence"] <= 5.0
        for split in splits.values()
    )
    integrity_pass = len(anomalies) / len(dates) <= 0.01
    density_pass = cadence_pass and integrity_pass
    temporal_provenance_pass = all(
        TEMPORAL_PROVENANCE_AUDIT[field]
        for field in (
            "official_published_at_with_time_and_timezone",
            "first_publication_lineage_available",
            "revision_lineage_available",
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "row_count": len(rows),
        "source_date_count": len(dates),
        "first_trade_date": dates[0],
        "last_trade_date": dates[-1],
        "duplicate_date_session_round_keys": sum(
            count > 1 for count in duplicate_counter.values()
        ),
        "session_anomalies": anomalies,
        "valid_final_pm_count": len(final_pm),
        "per_year": per_year,
        "splits": splits,
        "density_gate": {
            "cadence_2_to_5_each_unsealed_split": cadence_pass,
            "session_anomaly_rate_le_1pct": integrity_pass,
            "pass": density_pass,
        },
        "temporal_provenance_gate": {
            **TEMPORAL_PROVENANCE_AUDIT,
            "pass": temporal_provenance_pass,
        },
        "source_gate": {
            "density_pass": density_pass,
            "temporal_provenance_pass": temporal_provenance_pass,
            "pass": density_pass and temporal_provenance_pass,
        },
        "holdout_2024_2025_loaded": False,
        "price_outcomes_accessed": False,
    }


def profile(csv_path: Path, output_path: Path) -> dict:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    payload = build_profile(rows)
    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["source_csv"] = csv_path.as_posix()
    payload["source_csv_sha256"] = sha256_file(csv_path)
    temporary = output_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1] / "external" / "sge_shau_auction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=root / "shau_fixing_rounds.csv")
    parser.add_argument("--output", type=Path, default=root / "source_profile.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = profile(args.csv, args.output)
    print(
        "SGE_SHAU_PROFILE "
        f"dates={payload['source_date_count']} pm={payload['valid_final_pm_count']} "
        f"density={'PASS' if payload['density_gate']['pass'] else 'FAIL'} "
        f"gate={'PASS' if payload['source_gate']['pass'] else 'FAIL'}"
    )
    return 0 if payload["source_gate"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
