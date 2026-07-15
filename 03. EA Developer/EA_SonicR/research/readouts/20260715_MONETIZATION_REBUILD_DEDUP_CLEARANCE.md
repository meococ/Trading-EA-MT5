# De-dup clearance — monetization rebuild

Date: 2026-07-15
Authority: Owner rebuild authorized; EXO_FRED_DISPLACE_SPAM_PAUSED

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001` | Partial scale-out | ≠ BE@1R; ≠ MFE stall; ≠ vol-target; ≠ H4 gate |
| `HYP-RR2-EXIT-TIMEBOX-SCALPLOCK-2H-001` | Time-box scalp lock hybrid | ≠ ATR OHLC; ≠ MFE stall timer; ≠ BE clamp |
| `HYP-RR2-VOLREGIME-RMULT-H1ATR-001` | Vol-regime TP multiple | ≠ H4 EMA gate; ≠ entry densify; ≠ sizing vol-target |

## Banned collisions

- BE@1R / MFE stall-cut / vol-target / H4-regime
- FRED / XS / LNY / Asia densify
- Using voided OHLC false-SL path as kill authority for scale-out/ATR

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 ∧ stress lift vs RR2 baseline x1.5.

## Clearance

**CLEARED** for offline probe only (outcome-faithful scoring).

