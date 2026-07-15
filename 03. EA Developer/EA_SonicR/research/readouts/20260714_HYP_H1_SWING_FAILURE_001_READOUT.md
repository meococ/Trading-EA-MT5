# Readout — HYP-H1-SWING-FAILURE-001

Date: 2026-07-14  
State: `KILLED_AT_MODEL_0`  
Run: `20260714_031824`  
EA: `EA_H1SwingFailure`  
Cost: tester `current` / MetaQuotes-Demo — **not** Real QFSI; missing≠0

## Metrics (USDJPY H1 2021.01.01–2025.12.31, Deposit=10000)

| Metric | Value |
|---|---|
| Profit factor | **0.97** |
| Trades | **798** |
| Trades/week (elapsed) | **~3.06** |
| Net | **−$744.63** |
| Expectancy | −0.93 |
| Equity DD max | **~17.64%** |
| Win rate | 40.23% |

Report SHA256: `28AD81FBA3826AB38C3C8591D7D33DE281FBB2B75DCD8E9072858E750011B433`

## Gates

| Gate | Result |
|---|---|
| Kill PF&lt;1.00 | **FAIL** (0.97) |
| Kill tpw∉[1.0,6.0] | PASS (~3.06) |
| Kill N&lt;80 | PASS |
| Research bar | N/A — killed |

## Non-repaint

Closed H1 `bar[1]`; pivot confirmed at shift≥1+L with L=2 frozen.

## Ceremony note

Alpha closeout `includes_sha256` mismatch after report ready; artifacts kept
under `02. AlphaFactory/runs/EA_H1SwingFailure/20260714_031824/`.

## Verdict

**KILLED.** Cadence OK; edge fails. **Do not** mine PivotL, day/hour, or retarget
M15 Viper/FailedORB/LiqSweep.

## Independence

`readouts/20260714_H1_SWING_FAILURE_VS_ORB_LIQSWEEP_DEDUP_CLEARANCE.md`
