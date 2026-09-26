# LEVEL ANATOMY (V2)

Trusted subset: 39 LEVEL_CARRIED + 28 MINI_LEVEL (V1 audit minus Tier-A).
Script: `levellab/anatomy_levels.py` → `anatomy_levels.json`. All measures
causal — only bars strictly before golden `t0`. tol = 2.0 p (LEVEL) /
1.5 p (MINI). Swing stream = engine `swings.py` (θ1 micro / θ2 structural).

## Origin classes

| origin class | LEVEL_CARRIED | MINI_LEVEL |
|---|---|---|
| θ2 structural pivot | 16 (41%) | 14 (50%) |
| θ1 micro pivot | 11 (28%) | 3 (11%) |
| session running extreme | 4 (10%) | 3 (11%) |
| Asia-session extreme | 4 (10%) | 5 (18%) |
| prior-day H/L | 0 | 0 |
| box-edge (≥3-touch cluster) | 0 primary* | 0 primary* |
| other bar / none | 4 (10%) | 3 (11%) |

*box-edge overlaps pivot classes — a congestion edge nearly always *is* a
swing extreme; it never wins as primary class. No broken-line-edge origins.

**The author's levels are old swing pivots.** ~70% of LEVEL_CARRIED and ~61%
of MINI_LEVEL prices sit on a θ1/θ2 pivot extreme. Session/Asia extremes
cover most of the rest. Prior-day H/L: **zero** price matches. Round
numbers: 33% (LEVEL) / 43% (MINI) sit within ±1 p of the 10-pip grid —
*below* the ~60% base rate of the grid itself → the author does not choose
round numbers; the tape chooses the price.

## Shape measures

| measure | LEVEL_CARRIED | MINI_LEVEL |
|---|---|---|
| age p25/p50/p90 (min) | 183 / 365 / 695 | 117 / 325 / 849 |
| age ≥ 6 h | 19/37 | 12/27 |
| prior defences (touches) p50 | 13 | 11.5 |
| touches ≥3 | 33/39 (85%) | 22/28 (79%) |
| lone extreme (0 touches) | 4 | 2 |
| dist at τ (ABR) p50 | 1.64 | 1.32 |
| dist ≤0.5 ABR / 0.5–2 / >2 | 5 / 18 / 16 | 6 / 16 / 6 |
| zone width p50 (pips) | 7.5 | 5.4 |
| carried across sub-panels | 3/39 | 3/28 |
| first-knowable lead p50 | 365 min | 310 min |

## Hypothesis tests (drawing behaviour, not outcomes)

| hypothesis | verdict | evidence |
|---|---|---|
| age < 3 h | **rejected as dominant** | only 24%/30% — the author carries structures half a day old or older |
| first touch | rejected | 85%/79% have ≥3 prior defences; lone extremes are rare (4/2) |
| S1/S2 (θ-pivot) | **confirmed** | 69% / 61% — the dominant origin |
| Asia H/L | partial | 10% / 18% — a real minority class |
| PDH/PDL | **rejected** | 0 price matches on either type |
| round numbers | **rejected** | below grid base rate — price is tape-anchored, not arithmetic |

## What this means for the proposer (V4)

1. Origin universe = confirmed θ1/θ2 pivots + session/Asia running extremes.
   That covers ~90% of trusted golden prices. PDH/PDL and round-number
   proposers would add ink with zero golden support — skip them.
2. Age is a *feature*, not a gate: golden levels are old (p50 ~6 h), so the
   proposer must keep stale pivots alive — opposite of freshness scoring.
3. The draw trigger is approach, not formation: level knowable ~6 h before
   `t0`, median distance at draw-time ~1.6 ABR. A causal proposer should
   surface a level when price *returns toward* a defended old pivot.
4. Defence count is the quality signal: ≥3 touches at the origin band is
   the norm — a lone extreme is rarely drawn.
5. Level = zone ~5–8 p wide: matching tolerance and anti-duplicate NMS
   should use ~±2–3 p, not point prices.
