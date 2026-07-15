# Price-M15 Dual-Filter Shelf Scan — 2026-07-14 (self-research)

Status: `EMPTY / FAIL_CLOSED`  
Authority: `hot.md`, `STRATEGY_LOG.md`, registry kill/park rows, Owner MT autonomy.

## Question

Is there a legal new independent M15 family with structural path to ≥2
trades/elapsed calendar week that is not on the kill/park list?

## De-dup scan (not exhaustive of entire STRATEGY_LOG; covers dual-filter near-misses)

| Seed / family | Cadence path | Edge note | Verdict tonight |
|---|---|---|---|
| SB weekend-flat A1 | ~1.99/wk | PF~1.33 Demo | **parked** — not a new family |
| Spark Asian S111 transfer | ~1.25/wk | PF 1.31 Model0 | **parked** — cadence fail |
| InsideBar M15 | ~1.18/wk | PF 0.96 | **killed** |
| VolExp / VolCluster S639 | dense OK | PF 1.01 Model0 | **killed** |
| ChopRegime / ChopTrend | dense OK | PF 1.08 Model0 | **killed / FAIL_CLOSED** |
| GoldJPY Lead | dense OK | PF 0.97 | **killed** |
| TickVolImpulse | dense OK | PF 1.00 | **killed** |
| HourOpenBreak | dense OK | prior kill | **killed** |
| USBILL basket | ~1/wk | Model0 kill | **killed** |
| ITSM S509 denser | ~3.27/wk Model0 | PF 1.16 `20260714_003635` | **parked** — do not T10-mine |
| Gotobi / LondonNY | sparse quality | shelf fail / cadence | **do not reopen as GOAL book** |
| Carry/COT/bond/OIS/equity-bond | — | offline kills | **closed** |
| USD-factor M15 cross-section | — | cost-data blocked | **blocked** |

## Verdict

**No legal agent-executable new M15 Model 0 candidate** without Owner-supplied
Real/QFSI cost or a genuinely new exogenous/source thesis outside this shelf.

Next autonomous contract work taken: Phase 0 portfolio identity subset for
`HYP-PORTFOLIO-COMPOSE-001` (see companion readout). No compile/backtest from
this scan.
