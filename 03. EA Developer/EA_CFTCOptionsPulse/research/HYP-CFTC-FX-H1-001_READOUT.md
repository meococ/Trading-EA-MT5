# HYP-CFTC-FX-H1-001 — Offline Probe Readout

Verdict: **`KILL_AT_OFFLINE_PROBE`**  
Workspace goal: **`UNMET`**  
EA/source/compile/Model-0 authority: **none**

## What was tested

The frozen candidate used weekly change in CFTC TFF leveraged-money
options-equivalent positioning, calculated as `Combined - FutOnly`, for
EURUSD/GBPUSD/USDJPY. It traded the following Monday from 07:00 to 16:00 UTC
with a closed-H1 ATR stop. A matched control used futures-only leveraged-money
net change on the same eligible events.

The first launch returned zero bars because the MT5 bridge was not ready. Its
receipt proves zero outcome access. One operational retry added only the
standard MT5 timeout, `symbol_select`, and bounded history-read retry; all
economic rules and gates remained frozen.

## Evidence identity

- Probe artifact:
  `research/evidence/20260716_084740_HYP_CFTC_FX_H1_001_PROBE.json`
  — SHA256 `4AEFC0E34358A4E23CC2CCBB6C337C58F85A26601F491780BF5FF7CE56156CED`.
- Trade ledger:
  `research/evidence/20260716_084740_HYP_CFTC_FX_H1_001_TRADES.csv`
  — SHA256 `3BD5C3CE943CCC87B8DE24194F6355765049C0391320C7C9C2FB249822F2B643`.
- Official-source manifest SHA256:
  `F281B9378A9D7774B2B2246EDC4D9A12ECD43698C5A9BDF919B3F8189EB7B7FD`.
- Runtime: FivePercent terminal build 6006, `portable=true`, terminal/data path
  on `D:`, exact symbols EURUSD/GBPUSD/USDJPY.
- Loaded H1 coverage ends `2023-12-29`; 2024-2025 archives and price outcomes
  were not loaded.

## Frozen split results

| Metric | Train 2018-2021 | Internal validation 2022-2023 |
|---|---:|---:|
| Candidate trades | 410 | 299 |
| Trades / elapsed week | 1.964 | 2.867 |
| Gross PF (derived from frozen CSV) | 0.979 | 0.871 |
| Gross net R | -4.321R | -20.927R |
| PF x1 proxy | 0.812 | 0.766 |
| PF x1.5 | 0.742 | 0.720 |
| PF x2 | 0.678 | 0.676 |
| Net R x1 | -43.594R | -41.031R |
| Max DD x1 at 0.25% risk | 16.783% | 11.159% |
| Positive years | 1/4 | 0/2 |
| Matched-control PF x1 | 0.796 | 0.795 |
| Matched-control net R x1 | -48.837R | -35.279R |

Only 2 of 22 split gates passed: validation cadence and validation minimum
trades per symbol. The candidate was loss-making before costs in both splits,
remained far below every PF/cost/DD/stability gate, and failed to beat the
matched control by the frozen margin.

## Data-contract failure

The exact market-name guard rejected 532 historical GBPUSD rows even though
their CFTC contract code matched. This removed GBPUSD from train and itself
fails the frozen source-integrity gate. There were also 8 train and 6 validation
price-event skips, exceeding the `<=2` contract.

This is not a reason to repair and rerun the same hypothesis after seeing its
outcomes. The economic sample that did execute was already negative gross in
both splits. Changing historical name mapping, skip policy, entry hour,
direction, threshold, cost, stop or holding window would be a post-outcome
successor and is not authorized.

## Decision

`HYP-CFTC-FX-H1-001` is terminal. No `.mq5` is created, therefore no compile or
Strategy Tester run exists for this failed hypothesis. That is the intended
fail-closed sequence: the previous Unicorn collector already proved that the
compiler/tester harness works; this fresh economic family failed before build.
The workspace must move to a genuinely new point-in-time mechanism rather than
rescue CFTC TFF weekly positioning.
