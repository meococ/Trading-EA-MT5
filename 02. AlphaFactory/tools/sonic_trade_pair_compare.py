#!/usr/bin/env python3
"""Pair Sonic R trades by entry key and compare control vs challenger outcomes."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-run-dir", required=True, type=Path)
    parser.add_argument("--control-run-dir", required=True, type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--out-csv", type=Path)
    parser.add_argument("--top", type=int, default=20)
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


def joined_path(run_dir: Path) -> Path:
    path = run_dir / "analysis" / "sonic_trade_state_joined.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing joined trade/state file: {path}")
    return path


def key(row: dict[str, str]) -> str:
    return "|".join(
        [
            row.get("entry_server_ts", ""),
            row.get("engine_variant", ""),
            row.get("direction", ""),
            row.get("entry_price", ""),
            row.get("initial_stop", ""),
        ]
    )


def index_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    duplicates: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        base = key(row)
        duplicates[base] += 1
        indexed[base if duplicates[base] == 1 else f"{base}|dup{duplicates[base]}"] = row
    return indexed


def stats(rows: list[dict[str, Any]], field: str = "current_pnl") -> dict[str, Any]:
    values = [safe_float(row.get(field, 0.0)) for row in rows]
    wins = sum(value for value in values if value > 0.0)
    losses = -sum(value for value in values if value < 0.0)
    return {
        "n": len(values),
        "net": round(sum(values), 6),
        "pf": round(wins / losses if losses else (999.99 if wins else 0.0), 6),
        "avg": round(sum(values) / len(values), 6) if values else 0.0,
    }


def grouped(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(field, ""))].append(row)
    out: list[dict[str, Any]] = []
    for name, group in buckets.items():
        delta = [safe_float(row.get("delta_pnl", 0.0)) for row in group]
        out.append(
            {
                "field": field,
                "bucket": name,
                "n": len(group),
                "delta_pnl": round(sum(delta), 6),
                "current_net": round(sum(safe_float(row.get("current_pnl", 0.0)) for row in group), 6),
                "control_net": round(sum(safe_float(row.get("control_pnl", 0.0)) for row in group), 6),
            }
        )
    return sorted(out, key=lambda row: (row["delta_pnl"], row["n"]))


def main() -> int:
    args = parse_args()
    current_rows = read_csv_rows(joined_path(args.current_run_dir))
    control_rows = read_csv_rows(joined_path(args.control_run_dir))
    current = index_rows(current_rows)
    control = index_rows(control_rows)

    paired: list[dict[str, Any]] = []
    for trade_key in sorted(set(current) & set(control)):
        c = current[trade_key]
        b = control[trade_key]
        current_pnl = safe_float(c.get("pnl_net"))
        control_pnl = safe_float(b.get("pnl_net"))
        current_r = safe_float(c.get("realized_r"))
        control_r = safe_float(b.get("realized_r"))
        paired.append(
            {
                "entry_server_ts": c.get("entry_server_ts", ""),
                "engine_variant": c.get("engine_variant", ""),
                "direction": c.get("direction", ""),
                "session_tag": c.get("session_tag", ""),
                "weekday_tag": c.get("weekday_tag", ""),
                "entry_hour": c.get("entry_hour", ""),
                "current_exit": c.get("exit_reason", ""),
                "control_exit": b.get("exit_reason", ""),
                "current_pnl": current_pnl,
                "control_pnl": control_pnl,
                "delta_pnl": round(current_pnl - control_pnl, 6),
                "current_r": current_r,
                "control_r": control_r,
                "delta_r": round(current_r - control_r, 6),
                "scalp_opportunity_score": c.get("scalp_opportunity_score", ""),
                "extension_from_dragon_atr": c.get("extension_from_dragon_atr", ""),
                "sr_runway_pips": c.get("sr_runway_pips", ""),
                "retest_dragon_ok": c.get("retest_dragon_ok", ""),
                "sweep_reclaim_side": c.get("sweep_reclaim_side", ""),
            }
        )

    changed = [row for row in paired if row["current_exit"] != row["control_exit"] or abs(safe_float(row["delta_pnl"])) > 0.01]
    top_improvements = sorted(changed, key=lambda row: safe_float(row["delta_pnl"]), reverse=True)[: args.top]
    top_damages = sorted(changed, key=lambda row: safe_float(row["delta_pnl"]))[: args.top]
    summary = {
        "current_run": args.current_run_dir.name,
        "control_run": args.control_run_dir.name,
        "current_only": len(set(current) - set(control)),
        "control_only": len(set(control) - set(current)),
        "paired": len(paired),
        "changed": len(changed),
        "current": stats(paired, "current_pnl"),
        "control": stats(paired, "control_pnl"),
        "delta": {
            "net": round(sum(safe_float(row["delta_pnl"]) for row in paired), 6),
            "r": round(sum(safe_float(row["delta_r"]) for row in paired), 6),
        },
        "by_current_exit": grouped(changed, "current_exit"),
        "by_weekday": grouped(changed, "weekday_tag"),
        "top_improvements": top_improvements,
        "top_damages": top_damages,
    }

    out_json = args.out_json or args.current_run_dir / "analysis" / "sonic_trade_pair_compare.json"
    out_md = args.out_md or args.current_run_dir / "analysis" / "sonic_trade_pair_compare.md"
    out_csv = args.out_csv or args.current_run_dir / "analysis" / "sonic_trade_pair_compare.csv"

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(out_csv, changed)

    lines = [
        f"# Sonic Trade Pair Compare - {args.current_run_dir.name} vs {args.control_run_dir.name}",
        "",
        "## Summary",
        f"- Paired trades: `{summary['paired']}`",
        f"- Changed trades: `{summary['changed']}`",
        f"- Current-only/control-only: `{summary['current_only']}` / `{summary['control_only']}`",
        f"- Net delta: `{summary['delta']['net']}`",
        f"- R delta: `{summary['delta']['r']}`",
        "",
        "## Changed By Current Exit",
        "| exit | n | delta_pnl | current_net | control_net |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["by_current_exit"]:
        lines.append(f"| `{row['bucket']}` | {row['n']} | {row['delta_pnl']} | {row['current_net']} | {row['control_net']} |")
    lines.extend(["", "## Top Improvements", "| entry | dir | weekday | hour | current_exit | control_exit | delta_pnl | delta_r | score | ext | runway |", "|---|---|---|---:|---|---|---:|---:|---:|---:|---:|"])
    for row in top_improvements:
        lines.append(
            f"| `{row['entry_server_ts']}` | `{row['direction']}` | `{row['weekday_tag']}` | {row['entry_hour']} | `{row['current_exit']}` | `{row['control_exit']}` | {row['delta_pnl']} | {row['delta_r']} | {row['scalp_opportunity_score']} | {row['extension_from_dragon_atr']} | {row['sr_runway_pips']} |"
        )
    lines.extend(["", "## Top Damages", "| entry | dir | weekday | hour | current_exit | control_exit | delta_pnl | delta_r | score | ext | runway |", "|---|---|---|---:|---|---|---:|---:|---:|---:|---:|"])
    for row in top_damages:
        lines.append(
            f"| `{row['entry_server_ts']}` | `{row['direction']}` | `{row['weekday_tag']}` | {row['entry_hour']} | `{row['current_exit']}` | `{row['control_exit']}` | {row['delta_pnl']} | {row['delta_r']} | {row['scalp_opportunity_score']} | {row['extension_from_dragon_atr']} | {row['sr_runway_pips']} |"
        )
    lines.extend(["", "## Notes", "- Research-only paired comparison. It explains changed outcomes; it is not a promotion gate."])
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
