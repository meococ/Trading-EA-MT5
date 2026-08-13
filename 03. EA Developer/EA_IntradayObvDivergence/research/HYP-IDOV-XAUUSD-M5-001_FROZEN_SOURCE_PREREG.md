# HYP-IDOV-XAUUSD-M5-001 — frozen source feasibility

Status: `FROZEN_BEFORE_SOURCE_READ_OR_OUTCOME_ACCESS`

## Thesis

Classical OBV treats tick volume on an up-close bar as positive activity and
tick volume on a down-close bar as negative activity. Over a complete
00:00–15:55 UTC XAUUSD M5 session, disagreement between the full-session price
return and the accumulated signed tick-volume flow is a falsifiable exhaustion
state: fade the price move at the exact next 16:00 open.

This is one daily price–activity disagreement mechanism. It is not DPMO's
total-volume participation momentum, IDEM entropy, ISDS autocorrelation, MFI
pivots/re-entry, or TFCVD quote-arrival polarity. It uses broker-native MT5
bars only; no paid data.

## Frozen mapping

- FivePercent XAUUSD native M5 DESIGN `[2018-01-01, 2023-01-01)`.
- A session is exactly 192 finite, positive-tick-volume, geometrically valid,
  contiguous bars from 00:00 through 15:55 UTC.
- For bars `i=1..191`, add `tick_volume[i]` when `close[i]>close[i-1]`, subtract
  it when `close[i]<close[i-1]`, and add zero on equality. The accumulated sum
  is `signed_tick_volume_flow`; no smoothing, normalization or threshold.
- `session_return = ln(close_15:55 / close_00:00)`.
- LONG only when `session_return<0` and signed flow `>0`; SHORT only when
  `session_return>0` and signed flow `<0`. Equality emits nothing.
- Decision is completed 15:55; availability is exact next 16:00. Inspect only
  the next timestamp, never its price.
- No lookback selection, session subset, weekday rule, cooldown, ATR, outcome,
  cost, future-return or subgroup field.

## Outcome-blind source gates

- design rows `>=300,000`; complete-session and measurement coverage `>=95%`;
- exact-next coverage `>=97%`; executable events `>=500`;
- pooled cadence `2..5/week`, each calendar year `1.25..6.5/week`;
- each direction share `>=30%`; max year share `<=30%`; zero conflicts;
- deterministic same-frame replay.

Any failure parks this exact session-OBV divergence fade. No sign inversion,
threshold, smoothing, session, direction, cooldown or timeframe rescue is
authorized. Outcomes and economics remain sealed.
