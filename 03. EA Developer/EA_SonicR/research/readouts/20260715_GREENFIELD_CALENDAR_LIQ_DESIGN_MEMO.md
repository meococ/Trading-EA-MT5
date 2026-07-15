# Design memo — Greenfield calendar/liquidity FX3

Date: 2026-07-15
Parent: anti-carry vol-spike ALL_KILL; G10 alt-source parallel.

## Design 1 — Turn-of-month liquidity continuation
`HYP-FX3-H4-TURNMONTH-LIQ-BOOK-001`
Window = last 2 weekdays of month + first 2 of next.
Direction = sign of prior 5 D1 closes; enter H4≥08 UTC;
SL 1.5×ATR14_H4; RR=2.0; hold≤6; book≤2.

## Design 2 — Weekend gap fade
`HYP-FX3-H1-WEEKEND-GAP-FADE-001`
Monday first H1; |gap|≥0.35×ATR14_D1 vs Friday close;
fade gap; SL buffer 0.15×ATR; RR=1.5; hold≤12 H1.

## ≠ kill shelf
≠ carry Mon→Thu/flush/anticarry; ≠ D1 volregime/swing; ≠ RR2 exit/entry;
≠ FRED displace; ≠ LNY/XS; ≠ NR7/ORB/IB densify; ≠ 6J/USBILL.
