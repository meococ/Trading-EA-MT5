# HYP-GLDFLOW-XAU-M15-002 — Frozen Preregistration

Frozen: 2026-07-16T08:00:00Z  
Parent: `HYP-GLDFLOW-XAU-M15-001` killed pre-outcome because the official XLSX
omits a direct total-shares field. No data row, signal count, XAU outcome, or
2025+ record was inspected before this freeze.  
Promotion authority: none; one closed-bar 2022-2024 train probe only.

## Causal thesis and deterministic mapping

The causal thesis, lag, split, entry, risk, cost, control and gates are exactly
those frozen in HYP-001. The only operational change is how total shares are
reconstructed from two official archive fields:

`raw_shares = Total Ounces of Gold in the Trust / Ounces of Gold per Share`

The official SPDR page states that one basket is 100,000 shares. To suppress
floating representation noise without choosing a result-driven threshold:

`derived_shares = round(raw_shares / 100000) * 100000`

`delta_shares = derived_shares[t] - derived_shares[t-1]`. Positive means long
XAUUSD on the next US trading day; negative means short; zero means no trade.
No alternative rounding, magnitude threshold, smoothing, percentile, z-score,
direction flip, or use of holdings-tonnage delta is allowed.

Primary source and frozen input:

- `https://www.spdrgoldshares.com/usa/gld/`
- `https://api.spdrgoldshares.com/api/v1/historical-archive?exchange=NYSE&lang=en&product=gld`
- workbook path:
  `03. EA Developer/EA_GLDFlowPulse/research/data/US_GLD_Archive_EN.xlsx`
- workbook SHA256:
  `8E7F1DA21C7169D1950F865731817E191E897E650454F9FA37AE5AD1CBD08C38`

## Frozen split, availability and execution

- `XAUUSD` M15, train `2022-01-01..2024-12-31` inclusive.
- `2025-01-01+` is sealed and must not be loaded, counted or summarized.
- Archive row `t` is usable only on the first XAU trading day after date `t`.
- Entry: first M15 bar at/after `09:30 America/New_York`, IANA DST calendar.
- ATR(14) from closed bars through entry-1; stop `1.50 ATR`, target `1.50R`.
- Maximum 16 M15 bars, stop-first same-bar tie, no overnight/weekend hold.
- One trade per signal day; research risk 0.25% for DD mapping.
- Round-trip cost: 82/123/164 XAU points at x1/x1.5/x2.
- Matched control: same dates/entry/ATR/exit/cost, direction from prior-24h
  closed-bar XAU momentum. Zero control change means no control trade.
- XAU and all retained evidence stay on `D:`; `FILE_COMMON` forbidden and
  protected C roots require before/after invariance.

## All-or-nothing gates

All must pass on 2022-2024:

- cadence 2.0..5.0 trades per elapsed calendar week;
- x1 PF >=1.35, net R >0, expectancy >=0.10R;
- x1.5 PF >=1.25 and x2 PF >=1.00;
- DD at 0.25% risk <=5.5%; at least 2/3 positive years;
- at least 40 long and 40 short trades;
- challenger x1 PF >= control x1 PF +0.10 and challenger x1 net R >= control;
- exact workbook/prereg hash, next-day lag, closed-bar/DST and D-only storage.

Any failed gate is `KILL_AT_OFFLINE_PROBE`: no `.mq5`, compile, Model 0,
mapping change or holdout access. Passing all gates grants build review only,
not promotion/live authority.
