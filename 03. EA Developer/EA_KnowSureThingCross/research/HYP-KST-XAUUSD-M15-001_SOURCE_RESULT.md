# HYP-KST-XAUUSD-M15-001 — source result

Verdict: `PARK_SOURCE_FEASIBILITY_OVER_FREQUENCY_NO_ECONOMIC_READ`

- Default TradingView KST `10,15,20,30,10,10,10,15,9`, with negative bullish
  signal cross and positive bearish signal cross, XAUUSD M15, 2018–2022.
- M15 rows `115,746`; feature coverage `100%` after warmup.
- Raw/executable events `4,471/4,433`; exact-next `99.1501%`.
- Cadence `16.9940/week`, failing the frozen `2–5/week` gate.
- LONG/SHORT `2,231/2,202`; every year `16.57–17.64/week`.
- All non-cadence source gates and deterministic replay passed.
- No post-decision price, trade, return, cost, PF, validation or holdout was
  opened.

Park only this exact default KST sign-conditioned signal crossover. Do not
rescue it with zero-line events, alternate lengths, threshold, cooldown,
session, direction or timeframe. The next mechanism must use a materially
different information family and decision surface.
