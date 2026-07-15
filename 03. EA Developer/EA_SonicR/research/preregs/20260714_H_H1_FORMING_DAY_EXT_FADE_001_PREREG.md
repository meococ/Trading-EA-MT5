# Prereg — HYP-H1-FORMING-DAY-EXT-FADE-001

Date: 2026-07-14  
State: `FROZEN / preregistered`  
Lane: Discovery Wave6  
GPT: waived

## Identity
- ID: `HYP-H1-FORMING-DAY-EXT-FADE-001`
- Symbol/TF: USDJPY H1 · Window 2021.01.01–2025.12.31
- Explicitly not: D1→H1 PB cont / gap fade / Asia-London fail-fade / Donchian MR

## Thesis
After ≥10 H1 bars of the forming day and forming range ≥0.80×ATR14, fade a pierce
beyond 0.90 of forming day range toward day mid. Late-day extension mean-revert
without session-box mining.

## Locked
Hours 12–18 UTC; Mon–Thu; max 1/day; RR toward mid capped at 3; risk 0.5%;
SL beyond extreme ±0.1 ATR; max hold 10 H1. Offline +$12 x1.5 baked.

## Gates
KILL: N<80 ∨ tpw∉[1,6] ∨ PF<1 ∨ x1.5<1.25  
HIT: PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00  
Model 0 only if PROBE_SURVIVOR.

De-dup: `readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md`
