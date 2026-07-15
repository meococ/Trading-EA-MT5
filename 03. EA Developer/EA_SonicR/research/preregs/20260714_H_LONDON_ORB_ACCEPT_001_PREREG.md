# Prereg — HYP-LONDON-ORB-ACCEPT-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuke ~19:29 — rebuild without QFSI stall

## Identity

- Hypothesis ID: `HYP-LONDON-ORB-ACCEPT-001`
- EA: `EA_M15LondonORBAccept`
- Path: `03. EA Developer/EA_M15LondonORBAccept/EA_M15LondonORBAccept.mq5`
- Parent: structural rebuild of parked `HYP-LONDON-ORB-M15-001` (PF~1.17) — **not** FailedORB fade; **not** SB densify

## Thesis

London ORB `[9,10)` same as parent. Entry requires **two consecutive closed closes** outside ORB with buffer, both on the same side of ORB mid (acceptance), plus D1 EMA50. Stricter than raw pierce — expected lower cadence, higher PF if edge is acceptance not noise.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| ORB | `[9,10)`; trade `[10,16)` |
| Accept | bar[1]+bar[2] close outside; mid not reclaimed |
| Days | Mon–Thu; flat 21 |
| Risk | 0.50%; 1/day; TP 1.5R |
| Magic | 880960 |

Banned: ORB minute/day mine; flipping to fade; stacking with MaxKZ2 densify.

## Kill / Park / HIT

Same Model 0 research bar as parent LondonORB prereg.

## Cost honesty

Tester `current` only; not Real QFSI.
