# Cost surface coverage proof (one page)

## Question

Can AlphaFactory/MT5 build an honest multi-session multi-month/year
spread×commission research cost surface tonight?

## Answer

**NO — research-grade freeze still blocked.**

### Why (technical, not login-wait)

1. **Broker tick history depth via `copy_ticks_range`:** observed max **2** calendar day(s) with ticks across USDJPY/EURUSD/GBPUSD/XAUUSD — far below the 90-day research bar. Empty ranges at 120d/30d probes (if any) are recorded in the receipt; this is a terminal/broker retention limit, not an agent stall.
2. **QFSI live accumulate on disk:** still **1** calendar day(s) of Real quote ticks (001–005). Session×hour diagnostics exist but are single-day.
3. **Commission / slip:** deal-history unique commission counts and slip fills remain below freeze thresholds (see `missing_for_research_freeze`). MISSING ≠ 0.
4. **Tester multi-year 'current' spread** is not broker session×hour evidence and must not be SHA-frozen as research cost surface.

### What was SHA-frozen anyway

- Diagnostic/partial table: `20260715_COST_SURFACE_SESSION_HOUR_TABLE_V1.json` SHA `D12519B37A0CB9E24D8141A4099EFCA6C4E1068141CD3861194B2ADD68A9EE48`
- Grade: `SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY` — **not** eligible for RR2 full-cost rebind.

### What would clear the freeze

- ≥90 distinct UTC quote days (Real accumulate or vendor tape)
- ≥30 unique commission observations per primary symbol
- ≥100 side-referenced fill/slip samples per symbol

### Binding blocker

`COST_PROVENANCE_GAP` remains **NARROWED_NOT_CLEARED**. Track B (architecture rebuild) proceeds without inventing a surface.

Receipt: `F2A1F12EFD38E05B82D7B31CB871BD97993ED868C7F9FD3834BB02DDF488002E`
Sample: `03. EA Developer/EA_SonicR/research/preflight/20260715_COST_SURFACE_MT5_HISTORY_SAMPLE.json`

