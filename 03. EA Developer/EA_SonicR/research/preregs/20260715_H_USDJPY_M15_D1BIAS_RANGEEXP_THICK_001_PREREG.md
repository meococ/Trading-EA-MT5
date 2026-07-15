# Prereg — HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001

Date: 2026-07-15
State on freeze: `preregistered` (offline probe first)
Authority: Owner unpark M15 thick-stop-from-scratch; ≠ PDH/SB densify

## Identity
- Hypothesis ID: `HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001`
- Parent: parked M15 thick-stop class; **replacement** after PDH sketch INTAKE_KILL

## Thesis
D1 EMA50 sets bias. Entry is **M15 range expansion** (range ≥ 1.5×ATR14) with close in outer third in bias direction. Stop architecture is thick (2.5×ATR) from scratch — not SB FVG, not PDH/PDL break, not ORB/IB.

## Locked Design
| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 + D1 bias |
| Bias | D1 close vs EMA50 |
| Entry | M15 range≥1.5×ATR; outer-third close w/ bias |
| SL | 2.5×ATR14(M15); no fixed TP |
| Exit | time ≤16 M15 **or** opposite D1 bias |
| Caps | 1/day; Mon–Fri |
| Window | 2021.01.01–2025.12.31 |
| Cost screen | +$12 / x1.5 / x2 joint |

## Banned
- PDH/PDL break entry (parked densify)
- SB FVG / KZ / RR / MaxKZ densify
- ORB / IB / Asia-coil / LNY session retune
