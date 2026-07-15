# Next M15 Model 0 Coordinator — 2026-07-14

Status: **KILL_AT_MODEL0** (GOAL unmet)

## Selection

| Candidate | Decision |
|---|---|
| Chop / VolExp / SB Friday mine | Banned (prior kills / park) |
| GoldJPY lead | FAIL_CLOSED de-dup (`S671` no-day-filter dead) |
| USBILL | Deferred parallel lane (cadence ~1/wk; cost gap) |
| **`HYP-INSIDEBAR-M15-001` / `EA_M15InsideBreak`** | **Executed** — independent S226/S232 seed |

## Result

| Field | Value |
|---|---|
| run_id | `20260714_001629` |
| PF | **0.96** |
| Trades | **308** |
| tpw elapsed | **~1.18** |
| Net | **−$329.99** |

Kill vs frozen prereg: PF < 1.00 **and** cadence < 1.5. Tester cost only.

## Explicit non-claims

- GOAL **not** met.
- Tester PF ≠ verified after-cost PF.
- Missing cost ≠ zero.
- Do not mine IB/KZ/day/H1 from this kill.

## Paths

- Prereg: `preregs/20260714_H_INSIDEBAR_M15_001_PREREG.md`
- Receipt: `preflight/20260714_NEXT_M15_MODEL0_CAMPAIGN_RECEIPT.json`
- Readout: `readouts/20260714_HYP_INSIDEBAR_M15_001_READOUT.md`
- Run: `02. AlphaFactory/runs/EA_M15InsideBreak/20260714_001629/`

## Next agent-executable

Open another **independent** price-M15 ID only if shelf/de-dup clears a non-killed
family; else Owner Real QFSI for USBILL promotion path. Do not ChatGPT.
