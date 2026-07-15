#!/usr/bin/env python3
"""Build a multi-horizon market-regime profit atlas for Sonic R trades.

This tool is deliberately diagnostic.  It enriches trade labels with rolling
price regimes from the PVSRA/SR sidecar and reports where PnL concentrates by
multi-hour, intraday, multi-day, volatility, chop, and macro-year buckets.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"

TIME_FORMATS = ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def parse_ts(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def newest_file(root: Path, pattern: str) -> Path | None:
    files = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def profit_factor(values: Iterable[float]) -> float:
    vals = list(values)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = -sum(v for v in vals if v < 0)
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def percentile_rank(values: list[float], current: float) -> float:
    if not values:
        return 0.0
    below_or_equal = sum(1 for value in values if value <= current)
    return 100.0 * below_or_equal / len(values)


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def macro_year_tag(year: int) -> str:
    tags = {
        2019: "2019_PRE_COVID_MIXED",
        2020: "2020_COVID_POLICY_SHOCK",
        2021: "2021_REOPENING_YIELD_CHOP",
        2022: "2022_RATE_HIKE_USD_PRESSURE",
        2023: "2023_TRANSITION_DISINFLATION",
        2024: "2024_GOLD_FLOW_MOMENTUM",
        2025: "2025_HIGH_PRICE_UNCERTAINTY",
    }
    return tags.get(year, f"{year}_UNCLASSIFIED")


@dataclass
class TradeLabel:
    row: dict[str, str]
    row_id: int
    entry_ts: datetime
    pnl_net: float
    realized_r: float
    engine_variant: str
    direction: str
    market_phase: str


def load_trade_labels(path: Path) -> list[TradeLabel]:
    output: list[TradeLabel] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = parse_ts(row.get("entry_server_ts", ""))
            if ts is None:
                continue
            output.append(
                TradeLabel(
                    row=row,
                    row_id=safe_int(row.get("row_id")),
                    entry_ts=ts,
                    pnl_net=safe_float(row.get("pnl_net")),
                    realized_r=safe_float(row.get("realized_r")),
                    engine_variant=(row.get("engine_variant") or "UNKNOWN").strip(),
                    direction=(row.get("direction") or "UNKNOWN").strip(),
                    market_phase=(row.get("market_phase") or "UNKNOWN").strip(),
                )
            )
    return output


def trend_bucket(delta_atr: float, strong: float = 5.0, mild: float = 2.0) -> str:
    if delta_atr >= strong:
        return "STRONG_UP"
    if delta_atr >= mild:
        return "UP"
    if delta_atr <= -strong:
        return "STRONG_DOWN"
    if delta_atr <= -mild:
        return "DOWN"
    return "FLAT"


def vol_bucket(percentile: float) -> str:
    if percentile >= 80:
        return "HIGH_VOL"
    if percentile <= 25:
        return "LOW_VOL"
    return "NORMAL_VOL"


def efficiency_bucket(value: float) -> str:
    if value >= 0.42:
        return "EFFICIENT_TREND"
    if value <= 0.18:
        return "CHOPPY"
    return "MIXED"


def range_bucket(width_atr: float) -> str:
    if width_atr <= 3.0:
        return "COMPRESSED"
    if width_atr <= 6.0:
        return "BALANCED"
    return "EXPANDED"


def direction_sign(direction: str) -> int:
    if direction == "LONG":
        return 1
    if direction == "SHORT":
        return -1
    return 0


def enrich_from_pvsra(pvsra_path: Path, labels: list[TradeLabel]) -> dict[int, dict[str, Any]]:
    lookup: dict[datetime, list[int]] = defaultdict(list)
    for label in labels:
        for offset in (-5, 0, 5):
            lookup[label.entry_ts + timedelta(minutes=offset)].append(label.row_id)

    enriched: dict[int, dict[str, Any]] = {}
    best_distance: dict[int, int] = {}

    closes: deque[float] = deque(maxlen=5760)
    highs: deque[float] = deque(maxlen=5760)
    lows: deque[float] = deque(maxlen=5760)
    ranges: deque[float] = deque(maxlen=5760)
    abs_changes: deque[float] = deque(maxlen=5760)
    atr20_history: deque[float] = deque(maxlen=1440)

    previous_close: float | None = None

    with pvsra_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = parse_ts(row.get("server_ts", ""))
            close = safe_float(row.get("bar_close"))
            high = safe_float(row.get("bar_high"))
            low = safe_float(row.get("bar_low"))
            bar_range = max(safe_float(row.get("bar_range_pips")), high - low, 0.000001)
            if close <= 0 or high <= 0 or low <= 0:
                continue

            if previous_close is None:
                change = 0.0
            else:
                change = abs(close - previous_close)
            previous_close = close

            closes.append(close)
            highs.append(high)
            lows.append(low)
            ranges.append(bar_range)
            abs_changes.append(change)
            atr20 = mean(list(ranges)[-20:])
            atr20_history.append(atr20)

            if ts is None or ts not in lookup:
                continue

            close_list = list(closes)
            high_list = list(highs)
            low_list = list(lows)
            range_list = list(ranges)
            change_list = list(abs_changes)
            atr_base = max(atr20, 0.000001)

            def window_metrics(n: int) -> dict[str, Any]:
                if len(close_list) < n:
                    return {
                        f"delta_atr_{n}": None,
                        f"trend_bucket_{n}": "UNKNOWN",
                        f"range_width_atr_{n}": None,
                        f"range_bucket_{n}": "UNKNOWN",
                        f"efficiency_{n}": None,
                        f"efficiency_bucket_{n}": "UNKNOWN",
                    }
                c = close_list[-n:]
                h = high_list[-n:]
                l = low_list[-n:]
                changes = change_list[-n:]
                delta = c[-1] - c[0]
                delta_atr = delta / atr_base
                width_atr = (max(h) - min(l)) / atr_base
                path = max(sum(changes), 0.000001)
                efficiency = abs(delta) / path
                return {
                    f"delta_atr_{n}": round(delta_atr, 4),
                    f"trend_bucket_{n}": trend_bucket(delta_atr),
                    f"range_width_atr_{n}": round(width_atr, 4),
                    f"range_bucket_{n}": range_bucket(width_atr),
                    f"efficiency_{n}": round(efficiency, 4),
                    f"efficiency_bucket_{n}": efficiency_bucket(efficiency),
                }

            features: dict[str, Any] = {
                "joined_server_ts": ts.strftime("%Y.%m.%d %H:%M:%S"),
                "atr20_pips": round(atr20, 4),
                "atr20_percentile_1440": round(percentile_rank(list(atr20_history), atr20), 2),
            }
            features["vol_regime_1440"] = vol_bucket(features["atr20_percentile_1440"])
            for n in (36, 96, 288, 1440, 2880, 5760):
                features.update(window_metrics(n))

            for row_id in lookup[ts]:
                distance = abs(int((ts - next(lbl.entry_ts for lbl in labels if lbl.row_id == row_id)).total_seconds() / 60))
                if row_id not in best_distance or distance < best_distance[row_id]:
                    enriched[row_id] = dict(features)
                    enriched[row_id]["regime_join_distance_minutes"] = distance
                    best_distance[row_id] = distance

    return enriched


def bucket_summary(rows: list[dict[str, Any]], key: str, cost: float = 0.0, min_n: int = 1) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key, "UNKNOWN") or "UNKNOWN")].append(row)
    output: list[dict[str, Any]] = []
    for bucket, members in buckets.items():
        if len(members) < min_n:
            continue
        pnls = [safe_float(row.get("pnl_net")) - cost for row in members]
        wins = [value for value in pnls if value > 0]
        output.append(
            {
                "bucket": bucket,
                "n": len(members),
                "net": round(sum(pnls), 2),
                "pf": round(profit_factor(pnls), 4),
                "win_rate_pct": round(100.0 * len(wins) / len(members), 2),
                "avg_r": round(mean(safe_float(row.get("realized_r")) for row in members), 4),
            }
        )
    return sorted(output, key=lambda item: (-item["n"], item["bucket"]))


def combo_summary(rows: list[dict[str, Any]], keys: list[str], cost: float, min_n: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        bucket = tuple(str(row.get(key, "UNKNOWN") or "UNKNOWN") for key in keys)
        buckets[bucket].append(row)
    output = []
    for bucket, members in buckets.items():
        if len(members) < min_n:
            continue
        pnls = [safe_float(row.get("pnl_net")) - cost for row in members]
        output.append(
            {
                "bucket": " | ".join(bucket),
                "n": len(members),
                "net": round(sum(pnls), 2),
                "pf": round(profit_factor(pnls), 4),
                "keys": dict(zip(keys, bucket)),
            }
        )
    return sorted(output, key=lambda item: item["net"])


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Sonic Market Regime Profit Atlas - {payload['run_id']}",
        "",
        "## Summary",
        "",
        f"- Trades: `{payload['trade_count']}`",
        f"- Enriched: `{payload['enriched_count']}`",
        f"- Cost per trade: `{payload['cost_per_trade']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Macro Year Tags",
        "",
        "| Tag | N | Net After Cost | PF | Win% |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["by_macro_year_after_cost"]:
        lines.append(f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} | {row['win_rate_pct']} |")
    lines.extend(["", "## Volatility Regime", "", "| Vol | N | Net After Cost | PF | Win% |", "|---|---:|---:|---:|---:|"])
    for row in payload["by_vol_regime_after_cost"]:
        lines.append(f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} | {row['win_rate_pct']} |")
    lines.extend(["", "## Worst Regime Combos", "", "| Combo | N | Net After Cost | PF |", "|---|---:|---:|---:|"])
    for row in payload["worst_combos_after_cost"][:15]:
        lines.append(f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} |")
    lines.extend(["", "## Best Regime Combos", "", "| Combo | N | Net After Cost | PF |", "|---|---:|---:|---:|"])
    for row in payload["best_combos_after_cost"][:15]:
        lines.append(f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} |")
    lines.extend(["", "## Findings", ""])
    for finding in payload["findings"]:
        lines.append(f"- {finding}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Run id or run directory.")
    parser.add_argument("--ea", default=DEFAULT_EA)
    parser.add_argument("--cost-per-trade", type=float, default=0.50)
    parser.add_argument("--min-combo-n", type=int, default=20)
    args = parser.parse_args()

    run_dir = run_dir_for(args.run, args.ea)
    analysis_dir = run_dir / "analysis"
    logs_dir = analysis_dir / "logs"
    labels_path = analysis_dir / "market_phase_trade_labels.csv"
    pvsra_path = newest_file(logs_dir, "*_PVSRA_SR_Fields_*.csv")
    if not labels_path.exists():
        raise FileNotFoundError(labels_path)
    if pvsra_path is None:
        raise FileNotFoundError(f"PVSRA sidecar not found under {logs_dir}")

    labels = load_trade_labels(labels_path)
    enriched = enrich_from_pvsra(pvsra_path, labels)
    rows: list[dict[str, Any]] = []
    for label in labels:
        row = dict(label.row)
        row.update(enriched.get(label.row_id, {}))
        row["macro_year_tag"] = macro_year_tag(label.entry_ts.year)
        row["half_year"] = f"{label.entry_ts.year}H{1 if label.entry_ts.month <= 6 else 2}"
        sign = direction_sign(label.direction)
        delta_288 = safe_float(row.get("delta_atr_288"))
        delta_1440 = safe_float(row.get("delta_atr_1440"))
        delta_2880 = safe_float(row.get("delta_atr_2880"))
        delta_5760 = safe_float(row.get("delta_atr_5760"))
        row["trade_aligns_1d_trend"] = "YES" if sign and sign * delta_288 > 0 else "NO"
        row["trade_aligns_5d_trend"] = "YES" if sign and sign * delta_1440 > 0 else "NO"
        row["trade_aligns_10d_trend"] = "YES" if sign and sign * delta_2880 > 0 else "NO"
        row["trade_aligns_20d_trend"] = "YES" if sign and sign * delta_5760 > 0 else "NO"
        rows.append(row)

    cost = args.cost_per_trade
    combo_keys = ["engine_variant", "macro_year_tag", "vol_regime_1440", "efficiency_bucket_288", "range_bucket_288"]
    combos = combo_summary(rows, combo_keys, cost, args.min_combo_n)
    best = list(reversed(combos))

    by_macro = bucket_summary(rows, "macro_year_tag", cost)
    by_hy = bucket_summary(rows, "half_year", cost)
    by_vol = bucket_summary(rows, "vol_regime_1440", cost)
    by_eff_288 = bucket_summary(rows, "efficiency_bucket_288", cost)
    by_range_288 = bucket_summary(rows, "range_bucket_288", cost)
    by_align_1d = bucket_summary(rows, "trade_aligns_1d_trend", cost)
    by_align_5d = bucket_summary(rows, "trade_aligns_5d_trend", cost)
    by_align_10d = bucket_summary(rows, "trade_aligns_10d_trend", cost)
    by_align_20d = bucket_summary(rows, "trade_aligns_20d_trend", cost)

    findings: list[str] = []
    positive_macro = [row["bucket"] for row in by_macro if float(row["net"]) > 0]
    if positive_macro and all(bucket.startswith(("2024", "2025")) for bucket in positive_macro):
        findings.append("Positive cost-adjusted macro-year buckets are concentrated in 2024-2025; treat the current edge as flow/regime-dependent.")
    weak_halfyears = [row for row in by_hy if int(row["n"]) >= 20 and float(row["pf"]) < 0.9]
    if weak_halfyears:
        findings.append(
            "Weak half-years remain after cost: "
            + ", ".join(f"{row['bucket']} PF {row['pf']}" for row in weak_halfyears[:6])
        )
    if combos and float(best[0]["pf"]) < 1.25:
        findings.append("No multi-regime combo with the configured minimum sample reaches cost-adjusted PF 1.25.")

    payload = {
        "schema_version": "sonic_market_regime_profit_atlas.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "labels": str(labels_path),
        "pvsra": str(pvsra_path),
        "trade_count": len(labels),
        "enriched_count": len(enriched),
        "cost_per_trade": cost,
        "min_combo_n": args.min_combo_n,
        "verdict": "REVIEW_REGIME_DEPENDENT",
        "by_macro_year_after_cost": by_macro,
        "by_half_year_after_cost": by_hy,
        "by_vol_regime_after_cost": by_vol,
        "by_efficiency_288_after_cost": by_eff_288,
        "by_range_288_after_cost": by_range_288,
        "by_trade_aligns_1d_trend_after_cost": by_align_1d,
        "by_trade_aligns_5d_trend_after_cost": by_align_5d,
        "by_trade_aligns_10d_trend_after_cost": by_align_10d,
        "by_trade_aligns_20d_trend_after_cost": by_align_20d,
        "worst_combos_after_cost": combos[:30],
        "best_combos_after_cost": best[:30],
        "findings": findings,
    }

    out_json = analysis_dir / "market_regime_profit_atlas.json"
    out_md = analysis_dir / "market_regime_profit_atlas.md"
    out_csv = analysis_dir / "market_regime_profit_atlas_by_macro.csv"
    out_combo_csv = analysis_dir / "market_regime_profit_atlas_combos.csv"
    out_enriched_csv = analysis_dir / "market_regime_trade_labels.csv"

    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(out_csv, by_macro)
    write_csv(out_combo_csv, combos)
    write_csv(out_enriched_csv, rows)
    print(json.dumps({"run_id": run_dir.name, "verdict": payload["verdict"], "outputs": [str(out_json), str(out_md)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
