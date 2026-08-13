# HYP-ISVA-XAUUSD-M5-001 — source result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_DAILY_SEMIVARIANCE_CLV_ABSORPTION`

The sole deterministic outcome-blind source attempt completed with structured
evidence. Exact daily joint downside/upside semivariance dominance and terminal
close-location absorption is too sparse for the target operating envelope.

- DESIGN rows: `351,303`; exact complete sessions `1,276 / 1,305` (`97.7778%`).
- Raw/executable: `105 / 105`; exact-next `100%`.
- LONG/SHORT: `71 / 34` (`67.62% / 32.38%`).
- Cadence: `0.402519/week`; yearly `0.3260–0.4986/week`.
- Max-year share: `24.7619%`; conflicts `0`; replay PASS.

Evidence SHA256: start `DC797317...5A829`, report `1AAD1E3B...570DF`, ledger
`D6A1BB6A...CD74`, receipt `FC174B79...C278`, terminal
`EC0538E1...8D02D`.

No outcome, return, trade, cost, PF, MQL5, MT5, validation or holdout was
opened. Do not relax the CLV terciles, change the checkpoint/session, replace
strict variance dominance, delete a direction or change symbol/timeframe under
this ID.
