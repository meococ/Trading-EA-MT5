# Universe freeze — HARD PIVOT W5 asia-sweep + leadlag peer

Date: 2026-07-15
Status: `APRIORI_FREEZE__PRE_METRICS`
Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`

## Universe (a priori — NOT post-cadence expansion)
- Symbols: EURUSD, GBPUSD, USDJPY
- Leadlag edges frozen: EURUSD↔GBPUSD same-side; EUR/GBP→USDJPY opposite

## Children
1. HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001
2. HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001

## thick∩cadence break mechanism
- Asia: daily location clock + mid reclaim (not open FVG window)
- Leadlag: peer book cadence from frozen multi-symbol edges

## Forbidden
FVG densify; W1–W4 densify; R10–R31 densify; exit/MaxKZ/ORB/IB/FRED.
