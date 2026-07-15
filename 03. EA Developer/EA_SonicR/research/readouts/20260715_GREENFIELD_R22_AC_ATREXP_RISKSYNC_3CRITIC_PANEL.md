# 3-critic panel — Round 22 AC / ATR-exp / FX3-risksync

Date: 2026-07-15
Nested critic **GO** (break lead-clone local optimum; not R16–R21 densify).

## Named (NON-FADE) — why different mechanisms
1. `FX3_H1_LAG1AC_REGIME_BODY_CONT` — lag-1 return AC regime (≠ VR/ER/lead)
2. `GBPUSD_H1_ATREXP_BURST_CONT` — ATR expansion burst (≠ Parkinson compress/Donch)
3. `AUDUSD_H1_FX3_RISKSYNC_CONT` — same-bar FX risk-sync (≠ XTI/XAU/US30 lead)

| Critic | Stance |
|---|---|
| Sonic trader | PASS — three independent edge stories; AUD sync ≠ oil/metal lead |
| Quant | PASS — AC≠VR; expansion≠compress; FX breadth≠cross-asset lag |
| MQL5/MT5 | PASS — closed-bar as-of; ATR/AC precomputed on closed bars |

Merge: **GO** offline only. Model 0 WITHHELD until PROBE_SURVIVOR.
