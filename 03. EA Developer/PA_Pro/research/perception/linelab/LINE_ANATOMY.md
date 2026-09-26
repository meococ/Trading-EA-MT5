# LINE_ANATOMY — L2: how Volman anchors lines (trusted subset n=141)

Method: `linelab/anatomy.py` + `anatomy_lines.json`.  Anchors measured
at the line's *touch events* (consecutive bars whose defended-side
extreme sits ≤1.5 p of the label, grouped to one bar per event) — NOT
at catalogue t0/t1, which are span bounds, not anchor points (L1).
Pivot classes from the engine's own swing stream (`swings.py`
DCStream k1=0.8·ABR wick-confirm + SwingBook pmin=0.5/pstruct=2.5·ABR),
run per day, causal.

## 1. Anchor types (the load-bearing result)

| touch position | θ2 structural | θ1 pivot | wick-only | spike |
|---|---|---|---|---|
| first anchor | **86 (61%)** | 26 (18%) | 28 (20%) | 1 |
| mid touches  | 57 | **108** | 42 | 1 |
| last touch   | 15 (11%) | 46 (33%) | **67 (48%)** | 1 |

- First anchor ≈ a **structural pivot** ~2/3 of the time.
- Subsequent anchors are mostly **θ1-class or unconfirmed wick
  extremes** — the defended run gets *finer* as it ages; the last
  touch before the break is a micro low/high ~half the time.
- Touch events per drawn line: p25/p50/p75 = **2 / 3 / 4** — Volman
  lines are 2–4-touch objects, not 6+.  (Raw within-tol bars median 6.)
- Named-anchor share: only ~40% of trusted lines have a text-named
  anchor in the clause; the rest are span+side descriptions.

## 2. Span, slope, draw time

- span_min p10/p25/p50/p75/p90 = **30 / 55 / 95 / 170 / 255**;
  19% are short (<45 min), 20% long (>3 h).  v1's
  `context_min_bars=36` (3 h) gate kills the whole short class.
- slope: |slope| p25/p50/p75/p90 = **0.75 / 1.5 / 2.9 / 4.4 ABR/hr**;
  61% below 2·ABR/hr; a real steep tail: 18% ≥ 20 pips/hr (bear-flag /
  momentum legs — DN_LINE §5 was right to allow θ1 anchors there).
- slope sign: dir field consistent in all trusted lines (72 up,
  41 down, 28 unlabeled); side = under 80 / over 42.
- **Draw lag**: second anchor's pivot confirms ~**1 bar** after the
  extreme (p50=p90=1 bar at k1=0.8·ABR wick-confirm) — the author can
  ink almost immediately after the second touch; no long confirm
  delay is needed.

## 3. End reason (why the drawn span stops where it does)

| reason | n | share |
|---|---|---|
| break (close-through within ±2 bars of t1) | 93 | 66% |
| panel edge (t1 ≈ window x1) | 27 | 19% |
| fade (ink stops mid-air) | 21 | 15% |

→ The "solid span ends at the break bar" convention is the *dominant*
one — v1's `t1_drawn = pierce_bar` is right; the 3–17-bar dashed
extension must stay out of the matched span (it does via t1_drawn).

## 4. Relation to boxes (Ruling 9a link)

36 trusted lines overlap a golden BOX span >10 min:
- 16 run *inside* the box (flag lines, necklines inside ranges);
- 10 converge toward an edge; only **2** are textbook pressure-side
  (rising line converging into box top / falling into bottom);
- 12 end beyond the box.

→ "Line = pressure side of a buildup" is real but **rare (~1.5% of
trusted lines)**.  The buildup-pressure feature belongs to BOX/SQUEEZE
scoring (Ruling 9a), not to line detection.  Lines are mostly
standalone barriers/necklines.

## 5. v0 vs v1 anchor rules — what v0 did right

| | v0 (`engine_v0._line_birth`) | v1 (`lines.py`) |
|---|---|---|
| anchor pool | confirmed close-pullback pivots, min_swing 6 p, within 84 bars | alive θ1 pivots + named-bar local extremes (±3 b), within 96 bars; CONTEXT: θ2 only |
| trigger | births when the *newest same-side pivot lands on the pair line* (freshness: `same[-1][0]==idx`) | any pivot confirm → eval; birth via salience round |
| slope rule | \|s\| ≤ 0.30 p/bar (~3.6 p/h) on break-defining side | asymmetric: top lines may rise only if ≤0.5 p/bar and ≤10 p total drift |
| coexistence | one active line per side; merge or replace | NMS/salience budget, re_anchor hysteresis |
| min touches | 2 pivots (then ≥3 touches or ≤3·ABR to price) | ≥2 pivots/anchors within tol + no pivot beyond tol on defended side |

What v0 got right that v1 lost:
1. **Freshness = the draw moment.**  v0 inks exactly when the
   confirming touch lands — matching anatomy §2 (draw lag ~1 bar).
   v1's propose→compete→maybe-birth path loses the moment and often
   loses the slot to boxes/levels under rate caps (DISAGREEMENT_2's
   cap-ordering problem, §9a).
2. **Mid-scale pivot stream.**  v0's close-confirm + min_swing 6 p
   stream sits between θ1 and θ2 — near where golden mid/last touches
   live (§1).  v1's hull route is alive-θ1 + local extremes — the
   *universe* is fine; the failure is downstream (selection + the
   pair trigger requiring the new pivot on/near the pair line within
   tol, which misses anchors connected to *non-hull* intermediate
   points).
3. v0 keeps a single best line per side — cheap dedup that matches
   the golden ~1 line per side per panel.

What v0 got wrong (don't copy):
- slope cap 3.6 p/h removes the 18% steep class entirely;
- close-pullback confirms lag wick-confirms (draw lag would be ≥2-3
  bars, and 6 p min_swing skips micro anchors);
- no named-bar anchor path.

## 6. Implications for the L3 prototype

- Anchor universe: θ1 pivots + named-bar local extremes (±3 b).
  Confirmed pivots cover ~71% of all touch events (θ2 33%, θ1 38%);
  the rest are wick-only extremes — usable as the *terminal* anchor
  (the last defended point needs no confirmation to be inked).
- Proposal trigger: on each new confirmed pivot of side s, pair it
  with each older same-side anchor candidate; also try pairs where
  the new pivot merely *lies on* the line (v1 already does this).
- Score: touch-count (bar-wick, deduped to events) − overshoot − age,
  with **freshness bonus** when the second anchor is the triggering
  pivot — the draw moment is the strongest signal.
- Death: pierce → confirm next bar → t1_drawn at pierce bar; keep the
  dashed carry out of the evaluable span.
- Expected failure zone: steep flag lines (18% of trusted) need slope
  ≤ ~2-4 ABR/hr allowed; wick-only last touches mean the *last*
  anchor should not require pivot confirmation — allow the newest
  local extreme as terminal anchor.
