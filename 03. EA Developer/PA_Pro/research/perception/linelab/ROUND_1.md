# L3 ROUND 1 — first working anchor-first prototype

Config (`lines_lab.py` initial):
- anchor pool: alive confirmed θ-pivots (swings.py DCStream,
  k1·ABR) + ±3-bar local extremes (`loc_ext_bars=3`).
- trigger: DC-pivot confirmations only; pair must include the new
  pivot or have it lie within tol (`on` continuation).
- gates: span 4..96 bars, span_max_min 240, slope-direction
  consistency (top lines may not rise > flat/drift), |slope| ≤
  8·ABR/hr, pivot-overshoot veto at 1·tol, min_touches 2.
- birth: argmax score = nt − over/tol − age/120 per event,
  min_score 2.0; one active line per side, replace margin 0.5.
- lifecycle: pierce = 1 close through tol → dead after 1 bar unless
  re-entry; dashed residual extend 3..17 bars.

Two bugs found and fixed during bring-up:
- defended-side close-violation sign inverted for under-lines;
- slope-max compared per-bar slope to per-hour limit unscaled.

## Results

Limited eval (first 14 scorable panels, v2-style matching):
- PATTERN_LINE recall 2/14 = 0.143, precision 0.030,
  lines/panel med 7.5, p90 8.1; trusted subset 2/11 = 0.182.

Candidate dump (all 198 panels): 29,924 gate-passing candidates,
510 matching a golden line (<4p dev over overlap), 95/185 golden
lines with ≥1 match → coverage ceiling 51%.

Day-level 5-fold AUC (any-match labeling, n_pos=510):
- `age_min` 0.69/0.65/0.70/0.84/0.76 → KEEP (only feature ≥0.60
  every fold).
- `fresh` 0.62/0.59/0.59/0.58/0.60 → marginal, fails 3 folds.
- everything else <0.60 overall.

Kill-audit on the 90 never-matched scorable lines (anchor pool at
golden t1, unbounded lookback): 60 have no anchor pair within 4p
(18 at 4–8p), 22 expressible pairs vetoed by `over>1·tol`, 6 by
slope-direction, 1 by touches, 1 pass-all-but-never-triggered.

Veto histogram (per Lead note R11 §3 — the "0 lines/panel" bring-up
bug was the inverted close-violation sign + unscaled slope cap):

| stage | kills among 86 trusted-miss pool |
|-------|----------------------------------|
| no anchor pair <4p (geometry not expressible) | 60 |
| over_pivot veto at 1·tol | 22 |
| slope_sign (drifting top/bottom) | 6 |
| min_touches | 1 |
| pass-all-gates but never triggered | 1 |

## Delta vs intent

- Coverage is the binding constraint (51%), not the score.
- Missing anchors: leg/session extremes that are neither θ2 nor
  ±3-bar-local (e.g., 9.19a#0 "~14:45 low" at 13294 vs θ2 pivot
  13343) and 6h spans > span_max 240 (9.22c#0, 350min).
- `over_pivot` veto at 1·tol kills 22/86 expressible lines —
  golden tolerates ~2·tol pokes.

→ ROUND_2: sess-extreme anchor class, loc-ext triggers,
span_max 360, over 2·tol, drift ×2.
