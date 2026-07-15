#!/usr/bin/env python3
"""Audit Sonic R GoldRegimeContext sidecars against final trades.

The EA sidecar is research-only.  This script checks whether the local gold
flow features can explain long-window profit pockets without turning macro
year tags into a hidden hindsight filter.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"
TIME_FORMATS = ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def parse_ts(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def logs_dir(run_dir: Path) -> Path:
    for candidate in (run_dir / "analysis" / "logs", run_dir / "logs"):
        if candidate.exists():
            return candidate
    return run_dir / "analysis" / "logs"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def profit_factor(values: Iterable[float]) -> float:
    vals = list(values)
    gross_win = sum(value for value in vals if value > 0)
    gross_loss = -sum(value for value in vals if value < 0)
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def half_year(ts: datetime) -> str:
    return f"{ts.year}H{1 if ts.month <= 6 else 2}"


def final_trade_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in rows:
        flag = str(row.get("is_final_close", "1")).strip().lower()
        if flag in {"", "1", "true", "yes"}:
            output.append(row)
    return output


def trade_mode(row: dict[str, str]) -> str:
    value = (row.get("engine_variant") or row.get("entry_reason") or "").strip()
    aliases = {
        "classic_wave_break": "CLASSIC",
        "xau_s1_sweep_reclaim": "XAU_S1_SWEEP_RECLAIM",
        "continuation_pullback": "CONTINUATION",
        "reentry": "REENTRY",
    }
    return aliases.get(value.lower(), value)


def build_gold_index(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str, str, str], list[dict[str, str]]], list[dict[str, str]]]:
    index: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    parsed: list[dict[str, str]] = []
    for row in rows:
        row_ts = parse_ts(row.get("server_ts"))
        if row_ts is None:
            continue
        row["_parsed_server_ts"] = row_ts.isoformat()
        parsed.append(row)
        key = (
            row.get("run_id") or "",
            row.get("server_ts") or "",
            row.get("direction") or "",
            row.get("mode") or "",
        )
        index[key].append(row)
    return index, parsed


def find_gold_row(
    trade: dict[str, str],
    index: dict[tuple[str, str, str, str], list[dict[str, str]]],
    parsed_gold: list[dict[str, str]],
) -> dict[str, str] | None:
    mode = trade_mode(trade)
    key = (
        trade.get("run_id") or "",
        trade.get("entry_server_ts") or "",
        trade.get("direction") or "",
        mode,
    )
    if index.get(key):
        return index[key][0]

    trade_ts = parse_ts(trade.get("entry_server_ts"))
    if trade_ts is None:
        return None
    direction = trade.get("direction") or ""
    best: tuple[int, dict[str, str]] | None = None
    for row in parsed_gold:
        if (row.get("run_id") or "") != (trade.get("run_id") or ""):
            continue
        if (row.get("direction") or "") != direction:
            continue
        if (row.get("mode") or "") != mode:
            continue
        row_ts = parse_ts(row.get("server_ts"))
        if row_ts is None:
            continue
        distance = abs(int((row_ts - trade_ts).total_seconds() / 60))
        if distance <= 5 and (best is None or distance < best[0]):
            best = (distance, row)
    return best[1] if best else None


def join_trades(gold_rows: list[dict[str, str]], trade_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index, parsed_gold = build_gold_index(gold_rows)
    joined: list[dict[str, Any]] = []
    unmatched: list[dict[str, str]] = []
    for row_id, trade in enumerate(final_trade_rows(trade_rows), start=1):
        trade_ts = parse_ts(trade.get("entry_server_ts"))
        if trade_ts is None:
            unmatched.append(trade)
            continue
        gold = find_gold_row(trade, index, parsed_gold)
        if gold is None:
            unmatched.append(trade)
            continue
        merged: dict[str, Any] = dict(gold)
        for key, value in trade.items():
            merged[f"trade_{key}"] = value
        merged["row_id"] = row_id
        merged["entry_ts"] = trade_ts.strftime("%Y.%m.%d %H:%M:%S")
        merged["half_year"] = half_year(trade_ts)
        merged["year"] = str(trade_ts.year)
        merged["pnl_net"] = safe_float(trade.get("pnl_net"))
        merged["pnl_after_cost"] = merged["pnl_net"]
        merged["realized_r"] = safe_float(trade.get("realized_r"))
        merged["engine_variant"] = trade_mode(trade)
        joined.append(merged)
    summary = {
        "gold_rows": len(gold_rows),
        "final_trades": len(final_trade_rows(trade_rows)),
        "joined_trades": len(joined),
        "unmatched_trades": len(unmatched),
        "join_rate": round(len(joined) / len(final_trade_rows(trade_rows)), 6) if trade_rows else 0.0,
        "unmatched_sample": unmatched[:10],
    }
    return joined, summary


def summarize(rows: list[dict[str, Any]], cost: float) -> dict[str, Any]:
    pnls = [safe_float(row.get("pnl_net")) - cost for row in rows]
    wins = sum(1 for value in pnls if value > 0)
    by_half: defaultdict[str, float] = defaultdict(float)
    by_year: defaultdict[str, float] = defaultdict(float)
    for row, pnl in zip(rows, pnls):
        by_half[str(row.get("half_year") or "UNKNOWN")] += pnl
        by_year[str(row.get("year") or "UNKNOWN")] += pnl
    return {
        "n": len(rows),
        "net": round(sum(pnls), 2),
        "pf": round(profit_factor(pnls), 4),
        "win_rate_pct": round(100.0 * wins / len(rows), 2) if rows else 0.0,
        "positive_half_years": sum(1 for value in by_half.values() if value > 0),
        "half_years": len(by_half),
        "positive_years": sum(1 for value in by_year.values() if value > 0),
        "years": len(by_year),
    }


def bucket_summary(rows: list[dict[str, Any]], key: str, cost: float, min_n: int = 1) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key, "UNKNOWN") or "UNKNOWN")].append(row)
    output = []
    for bucket, members in buckets.items():
        if len(members) < min_n:
            continue
        item = summarize(members, cost)
        item["bucket"] = bucket
        output.append(item)
    return sorted(output, key=lambda item: (-item["n"], item["bucket"]))


def is_s1(row: dict[str, Any]) -> bool:
    return str(row.get("engine_variant") or row.get("mode") or "") == "XAU_S1_SWEEP_RECLAIM"


def evaluate_candidate(
    rows: list[dict[str, Any]],
    name: str,
    description: str,
    keep: Callable[[dict[str, Any]], bool],
    cost: float,
) -> dict[str, Any]:
    kept = [row for row in rows if keep(row)]
    removed = [row for row in rows if not keep(row)]
    result = summarize(kept, cost)
    result.update(
        {
            "candidate": name,
            "description": description,
            "removed_trades": len(removed),
            "s1_kept": sum(1 for row in kept if is_s1(row)),
            "s1_removed": sum(1 for row in removed if is_s1(row)),
        }
    )
    result["pass_research_gate"] = (
        result["n"] >= 240
        and result["pf"] >= 1.25
        and result["positive_half_years"] >= 9
        and result["positive_years"] >= 4
    )
    return result


def build_candidates(rows: list[dict[str, Any]], cost: float) -> list[dict[str, Any]]:
    checks: list[tuple[str, str, Callable[[dict[str, Any]], bool]]] = [
        ("all_joined", "All joined trades; control for this audit.", lambda row: True),
        (
            "router_drop_s1_5d_against",
            "Keep all non-S1; drop S1 when 5d flow is against trade direction.",
            lambda row: (not is_s1(row)) or str(row.get("flow_alignment_5d")) != "AGAINST",
        ),
        (
            "router_keep_s1_5d_aligned_or_flat",
            "Keep all non-S1; keep S1 only when 5d flow is aligned or flat.",
            lambda row: (not is_s1(row)) or str(row.get("flow_alignment_5d")) in {"ALIGNED", "FLAT"},
        ),
        (
            "router_drop_s1_20d_down",
            "Keep all non-S1; drop S1 in 20d down or strong-down trend buckets.",
            lambda row: (not is_s1(row)) or str(row.get("trend_bucket_20d")) not in {"DOWN", "STRONG_DOWN"},
        ),
        (
            "router_drop_s1_5d_choppy_expanded",
            "Keep all non-S1; drop S1 when 5d context is choppy and expanded.",
            lambda row: (not is_s1(row))
            or not (
                str(row.get("efficiency_bucket_5d")) == "CHOPPY"
                and str(row.get("range_bucket_5d")) == "EXPANDED"
            ),
        ),
        (
            "router_keep_s1_up_or_mixed_flow",
            "Keep all non-S1; keep S1 only outside clean down-flow regimes.",
            lambda row: (not is_s1(row)) or not str(row.get("flow_regime", "")).startswith("DOWN_FLOW"),
        ),
        (
            "s1_only_5d_aligned",
            "S1 only, 5d flow aligned with trade direction.",
            lambda row: is_s1(row) and str(row.get("flow_alignment_5d")) == "ALIGNED",
        ),
        (
            "s1_only_not_20d_down",
            "S1 only, excluding 20d down and strong-down trend buckets.",
            lambda row: is_s1(row) and str(row.get("trend_bucket_20d")) not in {"DOWN", "STRONG_DOWN"},
        ),
    ]
    return [evaluate_candidate(rows, name, desc, keep, cost) for name, desc, keep in checks]


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Sonic Gold Regime Context Audit - {payload['run_id']}",
        "",
        "## Summary",
        "",
        f"- Gold sidecar rows: `{payload['join']['gold_rows']}`",
        f"- Final trades: `{payload['join']['final_trades']}`",
        f"- Joined trades: `{payload['join']['joined_trades']}`",
        f"- Join rate: `{payload['join']['join_rate']}`",
        f"- Cost per trade: `{payload['cost_per_trade']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Candidate Screens",
        "",
        "| Candidate | N | Removed | S1 Kept/Removed | Net | PF | Positive Half-Years | Positive Years | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["candidate_screens"]:
        gate = "PASS" if row["pass_research_gate"] else "FAIL"
        lines.append(
            f"| {row['candidate']} | {row['n']} | {row['removed_trades']} | "
            f"{row['s1_kept']}/{row['s1_removed']} | {row['net']} | {row['pf']} | "
            f"{row['positive_half_years']}/{row['half_years']} | {row['positive_years']}/{row['years']} | {gate} |"
        )
    lines.extend(["", "## Flow Regime Buckets", "", "| Bucket | N | Net | PF | Win% |", "|---|---:|---:|---:|---:|"])
    for row in payload["by_flow_regime"][:20]:
        lines.append(f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} | {row['win_rate_pct']} |")
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
    parser.add_argument("--min-bucket-n", type=int, default=15)
    args = parser.parse_args()

    run_dir = run_dir_for(args.run, args.ea)
    analysis_dir = run_dir / "analysis"
    log_dir = logs_dir(run_dir)
    gold_files = sorted(log_dir.glob("*_GoldRegimeContext_*.csv"))
    trade_files = sorted(path for path in log_dir.glob("*_Trades_*.csv") if "_PX6_" not in path.name)
    if not gold_files:
        raise FileNotFoundError(f"GoldRegimeContext sidecar not found under {log_dir}")
    if not trade_files:
        raise FileNotFoundError(f"Trades sidecar not found under {log_dir}")

    gold_rows: list[dict[str, str]] = []
    trade_rows: list[dict[str, str]] = []
    for path in gold_files:
        gold_rows.extend(read_csv_rows(path))
    for path in trade_files:
        trade_rows.extend(read_csv_rows(path))

    joined, join_summary = join_trades(gold_rows, trade_rows)
    cost = args.cost_per_trade
    for row in joined:
        row["pnl_after_cost"] = safe_float(row.get("pnl_net")) - cost

    candidates = build_candidates(joined, cost)
    passers = [row for row in candidates if row["pass_research_gate"]]
    findings: list[str] = []
    if join_summary["join_rate"] < 0.995:
        findings.append("Join rate is below 99.5%; do not patch EA from this audit until telemetry alignment is fixed.")
    if not passers:
        findings.append("No GoldRegimeContext screen passed cost PF, half-year stability, and year-diversity gates.")
    s1_against = [row for row in joined if is_s1(row) and row.get("flow_alignment_5d") == "AGAINST"]
    if s1_against:
        s = summarize(s1_against, cost)
        findings.append(f"S1 against 5d flow after cost: {s['n']} trades, PF {s['pf']}, net {s['net']}.")
    s1_down20 = [row for row in joined if is_s1(row) and row.get("trend_bucket_20d") in {"DOWN", "STRONG_DOWN"}]
    if s1_down20:
        s = summarize(s1_down20, cost)
        findings.append(f"S1 in 20d down-flow buckets after cost: {s['n']} trades, PF {s['pf']}, net {s['net']}.")

    payload = {
        "schema_version": "sonic_gold_regime_context_audit.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "gold_files": [str(path) for path in gold_files],
        "trade_files": [str(path) for path in trade_files],
        "cost_per_trade": cost,
        "join": join_summary,
        "control_after_cost": summarize(joined, cost),
        "candidate_screens": candidates,
        "by_flow_regime": bucket_summary(joined, "flow_regime", cost, args.min_bucket_n),
        "by_5d_alignment": bucket_summary(joined, "flow_alignment_5d", cost, args.min_bucket_n),
        "by_20d_alignment": bucket_summary(joined, "flow_alignment_20d", cost, args.min_bucket_n),
        "by_5d_trend": bucket_summary(joined, "trend_bucket_5d", cost, args.min_bucket_n),
        "by_20d_trend": bucket_summary(joined, "trend_bucket_20d", cost, args.min_bucket_n),
        "findings": findings,
        "verdict": "RESEARCH_PASSER_FOUND" if passers else "REJECT_NO_PASSER",
    }

    analysis_dir.mkdir(parents=True, exist_ok=True)
    out_json = analysis_dir / "sonic_gold_regime_context_audit.json"
    out_md = analysis_dir / "sonic_gold_regime_context_audit.md"
    out_csv = analysis_dir / "sonic_gold_regime_context_audit_candidates.csv"
    out_joined = analysis_dir / "sonic_gold_regime_joined_trades.csv"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(out_csv, candidates)
    write_csv(out_joined, joined)
    print(json.dumps({"run_id": run_dir.name, "verdict": payload["verdict"], "outputs": [str(out_json), str(out_md)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
