# Semantic Contract — TB_Smart_Money_Concept_2026

Campaign: `FIV2-20260808-ATOMIC`  
Source fork SHA256: `D3A8002773EB8B186A8D9A13333E9FDEEBAA83E499A2CF08D619A99EAEBFA217`  
Path: `indicators/TB_Smart_Money_Concept_2026.mq5`  
Policy: **REUSE_AFTER_REAUDIT**  
License: MPL-2.0 (TBalgo Pine 2026.2.0; MQL5 port) — attribution retained.  
Buffer contract version: **3.0** (buffer 43).

## 1. Original formula

Closed-bar SMC map: swings → BOS/MSS → origin cells → FVG/voids + CE → sweeps → displacement → bias; v3 adds unconsumed liquidity pool buffers 44–47.

## 2. Update order

1. ATR(14)  
2. Swing confirmation  
3. Structure breaks BOS/MSS  
4. Sweep detection  
5. Displacement body/ATR  
6. Cells/voids lifecycle  
7. Bias + ready mask  
8. Liquidity pool nearest unconsumed levels  

## 3. Warm-up

- Requires swing history + ATR; `ClosedBarValid` (26) == 1.

## 4. Buffer ABI (EA-critical)

| Idx | Meaning |
|---:|---|
| 2 | Bias −1/0/+1 **state** |
| 3–6 | BOS/MSS up/down **event flags** |
| 7–8 | Sweep high/low **event flags** |
| 11–12 | Displacement bull/bear **event flags** |
| 13–14 | Confirmed swing high/low levels |
| 26 | ClosedBarValid |
| 27 | Structure event code ±1 BOS / ±2 MSS |
| 28 | ATR |
| 36 | Displacement ratio |
| 39 | Ready mask |
| 43 | Contract version (=3) |
| 44–47 | Liquidity pool levels/flags |

## 5. State vs event

- **State:** bias, swings, ranges, voids, liquidity levels, ATR.  
- **Events:** BOS/MSS/sweep/displacement flags; structure code 27.

## 6. Non-repaint

- Forming bar carries **no** trade event.  
- EA: buffer 26==1, shift>=1, buffer 43>=2.0 (prefer 3.0).

## 7. EA read rules

- Event clock / structure only; raw events ≠ entries.  
- ENGINE_R: sweep/reclaim at boundary.  
- ENGINE_T: BOS/MSS same dir + protected swing.  
- ENGINE_B: displacement / structure break.  
- Do not revive RSF HYP010 liquidity-pool objective without new mechanism ID and Stage-0.
