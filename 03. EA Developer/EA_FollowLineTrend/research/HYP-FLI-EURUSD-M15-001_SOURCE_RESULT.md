# HYP-FLI-EURUSD-M15-001 — source result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_FOLLOW_LINE_DEFAULT`

The sole outcome-blind attempt `FLI001-SOURCE-001` completed with clean input
bindings and deterministic replay. No next-bar price, order, trade, return,
cost, PF, validation or holdout field was opened.

## Gate result

- EURUSD M15 DESIGN rows: `174061`; usable `174061` (`100%`).
- Raw/executable events: `4021 / 4015`; exact-next coverage `99.8508%`.
- LONG/SHORT: `2008 / 2007` (`50.01% / 49.99%`).
- Cadence: `11.0043/week` — FAIL versus frozen `2–5/week`.
- Annual cadence: `10.1625–11.9153/week` — every year FAIL.
- Maximum year share: `15.52%` — PASS.
- All row, coverage, direction, concentration and conflict gates passed. Only
  pooled and annual cadence failed.

## Evidence

- attempt start SHA256:
  `A7F4D6162BE32081CA9766797BCCFE20C3BC578BC33862C903A4DF2A7082C181`
- report SHA256:
  `8D7E98CDCB363504B53944EC481720F98EF78BDAEF0AA0F100B5D72F40ABAA94`
- ledger SHA256:
  `D6F9823DFCC92FA417D9225DDEAE66FB27F531231DE35768C20F06984B6C39DF`
- receipt SHA256:
  `70C949FF4C1AFF73BF917BFB5EBC0421C432FFFA0DA2AD9277D6060C1E83EC13`
- terminal SHA256:
  `A081285361219F87E4212ECDD01141D4686110B3B79EF459B9613E242DCB5BC5`

## Failure radius

This parks only the normalized default Follow Line mapping on EURUSD M15:
BB21/population deviation1, Wilder ATR5, symmetric first-break initialization,
recursive ratchet and trend-direction flips over 2016–2022.

Do not rescue it by changing BB/ATR parameters, threshold, source seed,
cooldown, quota, session, weekday, direction, timeframe or symbol after seeing
the count. No MQL5 build or economic claim is authorized. Move to a materially
different information mechanism.

