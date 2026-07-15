# HYP-HIS-DIAG-GATECOUNT-M15-EUR-001 — Model 0 DIAG readout

Date: 2026-07-15  
Role: **DIAG only** — not promotion / not GOAL / cost UNVERIFIED

## Run

| Field | Value |
|---|---|
| Run dir | `02. AlphaFactory/runs/EA_HybridICT_Sonic/20260715_170448` |
| Symbol / TF | EURUSD M15 |
| Window | 2020.01.01 → 2026.07.15 |
| Model | 0 |
| Decision surface | `InpUseDragonSlFloor=false` + gate counters |
| Receipt SHA | `C51F8810DD0016A2A4129A05686CE733368008979BC0234089C3CAB3EDFA6CEA` |

## Results (tester)

| Metric | Value |
|---|---|
| Trades | **3** |
| Net | $780.75 |
| PF | 4.85 (toy sample — **not** claimable) |
| Max DD | 0.20% |
| Win rate | 66.7% |

Parent empty hyp had **0** trades with Dragon±40 floor ON.

## OnDeinit DIAG counters

```
eval=88076 atr=84248 bias=84248 levelObj=84248
near=48527 wave=12011 dragon=5536 pvsra=1508
slFail=1505 slOk=3 pendingOk=3 pendingFail=0
```

Interpretation:
1. SL floor OFF unblocked PlacePending (**DIAG success**).
2. Even with level-only SL, **1505/1508** still fail `MaxSl 2.5×ATR` — ICT level distance often > cap.
3. Cadence remains tiny (3 fills / ~6.5y) — not a book sleeve.

## Verdict

`DIAG_PASS_PLUMBING` — antagonism confirmed fixed enough to place trades.  
**Not** `research pass` / not GOAL. Do not densify Dragon period or hour veto from this.

## Forbidden next

- Claim PF≥1.65 / promote / live
- Rescue-tune parent hyp from these 3 Friday trades
- Optimize Dragon 30–38 from this sample
