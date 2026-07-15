#!/usr/bin/env python3
"""Offline SB+Spark option matrix V1 — a priori options, trade-log replay only.

Owner iterate/rebuild mandate 2026-07-14 ~19:09 ICT.
All option IDs below are frozen BEFORE reading outcomes of this batch.
No day/hour veto mining from by_hour/by_weekday. No USBILL retune.
Cost grade remains UNVERIFIED_TESTER_DEFAULT (Demo/tester current).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
RESEARCH = ROOT / "03. EA Developer" / "EA_SonicR" / "research"
PREFLIGHT = RESEARCH / "preflight"
READOUTS = RESEARCH / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

SB_DIR = RUNS / "EA_SilverBullet" / "20260714_002505"
SPARK_DIR = RUNS / "EA_M15SparkAsian" / "20260714_002614"
LONDON_DIR = RUNS / "EA_M15LondonORB" / "20260714_011347"
ITSM_DIR = RUNS / "EA_ITSM" / "20260714_003920"
NY_DIR = RUNS / "EA_M15NYOpenDrive" / "20260714_014224"
PDH_DIR = RUNS / "EA_M15PDHBreak" / "20260714_013818"

OUT_JSON = PREFLIGHT / "20260714_OFFLINE_SB_SPARK_OPTION_MATRIX_V1.json"
OUT_MD = READOUTS / "20260714_OFFLINE_SB_SPARK_OPTION_MATRIX_V1.md"

WINDOW_START = datetime(2021, 1, 1)
WINDOW_END = datetime(2025, 12, 31)
TRAIN_END = datetime(2023, 12, 31, 23, 59, 59)
HOLDOUT_START = datetime(2024, 1, 1)

# ---------------------------------------------------------------------------
# A priori option registry (frozen before outcome ranking)
# ---------------------------------------------------------------------------
# Categories:
#   BASE / WEIGHT / COST_STRESS / TEMPORAL / OVERLAP_EXEC / EXPANSION
# Expansion options are LAWFUL_EXPANSION screens, NOT Phase-0 universe swaps.
OPTION_SPECS = [
    {
        "option_id": "OPT-BASE-SB-SPARK-EQ",
        "category": "BASE",
        "description": "Equal-join SB+Spark (reproduce V1 baseline)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-W-SB70-SPARK30",
        "category": "WEIGHT",
        "description": "Risk weight SB 0.70 / Spark 0.30 (PnL scale)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 0.70 / 0.50, "spark": 0.30 / 0.50},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-W-SB30-SPARK70",
        "category": "WEIGHT",
        "description": "Risk weight SB 0.30 / Spark 0.70 (PnL scale)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 0.30 / 0.50, "spark": 0.70 / 0.50},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-W-SB60-SPARK40",
        "category": "WEIGHT",
        "description": "Risk weight SB 0.60 / Spark 0.40 (PnL scale)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 0.60 / 0.50, "spark": 0.40 / 0.50},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-COST-X1P25",
        "category": "COST_STRESS",
        "description": "Equal-join + loss-side cost stress x1.25",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.25,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-COST-X1P50",
        "category": "COST_STRESS",
        "description": "Equal-join + loss-side cost stress x1.50 (GOAL gate PF>=1.25)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.50,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-COST-X2P00",
        "category": "COST_STRESS",
        "description": "Equal-join + loss-side cost stress x2.00 (GOAL gate PF>=1.00)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 2.00,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-TEMP-TRAIN-21-23",
        "category": "TEMPORAL",
        "description": "Equal-join train window 2021-2023 only",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "train",
    },
    {
        "option_id": "OPT-TEMP-HOLDOUT-24-25",
        "category": "TEMPORAL",
        "description": "Equal-join holdout window 2024-2025 only",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "holdout",
    },
    {
        "option_id": "OPT-OV-SB-PRIORITY-SAME-DAY",
        "category": "OVERLAP_EXEC",
        "description": "Same calendar day: keep SB, drop Spark (SB priority)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "sb_priority_same_day",
        "temporal": "full",
    },
    {
        "option_id": "OPT-OV-SPARK-PRIORITY-SAME-DAY",
        "category": "OVERLAP_EXEC",
        "description": "Same calendar day: keep Spark, drop SB (Spark priority)",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "spark_priority_same_day",
        "temporal": "full",
    },
    {
        "option_id": "OPT-OV-FIRST-ENTRY-SAME-DAY",
        "category": "OVERLAP_EXEC",
        "description": "Same calendar day: keep earliest entry across book only",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "first_entry_same_day",
        "temporal": "full",
    },
    {
        "option_id": "OPT-OV-DROP-SAME-M15-BAR",
        "category": "OVERLAP_EXEC",
        "description": "Same M15 bar: keep earlier sleeve entry, drop later",
        "sleeves": ["sb", "spark"],
        "weight": {"sb": 1.0, "spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "drop_later_same_m15_bar",
        "temporal": "full",
    },
    {
        "option_id": "OPT-EXP-SB-SPARK-LONDON",
        "category": "EXPANSION",
        "description": "LAWFUL_EXPANSION: SB+Spark+LondonORB equal-join (not Phase0)",
        "sleeves": ["sb", "spark", "london"],
        "weight": {"sb": 1.0, "spark": 1.0, "london": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-EXP-SB-SPARK-ITSM",
        "category": "EXPANSION",
        "description": "LAWFUL_EXPANSION control: SB+Spark+ITSM equal-join",
        "sleeves": ["sb", "spark", "itsm"],
        "weight": {"sb": 1.0, "spark": 1.0, "itsm": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-EXP-SB-SPARK-NY",
        "category": "EXPANSION",
        "description": "LAWFUL_EXPANSION: SB+Spark+NYOpenDrive equal-join",
        "sleeves": ["sb", "spark", "ny"],
        "weight": {"sb": 1.0, "spark": 1.0, "ny": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-EXP-SB-SPARK-PDH",
        "category": "EXPANSION",
        "description": "LAWFUL_EXPANSION: SB+Spark+PDHBreak equal-join",
        "sleeves": ["sb", "spark", "pdh"],
        "weight": {"sb": 1.0, "spark": 1.0, "pdh": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-EXP-SB-LONDON",
        "category": "EXPANSION",
        "description": "LAWFUL_EXPANSION pair: SB+LondonORB (Spark off)",
        "sleeves": ["sb", "london"],
        "weight": {"sb": 1.0, "london": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-SLEEVE-SB-ONLY",
        "category": "BASE",
        "description": "Diagnostic: SB A1 alone",
        "sleeves": ["sb"],
        "weight": {"sb": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
    {
        "option_id": "OPT-SLEEVE-SPARK-ONLY",
        "category": "BASE",
        "description": "Diagnostic: Spark alone",
        "sleeves": ["spark"],
        "weight": {"spark": 1.0},
        "cost_stress": 1.0,
        "overlap_policy": "none",
        "temporal": "full",
    },
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def decode_report(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-16-le", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def parse_num(s: str) -> float:
    s = (s or "").replace("\xa0", " ").replace(" ", "").replace(",", "")
    if not s or s == "-":
        return 0.0
    return float(s)


def parse_deals_html(report_path: Path) -> list[dict]:
    html = decode_report(report_path)
    m = re.search(r"<b>\s*(Giao dịch|Deals)\s*</b>", html, re.IGNORECASE)
    if not m:
        raise ValueError(f"Deals section missing: {report_path}")
    section = html[m.end() :]
    stop = re.search(r"<b>\s*(Orders|Lịch sử|History|Graph|Biểu đồ)\s*</b>", section, re.I)
    if stop:
        section = section[: stop.start()]
    tr_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
    td_re = re.compile(r"<td[^>]*>(.*?)</td>", re.I | re.S)
    deals = []
    for row in tr_re.findall(section):
        tds = [re.sub(r"<[^>]+>", "", td).strip() for td in td_re.findall(row)]
        if len(tds) < 11:
            continue
        if tds[0].lower().startswith("thời gian") or tds[0].lower().startswith("time"):
            continue
        if not re.match(r"^\d{4}\.\d{2}\.\d{2}", tds[0]):
            continue
        side = tds[3].lower()
        if side not in ("buy", "sell"):
            continue
        deals.append(
            {
                "time": datetime.strptime(tds[0][:19], "%Y.%m.%d %H:%M:%S"),
                "deal_id": tds[1],
                "symbol": tds[2],
                "side": side,
                "direction": tds[4].lower(),
                "volume": parse_num(tds[5].split("/")[0]) if tds[5] else 0.0,
                "price": parse_num(tds[6]) if tds[6] else 0.0,
                "order": tds[7],
                "commission": parse_num(tds[8]) if len(tds) > 8 else 0.0,
                "swap": parse_num(tds[9]) if len(tds) > 9 else 0.0,
                "profit": parse_num(tds[10]) if len(tds) > 10 else 0.0,
            }
        )
    return deals


def deals_to_trades(deals: list[dict], sleeve: str) -> list[dict]:
    open_by_order: dict[str, dict] = {}
    trades: list[dict] = []
    for d in deals:
        direction = d["direction"]
        if direction in ("in", "vào", "vao"):
            open_by_order[d["order"]] = d
        elif direction in ("out", "ra"):
            entry = open_by_order.pop(d["order"], None)
            pnl = d["profit"] + d["swap"] + d["commission"]
            if entry is not None:
                pnl += entry["commission"] + entry["swap"]
            trades.append(
                {
                    "sleeve": sleeve,
                    "entry_time": entry["time"] if entry else d["time"],
                    "exit_time": d["time"],
                    "side": entry["side"] if entry else d["side"],
                    "pnl": pnl,
                    "symbol": d["symbol"] or (entry["symbol"] if entry else ""),
                }
            )
        else:
            if abs(d["profit"]) > 1e-12:
                trades.append(
                    {
                        "sleeve": sleeve,
                        "entry_time": d["time"],
                        "exit_time": d["time"],
                        "side": d["side"],
                        "pnl": d["profit"] + d["swap"] + d["commission"],
                        "symbol": d["symbol"],
                    }
                )
    return trades


def profit_factor(pnls: list[float]) -> float | None:
    gp = sum(x for x in pnls if x > 0)
    gl = sum(x for x in pnls if x < 0)
    if gl == 0:
        return None if gp == 0 else float("inf")
    return gp / abs(gl)


def elapsed_weeks(start: datetime, end: datetime) -> float:
    return max((end - start).days / 7.0, 1e-9)


def max_drawdown_pct(pnls: list[float], start_equity: float = 100000.0) -> float:
    eq = start_equity
    peak = eq
    max_dd = 0.0
    for p in pnls:
        eq += p
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def year_pos_concentration(trades: list[dict]) -> float | None:
    by_year: dict[int, float] = defaultdict(float)
    for t in trades:
        by_year[t["entry_time"].year] += t["pnl"]
    pos = {y: v for y, v in by_year.items() if v > 0}
    if not pos:
        return None
    total_pos = sum(pos.values())
    if total_pos <= 0:
        return None
    return max(pos.values()) / total_pos


def floor_m15(dt: datetime) -> datetime:
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def load_sleeve(name: str, run_dir: Path) -> dict:
    report = run_dir / "report.html"
    if not report.exists():
        raise FileNotFoundError(report)
    deals = parse_deals_html(report)
    trades = deals_to_trades(deals, name)
    return {
        "name": name,
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "ea": run_dir.parent.name,
        "report_sha256": file_sha256(report),
        "trades": trades,
        "n": len(trades),
        "pf": profit_factor([t["pnl"] for t in trades]),
        "net": sum(t["pnl"] for t in trades),
    }


def apply_temporal(trades: list[dict], temporal: str) -> tuple[list[dict], datetime, datetime]:
    if temporal == "train":
        kept = [t for t in trades if WINDOW_START <= t["entry_time"] <= TRAIN_END]
        return kept, WINDOW_START, TRAIN_END
    if temporal == "holdout":
        kept = [t for t in trades if HOLDOUT_START <= t["entry_time"] <= WINDOW_END]
        return kept, HOLDOUT_START, WINDOW_END
    kept = [t for t in trades if WINDOW_START <= t["entry_time"] <= WINDOW_END]
    return kept, WINDOW_START, WINDOW_END


def apply_overlap(trades: list[dict], policy: str) -> list[dict]:
    if policy == "none" or not trades:
        return trades
    out = list(trades)
    if policy == "sb_priority_same_day":
        sb_days = {t["entry_time"].date() for t in out if t["sleeve"] == "sb"}
        return [t for t in out if t["sleeve"] != "spark" or t["entry_time"].date() not in sb_days]
    if policy == "spark_priority_same_day":
        spark_days = {t["entry_time"].date() for t in out if t["sleeve"] == "spark"}
        return [t for t in out if t["sleeve"] != "sb" or t["entry_time"].date() not in spark_days]
    if policy == "first_entry_same_day":
        by_day: dict = defaultdict(list)
        for t in out:
            by_day[t["entry_time"].date()].append(t)
        kept = []
        for day in sorted(by_day):
            day_trades = sorted(by_day[day], key=lambda x: x["entry_time"])
            kept.append(day_trades[0])
        return kept
    if policy == "drop_later_same_m15_bar":
        by_bar: dict = defaultdict(list)
        for t in out:
            by_bar[floor_m15(t["entry_time"])].append(t)
        kept = []
        for bar in sorted(by_bar):
            bar_trades = sorted(by_bar[bar], key=lambda x: (x["entry_time"], x["sleeve"]))
            kept.append(bar_trades[0])
            # keep non-colliding extras from other bars already handled; within bar keep one
        # Also keep trades whose bars had only one
        return kept
    raise ValueError(policy)


def apply_weight_and_stress(trades: list[dict], weights: dict, stress: float) -> list[dict]:
    out = []
    for t in trades:
        w = weights.get(t["sleeve"], 1.0)
        pnl = t["pnl"] * w
        if stress != 1.0 and pnl < 0:
            pnl = pnl * stress
        nt = deepcopy(t)
        nt["pnl"] = pnl
        nt["weight"] = w
        nt["cost_stress"] = stress
        out.append(nt)
    return out


def evaluate_option(spec: dict, sleeves: dict[str, dict]) -> dict:
    raw: list[dict] = []
    for s in spec["sleeves"]:
        if s not in sleeves:
            return {
                "option_id": spec["option_id"],
                "status": "BLOCKED_MISSING_SLEEVE",
                "missing": s,
            }
        raw.extend(deepcopy(sleeves[s]["trades"]))

    filtered, w_start, w_end = apply_temporal(raw, spec["temporal"])
    filtered = apply_overlap(filtered, spec["overlap_policy"])
    filtered = apply_weight_and_stress(filtered, spec["weight"], spec["cost_stress"])
    filtered = sorted(filtered, key=lambda t: t["entry_time"])

    pnls = [t["pnl"] for t in filtered]
    n = len(filtered)
    weeks = elapsed_weeks(w_start, w_end)
    tpw = n / weeks if weeks else None
    pf = profit_factor(pnls)
    net = sum(pnls)
    exp = (net / n) if n else None
    dd = max_drawdown_pct(pnls) if n else None
    yconc = year_pos_concentration(filtered)

    # Research screens (honest; not confirmed)
    cadence_ok = tpw is not None and 2.0 <= tpw <= 5.0
    pf_ok = pf is not None and pf > 1.30
    # GOAL cost-stress gates when this option IS a stress option
    stress = spec["cost_stress"]
    if stress >= 1.5 - 1e-9 and stress < 2.0 - 1e-9:
        stress_gate_ok = pf is not None and pf >= 1.25
    elif stress >= 2.0 - 1e-9:
        stress_gate_ok = pf is not None and pf >= 1.00
    else:
        stress_gate_ok = None

    if n < 40:
        verdict = "KILL_SAMPLE_TOO_SMALL"
    elif spec["category"] == "COST_STRESS":
        if stress_gate_ok:
            verdict = "PASS_STRESS_GATE_RESEARCH_PROXY"
        else:
            verdict = "FAIL_STRESS_GATE"
    elif cadence_ok and pf_ok:
        verdict = "SURVIVE_NEAR_GOAL_RESEARCH_PROXY"
    elif pf_ok and not cadence_ok:
        verdict = "FAIL_CADENCE"
    elif cadence_ok and not pf_ok:
        verdict = "FAIL_PF"
    else:
        verdict = "FAIL_BOTH"

    # Disposition (killboard)
    if verdict.startswith("SURVIVE") or verdict.startswith("PASS_STRESS"):
        disposition = "PROMOTE_RANK"  # research ranking only
    elif verdict == "FAIL_STRESS_GATE" and stress >= 2.0:
        disposition = "KILL"
    elif verdict in ("FAIL_PF", "FAIL_BOTH", "KILL_SAMPLE_TOO_SMALL"):
        disposition = "KILL" if verdict != "FAIL_PF" or (pf is not None and pf < 1.05) else "PARK"
    elif verdict == "FAIL_CADENCE":
        disposition = "PARK"
    else:
        disposition = "PARK"

    # Soften: for expansion FAIL_PF with pf>=1.20 park for comparison
    if spec["category"] == "EXPANSION" and verdict == "FAIL_PF" and pf is not None and pf >= 1.20:
        disposition = "PARK"

    return {
        "option_id": spec["option_id"],
        "category": spec["category"],
        "description": spec["description"],
        "sleeves": spec["sleeves"],
        "weight": spec["weight"],
        "cost_stress": spec["cost_stress"],
        "overlap_policy": spec["overlap_policy"],
        "temporal": spec["temporal"],
        "window": {"from": w_start.isoformat(), "to": w_end.isoformat(), "elapsed_weeks": weeks},
        "n_trades": n,
        "net_profit": round(net, 2) if net is not None else None,
        "pf": None if pf is None else (None if math.isinf(pf) else round(pf, 4)),
        "tpw_elapsed": None if tpw is None else round(tpw, 4),
        "expectancy": None if exp is None else round(exp, 4),
        "max_dd_pct_path": None if dd is None else round(dd, 4),
        "year_pos_concentration": None if yconc is None else round(yconc, 4),
        "cadence_ok_2_5": cadence_ok,
        "pf_ok_gt_1_30": pf_ok,
        "stress_gate_ok": stress_gate_ok,
        "verdict": verdict,
        "disposition": disposition,
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "confirmed": False,
    }


def write_readout(result: dict) -> None:
    rows = result["options"]
    lines = [
        "# Offline SB+Spark Option Matrix V1",
        "",
        f"Generated: {result['generated_at_ict']} ICT",
        f"Probe ID: `{result['probe_id']}`",
        f"Result SHA256: `{result['result_sha256']}`",
        f"Owner mandate: `{result['owner_mandate']}`",
        "",
        "## Hard caveats",
        "",
        "- Cost grade = `UNVERIFIED_TESTER_DEFAULT` (MetaQuotes-Demo / tester `current`).",
        "- **Not confirmed / not GOAL.** Missing commission ≠ zero cost.",
        "- Options were a priori frozen in the tool before outcome ranking.",
        "- No day/hour veto mining. No USBILL retune. No Spark Mon–Thu densify.",
        "- Expansion options are labeled `LAWFUL_EXPANSION`, not Phase-0 universe membership.",
        "",
        "## Sleeve inputs",
        "",
        "| Sleeve | EA | Run | N | PF | Net | Report SHA256 |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for s in result["sleeves"].values():
        lines.append(
            f"| {s['name']} | {s['ea']} | `{s['run_id']}` | {s['n']} | "
            f"{s['pf']:.4f} | {s['net']:.2f} | `{s['report_sha256']}` |"
        )
    lines += [
        "",
        "## Option outcomes",
        "",
        "| option_id | cat | N | PF | tpw | net | DD% | yconc | verdict | disp |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in rows:
        if r.get("status") == "BLOCKED_MISSING_SLEEVE":
            lines.append(
                f"| `{r['option_id']}` | — | — | — | — | — | — | — | BLOCKED | — |"
            )
            continue
        lines.append(
            f"| `{r['option_id']}` | {r['category']} | {r['n_trades']} | "
            f"{r['pf']} | {r['tpw_elapsed']} | {r['net_profit']} | "
            f"{r['max_dd_pct_path']} | {r['year_pos_concentration']} | "
            f"{r['verdict']} | {r['disposition']} |"
        )

    survivors = [r for r in rows if r.get("disposition") == "PROMOTE_RANK"]
    killed = [r for r in rows if r.get("disposition") == "KILL"]
    parked = [r for r in rows if r.get("disposition") == "PARK"]

    lines += [
        "",
        "## Killboard summary",
        "",
        f"- PROMOTE_RANK (research ranking only): **{len(survivors)}**",
        f"- PARK: **{len(parked)}**",
        f"- KILL: **{len(killed)}**",
        "",
        "### Survivors / best ranks",
        "",
    ]
    for r in sorted(survivors, key=lambda x: (-(x.get("pf") or 0), -(x.get("tpw_elapsed") or 0))):
        lines.append(
            f"- `{r['option_id']}`: PF **{r['pf']}**, tpw **{r['tpw_elapsed']}**, "
            f"net **{r['net_profit']}**, verdict `{r['verdict']}`"
        )
    if not survivors:
        lines.append("- (none)")

    lines += [
        "",
        "### Killed",
        "",
    ]
    for r in killed:
        lines.append(f"- `{r['option_id']}`: `{r['verdict']}` PF={r.get('pf')} tpw={r.get('tpw_elapsed')}")
    if not killed:
        lines.append("- (none)")

    best = result.get("best_current_candidate")
    lines += [
        "",
        "## Best current candidate vs GOAL",
        "",
    ]
    if best:
        lines += [
            f"- **option_id:** `{best['option_id']}`",
            f"- **PF / tpw / net:** {best['pf']} / {best['tpw_elapsed']} / {best['net_profit']}",
            f"- **vs GOAL:** research bars {'PASS' if best.get('pf_ok_gt_1_30') and best.get('cadence_ok_2_5') else 'FAIL'} "
            f"on tester cost; confirmed=NO; Real QFSI still required.",
            f"- **cost stress x1.5/x2:** see `OPT-COST-*` rows.",
        ]
    else:
        lines.append("- No survivor cleared research ranking this batch.")

    lines += [
        "",
        "## What this does NOT authorize",
        "",
        "- No `confirmed` / GOAL claim.",
        "- No post-hoc hour/day filter from this matrix.",
        "- No USBILL rescue.",
        "- Portfolio EA rebuild only if Owner accepts research-scaffold + Phase0 contamination path,",
        "  or a clean new hyp/prereg under iterate mandate.",
        "",
        f"Tool: `preflight/{OUT_JSON.name.replace('.json', '.py')}`",
        f"Machine JSON: `preflight/{OUT_JSON.name}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    sleeve_paths = {
        "sb": SB_DIR,
        "spark": SPARK_DIR,
        "london": LONDON_DIR,
        "itsm": ITSM_DIR,
        "ny": NY_DIR,
        "pdh": PDH_DIR,
    }
    sleeves: dict[str, dict] = {}
    load_errors = {}
    for name, path in sleeve_paths.items():
        try:
            sleeves[name] = load_sleeve(name, path)
        except Exception as exc:  # noqa: BLE001
            load_errors[name] = f"{type(exc).__name__}: {exc}"

    options = [evaluate_option(spec, sleeves) for spec in OPTION_SPECS]

    survivors = [
        r
        for r in options
        if r.get("disposition") == "PROMOTE_RANK" and r.get("category") in ("BASE", "WEIGHT", "OVERLAP_EXEC", "TEMPORAL")
    ]
    # Prefer Phase0-family survivors over expansion for "best"
    if not survivors:
        survivors = [r for r in options if r.get("disposition") == "PROMOTE_RANK"]
    best = None
    if survivors:
        best = sorted(
            survivors,
            key=lambda x: (
                0 if x.get("category") != "EXPANSION" else 1,
                -(x.get("pf") or 0),
                -(x.get("net_profit") or 0),
            ),
        )[0]

    # Temporal joint check
    train = next((r for r in options if r["option_id"] == "OPT-TEMP-TRAIN-21-23"), None)
    holdout = next((r for r in options if r["option_id"] == "OPT-TEMP-HOLDOUT-24-25"), None)
    temporal_joint = {
        "train_pf": train.get("pf") if train else None,
        "train_tpw": train.get("tpw_elapsed") if train else None,
        "holdout_pf": holdout.get("pf") if holdout else None,
        "holdout_tpw": holdout.get("tpw_elapsed") if holdout else None,
        "both_pf_gt_1_30": bool(
            train and holdout and (train.get("pf") or 0) > 1.30 and (holdout.get("pf") or 0) > 1.30
        ),
        "both_cadence_2_5": bool(
            train
            and holdout
            and train.get("cadence_ok_2_5")
            and holdout.get("cadence_ok_2_5")
        ),
    }

    cost_x15 = next((r for r in options if r["option_id"] == "OPT-COST-X1P50"), None)
    cost_x2 = next((r for r in options if r["option_id"] == "OPT-COST-X2P00"), None)

    result = {
        "probe_id": "OFFLINE_SB_SPARK_OPTION_MATRIX_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "owner_mandate": "ITERATE_EXPERIMENT_TEARDOWN_REBUILD_20260714_1909",
        "gpt_status": "GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY",
        "hypothesis_family": "HYP-PORTFOLIO-COMPOSE-001 children / SB+Spark near-GOAL",
        "a_priori_rule": (
            "OPTION_SPECS frozen in this file before outcome ranking; "
            "no readout-mined hour/day veto; expansion labeled separately"
        ),
        "cost_caveat": {
            "status": "tester_current_spread_only",
            "confirmed": False,
            "broker_observed": "MetaQuotes-Demo",
            "fivepercent_real_login_present": False,
            "note": "Loss-side stress is a research proxy, not Real QFSI.",
        },
        "load_errors": load_errors,
        "sleeves": {
            k: {
                "name": v["name"],
                "ea": v["ea"],
                "run_id": v["run_id"],
                "n": v["n"],
                "pf": v["pf"],
                "net": v["net"],
                "report_sha256": v["report_sha256"],
                "run_dir": v["run_dir"],
            }
            for k, v in sleeves.items()
        },
        "options": options,
        "temporal_joint": temporal_joint,
        "cost_stress_summary": {
            "x1_50": {
                "pf": cost_x15.get("pf") if cost_x15 else None,
                "verdict": cost_x15.get("verdict") if cost_x15 else None,
                "gate_need_pf_ge_1_25": True,
            },
            "x2_00": {
                "pf": cost_x2.get("pf") if cost_x2 else None,
                "verdict": cost_x2.get("verdict") if cost_x2 else None,
                "gate_need_pf_ge_1_00": True,
            },
        },
        "best_current_candidate": best,
        "killboard_counts": {
            "PROMOTE_RANK": sum(1 for r in options if r.get("disposition") == "PROMOTE_RANK"),
            "PARK": sum(1 for r in options if r.get("disposition") == "PARK"),
            "KILL": sum(1 for r in options if r.get("disposition") == "KILL"),
            "BLOCKED": sum(1 for r in options if r.get("status") == "BLOCKED_MISSING_SLEEVE"),
        },
        "path_blockers": {
            "real_qfsi": "BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN",
            "phase0_prereg_freeze": "BLOCKED_NOT_READY_FOR_PREREG_FREEZE",
            "confirmed": False,
        },
        "next_auto_moves": [
            "If OPT-BASE / WEIGHT / OVERLAP survivors remain best: keep as research champion; do not claim GOAL.",
            "If cost-stress x1.5/x2 fails hard: prioritize Real QFSI over more Demo Model 0.",
            "If expansion beats Phase0 on PF+cadence without cherry-picking: open NEW child hyp+prereg before MT.",
            "Owner login FivePercentOnline-Real remains the confirmed-grade gate.",
        ],
    }

    # Write JSON without sha first, then embed sha of canonical body
    body_for_hash = dict(result)
    body_for_hash.pop("result_sha256", None)
    raw = json.dumps(body_for_hash, indent=2, sort_keys=True, default=str).encode("utf-8")
    result_sha = hashlib.sha256(raw).hexdigest().upper()
    result["result_sha256"] = result_sha

    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    write_readout(result)
    print(json.dumps({"result_sha256": result_sha, "killboard": result["killboard_counts"], "best": best}, indent=2, default=str))
    print(f"Wrote {OUT_JSON}", file=sys.stderr)
    print(f"Wrote {OUT_MD}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
