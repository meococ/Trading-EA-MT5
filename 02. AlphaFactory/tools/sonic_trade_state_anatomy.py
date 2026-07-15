#!/usr/bin/env python3
"""Join Sonic R trades to StateTelemetry and analyze win/loss anatomy."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


NUMERIC_FEATURES = [
    "min_score",
    "score_delta",
    "structure_score",
    "htf_score",
    "pvsra_score",
    "level_score",
    "time_safety_score",
    "spread_news_penalty",
    "scalp_opportunity_score",
    "classic_setup_score",
    "reentry_setup_score",
    "extension_from_dragon_atr",
    "extension_from_break_atr",
    "sr_runway_pips",
    "wave_smoothness",
    "overlap_ratio",
]

BUCKET_FIELDS = [
    "engine_variant",
    "setup_type",
    "direction",
    "session_tag",
    "weekday_tag",
    "entry_hour",
    "entry_year",
    "entry_month",
    "exit_reason",
    "close_source",
    "retest_dragon_ok",
    "sweep_reclaim_side",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="AlphaFactory run directory.")
    parser.add_argument("--out-json", type=Path, help="Default: <run>/analysis/sonic_trade_state_anatomy.json")
    parser.add_argument("--out-md", type=Path, help="Default: <run>/analysis/sonic_trade_state_anatomy.md")
    parser.add_argument("--out-csv", type=Path, help="Default: <run>/analysis/sonic_trade_state_joined.csv")
    parser.add_argument("--min-bucket-n", type=int, default=5)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def logs_dir(run_dir: Path) -> Path:
    for candidate in (run_dir / "analysis" / "logs", run_dir / "logs"):
        if candidate.exists():
            return candidate
    return run_dir / "analysis" / "logs"


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


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def as_float(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_float(value: Any, default: float = 0.0) -> float:
    number = as_float(value)
    return number if number is not None else default


def as_bool_label(value: Any) -> str:
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "y"}:
        return "true"
    if raw in {"0", "false", "no", "n"}:
        return "false"
    return "unknown"


def ts_part(value: str, part: str) -> str:
    try:
        date, time = value.strip().split(" ")
        year, month, _day = date.split(".")
        hour = time.split(":")[0]
    except ValueError:
        return "UNKNOWN"
    if part == "year":
        return year
    if part == "month":
        return f"{year}-{month}"
    if part == "hour":
        return hour
    return "UNKNOWN"


def variant_alias(value: str) -> str:
    value = (value or "").strip()
    aliases = {
        "classic_wave_break": "CLASSIC",
        "xau_s1_sweep_reclaim": "XAU_S1_SWEEP_RECLAIM",
        "continuation_pullback": "CONTINUATION",
        "reentry": "REENTRY",
    }
    return aliases.get(value.lower(), value)


def load_run(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[Path], list[Path]]:
    manifest = read_json(run_dir / "run_manifest.json")
    log_dir = logs_dir(run_dir)
    state_files = sorted(log_dir.glob("*_StateTelemetry_*.csv"))
    trade_files = sorted(path for path in log_dir.glob("*_Trades_*.csv") if "_PX6_" not in path.name)
    state_rows: list[dict[str, str]] = []
    trade_rows: list[dict[str, str]] = []
    for path in state_files:
        state_rows.extend(read_csv_rows(path))
    for path in trade_files:
        trade_rows.extend(read_csv_rows(path))
    return manifest, state_rows, trade_rows, state_files, trade_files


def state_index(state_rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in state_rows:
        key = (
            row.get("run_id") or "",
            row.get("server_ts") or "",
            row.get("direction") or "",
            row.get("setup_type") or "",
        )
        index[key].append(row)
    return index


def join_rows(state_rows: list[dict[str, str]], trade_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    index = state_index(state_rows)
    joined: list[dict[str, Any]] = []
    unmatched: list[dict[str, str]] = []

    for trade in trade_rows:
        if str(trade.get("is_final_close", "1")).strip() not in {"", "1", "true", "True"}:
            continue
        variant = variant_alias(trade.get("engine_variant") or trade.get("entry_reason") or "")
        key = (
            trade.get("run_id") or "",
            trade.get("entry_server_ts") or "",
            trade.get("direction") or "",
            variant,
        )
        matches = index.get(key, [])
        if not matches:
            unmatched.append(trade)
            continue
        state = matches[0]
        row: dict[str, Any] = {
            "run_id": trade.get("run_id", ""),
            "candidate_id": state.get("candidate_id", ""),
            "engine_variant": variant,
            "setup_type": state.get("setup_type", ""),
            "mode": state.get("mode", ""),
            "direction": trade.get("direction", ""),
            "entry_server_ts": trade.get("entry_server_ts", ""),
            "exit_server_ts": trade.get("exit_server_ts", ""),
            "entry_year": ts_part(trade.get("entry_server_ts", ""), "year"),
            "entry_month": ts_part(trade.get("entry_server_ts", ""), "month"),
            "entry_hour": ts_part(trade.get("entry_server_ts", ""), "hour"),
            "session_tag": trade.get("session_tag", ""),
            "weekday_tag": trade.get("weekday_tag", ""),
            "exit_reason": trade.get("exit_reason", ""),
            "close_source": trade.get("close_source", ""),
            "hold_minutes": safe_float(trade.get("hold_minutes")),
            "realized_r": safe_float(trade.get("realized_r")),
            "pnl_net": safe_float(trade.get("pnl_net")),
            "initial_r_points": safe_float(trade.get("initial_r_points")),
            "news_proximity_min": safe_float(trade.get("news_proximity_min")),
            "is_win": 1 if safe_float(trade.get("pnl_net")) > 0 else 0,
            "is_loss": 1 if safe_float(trade.get("pnl_net")) < 0 else 0,
            "retest_dragon_ok": as_bool_label(state.get("retest_dragon_ok")),
            "sweep_reclaim_side": state.get("sweep_reclaim_side", ""),
            "wave_id": state.get("wave_id", ""),
        }
        for field in NUMERIC_FEATURES:
            row[field] = safe_float(state.get(field))
        joined.append(row)
    return joined, unmatched


def pf(values: Iterable[float]) -> float:
    gross_win = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss == 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    values = sorted(values)
    last = len(values) - 1
    result: dict[str, float] = {}
    for pct in (0, 10, 25, 50, 75, 90, 100):
        idx = int(round((pct / 100.0) * last))
        result[f"p{pct:02d}"] = round(values[idx], 6)
    return result


def trade_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [float(row["pnl_net"]) for row in rows]
    r_values = [float(row["realized_r"]) for row in rows]
    wins = sum(1 for value in pnl if value > 0)
    losses = sum(1 for value in pnl if value < 0)
    return {
        "n": len(rows),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(rows), 6) if rows else 0.0,
        "net": round(sum(pnl), 6),
        "pf": round(pf(pnl), 6),
        "expectancy": round(mean(pnl), 6),
        "r_sum": round(sum(r_values), 6),
        "r_mean": round(mean(r_values), 6),
        "avg_win": round(mean([value for value in pnl if value > 0]), 6),
        "avg_loss": round(mean([value for value in pnl if value < 0]), 6),
    }


def bucket_stats(rows: list[dict[str, Any]], field: str, min_n: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(field, ""))].append(row)
    result = []
    for key, bucket_rows in buckets.items():
        if len(bucket_rows) < min_n:
            continue
        item = {"bucket": key, **trade_stats(bucket_rows)}
        result.append(item)
    return sorted(result, key=lambda row: (row["net"], row["pf"], -row["n"]))


def feature_contrast(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    winners = [float(row[field]) for row in rows if row["pnl_net"] > 0]
    losers = [float(row[field]) for row in rows if row["pnl_net"] < 0]
    all_values = [float(row[field]) for row in rows]
    return {
        "field": field,
        "winner_n": len(winners),
        "loser_n": len(losers),
        "winner_mean": round(mean(winners), 6),
        "loser_mean": round(mean(losers), 6),
        "mean_delta_win_minus_loss": round(mean(winners) - mean(losers), 6),
        "winner_quantiles": quantiles(winners),
        "loser_quantiles": quantiles(losers),
        "all_quantiles": quantiles(all_values),
    }


def decile_buckets(rows: list[dict[str, Any]], field: str, min_n: int) -> list[dict[str, Any]]:
    values = sorted(float(row[field]) for row in rows)
    if not values:
        return []
    thresholds = [values[int(round((pct / 10) * (len(values) - 1)))] for pct in range(1, 10)]

    def bucket(value: float) -> str:
        for idx, threshold in enumerate(thresholds, start=1):
            if value <= threshold:
                return f"d{idx:02d}"
        return "d10"

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[bucket(float(row[field]))].append(row)
    result: list[dict[str, Any]] = []
    for key, bucket_rows in sorted(buckets.items()):
        if len(bucket_rows) < min_n:
            continue
        values_in_bucket = [float(row[field]) for row in bucket_rows]
        result.append(
            {
                "bucket": key,
                "field_min": round(min(values_in_bucket), 6),
                "field_max": round(max(values_in_bucket), 6),
                **trade_stats(bucket_rows),
            }
        )
    return result


def top_rows(rows: list[dict[str, Any]], reverse: bool, limit: int = 12) -> list[dict[str, Any]]:
    selected = sorted(rows, key=lambda row: row["pnl_net"], reverse=reverse)[:limit]
    keys = [
        "candidate_id",
        "engine_variant",
        "direction",
        "entry_server_ts",
        "session_tag",
        "weekday_tag",
        "entry_hour",
        "exit_reason",
        "pnl_net",
        "realized_r",
        "scalp_opportunity_score",
        "extension_from_dragon_atr",
        "sr_runway_pips",
        "wave_smoothness",
        "overlap_ratio",
        "retest_dragon_ok",
        "sweep_reclaim_side",
    ]
    return [{key: row.get(key, "") for key in keys} for row in selected]


def hypothesis_flags(rows: list[dict[str, Any]], min_n: int) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for field in BUCKET_FIELDS:
        for row in bucket_stats(rows, field, min_n):
            if row["net"] < 0 and row["pf"] < 0.9:
                flags.append(
                    {
                        "type": "weak_bucket",
                        "field": field,
                        "bucket": row["bucket"],
                        "n": row["n"],
                        "net": row["net"],
                        "pf": row["pf"],
                        "win_rate": row["win_rate"],
                    }
                )
    for field in ("extension_from_dragon_atr", "sr_runway_pips", "overlap_ratio", "wave_smoothness"):
        for row in decile_buckets(rows, field, min_n):
            if row["net"] < 0 and row["pf"] < 0.9:
                flags.append(
                    {
                        "type": "weak_feature_decile",
                        "field": field,
                        "bucket": row["bucket"],
                        "range": [row["field_min"], row["field_max"]],
                        "n": row["n"],
                        "net": row["net"],
                        "pf": row["pf"],
                        "win_rate": row["win_rate"],
                    }
                )
    return sorted(flags, key=lambda row: (row["net"], row["pf"], -row["n"]))[:30]


def build_audit(run_dir: Path, min_bucket_n: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_dir = run_dir.resolve()
    manifest, state_rows, trade_rows, state_files, trade_files = load_run(run_dir)
    joined, unmatched = join_rows(state_rows, trade_rows)

    field_buckets = {field: bucket_stats(joined, field, min_bucket_n) for field in BUCKET_FIELDS}
    feature_contrasts = {field: feature_contrast(joined, field) for field in NUMERIC_FEATURES}
    feature_deciles = {field: decile_buckets(joined, field, min_bucket_n) for field in NUMERIC_FEATURES}

    audit = {
        "schema_version": "sonic_trade_state_anatomy.v1",
        "run_id": manifest.get("run_id") or run_dir.name,
        "run_dir": str(run_dir),
        "symbol": manifest.get("symbol", ""),
        "period": manifest.get("period", ""),
        "from": manifest.get("from", ""),
        "to": manifest.get("to", ""),
        "model": manifest.get("model", ""),
        "artifacts": {
            "state_files": [rel(path, run_dir) for path in state_files],
            "trade_files": [rel(path, run_dir) for path in trade_files],
        },
        "coverage": {
            "state_rows": len(state_rows),
            "trade_rows": len(trade_rows),
            "joined_final_trades": len(joined),
            "unmatched_final_trades": len(unmatched),
            "join_method": "run_id + entry_server_ts + direction + variant",
        },
        "overall": trade_stats(joined),
        "bucket_stats": field_buckets,
        "feature_contrast": feature_contrasts,
        "feature_deciles": feature_deciles,
        "hypothesis_flags": hypothesis_flags(joined, min_bucket_n),
        "top_losses": top_rows(joined, reverse=False),
        "top_wins": top_rows(joined, reverse=True),
        "unmatched_trade_sample": unmatched[:10],
        "limitations": [
            "Uses heuristic join because Trades CSV has no candidate_id.",
            "Feature buckets are exploratory diagnostics, not pre-registered trading rules.",
            "Do not promote a rule from this report without matched backtest, validation, and cost stress.",
        ],
    }
    return audit, joined


def render_md(audit: dict[str, Any]) -> str:
    lines = [
        f"# Sonic Trade State Anatomy - {audit['run_id']}",
        "",
        "## Run",
        f"- Symbol/TF: `{audit['symbol']} {audit['period']}`",
        f"- Window/model: `{audit['from']} -> {audit['to']}`, Model `{audit['model']}`",
        f"- Joined final trades: `{audit['coverage']['joined_final_trades']}`",
        f"- Unmatched final trades: `{audit['coverage']['unmatched_final_trades']}`",
        "",
        "## Overall",
        f"- Trades: `{audit['overall']['n']}`",
        f"- Net: `{audit['overall']['net']}`",
        f"- PF: `{audit['overall']['pf']}`",
        f"- Win rate: `{audit['overall']['win_rate']}`",
        f"- R sum: `{audit['overall']['r_sum']}`",
        "",
        "## Weak Buckets",
        "| type | field | bucket | range | n | net | PF | win_rate |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in audit["hypothesis_flags"][:20]:
        range_text = ""
        if "range" in row:
            range_text = f"{row['range'][0]}..{row['range'][1]}"
        lines.append(
            f"| `{row['type']}` | `{row['field']}` | `{row['bucket']}` | `{range_text}` | "
            f"{row['n']} | {row['net']} | {row['pf']} | {row['win_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Setup / Variant",
            "| field | bucket | n | net | PF | win_rate | R_sum |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for field in ("engine_variant", "direction", "session_tag", "weekday_tag", "entry_hour", "entry_year"):
        for row in audit["bucket_stats"].get(field, [])[:12]:
            lines.append(
                f"| `{field}` | `{row['bucket']}` | {row['n']} | {row['net']} | {row['pf']} | "
                f"{row['win_rate']} | {row['r_sum']} |"
            )

    lines.extend(
        [
            "",
            "## Feature Contrast",
            "| feature | winner_mean | loser_mean | win_minus_loss | winner_p50 | loser_p50 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for field, row in audit["feature_contrast"].items():
        lines.append(
            f"| `{field}` | {row['winner_mean']} | {row['loser_mean']} | "
            f"{row['mean_delta_win_minus_loss']} | {row['winner_quantiles'].get('p50', '')} | "
            f"{row['loser_quantiles'].get('p50', '')} |"
        )

    lines.extend(
        [
            "",
            "## Top Losses",
            "| entry | variant | dir | hour | weekday | pnl | R | score | ext_dragon | runway | overlap |",
            "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in audit["top_losses"][:8]:
        lines.append(
            f"| `{row['entry_server_ts']}` | `{row['engine_variant']}` | `{row['direction']}` | "
            f"{row['entry_hour']} | `{row['weekday_tag']}` | {row['pnl_net']} | {row['realized_r']} | "
            f"{row['scalp_opportunity_score']} | {row['extension_from_dragon_atr']} | "
            f"{row['sr_runway_pips']} | {row['overlap_ratio']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- Research-only artifact. Use it to form hypotheses, not to authorize rules directly.",
        ]
    )
    for item in audit["limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    out_json = args.out_json or (run_dir / "analysis" / "sonic_trade_state_anatomy.json")
    out_md = args.out_md or (run_dir / "analysis" / "sonic_trade_state_anatomy.md")
    out_csv = args.out_csv or (run_dir / "analysis" / "sonic_trade_state_joined.csv")

    audit, joined = build_audit(run_dir, args.min_bucket_n)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    out_md.write_text(render_md(audit), encoding="utf-8")
    write_csv(out_csv, joined)

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
