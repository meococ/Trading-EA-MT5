#!/usr/bin/env python3
"""Audit S1 phase-context feature candidates from market-phase trade labels.

This is an offline falsification screen.  It does not authorize an EA patch by
itself; it shows whether a proposed S1 phase veto/keep rule survives cost and
time splits before spending MT5 backtest time.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y.%m.%d %H:%M:%S")


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


@dataclass
class Row:
    row_id: int
    entry_ts: datetime
    engine_variant: str
    direction: str
    session_tag: str
    weekday_tag: str
    hour: int
    pnl_net: float
    realized_r: float
    market_phase: str
    trend_delta_atr_36: float
    range_width_atr_36: float
    close_pos_36: float
    cross_count_36: int
    dist_close_to_quarter_pips: float
    vol_rank_20: int
    vol_vs_avg_20: float
    seq_5_high_volume_count: int
    seq_5_climax_count: int
    signal_dragon_slope_atr: float
    signal_trend_slope_atr: float
    signal_h1_bias: int
    signal_h4_bias: int
    signal_body_ratio: float
    signal_level_zone: str

    @property
    def is_s1(self) -> bool:
        return self.engine_variant == "XAU_S1_SWEEP_RECLAIM"

    @property
    def half_year(self) -> str:
        return f"{self.entry_ts.year}H{1 if self.entry_ts.month <= 6 else 2}"

    @property
    def direction_sign(self) -> int:
        if self.direction == "LONG":
            return 1
        if self.direction == "SHORT":
            return -1
        return 0

    @property
    def htf_against_direction(self) -> bool:
        if self.direction_sign > 0:
            return self.signal_h1_bias < 0 or self.signal_h4_bias < 0
        if self.direction_sign < 0:
            return self.signal_h1_bias > 0 or self.signal_h4_bias > 0
        return False

    @property
    def dragon_against_direction(self) -> bool:
        return self.direction_sign != 0 and self.direction_sign * self.signal_dragon_slope_atr < 0


def load_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for item in reader:
            rows.append(
                Row(
                    row_id=safe_int(item.get("row_id")),
                    entry_ts=parse_ts(item.get("entry_server_ts", "")),
                    engine_variant=(item.get("engine_variant") or "UNKNOWN").strip(),
                    direction=(item.get("direction") or "UNKNOWN").strip(),
                    session_tag=(item.get("session_tag") or "UNKNOWN").strip(),
                    weekday_tag=(item.get("weekday_tag") or "UNKNOWN").strip(),
                    hour=safe_int(item.get("hour")),
                    pnl_net=safe_float(item.get("pnl_net")),
                    realized_r=safe_float(item.get("realized_r")),
                    market_phase=(item.get("market_phase") or "UNKNOWN").strip(),
                    trend_delta_atr_36=safe_float(item.get("trend_delta_atr_36")),
                    range_width_atr_36=safe_float(item.get("range_width_atr_36")),
                    close_pos_36=safe_float(item.get("close_pos_36")),
                    cross_count_36=safe_int(item.get("cross_count_36")),
                    dist_close_to_quarter_pips=safe_float(item.get("dist_close_to_quarter_pips")),
                    vol_rank_20=safe_int(item.get("vol_rank_20")),
                    vol_vs_avg_20=safe_float(item.get("vol_vs_avg_20")),
                    seq_5_high_volume_count=safe_int(item.get("seq_5_high_volume_count")),
                    seq_5_climax_count=safe_int(item.get("seq_5_climax_count")),
                    signal_dragon_slope_atr=safe_float(item.get("signal_dragon_slope_atr")),
                    signal_trend_slope_atr=safe_float(item.get("signal_trend_slope_atr")),
                    signal_h1_bias=safe_int(item.get("signal_h1_bias")),
                    signal_h4_bias=safe_int(item.get("signal_h4_bias")),
                    signal_body_ratio=safe_float(item.get("signal_body_ratio")),
                    signal_level_zone=(item.get("signal_level_zone") or "").strip(),
                )
            )
    return rows


def profit_factor(values: Iterable[float]) -> float:
    vals = list(values)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = -sum(v for v in vals if v < 0)
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def stats(rows: list[Row], cost: float = 0.0) -> dict[str, float | int]:
    pnls = [row.pnl_net - cost for row in rows]
    wins = [value for value in pnls if value > 0]
    return {
        "n": len(rows),
        "net": round(sum(pnls), 2),
        "pf": round(profit_factor(pnls), 4),
        "win_rate_pct": round(100.0 * len(wins) / len(rows), 2) if rows else 0.0,
        "avg_r": round(sum(row.realized_r for row in rows) / len(rows), 4) if rows else 0.0,
    }


def half_year_stats(rows: list[Row], cost: float) -> list[dict[str, float | int | str]]:
    buckets: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        buckets[row.half_year].append(row)
    output = []
    for key, members in sorted(buckets.items()):
        item = stats(members, cost)
        item["bucket"] = key
        output.append(item)
    return output


def candidate_rules() -> list[tuple[str, Callable[[Row], bool], str]]:
    return [
        ("base", lambda row: True, "No offline filter."),
        (
            "drop_s1_sideway_any",
            lambda row: not (row.is_s1 and row.market_phase.startswith("SIDEWAY")),
            "Drop S1 in any sideway phase.",
        ),
        (
            "drop_s1_sideway_wide",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE"),
            "Drop S1 only in SIDEWAY_WIDE.",
        ),
        (
            "drop_s1_sideway_wide_cross_ge4",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE" and row.cross_count_36 >= 4),
            "Drop S1 sideway-wide with high midline crossing.",
        ),
        (
            "drop_s1_sideway_wide_cross_ge6",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE" and row.cross_count_36 >= 6),
            "Drop S1 sideway-wide with very high midline crossing.",
        ),
        (
            "keep_s1_impulse_only",
            lambda row: (not row.is_s1) or row.market_phase.startswith("IMPULSE"),
            "Keep S1 only in impulse phases; keep non-S1.",
        ),
        (
            "keep_s1_impulse_or_transition_strong",
            lambda row: (not row.is_s1)
            or row.market_phase.startswith("IMPULSE")
            or (row.market_phase == "TRANSITION" and abs(row.trend_delta_atr_36) >= 1.0 and row.cross_count_36 <= 4),
            "Keep S1 impulse plus directional transition; keep non-S1.",
        ),
        (
            "drop_s1_hour10_17",
            lambda row: not (row.is_s1 and row.hour in {10, 17}),
            "Drop S1 in weak long-window hours 10 and 17.",
        ),
        (
            "drop_s1_sideway_or_hour10_17",
            lambda row: not (row.is_s1 and (row.market_phase.startswith("SIDEWAY") or row.hour in {10, 17})),
            "Drop S1 sideway plus S1 hours 10/17.",
        ),
        (
            "drop_s1_no_near_level_impulse",
            lambda row: not (
                row.is_s1
                and row.market_phase.startswith("IMPULSE")
                and row.dist_close_to_quarter_pips > 8.0
                and row.seq_5_high_volume_count == 0
            ),
            "Drop impulse S1 without nearby quarter-level or high-volume context.",
        ),
        (
            "drop_s1_sideway_against_htf",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE" and row.htf_against_direction),
            "Drop S1 sideway-wide when H1/H4 bias fights the entry direction.",
        ),
        (
            "drop_s1_sideway_against_dragon",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE" and row.dragon_against_direction),
            "Drop S1 sideway-wide when Dragon slope fights the entry direction.",
        ),
        (
            "drop_s1_sideway_weak_body",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE" and row.signal_body_ratio < 0.30),
            "Drop S1 sideway-wide when trigger body is weak.",
        ),
        (
            "drop_s1_sideway_no_level",
            lambda row: not (row.is_s1 and row.market_phase == "SIDEWAY_WIDE" and row.signal_level_zone == "NONE"),
            "Drop S1 sideway-wide when no level zone is attached.",
        ),
        (
            "drop_s1_sideway_htf_or_weak_body",
            lambda row: not (
                row.is_s1
                and row.market_phase == "SIDEWAY_WIDE"
                and (row.htf_against_direction or row.signal_body_ratio < 0.30)
            ),
            "Drop S1 sideway-wide if HTF fights entry or body confirmation is weak.",
        ),
        (
            "keep_s1_impulse_dragon_aligned",
            lambda row: (not row.is_s1) or (row.market_phase.startswith("IMPULSE") and not row.dragon_against_direction),
            "Keep S1 only in impulse phases when Dragon slope does not fight entry.",
        ),
    ]


def evaluate(rows: list[Row], cost: float, min_halfyears: int) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for name, predicate, description in candidate_rules():
        kept = [row for row in rows if predicate(row)]
        removed = len(rows) - len(kept)
        base = stats(kept, 0.0)
        stressed = stats(kept, cost)
        splits = half_year_stats(kept, cost)
        active_splits = [split for split in splits if int(split["n"]) > 0]
        positive_splits = [split for split in active_splits if float(split["net"]) > 0]
        worst_split = min(active_splits, key=lambda split: float(split["net"])) if active_splits else None
        pf_pass = float(stressed["pf"]) >= 1.25
        split_pass = len(active_splits) >= min_halfyears and len(positive_splits) >= math.ceil(0.6 * len(active_splits))
        output.append(
            {
                "candidate": name,
                "description": description,
                "removed_trades": removed,
                "base": base,
                "cost": stressed,
                "active_halfyears": len(active_splits),
                "positive_halfyears_after_cost": len(positive_splits),
                "worst_halfyear_after_cost": worst_split,
                "halfyears_after_cost": splits,
                "research_verdict": "PASS_SCREEN" if pf_pass and split_pass else "REJECT_SCREEN",
            }
        )
    return output


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        f"# Sonic S1 Phase Feature Audit - {payload['run_id']}",
        "",
        f"- Cost per trade: `{payload['cost_per_trade']}`",
        f"- Source rows: `{payload['source_rows']}`",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | Verdict | N | Removed | Net | PF | Cost Net | Cost PF | Positive Half-Years | Worst Half-Year |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["candidates"]:  # type: ignore[index]
        worst = row.get("worst_halfyear_after_cost") or {}
        lines.append(
            "| {candidate} | {verdict} | {n} | {removed} | {net} | {pf} | {cnet} | {cpf} | {pos}/{active} | {worst_bucket} {worst_net} PF {worst_pf} |".format(
                candidate=row["candidate"],
                verdict=row["research_verdict"],
                n=row["base"]["n"],
                removed=row["removed_trades"],
                net=row["base"]["net"],
                pf=row["base"]["pf"],
                cnet=row["cost"]["net"],
                cpf=row["cost"]["pf"],
                pos=row["positive_halfyears_after_cost"],
                active=row["active_halfyears"],
                worst_bucket=worst.get("bucket", ""),
                worst_net=worst.get("net", ""),
                worst_pf=worst.get("pf", ""),
            )
        )
    lines.extend(["", "## Decision", ""])
    lines.extend(f"- {item}" for item in payload["findings"])  # type: ignore[index]
    lines.append("")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    flat_rows = []
    for row in rows:
        worst = row.get("worst_halfyear_after_cost") or {}
        flat_rows.append(
            {
                "candidate": row["candidate"],
                "research_verdict": row["research_verdict"],
                "removed_trades": row["removed_trades"],
                "base_n": row["base"]["n"],
                "base_net": row["base"]["net"],
                "base_pf": row["base"]["pf"],
                "cost_net": row["cost"]["net"],
                "cost_pf": row["cost"]["pf"],
                "positive_halfyears_after_cost": row["positive_halfyears_after_cost"],
                "active_halfyears": row["active_halfyears"],
                "worst_halfyear": worst.get("bucket", ""),
                "worst_halfyear_net": worst.get("net", ""),
                "worst_halfyear_pf": worst.get("pf", ""),
                "description": row["description"],
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Run id or run directory.")
    parser.add_argument("--ea", default=DEFAULT_EA)
    parser.add_argument("--cost-per-trade", type=float, default=0.50)
    parser.add_argument("--min-halfyears", type=int, default=10)
    args = parser.parse_args()

    run_dir = run_dir_for(args.run, args.ea)
    label_path = run_dir / "analysis" / "market_phase_trade_labels.csv"
    if not label_path.exists():
        raise SystemExit(f"market_phase_trade_labels.csv not found: {label_path}")

    rows = load_rows(label_path)
    candidates = evaluate(rows, args.cost_per_trade, args.min_halfyears)
    passers = [row for row in candidates if row["research_verdict"] == "PASS_SCREEN"]
    findings = []
    if not passers:
        findings.append("No S1 phase feature candidate passes the offline cost/split screen. Do not patch EA yet.")
    else:
        findings.append("At least one offline candidate passes first screen; require visual labels and matched MT5 backtest before coding.")
    base = candidates[0]
    findings.append(
        f"Base long-window after cost: n={base['cost']['n']}, net={base['cost']['net']}, PF={base['cost']['pf']}."
    )

    payload = {
        "schema_version": "sonic_s1_phase_feature_audit.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "source": str(label_path),
        "source_rows": len(rows),
        "cost_per_trade": args.cost_per_trade,
        "min_halfyears": args.min_halfyears,
        "candidates": candidates,
        "findings": findings,
        "verdict": "REVIEW_HAS_PASSER" if passers else "REJECT_NO_PASSER",
    }
    out_json = run_dir / "analysis" / "sonic_s1_phase_feature_audit.json"
    out_md = run_dir / "analysis" / "sonic_s1_phase_feature_audit.md"
    out_csv = run_dir / "analysis" / "sonic_s1_phase_feature_audit.csv"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(out_csv, candidates)
    print(json.dumps({"run_id": run_dir.name, "verdict": payload["verdict"], "outputs": [str(out_json), str(out_md)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
