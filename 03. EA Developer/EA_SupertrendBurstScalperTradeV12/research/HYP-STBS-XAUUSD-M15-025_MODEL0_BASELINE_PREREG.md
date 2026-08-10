# HYP025 frozen Model0 baseline preregistration

Status: FROZEN BEFORE ANY HYP025 PACKET, MODEL0 ATTEMPT, REPORT OR OUTCOME READ

## Identity and legal lineage

- Hypothesis: `HYP-STBS-XAUUSD-M15-025`
- EA: `EA_SupertrendBurstScalperTradeV12`
- Parent: terminal `HYP-STBS-XAUUSD-M15-024`
- Parent terminal raw-row SHA256: `0DF555A30DE1674919A736177BA9CFAC0B587FA7B15AD12A1CB174CF5B3EF47E`
- Parent pre-MT5 failure SHA256: `D58707EF9ADCCEE78FEFBCAFBB35B06342D3DDB5A641421097EA77EBD674ADEA`
- Parent post-failure review SHA256: `B953B81C316690F8F0B4E7EB226F10E16FE49B68B6DD31102D2E90F9E87548E3`
- V12 source SHA256: `D96F55A26F277CFC3FDC4E23A11A84C74598C111639E629CEC1877AC3F7704C5`
- Static EX5 SHA256: `229E76BA503471AC86C947463FF1DD340FF1B182E9A5D8A193DFD16AFEEFD27F`
- Static compile log SHA256: `B2D9AA542737168BEC8A9A2A4135D407A3CE2546577B398076E5328B4AD7BEF9` with exactly `0 errors, 0 warnings`
- Non-repaint manifest SHA256: `B8D52779E516C8BD5B3BD776BECF80B98EC26E568FF0B443A7C74362DAB81A2A`
- Non-repaint audit SHA256: `3ECC757DB44BD40BF77AAD25BA9131704DCA452F7C7137557A85FDEA84A8AF2E`, status PASS, zero findings, exact allowed nondecision CopyTime at source line 678
- V11-to-V12 identity-only diff proof SHA256: `507F9E3F75EECE7F107499ECF083D929E70535D424C7FA836B301C6D8F61F11C`
- Journal-budget addendum SHA256: `F256F9FA6A3358ABD2658BDF59240B38B28DDEB97D363D3C1C4F7283478A1A85`
- Pre-execution harness addendum SHA256: `C098ADC331255509C6FF7905F65F335FC1252857D80AA094E98410B56BB62951`
- Tester no-spam projection SHA256: `DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B`, 871,692 bytes
- Agent no-spam projection SHA256: `2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF`, 858,852 bytes
- V12 identity/telemetry contract test SHA256: `07E235A86CEBFD7809FAA721565A2943DB7607F62BAB2B8D7099D3C6CF94384F`
- AlphaFactory SHA256 with bounded-cap support: `55B3B0641BD843B1B1D9620086180CDBC180E9FA2865B08090ED89DF92043571`
- Research-cost manifest SHA256: `2ACD676CA04DB1DF83C931514C6B05DAABFDCF94F5F29B7A575E0492B0F7FD86`

HYP024 never created its Model0 attempt root and never reached Alpha or MT5. It terminalized only because its screened row omitted the generic pre-execution harness addendum binding required by the frozen runner. No HYP024 report, PF, PnL, expectancy, validation or market-edge result exists.

## Exactly authorized revision

V12 is an identity-only clone of V11. Outer registry, packet, receipt, attempt and run-manifest identity, plus inner MQL5 override, RunMeta and lifecycle identity, all equal HYP025. Only version/description, EA name, hypothesis, variant and magic identity changed; executable strategy logic and numeric strategy inputs are unchanged.

No signal, indicator, timeframe, ATR, price geometry, candidate loop, margin calculation, selected volume, entry, SL, TP, holding, exit, risk lock, commission reserve, cost source, filter, threshold or acceptance change is authorized.

The harness must also carry an explicit `max_journal_delta_bytes=4194304` through the task packet, contract receipt, normalized Alpha manifest, DQ gate and HYP025 runner. Omission defaults to one MiB for unrelated lanes. HYP025 requires exactly four MiB. Truncation remains an unconditional engineering failure.

Measured informing replay after only the exact spam deletion is two files and 1,730,544 raw UTF-16LE bytes (871,692 + 858,852), with one identical terminal summary per source. One MiB is provably insufficient; four MiB provides 2.42x headroom. Raising the cap without removing spam would exceed 17 MiB and remains forbidden.

## Frozen MT5 contract

