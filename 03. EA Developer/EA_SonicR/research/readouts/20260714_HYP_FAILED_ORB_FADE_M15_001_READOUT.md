# Readout — HYP-FAILED-ORB-FADE-M15-001

Date: 2026-07-14 ~01:50 ICT  
State: `KILLED_AT_MODEL_0`  
Agent: Grok 4.5 High Fast (Owner MT free-run continuation)

## Identity

- Hypothesis: `HYP-FAILED-ORB-FADE-M15-001`
- EA: `EA_M15FailedORBFade`
- Run: `20260714_014952` (Model 0, USDJPY M15, 2021-01-01–2025-12-31, Deposit 10000)
- Role: control
- Compile: SUCCESS (0 errors)
- Non-repaint: closed-bar[1] only; OR built from closed bars; PASS by audit scan
- Cost: `UNVERIFIED_TESTER_DEFAULT` (tester `current`); missing ≠ 0; not Real QFSI

## Metrics

| Metric | Value |
|---|---:|
| Trades | 522 |
| PF | **0.83** |
| Net | −$2278.67 |
| Expectancy | −$4.37 |
| Win rate | 37.7% |
| Max equity DD | ~29.2% |
| Elapsed tpw | **~2.00**/wk |

Report SHA256 `EE58B59F1B00BCF97682B9B45A7462FFAEC64CD4EF0504CE7662F3FFC79AC914`.  
Alpha closeout threw `includes_sha256` mismatch after report ready (same flake as prior tonight); artifacts kept.

## Gate vs prereg

- N≥80: PASS  
- tpw ∈ [1.0, 6.0]: PASS (~2.00)  
- PF ≥ 1.00: **FAIL** → **KILL**

## Independence note

Opposite of parked LondonORB break-continuation; same a-priori OR `[9,10)`. Cadence OK; edge fails. Do **not** retune OR hours/days or flip back to breakout.

## Verdict

`KILLED_AT_MODEL_0`. Do not rescue.
