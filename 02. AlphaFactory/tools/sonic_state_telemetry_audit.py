#!/usr/bin/env python3
"""Audit Sonic R StateTelemetry sidecars for one AlphaFactory run."""

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


NUMERIC_FIELDS = [
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="AlphaFactory run directory.")
    parser.add_argument("--out-json", type=Path, help="Default: <run>/analysis/sonic_state_telemetry_audit.json")
    parser.add_argument("--out-md", type=Path, help="Default: <run>/analysis/sonic_state_telemetry_audit.md")
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


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def as_float(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def as_hour(value: str) -> int | None:
    # Expected format: YYYY.MM.DD HH:MM:SS. Keep this local and strict enough
    # so malformed timestamps do not silently become useful data.
    try:
        return int(value.strip().split(" ")[1].split(":")[0])
    except (IndexError, TypeError, ValueError):
        return None


def session_bucket(hour: int | None) -> str:
    if hour is None:
        return "UNKNOWN"
    if 0 <= hour < 7:
        return "ASIA"
    if 7 <= hour < 13:
        return "EUROPE_LONDON"
    if 13 <= hour < 21:
        return "NEWYORK"
    return "OFF_HOURS"


def variant_alias(value: str) -> str:
    value = (value or "").strip()
    aliases = {
        "classic_wave_break": "CLASSIC",
        "xau_s1_sweep_reclaim": "XAU_S1_SWEEP_RECLAIM",
        "continuation_pullback": "CONTINUATION",
        "reentry": "REENTRY",
    }
    return aliases.get(value.lower(), value)


def counter_by(rows: Iterable[dict[str, str]], field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[str(row.get(field) or "")] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    values = sorted(values)
    last = len(values) - 1
    output: dict[str, float] = {}
    for pct in range(0, 101, 10):
        idx = int(round((pct / 100.0) * last))
        output[f"p{pct:02d}"] = round(values[idx], 6)
    return output


def numeric_summary(rows: list[dict[str, str]], field: str) -> dict[str, Any]:
    values = [value for row in rows if (value := as_float(row.get(field))) is not None]
    if not values:
        return {"n": 0, "quantiles": {}}
    return {
        "n": len(values),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "mean": round(sum(values) / len(values), 6),
        "quantiles": quantiles(values),
    }


def setup_breakdown(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        buckets[row.get("setup_type") or ""] .append(row)

    result: dict[str, dict[str, Any]] = {}
    for setup, setup_rows in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        result[setup] = {
            "rows": len(setup_rows),
            "directions": counter_by(setup_rows, "direction"),
            "modes": counter_by(setup_rows, "mode"),
            "pre_true": sum(1 for row in setup_rows if as_bool(row.get("pre_score_should_trade"))),
            "post_true": sum(1 for row in setup_rows if as_bool(row.get("post_score_should_trade"))),
            "below_min_score": sum(
                1
                for row in setup_rows
                if (as_float(row.get("scalp_opportunity_score")) is not None)
                and (as_float(row.get("min_score")) is not None)
                and (as_float(row.get("scalp_opportunity_score")) or 0.0) < (as_float(row.get("min_score")) or 0.0)
            ),
            "score": numeric_summary(setup_rows, "scalp_opportunity_score"),
            "score_delta": numeric_summary(setup_rows, "score_delta"),
        }
    return result


def time_breakdown(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_hour: Counter[str] = Counter()
    by_session: Counter[str] = Counter()
    by_session_direction: Counter[str] = Counter()
    for row in rows:
        hour = as_hour(row.get("server_ts") or row.get("bar_time") or "")
        hour_key = f"{hour:02d}" if hour is not None else "UNKNOWN"
        session = session_bucket(hour)
        direction = row.get("direction") or ""
        by_hour[hour_key] += 1
        by_session[session] += 1
        by_session_direction[f"{session}|{direction}"] += 1
    return {
        "by_hour": dict(sorted(by_hour.items())),
        "by_session": dict(sorted(by_session.items(), key=lambda item: item[0])),
        "by_session_direction": dict(sorted(by_session_direction.items())),
    }


def join_trades(state_rows: list[dict[str, str]], trade_rows: list[dict[str, str]]) -> dict[str, Any]:
    state_index: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in state_rows:
        key = (
            row.get("run_id") or "",
            row.get("server_ts") or "",
            row.get("direction") or "",
            row.get("setup_type") or "",
        )
        state_index[key].append(row)

    matched: list[dict[str, str]] = []
    unmatched_trades: list[dict[str, str]] = []
    matched_state_ids: set[str] = set()
    variant_counts: Counter[str] = Counter()
    variant_pnl: defaultdict[str, float] = defaultdict(float)
    variant_r: defaultdict[str, float] = defaultdict(float)
    variant_wins: Counter[str] = Counter()

    for trade in trade_rows:
        variant = variant_alias(trade.get("engine_variant") or trade.get("entry_reason") or "")
        key = (
            trade.get("run_id") or "",
            trade.get("entry_server_ts") or "",
            trade.get("direction") or "",
            variant,
        )
        candidates = state_index.get(key, [])
        if candidates:
            state = candidates[0]
            matched.append(trade)
            matched_state_ids.add(state.get("candidate_id") or f"{key}")
        else:
            unmatched_trades.append(trade)
        pnl = as_float(trade.get("pnl_net")) or 0.0
        realized_r = as_float(trade.get("realized_r")) or 0.0
        variant_counts[variant] += 1
        variant_pnl[variant] += pnl
        variant_r[variant] += realized_r
        if pnl > 0:
            variant_wins[variant] += 1

    final_trades = [row for row in trade_rows if str(row.get("is_final_close", "1")).strip() in {"", "1", "true", "True"}]
    total_pnl = sum((as_float(row.get("pnl_net")) or 0.0) for row in final_trades)

    by_variant: dict[str, Any] = {}
    for variant, count in sorted(variant_counts.items(), key=lambda item: (-item[1], item[0])):
        by_variant[variant] = {
            "trades": count,
            "wins": variant_wins[variant],
            "win_rate": round(variant_wins[variant] / count, 6) if count else 0.0,
            "pnl_net": round(variant_pnl[variant], 6),
            "realized_r_sum": round(variant_r[variant], 6),
        }

    return {
        "method": "heuristic_exact_run_id_entry_server_ts_direction_variant",
        "candidate_id_present_in_trades": bool(trade_rows and "candidate_id" in trade_rows[0]),
        "state_rows": len(state_rows),
        "trade_rows": len(trade_rows),
        "final_trade_rows": len(final_trades),
        "matched_trades": len(matched),
        "unmatched_trades": len(unmatched_trades),
        "matched_state_rows": len(matched_state_ids),
        "match_rate": round(len(matched) / len(trade_rows), 6) if trade_rows else 0.0,
        "total_pnl_net": round(total_pnl, 6),
        "by_engine_variant": by_variant,
        "unmatched_trade_sample": unmatched_trades[:10],
    }


def build_audit(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    analysis_dir = run_dir / "analysis"
    log_dir = logs_dir(run_dir)
    manifest = read_json(run_dir / "run_manifest.json")
    enhanced = read_json(analysis_dir / "enhanced_summary.json")

    state_files = sorted(log_dir.glob("*_StateTelemetry_*.csv"))
    trade_files = sorted(path for path in log_dir.glob("*_Trades_*.csv") if "_PX6_" not in path.name)
    state_rows: list[dict[str, str]] = []
    trade_rows: list[dict[str, str]] = []
    for path in state_files:
        state_rows.extend(read_csv_rows(path))
    for path in trade_files:
        trade_rows.extend(read_csv_rows(path))

    gate_enabled = sum(1 for row in state_rows if as_bool(row.get("score_gate_enabled")))
    pre_true = sum(1 for row in state_rows if as_bool(row.get("pre_score_should_trade")))
    post_true = sum(1 for row in state_rows if as_bool(row.get("post_score_should_trade")))
    blocked_by_score = [
        row
        for row in state_rows
        if as_bool(row.get("pre_score_should_trade")) and not as_bool(row.get("post_score_should_trade"))
    ]
    below_min_fired = [
        row
        for row in state_rows
        if as_bool(row.get("post_score_should_trade"))
        and (as_float(row.get("scalp_opportunity_score")) is not None)
        and (as_float(row.get("min_score")) is not None)
        and (as_float(row.get("scalp_opportunity_score")) or 0.0) < (as_float(row.get("min_score")) or 0.0)
    ]

    return {
        "schema_version": "sonic_state_telemetry_audit.v1",
        "run_id": manifest.get("run_id") or run_dir.name,
        "run_dir": str(run_dir),
        "symbol": manifest.get("symbol", ""),
        "period": manifest.get("period", ""),
        "from": manifest.get("from", ""),
        "to": manifest.get("to", ""),
        "model": manifest.get("model", ""),
        "variant_tag": next(
            (
                part.split("=", 1)[1]
                for part in str(manifest.get("overrides", "")).split(";")
                if part.startswith("InpVariantTag=")
            ),
            "",
        ),
        "artifacts": {
            "state_telemetry_files": [rel(path, run_dir) for path in state_files],
            "trade_files": [rel(path, run_dir) for path in trade_files],
            "log_dir": rel(log_dir, run_dir),
        },
        "enhanced_summary": {
            "n_trades": enhanced.get("n_trades"),
            "net_profit": enhanced.get("net_profit"),
            "profit_factor": enhanced.get("profit_factor"),
            "max_drawdown_pct": enhanced.get("max_drawdown_pct"),
        },
        "coverage": {
            "state_rows": len(state_rows),
            "trade_rows": len(trade_rows),
            "gate_enabled_rows": gate_enabled,
            "gate_disabled_rows": len(state_rows) - gate_enabled,
            "pre_score_should_trade_rows": pre_true,
            "post_score_should_trade_rows": post_true,
            "blocked_by_score_rows": len(blocked_by_score),
            "below_min_score_but_post_true_rows": len(below_min_fired),
        },
        "distributions": {field: numeric_summary(state_rows, field) for field in NUMERIC_FIELDS},
        "breakdowns": {
            "setup_type": setup_breakdown(state_rows),
            "direction": counter_by(state_rows, "direction"),
            "mode": counter_by(state_rows, "mode"),
            "pvsra_side": counter_by(state_rows, "sweep_reclaim_side"),
            "time": time_breakdown(state_rows),
        },
        "score_gate_research": {
            "blocked_by_score_sample": blocked_by_score[:20],
            "below_min_score_but_post_true_sample": below_min_fired[:20],
        },
        "trade_join": join_trades(state_rows, trade_rows),
        "limitations": [
            "Trades CSV currently has no candidate_id; trade join uses run_id+entry_server_ts+direction+variant heuristic.",
            "Session buckets are derived from server_ts hour and are for research attribution only.",
            "This audit reads artifacts only; it does not mutate EA behavior or AlphaFactory outputs.",
        ],
    }


def render_md(audit: dict[str, Any]) -> str:
    coverage = audit["coverage"]
    join = audit["trade_join"]
    lines = [
        f"# Sonic StateTelemetry Audit - {audit['run_id']}",
        "",
        "## Run",
        f"- Symbol/TF: `{audit['symbol']} {audit['period']}`",
        f"- Window/model: `{audit['from']} -> {audit['to']}`, Model `{audit['model']}`",
        f"- Variant tag: `{audit['variant_tag']}`",
        f"- State rows: `{coverage['state_rows']}`",
        f"- Trade rows: `{coverage['trade_rows']}`",
        "",
        "## Gate Readout",
        f"- Gate enabled rows: `{coverage['gate_enabled_rows']}`",
        f"- Pre-score should-trade rows: `{coverage['pre_score_should_trade_rows']}`",
        f"- Post-score should-trade rows: `{coverage['post_score_should_trade_rows']}`",
        f"- Blocked by score rows: `{coverage['blocked_by_score_rows']}`",
        f"- Below-min-score but still post-true rows: `{coverage['below_min_score_but_post_true_rows']}`",
        "",
        "## Setup Breakdown",
        "| setup_type | rows | post_true | below_min | score_p50 | score_p90 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for setup, row in audit["breakdowns"]["setup_type"].items():
        quant = row.get("score", {}).get("quantiles", {})
        lines.append(
            f"| `{setup}` | {row['rows']} | {row['post_true']} | {row['below_min_score']} | "
            f"{quant.get('p50', '')} | {quant.get('p90', '')} |"
        )

    lines.extend(
        [
            "",
            "## Trade Join",
            f"- Method: `{join['method']}`",
            f"- Matched trades: `{join['matched_trades']}/{join['trade_rows']}`",
            f"- Total trade PnL net: `{join['total_pnl_net']}`",
            "",
            "| engine_variant | trades | wins | win_rate | pnl_net | R_sum |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for variant, row in join["by_engine_variant"].items():
        lines.append(
            f"| `{variant}` | {row['trades']} | {row['wins']} | {row['win_rate']} | "
            f"{row['pnl_net']} | {row['realized_r_sum']} |"
        )

    lines.extend(
        [
            "",
            "## Time Buckets",
            "| session | rows |",
            "|---|---:|",
        ]
    )
    for session, count in audit["breakdowns"]["time"]["by_session"].items():
        lines.append(f"| `{session}` | {count} |")

    lines.extend(
        [
            "",
            "## Notes",
            "- Research-only artifact. No deploy/demo/prop claim.",
        ]
    )
    for item in audit["limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    out_json = args.out_json or (run_dir / "analysis" / "sonic_state_telemetry_audit.json")
    out_md = args.out_md or (run_dir / "analysis" / "sonic_state_telemetry_audit.md")

    audit = build_audit(run_dir)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    out_md.write_text(render_md(audit), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
