#!/usr/bin/env python3
"""Freeze Cell-16 chart cases before any chart is viewed.

The selector uses only lifecycle fields already known at entry plus the final
winner/loser label required to define the sampling stratum.  It deliberately
does not inspect candles or indicator states.  Each active engine contributes
one median loser and one matched winner; global R extremes are added when they
are not already present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


SCHEMA = "rsf_cell16_forensic_selection.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def parse_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%Y.%m.%d %H:%M:%S", errors="raise")


def session_name(utc: pd.Timestamp) -> str:
    # The forensic matcher only needs a stable coarse stratum.  Entries in the
    # frozen Union mask are split at 12:00 UTC; exact EA DST masks remain in the
    # run source and are not reclassified for economic claims here.
    return "LONDON" if utc.hour < 12 else "OVERLAP"


def truth_table(lifecycle: pd.DataFrame) -> pd.DataFrame:
    opens = lifecycle[lifecycle["action"] == "OPEN"].copy()
    closes = lifecycle[lifecycle["is_final_close"].astype(str) == "1"].copy()
    if opens["position_id"].duplicated().any() or closes["position_id"].duplicated().any():
        raise SystemExit("position lifecycle is not one-open/one-final-close")
    keep = [
        "position_id", "event_time", "utc_time", "order_type", "entry_price",
        "initial_sl", "initial_tp", "risk_pts", "initial_risk_account", "volume",
        "engine_name", "tag", "hypothesis_id",
    ]
    joined = opens[keep].merge(
        closes[["position_id", "event_time", "utc_time", "price", "reason", "net_profit", "achievedr"]],
        on="position_id", how="inner", validate="one_to_one", suffixes=("_entry", "_exit"),
    )
    if len(joined) != len(closes):
        raise SystemExit("open/final-close reconciliation failed")
    rename = {
        "event_time_entry": "entry_time_server",
        "utc_time_entry": "entry_time_utc",
        "event_time_exit": "exit_time_server",
        "utc_time_exit": "exit_time_utc",
        "price": "exit_price",
        "reason": "exit_reason",
        "net_profit": "net_profit",
        "achievedr": "net_r",
    }
    joined = joined.rename(columns=rename)
    for col in ("entry_price", "initial_sl", "initial_tp", "risk_pts", "initial_risk_account", "volume", "exit_price", "net_profit", "net_r"):
        joined[col] = pd.to_numeric(joined[col], errors="raise")
    for col in ("entry_time_server", "entry_time_utc", "exit_time_server", "exit_time_utc"):
        joined[col] = parse_time(joined[col])
    joined["direction"] = joined["order_type"].map({"BUY": 1, "SELL": -1})
    if joined["direction"].isna().any():
        raise SystemExit("unknown entry direction")
    joined["outcome"] = joined["net_profit"].map(lambda x: "WIN" if x > 0 else "LOSS")
    joined["holding_minutes"] = (
        joined["exit_time_server"] - joined["entry_time_server"]
    ).dt.total_seconds() / 60.0
    joined["year"] = joined["entry_time_utc"].dt.year
    joined["month"] = joined["entry_time_utc"].dt.to_period("M").astype(str)
    joined["entry_hour_utc"] = (
        joined["entry_time_utc"].dt.hour + joined["entry_time_utc"].dt.minute / 60.0
    )
    joined["session"] = joined["entry_time_utc"].map(session_name)
    joined["position_id_num"] = pd.to_numeric(joined["position_id"], errors="raise")
    return joined.sort_values("entry_time_server").reset_index(drop=True)


def nearest_to_median(group: pd.DataFrame, column: str) -> pd.Series:
    target = float(group[column].median())
    ranked = group.assign(_d=(group[column] - target).abs()).sort_values(
        ["_d", "position_id_num"], kind="stable"
    )
    return ranked.iloc[0]


def cyclic_hour_distance(a: float, b: float) -> float:
    direct = abs(a - b)
    return min(direct, 24.0 - direct) / 12.0


def match_winner(truth: pd.DataFrame, loser: pd.Series) -> tuple[pd.Series, str]:
    winners = truth[(truth["engine_name"] == loser["engine_name"]) & (truth["net_profit"] > 0)].copy()
    same_session = winners[winners["session"] == loser["session"]]
    same_year = same_session[same_session["year"] == loser["year"]]
    if not same_year.empty:
        candidates, relaxation = same_year, "same_engine_session_year"
    elif not same_session.empty:
        candidates, relaxation = same_session, "same_engine_session"
    else:
        candidates, relaxation = winners, "same_engine_only"
    if candidates.empty:
        raise SystemExit(f"no winner available for engine {loser['engine_name']}")
    risk_anchor = max(float(loser["risk_pts"]), 1e-9)
    candidates = candidates.copy()
    candidates["_risk_d"] = candidates["risk_pts"].map(
        lambda v: abs(math.log(max(float(v), 1e-9) / risk_anchor))
    )
    candidates["_hour_d"] = candidates["entry_hour_utc"].map(
        lambda v: cyclic_hour_distance(float(v), float(loser["entry_hour_utc"]))
    )
    candidates["_date_d"] = candidates["entry_time_utc"].map(
        lambda v: abs((v - loser["entry_time_utc"]).total_seconds()) / (5 * 365.25 * 86400)
    )
    candidates["_match_d"] = candidates["_risk_d"] + candidates["_hour_d"] + 0.25 * candidates["_date_d"]
    return candidates.sort_values(["_match_d", "position_id_num"], kind="stable").iloc[0], relaxation


def case_row(row: pd.Series, case_id: str, stratum: str, match_rule: str = "") -> dict:
    return {
        "case_id": case_id,
        "stratum": stratum,
        "position_id": str(row["position_id"]),
        "engine_name": row["engine_name"],
        "direction": int(row["direction"]),
        "direction_name": "LONG" if int(row["direction"]) > 0 else "SHORT",
        "entry_time_server": row["entry_time_server"].strftime("%Y.%m.%d %H:%M:%S"),
        "exit_time_server": row["exit_time_server"].strftime("%Y.%m.%d %H:%M:%S"),
        "entry_time_utc": row["entry_time_utc"].strftime("%Y-%m-%d %H:%M:%S"),
        "exit_time_utc": row["exit_time_utc"].strftime("%Y-%m-%d %H:%M:%S"),
        "entry": float(row["entry_price"]),
        "exit": float(row["exit_price"]),
        "sl": float(row["initial_sl"]),
        "tp": float(row["initial_tp"]),
        "risk_pts": float(row["risk_pts"]),
        "initial_risk_account": float(row["initial_risk_account"]),
        "net_profit": float(row["net_profit"]),
        "net_r": float(row["net_r"]),
        "holding_minutes": float(row["holding_minutes"]),
        "reason": row["exit_reason"],
        "session": row["session"],
        "match_rule": match_rule,
        "label": f"{row['engine_name']} {row['outcome']} {float(row['net_r']):+.2f}R",
    }


def merge_capture_windows(cases: list[dict]) -> list[tuple[datetime, datetime]]:
    raw = []
    for case in cases:
        entry = datetime.strptime(case["entry_time_server"], "%Y.%m.%d %H:%M:%S")
        exit_ = datetime.strptime(case["exit_time_server"], "%Y.%m.%d %H:%M:%S")
        raw.append((entry - timedelta(hours=10), max(entry, exit_) + timedelta(hours=5)))
    raw.sort()
    merged: list[list[datetime]] = []
    for start, end in raw:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lifecycle", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    lifecycle = pd.read_csv(args.lifecycle, dtype={"position_id": str})
    truth = truth_table(lifecycle)
    if len(truth) != 670:
        raise SystemExit(f"expected 670 Cell-16 final positions, got {len(truth)}")

    cases: list[dict] = []
    selected: set[str] = set()
    for engine in sorted(truth["engine_name"].unique()):
        losses = truth[(truth["engine_name"] == engine) & (truth["net_profit"] < 0)]
        loser = nearest_to_median(losses, "net_r")
        winner, relaxation = match_winner(truth, loser)
        token = engine.replace("_", "-")
        for row, suffix, stratum, match_rule in (
            (loser, "L", "engine_median_loser", "negative_median_R"),
            (winner, "W", "matched_winner", relaxation),
        ):
            pid = str(row["position_id"])
            if pid in selected:
                continue
            selected.add(pid)
            cases.append(case_row(row, f"RSF-C16-{token}-{suffix}", stratum, match_rule))

    for row, case_id, stratum in (
        (truth.sort_values(["net_r", "position_id_num"]).iloc[0], "RSF-C16-EXTREME-LOSS", "global_min_R"),
        (truth.sort_values(["net_r", "position_id_num"], ascending=[False, True]).iloc[0], "RSF-C16-EXTREME-WIN", "global_max_R"),
    ):
        pid = str(row["position_id"])
        if pid not in selected:
            selected.add(pid)
            cases.append(case_row(row, case_id, stratum))

    cases_df = pd.DataFrame(cases)
    cases_path = args.out_dir / "cases.csv"
    truth_path = args.out_dir / "position_truth_table.csv"
    cases_df.to_csv(cases_path, index=False)
    truth.drop(columns=["position_id_num"]).to_csv(truth_path, index=False)

    windows = merge_capture_windows(cases)
    window_string = "~".join(
        f"{start.strftime('%Y.%m.%d %H:%M')}|{end.strftime('%Y.%m.%d %H:%M')}"
        for start, end in windows
    )
    manifest = {
        "schema_version": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_run_id": "20260806_210021",
        "source_variant": "B1C16_UNION_FULL",
        "lifecycle": str(args.lifecycle),
        "lifecycle_sha256": sha256_file(args.lifecycle),
        "position_count": int(len(truth)),
        "case_count": int(len(cases)),
        "sampling_rule": {
            "per_engine": "R closest to negative median, then matched winner by same engine/session/year when available",
            "match_distance": "abs(log risk ratio) + cyclic UTC-hour distance + 0.25 * normalized calendar distance",
            "extremes": "global min and max net_R added if not already selected",
            "chart_or_indicator_values_viewed_before_selection": False,
        },
        "cases_csv": str(cases_path),
        "cases_sha256": sha256_file(cases_path),
        "truth_table_csv": str(truth_path),
        "truth_table_sha256": sha256_file(truth_path),
        "capture_windows_server": [
            {"from": start.strftime("%Y.%m.%d %H:%M:%S"), "to": end.strftime("%Y.%m.%d %H:%M:%S")}
            for start, end in windows
        ],
        "capture_windows_input": window_string,
        "cases": cases,
    }
    manifest_path = args.out_dir / "selection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"RSF_CASE_SELECTION positions={len(truth)} cases={len(cases)} windows={len(windows)} manifest={manifest_path}")
    print(f"CAPTURE_WINDOWS={window_string}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
