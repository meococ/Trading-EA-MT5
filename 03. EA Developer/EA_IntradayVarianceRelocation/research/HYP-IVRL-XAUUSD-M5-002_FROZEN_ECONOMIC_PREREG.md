# HYP-IVRL-XAUUSD-M5-002 — frozen telemetry-cap revision baseline

Status: `FROZEN_BEFORE_OUTCOME_READ`

Parent `HYP-IVRL-XAUUSD-M5-001` reached MT5 but was rejected before economic
acceptance because three raw journal deltas exhausted the frozen 4 MiB cap.
The parent terminal summary still proves the exact source counts completed and
`runtime_failed=false`; its PF and returns remain inadmissible.

IVRL-002 changes only hypothesis identity, magic/log prefix, and the receipt's
raw journal-delta cap from `4,194,304` to `16,777,216` bytes. A normalized
source comparison against the parent run snapshot must be byte-identical.
Signal formula, entry, 12-bar plus 0.20 ATR stop, 1.50R target, 0.10% risk,
3.5%/8% locks, 20:00 flatten and all broker gates are unchanged.

Exactly one AlphaFactory Model-0 run is authorized on FivePercent XAUUSD M5,
`2018.01.01..2023.01.01`, USD100,000, leverage 1:100, current spread and
report commission. No paid data is used.

Engineering gates precede economics: HQ>97%, journal present and untruncated
under 16 MiB, exactly 1,196 raw signals with 607 LONG/589 SHORT,
`runtime_failed=false`, and direct entry/close/reject/risk-lock reconciliation.
Economic gates remain PF>1.30 after costs, expectancy>0, 2–5 completed trades
per `1826/7` weeks, both directions >=30%, no year >30%, and relative equity
DD<=8%. Cost stress, validation, holdout, optimization, paper and live remain
closed until every baseline gate passes.
