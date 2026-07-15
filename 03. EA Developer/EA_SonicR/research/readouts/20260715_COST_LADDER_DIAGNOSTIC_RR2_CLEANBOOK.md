# Cost-ladder diagnostic — RR2 `194548` + clean PRIMARY + FVG cite

Generated: 2026-07-15T10:18:43.057725Z
Receipt SHA256: `6479B6A10B2402E972EF3B46112F3EF14BBC884453AF1A36BC9023A1B7E1BECA`

## Honesty

- DIAGNOSTIC ≠ GOAL / confirmed / freeze-eligible.
- RESEARCH-GRADE = a priori +$12 (binding kill/survive screen) and ×1.5 stress.
- Real/QFSI partial USDJPY trade-cost P50=`2.6168` P90=`2.9251` (verified from QFSI table + prior W7CONT stress JSON).
- Cost freeze still GAP (live deals≈11; quote days≪90; slip MISSING≠0).

## RR2 shelf `194548`

| Ladder | Grade | $/trade | PF | tpw | net | goal-shape? | Note |
|---|---|---:|---:|---:|---:|:---:|---|
| `tester_only` | **DIAGNOSTIC** | 0.0000 | 1.3783 | 2.0099 | 9828.35 | Y | raw tester report PnL; NOT full cost |
| `real_qfsi_partial_p50` | **DIAGNOSTIC** | 2.6168 | 1.316 | 2.0099 | 8457.17 | Y | FivePercentOnline-Real PARTIAL; USDJPY unit_p50@$0.5lot; sli |
| `real_qfsi_partial_p90` | **DIAGNOSTIC** | 2.9251 | 1.3089 | 2.0099 | 8295.57 | Y | same provenance as P50; P90 spread+EURUSD commission clue; N |
| `apriori_8` | **DIAGNOSTIC** | 8.0000 | 1.1986 | 2.0099 | 5636.35 | N | a priori alternate haircut; NOT the frozen research screen |
| `apriori_12` | **RESEARCH-GRADE** | 12.0000 | 1.1197 | 2.0099 | 3540.35 | N | frozen a priori +$12 research screen (binding) |
| `apriori_12_x1_5` | **RESEARCH-GRADE** | 18.0000 | 1.0126 | 2.0099 | 396.35 | N | a priori +$12 ×1.5 stress of research screen |

## Clean book PRIMARY (RR2+Spark, heat-pooled)

Dropped heat: 4. Corr(raw)=0.0414 overlap=0.0123.

| Ladder | Grade | $/trade | PF | tpw | net | goal-shape? | Note |
|---|---|---:|---:|---:|---:|:---:|---|
| `tester_only` | **DIAGNOSTIC** | 0.0000 | 1.4088 | 3.2411 | 20223.08 | Y | raw tester report PnL; NOT full cost |
| `real_qfsi_partial_p50` | **DIAGNOSTIC** | 2.6168 | 1.3558 | 3.2411 | 18011.92 | Y | FivePercentOnline-Real PARTIAL; USDJPY unit_p50@$0.5lot; sli |
| `real_qfsi_partial_p90` | **DIAGNOSTIC** | 2.9251 | 1.3497 | 3.2411 | 17751.33 | Y | same provenance as P50; P90 spread+EURUSD commission clue; N |
| `apriori_8` | **DIAGNOSTIC** | 8.0000 | 1.254 | 3.2411 | 13463.08 | N | a priori alternate haircut; NOT the frozen research screen |
| `apriori_12` | **RESEARCH-GRADE** | 12.0000 | 1.1841 | 3.2411 | 10083.08 | N | frozen a priori +$12 research screen (binding) |
| `apriori_12_x1_5` | **RESEARCH-GRADE** | 18.0000 | 1.0873 | 3.2411 | 5013.08 | N | a priori +$12 ×1.5 stress of research screen |

## FVG near-miss (cite only)

- `HYP-SB-FVG-RETEST-ACCEPT-DELAY-001` N=299 PF=1.2747 tpw=1.1468 PF@$12=1.2054 x1.5=1.1724 → KILLED_AT_OFFLINE_PROBE
- Prior offline probe under a priori +$12 — RESEARCH-GRADE screen numbers only; densify FORBIDDEN; Real/QFSI ladder NOT reconstructable (no trade list).
- Densify FORBIDDEN.

## Decision

$12 remains the binding RESEARCH-GRADE screen. DIAGNOSTIC Real/QFSI partials (~$2.62 P50) show RR2/clean-book PF much higher than under $12, so $12 is punitive vs thin Real sample — BUT freeze still GAP (11 deals, ≪90 quote days, slip MISSING). Do NOT relax GOAL/confirmed from DIAGNOSTIC. Keep +$12 as kill/survive screen until research-grade cost freeze exists.

JSON: `preflight/20260715_COST_LADDER_DIAGNOSTIC_RR2_CLEANBOOK.json`

