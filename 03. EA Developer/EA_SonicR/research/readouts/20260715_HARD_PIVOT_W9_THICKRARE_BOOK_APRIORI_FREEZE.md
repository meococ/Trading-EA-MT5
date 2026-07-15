# A priori freeze — HARD PIVOT W9 thick-rare BOOK

Date: 2026-07-15
Status: `APRIORI_FREEZE__PRE_METRICS`
Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`
Book hyp: `HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001`

## Thesis
Thick-rare singles starve cadence; cadence accepts die under +$12.
BOOK of ≥2 independent thick-rare location sleeves → cadence 2–5/wk
while preserving high $/trade per fill. NOT open-FVG-for-cadence.

## Universe (a priori)
- Symbols: EURUSD, GBPUSD, USDJPY
- Window: 2021-01-01 → 2025-12-31
- Haircut: +$12 RT a priori on every closed trade

## Sleeves (membership frozen before combo metrics)
| Slot | hypothesis_id | clock | priority |
|---|---|---|---|
| A | HYP-FX3-H1-NY-ASIA-RAID-RECLAIM-ACCEPT-CONT-001 | NY raid of Asia range | 1 |
| B | HYP-FX3-H1-FAILED-2D-RANGE-BREAK-REVERSE-ACCEPT-001 | fail-back of 2D break | 2 |

## Optional single (outside W1–W8; not a book sleeve)
- HYP-FX3-H1-H4-SWING-FIRST-RETEST-ACCEPT-CONT-001

## Caps / overlap (a priori; fail closed)
- Weekly PnL corr ≤ 0.35
- Same-symbol H1-bar overlap frac ≤ 0.05
- Heat: max 1 trade per (symbol, H1 bar); priority A > B
- Book screen: tpw ∈ [2.0, 5.0]; PF@$12 ≥ 1.30; x1.5 ≥ 1.25; N ≥ 80
- Sleeve individual cadence starve is EXPECTED; book pooled is the claim

## Forbidden
FVG densify; W1–W8 knob densify; R10–R31 densify; exit/MaxKZ densify;
Phase-0 ceremony; reopen contaminated Phase-0 attestation.

## Model 0
WITHHELD unless book or optional single is PROBE_SURVIVOR.
Book pooling is diagnostic offline — not EA challenger until coded.
