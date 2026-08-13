# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - target mechanism preregistration

Status: frozen before any DESIGN futures reference or EURUSD outcome payload is
opened; conditional on `SOURCE_DESIGN_PASS`.

## Mechanical correction

CME Euro FX options are options on deliverable `6E` futures.  Their strike is a
futures price, not a spot EURUSD price.  CME's September-6-2019 example requires
a forward/swap-point adjustment when comparing a CME futures-option strike with
an OTC spot-delivery strike.  The earlier unexecuted idea of comparing the pin
directly with EURUSD spot is therefore forbidden.

## Frozen direction reference

For every source-valid unique-pin event:

- exact instrument: the source-defined raw underlying futures symbol, e.g.
  `6EU9`;
- dataset/schema: `GLBX.MDP3`, `mbp-1`;
- symbology: `stype_in=raw_symbol`, `stype_out=instrument_id`;
- interval: `[decision_utc - 60 seconds, decision_utc)`;
- latest valid update by `(ts_recv, ts_event, sequence)` strictly before the
  decision;
- a valid quote requires finite bid and ask, positive bid and ask sizes, and
  `bid < ask`; crossed, locked, one-sided, empty, stale-outside-window, or
  unresolved records are skipped while searching backward inside the same
  fixed 60-second window;
- if no valid update remains, the event is no-trade;
- `ref_mid = (bid + ask) / 2`; depth, trade price, size, and all later updates
  are discarded after validity is established.

No fallback schema or wider time window is permitted after readout.  Target
reference coverage must be at least 95% of source-valid unique-pin events or the
mapping is killed before spot economics.

## Direction and comparator

- `ref_mid < pin_strike`: BUY EURUSD;
- `ref_mid > pin_strike`: SELL EURUSD;
- equality or missing reference: no trade;
- reverse comparator: exact sign reversal on identical events, timestamps,
  execution assumptions, and costs.

No futures-to-spot basis conversion is required for the direction because both
pin and reference are compared in futures space.  The only remaining mechanism
risk is whether the 15-minute direction transfers to broker EURUSD spot strongly
enough after costs; that is an economic hypothesis, not a source assumption.

## Conditional later execution

Only after source and futures-reference coverage pass may the target contract
open broker EURUSD data.  Entry is the first executable MT5 tick at or after the
closed-M15 decision; exit is the first executable tick at or after the official
option expiration.  MT5 spread, commission, dynamic slippage, missing ticks,
and market availability remain binding.  There is no SL/TP, proximity filter,
distance threshold, direction filter, expiry-family selection, or post-outcome
parameter grid.

The static event/direction resource must be hash-bound and point-in-time.  MQL5,
MT5 backtest, validation, holdout, optimization, paper, and live use remain
unauthorized until their later gates are explicitly opened.

Primary anchor: `https://www.cmegroup.com/education/brochures-and-handbooks/cme-listed-fx-options-a-capital-efficient-low-cost-solution.html`

