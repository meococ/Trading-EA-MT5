# VOID — HYP-CHOP-TREND-EU-M15-002

Date: 2026-07-14  
State: `VOID / NEVER_AUTHORIZED`

## Reason

Coordinator de-dup authority
`readouts/20260714_HYP_CHOP_TREND_M15_001_DEDUP_FAIL_CLOSED.md` marks the
entire ChopRegime / ChopTrend CI+EMA family `KILL_FAMILY / FAIL_CLOSED`.
Child Europe-hour ID `HYP-CHOP-TREND-EU-M15-002` is the same causal surface
with a session override and is therefore also void.

## Disposition

- Prereg `preregs/20260714_H_CHOP_TREND_EU_M15_002_PREREG.md` — **not** an
  authorizing freeze for Model 0.
- Receipt stubs under `preflight/chop_trend_m15/contracts/` for EU-002 —
  engineering artifacts only; **do not** backtest.
- No Model 0 run for EU-002 was started under a successful AlphaFactory lock
  (blocked by concurrent SB lock; cancelled after family kill).

## Race note

Parent race run `20260714_000557` (PF 1.08) remains non-authorizing empirical
reinforce only per hot.md / backlog.
