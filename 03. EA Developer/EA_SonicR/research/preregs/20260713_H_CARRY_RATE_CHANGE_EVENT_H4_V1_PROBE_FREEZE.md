# Probe Design Freeze — Carry Rate-Change Event H4 V1

Status: `FROZEN_PRE_RESULT / INDEPENDENT_OF_WEEKLY_RANK_KILL`  
Date: 2026-07-13  
Owner override: local self-research; no ChatGPT dependency.

## Independence claim

Killed book (`20260713_V8_CARRY_DIFF_OFFLINE_PROBE`): Friday D1
**cross-sectional rank** of carry levels → hold one pair/week.

This probe is a different mechanism family:

- Trigger = discrete **change** in lagged money-market differential (|Δcarry| ≥
  frozen threshold), not weekly rank of levels.
- Decision bar = closed **H4** after `available_at_utc`.
- Arbitration = **per-pair independent** event trades (not single-winner book).
- Literature anchor: interest-differential carry risk premium responds to
  funding/policy innovations; Menkhoff et al. (JF 2012) link carry payoffs to
  volatility *risk*, motivating event/innovation focus rather than static weekly
  level ranking. This probe tests **rate-change events** only (not a vol-gate
  rescue of the killed weekly book).

Explicit non-identity with banned rescues: not “same weekly book but daily”,
not multi-pair concurrent rank, not price/vol filters mined from the 13 killed
trades.

## Frozen constants (no post-hoc edit)

| Constant | Value |
|---|---|
| Symbols | EURUSD, GBPUSD, USDJPY |
| Decision TF | H4 closed bar |
| MIN_DELTA_BPS | 5.0 (0.05 percentage points) |
| HOLD_BARS | 12 H4 (~48h) |
| Weekend | force flat on Friday H4 bars with hour >= 16 UTC |
| Cost stress A/B | 1.5 / 3.0 pip RT |
| Train | 2018-01-01 .. 2022-12-31 |
| Holdout | 2023-01-01 .. 2025-12-31 (only if train passes) |
| USD series | DFF∪SOFR, lag +1d |
| EUR | ECB DFR, lag +1d |
| GBP | BoE IUDBEDR, lag +1d |
| JPY | BoJ call ON, lag +2d |
| Direction | sign(new carry level) after change (long high-yield leg) |
| Control | same event times/symbols/holds; direction = sign of prior 20 H4 mid returns |

## Train gates (fail-closed)

1. trades >= 100
2. trades/elapsed_week >= 1.5 (structural path toward GOAL 2–5)
3. PF stress-A >= 1.10
4. PF stress-A > control PF stress-A
5. expectancy stress-A > 0

Holdout (if train passes): trades >= 40, trades/week >= 1.0, PF stress-A >= 1.00,
beats control.

## Authority

Discovery probe only. Survivor → registry + prereg before EA/Model 0.
Demo MT5 falsification only.
