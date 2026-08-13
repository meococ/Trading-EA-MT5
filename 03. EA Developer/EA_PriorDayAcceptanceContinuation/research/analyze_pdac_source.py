from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-PDAC-XAUUSD-H1-001"
SOURCE_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
ELAPSED_WEEKS = 1826.0 / 7.0
REQUIRED_COLUMNS = [
    "symbol", "timeframe", "source_epoch", "time_server", "open", "high",
    "low", "close", "tick_volume",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.columns) != REQUIRED_COLUMNS:
        raise ValueError(f"schema mismatch: {list(frame.columns)}")
    if frame.empty or len(frame) < 25_000:
        raise ValueError("insufficient design rows")
    if not frame["symbol"].eq("XAUUSD").all():
        raise ValueError("symbol mismatch")
    if not frame["timeframe"].eq("H1").all():
        raise ValueError("timeframe mismatch")
    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    if not (np.diff(epoch) > 0).all():
        raise ValueError("source_epoch must be strictly increasing and unique")
    if epoch[0] < START_EPOCH or epoch[-1] >= END_EPOCH:
        raise ValueError("sealed window violation")
    prices = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    valid = (
        np.isfinite(prices).all(axis=1)
        & np.isfinite(volume)
        & (volume > 0)
        & (prices[:, 1] >= prices[:, 2])
        & (prices[:, 2] <= prices[:, 0])
        & (prices[:, 0] <= prices[:, 1])
        & (prices[:, 2] <= prices[:, 3])
        & (prices[:, 3] <= prices[:, 1])
    )
    if not valid.all():
        raise ValueError("invalid price geometry or tick volume")
    result = frame.copy()
    result["server_dt"] = pd.to_datetime(result["time_server"], errors="raise")
    result["server_date"] = result["server_dt"].dt.date
    return result


def analyze_frame(frame: pd.DataFrame) -> tuple[dict, list[dict]]:
    data = validate_frame(frame)
    groups = [(day, g.index.to_list()) for day, g in data.groupby("server_date", sort=True)]
    raw_events: list[dict] = []
    conflicts = 0

    for group_pos in range(1, len(groups)):
        _, prior_idx = groups[group_pos - 1]
        current_day, current_idx = groups[group_pos]
        if not 20 <= len(prior_idx) <= 24:
            continue
        prior = data.loc[prior_idx]
        prior_high = float(prior["high"].max())
        prior_low = float(prior["low"].min())
        consumed = False
        for local_pos in range(2, len(current_idx)):
            i2, i1, i0 = current_idx[local_pos - 2 : local_pos + 1]
            e2 = int(data.at[i2, "source_epoch"])
            e1 = int(data.at[i1, "source_epoch"])
            e0 = int(data.at[i0, "source_epoch"])
            if e1 - e2 != 3600 or e0 - e1 != 3600:
                continue
            c2 = float(data.at[i2, "close"])
            c1 = float(data.at[i1, "close"])
            c0 = float(data.at[i0, "close"])
            long_event = c2 <= prior_high and c1 > prior_high and c0 > prior_high and c0 > c1
            short_event = c2 >= prior_low and c1 < prior_low and c0 < prior_low and c0 < c1
            if long_event and short_event:
                conflicts += 1
                continue
            if not (long_event or short_event):
                continue
            if consumed:
                continue
            consumed = True
            next_exact = i0 + 1 < len(data) and int(data.at[i0 + 1, "source_epoch"]) == e0 + 3600
            raw_events.append({
                "hypothesis_id": HYPOTHESIS_ID,
                "decision_source_epoch": e0,
                "decision_time_server": data.at[i0, "server_dt"].isoformat(),
                "decision_year": int(data.at[i0, "server_dt"].year),
                "current_server_date": str(current_day),
                "direction": "LONG" if long_event else "SHORT",
                "prior_day_high": prior_high,
                "prior_day_low": prior_low,
                "close_t_minus_2": c2,
                "close_t_minus_1": c1,
                "close_t": c0,
                "decision_epoch": e0 + 3600,
                "exact_next": bool(next_exact),
            })

    executable = [row for row in raw_events if row["exact_next"]]
    n = len(executable)
    direction_counts = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    year_counts = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (pd.Timestamp(year + 1, 1, 1) - pd.Timestamp(year, 1, 1)).days / 7.0 for year in range(2018, 2023)}
    next_coverage = n / len(raw_events) if raw_events else 0.0
    cadence = n / ELAPSED_WEEKS
    direction_shares = {side: direction_counts[side] / n if n else 0.0 for side in direction_counts}
    max_year_share = max(year_counts.values()) / n if n else 1.0
    year_cadence = {str(year): year_counts[year] / year_weeks[year] for year in year_counts}
    gates = {
        "rows_gte_25000": len(data) >= 25_000,
        "exact_next_gte_0_97": next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "pooled_cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": direction_shares["LONG"] >= 0.30,
        "short_share_gte_0_30": direction_shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_cadence_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in year_cadence.values()),
        "zero_conflicts": conflicts == 0,
    }
    report = {
        "schema_version": "pdac_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "design_rows": len(data),
        "raw_events": len(raw_events),
        "executable_events": n,
        "exact_next_coverage": next_coverage,
        "elapsed_weeks": ELAPSED_WEEKS,
        "cadence_per_week": cadence,
        "direction_counts": direction_counts,
        "direction_shares": direction_shares,
        "year_counts": year_counts,
        "year_cadence": year_cadence,
        "max_year_share": max_year_share,
        "conflicts": conflicts,
        "gates": gates,
        "verdict": "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY_GATE_FAIL",
    }
    return report, executable


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    args = parser.parse_args()
    if sha256_file(args.source) != SOURCE_SHA256:
        raise SystemExit("source hash mismatch")
    frame = pd.read_parquet(
        args.source,
        columns=REQUIRED_COLUMNS,
        filters=[("source_epoch", ">=", START_EPOCH), ("source_epoch", "<", END_EPOCH)],
        engine="pyarrow",
    )
    report, ledger = analyze_frame(frame)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.ledger.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger), encoding="utf-8")


if __name__ == "__main__":
    main()
