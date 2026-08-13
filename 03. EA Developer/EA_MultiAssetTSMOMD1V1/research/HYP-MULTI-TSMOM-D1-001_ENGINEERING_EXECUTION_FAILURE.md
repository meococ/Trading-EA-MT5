# HYP-MULTI-TSMOM-D1-001 — engineering execution failure

Status: `PARK_ENGINEERING_MARKET_CLOSED_REBALANCE_IDENTITY_NO_ECONOMIC_VERDICT`

Run: `02. AlphaFactory/runs/EA_MultiAssetTSMOMD1V1/20260812_050007`

The source/data contract passed. The journal recorded 208 Monday decisions, 208 complete nine-symbol source snapshots, zero skipped baskets, and 52 decisions in each design year from 2018 through 2021.

The run is not economically admissible. V1 consumed the Monday key at the first EURUSD H1 tick and immediately sent the close/reopen basket at broker Monday 00:00. The FivePercent test environment still reported `Market closed` at that instant. The terminal summary recorded:

- `entries_requested=1822`, `entries_accepted=190`, `order_send_rejects=1632`
- `closes_requested=1062`, `closes_accepted=182`, `close_rejects=880`
- 5,044 journal occurrences of `Market closed` (including duplicated tester log streams)

Because failed weekly closes left stale positions in place and most target baskets were never opened, the resulting 190 trades, PF 0.5600704740, and net loss are properties of the broken rebalance execution path—not a test of the frozen time-series-momentum hypothesis. They must not be used as economic evidence, as a strategy kill, or as a tuning input.

Authorized successor scope: a fresh package/hypothesis identity may implement only the preregistered `Monday at/after 00:00, next available tick if closed` execution semantics. Formation, volatility estimator, signal direction, universe, caps, risk limits, cost contract, and design/validation/holdout partitions remain unchanged. The successor must not consume a Monday until the old basket is closed and the new planned basket is accepted; partial opens must be unwound before retry.
