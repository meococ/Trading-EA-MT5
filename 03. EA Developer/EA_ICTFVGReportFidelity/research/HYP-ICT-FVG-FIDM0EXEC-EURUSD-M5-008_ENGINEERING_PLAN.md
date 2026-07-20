# HYP-ICT-FVG-FIDM0EXEC-EURUSD-M5-008 - frozen OrderCheck and funnel-observability repair

Status: **FROZEN AFTER DIAGNOSIS, BEFORE SOURCE CHANGE OR CHILD OUTCOME**

## Parent evidence and defect

- Parent: terminal `HYP-ICT-FVG-FIDM0NEWS-EURUSD-M5-007`.
- Parent source SHA-256:
  `E979C05A57A2C77877CF8CA50620925A4FD7A41DBACD5CD96FE078F452204B82`.
- Immutable parent snapshot:
  `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_005716/snapshot/source/EA_ICTFVGReportFidelity.mq5`.
- Parent control `20260719_005603` is not an economic control. Tester journal
  evidence contains 11,330 `OrderCheck rejected retcode=0` rows and five
  genuine `retcode=10016 Invalid stops` rows. `MqlTradeCheckResult.retcode=0`
  is compatible with a successful `OrderCheck`; the source incorrectly
  required `TRADE_RETCODE_DONE` or `TRADE_RETCODE_PLACED`, which are trade
  request execution codes.
- Parent challenger `20260719_005716` never called `TryOpenTrade`: its frozen
  signal funnel reached one valid first retest and then the combined ADX gate
  rejected it. The OrderCheck defect therefore invalidates the control and the
  execution proof, but does not explain the challenger's pre-execution signal
  starvation.
- Existing telemetry combines several materially different rejection reasons,
  so the 149-MSS to one-retest attrition cannot be decomposed from the parent
  artifacts.

## Legal engineering delta

The child may change only execution-check correctness, diagnostic counters,
embedded identity/version and their tests/receipts:

1. Treat `OrderCheck()` boolean failure as rejection and record `GetLastError`,
   check retcode and comment. A successful boolean result with retcode zero is
   accepted as a completed preflight and counted separately. Do not weaken
   stop, margin, volume, broker or post-send retcode checks.
2. Split control gate telemetry into research-disabled, news, session/flatten,
   daily/prop/cooldown, exposure, spread, stop-direction, stop-geometry,
   volume-sizing, OrderCheck and send-failure counters.
3. Split signal attrition into displacement day/timeout, pre-MSS mitigation,
   retest day/timeout, stop breach, invalid zone, depth, rejection-candle, ADX
   read and ADX threshold counters.
4. Do not change any input default, preset byte, signal rule, session, news
   window, risk percentage, stop, target, spread cap, timeframe or holdout.

## Red-first verification

- A source contract test must fail on the parent behavior by proving that
  retcode zero is not compared to `TRADE_RETCODE_DONE/PLACED` after a successful
  `OrderCheck` and that the new reason counters are emitted in RunMeta.
- All package tests, AlphaFactory compile, exact-source non-repaint audit and a
  new source/binary receipt must pass before any child Tester run.

## Frozen execution contract

- Run exactly one sequential pair through AlphaFactory:
  - CONTROL: preset SHA
    `E62D0386B915B4E9BD1FA4A8C761FD72844DBDE2223D175A48F798D6D2F84DB3`.
  - CHALLENGER: preset SHA
    `74FCE7C0C465D5BEA6BAEA9538071C290207621194BA7D74E41996C4CB0A0C68`.
- FivePercent EURUSD M5, MT5 Model 0, 2019.01.01-2022.12.31, deposit 100,000,
  no optimization, no parameter change and no additional rerun.
- Holdout 2023+ remains sealed. Historical execution-cost provenance remains
  failed; fixed 1.5/2.25/3.0-pip costs are diagnostic only and
  `promotion_eligible=false`.
- The child may correct the invalid control and classify signal attrition. It
  may not rescue the parent strategy, tune thresholds or grant paper/live
  authority. Economics are evaluated only if a non-empty trade set exists.
