# BOX_YARDSTICK_AUDIT — X1 box label audit (BOX-LAB)

Measured: every golden BOX in TUNE v2 against M5 bars inside its
containment window `build_start..build_end` (fallback `t0..t1`), bars via
`golden/book_loader.py` only. Script: `boxlab/audit_boxes.py` →
`cache/box_audit.jsonl` (116 rows). Renders: `audit_png/` (20 boxes,
seed 20260921). Ruler: `evalcheck/eval_v2.py` (`cand_right` prefix rule
from `funnel.py`).

## Population

- 116 BOX objects: 63 ok / 48 repaired / 5 unusable.
- 108 usable + scorable + non-degenerate (the funnel's BOX denominator).
- `build_start` present: 47/116 (fallback `t0` for the rest — mandate D9).
- RANGE_OPEN = 8, CONTEXT_RANGE = 6 usable — same family, audited later
  in X3 scoring; not part of the 108.

## Core distributions (n = 108)

| metric | p10 | med | p90 |
|---|---:|---:|---:|
| height (pips) | 10.0 | 15.8 | 36.5 |
| height (ABR50) | 1.54 | 3.16 | 7.29 |
| drawn span (min) | 43.5 | 135 | 415 |
| build span (min) | 10 | 72.5 | 250 |
| closes outside band | 0 | 0 | 2 |
| closes outside band +1.5p | 0 | 0 | 0 |
| contain frac (closes) | 0.75 | 1.00 | 1.00 |
| pokes (either edge) | 0 | 2 | 5 |
| poke depth (pips) | 0 | 1.2 | 6.4 |
| touch bars/edge @1.5p | 0 | 2 | ~6 |
| touch events/edge @1.5p | 0 | 1–1.5 | 3 |
| touch scatter σ (pips) | 0 | 0.5–0.7 | 1.1 |

vs Q2_MEASUREMENTS (n=111): height 16 (10–37) ✓, drawn span 135 ✓,
buildup ~65 vs my 72.5 ✓, ~2.5 touches/edge = touch **bars** (measure.py
sums `|ext−edge|≤1.5` per bar; event-runs med is 1–1.5), ~1.5 pokes ✓.

## Window semantics confirmed

- `closes_out` med 0, p90 2 (p90 of closes_out_tol = 0): inside
  `build_start..build_end` closes stay inside the band. Wick overshoot
  (pokes) is texture, not containment failure.
- `break_bar − build_end`: med +5 min, p90 +45 — the label's build_end
  sits at/near the first decisive close outside (within ~1 bar median;
  a tail of labels ends the window before the actual break).
- Drawn span ≠ containment window (D9): drawn 135 min med vs build
  72.5 min med; `t0 − build_start` med 0, p10 −15 (the drawn left edge
  is usually the build start, sometimes 15 min earlier).
- `first_touch − build_start` med +5, p90 +45.5: the edges get their
  first in-window touch almost immediately — the label starts the
  window roughly when defence begins, not after.
- `hi − max_high` med −1.5 (p10 −10.5, p90 +1.4): the top edge sits
  ~1.5 p below the window's max high on median — shallow pokes stay
  inside the label. `hi − p95_high` med −0.05: the top edge ≈ p95 of
  window highs (the edge is the extreme *with company*, not the max).
- 60-min pre-window touch bars: med 0, p90 2 — edges mostly form
  inside the window; a minority reuse a pre-existing level.

## (a) Reliability per stratum (trusted = contain_ok ∧ edge-support ∧ geom)

`trusted` = closes_out_tol ≤ max(1, 10% of window bars) ∧ each edge has
defence evidence (≥2 hugging bars, or 1 hug + a poke, or a pre-window
touch) ∧ 4 ≤ height ≤ 80 p ∧ build ≥ 15 min.

| stratum | n | trusted | edges_ok(≥2ev) | edges_sup |
|---|---:|---:|---:|---:|
| all | 108 | 68 (0.63) | 0.30 | 0.72 |
| has build_start | 43 | 19 (0.44) | 0.30 | 0.51 |
| fallback t0 | 65 | 49 (0.75) | 0.31 | 0.80 |
| prec=meas | 30 | 17 (0.57) | 0.33 | 0.57 |
| prec=eye | 78 | 51 (0.65) | 0.29 | 0.73 |
| repair=text_price | 55 | 27 (0.49) | 0.31 | 0.55 |
| repair=edge_from_bars | 44 | 35 (0.80) | 0.23 | 0.82 |
| repair=+subwindow | 3 | 2 (0.67) | 1.00 | 1.00 |
| repair=none | 6 | 4 (0.67) | 0.50 | 0.83 |
| σ=1.5 (refined) | 47 | 37 (0.79) | 0.28 | 0.83 |
| σ=2.0 (meas) | 30 | 17 (0.57) | 0.33 | 0.57 |
| σ=5.0 (eye) | 31 | 14 (0.45) | 0.32 | 0.58 |

Findings:
- Bar-anchored repairs (`edge_from_bars`, σ=1.5) are the most reliable
  stratum (0.79–0.80). Text-price (`eye`, σ=5) is the weakest (0.45).
- Boxes with an explicit `build_start` are *less* reliable in-window
  (0.44): those windows are typically shorter/tighter, leaving fewer
  in-window touch bars — the edges were often already formed when the
  window starts (the author marked `build_start` exactly where defence
  became visible).
- `EDGE_TOUCH_*` validator flags mark boxes where one edge lacks
  in-window hugging bars — usually a break-side edge defended only by
  the approach, or an edge formed just before `build_start`.

## (b) Suspect list (proposals only — yardstick stays frozen)

Hard suspects (geometry or containment visibly off):
`9.24b#1` h=0.4 p (degenerate), `9.48b#0` h=0.3 p (degenerate),
`9.42b#1` h=84 p, `9.60b#4` h=66 p, `9.37b#0` h=50 p, `9.34b#0` h=56 p,
`9.16c#0` h=55 p (likely episode/context ranges annotated as BOX),
`9.66c#4` closes_out_tol=8 (subwindow repair still breaches),
degenerate windows bs==be: `9.6a#3`, `9.7a#2`, `9.18b#0`, `9.36b#2`,
`9.38a#0`, `9.50b#0`, `9.56a#0`.

Soft suspects (one edge lacks defence evidence inside the window):
`9.1c#0`, `9.2a#0`, `9.2b#3`, `9.3b#0`, `9.6a#0`, `9.7b#0`,
`9.10c#1`, `9.14b#3`, `9.15c#0`, `9.16b#0`, `9.16c#2`, `9.19a#1`,
`9.20a#0`, `9.20b#0`, `9.22a#2`, `9.22b#0`, `9.23c#1`, `9.30a#0`,
`9.30c#1`, `9.31c#2`, `9.34a#0`, `9.35a#1`, `9.44b#2`, `9.47b#0`,
`9.50c#0`, `9.51a#0`, `9.51b#0`, `9.52b#0`, `9.53b#0`, `9.56a#2`,
`9.57c#4`, `9.58a#2`, `9.60b#2`, `9.61b#2`, `9.62a#3`, `9.63a#0`,
`9.10a#2`, `9.13a#0`, `9.13b#0`, `9.17a#1`, `9.17b#4`, `9.19b#2`,
`9.24c#3`, `9.27a#0`, `9.32a#1`, `9.34a#1`, `9.38c#4`, `9.43c#0`,
`9.44b#0`, `9.45a#0`, `9.45b#0`, `9.46a#2`, `9.48a#2`, `9.48a#3`,
`9.48c#0`, `9.2c#0`, `9.8b#0`, `9.12c#0`, `9.22c#1`, `9.40c#2`.

(Full per-box rows: `cache/box_audit.jsonl`.)

## (c) Tolerances the labels support

- **Edge σ**: residual |stated edge − nearest defended cluster| p90 =
  2.1 p (top) / 1.6 p (bot); touch scatter σ ≈ 0.5–0.7 p.
  - `edge_from_bars` (σ=1.5): supported — residuals med 0.3.
  - `meas` (σ=2.0): supported.
  - `eye` (σ=5.0): labels are tighter than the allowance — residual p90
    ≈ 2–3 p; 5 p is generous but not wrong.
- **Start**: `t0 − build_start` med 0 / p10 −15; `first_touch − bs`
  med +5 / p90 +45. The funnel's candidate-start rule (±20 min of
  `build_start`, fallback `t0`) covers the median exactly and fails the
  ~10% where the true anchor is a prior swing extreme >20 min before
  the labelled start — a proposer that anchors at the *first defended
  touch* lands ~+5 min late (safe), but must also allow anchoring at a
  swing high/low up to ~45 min early for the tail.
- **Poke allowance**: med depth 1.2 p, p75 ≈ 2.5 p, p90 6.4 p — a
  ~2 p tease tolerance matches production `tease_tol_pips=2.0`; deep
  pokes (>4 p) exist but are rare and mostly inside the window.

## (d) Trusted subset for tuning

**TRUSTED** = usable ∧ scorable ∧ `flag_contain_ok` ∧ `flag_top_sup` ∧
`flag_bot_sup` ∧ `flag_geom` → **68/108** boxes (list: `trusted=True`
rows in `cache/box_audit.jsonl`). All X2 anatomy claims and X3
trusted-subset recall use this set.
