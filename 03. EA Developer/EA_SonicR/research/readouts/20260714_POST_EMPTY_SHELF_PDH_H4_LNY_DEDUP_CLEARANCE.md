# De-dup clearance — Post-empty-shelf trio (PDH-retest / H4-struct / LNY dual-window)

Date: 2026-07-14 ~20:05 ICT  
Verdict: `INTAKE_CLEARED / THREE_INDEPENDENT`  
Authority: Owner iterate after `HARD_EMPTY_SHELF`; GPT waived; free MT

## Candidates

| ID | Mechanism | Cleared vs |
|---|---|---|
| `HYP-PDH-RETEST-M15-001` | D1 PDH/PDL **break then retest+reject** continuation | Parked `HYP-PDH-BREAK` (immediate break entry); LiqSweep/PDLevel **fade**; LondonORB |
| `HYP-H4-STRUCT-BREAK-M15-001` | H4 swing BOS + M15 level retest | Killed `HYP-H1-BOS-M15-PB` (H1+EMA PB); H1SwingFailure fade; ITSM/SB/ORB |
| `HYP-LNY-DUALWIN-M15-001` (executed) | London ATR bias + dual PB windows; MaxPerDay=2 | Classic LondonNY sole-book; **not** S530 day-mine |
| `HYP-LNY-DUAL-WINDOW-001` | **INTAKE twin** of DualWin — **no Model 0** | See `readouts/20260714_LNY_DUAL_WINDOW_VS_DUALWIN_INTAKE_KILL.md` |

## Shared bans honored

No MaxKZ densify; no RR retune; no USBILL rescue; no VWAP/ATF/HBOS reopen;
no S530 day-mine; no Gotobi/LondonNY as sole GOAL book without cadence path.

## Probe note → Model 0 results (executed)

| ID | Run | Verdict |
|---|---|---|
| PDH-retest | `20260714_200819` | **KILL** PF 0.83 |
| H4-struct | `20260714_200944` | **KILL** PF 0.91 |
| LNY DualWin | `20260714_201038` | **KILL** N+cadence (PF 1.42 thick but ~0.26/wk) |

Closeout: `readouts/20260714_EMPTY_SHELF_PDH_H4_LNY_REBUILD_CLOSEOUT.md`.
Hard screen held. No research HIT → no survivor to promote.
