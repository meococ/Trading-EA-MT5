#!/usr/bin/env python3
"""Freeze and materialize two disjoint random-loser casebooks for HYP-006.

This is diagnostic evidence only.  It samples lifecycle positions before chart
rendering, exports bounded M5 bar windows from the same portable FivePercent
terminal history, and writes hash-bound inputs for chart_case_render.py.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006"
RUN_ID = "20260721_190051"
SEED = 5600721
POINT = 0.01
MAX_SPREAD_PRICE = 0.35
SAMPLE_SIZE_PER_WORKER = 20

RUN_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_MZMS_Scalper" / RUN_ID
LIFECYCLE = (
    RUN_DIR
    / "logs"
    / "XAUUSD_LifecycleTrades_HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_85323953.csv"
)
RUN_META = (
    RUN_DIR
    / "logs"
    / "XAUUSD_RunMeta_HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_85323953.json"
)
REPORT = RUN_DIR / "report.html"
SOURCE = RUN_DIR / "snapshot" / "source" / "EA_MZMS_Scalper.mq5"
TERMINAL = (
    ROOT
    / "02. AlphaFactory"
    / "runtime"
    / "mt5-portable-fivepercent"
    / "terminal64.exe"
)
OUT = (
    Path(__file__).resolve().parent
    / "evidence"
    / f"{HYPOTHESIS_ID}_GROK_RANDOM_LOSER_FORENSICS"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_server_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def aggregate_losers() -> tuple[list[dict[str, object]], int]:
    with LIFECYCLE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["position_id"]].append(row)

    losers: list[dict[str, object]] = []
    for position_id, position_rows in grouped.items():
        position_rows.sort(key=lambda row: row["event_time"])
        opens = [row for row in position_rows if row["action"] == "OPEN"]
        closes = [row for row in position_rows if row["action"] == "CLOSE"]
        if len(position_rows) != 2 or len(opens) != 1 or len(closes) != 1:
            raise RuntimeError(
                f"position {position_id} violates exact OPEN/CLOSE lifecycle contract"
            )
        opened, closed = opens[0], closes[0]
        total_net = sum(float(row["deal_net"]) for row in position_rows)
        if total_net >= 0.0:
            continue
        risk_account = float(opened["initial_risk_account"])
        risk_points = float(opened["risk_pts"])
        direction = 1 if opened["order_type"] == "BUY" else -1
        entry = float(opened["price"])
        risk_price = risk_points * POINT
        losers.append(
            {
                "position_id": int(position_id),
                "direction": direction,
                "side": opened["order_type"],
                "entry_time_server": opened["event_time"],
                "entry": entry,
                "exit_time_server": closed["event_time"],
                "exit": float(closed["price"]),
                "risk_pts": risk_points,
                "initial_risk_account": risk_account,
                "net_usd": total_net,
                "net_R": total_net / risk_account if risk_account > 0.0 else None,
                "sl": entry - direction * risk_price if risk_points > 0.0 else None,
                "tp": entry + direction * 1.6 * risk_price if risk_points > 0.0 else None,
            }
        )
    losers.sort(key=lambda item: int(item["position_id"]))
    return losers, len(grouped)


def freeze_samples(losers: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    shuffled = list(losers)
    random.Random(SEED).shuffle(shuffled)
    required = 2 * SAMPLE_SIZE_PER_WORKER
    if len(shuffled) < required:
        raise RuntimeError(f"need {required} losers, found {len(shuffled)}")
    return {
        "worker_a": shuffled[:SAMPLE_SIZE_PER_WORKER],
        "worker_b": shuffled[SAMPLE_SIZE_PER_WORKER:required],
    }


def write_cases(worker: str, records: list[dict[str, object]]) -> Path:
    path = OUT / f"{worker}_cases.csv"
    fields = [
        "case_id",
        "position_id",
        "entry_time_utc",
        "direction",
        "entry",
        "sl",
        "tp",
        "exit_time_utc",
        "exit",
        "reason",
        "label",
        "net_usd",
        "net_R",
        "risk_pts",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, item in enumerate(records, 1):
            case_id = f"{worker[-1].upper()}-{index:02d}-P{item['position_id']}"
            writer.writerow(
                {
                    "case_id": case_id,
                    "position_id": item["position_id"],
                    # chart_case_render requires these legacy column names. Values
                    # remain raw MT5 server clock and are not asserted as UTC.
                    "entry_time_utc": item["entry_time_server"],
                    "direction": item["direction"],
                    "entry": f"{float(item['entry']):.2f}",
                    "sl": "" if item["sl"] is None else f"{float(item['sl']):.2f}",
                    "tp": "" if item["tp"] is None else f"{float(item['tp']):.2f}",
                    "exit_time_utc": item["exit_time_server"],
                    "exit": f"{float(item['exit']):.2f}",
                    "reason": "lifecycle_final_close",
                    "label": (
                        f"P{item['position_id']} | {item['side']} | "
                        f"net ${float(item['net_usd']):.2f} | "
                        f"{float(item['net_R']):.3f}R"
                    ),
                    "net_usd": f"{float(item['net_usd']):.8f}",
                    "net_R": f"{float(item['net_R']):.8f}",
                    "risk_pts": f"{float(item['risk_pts']):.8f}",
                }
            )
    return path


def export_bounded_bars(records: list[dict[str, object]]) -> pd.DataFrame:
    if not mt5.initialize(path=str(TERMINAL), portable=True, timeout=60_000):
        raise RuntimeError(f"MetaTrader5 initialize failed: {mt5.last_error()}")
    frames: list[pd.DataFrame] = []
    try:
        for item in records:
            entry = parse_server_time(str(item["entry_time_server"]))
            exit_time = parse_server_time(str(item["exit_time_server"]))
            start = (entry - timedelta(days=7)).replace(tzinfo=timezone.utc)
            finish = (exit_time + timedelta(days=2)).replace(tzinfo=timezone.utc)
            rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M5, start, finish)
            if rates is None or len(rates) == 0:
                raise RuntimeError(
                    f"no M5 bars for P{item['position_id']}: {mt5.last_error()}"
                )
            frames.append(pd.DataFrame(rates))
    finally:
        mt5.shutdown()

    bars = pd.concat(frames, ignore_index=True)
    bars = bars.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    bars["time_utc"] = pd.to_datetime(bars["time"], unit="s", utc=True).dt.tz_localize(None)
    return bars[
        ["time_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    ]


def price_alignment(
    bars: pd.DataFrame, records: list[dict[str, object]]
) -> list[dict[str, object]]:
    by_time = bars.set_index("time_utc")
    checks: list[dict[str, object]] = []
    for item in records:
        entry_time = pd.Timestamp(parse_server_time(str(item["entry_time_server"]))).floor("5min")
        exit_time = pd.Timestamp(parse_server_time(str(item["exit_time_server"]))).floor("5min")
        if entry_time not in by_time.index or exit_time not in by_time.index:
            raise RuntimeError(f"bar alignment missing for P{item['position_id']}")
        entry_bar = by_time.loc[entry_time]
        exit_bar = by_time.loc[exit_time]
        entry_allowance = MAX_SPREAD_PRICE if int(item["direction"]) > 0 else 0.0
        exit_allowance = MAX_SPREAD_PRICE if int(item["direction"]) < 0 else 0.0
        entry_ok = bool(
            float(entry_bar["low"]) - 1e-9
            <= float(item["entry"])
            <= float(entry_bar["high"]) + entry_allowance + 1e-9
        )
        exit_ok = bool(
            float(exit_bar["low"]) - 1e-9
            <= float(item["exit"])
            <= float(exit_bar["high"]) + exit_allowance + 1e-9
        )
        checks.append(
            {
                "position_id": item["position_id"],
                "entry_bar_time_raw_mt5": entry_time.isoformat(),
                "exit_bar_time_raw_mt5": exit_time.isoformat(),
                "entry_price_aligned_with_bid_bar_plus_frozen_spread_ceiling": entry_ok,
                "exit_price_aligned_with_bid_bar_plus_frozen_spread_ceiling": exit_ok,
            }
        )
    return checks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bars").mkdir(exist_ok=True)
    losers, population_positions = aggregate_losers()
    samples = freeze_samples(losers)
    all_selected = samples["worker_a"] + samples["worker_b"]

    case_paths = {
        worker: write_cases(worker, records) for worker, records in samples.items()
    }
    bars = export_bounded_bars(all_selected)
    bars_path = OUT / "bars" / "XAUUSD_M5_random_loser_windows.parquet"
    bars.to_parquet(bars_path, index=False)
    checks = price_alignment(bars, all_selected)
    if not all(
        check["entry_price_aligned_with_bid_bar_plus_frozen_spread_ceiling"]
        and check["exit_price_aligned_with_bid_bar_plus_frozen_spread_ceiling"]
        for check in checks
    ):
        raise RuntimeError("one or more selected lifecycle prices do not align with M5 bars")

    bars_manifest = {
        "schema_version": "mzms_xau_m5_bounded_bar_export.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "validity_boundary": "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99",
        "source": "MetaTrader5.copy_rates_range from portable FivePercent terminal on D:",
        "terminal_path": str(TERMINAL),
        "symbol": "XAUUSD",
        "timeframe": "M5",
        "clock_note": (
            "time_utc is the renderer compatibility column name; values are raw "
            "MT5 bar epochs aligned directly to lifecycle server-clock timestamps"
        ),
        "bounded_windows": "entry minus 7 calendar days through exit plus 2 days",
        "row_count": len(bars),
        "first_bar": str(bars["time_utc"].min()),
        "last_bar": str(bars["time_utc"].max()),
        "bar_file": str(bars_path),
        "bar_sha256": sha256_file(bars_path),
        "price_alignment": checks,
        "all_40_entry_exit_prices_aligned": True,
        "limitation": (
            "This post-run bounded bar export is not tick parity proof and does not "
            "repair the tester report's invalid 98% history quality."
        ),
    }
    bars_manifest_path = OUT / "bars_manifest.json"
    bars_manifest_path.write_text(
        json.dumps(bars_manifest, indent=2), encoding="utf-8"
    )

    selection_manifest = {
        "schema_version": "mzms_random_loser_selection.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "validity_verdict": "INVALID_ENGINEERING_RUN",
        "invalidity_reason": "tester_history_quality_98_below_frozen_99_gate",
        "selection_frozen_before_individual_chart_rendering": True,
        "population_rule": "aggregate exact OPEN+CLOSE lifecycle rows by position_id",
        "loser_rule": "sum(deal_net) < 0",
        "population_positions": population_positions,
        "losing_positions": len(losers),
        "zero_risk_losing_positions_in_population": sum(
            float(item["risk_pts"]) <= 0.0 for item in losers
        ),
        "prng": "Python random.Random Mersenne Twister",
        "seed": SEED,
        "sampling_method": (
            "sort losing positions by numeric position_id, deterministic shuffle, "
            "worker_a receives indices 0:20 and worker_b receives 20:40"
        ),
        "disjoint_worker_samples": True,
        "sample_size_per_worker": SAMPLE_SIZE_PER_WORKER,
        "source_artifacts": {
            "lifecycle": str(LIFECYCLE),
            "lifecycle_sha256": sha256_file(LIFECYCLE),
            "run_meta": str(RUN_META),
            "run_meta_sha256": sha256_file(RUN_META),
            "report": str(REPORT),
            "report_sha256": sha256_file(REPORT),
            "source_snapshot": str(SOURCE),
            "source_snapshot_sha256": sha256_file(SOURCE),
            "bars_manifest": str(bars_manifest_path),
            "bars_manifest_sha256": sha256_file(bars_manifest_path),
        },
        "workers": {
            worker: {
                "case_csv": str(case_paths[worker]),
                "case_csv_sha256": sha256_file(case_paths[worker]),
                "position_ids": [item["position_id"] for item in records],
                "cases": records,
            }
            for worker, records in samples.items()
        },
        "interpretation_boundary": (
            "Random-loser chart review is mechanism discovery only. It cannot estimate "
            "population prevalence, authorize a subgroup veto, tune a threshold, or "
            "convert this invalid run into valid economic evidence."
        ),
    }
    manifest_path = OUT / "selection_manifest.json"
    manifest_path.write_text(
        json.dumps(selection_manifest, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "selection_manifest": str(manifest_path),
                "bars_manifest": str(bars_manifest_path),
                "bars": str(bars_path),
                "bar_rows": len(bars),
                "worker_a_positions": selection_manifest["workers"]["worker_a"]["position_ids"],
                "worker_b_positions": selection_manifest["workers"]["worker_b"]["position_ids"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
