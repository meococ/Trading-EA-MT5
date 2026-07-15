# A priori freeze — SB/RR2 quality-thickness (W27 child)

Child: `HYP-SB-RR2-QUALITY-THICK-DISP-001`  
Parent: `HYP-SB-MAXKZ2-RR2-FRICTION-001` / run `20260714_194548`

## Problem
Clean/RR2 shelf PF@$12≈1.184 with tpw in [2,5]. Need thicker $/trade
without FVG densify or exit densify. UUP/DTWEX W27 exo ALL_KILL.

## Contract (frozen before metrics)
Keep parent RR2 trade iff entry-signal M15 (bar before fill) satisfies:
- body/ATR ≥ `0.55`
- body/range ≥ `0.75`
- close in trade-direction extreme ≥ `0.67` of range

Exits = parent (unchanged). FVG params = parent (unchanged). MaxKZ = parent.

## Banned
FVG size/wait mine · BE/trail/TP/RR exit densify · MaxKZ densify ·
commodity ToT · credit-MOVE · UUP/DTWEX z mine · W1–W26 OHLC densify.
