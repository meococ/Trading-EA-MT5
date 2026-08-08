
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


LONG_FLAGS = ("tb_structure_up", "tb_displacement_up", "tb_sweep_low")
SHORT_FLAGS = ("tb_structure_down", "tb_displacement_down", "tb_sweep_high")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    usecols = ["source_bar_time_utc", "hypothesis_id", *LONG_FLAGS, *SHORT_FLAGS]
    df = pd.read_csv(args.census, usecols=usecols)
    if (df["hypothesis_id"] != "HYP-RSF-USDJPY-M15-STATE-MODEL-015").any():
        raise SystemExit("Parent census identity mismatch")
    times = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)

    rises = {}
    for flag in (*LONG_FLAGS, *SHORT_FLAGS):
        current = df[flag].astype(bool)
        rises[flag] = current & ~current.shift(1, fill_value=False)
    long_rise = pd.concat([rises[name] for name in LONG_FLAGS], axis=1).any(axis=1)
    short_rise = pd.concat([rises[name] for name in SHORT_FLAGS], axis=1).any(axis=1)
    conflict = long_rise & short_rise
    eligible = long_rise ^ short_rise

    events = pd.DataFrame(
        {
            "source_bar_time_utc": times[eligible].astype(str),
            "direction": long_rise[eligible].map({True: 1, False: -1}).astype(int),
            "structure_rise": (rises["tb_structure_up"] | rises["tb_structure_down"])[eligible].astype(int),
            "displacement_rise": (rises["tb_displacement_up"] | rises["tb_displacement_down"])[eligible].astype(int),
            "sweep_rise": (rises["tb_sweep_low"] | rises["tb_sweep_high"])[eligible].astype(int),
        }
    ).reset_index(names="census_index")
    if events["source_bar_time_utc"].duplicated().any():
        raise SystemExit("Collapsed event timestamps are not unique")
    events.to_csv(args.out_dir / "tb_event_clock.csv", index=False)

    elapsed_weeks = max((times.iloc[-1] - times.iloc[0]).total_seconds() / (7 * 86400), 1.0)
    by_year = []
    for year in range(2018, 2023):
        count = int((pd.to_datetime(events["source_bar_time_utc"], utc=True).dt.year == year).sum())
        year_start = max(times.iloc[0], pd.Timestamp(f"{year}-01-01", tz="UTC"))
        year_end = min(times.iloc[-1], pd.Timestamp(f"{year + 1}-01-01", tz="UTC"))
        weeks = max((year_end - year_start).total_seconds() / (7 * 86400), 1.0)
        by_year.append({"year": year, "events": count, "elapsed_weeks": weeks, "events_per_week": count / weeks})

    count = len(events)
    long_count = int((events.direction == 1).sum())
    conflict_count = int(conflict.sum())
    max_year_share = max(row["events"] for row in by_year) / count if count else 1.0
    gates = {
        "pooled_events_per_week_ge_2": count / elapsed_weeks >= 2.0,
        "every_year_events_per_week_ge_1_5": all(row["events_per_week"] >= 1.5 for row in by_year),
        "max_year_share_le_0_35": max_year_share <= 0.35,
        "long_share_0_30_to_0_70": count > 0 and 0.30 <= long_count / count <= 0.70,
        "unique_timestamps": not events["source_bar_time_utc"].duplicated().any(),
    }
    result = {
        "schema_version": "rsf_tb_event_clock018_stage0.v1",
        "hypothesis_id": "HYP-RSF-USDJPY-M15-TB-EVENT-ACCEPTANCE-018",
        "parent_census_sha256": sha256_file(args.census),
        "future_outcome_columns_read": False,
        "events": count,
        "conflicts_rejected": conflict_count,
        "long_events": long_count,
        "short_events": count - long_count,
        "long_share": long_count / count if count else 0.0,
        "elapsed_weeks": elapsed_weeks,
        "events_per_week": count / elapsed_weeks,
        "max_year_share": max_year_share,
        "by_year": by_year,
        "event_type_counts": {
            "structure_rise": int(events.structure_rise.sum()),
            "displacement_rise": int(events.displacement_rise.sum()),
            "sweep_rise": int(events.sweep_rise.sum()),
        },
        "gates": gates,
        "verdict": "PASS_STAGE0_AUTHORIZE_FROZEN_STAGE_B" if all(gates.values()) else "PARK_STAGE0_CADENCE_OR_BALANCE_FAIL",
    }
    (args.out_dir / "tb_event_clock018_stage0.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


