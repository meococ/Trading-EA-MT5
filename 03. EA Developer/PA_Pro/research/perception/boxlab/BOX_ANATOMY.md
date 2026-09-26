# BOX_ANATOMY — X2: how golden boxes are actually built (n = 69 trusted)

Trusted subset from X1 (`cache/box_audit.jsonl`, `trusted=True`,
scorable). Swings = the engine's own `swings.py` DCStream+SwingBook
(k1=0.8·ABR, pmin=0.5·ABR, pstruct=2.5·ABR, spike=2.5·ABR) run per day.
Script: `boxlab/anatomy_boxes.py` → `cache/anatomy_boxes.json`.

## 1. Start anchor — the box begins at a swing extreme

| anchor at `build_start` (±15 min) | n |
|---|---:|
| θ2 structural pivot | 46 |
| θ1 micro pivot | 21 |
| first edge touch / session / other | 2 |

**97% of trusted build windows start at a confirmed pivot extreme** —
the bar where the prior leg turns into congestion. Not at a session
boundary (0/69), not at a day extreme (day_extreme caught 0 after
pivots). The pivot's `t_ext` is the anchor; `t_conf` lags a few bars —
a causal proposer can only *recognise* the anchor at t_conf, so the
drawn/labelled start is the pivot's extreme bar, reachable causally.

## 2. Edge construction — edges ARE pivot extremes

| edge | θ2 piv | θ1 piv | pivot outside window | pure cluster |
|---|---:|---:|---:|---:|
| top | 39 | 14 | 14 | 2 |
| bottom | 49 | 11 | 7 | 2 |
| breakout edge | 43 | 12 | 9 | 3 |

- ~78% of edges coincide with an **in-window** confirmed pivot extreme
  (≤2 p); another ~15% reuse a pivot formed *before* build_start
  (`piv_outside_window` — the barrier was pre-existing). Only ~4/136
  edges are pure touch clusters with no pivot nearby.
- `brk_edge_pre_level` True 32 / False 35: about half of breakout edges
  were already a level before the window (barrier pre-formed — R9a's
  "buildup against a barrier"), half are created inside the window.
- `brk_edge_day_ext` 5/67: the breakout edge is rarely the day's
  running extreme — boxes sit mid-range (box height = 18% of day range
  med, p90 43%).
- Wick vs close: the edge sits at the *defended extreme* — the audit's
  `hi − p95_high` ≈ 0 shows the labelled edge is the p95 of window
  highs, i.e. the extreme with company, ~1.5 p inside the absolute max
  (shallow pokes do not move the edge).

## 3. Draw moment — knowable ~15 min before the break

- `knowable_min` = first bar with ≥2 hug-bars on each edge AND ≥6
  contained closes: med **−15 min** before build_end (p10 −163).
- 2nd touch on the breakout edge: med **−22.5 min** before build_end
  (p10 −168).
- 12/69 trusted boxes never reach the strict knowable condition
  in-window (short windows: 10–30 min builds with thin touch counts —
  these need a "2 touches total per edge" variant or a fast-lane for
  compressed builds).

## 4. Buildup against the barrier (R9a)

- Pressure (opposite-side creep toward the breakout edge): med +2.7 p
  (p90 +14.6) — real but mild; ~1/3 of boxes show negative creep.
- Late-window closes lean to the breakout side: med 0.75 of last-third
  closes on the breakout half — the strongest single buildup signal.
- Compression (median window range / ABR): med **1.08** — in-window
  bars are NOT compressed vs ambient ABR. Boxes are not tighter tape;
  compression is not a usable gate.
- EMA25 sits *inside* the box in 48/67 cases (above 14, below 5) —
  boxes straddle the EMA; no EMA-edge guidance.

## 5. Nesting and Asia

- Only 4/69 trusted boxes are nested inside a wider golden box on the
  same panel — golden nesting is rare (the book labels one box per
  congestion episode).
- 22/69 start in Asia hours (bs < 480): Asia-born boxes are common;
  they are ordinary boxes, not a separate class (but see CONTEXT_RANGE
  for the pure session-range annotation).

## 6. End — break and tail

- `break_bar − build_end` med +5 min (X1): build_end ≈ first decisive
  close beyond the band (±1 bar).
- Drawn tail `t1 − be`: med +5 min, p90 +90 — the drawn rectangle often
  extends past the break (the book keeps drawing until the next
  picture-relevant event); the containment window is what matters.
- break_dir up 35 / down 32 — symmetric.

## 7. Engine comparison — where generation fails (all 108 scorable)

Nearest cand_log candidate per golden box (`miss_classes.py`,
`cache/miss_classes.json`):

| class | v0 | v1 |
|---|---:|---:|
| matched (born+assigned) | 23 | 5 |
| right but filtered (selection) | 8 | 25 |
| right, born twin lost assignment | 3 | 2 |
| right place, wrong edges | **57** | **52** |
| right edges, wrong start | 5 | 1 |
| too late | 2 | 6 |
| never near | 10 | 17 |

oracle ≈ matched+right_filtered+right_born_lost = v0 **34**, v1 **32**
(≈ FUNNEL's 33/108 = 0.31 each).

Edge errors of nearest in-vicinity candidate: |lo_err| med 3.0 (v0) /
4.2 (v1) p, |hi_err| med 2.9/2.8 p, |start_err| med 10 p90 45–50 min,
birth − be med 45–55 min (proposals arrive ~an hour after the golden
window closed — both engines draw the congestion late).

wrong_edges sub-patterns (v0/v1): `one_edge` 33/28 — one edge right,
the other off (a neighboring band's edge, an excursion cluster, or the
mid-line); `narrower_band` 10/15; `shifted_band` 7/8; `wider_band`
7/1. v0 nearest routes: `pullback_end` 82/96. v1: `cluster_range` 53,
`congestion_scan` 36.

**Diagnosis.** Both engines live in the right neighborhood but draw
edges from *adjacent* defended levels (excursion clusters, thrust
extremes, mid-band shelves) rather than the two pivot extremes that
bound the golden box, and they propose ~45–55 min after the golden
build_end on median — after the break, not during the buildup.

## Consequences for X3 (the proposer's blueprint)

1. **Anchors**: candidate edges = confirmed pivot extremes only
   (θ1+θ2); start = the earlier anchor pivot's `t_ext` (causal via
   `t_conf`, anchored backwards).
2. **Edges**: the *extreme with company* — pivot price, not the window
   max; excursion/wick clusters never widen an edge (R12).
3. **Draw**: emit when both candidate edges have defence evidence
   (≥2 hug bars or a touch+poke) AND ≥K contained closes since start —
   lands ~15–25 min before build_end, satisfying `t_birth ≤ be + 10`.
4. **End**: first decisive close beyond edge − tease_tol ~2 p ends the
   window (D9).
5. Selection features to test: pivot prominence (θ2 vs θ1), structure
   age (`t_now − t_ext`), late-close-side lean, containment tightness.
