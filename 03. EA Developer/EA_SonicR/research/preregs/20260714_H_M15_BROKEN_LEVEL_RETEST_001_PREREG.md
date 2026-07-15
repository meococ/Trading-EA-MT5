# Prereg — HYP-M15-BROKEN-LEVEL-RETEST-001

Date: 2026-07-14  
State: `FROZEN / preregistered`  
Lane: Discovery Wave6  
GPT: waived

## Identity
- ID: `HYP-M15-BROKEN-LEVEL-RETEST-001`
- Symbol/TF: USDJPY M15 · Window 2021.01.01–2025.12.31
- Explicitly not: H1-BOS+EMA-PB / H4-struct / PDH retest / stop-run accept

## Thesis
M15 swing pivot (L=3) break, then retest of broken level within 8 bars with
close holding break side → continuation. Session-structure with higher base rate
than rare H4 objects.

## Locked
Mon–Thu; RR=3; risk 0.5%; SL beyond level ±0.15 ATR; max hold 24 M15;
weekend/hour≥22 flat. Offline +$12 x1.5 baked.

## Gates
KILL: N<80 ∨ tpw∉[1,6] ∨ PF<1 ∨ x1.5<1.25  
HIT: PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00  
Model 0 only if PROBE_SURVIVOR.

De-dup: `readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md`
