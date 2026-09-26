# CENSUS_DR1_SUMMARY — VPA-DR1 (outcome-blind)

DESIGN 2016-01-01 → 2021-12-31 · EURUSD M5 · defaults per `VPA-DR1_FROZEN_PREREG.md` (θ=0.10, band 0.5, overlap 0.45, expiry 20, room 2.0R, 50-pip grid).
Runtime 11.9s · median ATR14 3.41 pips.

## 1. Cadence (D2)

- EXECUTABLE total: **1** over 314 weeks = **0.003/week** (PB 1, Combi 0)
- Rule D2 applied: **STOP (<3/week): report funnel + recommendation, STATUS PARTIAL**

Per year:

| year | executable |
|---|---|
| 2017 | 1 |

Per session:

| session | executable |
|---|---|
| us | 1 |

## 2. Rejection funnel (evaluations, in gate order)

| stage | count |
|---|---|
| barriers locked | 45073 |
| signal-bar evaluations (close at/through barrier) | 19957 |
| — unique in-session barriers with a signal eval | 3312 (10.55/week) |
| — rejected: outside EU/US session | 15276 |
| — in-session evaluations | 4681 |
| — rejected: skip_warmup | 0 |
| — rejected: skip_direction | 202 |
| — rejected: skip_trend | 2752 |
| — rejected: skip_chop | 284 |
| — rejected: skip_no_buildup | 635 |
| — rejected: skip_room | 779 |
| — rejected: skip_adverse_magnet | 2 |
| — rejected: skip_anti_chase | 26 |
| — rejected: skip_cost | 0 |
| — chop exempted by valid buildup | 278 |
| **EXECUTABLE** | **1** |
| (barrier consumed as missed break, anti-chase) | 23067 |

Note: rejections do not consume the barrier, so the same barrier can be evaluated on several bars; the funnel counts evaluations, not unique barriers.

## 3. What-if diagnostics (NOT the baseline; DR2 decision support)

| variant | executable | /week |
|---|---|---|
| theta_slope=0.0 (book-literal EMA direction) | 1 | 0.003 |
| trend gate off (theta=0, frac=0) | 1 | 0.003 |
| room_r_min=1.4 (book-literal, needs manual exit) | 2 | 0.006 |
| room gate off | 33 | 0.105 |
| signal_max_atr=0.5 (wider signal-bar window) | 1 | 0.003 |
| chop veto off | 1 | 0.003 |
| buildup band widened (hi 0.75, 1 close) | 2 | 0.006 |
| theta=0.0 + room=1.4 + signal 0.5 + no chop | 2 | 0.006 |
| all gates loose (ceiling diagnostic) | 10 | 0.032 |

## 4. Column check (no outcome fields)

CSV columns: `['week', 'exec_pb', 'exec_combi', 'exec_total']`; JSON `outcome_fields`: `[]`.
No PnL, win rate, MFE/MAE or fill-to-exit is computed anywhere in this task (D6).

## 5. Recommendation (D2 STOP)

Baseline DR1 fires **1** executable setup in 6 years (0.003/week), far below the D2 floor of 3/week. The detection layer is not the problem: **3312 unique in-session signal-bar candidates (10.5/week)** exist; the conjunctive gate stack removes all but one. Marginal first-failure counts (in-session): trend 2752, room 779, buildup 635, chop 284, direction 202, anti-chase 26.

Recommended DR2 directions (for Lead approval; all would need a fresh prereg):
1. Replace the AND-stack with a **score/threshold** (the P2b finding: the Lead's own A/B rate is ~8.6/week while DR1's stack keeps 1).
2. **Room gate**: measure against *significant* pivots (higher pivot_lag) or barrier-quality levels only, not every 2-bar pivot; `room gate off` raises executables to 33.
3. Keep the signal-bar entry semantics (D1a) — they are the book-faithful core and the detection layer already yields ~10/week in-session candidates.
4. Re-run this census after any change; do not tune against outcomes (none exist).
