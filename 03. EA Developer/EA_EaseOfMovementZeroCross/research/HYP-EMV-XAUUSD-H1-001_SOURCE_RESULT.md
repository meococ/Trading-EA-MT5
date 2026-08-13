# HYP-EMV-XAUUSD-H1-001 — Source result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_EMV14_ZERO_CROSS`

- Native FivePercent XAUUSD H1, 2018–2022 design window.
- Source rows: 107,679; design rows: 29,461; feature coverage: 100%.
- Raw/executable/gap-rejected events: 2,864 / 2,764 / 100.
- Exact-next coverage: `96.5084%` — FAIL versus 97%.
- LONG/SHORT: 1,377 / 1,387.
- Cadence: `10.5958/week` — FAIL versus 2–5/week.
- Annual cadence: `9.8767–11.2575/week` — every year FAIL.
- Year concentration, direction balance, minimum rows/events and deterministic
  replay passed.
- Outcome counters, trades, PnL, PF, validation and holdout remained zero.

Failure radius is only the exact raw EOM formula, SMA14 and zero-line crossing
on native H1. Do not rescue it through a different period, smoothing, threshold,
cooldown, session, timeframe or direction deletion. This is source
over-frequency/exact-next insufficiency, not an economic no-edge verdict.

Evidence directory:
`research/evidence/HYP-EMV-XAUUSD-H1-001/EMV001-SOURCE-001/`.
