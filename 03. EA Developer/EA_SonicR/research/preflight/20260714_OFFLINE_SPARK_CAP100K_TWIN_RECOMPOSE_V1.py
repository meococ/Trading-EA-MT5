#!/usr/bin/env python3
"""Recompose SB/MaxKZ2 books with Spark Deposit=100000 twin 20260714_193358."""
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


def pool(a, b):
    trades = deepcopy(a["trades"]) + deepcopy(b["trades"])
    pnls = [t["pnl"] for t in trades]
    weeks = v1.elapsed_weeks(v1.WINDOW_START, v1.WINDOW_END)
    pf = v1.profit_factor(pnls)
    n = len(pnls)
    return {
        "n": n,
        "pf": round(pf, 4) if pf is not None else None,
        "tpw": round(n / weeks, 4),
        "net": round(sum(pnls), 2),
        "dd": round(v1.max_drawdown_pct(pnls), 4),
    }


def main() -> int:
    sb = v1.load_sleeve("sb", RUNS / "EA_SilverBullet" / "20260714_002505")
    sb_kz = v1.load_sleeve("sb_kz", RUNS / "EA_SilverBullet" / "20260714_192304")
    sp10 = v1.load_sleeve("sp10", RUNS / "EA_M15SparkAsian" / "20260714_002614")
    sp100 = v1.load_sleeve("sp100", RUNS / "EA_M15SparkAsian" / "20260714_193358")
    weeks = v1.elapsed_weeks(v1.WINDOW_START, v1.WINDOW_END)

    rows = {
        "spark_10k_alone": {
            "n": sp10["n"],
            "pf": round(sp10["pf"], 4),
            "net": round(sp10["net"], 2),
            "tpw": round(sp10["n"] / weeks, 4),
        },
        "spark_100k_alone": {
            "n": sp100["n"],
            "pf": round(sp100["pf"], 4),
            "net": round(sp100["net"], 2),
            "tpw": round(sp100["n"] / weeks, 4),
        },
        "A1_plus_spark10k": pool(sb, sp10),
        "A1_plus_spark100k": pool(sb, sp100),
        "MaxKZ2_plus_spark100k": pool(sb_kz, sp100),
    }
    out = {
        "probe_id": "OFFLINE_SPARK_CAP100K_TWIN_RECOMPOSE_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "spark_twin_run": "20260714_193358",
        "spark_twin_hyp": "HYP-SB-SPARK-BOOK-001",
        "deposit": 100000,
        "alpha_closeout": "includes_sha256_mismatch_after_report_ready",
        "report_sha256": "8E655DB0E5537F99CEB9ED7560D472FC8F45E6D862F5495A0B965D82BBDE9357",
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "confirmed": False,
        "rows": rows,
        "note": (
            "Authoritative Spark capital twin kept despite Alpha includes_sha256 flake. "
            "Replaces CAPNORM x10 proxy for book joins."
        ),
    }
    raw = json.dumps({k: v for k, v in out.items()}, indent=2, sort_keys=True).encode()
    out["result_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    (PRE / "20260714_OFFLINE_SPARK_CAP100K_TWIN_RECOMPOSE_V1.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    lines = [
        "# Spark Deposit=100000 Capital Twin + Book Recompose V1",
        "",
        f"SHA256: `{out['result_sha256']}`",
        "",
        f"Run: `{out['spark_twin_run']}` | Deposit 100000 | closeout flake: includes_sha256",
        "",
        "| book | N | PF | tpw | net |",
        "|---|---:|---:|---:|---:|",
    ]
    for k, v in rows.items():
        lines.append(f"| `{k}` | {v['n']} | {v['pf']} | {v.get('tpw')} | {v['net']} |")
    lines += ["", "Not confirmed / not GOAL. Tester current only.", ""]
    (READ / "20260714_OFFLINE_SPARK_CAP100K_TWIN_RECOMPOSE_V1.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"sha": out["result_sha256"], "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
