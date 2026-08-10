# HYP026 frozen Model0 baseline preregistration

Status: FROZEN BEFORE ANY HYP026 PACKET, MODEL0 ATTEMPT, REPORT OR OUTCOME READ

## Identity and legal lineage

- Hypothesis: `HYP-STBS-XAUUSD-M15-026`
- EA: `EA_SupertrendBurstScalperTradeV13`
- Parent: terminal `HYP-STBS-XAUUSD-M15-025`
- Parent terminal raw-row SHA256: `702308403DE58F752A8ECF6F249D7167546F9BD837D42F04386D4B3F3D86B6AA`
- Parent verdict: `KILL_POSTCLAIM_ONE_SHOT_SELF_REJECTION_NO_ALPHA_NO_MT5_NO_ECONOMIC_VERDICT`
- Parent failure SHA256: `F1B8F99D3D49974D20B8A77A6C554A49A4FBE20AE4FA1067122C509623270292`
- Parent post-failure review SHA256: `3ED0948EB0C7D3E59C6E86539BAA38DA2E20E0AAB4C03884120AB41BBDBEBB9F`
- V13 source SHA256: `F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4`
- Static EX5 SHA256: `032ACE29E30750585C34A39F6F74B6DA684C0BF4D1D6ACCFB04245BCBF5D92D4`
- Static compile log SHA256: `FEC1E4F30F811E4BF5BD5B4CFD75E27705CBDE949EDA7E0D0F1FDEF72422710C`, exactly `0 errors, 0 warnings`
- Non-repaint manifest SHA256: `958B4678772D2FFEF8DAC9A22ADCACEFCD0D868862180D02974C0C7433138E63`
- Non-repaint audit SHA256: `D94C9745A0349D946C242B72B2F230B03E43F7E6334711D9ACDB2F89A00DA1E0`, PASS, zero findings, exact nondecision CopyTime allowance at source line 678
- V12-to-V13 diff proof SHA256: `7E1BD63D851B6E77C94106DBCE5B737EA7C1A04539B683C34B33D87745FF3095`
- Journal-budget addendum SHA256: `17D03D4936C9146441BA01D6F4F16DB13CBC2B622E01C56E78EF291981854176`
- Pre-execution harness addendum SHA256: `68DAF00C76CDFEAC2F8558A6BC275A72E10D9CC3B7A68AD193C236A9CDF8D882`
- Tester no-spam projection SHA256: `DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B`, 871,692 bytes
- Agent no-spam projection SHA256: `2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF`, 858,852 bytes
- V13 identity/cost contract test SHA256: `66DD9F7B31A85DF16AEFBFC7941EB1B36D67707D890CF5B5F222DB7F96E19FDE`
- AlphaFactory SHA256 with bounded-cap support: `55B3B0641BD843B1B1D9620086180CDBC180E9FA2865B08090ED89DF92043571`
- Research-cost manifest SHA256: `5C9E00C6405D82D3756DF2E913E69B1E2E34E2405B8E76DFB7EBCDECF602C513`

HYP025 created its sole durable Model0 start, but the later generic authority blocker rejected that exact in-memory marker before Alpha. Its attempt terminal has null run identity and no Alpha run, compile, MT5, data, order, outcome, return or economic evidence. HYP026 must not reuse the consumed HYP025 identity or artifacts as a run.

## Exactly authorized revision

V13 is an identity-only clone of V12. Version, description, EA name, hypothesis, variant and magic advance to HYP026/V13. Strategy logic and all numeric strategy inputs are unchanged.

The only harness behavior change is post-claim reconciliation: once `-Execute` creates and fsyncs the exact HYP026 Model0 start, the later authority check accepts only the exact in-memory start whose path, terminal path, start hash, registry hash, registry-row hash, task-packet path and task-packet hash all match. Missing, pre-existing, terminalized or mutated evidence still fails. Dry-run continues to reject every pre-existing start or terminal.

No signal, indicator, timeframe, ATR, price geometry, candidate loop, margin calculation, volume, entry, SL, TP, holding, exit, risk lock, commission reserve, cost source, filter, threshold or acceptance change is authorized.

