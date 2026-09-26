# FROZEN PREREG — HYP-BEDGE-CHF-M5-001

Frozen before any Strategy Tester outcome for this hypothesis. 2026-09-18.
First cell of the BoundaryEdge union sleeve — the session-boundary
reversion + week-boundary drift family discovered in the Stage-0 probe
campaign `probe_session_flow.py` -> `probe_close_pierce.py` ->
`probe_retest_calendar.py` -> `probe_asia_fade_union.py` (all
lookahead-free, split-half validated).

## Prior falsification context (declared up front)

- 19 governed kills (era-2 fleet 15, LSW-EUR, LSW-XAU, SDRIVE-GBP,
  SDRIVE-JPY) falsified every tight-geometry M5 scalp family: signals
  were real (~15/wk) but executed economics were PF 0.5-0.8.
- Cross-asset M5 lead-lag falsified at Stage 0 (lag-1 |rho| <= 0.013).
- Session-boundary matrix (3 sessions x momentum/fade x wick/close
  x level-source) mapped: everything noise/negative EXCEPT the Asia
  first-hours close-pierce fade below.
- A look-ahead bug in one probe (including same-day future NY bars in
  a "prior" level) produced fake +8-19p edges; rejected and documented
  in `hot.md`. This prereg's mechanism uses strictly completed
  prior-hour bars only.

## Confirmed Stage-0 evidence (what this cell bets on)

ASIA session (00:00 GMT open): a CLOSE beyond the prior-hour extreme
(12 M5 bars, 23:00-24:00) inside the first 2 hours, faded to session
end (07:00 GMT), immediate entry at piercing-bar close:

| Symbol | n (2022+) | /wk | mean pips | t | net of ~3.6p cost |
|---|---|---|---|---|---|
| NZDUSD | 295 | 4.3 | +7.50 | +7.56 | +3.90 |
| USDCAD | 222 | 3.2 | +7.39 | +8.31 | +3.79 |
| GBPUSD | 265 | 3.8 | +6.73 | +6.16 | +3.13 |
| USDCHF | 302 | 4.4 | +6.28 | +8.22 | +2.68 |
| AUDUSD | 295 | 4.3 | +5.52 | +5.58 | +1.92 |
| EURUSD | 216 | 3.1 | +4.67 | +4.70 | +1.07 |
| USDJPY | 274 | 4.0 | +3.48 | +1.84 | -0.12 (EXCLUDED) |

Both data halves positive on all six retained symbols (regime
stability). Retest/limit-at-level entry measured WORSE everywhere
(forfeits the overshoot); immediate entry is the frozen choice.

Plus the week-open drift leg (hour-of-week scan, same-sign +
|t|>2.8 in BOTH halves, ~1400 cells tested): USDCHF long at Monday
00:00 GMT -> exit 02:00 GMT: +7.16 pips/2h chain (Mon-00h +4.63,
Mon-01h +2.53), n~833+836.

## Hypothesis (frozen)

- **Sleeve:** USDCHF only (cell 1). Same EA may host later cells
  (GBP/EUR/AUD/NZD/CAD fade; JPY/XAU calendar legs) under their own
  hypothesis IDs — NOT this one.
- **Leg A — ASIA-FADE:** on each closed M5 bar with GMT minute in
  [0,120): if bar close > max(high of the 12 bars before 00:00 GMT)
  -> SELL at next bar open; if close < min(low of those 12 bars) ->
  BUY at next bar open. First pierce only, one entry/day max.
- **Leg B — MON-OPEN-CHAIN:** BUY USDCHF at the Monday 00:00 GMT bar
  open; exit at the 02:00 GMT bar (2h hold). Chain entry precedes
  any possible fade entry (00:00 < 00:05), so Monday fade signals
  are suppressed by the position-open filter — declared interaction,
  not an accident.
- **Exits:** Leg A flat at first bar >= 07:00 GMT; Leg B flat at
  first bar >= 02:00 GMT. Catastrophe SL = 4.0 x ATR14(M5) from
  entry (sizing anchor; probe measured unbounded expectancy — SL is
  tail insurance only). TP = 10R (never binds; real exit is time).
  Daily flat server >= 22; Friday flat >= 20 (backstop only).
- **Sizing:** 0.35% equity risk; max 6 entries/day; daily loss lock
  2%; streak lock 4. Account DD lock: **DISABLED** — the 10% latch
  inherited from LSW vetoed 59-68% of all SDRIVE signals and made
  the executed sample unrepresentative of the mechanism; this
  contract replaces it with the daily-loss + streak locks above so
  the governed run measures the mechanism, not the lock.
- **News:** +/-20 min high-impact blackout; fail-open counted.
- **Decision semantics:** closed-bar only; stdlib iATR; shared
  AF_ExecutionKernel; per-leg telemetry counters.

## Environment (frozen)

- **Broker/server:** MetaQuotes Ltd. / MetaQuotes-Demo (AlphaFactory
  portable isolate `mt5-portable-mqdemo`, current build). RESEARCH-ONLY.
- **Coverage mode:** `all_available_asof` — From=1970.01.01 sentinel
  resolved to first real bar (local USDCHF history 2022+; tester syncs
  server history as proven on USDJPY 1999+), To=2026.09.11.
- **Model:** 0. **Cost tier:** `research_proxy` — USDCHF spread/
  slippage/commission measured on the isolate before the run.
- **Data-quality gate:** report History Quality > 97, unbypassed.

## Expected vs GOAL band (declared honestly)

Probe-implied cadence ~4.5-5.5 trades/week (fade ~3.5 after Monday
suppression + chain 1). This is BELOW the GOAL band 10-40/week. The
run's purpose: (a) governed economic validation of the first
cross-validated edge found in this repo (PF gate is the live
question), and (b) hard evidence for the cadence feasibility
boundary already documented in `hot.md`. A PASS on economics with
a cadence shortfall is a GOAL-amendment case for the Owner, not a
silent pass and not a parameter failure.

## Kill criteria (frozen)

- PF <= 1.30 at cost x1, OR PF < 1.25 at x1.5, OR PF < 1.00 at x2.
- Executed cadence < 3.0/week (mechanism diluted beyond probe).
- DD > 10% or MC p95 DD > 15%.
- Any leg with t < 0 on >= 150 executed trades (leg-level falsification).
- Overnight holds > 0 (excluding tester artifacts) or any weekend hold.
