# Design — Round 16 HL-break / CPI / US30-lead

Date: 2026-07-15
Hard constraint: NON-FADE; outside R10–R15 densify; no ROC-k thick densify.
Broker adapt: DE40 missing → US30.

## 1 `HYP-US30-H4-D1-HL-BREAK-CONT-001`
H4 close beyond prior D1 H/L by ≥0.15×D1 ATR → CONT;
SL=2.0 RR=2.5 hold≤20; 1/day.

## 2 `HYP-USDJPY-H1-CPI-IMPULSE-CONT-001`
Frozen CPI calendar; hour∈(12, 13) UTC; |body|≥1.0×ATR;
CONTINUE; SL=1.5 RR=2.0 hold≤8; 1/event.

## 3 `HYP-EURJPY-H1-US30-LEAD-CONT-001`
US30 |body|≥0.6×ATR leads EURJPY same-sign |body|≥0.25×ATR;
lag∈(0, 1); SL=1.4 RR=2.0 hold≤10; 1/day.
