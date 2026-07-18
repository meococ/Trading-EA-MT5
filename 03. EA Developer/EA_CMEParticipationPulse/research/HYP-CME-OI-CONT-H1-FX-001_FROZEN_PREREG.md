# HYP-CME-OI-CONT-H1-FX-001 — Frozen pre-outcome preregistration

State: `FROZEN_SOURCE_ACQUISITION_PENDING`  
Frozen at: 2026-07-16 before any price outcome was evaluated for this mechanism.

## Economic mechanism

CME major-FX futures open-interest expansion is a public, independently
measured participation field.  A price move accompanied by expanding OI is
treated as new-position participation rather than pure liquidation.  The
candidate tests whether that participation confirmation carries into the U.S.
afternoon after CME's final daily report is public.  This is not a rescue of
KLR/Unicorn/PO3 or the killed futures-only COT threshold families.

## Point-in-time source contract

- Official source: `ftp.cmegroup.com/pub/pub/pub/daily_volume/`.
- Source fields: exact futures rows `EC/EURO FX FUTURE`, `BP/BRITISH POUND
  FUTURE`, `J1/JAPANESE YEN FUTURE`; `Total Volume` and `Open Interest`.
- Final report availability assumption: 10:00 CT on the next CME business day.
- Conservative use time: 17:00 UTC on the next date present in the official
  daily-file sequence.  This is after 10:00 CT in both U.S. standard and
  daylight time.
- Schema-only files inspected before freeze: 2017-01-03, 2022-01-03,
  2025-01-02.  No price outcome was joined to them.
- Research source window: 2017-01-01 through 2023-12-31.
- Holdout source/outcomes: 2024-01-01 through 2025-12-31 sealed.  The single
  2025 schema sample is not authorized for feature or outcome use.
- All corpus, generated features, terminal data and evidence stay physically
  on `D:`. `FILE_COMMON` is forbidden.

## Frozen candidate rule

Universe order for deterministic ties: `EURUSD`, `GBPUSD`, `USDJPY`.

For each official trade date `t` after a preceding official trade date
`t_prev`:

1. Compute each contract's fractional OI change
   `(OI[t] / OI[t_prev]) - 1`.
2. Eligible symbols have strictly positive OI change.  If none are eligible,
   do not trade.
3. Select exactly one eligible symbol with the largest fractional OI change;
   deterministic universe order breaks exact ties.
4. Compute the selected MT5 spot symbol's prior public move from the H1 open at
   21:00 UTC on `t_prev` to the H1 open at 21:00 UTC on `t`.  Zero move skips.
5. At 17:00 UTC on the next date in the official CME file sequence, enter in
   the sign of that prior spot move.
6. Initial stop is `1.5 * ATR(14)` from fully closed H1 bars at entry.  Exit at
   the stop or the 21:00 UTC H1 open on the same UTC date, whichever occurs
   first.  No take-profit, trailing, break-even or discretionary filter.
7. Risk is 0.25% of starting-equity proxy per trade; one basket trade per UTC
   day; no overnight or weekend exposure.

## Frozen matched control

On every candidate publication date, ignore CME OI and select the symbol with
the largest absolute prior public spot move across the same three-symbol
universe.  Trade that move's direction with identical entry, stop, exit, risk
and cost handling.  This is the price-only continuation control.

## Windows and costs

- Train: 2018-01-01 through 2021-12-31.
- Internal validation: 2022-01-01 through 2023-12-31.
- Holdout: 2024-01-01 through 2025-12-31, sealed until both earlier splits pass.
- Offline x1 round-trip cost proxy: EURUSD 1.5 pips, GBPUSD 2.0 pips, USDJPY
  1.5 pips.  x1.5 and x2 multiply those exact costs.  Proxy cost never becomes
  promotion-grade cost provenance; Model 0 must bind same-broker evidence.

## Frozen gates — every split must pass independently

- elapsed-calendar cadence: `2.0 <= trades/week <= 5.0`;
- x1 PF `> 1.30`; x1.5 PF `>= 1.25`; x2 PF `>= 1.00`;
- positive x1 net expectancy and at least 100 trades;
- max balance-path drawdown `<= 5.5%` at 0.25% risk/trade;
- candidate x1 PF at least control x1 PF + 0.10 and candidate x1 net R greater
  than control;
- source parse failures `= 0`, price skips `<= 2` per split;
- no single calendar year may contribute more than 45% of positive x1 R.

Any failed gate is `KILL_AT_OFFLINE_PROBE`: no `.mq5`, compile, Model 0 or
holdout access under this hypothesis.  A pass authorizes one exact-source
closed-bar implementation and matched Model 0; it does not authorize tuning,
promotion, paper/live attachment or a profit claim.
