#!/usr/bin/env python3
"""Deeper cost-stress V3 — MaxKZ2 single + best books.

A priori ladders frozen before ranking:
  - Dollar haircut per trade: fine grid 0..12
  - Loss-side multiplier stress: x1.0 / x1.25 / x1.5 / x2.0 (GOAL-style)
  - Books: MaxKZ2 alone, A1+Spark (RAW + CAPNORM x10), MaxKZ2+Spark (RAW + CAPNORM)

Cost grade remains UNVERIFIED_TESTER_DEFAULT. Not confirmed / not GOAL.
Does not mine hour/day from readouts. Complements haircut V2.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
RESEARCH = ROOT / "03. EA Developer" / "EA_SonicR" / "research"
PREFLIGHT = RESEARCH / "preflight"
READOUTS = RESEARCH / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

OUT_JSON = PREFLIGHT / "20260714_OFFLINE_SB_MAXKZ2_COST_STRESS_V3.json"
OUT_MD = READOUTS / "20260714_OFFLINE_SB_MAXKZ2_COST_STRESS_V3.md"

_SPEC = importlib.util.spec_from_file_location(
    "opt_v1",
    str(PREFLIGHT / "20260714_OFFLINE_SB_SPARK_OPTION_MATRIX_V1.py"),
)
v1 = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(v1)

# Frozen a priori
HAIRCUTS_USD = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]
LOSS_STRESS = [1.0, 1.25, 1.50, 2.00]

MAXKZ2_DIR = RUNS / "EA_SilverBullet" / "20260714_192304"
A1_DIR = RUNS / "EA_SilverBullet" / "20260714_002505"
SPARK_DIR = RUNS / "EA_M15SparkAsian" / "20260714_002614"

BOOKS = [
    {
        "book_id": "SINGLE-MAXKZ2",
        "description": "MaxKZ2 density child alone (20260714_192304)",
        "legs": [("maxkz2", 1.0)],
        "spark_scale": 1.0,
    },
    {
        "book_id": "BOOK-A1-SPARK-RAW",
        "description": "A1 002505 + Spark 002614 raw mixed deposit",
        "legs": [("a1", 1.0), ("spark", 1.0)],
        "spark_scale": 1.0,
    },
    {
        "book_id": "BOOK-A1-SPARK-CAPNORM10",
        "description": "A1 + Spark with Spark PnL x10 capital-normalize proxy",
        "legs": [("a1", 1.0), ("spark", 1.0)],
        "spark_scale": 10.0,
    },
    {
        "book_id": "BOOK-MAXKZ2-SPARK-RAW",
        "description": "MaxKZ2 192304 + Spark 002614 raw mixed deposit",
        "legs": [("maxkz2", 1.0), ("spark", 1.0)],
        "spark_scale": 1.0,
    },
    {
        "book_id": "BOOK-MAXKZ2-SPARK-CAPNORM10",
        "description": "MaxKZ2 + Spark CAPNORM x10 proxy",
        "legs": [("maxkz2", 1.0), ("spark", 1.0)],
        "spark_scale": 10.0,
    },
]


def profit_factor(pnls):
    return v1.profit_factor(pnls)


def apply_haircut(trades, haircut: float):
    out = []
    for t in trades:
        nt = deepcopy(t)
        nt["pnl"] = t["pnl"] - haircut
        out.append(nt)
    return out


def apply_loss_stress(trades, stress: float):
    out = []
    for t in trades:
        nt = deepcopy(t)
        pnl = t["pnl"]
        if stress != 1.0 and pnl < 0:
            pnl = pnl * stress
        nt["pnl"] = pnl
        out.append(nt)
    return out


def metrics(trades, weeks: float) -> dict:
    pnls = [t["pnl"] for t in trades]
    n = len(pnls)
    pf = profit_factor(pnls)
    net = sum(pnls)
    tpw = n / weeks if weeks else None
    dd = v1.max_drawdown_pct(pnls) if n else None
    cadence_ok = tpw is not None and 2.0 <= tpw <= 5.0
    pf_ok = pf is not None and pf > 1.30
    return {
        "n_trades": n,
        "pf": None if pf is None or (isinstance(pf, float) and math.isinf(pf)) else round(pf, 4),
        "net_profit": round(net, 2),
        "tpw_elapsed": None if tpw is None else round(tpw, 4),
        "max_dd_pct_path": None if dd is None else round(dd, 4),
        "cadence_ok_2_5": cadence_ok,
        "pf_ok_gt_1_30": pf_ok,
        "expectancy": None if n == 0 else round(net / n, 4),
    }


def interpolate_break_even(rows_sorted, target_pf: float):
    """rows_sorted: list of (haircut, pf) ascending haircut. Find approx haircut where pf==target."""
    prev_h, prev_pf = None, None
    for h, pf in rows_sorted:
        if pf is None:
            continue
        if pf <= target_pf:
            if prev_h is None or prev_pf is None:
                return {"haircut_usd": h, "method": "first_at_or_below", "pf_at": pf}
            # linear interpolate
            if prev_pf == pf:
                return {"haircut_usd": h, "method": "flat", "pf_at": pf}
            frac = (prev_pf - target_pf) / (prev_pf - pf)
            est = prev_h + frac * (h - prev_h)
            return {
                "haircut_usd": round(est, 3),
                "method": "linear_interp",
                "pf_at": target_pf,
                "bracket": [prev_h, h],
            }
        prev_h, prev_pf = h, pf
    return {"haircut_usd": None, "method": "never_crossed", "last_pf": prev_pf}


def build_book(sleeves: dict, book: dict) -> list[dict]:
    out = []
    for name, w in book["legs"]:
        for t in sleeves[name]["trades"]:
            nt = deepcopy(t)
            scale = book["spark_scale"] if name == "spark" else 1.0
            nt["pnl"] = t["pnl"] * scale * w
            nt["sleeve"] = name
            out.append(nt)
    return sorted(out, key=lambda x: x["entry_time"])


def classify_haircut(m: dict, haircut: float) -> tuple[str, str]:
    pf = m["pf"]
    cadence_ok = m["cadence_ok_2_5"]
    if haircut == 0:
        if cadence_ok and m["pf_ok_gt_1_30"]:
            return "SURVIVE_NEAR_GOAL_RESEARCH_PROXY", "PROMOTE_RANK"
        if cadence_ok:
            return "FAIL_PF_BELOW_1_30", "PARK"
        return "FAIL_CADENCE", "PARK"
    if pf is not None and pf > 1.30 and cadence_ok:
        return "PASS_HAIRCUT_STILL_GT_1_30", "PROMOTE_RANK"
    if pf is not None and pf >= 1.25 and haircut <= 3:
        return "PASS_SOFT_HAIRCUT_PF_GE_1_25", "PROMOTE_RANK"
    if pf is not None and pf >= 1.00:
        return "PASS_PF_GE_1_00_ONLY", "PARK"
    if pf is not None and pf < 1.00:
        return "FAIL_HAIRCUT_PF_BELOW_1_00", "KILL"
    return "UNKNOWN", "PARK"


def classify_loss_stress(m: dict, stress: float) -> tuple[str, str]:
    pf = m["pf"]
    if stress >= 2.0 - 1e-9:
        ok = pf is not None and pf >= 1.00
        gate = "GOAL_X2_PF_GE_1_00"
    elif stress >= 1.5 - 1e-9:
        ok = pf is not None and pf >= 1.25
        gate = "GOAL_X1P5_PF_GE_1_25"
    elif stress >= 1.25 - 1e-9:
        ok = pf is not None and pf >= 1.25
        gate = "SOFT_X1P25_PF_GE_1_25"
    else:
        ok = m["pf_ok_gt_1_30"] and m["cadence_ok_2_5"]
        gate = "BASE_NEAR_GOAL"
    if stress == 1.0:
        if ok:
            return "SURVIVE_NEAR_GOAL_RESEARCH_PROXY", "PROMOTE_RANK"
        return "FAIL_BASE", "PARK"
    if ok:
        return f"PASS_{gate}", "PROMOTE_RANK" if stress < 2.0 else "PASS_STRESS"
    if pf is not None and pf >= 1.00 and stress < 2.0:
        return f"FAIL_{gate}_BUT_PF_GE_1", "PARK"
    if pf is not None and pf < 1.00:
        return f"KILL_{gate}", "KILL"
    return f"FAIL_{gate}", "PARK"


def main() -> int:
    sleeves = {
        "maxkz2": v1.load_sleeve("maxkz2", MAXKZ2_DIR),
        "a1": v1.load_sleeve("a1", A1_DIR),
        "spark": v1.load_sleeve("spark", SPARK_DIR),
    }
    weeks = v1.elapsed_weeks(v1.WINDOW_START, v1.WINDOW_END)

    haircut_rows = []
    loss_rows = []
    breakpoints = {}

    for book in BOOKS:
        base = build_book(sleeves, book)
        # dollar haircut ladder
        ladder = []
        for h in HAIRCUTS_USD:
            adj = apply_haircut(base, h)
            m = metrics(adj, weeks)
            verdict, disp = classify_haircut(m, h)
            row = {
                "book_id": book["book_id"],
                "stress_family": "USD_HAIRCUT_PER_TRADE",
                "haircut_usd_per_trade": h,
                "loss_stress_mult": 1.0,
                "description": book["description"],
                **m,
                "verdict": verdict,
                "disposition": disp,
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                "confirmed": False,
            }
            haircut_rows.append(row)
            ladder.append((h, m["pf"]))

        breakpoints[book["book_id"]] = {
            "pf_cross_1_30": interpolate_break_even(ladder, 1.30),
            "pf_cross_1_25": interpolate_break_even(ladder, 1.25),
            "pf_cross_1_00": interpolate_break_even(ladder, 1.00),
            "base_h0": next(
                r for r in haircut_rows if r["book_id"] == book["book_id"] and r["haircut_usd_per_trade"] == 0
            ),
        }

        # loss-side multiplier stress (GOAL-style)
        for s in LOSS_STRESS:
            adj = apply_loss_stress(base, s)
            m = metrics(adj, weeks)
            verdict, disp = classify_loss_stress(m, s)
            # normalize disposition label
            if disp == "PASS_STRESS":
                disp = "PROMOTE_RANK"
            loss_rows.append(
                {
                    "book_id": book["book_id"],
                    "stress_family": "LOSS_SIDE_MULTIPLIER",
                    "haircut_usd_per_trade": 0.0,
                    "loss_stress_mult": s,
                    "description": book["description"],
                    **m,
                    "verdict": verdict,
                    "disposition": disp,
                    "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                    "confirmed": False,
                }
            )

    # Structural dead-end heuristic (research-proxy only)
    # Edge dies if break-even to PF=1.30 is <= ~$2 AND x1.5 loss stress fails GOAL gate.
    dead_end_notes = {}
    for book in BOOKS:
        bid = book["book_id"]
        be130 = breakpoints[bid]["pf_cross_1_30"].get("haircut_usd")
        x15 = next(
            r
            for r in loss_rows
            if r["book_id"] == bid and abs(r["loss_stress_mult"] - 1.5) < 1e-9
        )
        x2 = next(
            r
            for r in loss_rows
            if r["book_id"] == bid and abs(r["loss_stress_mult"] - 2.0) < 1e-9
        )
        fragile = be130 is not None and be130 <= 2.5
        x15_fail = x15["disposition"] != "PROMOTE_RANK"
        x2_fail = x2["pf"] is not None and x2["pf"] < 1.00
        if fragile and x15_fail:
            note = "STRUCTURAL_FRICTION_DEAD_END_CANDIDATE"
        elif fragile:
            note = "FRAGILE_TO_USD_HAIRCUT_BUT_LOSS_STRESS_MIXED"
        elif x15_fail:
            note = "FAILS_GOAL_X1P5_LOSS_STRESS"
        else:
            note = "SURVIVES_PROXY_STRESS_STILL_UNCONFIRMED"
        dead_end_notes[bid] = {
            "note": note,
            "be_pf_1_30_usd": be130,
            "x1_5_pf": x15["pf"],
            "x1_5_verdict": x15["verdict"],
            "x2_pf": x2["pf"],
            "x2_verdict": x2["verdict"],
            "x2_kill": x2_fail,
        }

    # Rank books at H0
    h0 = [r for r in haircut_rows if r["haircut_usd_per_trade"] == 0]
    best = sorted(
        [r for r in h0 if r["disposition"] == "PROMOTE_RANK"],
        key=lambda x: (-(x["pf"] or 0), -(x["tpw_elapsed"] or 0)),
    )
    best_book = best[0] if best else None

    result = {
        "probe_id": "OFFLINE_SB_MAXKZ2_COST_STRESS_V3",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "owner_mandate": "ITERATE_CONTINUATION_COST_STRESS_SPARK100K_20260714",
        "a_priori_rule": (
            "HAIRCUTS_USD, LOSS_STRESS, BOOKS frozen before ranking; "
            "not mined from hour/day tables; not USBILL rescue"
        ),
        "method_note": (
            "Dollar haircut = flat $/trade friction ladder (research proxy). "
            "Loss-side multiplier = amplify losing trades only (GOAL-style x1.5/x2). "
            "Neither equals broker QFSI. CAPNORM x10 is interim until Spark Deposit=100000 twin. "
            "All UNVERIFIED_TESTER_DEFAULT."
        ),
        "sleeves": {
            k: {
                "run_id": v["run_id"],
                "n": v["n"],
                "pf": None if v["pf"] is None or math.isinf(v["pf"]) else round(v["pf"], 4),
                "net": round(v["net"], 2),
                "report_sha256": v["report_sha256"],
            }
            for k, v in sleeves.items()
        },
        "breakpoints": breakpoints,
        "dead_end_notes": dead_end_notes,
        "haircut_ladder": haircut_rows,
        "loss_stress_ladder": loss_rows,
        "best_h0_book": best_book,
        "killboard_haircut": {
            "PROMOTE_RANK": sum(1 for r in haircut_rows if r["disposition"] == "PROMOTE_RANK"),
            "PARK": sum(1 for r in haircut_rows if r["disposition"] == "PARK"),
            "KILL": sum(1 for r in haircut_rows if r["disposition"] == "KILL"),
        },
        "killboard_loss_stress": {
            "PROMOTE_RANK": sum(1 for r in loss_rows if r["disposition"] == "PROMOTE_RANK"),
            "PARK": sum(1 for r in loss_rows if r["disposition"] == "PARK"),
            "KILL": sum(1 for r in loss_rows if r["disposition"] == "KILL"),
        },
        "path_blockers": {
            "real_qfsi": "BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN",
            "confirmed": False,
            "goal": "UNMET",
        },
    }

    body = dict(result)
    raw = json.dumps(body, indent=2, sort_keys=True, default=str).encode("utf-8")
    result["result_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Offline MaxKZ2 / SB+Spark Cost Stress V3",
        "",
        f"Generated: {result['generated_at_ict']} ICT",
        f"Result SHA256: `{result['result_sha256']}`",
        "",
        "## Method",
        "",
        result["method_note"],
        "",
        "A priori: fine $/trade haircut grid + GOAL-style loss-side x1.25/x1.5/x2 on "
        "MaxKZ2 single and A1/MaxKZ2 × Spark books (RAW + CAPNORM×10).",
        "",
        "## Sleeve baselines",
        "",
        "| sleeve | run_id | N | PF | net |",
        "|---|---|---:|---:|---:|",
    ]
    for k, v in result["sleeves"].items():
        lines.append(f"| {k} | `{v['run_id']}` | {v['n']} | {v['pf']} | {v['net']} |")

    lines += [
        "",
        "## Break-even map (PF crosses)",
        "",
        "| book | base PF | tpw | BE PF=1.30 $ | BE PF=1.25 $ | BE PF=1.00 $ | dead-end note |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for book in BOOKS:
        bid = book["book_id"]
        b0 = breakpoints[bid]["base_h0"]
        be = breakpoints[bid]
        de = dead_end_notes[bid]
        lines.append(
            f"| `{bid}` | {b0['pf']} | {b0['tpw_elapsed']} | "
            f"{be['pf_cross_1_30'].get('haircut_usd')} | "
            f"{be['pf_cross_1_25'].get('haircut_usd')} | "
            f"{be['pf_cross_1_00'].get('haircut_usd')} | "
            f"{de['note']} |"
        )

    lines += [
        "",
        "## Loss-side stress (GOAL-style)",
        "",
        "| book | x1.0 PF | x1.25 PF | x1.5 PF / verdict | x2.0 PF / verdict |",
        "|---|---:|---:|---|---|",
    ]
    for book in BOOKS:
        bid = book["book_id"]
        by_s = {
            r["loss_stress_mult"]: r
            for r in loss_rows
            if r["book_id"] == bid
        }
        lines.append(
            f"| `{bid}` | {by_s[1.0]['pf']} | {by_s[1.25]['pf']} | "
            f"{by_s[1.5]['pf']} / {by_s[1.5]['verdict']} | "
            f"{by_s[2.0]['pf']} / {by_s[2.0]['verdict']} |"
        )

    lines += [
        "",
        "## Dollar haircut ladder (selected books)",
        "",
        "| book | $/trade | N | PF | tpw | net | verdict | disp |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in haircut_rows:
        if r["book_id"] not in (
            "SINGLE-MAXKZ2",
            "BOOK-A1-SPARK-CAPNORM10",
            "BOOK-MAXKZ2-SPARK-CAPNORM10",
            "BOOK-A1-SPARK-RAW",
            "BOOK-MAXKZ2-SPARK-RAW",
        ):
            continue
        lines.append(
            f"| `{r['book_id']}` | {r['haircut_usd_per_trade']} | {r['n_trades']} | "
            f"{r['pf']} | {r['tpw_elapsed']} | {r['net_profit']} | "
            f"{r['verdict']} | {r['disposition']} |"
        )

    best_id = best_book["book_id"] if best_book else None
    lines += [
        "",
        f"Best H0 research-proxy book: `{best_id}`",
        "",
        "## Integrity",
        "",
        "- Not confirmed. Real QFSI still required for GOAL after-cost claims.",
        "- CAPNORM×10 is interim until Spark Deposit=100000 twin lands.",
        "- Do not mine hour/day from this ladder. Structural child only if dead-end note fires.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "result_sha256": result["result_sha256"],
                "best_h0": best_book,
                "dead_end_notes": dead_end_notes,
                "breakpoints_summary": {
                    k: {
                        "be_1_30": v["pf_cross_1_30"].get("haircut_usd"),
                        "be_1_00": v["pf_cross_1_00"].get("haircut_usd"),
                    }
                    for k, v in breakpoints.items()
                },
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