The explicit `max_journal_delta_bytes=4194304` contract remains unchanged through packet, receipt, normalized Alpha manifest, DQ gate and runner. Truncation is an unconditional engineering failure.

## Frozen MT5 contract

- Symbol/chart: native `XAUUSD`, EA attached to `M15`
- Supertrend source: completed native H1 bars, frozen Supertrend 10 x 3 mapping inherited from HYP003/HYP012 parity
- Execution ATR: completed native M15 ATR14 at the exact decision time
- Tester preload: `2005.01.01` through `2023.01.01`, Model0, ExecutionMode0, FixedDelay0
- Economic scoring window: inclusive `2018.01.02` through `2022.12.30`; pre-2018 bars advance state only
- Account: 100000 USD, 1:100, current spread semantic with Spread CLI omitted
- Telemetry: `trade-only`, lifecycle-v3, `InpAuditOnly=false`, `InpEnableTelemetry=true`
- Exact overrides: `InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-026;InpMagic=5604126;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE`
- Timeout: 900 seconds
- One-shot IDs: `STBS026-PACKET-BUILD-001`, then `STBS026-MODEL0-TRAIN-001`
- Same-ID retry: false

The exact addendum path `03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_PRE_EXECUTION_HARNESS_ADDENDUM.md` is mandatory in probe, packet, screened authority and post-claim validation.

The reserved review path `03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/HYP-STBS-XAUUSD-M15-026_POST_PACKET_REVIEW.md` must exist before packet sealing. The builder rehashes its placeholder and the unchanged Git path set immediately before COMPLETE. After COMPLETE, only bytes at that same path may change. Final content is exactly five ordered lines: schema `stbs026_post_packet_review.v1`, HYP026 ID, packet SHA, packet-terminal SHA and verdict `PASS_SCREENED_AUTHORITY`.

## Engineering gates before any economic readout

All must pass in the sole attempt:

1. fresh run compile 0 errors and 0 warnings with exact source, EX5, config, report and manifest hashes;
2. HQ strictly above 97, full window and native series proof;
3. journal below 4,194,304 raw bytes, `truncated=false`, complete terminal summary, no fatal, exact duplicate normalization and deterministic replay;
4. raw signals 690, executable 683, gaps 7, LONG 339, SHORT 344, ATR-ready 683, geometry-ready 683 and margin-ready 683;
5. exact RunMeta identity, `audit_only=false`, `promotion_eligible=false`, runtime failure false and lifecycle row reconciliation;
6. every request/order/deal/position/exit reconciles, with no orphan, pending exposure, stopout, margin emergency, unresolved lifecycle ticket or unbalanced position;
7. report deals equal lifecycle deals plus the single 100000 funding row;
8. static and run-local non-repaint audits pass with only the exact nondecision CopyTime allowance;
9. verified research-cost artifact and unified rebuild are deterministic from captured immutable bytes.

Any engineering failure terminalizes HYP026 with no economic verdict and may not be used for tuning.

## Frozen costs and baseline acceptance

Cost tier is `VERIFIED_RESEARCH_PROXY_NONPROMOTABLE`: historical M1 spread, tester-maximum 4.4 USD/lot round-turn commission and direction-aware fixed-latency adverse quote proxy. It can falsify the baseline but cannot establish promotion readiness.

Only after every engineering gate passes, the one untuned TRAIN baseline must satisfy:

- at least 500 completed trades;
- 2.0 to 5.0 completed trades per inclusive calendar week using `((to_date-from_date).days+1)/7`;
- each direction at least 30%, and no calendar year above 30% of trades;
- PF after x1 frozen costs at least 1.30 and positive x1 expectancy;
- every calendar year positive at x1 costs;
- PF at x1.5 costs at least 1.25;
- PF at x2 costs at least 1.00;
- maximal drawdown at most 8%, with later Monte Carlo p95 drawdown at most 8%.

This baseline authorizes no optimization, parameter search, direction/session filtering, OOS, holdout, paper, live or market-edge claim. Only an engineering-valid and economically passing baseline may open a separately frozen robustness stage.
