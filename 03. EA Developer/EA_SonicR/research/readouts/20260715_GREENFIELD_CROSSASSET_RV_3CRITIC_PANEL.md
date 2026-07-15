# 3-critic panel — Cross-asset / RV greenfield (Round 6)

Date: 2026-07-15
Nested model: `cursor-grok-4.5-high-fast`
Parent: FX3 H4 R1–R5 OHLC path/cont/fade family **SATURATED** under +$12.

## Named classes (≥3)
1. `EUR_TRIANGULAR_PARITY_RESIDUAL_MR` — rank 4.5
2. `EQUITY_FX_BETA_RESID_FADE` (NAS100 proxy; US500 missing) — rank 4
3. `XAU_XAG_RATIO_RESIDUAL_MR` — rank 4
4. W1 HL-break sleeve — parked (N/tpw joint-screen risk)
5. M15 thick-stop non-SB — parked (cost + densify contamination)

## Top 3 selected
- EUR triad H1 parity residual MR
- USDJPY H1 × NAS100 frozen-β residual fade
- XAU–XAG H1 ratio ZMR

## Critic merge
| Critic | Stance |
|---|---|
| Sonic trader | PASS — objects outside H4 path states |
| Quant | SOFT — residual edges often cost-killed; still lawful probe |
| MQL5/MT5 | PASS — closed-bar sync; no tick-cost claim; no Model 0 yet |

Model 0: **WITHHELD** until PROBE_SURVIVOR.
