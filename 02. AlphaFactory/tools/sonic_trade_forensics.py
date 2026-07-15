#!/usr/bin/env python3
"""Deep Sonic R trade forensics from joined trade/state telemetry."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


NUMERIC_FIELDS = [
    "scalp_opportunity_score",
    "classic_setup_score",
    "structure_score",
    "htf_score",
    "pvsra_score",
    "extension_from_dragon_atr",
    "extension_from_break_atr",
    "sr_runway_pips",
    "wave_smoothness",
    "overlap_ratio",
    "initial_r_points",
    "hold_minutes",
    "news_proximity_min",
]

CATEGORICAL_FIELDS = [
    "engine_variant",
    "direction",
    "session_tag",
    "weekday_tag",
    "entry_hour",
    "entry_year",
    "exit_reason",
    "close_source",
    "retest_dragon_ok",
    "sweep_reclaim_side",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--control-run-dir", type=Path)
    parser.add_argument("--min-removed", type=int, default=4)
    parser.add_argument("--min-kept", type=int, default=40)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--out-rules-csv", type=Path)
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def load_joined(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "analysis" / "sonic_trade_state_joined.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing joined trade/state file: {path}")
    rows: list[dict[str, Any]] = []
    for row in read_csv_rows(path):
        converted: dict[str, Any] = dict(row)
        for field in NUMERIC_FIELDS + ["pnl_net", "realized_r"]:
            converted[field] = safe_float(converted.get(field))
        rows.append(converted)
    return rows


def profit_factor(values: Iterable[float]) -> float:
    gross_win = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss == 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [float(row["pnl_net"]) for row in rows]
    wins = [value for value in pnl if value > 0]
    losses = [value for value in pnl if value < 0]
    return {
        "n": len(rows),
        "net": round(sum(pnl), 6),
        "pf": round(profit_factor(pnl), 6),
        "win_rate": round(len(wins) / len(rows), 6) if rows else 0.0,
        "expectancy": round(sum(pnl) / len(rows), 6) if rows else 0.0,
        "avg_win": round(sum(wins) / len(wins), 6) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 6) if losses else 0.0,
        "r_sum": round(sum(float(row["realized_r"]) for row in rows), 6),
    }


def quantile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = int(round((pct / 100.0) * (len(values) - 1)))
    return values[max(0, min(len(values) - 1, idx))]


def by_field(rows: list[dict[str, Any]], field: str, min_n: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(field, ""))].append(row)
    out = []
    for bucket, bucket_rows in buckets.items():
        if len(bucket_rows) < min_n:
            continue
        out.append({"field": field, "bucket": bucket, **stats(bucket_rows)})
    return sorted(out, key=lambda item: (item["net"], item["pf"], -item["n"]))


@dataclass(frozen=True)
class Rule:
    name: str
    predicate: Callable[[dict[str, Any]], bool]


def make_rules(rows: list[dict[str, Any]]) -> list[Rule]:
    rules: list[Rule] = []

    for field in CATEGORICAL_FIELDS:
        counts = Counter(str(row.get(field, "")) for row in rows)
        for value, count in counts.items():
            if not value or count < 3:
                continue
            rules.append(Rule(f"{field} == {value}", lambda row, f=field, v=value: str(row.get(f, "")) == v))

    for field in NUMERIC_FIELDS:
        values = [float(row[field]) for row in rows]
        if len(set(round(v, 8) for v in values)) < 4:
            continue
        thresholds = sorted({round(quantile(values, pct), 6) for pct in (10, 20, 30, 40, 50, 60, 70, 80, 90)})
        for threshold in thresholds:
            rules.append(Rule(f"{field} <= {threshold}", lambda row, f=field, t=threshold: float(row[f]) <= t))
            rules.append(Rule(f"{field} >= {threshold}", lambda row, f=field, t=threshold: float(row[f]) >= t))

    singles = list(rules)
    important_cats = [rule for rule in singles if any(rule.name.startswith(f"{field} ==") for field in ("entry_hour", "weekday_tag", "direction", "session_tag"))]
    important_nums = [rule for rule in singles if any(rule.name.startswith(field) for field in ("sr_runway_pips", "extension_from_dragon_atr", "overlap_ratio", "scalp_opportunity_score"))]
    for left in important_cats:
        for right in important_nums:
            rules.append(Rule(f"{left.name} AND {right.name}", lambda row, a=left, b=right: a.predicate(row) and b.predicate(row)))

    return rules


def split_delta(total_rows: list[dict[str, Any]], kept_rows: list[dict[str, Any]], split_field: str) -> dict[str, Any]:
    splits = sorted(set(str(row.get(split_field, "")) for row in total_rows))
    out: dict[str, Any] = {}
    for split in splits:
        total = [row for row in total_rows if str(row.get(split_field, "")) == split]
        kept = [row for row in kept_rows if str(row.get(split_field, "")) == split]
        out[split] = {
            "total_net": stats(total)["net"],
            "kept_net": stats(kept)["net"],
            "delta": round(stats(kept)["net"] - stats(total)["net"], 6),
            "total_n": len(total),
            "kept_n": len(kept),
        }
    return out


def evaluate_rules(rows: list[dict[str, Any]], min_removed: int, min_kept: int) -> list[dict[str, Any]]:
    base = stats(rows)
    out: list[dict[str, Any]] = []
    for rule in make_rules(rows):
        removed = [row for row in rows if rule.predicate(row)]
        kept = [row for row in rows if not rule.predicate(row)]
        if len(removed) < min_removed or len(kept) < min_kept:
            continue
        removed_stats = stats(removed)
        kept_stats = stats(kept)
        if removed_stats["net"] >= 0:
            continue
        year_delta = split_delta(rows, kept, "entry_year")
        stable_years = sum(1 for value in year_delta.values() if value["delta"] > 0)
        out.append(
            {
                "rule": rule.name,
                "removed_n": removed_stats["n"],
                "removed_net": removed_stats["net"],
                "removed_pf": removed_stats["pf"],
                "kept_n": kept_stats["n"],
                "kept_net": kept_stats["net"],
                "kept_pf": kept_stats["pf"],
                "kept_win_rate": kept_stats["win_rate"],
                "delta_net": round(kept_stats["net"] - base["net"], 6),
                "delta_pf": round(kept_stats["pf"] - base["pf"], 6),
                "year_delta": year_delta,
                "stable_year_splits": stable_years,
            }
        )
    return sorted(out, key=lambda item: (item["stable_year_splits"], item["delta_net"], item["delta_pf"]), reverse=True)


def trade_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row.get("entry_server_ts", "")), str(row.get("direction", "")), str(row.get("engine_variant", "")))


def compare_control(rows: list[dict[str, Any]], control_rows: list[dict[str, Any]] | None, min_n: int) -> dict[str, Any] | None:
    if not control_rows:
        return None
    current_keys = {trade_key(row) for row in rows}
    control_by_key = {trade_key(row): row for row in control_rows}
    removed = [row for key, row in control_by_key.items() if key not in current_keys]
    kept = [row for key, row in control_by_key.items() if key in current_keys]
    return {
        "control": stats(control_rows),
        "current": stats(rows),
        "removed_from_control": stats(removed),
        "kept_from_control": stats(kept),
        "removed_buckets": {
            "entry_hour": by_field(removed, "entry_hour", max(1, min_n // 2)),
            "weekday_tag": by_field(removed, "weekday_tag", max(1, min_n // 2)),
            "direction": by_field(removed, "direction", max(1, min_n // 2)),
        },
    }


def top_trades(rows: list[dict[str, Any]], reverse: bool, limit: int) -> list[dict[str, Any]]:
    selected = sorted(rows, key=lambda row: float(row["pnl_net"]), reverse=reverse)[:limit]
    fields = [
        "entry_server_ts",
        "engine_variant",
        "direction",
        "session_tag",
        "weekday_tag",
        "entry_hour",
        "exit_reason",
        "pnl_net",
        "realized_r",
        "scalp_opportunity_score",
        "extension_from_dragon_atr",
        "sr_runway_pips",
        "overlap_ratio",
        "retest_dragon_ok",
        "sweep_reclaim_side",
    ]
    return [{field: row.get(field, "") for field in fields} for row in selected]


def format_table(rows: list[dict[str, Any]], fields: list[str], limit: int) -> str:
    if not rows:
        return "_none_\n"
    shown = rows[:limit]
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in shown:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines) + "\n"


def write_markdown(path: Path, data: dict[str, Any], top: int) -> None:
    lines = [
        f"# Sonic Trade Forensics - {data['run_id']}",
        "",
        "## Overall",
        "",
        json.dumps(data["overall"], indent=2),
        "",
    ]
    if data.get("control_compare"):
        lines.extend(
            [
                "## Control Delta",
                "",
                json.dumps(data["control_compare"], indent=2),
                "",
            ]
        )
    lines.extend(
        [
            "## Weak Buckets",
            "",
            format_table(data["weak_buckets"], ["field", "bucket", "n", "net", "pf", "win_rate"], top),
            "## Candidate Block Rules",
            "",
            format_table(data["candidate_block_rules"], ["rule", "removed_n", "removed_net", "kept_n", "kept_net", "kept_pf", "delta_net", "stable_year_splits"], top),
            "## Top Losses",
            "",
            format_table(data["top_losses"], list(data["top_losses"][0].keys()) if data["top_losses"] else [], top),
            "## Top Wins",
            "",
            format_table(data["top_wins"], list(data["top_wins"][0].keys()) if data["top_wins"] else [], top),
            "## Notes",
            "",
            "- Research-only. Rules here are hypotheses until tested in EA with matched controls.",
            "- Exit fields are diagnostic only; do not use exit outcome as an entry rule.",
            "- Stable splits matter more than single-run PF.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = load_joined(args.run_dir)
    control_rows = load_joined(args.control_run_dir) if args.control_run_dir else None

    weak_buckets: list[dict[str, Any]] = []
    for field in CATEGORICAL_FIELDS:
        weak_buckets.extend(by_field(rows, field, args.min_removed))
    weak_buckets = [row for row in weak_buckets if row["net"] < 0]
    weak_buckets = sorted(weak_buckets, key=lambda row: (row["net"], row["pf"], -row["n"]))

    candidate_rules = evaluate_rules(rows, args.min_removed, args.min_kept)
    out = {
        "schema_version": "sonic_trade_forensics.v1",
        "run_id": args.run_dir.name,
        "run_dir": str(args.run_dir),
        "overall": stats(rows),
        "control_compare": compare_control(rows, control_rows, args.min_removed),
        "weak_buckets": weak_buckets[:50],
        "candidate_block_rules": candidate_rules[:100],
        "top_losses": top_trades(rows, reverse=False, limit=args.top),
        "top_wins": top_trades(rows, reverse=True, limit=args.top),
    }

    out_json = args.out_json or args.run_dir / "analysis" / "sonic_trade_forensics.json"
    out_md = args.out_md or args.run_dir / "analysis" / "sonic_trade_forensics.md"
    out_csv = args.out_rules_csv or args.run_dir / "analysis" / "sonic_trade_forensics_rules.csv"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    write_markdown(out_md, out, args.top)
    write_csv(out_csv, candidate_rules)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
