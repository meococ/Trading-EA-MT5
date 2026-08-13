# HYP-EIBB-XAUUSD-M15-001 — source result

Verdict: `PASS_SOURCE_FEASIBILITY_DIRECT_M5_TO_M15_MQL5_BUILD_AUTHORIZED`.

- FivePercent XAUUSD M5 design rows: 351,303.
- Valid exact-triplet M15 bars: 115,746.
- Valid four-bar initial-balance dates: 1,290.
- Raw/executable/gap-rejected events: 1,287 / 1,287 / 0.
- LONG/SHORT: 664 / 623.
- Cadence: 4.93373494 per elapsed week.
- Annual executable counts: 257 / 258 / 257 / 258 / 257.
- Exact-next coverage: 100%; max-year share: 20.0466%.
- All frozen source gates passed; no outcome, return, PnL or post-event price
  was read.

The only authorized build is an M5 EA that reconstructs each M15 bar from the
same exact three M5 constituents. Native-M15 substitution is not authorized.

