# Readout — HYP-EMA-STRETCH-FADE-M15-001

Date: 2026-07-14 ~01:52 ICT  
State: `KILLED_AT_MODEL_0`  
Agent: Grok 4.5 High Fast (Owner MT free-run continuation)

## Identity

- Hypothesis: `HYP-EMA-STRETCH-FADE-M15-001`
- EA: `EA_M15EMAStretchFade`
- Run: `20260714_015218` (Model 0, USDJPY M15, 2021-01-01–2025-12-31, Deposit 10000)
- Role: control
- Compile: SUCCESS (0 errors)
- Non-repaint: closed-bar[1] EMA/ATR shift≥1; PASS by audit scan
- Cost: `UNVERIFIED_TESTER_DEFAULT` (tester `current`); missing ≠ 0; not Real QFSI

## Metrics

| Metric | Value |
|---|---:|
| Trades | 1980 |
| PF | **0.84** |
| Net | −$6587.93 |
| Expectancy | −$3.33 |
| Win rate | 32.1% |
| Max equity DD | ~68.6% |
| Elapsed tpw | **~7.59**/wk |

Report SHA256 `1E26BF003D4A3ECAADD1D0282B276A2B58AAEE99DA52B2D8BF8D93B4383C94BB`.  
Alpha closeout `includes_sha256` mismatch after report ready; artifacts kept.

## Gate vs prereg

- N≥80: PASS  
- tpw ∈ [1.0, 6.0]: **FAIL** (~7.59)  
- PF ≥ 1.00: **FAIL** → **KILL** (PF primary; cadence also out)

## Independence note

Pure EMA stretch MR; not ADR exhaust / ChopMeanRevert / ORB shelf. Edge fails across all years 2021–2025. Do **not** mine stretch threshold / EMA / hour / day.

## Verdict

`KILLED_AT_MODEL_0`. Do not rescue.
