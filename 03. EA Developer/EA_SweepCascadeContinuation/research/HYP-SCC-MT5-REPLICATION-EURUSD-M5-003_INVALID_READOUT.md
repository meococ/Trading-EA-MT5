# HYP-SCC-MT5-REPLICATION-EURUSD-M5-003 - invalid control readout

Verdict: `PARK_INVALID_DIAGNOSTIC_REPRODUCED_BROKER_STOP_OUT`

HYP-003 was frozen before the MT5 agent log was correctly interpreted. It
changed only source identity, magic and synchronous orchestration. The single
authorized control run reproduced HYP-002 exactly and invalidated HYP-003
before a challenger run could legally start.

## Control evidence

- AlphaFactory run: `20260725_205454`
- MT5: D-drive portable FivePercent terminal, Model 0, EURUSD M5
- Requested interval: `2019.01.01` through `2022.12.31`
- Actual processed bars: 225,411 RunMeta bars (225,412 report bars)
- Lifecycle: 832 OPEN, 831 CLOSE; final event is unresolved OPEN at
  `2022.01.11 02:25:00`
- Native report: N=832, PF=0.6489, net `-$10,013.37`, DD=10.19%
- Tester log: `position stop out triggered` at `2022.01.11 02:40:00`,
  final balance `89,986.63 USD`, and stop-out at 75% of the testing interval

The run matches HYP-002 control on market time, trade count, PF, net P/L,
balance, processed bars and lifecycle imbalance. Synchronous orchestration did
not change the outcome. The control hit the broker/tester stop-out boundary
after about 10% cumulative account loss.

## Decision

The challenger was not run because the frozen full-window and flat-final-state
gates had already failed. HYP-003 is terminal invalid and authorizes no same-ID
rerun or parameter amendment.

A fresh diagnostic child may use `InpRiskPercent=0.01` instead of `0.05` only
as a scale instrument to keep the tester alive. It must bind a new identity and
magic, preserve every alpha and execution-geometry rule, remain
`promotion_eligible=false`, and treat dollar P/L as non-comparable across risk
scales. No post-outcome strategy rescue is authorized.
