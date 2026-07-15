# Readout — HYP-D1-TREND-H1-PB-001

Date: 2026-07-14 ~23:12 ICT  
Authority: Owner post-Wave5 rebuild path **B**  
GPT: waived

## Verdict

**`KILLED_AT_MODEL_0`** — PF **0.967** < 1.00 hard kill.

Not GOAL. Do **not** densify D1/H1 EMA periods, PB lookback, RR, body ATR,
or Mon/day/hour from this readout.

## Identity

| Item | Value |
|---|---|
| hypothesis_id | `HYP-D1-TREND-H1-PB-001` |
| EA | `EA_D1TrendH1PB` |
| run_id | `20260714_231055` |
| receipt SHA | `0369B1809CEA8C0CB721DAEFDB5A2AB757E1AF852F76C04D4ABCBB65C2EDA073` |
| source SHA | `268946B176489B8C7B5A065DCCE87D3ECFA07C1A4981DA96A62F012361B594B5` |
| symbol/TF/window | USDJPY H1 2021.01.01–2025.12.31 |
| model / deposit | 0 / 100000 |
| cost grade | `UNVERIFIED_TESTER_DEFAULT` |

## Metrics (tester `current`)

| Metric | Value |
|---|---|
| Trades | 959 |
| PF | 0.967 |
| Net | −$4021.73 |
| Expectancy | −$4.19/trade |
| Max DD | 10.32% |
| tpw (elapsed calendar weeks) | ~3.68 |
| Win rate | 47.0% |

Cadence was in-band (~3.7/wk) but edge is negative after tester cost.

## Gate vs GOAL

| Gate | Result |
|---|---|
| Research PF > 1.30 | FAIL (0.97) |
| tpw ∈ [2, 5] | PASS (~3.68) |
| Hard kill PF < 1 | **TRIPPED** |
| Cost stress +$12 x1.5/x2 | Skipped (not research HIT) |
| GOAL | **Unmet** |

## Independence note

Distinct from parked `HYP-D1-TREND-H4-PB-001` (H4/RR3). Same D1-bias object
transferred to H1 with RR=2.5 did **not** produce positive expectancy.
Family budget for this H1 sibling: **1/1 spent**.

## Banned densify

EMA50/21, PB lookback 4, MinBodyATR 0.30, RR 2.5, MaxPerDay 2, Mon–Thu —
frozen failures; new ideas only via independent thesis (e.g. backlog **A**
AUDJPY-lead if still legal).

## Artifacts

- Prereg: `preregs/20260714_H_D1_TREND_H1_PB_001_PREREG.md`
- De-dup: `readouts/20260714_D1_TREND_H1_PB_DEDUP_CLEARANCE.md`
- Run: `02. AlphaFactory/runs/EA_D1TrendH1PB/20260714_231055/`
- Analysis: `.../analysis/enhanced_summary.json`
