# Design — Book-dispersion fade + Path-ER cont (Round 4)

Date: 2026-07-15
Parent: Round1–3 ALL_KILL (thick / quality / middle-death+thick).
Nested critic `cursor-grok-4.5-high-fast`.

## Why these break dichotomy (a priori)
- R1 follow co-move / R3 solo-cont both die; Disp **fades** extreme vs book median.
- R2 rare auction starves; Path-ER uses frequent path-shape state, not spring/PB.
- R3 accept was soft handshake spam; ER skips low path-efficiency thrash.

## 1 `HYP-FX3-H4-BOOKDISP-EXTREME-FADE-001`
r=(C-O)/ATR; ext=argmax|r|; |r_ext|≥0.55; |r_ext−med|≥0.40; max|r|−min|r|≥0.50;
skip if |r_ext|≥0.70 climax; fade against ext next H4. SL1.10 RR2 hold≤4;
MaxOpen1 MaxPerDay1 Mon–Thu.

## 2 `HYP-FX3-H4-PATH-ER-CONT-001`
ER8≥0.62; body≥0.40 ATR; close outer 30%; WITH next H4. SL1.20 RR2.5 hold≤6;
MaxPerDay1/sym book≤2; EUR+GBP same-USD → keep higher ER only.

## Model 0
Only PROBE_SURVIVOR. No densify R1–R3 knobs.
