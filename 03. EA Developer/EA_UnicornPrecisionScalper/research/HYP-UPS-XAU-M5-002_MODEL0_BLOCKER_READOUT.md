# Model 0 Preflight Readout — HYP-UPS-XAU-M5-002

## Result

The generic AlphaFactory loop was invoked in dry-run mode for XAUUSD M5,
2024-01-01 through 2026-07-15, Model 0, control role and lifecycle-v3
trade-only telemetry. It returned exit 0 with `execution_allowed=false`. No
terminal/tester process or report was created.

## Contracts that passed

- latest registry state `screened`, canonical source and source SHA;
- frozen prereg, capability contract and lifecycle telemetry tier;
- task packet, current Git/status identity and empty custom-include closure;
- symbol geometry, window, Model, deposit/leverage and exact overrides;
- seven frozen acceptance gates.

## Blocking contract

All 20 detailed blockers are cost-source requirements:

- no historical XAU spread source bound to the MetaQuotes packet identity
  (the separate FivePercent raw source passes coverage validation);
- no >=30 same-symbol commission lifecycles or explicit same-broker contract;
- no >=100 independent-reference slippage samples, including >=30 buy and >=30
  sell observations against ask/bid respectively;
- no direction-aware cost methodology binding those sources.

The explicit manifest is intentionally marked
`MISSING_REQUIRED_PROVENANCE`; missing/null fields were not represented as zero.

## Verdict and next legal action

`BLOCKED_BY_MISSING_INPUT`. Acquire and audit the same-broker XAU cost evidence,
refresh packet hashes, rerun dry-run, and use `-Execute` only if the plan returns
`execution_allowed=true`. Until then there is no backtest economics to analyze
and no legal threshold/strategy rescue.

## Cost-frontier follow-up

The follow-up audit exported 894,192 same-broker M1 spread observations to `D:`
and passed AlphaFactory's raw spread validator. Local QFSI/account history still
contains zero XAU commission lifecycles and zero XAU independent-reference
slippage fills. It also found that the active demo terminal is currently bound
to FivePercentOnline while this task packet was prepared with a MetaQuotes
identity; the identities must not be mixed. See
`HYP-UPS-XAU-M5-002_COST_FRONTIER_AUDIT.md`. No `-Execute` run was started.

## Third-turn local-reuse audit

The complete local AlphaFactory inventory was rebuilt and 52 XAU run
manifests/reports were inspected. The strongest FivePercent legacy run has 335
tester commission lifecycles and 335 request/fill rows (171 BUY / 164 SELL),
but every modeled entry-slippage value is zero. Its PX6 sidecars lack
independent millisecond BID/ASK timing and the old run manifest does not bind
source/EX5/fingerprint/lifecycle-v3 reconciliation. This cannot prove real
slippage is zero. See `HYP-UPS-XAU-M5-002_LOCAL_COST_REUSE_AUDIT.md`.

The same external-input blocker has now repeated across the original goal turn
and two automatic continuations. No remaining local artifact can legally open
Model 0 without relabeling tester simulation as real execution evidence.
