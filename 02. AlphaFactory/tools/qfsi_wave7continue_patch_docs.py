#!/usr/bin/env python3
"""Patch deliverable + hot.md SHA after Wave7-continue reprice; launch 006 watcher."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
HOT = ROOT / "04. Project Control/ai/hot.md"
RECEIPT = PRE / "20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_RECEIPT.json"


def main() -> int:
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    body = {k: v for k, v in r.items() if k != "receipt_sha256"}
    body_text = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
    sha_doc = hashlib.sha256(body_text.encode("utf-8")).hexdigest().upper()
    body["receipt_sha256"] = sha_doc
    RECEIPT.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    books = body["books"]
    cost_sha = body["cost_table_sha256"]
    live = body["live_account"]
    compose = body.get("compose_a1_spark") or {}

    def row(label: str, key: str) -> str:
        b = books[key]
        g = "**PASS**" if b.get("goal_cost_stress_pass") else "**FAIL**"
        return (
            f"| {label} | `{b['run_id']}` | {b['base_pf']:.3f} | {b['x1_pf']:.3f} | "
            f"{b['x1_5_pf']:.3f} | {b['x2_pf']:.3f} | {g} |"
        )

    md = f"""# Deliverable — Wave7-continue QFSI / Real shelf reprice

Date: 2026-07-14 ~23:50 ICT  
Authority: Owner CONTINUE after `WAVE7_EXECUTED_EMPTY`  
GPT: waived · Grok · no-Git · cost honesty absolute

## Verdict

**`REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE_COMPLETE`.**  
Full QFSI still **`STOP_DATA_FRONTIER`**. GOAL unmet. Demo PF is not confirmed.

Receipt content SHA `{sha_doc}`

## 1) Live Real / QFSI status (do not kill)

| Item | Value |
|---|---|
| Probe V8 | `TARGET_SERVER_READONLY_PROBE_COMPLETE` · server_match=true |
| Live login | **{live['login']}** @ `{live['server']}` · balance ${live['balance']:.2f} · trade_allowed={live['trade_allowed']} |
| Processes | terminal64 **29076** + QFSI python **35892** (005) — **left running** |
| Capture | `20260714_QFSI_REAL_005_POSTAUTH` LIVE (~1h window; ETA ~00:23 ICT) |
| Quote days | **1** (need 90) |
| Commission unique EURUSD | **2** (need ≥30/symbol) |
| Slippage fills | **0** (MISSING ≠ 0) |

## 2) Cost model (partial — not confirmed)

- Unit USDJPY P50 **$5.2335/lot** = capture-spread P50 + EURUSD commission clue **$4.00/lot RT** (unique N=2)
- Canonical lot-0.5 trade P50 **$2.6168** (matches prior hygiene table)
- Slippage: **MISSING ≠ 0** (not invented)
- Table: `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI_W7CONT.json` SHA `{cost_sha}`

## 3) Shelf reprice (lot-scaled)

| Book | run | base PF | x1 | x1.5 | x2 | GOAL stress |
|---|---|---:|---:|---:|---:|---|
{row('RR2 shelf', 'RR2_SHELF')}
{row('RR2 fresh M0', 'RR2_FRESH_MODEL0')}
{row('SB A1', 'SB_A1')}
{row('Spark 100k', 'SPARK100K')}
{row('MaxKZ2', 'MAXKZ2')}
{row('RR2 194221 ctrl', 'RR2_CONTROL_194221')}

Label: **`PARTIAL_REAL_COST`** — not full QFSI. PASS ≠ confirmed.

## 4) A1 + Spark compose (diagnostic)

pooled x1/x1.5/x2 PF **{compose['x1']['pooled_pf']:.3f} / {compose['x1_5']['pooled_pf']:.3f} / {compose['x2']['pooled_pf']:.3f}** · tpw **{compose['x1']['pooled_tpw']:.2f}** · same-day overlap **{compose['same_day_overlap_n']}** · goal-like **{compose['goal_cost_stress_like']}**

## 5) Friction vs GOAL

- Best shelf RR2 `194548` partial Real: x1/x1.5/x2 **1.316 / 1.286 / 1.257** → stress band PASS (partial only)
- Fresh Model0 `231750`: x1 **1.105** → PARK_MISS under present build
- A1 + MaxKZ2: FAIL x1.5 / x1 band
- Spark100k: stress PASS (partial) — still not confirmed
- Compose A1+Spark: goal-like False (x1 1.290)
- **Friction dead-end on Real: NOT confirmed** (quote-days/commission/slip gates open)
- Confirmed claim: **false**. Demo PF ≠ confirmed.

## 6) Next auto

1. Keep Real; let `005` finish; auto-launch `006` longer accumulate (4h) without killing Real.
2. No price-twin spam / no densify Wave6–7 / no blind COT revive.
3. When QFSI gates lift → re-bind RR2 family under full cost grade.
4. Owner optional: deal-export drop for commission/slip (no invented fills).
"""
    (READ / "20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_DELIVERABLE.md").write_text(md, encoding="utf-8")

    bullet = f"""- **QFSI / Real shelf CONTINUE (2026-07-14 ~23:55 ICT) —
  `REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE_COMPLETE`.**
  Probe V8 complete; login **26451822** `FivePercentOnline-Real`; `terminal64`
  PID **29076** + capture `20260714_QFSI_REAL_005_POSTAUTH` PID **35892**
  **left running** (do not kill). Full QFSI still `STOP_DATA_FRONTIER`
  (quote days=1; EURUSD commission unique=2; slip=0 MISSING≠0).
  Honest unit USDJPY P50 **$5.2335/lot** (spread + $4 commission clue) →
  lot-0.5 trade **~$2.6168**. Shelf partial reprice:
  RR2 `194548` x1/x1.5/x2 **1.316 / 1.286 / 1.257** stress PASS (partial only);
  fresh `231750` x1 **1.105** PARK_MISS; A1 **FAIL**; MaxKZ2 **FAIL**;
  Spark100k stress PASS (partial); A1+Spark compose goal-like **False**.
  Friction dead-end on Real **NOT confirmed**. Receipt content SHA
  `{sha_doc}`; deliverable
  `readouts/20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_DELIVERABLE.md`.
  No densify / no price-twin spam / no COT revive. GOAL unmet.

"""
    hot = HOT.read_text(encoding="utf-8")
    parts = hot.split("## Active Truth\n", 1)
    body_h = parts[1].lstrip("\n")
    body_h = re.sub(
        r"- \*\*QFSI / Real shelf CONTINUE[\s\S]*?(?=\n- \*\*|\n## )",
        "",
        body_h,
        count=1,
    )
    hot = parts[0] + "## Active Truth\n\n" + bullet + body_h.lstrip("\n")
    hot = re.sub(
        r"^Updated:.*$",
        "Updated: 2026-07-14 ~23:55 ICT | `REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE`; "
        "Wave7 empty; GOAL unmet",
        hot,
        count=1,
        flags=re.M,
    )
    HOT.write_text(hot, encoding="utf-8")
    print(json.dumps({"status": "OK", "receipt_sha": sha_doc}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
