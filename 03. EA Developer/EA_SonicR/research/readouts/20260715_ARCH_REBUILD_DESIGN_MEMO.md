# Design memo — ≤2 cost-resilient architecture rebuilds

Date: 2026-07-15  
Lane: single; no-Git; offline-first

## Problem

Parked RR2 `194548` hits research PF~1.38 / ~2/wk but dies under +$12 x1.5
(stress ~1.01). Exo gate spam (FRED displace/ToT) exhausted. Need architecture
that raises **post-friction $/trade** without densifying signal params.

## Rejected tonight (a priori)

- BE@1R / trail-from-BE readout rescue (already falsified).
- New FRED series / exo densify (`EXO_FRED_DISPLACE_SPAM_PAUSED`).
- RR/MaxKZ/session threshold mining from this board.

## Design 1 — Vol-targeted ATR risk (`HYP-RR2-VOLTARGET-ATRRISK-001`)

**Thesis:** Fixed 0.5-lot RR2 makes `risk_usd` path-dependent on SL distance.
Flat friction taxes small-risk legs disproportionately. Normalizing each trade
to median book risk (clip 0.5–2.0×) should stabilize R and lift expectancy after
size-aware cost.

**Frozen formula:** `scale = clip(median(risk_usd)/risk_usd, 0.5, 2.0)`;
`pnl' = pnl * scale`; stress cost `=$12 * scale` (spread scales with size).

**Cadence:** unchanged (all trades kept) → stays in 2–5/wk band if baseline does.

## Design 2 — H4 regime align gate (`HYP-RR2-H4-REGIME-ALIGN-GATE-001`)

**Thesis:** RR2 entries in extreme H4 vol or counter-H4 drift are friction
traps. Allow only mid-vol H4 (ATR%ile 20–80) with EMA20 alignment.

**Frozen:** ATR14, EMA20, lookback 60, band [20,80], closed H4 ≤ entry time.

**Cadence risk:** will thin; kill if tpw leaves [1.5,6].

## Deferred (not in ≤2)

- State-machine Asia-coil→London-fire entry (needs new signal object).
- Path-dependent MFE stall-cut exit (separate from BE@1R; next board if both kill).

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold.
