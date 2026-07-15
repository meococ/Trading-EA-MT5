#!/usr/bin/env python3
"""Compose a priori SB variants with Spark — research book screens.

Uses parked/authoritative runs only. Cost UNVERIFIED_TESTER_DEFAULT.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

PRE = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\preflight")
READ = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\readouts")
RUNS = Path(r"d:\Trading EA MT5\02. AlphaFactory\runs")

spec = importlib.util.spec_from_file_location(
    "v1", str(PRE / "20260714_OFFLINE_SB_SPARK_OPTION_MATRIX_V1.py")
)
v1 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v1)

SLEEVES = {
    "sb_a1": RUNS / "EA_SilverBullet" / "20260714_002505",
    "sb_maxhold": RUNS / "EA_SilverBullet" / "20260714_191628",
    "sb_maxkz2": RUNS / "EA_SilverBullet" / "20260714_192304",
    "sb_nypm": RUNS / "EA_SilverBullet" / "20260714_192203",
    "spark": RUNS / "EA_M15SparkAsian" / "20260714_002614",
}

BOOKS = [
    ("BOOK-A1-SPARK-RAW", "sb_a1", "spark", 1.0),
    ("BOOK-A1-SPARK-CAPX10", "sb_a1", "spark", 10.0),
    ("BOOK-MAXHOLD-SPARK-RAW", "sb_maxhold", "spark", 1.0),
    ("BOOK-MAXHOLD-SPARK-CAPX10", "sb_maxhold", "spark", 10.0),
    ("BOOK-MAXKZ2-SPARK-RAW", "sb_maxkz2", "spark", 1.0),
    ("BOOK-MAXKZ2-SPARK-CAPX10", "sb_maxkz2", "spark", 10.0),
    ("BOOK-NYPM-SPARK-RAW", "sb_nypm", "spark", 1.0),
    ("SLEEVE-MAXKZ2-ONLY", "sb_maxkz2", None, 1.0),
    ("SLEEVE-A1-ONLY", "sb_a1", None, 1.0),
]


def pool(a, b=None, scale_b=1.0):
    trades = deepcopy(a["trades"])
    if b is not None:
        for t in b["trades"]:
            nt = deepcopy(t)
            nt["pnl"] = t["pnl"] * scale_b
            trades.append(nt)
    pnls = [t["pnl"] for t in trades]
    weeks = v1.elapsed_weeks(v1.WINDOW_START, v1.WINDOW_END)
    pf = v1.profit_factor(pnls)
    n = len(pnls)
    tpw = n / weeks
    net = sum(pnls)
    if pf and pf > 1.30 and 2.0 <= tpw <= 5.0:
        verdict, disp = "SURVIVE_NEAR_GOAL_RESEARCH_PROXY", "PROMOTE_RANK"
    elif pf and pf >= 1.05:
        verdict, disp = "PARK_NEAR_MISS", "PARK"
    else:
        verdict, disp = "KILL", "KILL"
    return {
        "n": n,
        "pf": None if pf is None else round(pf, 4),
        "tpw": round(tpw, 4),
        "net": round(net, 2),
        "dd": round(v1.max_drawdown_pct(pnls), 4),
        "verdict": verdict,
        "disposition": disp,
    }


def main() -> int:
    loaded = {}
    errors = {}
    for k, p in SLEEVES.items():
        try:
            loaded[k] = v1.load_sleeve(k, p)
        except Exception as exc:  # noqa: BLE001
            errors[k] = f"{type(exc).__name__}: {exc}"

    rows = []
    for book_id, a, b, scale in BOOKS:
        if a not in loaded or (b and b not in loaded):
            rows.append({"book_id": book_id, "status": "BLOCKED_MISSING", "need": [a, b]})
            continue
        metrics = pool(loaded[a], loaded.get(b) if b else None, scale)
        rows.append(
            {
                "book_id": book_id,
                "sleeve_a": a,
                "sleeve_b": b,
                "spark_scale": scale,
                **metrics,
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                "confirmed": False,
            }
        )

    survivors = [r for r in rows if r.get("disposition") == "PROMOTE_RANK"]
    best = None
    if survivors:
        # Prefer MaxKZ2 books if they survive (cadence denser), else A1
        best = sorted(
            survivors,
            key=lambda x: (
                0 if "MAXKZ2" in x["book_id"] else 1,
                -(x.get("pf") or 0),
                -(x.get("tpw") or 0),
            ),
        )[0]

    out = {
        "probe_id": "OFFLINE_SB_VARIANT_COMPOSE_BATCH_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "owner_mandate": "ITERATE_EXPERIMENT_TEARDOWN_REBUILD_20260714_1909",
        "load_errors": errors,
        "sleeve_meta": {
            k: {
                "run_id": v["run_id"],
                "n": v["n"],
                "pf": v["pf"],
                "net": v["net"],
                "report_sha256": v["report_sha256"],
            }
            for k, v in loaded.items()
        },
        "books": rows,
        "best_current_candidate": best,
        "killboard_counts": {
            "PROMOTE_RANK": sum(1 for r in rows if r.get("disposition") == "PROMOTE_RANK"),
            "PARK": sum(1 for r in rows if r.get("disposition") == "PARK"),
            "KILL": sum(1 for r in rows if r.get("disposition") == "KILL"),
            "BLOCKED": sum(1 for r in rows if r.get("status") == "BLOCKED_MISSING"),
        },
        "notes": [
            "MaxHold A2 ~null vs A1; NYPM dilutes PF; MaxKZ2 densifies SB cadence.",
            "Spark still Deposit=10000 — CAPX10 is proxy until capital twin.",
            "Not confirmed / not GOAL.",
        ],
    }
    raw = json.dumps({k: v for k, v in out.items()}, indent=2, sort_keys=True, default=str).encode()
    out["result_sha256"] = hashlib.sha256(raw).hexdigest().upper()

    OUT_JSON = PRE / "20260714_OFFLINE_SB_VARIANT_COMPOSE_BATCH_V1.json"
    OUT_MD = READ / "20260714_OFFLINE_SB_VARIANT_COMPOSE_BATCH_V1.md"
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Offline SB Variant Compose Batch V1",
        "",
        f"SHA256: `{out['result_sha256']}`",
        f"Generated: {out['generated_at_ict']} ICT",
        "",
        "| book_id | N | PF | tpw | net | DD% | verdict | disp |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in rows:
        if r.get("status"):
            lines.append(f"| `{r['book_id']}` | — | — | — | — | — | {r['status']} | — |")
            continue
        lines.append(
            f"| `{r['book_id']}` | {r['n']} | {r['pf']} | {r['tpw']} | {r['net']} | "
            f"{r['dd']} | {r['verdict']} | {r['disposition']} |"
        )
    lines += [
        "",
        f"Best: `{best['book_id'] if best else None}`",
        "",
        "Cost grade: UNVERIFIED_TESTER_DEFAULT. Not GOAL.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"sha": out["result_sha256"], "best": best, "kb": out["killboard_counts"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
