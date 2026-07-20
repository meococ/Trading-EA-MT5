#!/usr/bin/env python3
"""Select four outcome-blind HYP-026 adverse strata plus deterministic matches."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from analyze_hyp026_pivot_reclaim_dwell_collection import (
    parse_time,
    server_to_utc,
    session_name,
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    logs = args.run_dir.resolve() / "logs"
    resilience = load_csv(next(logs.glob("*_LevelResilience_*.csv")))
    human = load_csv(next(logs.glob("*_HumanContext_*.csv")))
    human_by_key = {(row["decision_time"], row["direction"]): row for row in human}

    parsed: list[dict] = []
    for row in resilience:
        if row["resilience_label"] not in {"ADVERSE_DOMINANT", "FAVORABLE_DOMINANT"}:
            continue
        decision = parse_time(row["decision_time"])
        parsed.append(
            {
                "raw": row,
                "context": human_by_key[(row["decision_time"], row["direction"])],
                "decision": decision,
                "session": session_name(decision),
                "adverse_share": int(row["adverse_ms"]) / int(row["total_ms"]),
            }
        )

    adverse = [item for item in parsed if item["raw"]["resilience_label"] == "ADVERSE_DOMINANT"]
    favorable = [item for item in parsed if item["raw"]["resilience_label"] == "FAVORABLE_DOMINANT"]
    strata = [(-1, "LONDON"), (-1, "NEW_YORK"), (1, "LONDON"), (1, "NEW_YORK")]
    selected: list[tuple[str, dict]] = []
    used_matches: set[str] = set()
    for direction, session in strata:
        eligible_adverse = [
            item for item in adverse
            if int(item["raw"]["direction"]) == direction and item["session"] == session
        ]
        rare = min(
            eligible_adverse,
            key=lambda item: (-item["adverse_share"], item["raw"]["event_id"]),
        )
        selected.append((f"MAX_ADVERSE_SHARE_{direction}_{session}", rare))
        eligible_matches = [
            item for item in favorable
            if int(item["raw"]["direction"]) == direction
            and item["session"] == session
            and item["decision"].year == rare["decision"].year
            and item["raw"]["event_id"] not in used_matches
        ]
        match = min(
            eligible_matches,
            key=lambda item: (
                abs((item["decision"] - rare["decision"]).total_seconds()),
                item["raw"]["event_id"],
            ),
        )
        used_matches.add(match["raw"]["event_id"])
        selected.append(("NEAREST_SAME_DIRECTION_SESSION_YEAR", match))

    fields = [
        "case_id", "entry_time_utc", "direction", "entry", "reason", "label",
        "selection_stratum", "event_id", "decision_time_server", "session",
        "favorable_ms", "adverse_ms", "total_ms", "adverse_share", "max_gap_ms",
        "valid_ticks", "h1_range_location", "h4_range_location", "h1_structure",
        "h4_structure", "h1_aligned", "h4_aligned", "external_sweep",
        "external_swept_count", "room_r", "nearest_pool_type", "nearest_pool_pips",
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
                    "case_id": f"HYP026_{index:02d}_{short_label}_{decision_utc:%Y%m%d_%H%M}",
                    "entry_time_utc": decision_utc.isoformat(),
                    "direction": row["direction"],
                    "entry": row["level"],
                    "reason": f"pivot_fav_ms={row['favorable_ms']};pivot_adv_ms={row['adverse_ms']};max_gap_ms={row['max_gap_ms']}",
                    "label": row["resilience_label"].lower(),
                    "selection_stratum": stratum,
                    "event_id": row["event_id"],
                    "decision_time_server": row["decision_time"],
                    "session": item["session"],
                    "favorable_ms": row["favorable_ms"],
                    "adverse_ms": row["adverse_ms"],
                    "total_ms": row["total_ms"],
                    "adverse_share": f"{item['adverse_share']:.12f}",
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
    print(f"selected={len(selected)} adverse_population={len(adverse)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
