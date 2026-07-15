#!/usr/bin/env python3
"""Repair hot.md Active Truth + Next Move after Wave5 (no shell $-expansion)."""
from pathlib import Path

p = Path(r"d:\Trading EA MT5\04. Project Control\ai\hot.md")
text = p.read_text(encoding="utf-8")

keep_markers = [
    "- **PIN + THREEBAR",
    "- **Discovery Wave3",
    "- **Model 0 RR2 re-run attempt #2",
    "- **Owner \"đã login\"",
]
keep_at = None
for m in keep_markers:
    j = text.find(m)
    if j > 0:
        keep_at = j
        break
if keep_at is None:
    # fallback: find first bullet after mangled header that looks historical
    j = text.find("- **Model 0 RR2")
    if j < 0:
        raise SystemExit("cannot find keep anchor")
    keep_at = j

header = """# Hot Cache

Updated: 2026-07-14 ~22:58 ICT | Discovery Wave5 Model0 EMPTY
(ATR%ile PARK / EURUSD Asia-box KILL / NY-IB PARK); SBSparkBook KILL;
Phase-0 RR2+Spark universe frozen (compose not run); RR2 best

## Active Truth

- **Discovery Wave5 Model 0 CLOSEOUT (2026-07-14 ~22:58 ICT) —
  `WAVE5_EXECUTED_EMPTY`.** Owner R&D continue; no Real/QFSI stall.
  Authoritative board:
  1. `HYP-H1-ATR-PCTILE-BREAK-001` auth `20260714_224917` (twin `225208`)
     PF **1.10** / ~**1.71**/wk → **PARK**; +$12 x1 **~0.99 FAIL**.
     Readout `readouts/20260714_HYP_H1_ATR_PCTILE_BREAK_001_READOUT.md`.
  2. `HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001` auth `20260714_225314`
     (alt label `225610` same report SHA `FCF42B42…`) PF **0.90** / 500t /
     ~**1.92**/wk / exp −$13 → **KILL**. Receipt `E234B6FF…`.
  3. `HYP-M15-NY-IB-DRIVE-BREAK-001` `20260714_225340` PF **1.02** / 983t /
     ~**3.77**/wk / exp +$1.74 → **PARK** (+$12 x1 **0.90 FAIL**).
  Wave5 closeout
  `readouts/20260714_DISCOVERY_WAVE5_ATR_ASIA_NYIB_CLOSEOUT.md`; de-dup
  `readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md`. Phase-0 universe
  freeze (no combo metrics):
  `readouts/20260714_PHASE0_RR2_SPARK_UNIVERSE_FREEZE.md` (RR2 `194548` +
  Spark100k `193358`). Best shelf unchanged: RR2 `194548` PF **1.378**/~**2.01**
  (+$12 x1.5 FAIL). `DEMO_DISCOVERY_DIMINISHING_RETURNS=true`. Do **not**
  densify ATR%ile / Asia-London / NY-IB hours / MaxKZ / RR / SB / Spark.
- **`HYP-PORTFOLIO-SB-SPARK-RUNNER-001` — `KILLED_AT_MODEL_0`.** `20260714_224302`
  PF **1.219** / ~**3.23**/wk — research PF FAIL; +$12 FAIL. Family **1/1**.
  Readout `readouts/20260714_HYP_PORTFOLIO_SB_SPARK_RUNNER_001_READOUT.md`.
- **Discovery Wave4 CLOSEOUT — `WAVE4_EXECUTED_EMPTY`.** IB `223618` PARK /
  RV `223714` KILL cadence / GBPJPY `223748` PARK. Closeout
  `readouts/20260714_DISCOVERY_WAVE4_IB_RV_GBPJPY_CLOSEOUT.md`.
- **Best shelf (verified disk):** RR2 `20260714_194548` PF **1.378** / 524t /
  ~**2.01**/wk — research HIT / GOAL +$12 x1.5 FAIL / PARK. Do **not** densify
  RR/MaxKZ. Full QFSI still `STOP_DATA_FRONTIER` (parallel hygiene only).

"""

body = text[keep_at:]
# Drop a corrupted Active Truth prefix if keep_at landed inside mangled section
# by ensuring body starts with a clean historical bullet.
new = header + body

nm = """## Next Move

- **ACTIVE — after Wave5 EMPTY.** Prefer structural rebuilds / failure-packet
  Deep Research / Phase-0 compose ceremony **after** contamination contracts
  clear (universe already frozen: RR2 `194548` + Spark100k `193358`). Do **not**
  densify ATR%ile, Asia/London/NY IB hours, MaxKZ/RR/SB/Spark, or Wave1–5
  killed/parked families. Real/QFSI = parallel hygiene only — never discovery
  stop / never headline. RR2 `194548` still best Demo HIT / FRAGILE under +$12.
  `DEMO_DISCOVERY_DIMINISHING_RETURNS=true` — cheap offline probe before next
  Model 0 batch.
- **CLOSED — Discovery Wave5 Model 0:** `WAVE5_EXECUTED_EMPTY` (ATR PARK /
  EURUSD KILL / NY-IB PARK).
  Closeout `readouts/20260714_DISCOVERY_WAVE5_ATR_ASIA_NYIB_CLOSEOUT.md`.
- **CLOSED — Phase-0 universe freeze (no compose metrics):** RR2+Spark exact
  list frozen a priori —
  `readouts/20260714_PHASE0_RR2_SPARK_UNIVERSE_FREEZE.md`.
- **CLOSED — SBSparkBook Model 0:** `KILLED_AT_MODEL_0` `224302` PF 1.219.
- **CLOSED — Wave4 Model 0:** `WAVE4_EXECUTED_EMPTY`.

"""

nidx = new.find("## Next Move")
end = new.find("1. Do not mine more local XAU")
if nidx < 0 or end < 0:
    raise SystemExit(f"anchors missing nidx={nidx} end={end}")
new2 = new[:nidx] + nm + new[end:]
p.write_text(new2, encoding="utf-8")
# sanity
head = "\n".join(new2.splitlines()[:35])
assert "readouts/" in head
assert "+$12" in head
assert "`WAVE5_EXECUTED_EMPTY`" in head
print("OK repaired hot.md")
print(head)
