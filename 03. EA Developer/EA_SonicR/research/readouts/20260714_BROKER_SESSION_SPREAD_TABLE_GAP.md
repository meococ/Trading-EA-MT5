# Broker SessionxSymbol Spread Table — Honesty Assessment

## Conclusion: **GAP** (not SHA-freeze eligible for research cost surface)

No reconstructable multi-year (or multi-session-calendar) session×symbol spread/commission table was found that can support an honest research cost surface for RR2 **session-gated** cost probes.

## What exists
- QFSI quote ticks under `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_QFSI_*` — **single calendar day** (`2026-07-14`), partial session captures.
- Peer aggregate `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI.json` — useful as **PARTIAL** lot-scaled P50/P90 proxy; honesty flags include `QUOTE_ELAPSED_DAYS_FAR_BELOW_90`, `SESSION_HOUR_COVERAGE_SPARSE`, `NOT_CONFIRMED_COST_PROVENANCE`. Sparse hour cells ≠ multi-year session×symbol surface.
- Commission lifecycle / deal-history: EURUSD unique N=2; USDJPY commission 0; slip MISSING≠0.

## What was built (diagnostic only)
- `preflight/20260714_QFSI_TICK_HOUR_SPREAD_DIAGNOSTIC.json`
- Hourxsymbol P50 of (ask-bid) from available QFSI ticks.
- Explicitly labeled **NOT** a multi-year research cost surface; insufficient days; commission incomplete.
- Receipt SHA: `B38F41C52BE258E2B5C80C67C98D306DB429654E3A1B7B1CD3C0AD01382E8433`

## Policy
- Do **not** invent spreads.
- Do **not** gate-probe RR2 with the diagnostic table.
- SHA-freeze of a research cost surface remains **blocked** until multi-day/multi-regime Real quote+commission coverage exists.
