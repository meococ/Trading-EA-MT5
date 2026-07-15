# Design — Round 14 gap-cont / tvol-flow / NAS thick-mom

Date: 2026-07-15
Hard constraint: **FORBIDDEN** OHLC fade / MR / session-edge densify;
also no R13 NFP/CUSUM/XAU densify.

## 1 `HYP-FX3-H1-WEEKEND-GAP-CONT-001`
Mon H1 hour≤2; |open−Fri close|≥0.4×D1 ATR → CONTINUE gap;
SL=1.5 RR=2.0 hold≤16; first FX3.

## 2 `HYP-FX3-H1-TICKVOL-IMBALANCE-CONT-001`
Look=6; |signed_tv|/sum≥0.65 + body≥0.35 ATR same side;
CONTINUE; SL=1.4 RR=1.8 hold≤10.

## 3 `HYP-NAS100-H4-D1-TSMOM-THICK-001`
D1 |ROC20|≥2.0×ATR → H4 thick; SL=2.0 RR=2.5 hold≤36.