- Symbol/chart: native `XAUUSD`, EA attached to `M15`
- Supertrend decision source: completed native H1 bars, exact frozen Supertrend 10 x 3 recursive mapping inherited from HYP003/HYP012 parity
- Execution ATR: completed native M15 ATR14 at the exact decision time
- Tester preload: `2005.01.01` through `2023.01.01`, Model0, ExecutionMode0, FixedDelay0
- Economic scoring window: inclusive dates `2018.01.02` through `2022.12.30`; pre-2018 bars advance state only and must never trade or score
- Deposit/currency/leverage/spread: 100000 USD, 1:100, current spread semantic with Spread CLI omitted
- Telemetry: `trade-only`, lifecycle-v3, `InpAuditOnly=false`, `InpEnableTelemetry=true`
- Exact overrides: `InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-025;InpMagic=5604125;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V12_IDENTITY_CLONE`
- Timeout: 900 seconds
- One-shot IDs: `STBS025-PACKET-BUILD-001`, then `STBS025-MODEL0-TRAIN-001`
- Same-ID retry: false

The exact pre-execution harness addendum path is `03. EA Developer/EA_SupertrendBurstScalperTradeV12/research/HYP-STBS-XAUUSD-M15-025_PRE_EXECUTION_HARNESS_ADDENDUM.md`. It is a mandatory probe, packet, screened-authority and post-claim runner binding.

The exact `HYP-STBS-XAUUSD-M15-025_POST_PACKET_REVIEW.md` path must exist as the frozen `RESERVED_NOT_AUTHORITY` placeholder before packet sealing. The builder rehashes the placeholder and unchanged Git path set immediately before the COMPLETE terminal. After that terminal, only bytes at the same path may be replaced. The final control has exactly five ordered lines: schema `stbs025_post_packet_review.v1`, HYP025 ID, exact packet SHA, exact packet-terminal SHA, and exact verdict `PASS_SCREENED_AUTHORITY`. Any extra, duplicate, contradictory, FAIL, PENDING or negated verdict fails. The screened row binds its final SHA, and the runner may hash/read it only after the durable Model0 launch claim. The placeholder is never approval evidence.

## Engineering gates before any economic readout

All must pass in the sole attempt:

1. fresh run compile 0 errors and 0 warnings; exact source/EX5/config/report/run-manifest hashes;
2. HQ strictly above 97, full frozen window and exact native series proof;
3. journal raw delta below 4,194,304 bytes, `truncated=false`, exact source multiplicity, complete history/DQ records, terminal `STBS_SUMMARY`, no `STBS_FATAL`, and deterministic replay;
4. exact signal identity raw 690, executable 683, gaps 7, LONG 339, SHORT 344, ATR-ready 683, geometry-ready 683 and margin-ready 683;
5. RunMeta identity exact, `audit_only=false`, `promotion_eligible=false`, `diagnostic.runtime_failed=false`, and lifecycle row count matches the captured lifecycle CSV;
6. every request/order/deal/position/exit reconciles, no orphan/pending exposure, stopout, margin emergency, unresolved lifecycle ticket or unbalanced position;
7. report deal set equals lifecycle deal set plus the single frozen 100000 funding row;
8. static and run-local non-repaint audit both pass with only the exact nondecision CopyTime allowance;
9. verified research-cost artifact and unified rebuild are deterministic from captured immutable bytes.

Any failure above terminalizes HYP025 with no economic verdict. Existing report values must not be used to tune a successor.

## Frozen costs and baseline acceptance

Cost tier is `VERIFIED_RESEARCH_PROXY_NONPROMOTABLE`: historical M1 spread, tester-maximum 4.4 USD/lot round-turn commission, and direction-aware fixed-latency adverse quote proxy. This can falsify the baseline but cannot establish promotion readiness.

Only after every engineering gate passes, the one untuned TRAIN baseline must satisfy all:

- completed trades at least 500;
- cadence 2.0 to 5.0 completed trades per inclusive calendar week, using `((to_date-from_date).days+1)/7`;
- each direction at least 30%; no calendar year above 30% of trades;
- PF after x1 frozen cost at least 1.30 and positive x1 expectancy;
- every calendar year positive at x1 cost;
- PF at x1.5 cost at least 1.25;
- PF at x2 cost at least 1.00;
- maximal drawdown at most 8%; later Monte Carlo p95 drawdown at most 8%.

This baseline authorizes no optimization, parameter search, direction/session filtering, OOS, holdout, paper trading, live trading or market-edge claim. Only an engineering-valid and economically passing baseline may open a separately frozen robustness stage.
