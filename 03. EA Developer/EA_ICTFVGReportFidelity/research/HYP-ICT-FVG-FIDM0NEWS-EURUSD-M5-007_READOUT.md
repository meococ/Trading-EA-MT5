# HYP-ICT-FVG-FIDM0NEWS-EURUSD-M5-007 - Model-0 readout

Verdict: **KILL_AT_MODEL0_CADENCE_ZERO_TRADE**  
Promotion eligible: **false**  
Holdout 2023+: **sealed / not loaded**

## What was built and repaired

The canonical EA implements the ordered report-fidelity chain:

`M5 sweep/reclaim -> displacement + strict FVG -> fresh OB/FVG overlap ->
closed M15 MSS -> first 50-70% retest/rejection -> closed M15 ADX > 25`,

with London/New York sessions, immutable historical-news lookup, fixed-money
risk sizing, prop controls, restart reconciliation and lifecycle-v3 telemetry.

The first parent control attempt (`20260719_003953`) stopped in `OnInit` with
zero bars and zero ticks. It exposed a generator defect: 1,282 distinct news
events contained 869 distinct release timestamps, but all 1,282 timestamps
were copied into a lookup that requires strict ordering. The fresh child was
frozen before repair. Raw and CSV evidence remain at 1,282 events; the MQL5
lookup now contains 869 sorted unique timestamps and records that 413 same-time
event rows were collapsed only in the execution lookup.

Final engineering proof: 22/22 package tests PASS, AlphaFactory compile 0
errors / 0 warnings, exact-source static non-repaint V10 PASS and post-run
source/binary receipt V9 verified. Canonical source SHA-256 is
`E979C05A57A2C77877CF8CA50620925A4FD7A41DBACD5CD96FE078F452204B82`.

## Frozen Model-0 pair

Both runs used FivePercent EURUSD M5, MT5 Model 0, 2019.01.01-2022.12.31,
deposit 100,000, the frozen preset hashes and the same source/include closure.
Each report has 100% history quality, 298,483 bars and 79,486,116 ticks.
Run-scoped non-repaint audits pass with zero findings.

| Arm | Run | Funnel | Trades | Cadence |
|---|---|---|---:|---:|
| High-recall control | `20260719_005603` | 12,340 sweeps; 698 news rejects; 23 spread rejects; 11,336 risk/geometry rejects | 0 | 0.0/week |
| Full report-fidelity FSM | `20260719_005716` | 12,340 sweeps -> 293 displacement/FVG -> 149 M15 MSS -> 144 pre-MSS mitigations -> 1 valid first retest -> 1 ADX reject | 0 | 0.0/week |

The challenger task packet binds control manifest SHA
`8129842949B7C515222B20B2B61513925E27707631EB6020E60420FDC5C43CC1`
and report SHA
`EA7B7D1A5A4FA246CABEB556488F8C1F46B26FB780611721DF2058529B9C320B`.
The paired result artifact is
`research/evidence/HYP-ICT-FVG-FIDM0NEWS-EURUSD-M5-007_MODEL0_RESULT.json`.

## Gate decision

- Minimum sample >=300 closed trades: **FAIL (0)**.
- Cadence 2.0-5.0 per 208.571 elapsed weeks: **FAIL (0.0)**.
- PF at 1.5/2.25/3.0-pip round-trip cost: **not computable**, not zero.
- WR, expectancy, Sharpe, Sortino, Calmar, CVaR and economic drawdown are
  **undefined** for an empty trade set.
- WFA, Monte Carlo, prop simulation and public/pro-trader economic comparison
  are inapplicable after the terminal sample/cadence failure.

The full strategy is therefore inferior to the workspace's minimum viable
cadence requirement. This does not prove that discretionary ICT/FVG trading or
all OHLC/context strategies lack edge. It falsifies this exact quantified
ordering, freshness, first-retest, ADX and execution contract on this frozen
EURUSD M5 window.

## Comparison boundary and limitations

The high-recall arm is not a useful economic benchmark because every surviving
sweep was rejected before an order attempt, predominantly by stop geometry or
order-risk checks. Therefore the EA-versus-control performance verdict is
`INCONCLUSIVE`. This control defect does not rescue the full challenger: the
challenger itself produced only one valid retest in four years and zero entries.

Historical same-broker execution-cost provenance remains failed: spread data
contain zero rows, the commission lifecycle sample is insufficient and
direction-aware slippage is absent. The fixed 1.5/2.25/3.0-pip schedule was
diagnostic only. No paper/live attachment, optimization, rerun, threshold
loosening or 2023+ access is authorized. A future attempt requires a materially
different strategy object or information set under a fresh preregistration;
post-hoc loosening of this chain is forbidden.
