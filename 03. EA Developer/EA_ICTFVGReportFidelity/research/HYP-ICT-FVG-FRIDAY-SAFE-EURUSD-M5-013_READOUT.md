# HYP-ICT-FVG-FRIDAY-SAFE-EURUSD-M5-013 - engineering readout

Verdict: **PASS ENGINEERING; NO ECONOMIC, PAPER OR LIVE AUTHORITY**

## Outcome

The EA now requests closure of any owned position on the first available tick
at or after Friday `20:55 UTC`, before stop tightening or new-bar signal
processing. `CanOpenNow` uses the same cutoff as an entry veto. The original
cross-day and `InpFlattenUtcHour` checks remain as independent safety layers.

The child source is v1.19, SHA-256
`1E04144A5E26651B993E7A13202FC85B8D5C0AB3FD7C8FAA5D890897E3B4B196`.
Red-first proof observed three failures and one pass against the frozen HYP-012
parent, then all four new tests passed. The package is 35/35 PASS, AlphaFactory
compile is 0 errors / 0 warnings, EX5 is 81,848 bytes, and exact-source
non-repaint V15 is PASS with zero findings. Receipt V18 binds source, binary,
compile log, dependency hashes, frozen plan and non-repaint audit.

## Defect coverage

The hash-bound HYP-012 context ledger contains 37 diagnosed weekend crossings.
All 37 entered before Friday 20:55 UTC and remained open beyond that cutoff, so
all 37 are deterministically subject to the new close rule. Their parent sum is
`-13.6189227234454R`; this number describes the old observed rows only.

No hypothetical 20:55 close price was invented and parent economics were not
recomputed. Actual close success still depends on a tradable quote and broker
acceptance; a failed request is retried on subsequent ticks.

## Boundary

HYP-012 remains terminal. This repair removes a known operational defect but
does not create alpha, validate cost, or authorize another HYP-012 backtest.
The next signal question must use a fresh pre-outcome object. The permitted
next cheap step is a fixed probability-ranking/no-trade rolling-OOS diagnostic;
source implementation is forbidden unless that diagnostic passes its frozen
gate.

