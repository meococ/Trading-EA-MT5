# HYP-PDAC-XAUUSD-H1-001 pre-MT5 park

Verdict: `PARK_PRE_MT5_SOURCE_EXECUTION_POPULATION_MISMATCH`

No MT5 baseline or economic outcome was opened.

The source gate counted 564 exact-next events (`2.1621/week`) across all broker
weekdays. The subsequently frozen execution prereg and first MQL5 build blocked
every UTC Friday entry. A read-only ledger reconciliation found 103 Friday
events; the maximum executable population was therefore only 461, or
`1.7673/week`, before position overlap, broker geometry or risk locks. The
economic cadence requirement was structurally impossible.

The first MQL5 build also initialized its new-bar clocks to zero, so an EA
attached during an entry bar could process the signal after the first tick.

HYP001 is parked without an economic verdict. A single bounded engineering
child may preserve the exact two-close prior-day acceptance event and change
only: (1) block new Friday entries from 20:00 UTC instead of the whole Friday;
and (2) seed the current-bar clock on initialization so mid-bar attachment is
fail-closed. No price threshold, direction, timeframe, stop, target, hold or
risk change is authorized.
