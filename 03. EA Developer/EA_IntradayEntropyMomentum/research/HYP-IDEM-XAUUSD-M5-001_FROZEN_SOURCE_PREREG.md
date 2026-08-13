# HYP-IDEM-XAUUSD-M5-001 — frozen source feasibility

Status: `FROZEN_BEFORE_SOURCE_READ_OR_OUTCOME_ACCESS`

## Thesis

A complete intraday path with unusually low return-sign entropy represents
directional order rather than merely high activity or linear serial
correlation. When the current session is more ordered than the ordinary median
of its prior 20 complete sessions, continue the sign of the full session return
at the exact next 16:00 UTC M5 open.

This is materially distinct from DPMO's total tick-activity gate and ISDS's
lag-1 return-correlation state. It uses neither volume nor autocorrelation and
does not inherit their outcomes.

## Frozen mapping

- FivePercent XAUUSD native M5 DESIGN `[2018-01-01, 2023-01-01)`; no paid data.
- A session is exactly 192 finite, positive-volume, geometrically valid,
  contiguous bars from 00:00 through 15:55 UTC.
- Compute 191 log returns. Ignore exact-zero returns only in the sign count.
  With `p = positive / (positive + negative)`, binary entropy is
  `H = -p*ln(p) - (1-p)*ln(1-p)`; a one-sided path has `H=0`. A session with no
  nonzero return is invalid.
- Candidate only when current `H` is strictly below the ordinary median of the
  prior 20 valid complete-session entropies. Current day is excluded; every
  valid day updates history after its decision.
- LONG iff `ln(close_15:55/close_00:00)>0`; SHORT iff negative; equality emits
  nothing. Decision is completed 15:55, availability exact next 16:00. Inspect
  only the next timestamp, never its price.
- No fixed entropy threshold, session subset, weekday rule, cooldown, volume,
  ATR, outcomes or future returns.

## Outcome-blind source gates

- design rows `>=300,000`; complete-session and entropy coverage `>=95%`;
- exact-next coverage `>=97%`; executable events `>=500`;
- pooled cadence `2..5/week`, each calendar year `1.25..6.5/week`;
- each direction share `>=30%`; max year share `<=30%`; zero conflicts;
- deterministic same-frame replay.

Any source-gate failure parks this exact entropy/median/continuation mapping.
No median length, entropy formula, threshold, direction, session or cooldown
rescue is allowed under this ID. Outcomes and economics remain sealed.
