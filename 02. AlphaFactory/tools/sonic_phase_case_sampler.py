#!/usr/bin/env python3
"""Build a compact phase-specific casebook for MT5-native Sonic snapshots."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"

OUTPUT_COLUMNS = [
    "case_id",
    "symbol",
    "timeframe",
    "entry_server_ts",
    "direction",
    "entry_price",
    "stop_loss",
    "target_price",
    "entry_reason",
    "realized_r",
    "pnl_net",
    "session_bucket",
    "sample_reason",
    "engine_variant",
    "market_phase",
    "hour",
    "weekday_tag",
    "range_width_atr_36",
    "cross_count_36",
    "trend_delta_atr_36",
    "close_pos_36",
    "dist_close_to_quarter_pips",
    "note",
]


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except ValueError:
        return default


def trade_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        row.get("entry_server_ts", ""),
        row.get("direction", ""),
        row.get("engine_variant", ""),
    )


def classify(row: dict[str, str]) -> str | None:
    if row.get("engine_variant") != "XAU_S1_SWEEP_RECLAIM":
        return None
    phase = row.get("market_phase", "")
    pnl = safe_float(row, "pnl_net")
    if phase.startswith("IMPULSE") and pnl > 0:
        return "s1_impulse_win"
    if phase.startswith("IMPULSE") and pnl < 0:
        return "s1_impulse_loss"
    if phase == "SIDEWAY_WIDE" and pnl > 0:
        return "s1_sideway_wide_win"
    if phase == "SIDEWAY_WIDE" and pnl < 0:
        return "s1_sideway_wide_loss"
    if phase == "TRANSITION" and pnl < 0:
        return "s1_transition_loss"
    return None


def newest_standard_trade_file(logs_dir: Path) -> Path:
    files = [
        path
        for path in logs_dir.glob("*_Trades_*.csv")
        if "_PX6_" not in path.name and "_Ghost_" not in path.name
    ]
    if not files:
        raise FileNotFoundError(f"No standard trade sidecar under {logs_dir}")
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def pick_cases(rows: list[dict[str, str]], per_bucket: int) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, str]]] = {
        "s1_sideway_wide_loss": [],
        "s1_impulse_win": [],
        "s1_impulse_loss": [],
        "s1_sideway_wide_win": [],
        "s1_transition_loss": [],
    }
    for row in rows:
        reason = classify(row)
        if reason in buckets:
            row["sample_reason"] = reason
            buckets[reason].append(row)

    for reason, members in buckets.items():
        reverse = reason.endswith("_win")
        members.sort(key=lambda row: safe_float(row, "pnl_net"), reverse=reverse)

    selected: list[dict[str, str]] = []
    for reason in buckets:
        selected.extend(buckets[reason][:per_bucket])
    return selected


def output_row(label_row: dict[str, str], trade_row: dict[str, str], index: int) -> dict[str, str]:
    reason = label_row["sample_reason"]
    case_id = f"{reason}_{index:03d}"
    note = (
        f"{label_row.get('market_phase')} h{label_row.get('hour')} "
        f"widthATR={label_row.get('range_width_atr_36')} cross={label_row.get('cross_count_36')}"
    )
    return {
        "case_id": case_id,
        "symbol": "XAUUSD",
        "timeframe": "PERIOD_M5",
        "entry_server_ts": label_row.get("entry_server_ts", ""),
        "direction": label_row.get("direction", ""),
        "entry_price": trade_row.get("entry_price", ""),
        "stop_loss": trade_row.get("stop_loss", ""),
        "target_price": trade_row.get("target_price", ""),
        "entry_reason": label_row.get("entry_reason", ""),
        "realized_r": label_row.get("realized_r", ""),
        "pnl_net": label_row.get("pnl_net", ""),
        "session_bucket": label_row.get("session_tag", ""),
        "sample_reason": reason,
        "engine_variant": label_row.get("engine_variant", ""),
        "market_phase": label_row.get("market_phase", ""),
        "hour": label_row.get("hour", ""),
        "weekday_tag": label_row.get("weekday_tag", ""),
        "range_width_atr_36": label_row.get("range_width_atr_36", ""),
        "cross_count_36": label_row.get("cross_count_36", ""),
        "trend_delta_atr_36": label_row.get("trend_delta_atr_36", ""),
        "close_pos_36": label_row.get("close_pos_36", ""),
        "dist_close_to_quarter_pips": label_row.get("dist_close_to_quarter_pips", ""),
        "note": note,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Run id or run directory.")
    parser.add_argument("--ea", default=DEFAULT_EA)
    parser.add_argument("--per-bucket", type=int, default=8)
    args = parser.parse_args()

    run_dir = run_dir_for(args.run, args.ea)
    analysis_dir = run_dir / "analysis"
    labels_path = analysis_dir / "market_phase_trade_labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(labels_path)
    trade_path = newest_standard_trade_file(analysis_dir / "logs")
    labels = read_csv(labels_path)
    trades = {trade_key(row): row for row in read_csv(trade_path)}

    selected = pick_cases(labels, args.per_bucket)
    output_rows = []
    missing_join = 0
    for index, label_row in enumerate(selected, start=1):
        trade_row = trades.get(trade_key(label_row))
        if trade_row is None:
            missing_join += 1
            trade_row = {}
        output_rows.append(output_row(label_row, trade_row, index))

    out_dir = analysis_dir / "entry_asof_casebook"
    out_path = out_dir / "cases.csv"
    write_csv(out_path, output_rows)
    manifest = {
        "schema_version": "sonic_phase_case_sampler.v1",
        "run_id": run_dir.name,
        "source_labels": str(labels_path),
        "source_trades": str(trade_path),
        "cases_csv": str(out_path),
        "cases": len(output_rows),
        "missing_trade_joins": missing_join,
        "per_bucket": args.per_bucket,
        "role": "phase-specific MT5 snapshot request source; research only.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
