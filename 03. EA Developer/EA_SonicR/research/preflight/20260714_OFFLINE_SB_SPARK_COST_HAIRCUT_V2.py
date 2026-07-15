#!/usr/bin/env python3
"""Offline SB+Spark cost-haircut + capital-normalize matrix V2.

A priori options frozen before ranking. Complements V1 loss-side stress
(which is a harsh proxy, not broker cost x1.5).

Also screens capital normalization: Spark twin 002614 used Deposit=10000
while SB A1 002505 used Deposit=100000 — raw dollar compose mixes scales.
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
OUT_JSON = PREFLIGHT / "20260714_OFFLINE_SB_SPARK_COST_HAIRCUT_V2.json"
OUT_MD = READOUTS / "20260714_OFFLINE_SB_SPARK_COST_HAIRCUT_V2.md"

# Load V1 helpers
_SPEC = importlib.util.spec_from_file_location(
    "opt_v1",
    str(PREFLIGHT / "20260714_OFFLINE_SB_SPARK_OPTION_MATRIX_V1.py"),
)
v1 = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(v1)

# A priori haircuts ($ per trade, deducted from each trade PnL)
HAIRCUTS_USD = [0, 1, 2, 3, 5, 8, 10]
# A priori capital normalize factors for Spark relative to SB deposit
# 1.0 = raw (mixed deposits); 10.0 = scale Spark dollars to 100k/10k
SPARK_SCALE_OPTIONS = [
    ("RAW_MIXED_DEPOSIT", 1.0),
    ("CAPNORM_SPARK_X10", 10.0),
]


def profit_factor(pnls):
    return v1.profit_factor(pnls)


def evaluate(trades, haircut, weeks):
    adj = []
    for t in trades:
        nt = deepcopy(t)
        nt["pnl"] = t["pnl"] - haircut
        adj.append(nt)
    pnls = [t["pnl"] for t in adj]
    n = len(pnls)
    pf = profit_factor(pnls)
    net = sum(pnls)
    tpw = n / weeks if weeks else None
    dd = v1.max_drawdown_pct(pnls) if n else None
    cadence_ok = tpw is not None and 2.0 <= tpw <= 5.0
    pf_ok = pf is not None and pf > 1.30
    # GOAL cost-stress style screens on haircut ladder (research proxy)
    if haircut == 0:
        verdict = (
            "SURVIVE_NEAR_GOAL_RESEARCH_PROXY"
            if cadence_ok and pf_ok
            else ("FAIL_PF" if cadence_ok else "FAIL_CADENCE")
        )
    elif pf is not None and pf >= 1.25 and haircut <= 3:
        # soft: small haircut still near GOAL research bar
        verdict = "PASS_SOFT_HAIRCUT_PF_GE_1_25"
    elif pf is not None and pf >= 1.00:
        verdict = "PASS_PF_GE_1_00_ONLY"
    else:
        verdict = "FAIL_HAIRCUT_PF_BELOW_1_00"

    if verdict.startswith("SURVIVE") or verdict.startswith("PASS_SOFT"):
        disp = "PROMOTE_RANK"
    elif verdict == "PASS_PF_GE_1_00_ONLY":
        disp = "PARK"
    else:
        disp = "KILL" if (pf is not None and pf < 1.00) else "PARK"

    return {
        "n_trades": n,
        "pf": None if pf is None or math.isinf(pf) else round(pf, 4),
        "net_profit": round(net, 2),
        "tpw_elapsed": None if tpw is None else round(tpw, 4),
        "max_dd_pct_path": None if dd is None else round(dd, 4),
        "cadence_ok_2_5": cadence_ok,
        "pf_ok_gt_1_30": pf_ok,
        "verdict": verdict,
        "disposition": disp,
    }


def main() -> int:
    sb = v1.load_sleeve("sb", v1.SB_DIR)
    spark = v1.load_sleeve("spark", v1.SPARK_DIR)
    weeks = v1.elapsed_weeks(v1.WINDOW_START, v1.WINDOW_END)

    rows = []
    for scale_tag, spark_scale in SPARK_SCALE_OPTIONS:
        scaled_spark = []
        for t in spark["trades"]:
            nt = deepcopy(t)
            nt["pnl"] = t["pnl"] * spark_scale
            scaled_spark.append(nt)
        book = deepcopy(sb["trades"]) + scaled_spark
        for h in HAIRCUTS_USD:
            opt_id = f"OPT-HAIRCUT-{scale_tag}-H{h}"
            metrics = evaluate(book, h, weeks)
            rows.append(
                {
                    "option_id": opt_id,
                    "category": "COST_HAIRCUT_USD",
                    "scale_tag": scale_tag,
                    "spark_pnl_scale": spark_scale,
                    "haircut_usd_per_trade": h,
                    "description": (
                        f"SB+Spark equal-join; spark_scale={spark_scale}; "
                        f"deduct ${h}/trade"
                    ),
                    **metrics,
                    "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                    "confirmed": False,
                }
            )

    # Find break-even haircut for each scale (PF crosses 1.30 and 1.00)
    breakpoints = {}
    for scale_tag, _ in SPARK_SCALE_OPTIONS:
        subset = [r for r in rows if r["scale_tag"] == scale_tag]
        pf130 = None
        pf100 = None
        for r in subset:
            if pf130 is None and (r["pf"] or 0) <= 1.30:
                pf130 = r["haircut_usd_per_trade"]
            if pf100 is None and (r["pf"] or 0) < 1.00:
                pf100 = r["haircut_usd_per_trade"]
        breakpoints[scale_tag] = {
            "first_haircut_pf_le_1_30": pf130,
            "first_haircut_pf_lt_1_00": pf100,
        }

    # Champion under cap-norm zero haircut
    champs = [
        r
        for r in rows
        if r["haircut_usd_per_trade"] == 0 and r["disposition"] == "PROMOTE_RANK"
    ]
    best = None
    if champs:
        # Prefer CAPNORM for capital honesty, then higher PF
        best = sorted(
            champs,
            key=lambda x: (0 if x["scale_tag"] == "CAPNORM_SPARK_X10" else 1, -(x["pf"] or 0)),
        )[0]

    result = {
        "probe_id": "OFFLINE_SB_SPARK_COST_HAIRCUT_V2",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "owner_mandate": "ITERATE_EXPERIMENT_TEARDOWN_REBUILD_20260714_1909",
        "a_priori_rule": (
            "HAIRCUTS_USD and SPARK_SCALE_OPTIONS frozen before ranking; "
            "not mined from V1 readout hour/day tables"
        ),
        "deposit_caveat": {
            "sb_run": "20260714_002505",
            "sb_deposit_expected": 100000,
            "spark_run": "20260714_002614",
            "spark_deposit_observed": 10000,
            "note": (
                "RAW_MIXED_DEPOSIT understates Spark dollar contribution vs SB. "
                "CAPNORM_SPARK_X10 is a linear risk-% scale proxy only — "
                "authoritative fix is Spark Model 0 re-run at Deposit=100000."
            ),
        },
        "method_note": (
            "Dollar haircut is a research friction ladder. It is NOT identical to "
            "broker QFSI cost x1.5/x2. V1 loss-side multiplier remains a harsh "
            "upper-bound stress and must not be read as GOAL cost-stress alone."
        ),
        "sleeves": {
            "sb": {"n": sb["n"], "pf": sb["pf"], "net": sb["net"], "report_sha256": sb["report_sha256"]},
            "spark": {
                "n": spark["n"],
                "pf": spark["pf"],
                "net": spark["net"],
                "report_sha256": spark["report_sha256"],
            },
        },
        "breakpoints": breakpoints,
        "options": rows,
        "best_current_candidate": best,
        "killboard_counts": {
            "PROMOTE_RANK": sum(1 for r in rows if r["disposition"] == "PROMOTE_RANK"),
            "PARK": sum(1 for r in rows if r["disposition"] == "PARK"),
            "KILL": sum(1 for r in rows if r["disposition"] == "KILL"),
        },
        "path_blockers": {
            "real_qfsi": "BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN",
            "confirmed": False,
        },
    }

    body = dict(result)
    raw = json.dumps(body, indent=2, sort_keys=True, default=str).encode("utf-8")
    result["result_sha256"] = hashlib.sha256(raw).hexdigest().upper()

    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Offline SB+Spark Cost Haircut V2",
        "",
        f"Generated: {result['generated_at_ict']} ICT",
        f"Result SHA256: `{result['result_sha256']}`",
        "",
        "## Deposit caveat",
        "",
        result["deposit_caveat"]["note"],
        "",
        "## Method note",
        "",
        result["method_note"],
        "",
        "## Breakpoints",
        "",
        "```json",
        json.dumps(breakpoints, indent=2),
        "```",
        "",
        "## Ladder",
        "",
        "| option_id | scale | $/trade | N | PF | tpw | net | DD% | verdict | disp |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['option_id']}` | {r['scale_tag']} | {r['haircut_usd_per_trade']} | "
            f"{r['n_trades']} | {r['pf']} | {r['tpw_elapsed']} | {r['net_profit']} | "
            f"{r['max_dd_pct_path']} | {r['verdict']} | {r['disposition']} |"
        )
    lines += [
        "",
        f"Best (research ranking): `{best['option_id'] if best else None}`",
        "",
        "Not confirmed. Real QFSI still required for GOAL.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "result_sha256": result["result_sha256"],
        "breakpoints": breakpoints,
        "best": best,
        "killboard": result["killboard_counts"],
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
