# HYP-016 — frozen outcome-blind high-recall context collection

## Identity and boundary

- Hypothesis: `HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016`.
- Parent engineering source: HYP-015 v1.20 SHA-256
  `17E8C20F323402C60B830E47109AD265212869E2E0A8526F21EFDA4734AA1450`.
- Parent HYP-015 is parked engineering PASS. HYP-012 and HYP-014 remain
  terminal and grant no rerun, tuning or promotion authority.
- Purpose: collect every London/New-York high-recall M5 sweep/reclaim candidate
  together with the HYP-015 decision-time Human Context snapshot.
- This is an outcome-blind collection run, not an economic backtest. Trading is
  disabled with `InpResearchAutoMode=false`; zero opened trades is mandatory.
- No source logic may change except embedded identity/version v1.21. The
  existing HYP-015 logger already runs before `TryOpenTrade`.

## Frozen run

- Harness: AlphaFactory only.
- Broker/runtime: configured portable FivePercent tester on D:.
- Symbol/timeframe/model: `EURUSD`, `M5`, Model `0`.
- Window: `2018.01.01` through `2026.07.19`.
- Deposit: `100000`; timeout: `3600` seconds.
- Exact preset:
  `presets/EURUSD_M5_HYP016_HIGHRECALL_CONTEXT_COLLECT.set`.
- Exact overrides:

```text
InpResearchAutoMode=false;InpEnableTelemetry=true;InpSignalMode=0;InpRiskPercent=0.01;InpMagic=5600726;InpPivotStrength=2;InpSweepLookback=20;InpDisplacementBars=6;InpMeanBodyPeriod=20;InpDisplacementBodyMultiple=1.50;InpM15PivotStrength=2;InpM15Lookback=120;InpRetestBars=12;InpFvgDepthMin=0.50;InpFvgDepthMax=0.70;InpAdxPeriod=14;InpMinAdx=25.0;InpContextMaxBars=3;InpContextBodyMultiple=1.00;InpContextCloseFraction=0.25;InpHumanRangeBars=20;InpHumanPivotStrength=2;InpHumanPivotLookback=120;InpHumanAtrPeriod=14;InpStopBufferPips=1.50;InpTargetRR=2.00;InpMaxSpreadPips=1.50;InpMaxTradesPerDay=2;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=100.00;InpMaxConsecutiveLosses=2;InpCooldownMinutes=120;InpBreakEvenTriggerR=1.00;InpBreakEvenLockR=0.50;InpFlattenUtcHour=22;InpFridayFlattenUtcHour=20;InpFridayFlattenUtcMinute=55;InpServerUtcOffsetWinterHours=2;InpServerUsesEuropeDst=true;InpRequireNewsGuard=false;InpNewsBlackoutMinutes=30;InpUseAtrTrail=false;InpAtrTrailStartR=1.50;InpAtrTrailMultiple=1.00
```

## Collection contract

The collection parser may read only the HumanContext ledger, RunMeta identity
and lifecycle row count. It must not read report profit, exits, PnL, deal net,
commission, MFE, MAE or any other outcome field.

Required gates:

1. source, EX5, compile log and preset are hash-bound after a 0/0 compile;
2. exact-source/dependency non-repaint audit PASS with zero findings;
3. run identity is HYP-016, `signal_mode=0`, and history quality is at least
   99% for this diagnostic collection;
4. lifecycle data rows = 0 and `entries_opened=0`;
5. HumanContext rows equal `human_context_snapshots + human_context_invalid`;
6. event IDs and `(decision_time, direction, reason, event_id)` rows are unique;
7. rows span both directions, London and New York, and every available year;
8. complete-context fraction is at least 99%; no future/outcome column exists;
9. elapsed-calendar cadence of the collected universe is at least 2/week;
10. exact rerun of the parser produces the same result hash.

## Pre-economic policy gate

Without reading any outcome, compute the fixed natural policy population:

```text
valid == 1
AND context_state IN {
  EXTERNAL_SWEEP_WITH_ROOM,
  INTERNAL_SWEEP_WITH_ROOM
}
```

This means a directional liquidity target exists, room is at least the frozen
2R target, entry is not outside the H1/H4 20-bar dealing range, and both H1/H4
structures are not simultaneously opposed. It does not require an external
sweep and introduces no tunable threshold.

- If this population is below 2 candidates per elapsed calendar week or lacks
  either direction / either session / any available year: stop before economic
  work with `FRONTIER_CONTEXT_POLICY_CADENCE_FAILED_NO_ECONOMIC_RUN`.
- If it passes: a fresh HYP-017 policy plan must be frozen and SHA-bound before
  source gating or any outcome/economic read.
- HYP-016 can never authorize paper/live use or promotion.
