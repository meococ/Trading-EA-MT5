# HYP-SCC-MT5-REPLICATION-EURUSD-M5-002 - corrected invalid matched-pair readout

Verdict: `PARK_INVALID_DIAGNOSTIC_CONTROL_BROKER_STOP_OUT`

The Owner-directed native MT5 diagnostic reached Strategy Tester, but the
matched pair is not admissible as an economic comparison.

## Validity evidence

| Arm | Run | History | Bars | Last lifecycle event | Final position state |
|---|---|---:|---:|---|---|
| Control | `20260725_204410` | 100% | 225,412 | `2022.01.11 02:25:00` OPEN | unresolved after broker/tester stop-out |
| Challenger | `20260725_204518` | 100% | 298,483 | `2022.12.29 05:10:13` CLOSE | flat |

The first diagnosis incorrectly attributed the partial control horizon to an
outer-shell timeout. The retained MT5 agent log proves otherwise:

- `2022.01.11 02:40:00 position stop out triggered`;
- final balance `89,986.63 USD` from a `100,000 USD` initial deposit;
- `stop out occurred on 75% of testing interval`.

RunMeta independently records 225,411 processed bars. Lifecycle telemetry has
832 OPEN rows and 831 CLOSE rows, ending on an unresolved OPEN. The duplicated
HYP-003 control later reproduced the same stop-out at the same market time,
trade count, balance and bar count. This makes the corrected diagnosis
deterministic: the losing control hit the broker/tester stop-out boundary after
about 10% cumulative account loss. It was not an orchestration timeout.

## Descriptive data that cannot decide the pair

- Control partial run: N=832, PF=0.6489, net `-$10,013.37`, DD=10.19%.
- Challenger complete run: N=261, PF=0.6866, net `-$2,979.60`, DD=3.75%.
- Challenger funnel: 1,240 BREAK arms, 875 HOLD passes, 284 accepted retests,
  261 opened positions.

The complete challenger is strongly adverse, but the frozen contract required
a valid full-horizon matched pair. These numbers may not be used to tune a
threshold, subgroup, session or exit.

## Legal continuation

The already-frozen HYP-003 successor can only confirm the failure mode; it may
not be amended in place. A fresh diagnostic child may bind its own identity and
use micro-risk solely to keep the tester alive through the full chart. Signal,
entry, stop, target, timeout, data and pair gates must remain unchanged.
Dollar P/L from that child is scale-diagnostic only, with
`promotion_eligible=false`.
