# HYP-ICT-FVG-FRIDAY-SAFE-EURUSD-M5-013 - frozen Friday execution hardening

Status: **FROZEN AFTER DEFECT DIAGNOSIS, BEFORE SOURCE CHANGE OR CHILD OUTCOME**

## Parent evidence and defect

- Parent: terminal `HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012`.
- Parent source SHA-256:
  `8B1C9E283B97716C91F61FCDB2A74B6168CC0671DAE896A941F0F181674E6CE1`.
- Immutable parent snapshots are the source bound by runs `20260719_161929`
  and `20260719_162104`.
- Parent forensics found 37 positions held across the Friday market close for
  `-13.6189227234R`. The source waits for a tick at or after `22:00 UTC` before
  requesting a close. The tested feed stops producing Friday ticks before
  that threshold and the next request is therefore made on the first Sunday
  quote.
- This defect is independent from the killed parent economics. Removing the
  weekend contribution cannot rescue approximately `-332R`; HYP-012 remains
  terminal and supplies no rerun, promotion or tuning authority.

## Legal engineering delta

The child may change only Friday execution safety, embedded identity/version,
tests and engineering receipts:

1. Add an explicit Friday cutoff fixed at `20:55 UTC` using the existing
   server-to-UTC conversion. The cutoff is deliberately earlier than both
   observed seasonal FX close schedules; it was not selected by PnL outcome.
2. Veto new entries on Friday at or after the same cutoff. Existing London and
   New York session rules remain unchanged.
3. On each available tick at or after the Friday cutoff, request closure of an
   owned position before any stop-management or new-bar signal processing.
   A failed close remains fail-closed and is retried on subsequent ticks.
4. Retain the existing daily cross-day/`InpFlattenUtcHour` rule as a separate
   safety layer. Do not add a timer-based synthetic quote or trade without a
   current market tick.
5. Do not change any signal state, feature, session boundary, news rule, stop,
   target, break-even, risk percentage, spread cap, cadence cap or preset
   economics.

## Red-first verification

- A new source-contract test must fail against parent SHA
  `8B1C9E...E6CE1` and prove:
  - the `20:55 UTC` Friday cutoff is explicit and input-validated;
  - `CanOpenNow` vetoes Friday entries at/after that cutoff;
  - `ManageOwnedPosition` closes at the cutoff before stop tightening;
  - `OnTick` calls position management before bar/signal processing;
  - the parent signal/context functions are not changed by the engineering
    delta except for embedded identity/version.
- All package tests, AlphaFactory compile, exact-source non-repaint audit and a
  new source/binary/compile-log receipt must pass.

## Frozen verification boundary

- This is an engineering repair, not an economic challenger. No Model-0 PnL
  run, threshold search, HYP-012 replay or performance claim is authorized.
- A deterministic offline replay over the 37 diagnosed weekend-crossing rows
  may verify that each row would have been subject to the Friday cutoff; it may
  not substitute a hypothetical close price or recompute parent economics.
- Historical spread/slippage provenance remains failed and
  `promotion_eligible=false`. No paper/live attachment is authorized.

