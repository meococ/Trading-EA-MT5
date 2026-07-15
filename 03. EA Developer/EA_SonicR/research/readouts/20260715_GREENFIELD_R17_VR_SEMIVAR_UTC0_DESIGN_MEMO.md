# Design — Round 17 VR / semivar / UTC0

Date: 2026-07-15
## 1 `HYP-ETHUSD-H4-VARIANCE-RATIO-MOM-CONT-001`
VR(q=2, lb=48)>1.2 → CONT sign(sum last 8 logret);
SL=1.5 RR=2.0 hold≤10.

## 2 `HYP-NZDUSD-H1-SIGNED-SEMIVAR-CONT-001`
24-bar signed semi-var share≥0.62 → CONT; SL=1.4 RR=2.0 hold≤12.

## 3 `HYP-ETHUSD-H1-UTC0-OPEN-DRIVE-CONT-001`
UTC hour=0 |body|≥0.8×ATR → CONT; SL=1.5 RR=2.0 hold≤8.
