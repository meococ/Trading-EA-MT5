#!/usr/bin/env python3
"""Patch deliverable + offline RR2+Spark compose under Real P50 haircut."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
ALPHA = ROOT / "02. AlphaFactory"

sys.path.insert(0, str(ALPHA / "analysis"))
from quant_analyzer import deals_to_trades, parse_deals  # noqa: E402


def patch_deliverable() -> None:
    rec = json.loads((PRE / "20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json").read_text(encoding="utf-8"))
    sha = rec.get("receipt_sha256")
    inv = json.loads((PRE / "v4_data/20260714_EXECUTION_DATA_INVENTORY_V3.json").read_text(encoding="utf-8"))
    md_path = READ / "20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_DELIVERABLE.md"
    md = md_path.read_text(encoding="utf-8")
    md = re.sub(r"SHA256: `[^`]+`", f"SHA256: `{sha}`", md)
    block = (
        "## 5b) Inventory / validation\n\n"
        f"- Inventory V3: `qfsi.verdict={inv['qfsi']['verdict']}`; "
        f"eligible_bundle_count={inv['eligible_bundle_count']}; "
        f"capture_manifest_count={inv['capture_manifest_count']}\n"
        "- Capture validation: STOP_DATA_FRONTIER (sample gates unmet) — "
        "honest; reprice used partial Real sample only.\n\n"
    )
    if "## 5b) Inventory" not in md:
        md = md.replace("## 6) hot.md?", block + "## 6) hot.md?")
    md_path.write_text(md, encoding="utf-8")
    print("deliverable_sha", sha)
    print("inventory", inv["qfsi"]["verdict"], inv["eligible_bundle_count"])


def pf(ps: list[float]) -> float:
    gains = sum(p for p in ps if p > 0)
    losses = -sum(p for p in ps if p < 0)
    if losses > 0:
        return gains / losses
    return float("inf") if gains > 0 else 0.0


def profits(path: Path, haircut: float) -> tuple[list[float], int]:
    trades = deals_to_trades(parse_deals(path))
    return [t.profit - haircut for t in trades], len(trades)


def compose() -> None:
    rr2 = ALPHA / "runs/EA_SilverBullet/20260714_194221/report.html"
    spark = ALPHA / "runs/EA_M15SparkAsian/20260714_193358/report.html"
    if not spark.exists():
        spark = ALPHA / "runs/EA_M15SparkAsian/20260714_002614/report.html"
    base = 2.3087582361186474
    weeks = 261.0  # ~5 calendar years
    p_rr2, n1 = profits(rr2, base)
    p_sp, n2 = profits(spark, base)
    pool = p_rr2 + p_sp
    out = {
        "schema_version": "sonic_offline_compose_real_cost.v1",
        "note": (
            "Diagnostic equal-join pool with additive Real P50 haircut per trade; "
            "NOT Phase0 universe freeze; overlap not re-checked here."
        ),
        "base_cost_per_trade": base,
        "rr2_run": "20260714_194221",
        "spark_run": spark.parent.name,
        "rr2": {"n": n1, "pf_x1": pf(p_rr2), "net": sum(p_rr2), "tpw": n1 / weeks},
        "spark": {"n": n2, "pf_x1": pf(p_sp), "net": sum(p_sp), "tpw": n2 / weeks},
        "pooled": {
            "n": n1 + n2,
            "pf_x1": pf(pool),
            "net": sum(pool),
            "tpw": (n1 + n2) / weeks,
        },
        "goal_x1_pf_gt_1_30": pf(pool) > 1.30,
        "goal_cadence_2_5": 2.0 <= (n1 + n2) / weeks <= 5.0,
    }
    for mult, key in [(1.5, "x1_5"), (2.0, "x2")]:
        pr, _ = profits(rr2, base * mult)
        ps, _ = profits(spark, base * mult)
        out["pooled"][f"pf_{key}"] = pf(pr + ps)
    out["goal_cost_stress_like"] = (
        out["pooled"]["pf_x1"] > 1.30
        and out["pooled"][f"pf_x1_5"] >= 1.25
        and out["pooled"]["pf_x2"] >= 1.00
    )
    path = PRE / "20260714_OFFLINE_RR2_SPARK_REAL_P50_COMPOSE.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    patch_deliverable()
    compose()
