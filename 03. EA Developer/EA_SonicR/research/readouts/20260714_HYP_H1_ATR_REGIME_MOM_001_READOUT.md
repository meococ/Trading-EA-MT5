# Readout — HYP-H1-ATR-REGIME-MOM-001

Date: 2026-07-14  
State: `PARKED` (Model 0 research near-miss; GOAL unmet)  
Run: `20260714_031611`  
EA: `EA_H1ATRRegimeMom`  
Cost: tester `current` / MetaQuotes-Demo — **not** Real QFSI; missing≠0

## Metrics (USDJPY H1 2021.01.01–2025.12.31, Deposit=10000)

| Metric | Value |
|---|---|
| Profit factor | **1.12** |
| Trades | **516** |
| Trades/week (elapsed) | **~1.98** |
| Net | **+$1418.83** |
| Expectancy | +2.75 |
| Equity DD max | **~7.55%** |
| Win rate | 47.29% |

Report SHA256: `BFA0C208A994FC328E2E0E0A3216C259320E506BD22A56770AD1464C9AC8CD60`

## Gates

| Gate | Result |
|---|---|
| Kill PF&lt;1.00 | PASS |
| Kill tpw∉[1.0,6.0] | PASS (~1.98) |
| Kill N&lt;80 | PASS |
| Research bar PF&gt;1.30 + tpw∈[2.0,5.0] | **FAIL** (PF 1.12) |
| Confirmed / Real cost | **NOT claimed** |

## Non-repaint

Closed H1 `bar[1]` only; ATR/EMA buffers shift≥1. Chart must be H1.

## Ceremony note

Alpha closeout threw `includes_sha256` mismatch after report ready; artifacts kept
under `02. AlphaFactory/runs/EA_H1ATRRegimeMom/20260714_031611/`.

## Verdict

Survives kill screen; fails GOAL joint target. **Do not** mine ATR ratio, EMA
period, hour/day, or flip to fade. Not a VolExp/Chop/Stretch rescue.

## Independence

`readouts/20260714_H1_ATR_REGIME_MOM_VS_VOLEXP_CHOP_DEDUP_CLEARANCE.md`
