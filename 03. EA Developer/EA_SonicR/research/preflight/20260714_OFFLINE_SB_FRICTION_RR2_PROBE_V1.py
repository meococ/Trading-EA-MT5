#!/usr/bin/env python3
"""Offline optimistic RR-scale friction probe + honest Spark-100k book join.

A priori child thesis (frozen before ranking):
  HYP-SB-MAXKZ2-RR2-FRICTION-001
  Stretch InpTP_RR_LDN/NY from 1.50 -> 2.00 on MaxKZ2 geometry to thicken
  per-trade expectancy vs dollar friction. NOT densify. NOT USBILL. NOT hour mine.

Offline probe is OPTIMISTIC: scale winning trade PnL by (2.0/1.5), leave losers
unchanged. This overstates survivors that would time-out before 2R. If probe
fails even under optimism -> KILL without Model 0. If survives -> authorize
Model 0 only (optimistic pass is necessary not sufficient).

Also rebuild A1/MaxKZ2 + Spark compose using Deposit=100000 twin
20260714_193358 (no CAPNORM).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from copy import deepcopy
from datetime import datetime
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
RESEARCH = ROOT / "03. EA Developer" / "EA_SonicR" / "research"
PREFLIGHT = RESEARCH / "preflight"
READOUTS = RESEARCH / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

OUT_JSON = PREFLIGHT / "20260714_OFFLINE_SB_FRICTION_RR2_PROBE_V1.json"
OUT_MD = READOUTS / "20260714_OFFLINE_SB_FRICTION_RR2_PROBE_V1.md"
BOOK_JSON = PREFLIGHT / "20260714_OFFLINE_SB_SPARK100K_BOOK_JOIN_V1.json"
BOOK_MD = READOUTS / "20260714_OFFLINE_SB_SPARK100K_BOOK_JOIN_V1.md"

_SPEC = importlib.util.spec_from_file_location(
    "opt_v1",
    str(PREFLIGHT / "20260714_OFFLINE_SB_SPARK_OPTION_MATRIX_V1.py"),
)
v1 = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(v1)

MAXKZ2 = RUNS / "EA_SilverBullet" / "20260714_192304"
A1 = RUNS / "EA_SilverBullet" / "20260714_002505"
SPARK10K = RUNS / "EA_M15SparkAsian" / "20260714_002614"
SPARK100K = RUNS / "EA_M15SparkAsian" / "20260714_193358"

RR_FROM = 1.50
RR_TO = 2.00
RR_SCALE = RR_TO / RR_FROM  # 4/3
HAIRCUTS = [0.0, 1.0, 2.0, 3.0, 5.0]
LOSS_STRESS = [1.0, 1.5, 2.0]


def pf(pnls):
    return v1.profit_factor(pnls)


def metrics(trades, weeks):
    pnls = [t["pnl"] for t in trades]
    n = len(pnls)
    p = pf(pnls)
    net = sum(pnls)
    tpw = n / weeks if weeks else None
    return {
        "n": n,
        "pf": None if p is None or math.isinf(p) else round(p, 4),
        "net": round(net, 2),
        "tpw": None if tpw is None else round(tpw, 4),
        "expectancy": None if n == 0 else round(net / n, 4),
        "cadence_ok": tpw is not None and 2.0 <= tpw <= 5.0,
        "pf_ok": p is not None and p > 1.30,
    }


def scale_winners(trades, scale: float):
    out = []
    for t in trades:
        nt = deepcopy(t)
        if t["pnl"] > 0:
            nt["pnl"] = t["pnl"] * scale
        out.append(nt)
    return out


def haircut(trades, h: float):
    out = []
    for t in trades:
        nt = deepcopy(t)
        nt["pnl"] = t["pnl"] - h
        out.append(nt)
    return out


def loss_stress(trades, s: float):
    out = []
    for t in trades:
        nt = deepcopy(t)
        if s != 1.0 and t["pnl"] < 0:
            nt["pnl"] = t["pnl"] * s
        out.append(nt)
    return out


def join(a, b):
    return sorted(deepcopy(a) + deepcopy(b), key=lambda t: t["entry_time"])


def main() -> int:
    weeks = v1.elapsed_weeks(v1.WINDOW_START, v1.WINDOW_END)
    maxkz2 = v1.load_sleeve("maxkz2", MAXKZ2)
    a1 = v1.load_sleeve("a1", A1)
    spark10k = v1.load_sleeve("spark10k", SPARK10K)
    spark100k = v1.load_sleeve("spark100k", SPARK100K)

    # --- RR2 optimistic probe on MaxKZ2 ---
    base = maxkz2["trades"]
    scaled = scale_winners(base, RR_SCALE)
    probe_rows = []
    for h in HAIRCUTS:
        m = metrics(haircut(scaled, h), weeks)
        verdict = (
            "SURVIVE_OPTIMISTIC"
            if m["pf_ok"] and m["cadence_ok"]
            else ("FAIL_PF" if m["cadence_ok"] else "FAIL_CADENCE")
        )
        if h > 0 and m["pf"] is not None and m["pf"] < 1.00:
            verdict = "KILL_PF_LT_1"
        probe_rows.append({"family": "RR2_OPTIMISTIC_HAIRCUT", "h": h, **m, "verdict": verdict})
    for s in LOSS_STRESS:
        m = metrics(loss_stress(scaled, s), weeks)
        if s >= 2.0:
            ok = m["pf"] is not None and m["pf"] >= 1.00
            gate = "X2"
        elif s >= 1.5:
            ok = m["pf"] is not None and m["pf"] >= 1.25
            gate = "X1P5"
        else:
            ok = m["pf_ok"] and m["cadence_ok"]
            gate = "BASE"
        verdict = f"PASS_{gate}" if ok else f"FAIL_{gate}"
        if m["pf"] is not None and m["pf"] < 1.00 and s >= 1.5:
            verdict = f"KILL_{gate}"
        probe_rows.append({"family": "RR2_OPTIMISTIC_LOSS_STRESS", "stress": s, **m, "verdict": verdict})

    base_m = metrics(base, weeks)
    scaled_m = metrics(scaled, weeks)
    # Compare base haircut fragility
    base_h2 = metrics(haircut(base, 2.0), weeks)
    scaled_h2 = metrics(haircut(scaled, 2.0), weeks)
    base_x15 = metrics(loss_stress(base, 1.5), weeks)
    scaled_x15 = metrics(loss_stress(scaled, 1.5), weeks)

    optimistic_survive = scaled_m["pf_ok"] and scaled_m["cadence_ok"]
    friction_improved = (
        (scaled_h2["pf"] or 0) > (base_h2["pf"] or 0)
        and (scaled_x15["pf"] or 0) > (base_x15["pf"] or 0)
    )
    x15_pass = scaled_x15["pf"] is not None and scaled_x15["pf"] >= 1.25

    if not optimistic_survive:
        child_verdict = "KILL_AT_OFFLINE_PROBE_OPTIMISTIC_FAIL"
    elif x15_pass and friction_improved:
        child_verdict = "PROBE_SURVIVOR_AUTHORIZE_MODEL0_OPTIMISTIC"
    elif friction_improved and scaled_m["pf_ok"]:
        child_verdict = "PROBE_WEAK_SURVIVOR_MODEL0_OPTIONAL_FRICTION_STILL_FAILS_X15"
    else:
        child_verdict = "PARK_OPTIMISTIC_NO_MATERIAL_FRICTION_GAIN"

    probe = {
        "probe_id": "OFFLINE_SB_FRICTION_RR2_PROBE_V1",
        "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": (
            f"Optimistic winner PnL scale {RR_FROM}->{RR_TO} (x{RR_SCALE:.4f}); "
            "losers unchanged; not execution-true; timeout/maxhold ignored"
        ),
        "de_dup": [
            "Not MaxKZ densify (>2 banned)",
            "Not NYPM/MaxHold/London-only/ITSM",
            "Not USBILL rescue",
            "Not EURUSD transfer (separate ID)",
            "Not hour/day mine from readout",
        ],
        "base_maxkz2": base_m,
        "rr2_optimistic": scaled_m,
        "compare_h2": {"base": base_h2, "rr2": scaled_h2},
        "compare_x15": {"base": base_x15, "rr2": scaled_x15},
        "rows": probe_rows,
        "child_verdict": child_verdict,
        "authorize_model0": child_verdict.startswith("PROBE_SURVIVOR")
        or child_verdict.startswith("PROBE_WEAK"),
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "confirmed": False,
    }
    raw = json.dumps(probe, indent=2, sort_keys=True, default=str).encode("utf-8")
    probe["result_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    OUT_JSON.write_text(json.dumps(probe, indent=2, default=str), encoding="utf-8")

    # --- Honest Spark 100k book join ---
    books = []
    for bid, sb_name, sb in [
        ("BOOK-A1-SPARK100K", "a1", a1),
        ("BOOK-MAXKZ2-SPARK100K", "maxkz2", maxkz2),
    ]:
        book_trades = join(sb["trades"], spark100k["trades"])
        m0 = metrics(book_trades, weeks)
        row = {
            "book_id": bid,
            "sb_run": sb["run_id"],
            "spark_run": spark100k["run_id"],
            "spark_deposit": 100000,
            "capnorm_applied": False,
            **m0,
        }
        for h in HAIRCUTS:
            mh = metrics(haircut(book_trades, h), weeks)
            row[f"pf_h{h:g}"] = mh["pf"]
        for s in LOSS_STRESS:
            ms = metrics(loss_stress(book_trades, s), weeks)
            row[f"pf_x{s:g}"] = ms["pf"]
        # contrast vs old CAPNORM on 10k
        old = join(sb["trades"], [
            {**deepcopy(t), "pnl": t["pnl"] * 10.0} for t in spark10k["trades"]
        ])
        mold = metrics(old, weeks)
        row["capnorm10_proxy_pf"] = mold["pf"]
        row["capnorm10_proxy_net"] = mold["net"]
        books.append(row)

    spark_cmp = {
        "spark_10k_run": spark10k["run_id"],
        "spark_10k": {
            "n": spark10k["n"],
            "pf": round(spark10k["pf"], 4),
            "net": round(spark10k["net"], 2),
        },
        "spark_100k_run": spark100k["run_id"],
        "spark_100k": {
            "n": spark100k["n"],
            "pf": round(spark100k["pf"], 4),
            "net": round(spark100k["net"], 2),
            "report_sha256": spark100k["report_sha256"],
        },
        "note": (
            "Deposit=100000 twin landed run 20260714_193358; N identical 325; "
            "PF rose 1.31->~1.38; net ~8.5x not 10x so CAPNORM×10 was imperfect."
        ),
    }

    book = {
        "probe_id": "OFFLINE_SB_SPARK100K_BOOK_JOIN_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "spark_compare": spark_cmp,
        "books": books,
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "confirmed": False,
        "goal": "UNMET",
        "closeout_note": (
            "Alpha closeout threw includes_sha256 mismatch after report ready; "
            "artifacts kept; analyze completed."
        ),
    }
    rawb = json.dumps(book, indent=2, sort_keys=True, default=str).encode("utf-8")
    book["result_sha256"] = hashlib.sha256(rawb).hexdigest().upper()
    BOOK_JSON.write_text(json.dumps(book, indent=2, default=str), encoding="utf-8")

    # MD probe
    lines = [
        "# Offline SB MaxKZ2 RR2 Friction Probe V1",
        "",
        f"Generated: {probe['generated_at_ict']} ICT",
        f"Result SHA256: `{probe['result_sha256']}`",
        f"Hypothesis: `{probe['hypothesis_id']}`",
        "",
        "## Thesis",
        "",
        "Cost-stress V3 showed STRUCTURAL_FRICTION_DEAD_END on MaxKZ2/books "
        "(BE PF>1.30 ≈ $0.8–$1.3/trade; loss-side x1.5/x2 KILL). "
        "Child stretches TP RR 1.5→2.0 a priori to thicken winners vs friction — "
        "not densify, not USBILL, not hour mine.",
        "",
        "## Method caveat",
        "",
        probe["method"],
        "",
        "## Results",
        "",
        f"| metric | base MaxKZ2 | RR2 optimistic |",
        f"|---|---:|---:|",
        f"| PF | {base_m['pf']} | {scaled_m['pf']} |",
        f"| tpw | {base_m['tpw']} | {scaled_m['tpw']} |",
        f"| net | {base_m['net']} | {scaled_m['net']} |",
        f"| exp $/t | {base_m['expectancy']} | {scaled_m['expectancy']} |",
        f"| PF @ $2/t | {base_h2['pf']} | {scaled_h2['pf']} |",
        f"| PF @ loss×1.5 | {base_x15['pf']} | {scaled_x15['pf']} |",
        "",
        f"**Verdict:** `{child_verdict}`",
        "",
        f"Authorize Model 0: `{probe['authorize_model0']}`",
        "",
        "Not confirmed. Optimistic only.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    blines = [
        "# Offline SB + Spark Deposit=100000 Book Join V1",
        "",
        f"Generated: {book['generated_at_ict']} ICT",
        f"Result SHA256: `{book['result_sha256']}`",
        "",
        "## Spark capital twin",
        "",
        f"- 10k run `{spark10k['run_id']}`: N={spark10k['n']} PF={round(spark10k['pf'],4)} net={round(spark10k['net'],2)}",
        f"- 100k run `{spark100k['run_id']}`: N={spark100k['n']} PF={round(spark100k['pf'],4)} net={round(spark100k['net'],2)}",
        f"- Report SHA256: `{spark100k['report_sha256']}`",
        "",
        spark_cmp["note"],
        "",
        book["closeout_note"],
        "",
        "## Honest books (no CAPNORM)",
        "",
        "| book | N | PF | tpw | net | PF@$2 | PF x1.5 | PF x2 | old CAPNORM PF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in books:
        blines.append(
            f"| `{r['book_id']}` | {r['n']} | {r['pf']} | {r['tpw']} | {r['net']} | "
            f"{r.get('pf_h2')} | {r.get('pf_x1.5')} | {r.get('pf_x2')} | {r['capnorm10_proxy_pf']} |"
        )
    blines += [
        "",
        "Still UNVERIFIED_TESTER_DEFAULT. GOAL unmet. Do not mine hour-11 weakness.",
        "",
    ]
    BOOK_MD.write_text("\n".join(blines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "rr2_verdict": child_verdict,
                "rr2_sha": probe["result_sha256"],
                "authorize_model0": probe["authorize_model0"],
                "base": base_m,
                "rr2": scaled_m,
                "h2": {"base": base_h2["pf"], "rr2": scaled_h2["pf"]},
                "x15": {"base": base_x15["pf"], "rr2": scaled_x15["pf"]},
                "book_sha": book["result_sha256"],
                "books": books,
                "spark100k_pf": round(spark100k["pf"], 4),
                "spark100k_net": round(spark100k["net"], 2),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
