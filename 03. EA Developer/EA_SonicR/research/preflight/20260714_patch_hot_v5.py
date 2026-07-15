#!/usr/bin/env python3
from pathlib import Path

hot = Path(r"d:\Trading EA MT5\04. Project Control\ai\hot.md")
text = hot.read_text(encoding="utf-8")

# Header
text2 = text
if "Structural V5 offline 5/5 KILL" not in text2:
    text2 = text2.replace(
        "Updated: 2026-07-14 ~23:12 ICT | Path-B Model0 KILL `231055`;\n"
        "V4 offline empty; RR2 best; GOAL unmet",
        "Updated: 2026-07-14 ~23:30 ICT | Structural V5 offline 5/5 KILL;\n"
        "Path-B Model0 KILL; V1–V5 empty; RR2 best; GOAL unmet",
        1,
    )

v5_bullet = """- **Structural rebuild V5 CLOSEOUT (2026-07-14 ~23:30 ICT) —
  `OFFLINE_V5_ALL_KILL / NO_MODEL0`.** Five fresh objects (de-dup
  `readouts/20260714_STRUCTURAL_V5_DEDUP_CLEARANCE.md`) — **not** V1–V4 /
  Wave3–5 / Path-B retunes; discovery **without** Phase-0 wait:
  1. Orderblock mitigation N=412 PF **0.985**/tpw **1.58** → **KILL**
  2. D1-inside→H4 break N=369 PF **0.987**/tpw **1.41** → **KILL**
  3. London drive fail-fade N=298 PF **0.915**/tpw **1.14** → **KILL**
  4. Asia break fail-fade N=102 PF **0.923**/tpw **0.39** → **KILL**
  5. H4 break-pause-break N=31 PF **0.635**/tpw **0.12** → **KILL**
  SHA `59C951DFA93BA7AF5BBD50ECA427A107DC4C8982D81025CAA3240AA8BB1B2CA2`
  `preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V5.json`.
  Deliverable `readouts/20260714_STRUCTURAL_V5_SESSION_DELIVERABLE.md`.
  **Zero Model 0.** Do not densify V5 params. Best shelf RR2 `194548`.
"""

if "OFFLINE_V5_ALL_KILL" not in text2:
    marker = "## Active Truth\n\n"
    idx = text2.find(marker)
    if idx < 0:
        raise SystemExit("ACTIVE_TRUTH_MISSING")
    insert_at = idx + len(marker)
    text2 = text2[:insert_at] + v5_bullet + text2[insert_at:]

# Mark V4 as superseded
text2 = text2.replace(
    "Next: new structural object **outside** E/F (+ prior kills) — offline\n"
    "  first. GPT waived. Best shelf RR2 `194548` unchanged.",
    "Superseded as active next by V5. GPT waived. Best shelf RR2 `194548`.",
    1,
)

old_nm = (
    "- **ACTIVE — structural rebuild + offline-first (post V4 empty).** V1–V4\n"
    "  offline probes all **KILL** — **no Model 0**. Do **not** densify PWHL\n"
    "  reclaim / H4 balance / FVG / NYIB-fail / stop-run / LNY / Wave3–5 /\n"
    "  MaxKZ/RR. Next = **new** independent thick object\n"
    "  (probe→registry/prereg→Model0 only if survivor), or Owner clear Phase-0\n"
    "  contamination for RR2+Spark ceremony. Real/QFSI = parallel hygiene only —\n"
    "  never discovery headline. Best shelf: RR2 `194548` PF **1.378** /\n"
    "  ~**2.01**/wk. GPT waived unless Owner reopens.\n"
    "- **CLOSED — Structural V4 offline:** PWHL reclaim + H4 balance-break KILL.\n"
)
new_nm = (
    "- **ACTIVE — structural rebuild + offline-first (post V5 empty).** V1–V5\n"
    "  offline all **KILL** — **no Model 0**. Do **not** densify V5 / V4 PWHL /\n"
    "  H4-balance / FVG / NYIB / stop-run / LNY / Wave3–5 / Path-B D1-H1-PB /\n"
    "  MaxKZ/RR. Next = **new** independent thick object (consider cross-symbol\n"
    "  if USDJPY TF saturated); probe→Model0 only if survivor. Do **not** stall\n"
    "  on Phase-0 Owner clear. Real/QFSI = hygiene only. Best shelf: RR2\n"
    "  `194548` PF **1.378** / ~**2.01**/wk. GPT waived unless Owner reopens.\n"
    "- **CLOSED — Structural V5 offline:** 5/5 KILL.\n"
    "  `readouts/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V5.md`.\n"
    "- **CLOSED — Structural V4 offline:** PWHL reclaim + H4 balance-break KILL.\n"
)

if old_nm not in text2:
    # try softer: only replace ACTIVE line block start
    if "post V5 empty" not in text2:
        raise SystemExit("NEXT_NOT_FOUND")
else:
    text2 = text2.replace(old_nm, new_nm, 1)

hot.write_text(text2, encoding="utf-8")
print("OK")
