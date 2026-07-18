# Operational invalidation — HYP-UPS-XAU-M5-003

## Decision

`HYP-UPS-XAU-M5-003` is invalidated before analysis. Run `20260716_133403`
is not admissible strategy evidence and its performance must not be used to
change any signal, threshold, time filter, or management rule.

## Fail-closed reasons

- The EA wrote lifecycle-v3 telemetry through `FILE_COMMON`, while the frozen
  storage contract forbids Common files because that route resolves to the
  user profile on `C:`. AlphaFactory therefore collected no required sidecar.
- The source embedded `HYP-UPS-XAU-M5-002`; its RunMeta could not bind the
  executed telemetry to HYP-003.
- The portable terminal authenticated to `MetaQuotes-Demo`, not the frozen
  `FivePercentOnline-Real` broker/server identity. No fingerprint may be
  learned or rebound from that report.

## Allowed continuation

HYP-004 may change only the telemetry sink and embedded hypothesis identifier:
normal Strategy Tester sandbox files on the dedicated FivePercent portable
root on `D:`. HYP-004 inherits every frozen HYP-003 strategy, risk, window,
acceptance and research-cost rule unchanged. This is an operational repair,
not a post-hoc strategy rescue.

