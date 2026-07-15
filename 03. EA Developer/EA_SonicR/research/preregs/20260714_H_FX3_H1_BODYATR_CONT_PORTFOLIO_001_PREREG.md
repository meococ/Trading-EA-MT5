# Prereg — HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001

Date: 2026-07-14  
State: `FROZEN / preregistered`  
Lane: Discovery Wave6  
GPT: waived

## Identity
- ID: `HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001`
- Symbols: EURUSD + USDJPY + GBPUSD (equal a priori pool) · TF H1
- Window 2021.01.01–2025.12.31
- Explicitly not: ATR%ile Donchian / VolExp / TickVol / halfback / GBPJPY-lead /
  SB-Spark densify

## Thesis
Closed-H1 body ≥1.0×ATR14 with close in extreme quartile → next-open continuation.
Same rule on three majors pooled a priori to lift cadence while keeping
vol-normalized (body/ATR) thickness — not hist ATR%ile clone.

## Locked
Mon–Thu; RR=2.5; risk 0.5% per trade; max 1 trade/symbol/day; SL beyond signal
extreme ±0.1 ATR; max hold 12 H1; weekend/hour≥22 flat.
Cost stress: +$12 cash per trade x1/x1.5/x2 on pooled book.

## Gates
KILL: N<80 ∨ tpw∉[1,6] ∨ PF<1 ∨ x1.5<1.25  
HIT: PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00  
Model 0 only if PROBE_SURVIVOR (would require multi-symbol Model0 plan).

De-dup: `readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md`
