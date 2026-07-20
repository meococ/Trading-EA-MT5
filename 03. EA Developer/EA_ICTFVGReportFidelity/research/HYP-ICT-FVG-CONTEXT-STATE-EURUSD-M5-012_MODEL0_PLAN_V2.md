# HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012 — pre-outcome amendment V2

Status: **FROZEN BEFORE HYP-012 SOURCE CHANGE, COMPILE OR OUTCOME**

Date frozen: 2026-07-19

## Bound parent contract

This amendment binds and preserves every signal, execution, window, preset,
measurement, stop rule and no-tuning boundary in:

`HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012_MODEL0_PLAN.md`

Parent-plan SHA-256:
`86B0353905751BE905326DB1116D4B89401FF8F6C861755071D7CE4034F47FF5`.

No strategy rule or preset changed. This V2 exists because the registry
validator rejected the draft's non-schema acceptance fields and PF 1.10 floor
before any source edit, compile, Tester run or outcome access.

## Replacement acceptance contract

The workspace-standard acceptance contract is:

- minimum PF: `1.30`;
- cadence: `2.0–5.0` trades per elapsed calendar week;
- maximum drawdown: `8.0%`;
- minimum PF at cost stress x1.5: `1.25`;
- minimum PF at cost stress x2: `1.00`;
- maximum Monte Carlo P95 drawdown: `8.0%`.

The parent plan's additional diagnostic comparisons remain measurements, not
registry acceptance fields:

- at least 800 defined-risk closed positions;
- PF improvement over control at least 0.20;
- expectancy at least +0.05R/trade and improvement at least +0.15R/trade;
- at least six positive entry years;
- no single entry year above 35% of positive P&L.

Because verified historical cost provenance is absent and the full-chart
history previously reported 99%, passing these measurements can produce only
`ITERATE_FRESH_OOS_REQUIRED`. It cannot authorize promotion, paper or live.
