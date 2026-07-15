# Readout — HYP-M15-NY-IB-DRIVE-BREAK-001

Date: 2026-07-14  
State: `PARKED_AT_MODEL_0`  
Authority: Owner Wave5 last slot; GPT waived

## Verify (disk)

| Artifact | Status |
|---|---|
| Prereg | `preregs/20260714_H_M15_NY_IB_DRIVE_BREAK_001_PREREG.md` frozen |
| EA | `EA_M15NYIBDriveBreak/EA_M15NYIBDriveBreak.mq5` magic 880997 |
| Receipt SHA | `49AD42FA3EF65EC05E12E5D81D96137433E7E6BAA30E34E27803CC5CDA5CF458` |
| Lane | `terminal64=0`; no lock; no Owner Real kill |

## Run

| Item | Value |
|---|---|
| `run_id` | **`20260714_225915`** |
| Binding | USDJPY M15 2021–2025 deposit 100000 overrides empty Model 0 |
| Report SHA | `BC60B154F36065171F48EC58334F799C439674A9CA70859F4BBC0705DB8AB12A` |
| Closeout | empty required_sidecars throw after report; metrics via analyze |

## Metrics vs GOAL / Wave5 gates

| Metric | Value |
|---|---:|
| Trades | 983 |
| PF | **1.018** |
| Net | +$1713.70 |
| tpw (elapsed 260.714) | **~3.77** |
| Expectancy | +$1.74 |
| Max DD | 5.92% |

| Gate | Result |
|---|---|
| KILL (PF&lt;1 / tpw∉[1,6] / N&lt;80) | **PASS** (survive) |
| Research HIT (PF&gt;1.30 ∧ tpw∈[2,5]) | **FAIL** (cadence OK; PF thin) |
| PARK | **YES** |
| GOAL | unmet |
| +$12 cost stress | Skipped (PF&lt;1.20) |

## Banned (honored)

Do **not** densify NY IB hours [13,14)/[14,17), MinIBATR, RR, or Tue/Thu cut
from this readout. Not London-IB densify; not NYOpenDrive rescue.

## Wave5 closeout

| Slot | Run | Verdict |
|---|---|---|
| ATR%ile Break | `224917` | PARK PF 1.10 |
| EURUSD Asia-box | `225610` | KILL PF 0.90 |
| NY-IB Drive | `225915` | **PARK** PF 1.02 |

**Wave5 family budget exhausted.** Best shelf unchanged: RR2 `194548`.

## Next after Wave5 (legal backlog — not executed this turn)

See `readouts/20260714_SB_NEAR_GOAL_OPTION_BACKLOG_V1.md` § Next after Wave5.
