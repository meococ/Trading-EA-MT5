# HYP-SMOM-JPY-M5-001 — FROZEN PREREGISTRATION

Status: FROZEN before any governed run of this hypothesis ID.
Frozen at: 2026-09-18 (post-Stage-0 probe `probe_trend_continue.py`, pre-run).

## 1. Falsification context (why this direction)

21 governed kills + 4 Stage-0 campaigns falsified: tight-geometry M5 scalps,
sweep reversion, ORB open-drive, cross-asset lead-lag, session-boundary FADE
(BEDGE PF 0.767/0.822), week-open drift. Root cause of the recurring
probe-vs-governed gap: counter-move entries fill at next-bar open AFTER the
reversion started, paying spread on both sides.

This hypothesis tests the opposite entry geometry: **with-trend continuation**.
Slippage between trigger-close and next-bar-open is favorable-or-neutral for
continuation entries, so the governed outcome should meet or beat the probe
book price rather than degrade it.

## 2. Stage-0 evidence (probe_trend_continue.py, 483d M5, next-bar-open booking)

USDJPY:
- LDN-L1W-CONT: n=175, 2.5/wk, +10.59p gross, t=+2.47, half-t +3.0/+0.7
- NY-L1W-CONT: n=185, 2.7/wk, +12.37p gross, t=+2.90, half-t +1.8/+2.3
- NY-L1C-CONT: n=159, 2.3/wk, +13.90p gross, t=+2.87, half-t +2.1/+2.0

Family corroboration: LDN-L1 continuation positive on 6/7 symbols
(EUR +6.60 t=3.09; GBP +4.93; AUD +3.59; NZD +3.66; CHF +3.27; CAD flat).

Causal story: European/NY flow extends the prior session's range break —
the classic London/NY breakout pattern. On USDJPY both legs are USD-driven
extensions, the strongest cell in the map.

Honest cadence expectation: ~4.5-5.5 entries/wk — BELOW the GOAL band
(10-40/wk/symbol). Declared upfront: this test measures whether PF > 1.30
governs; cadence shortfall is a known contract tension, not hidden.

## 3. Frozen mechanism (USDJPY, M5)

Levels (strict past-only, same-day prior sessions):
- LDN leg: prior ASIA session high/low (00:00–07:00 GMT, full session wick extreme).
- NY leg: prior LDN session high/low (07:00–12:00 GMT, full session wick extreme).

Entry:
- LDN leg: first M5 WICK pierce beyond the ASIA extreme during 07:00–09:00 GMT;
  enter WITH the pierce direction at the next M5 bar open.
- NY leg: first M5 WICK pierce beyond the LDN 07:00–12:00 extreme during
  12:00–14:00 GMT; enter WITH direction at next M5 bar open.
- One position max; a still-open LDN trade suppresses the NY trigger.
- First pierce only per session; no re-entry after exit.

Exit:
- Session-end close: LDN leg 16:00 GMT, NY leg 20:00 GMT.
- Catastrophic SL = 25 × ATR(14) (non-binding; BEDGE showed interior stops
  destroy session-hold mechanics). No TP.
- Daily-flat backstop 20:30 GMT. No weekend holds. News blackout ±30 min
  high-impact per substrate calendar.

Filters (declared, complete list): position-open suppression, news blackout,
daily/streak loss locks from substrate, bar-gap data-contiguity guard.
NO ATR floor, NO spread-vs-ATR gate (undeclared gates poisoned BEDGE-001).

Sizing: substrate risk model (fixed fractional risk per trade, margin-checked).

## 4. Environment

- Research plane: AlphaFactory portable isolate, MQ-Demo feed.
- Identity: USDJPY verified coverage 1999→2026-09-11, HQ 99% (SDRIVE-JPY run
  `20260918_081608` fingerprint). All spec inputs pinned via exact_overrides.
- Cost: JPY measured evidence (spread p90 + slip RT + commission proxy).

## 5. Kill / pass criteria (frozen)

- PASS economics: PF > 1.30 at cost x1, trades n >= 300, DD inside budget.
- KILL this hypothesis: governed PF < 1.00 at x1 on n >= 300, OR per-leg
  attribution shows BOTH legs PF < 0.80.
- FAMILY kill (no further SMOM cells): PF < 1.00 AND the probe's positive
  legs both reproduce at PF < 0.90 in the governed run.
- Selection-on-survival subsets (e.g. time-exit-only) are NOT evidence —
  full executed set only.
- Any mechanism change (entry timing, level source, pierce mode, exits,
  filters) requires a NEW hypothesis ID + new prereg.
