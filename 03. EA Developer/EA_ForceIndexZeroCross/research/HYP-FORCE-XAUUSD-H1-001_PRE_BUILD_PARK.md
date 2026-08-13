# HYP-FORCE-XAUUSD-H1-001 — Pre-build source PARK

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_FORCE13_ZERO_CROSS`

The formula was frozen before the H1 count. An outcome-blind turnover screen on
the native FivePercent H1 source produced:

- design/usable rows: 29,461 / 29,461;
- raw/executable events: 3,730 / 3,704;
- exact-next coverage: `99.3030%`;
- LONG/SHORT: 1,853 / 1,851;
- cadence: `14.1993/week`;
- yearly events: 733 / 714 / 792 / 720 / 745.

No outcome, trade, PnL, PF, validation or holdout field was read. This exact
Force13 zero-cross is structurally over-frequent and is parked before a full EA
build. Do not rescue it with EMA period, threshold, signal line, cooldown,
session, timeframe or direction changes.
