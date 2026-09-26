# ROUND 4 — L7 coverage attack (MANDATE_LINE_LAB_2 §L7)

2026-09-21, engine hash series: post-L5 `694313a38abc2da6` →
L7-R1 `c3165fcdfc8d7db5` → L7-R2 `ebf320a2183aedb6` → L7-R3 (theta1
terminal anchor) — hash recorded in INTEGRATION_LOG at each run.

NOTE — attribution caveat: `engine.py` was being edited concurrently
by the build lane during this box (a mid-edit `_retire` broke the
suite for ~10 min at ~18:4xZ, then landed).  Engine-hash deltas
therefore mix my `lines.py` changes with their `engine.py` changes;
the funnel labels files record the exact hash measured.

## What was added (per mandate's L7 list)

1. **Terminal anchor** — first implemented as trailing-window argmax
   (R1), then refined to the literal mandate spec: the **θ1 DC
   stream's unconfirmed leg extreme** (`e.dc.ext_idx/ext_price`),
   fresh within `term_lookback_bars=18`, fires on extreme moves (R3).
   Basis: L2 — last touch is wick-only ~48%; draw lag ~1 bar.
2. **Session extremes** — running high/low since the last session
   boundary (480 EU open / 840 US open, gates.py constants); pool
   member only (never a trigger).  Book's named-bar class.
3. **Two-pass scan (R2 fix)** — `_eval` first scans pairs with no
   term/sess anchor; only if none survives does it retry allowing
   `term_ext`.  Reason: R1 showed unmarked terminal anchors crowding
   out confirmed-pair geometry (the fresh anchor wins score_key on
   age, then proposes a worse line — oracle dropped 0.36→0.34 while
   proposals grew 26%).

## Measured (eval_v2 `50e11fd5`, 198 panels, funnel labels)

| round | proposals | right proposals | oracle | born recall | trusted | ink/panel |
|---|---|---|---|---|---|---|
| post-L5 | 3,492 | 125 | 0.36 (67) | 0.109 (20) | 0.128 | 3.45 |
| R1 term-argmax + sess | 4,752 | 125 | 0.34 (63) | 0.098 (18) | 0.113 | 3.60 |
| R2 two-pass | 4,573 | 128 | 0.34 (62) | 0.098 (18) | 0.121 | 3.59 |
| R3 θ1-terminal | 3,776 | 126 | **0.38 (69)** | 0.103 (19) | **0.135** | 3.42 |

## Verdict

**R3 (θ1 DC-extreme terminal anchor, second-class via two-pass) is
the keeper.**  Oracle 0.36 → 0.38 (69 golden covered — the mandate's
coverage item delivered), trusted recall 0.135 = best measured, at
+8% proposal volume (vs R1's +36% spam).  The window-argmax variant
(R1) failed and was replaced; the two-pass rule (R2) is what makes
unconfirmed anchors additive-only.

The residual gap is selection, not generation: 76/126 right proposals
die `rate_limited` (REQUESTS.md REQ-1).  The ~23% "no pair under 8 p"
class is an expressibility ceiling, untouched by anchor additions.

(Pre-L5 v1 for reference: oracle 0.40, born 0.076, trusted 0.078.)

## Read

- Right proposals 125 → 128 under two-pass: the new anchor classes add
  a little coverage without crowding once second-classed.
- But born recall stayed ~0.10 and oracle did not recover to the
  pre-L5 0.40.  Two interpretations, both consistent with the data:
  (a) the stricter birth gates (`min_touch_events=3`) remove weak-but-
  right proposals — that is the intended trade, and born recall still
  rose vs pre-L5 (0.076 → ~0.10);
  (b) the residual coverage gap is selection-side: 75/128 right
  proposals die `rate_limited` (REQUESTS.md REQ-1).
- The "no anchor pair below 8 p" class (~23% of golden) is NOT moved
  by these anchors — it is an expressibility gap, not a trigger gap.
