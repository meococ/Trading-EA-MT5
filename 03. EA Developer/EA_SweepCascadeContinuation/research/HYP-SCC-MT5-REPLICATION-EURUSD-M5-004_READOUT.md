# HYP-SCC-MT5-REPLICATION-EURUSD-M5-004 - terminal readout

Verdict: **KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY**

HYP-004 completed the Owner-directed native MT5 replication end to end. The
micro-risk child removed the broker/tester survival artifact without changing
signal, entry, stop, target, timeout, data or control/challenger definitions.
Both arms are valid full-window Model-0 runs. The strategy mechanism fails.

## 1. Bound identity and validity

| Item | Control | Challenger |
|---|---|---|
| Run | `20260725_210715` | `20260725_210811` |
| Variant | `CONTROL_FIRST_CLOSE_BREAK` | `CHALLENGER_HOLD_RETEST` |
| Model / symbol / period | Model 0 / EURUSD / M5 | same |
| Window | 2019.01.01 to 2022.12.31 | same |
| History quality | 100% | 100% |
| RunMeta bars | 298,483 | 298,483 |
| Lifecycle | 1,112 OPEN = 1,112 CLOSE | 261 OPEN = 261 CLOSE |
| Final state | flat, December 2022 | flat, December 2022 |
| Source SHA256 | `9C03F4CB...7817B3` | same |
| Report/lifecycle net | reconciled exactly | reconciled exactly |
| Stop-out / fatal log error | none | none |
| Non-repaint | PASS | PASS |

The pre-outcome build passed 13/13 package tests and MetaEditor compile with
zero errors and zero warnings. The frozen risk scale was `0.01%`; dollar P/L is
therefore scale-diagnostic only.

## 2. Economics

| Metric | Control | Challenger | Challenger gate |
|---|---:|---:|---|
| Trades | 1,112 | 261 | FAIL, required >=418 |
| Trades / elapsed week | 5.332 | 1.251 | FAIL, required 2.00..5.00 |
| Net | -$2,320.05 | -$587.30 | diagnostic scale only |
| Profit factor | 0.6981 | 0.6913 | FAIL, required >=1.30 |
| Win rate | 34.08% | 31.42% | below realized-payoff breakeven |
| Mean realized R | -0.2156R | -0.2318R | FAIL, required >0 |
| Max DD | 2.379% | 0.748% | PASS at micro-risk scale |
| PF delta | - | -0.0068 | FAIL, required >=+0.10 |
| Mean-R delta | - | -0.0162R | FAIL, required >=+0.05R |
| 1.5-pip stress PF | 0.3639 | 0.3541 | FAIL |
| 2.25-pip stress PF | 0.2630 | 0.2554 | FAIL |

Frozen gates passed: **3/12**. The DD passes are a consequence of micro-risk
and lower trade count, not evidence of edge.

Year stability also fails. Challenger PF by year is 0.387, 0.781, 0.605 and
1.148 for 2019 through 2022; only one of four years exceeds 1. Both directions
lose (BUY PF 0.690, SELL PF 0.693). These are descriptive facts, not permission
to mine a 2022, direction, weekday or hour filter.

## 3. Funnel and mechanism

The control opens 1,112 positions from 1,240 BREAK arms. The challenger:

`1,240 BREAK -> 875 HOLD pass -> 284 RETEST accept -> 261 fills`.

The HOLD to first-passage RETEST path removes 76.5% of control fills, pushes
cadence below the frozen minimum, and does not improve PF or mean R. This is a
failed discriminator, not a promising low-frequency edge.

Observed challenger outcome anatomy:

- 67 of 261 trades are TP-like (`>=1.5R`);
- 167 are SL-like (`<=-0.8R`);
- mean winner is about `+1.64R`;
- mean loser is about `-1.09R`;
- 30 positions close at the 24-bar timeout.

The realized hit rate cannot support the payoff geometry. Commission is booked
on entry and averages `-$1.23` per challenger position, material against the
approximately `$10` planned micro-risk. Cost stress worsens an already losing
native result; it is not the sole cause.

## 4. Logic, execution and telemetry

- Closed-bar decision gate: `OnTick`, `CopyRates(...,1,6,...)` and closed ATR.
- Control call path: `DetectBreak -> ArmBreak -> ResolveControlBreak`.
- Challenger call path:
  `DetectBreak -> ArmBreak -> ResolveHold -> ResolveRetest`.
- Stop/target: BREAK or three-bar complex extreme plus/minus 0.25 ATR, then
  2R target from live entry.
- Management: SL, TP or 24 M5-bar timeout only; no break-even, trail or
  partial close.
- Expected broker-distance and spread rejections are present in the funnel.
  Bound tester windows contain no stop-out, no-money, crash or fatal error.

Four control OPEN rows have zero lifecycle `risk_pts` and
`initial_risk_account`. The analysis recovers those denominators from unique
ORDER_ACCEPTED decision rows. This is defensible for R diagnostics and cannot
change native P/L or PF, but it exposes a rare single-global lifecycle binding
defect in `LogLifecycleDeal`. No same-ID rerun is authorized to repair it.

## 5. Chart and GFI forensics

Five hash-bound M1 anatomy charts with H1 context cover two 2R wins, two fast
SL losses and one 24-bar timeout. Separate outcome-blind as-of charts preserve
the decision information set.

The charts show:

- winners require immediate continuation expansion;
- fast losses can hit extremely tight structure stops within minutes;
- the timeout case shows a valid retest without durable follow-through;
- H1 range location is mixed across the five cases and supplies no legal
  discriminator.

The accepted Grok GFI retry ended at `EndTurn`, opened 5/5 exact case IDs and
independently agreed with the kill. Its integrated readout is:
`research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/HYP004_GFI_INTEGRATED_READOUT.md`.

## 6. Validation boundary

AlphaFactory `validate-full` generated diagnostic Monte Carlo, walk-forward,
robustness and equity artifacts, then returned `REVIEW` for both arms. It
passed real-tick Model 0 and non-repaint, while cadence/equity/robustness
failed and cost/execution provenance remained blocked. Those generic outputs
cannot promote or rescue the strategy.

Costs remain `UNVERIFIED_DIAGNOSTIC_ONLY`: historical spread contains
zero-spread rows, independent slippage is unavailable, and news is disabled
matched. These limitations make promotion impossible; they do not turn PF
0.69 into an unknown economic result.

## 7. Decision and legal next work

The exact SCC mechanism on this frozen EURUSD M5 contract is killed. No
same-ID rerun, retest-bar tuning, ATR-buffer tuning, R:R tuning, session mask,
weekday mask, year mask, direction mask, sensitivity rescue, paper/live or
promotion is authorized.

Only materially new mechanisms may continue under fresh IDs and preregistration:

1. a different structural decision surface rather than first-close BREAK
   continuation;
2. an independently motivated multi-timeframe displacement state defined
   before fresh data is opened;
3. a different structural invalidation object rather than tuning the 0.25 ATR
   buffer observed here.

These are idea-level directions, not approved builds. HYP-001 through HYP-004
remain terminal, and the next mechanism must first pass de-dup plus a cheap
outcome-blind probe.
