#!/usr/bin/env python3
"""Select every rare HYP-024 case plus a deterministic nearest-context match."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from analyze_hyp024_time_resilience_collection import parse_time, server_to_utc, session_name


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    logs = args.run_dir.resolve() / "logs"
    resilience_path = next(logs.glob("*_LevelResilience_*.csv"))
    human_path = next(logs.glob("*_HumanContext_*.csv"))
    resilience = load_csv(resilience_path)
    human = load_csv(human_path)
    human_by_key = {(row["decision_time"], row["direction"]): row for row in human}

    parsed: list[dict] = []
    for row in resilience:
        if row["resilience_label"] not in {"ADVERSE_DOMINANT", "FAVORABLE_DOMINANT"}:
            continue
        decision = parse_time(row["decision_time"])
        context = human_by_key[(row["decision_time"], row["direction"])]
        parsed.append(
            {
                "raw": row,
                "context": context,
                "decision": decision,
                "session": session_name(decision),
            }
        )

    rare = sorted(
        (item for item in parsed if item["raw"]["resilience_label"] == "ADVERSE_DOMINANT"),
        key=lambda item: item["decision"],
    )
    favorable = [
        item for item in parsed if item["raw"]["resilience_label"] == "FAVORABLE_DOMINANT"
    ]
    used: set[str] = set()
    selected: list[tuple[str, dict]] = []
    for item in rare:
        selected.append(("RARE_ALL", item))
        eligible = [
            candidate
            for candidate in favorable
            if candidate["raw"]["direction"] == item["raw"]["direction"]
            and candidate["decision"].year == item["decision"].year
            and candidate["session"] == item["session"]
            and candidate["raw"]["event_id"] not in used
        ]
        match = min(
            eligible,
            key=lambda candidate: (
                abs((candidate["decision"] - item["decision"]).total_seconds()),
                candidate["raw"]["event_id"],
            ),
        )
        used.add(match["raw"]["event_id"])
        selected.append(("NEAREST_SAME_DIRECTION_SESSION_YEAR", match))

    fields = [
        "case_id", "entry_time_utc", "direction", "entry", "reason", "label",
        "selection_stratum", "event_id", "decision_time_server", "session",
        "favorable_ms", "adverse_ms", "total_ms", "max_gap_ms", "valid_ticks",
        "h1_range_location", "h4_range_location", "h1_structure", "h4_structure",
        "h1_aligned", "h4_aligned", "external_sweep", "external_swept_count",
        "room_r", "nearest_pool_type", "nearest_pool_pips",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, (stratum, item) in enumerate(selected, start=1):
            row = item["raw"]
            context = item["context"]
            decision_utc = server_to_utc(item["decision"])
            short_label = "ADVERSE" if row["resilience_label"] == "ADVERSE_DOMINANT" else "FAVORABLE_MATCH"
            writer.writerow(
                {
                    "case_id": f"HYP024_{index:02d}_{short_label}_{decision_utc:%Y%m%d_%H%M}",
                    "entry_time_utc": decision_utc.isoformat(),
                    "direction": row["direction"],
                    "entry": row["level"],
                    "reason": (
                        f"fav_ms={row['favorable_ms']};adv_ms={row['adverse_ms']};"
                        f"max_gap_ms={row['max_gap_ms']}"
                    ),
                    "label": row["resilience_label"].lower(),
                    "selection_stratum": stratum,
                    "event_id": row["event_id"],
                    "decision_time_server": row["decision_time"],
                    "session": item["session"],
                    "favorable_ms": row["favorable_ms"],
                    "adverse_ms": row["adverse_ms"],
                    "total_ms": row["total_ms"],
                    "max_gap_ms": row["max_gap_ms"],
                    "valid_ticks": row["valid_ticks"],
                    "h1_range_location": context["h1_range_location"],
                    "h4_range_location": context["h4_range_location"],
                    "h1_structure": context["h1_structure"],
                    "h4_structure": context["h4_structure"],
                    "h1_aligned": context["h1_aligned"],
                    "h4_aligned": context["h4_aligned"],
                    "external_sweep": context["external_sweep"],
                    "external_swept_count": context["external_swept_count"],
                    "room_r": context["room_r"],
                    "nearest_pool_type": context["nearest_pool_type"],
                    "nearest_pool_pips": context["nearest_pool_pips"],
                }
            )
    print(f"selected={len(selected)} rare={len(rare)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
