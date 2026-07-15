# Design — USD majority lag-follow + H4 TS-mom band

Date: 2026-07-15
Lane: single; offline-first; nested critic `cursor-grok-4.5-high-fast`
Parent: AONIA unlock + thin3 ALL_KILL; do not densify AONIA/CORRA/thin3

## 1 `HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001`
Thesis: when ≥2/3 FX3 print strong same-USD H4 body (≥0.45 ATR) and the
remaining lag is quiet (<0.20 ATR same-sign), delayed USD repricing hits the
lag pair — continuation WITH USD majority (not residual fade).
Frozen: enter next H4 open on lag; SL=1.25 ATR; RR=2.0; hold≤4 H4;
MaxOpen=1; MaxPerDay=1; +$12 a priori.

## 2 `HYP-FX3-H4-TSMOM-BAND-CONT-001`
Thesis: soft 5-bar H4 TS-momentum in ATR units stays alive inside [1.0, 2.5]
(not dead chop, not climax) with body≥0.35 ATR → continue with sign(S).
Frozen: SL=1.20 ATR; RR=2.5; hold≤10 H4; MaxPerDay=1/symbol; FX3 book; +$12.

## Model 0 policy
Only if offline PROBE_SURVIVOR. Else withhold. No densify of killed cousins.
