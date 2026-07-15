# A priori freeze — HARD PIVOT W10 high-R / multi-day

Date: 2026-07-15
Status: `APRIORI_FREEZE__PRE_METRICS`
Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`

## Cost-economics thesis (frozen)
- Cash R a priori ≈ $500 (deposit×0.005).
- High-R A target MFE ≈ 3.5×R = $1750 ≫ $12.0 RT.
- High-R B target MFE ≈ 3.0×R = $1500 ≫ $12.0 RT.
- Friction fraction of target ≤ 1%; NOT location-accept scalp economics.

## Universe
- Symbols: EURUSD, GBPUSD, USDJPY
- Window: 2021-01-01 → 2025-12-31
- Haircut: +$12.0 RT a priori on every closed trade

## High-R objects (membership frozen before combo metrics)
| Slot | hypothesis_id | clock | RR | hold_H1 | priority |
|---|---|---|---|---|---|
| A | HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001 | Mon WO bias → Tue–Thu H4 retest | 3.5 | 60 | 1 |
| B | HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001 | D1 displace → H4 mid reclaim | 3.0 | 72 | 2 |
| BOOK | HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001 | pool A+B | — | — | — |

## Optional thick-rare book ≠ W9 (NY-raid / fail-2D / H4-swing)
| Slot | hypothesis_id |
|---|---|
| C | HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001 |
| D | HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001 |
| BOOK2 | HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001 |

## Caps / overlap (a priori; fail closed)
- Weekly PnL corr ≤ 0.35
- Same-symbol H1-bar overlap frac ≤ 0.05
- Heat: max 1 trade per (symbol, H1 bar); priority A>B / C>D
- Book screen: tpw ∈ [2.0, 5.0]; PF@$12 ≥ 1.30; x1.5 ≥ 1.25; N ≥ 80

## Forbidden
FVG densify; W1–W9 densify; R10–R31 densify; swing ADX/TD-ROC densify;
Donchian densify; Outside densify; D1 volregime densify; carry/anticarry densify;
exit/MaxKZ densify; Phase-0 ceremony.

## Model 0
WITHHELD unless any PROBE_SURVIVOR.
