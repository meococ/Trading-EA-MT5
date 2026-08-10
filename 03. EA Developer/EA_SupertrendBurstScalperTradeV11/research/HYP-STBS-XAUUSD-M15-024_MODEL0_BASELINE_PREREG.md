# HYP024 frozen Model0 baseline preregistration

Status: FROZEN BEFORE ANY HYP024 PACKET, MODEL0 ATTEMPT, REPORT OR OUTCOME READ

## Identity and legal lineage

- Hypothesis: `HYP-STBS-XAUUSD-M15-024`
- EA: `EA_SupertrendBurstScalperTradeV11`
- Parent: terminal `HYP-STBS-XAUUSD-M15-023`
- Parent terminal raw-row SHA256: `2CA6AD8D565F0670E18DFBD58EA17CEE93372B18D1F06C27216288E49D6FA6B3`
- Parent failure packet SHA256: `7A70CAAC8421B158D26CAD074BC81EBAABFD457B11717845FF04DA524AA319A8`
- Parent post-failure review SHA256: `5906FE93BAE9FA6C700F57D1DC490F0C4FA319276E6D2DED9AA8667A6A7F6FC5`
- V11 source SHA256: `7CC7A9D7C30216A1669D84AEEA867E32EA15F2E9E8C195D171BD574A4D2EB0BC`
- Static EX5 SHA256: `C7C7451C719B4982BEE9F46F4CD1517D533CA0786DBC84128E9D7D9E6F77A22F`
- Static compile log SHA256: `AF7F78FF0EAAA98F9075A902D099AD1863C993474023E19DCA176F82C9C4B678` with exactly `0 errors, 0 warnings`
- Non-repaint manifest SHA256: `DB83B722461F96F39133F54A812B6416DC7F2F5482353550EE254D409F453928`
- Non-repaint audit SHA256: `52DE4406064F7C5586EAA3603F910C684C6E629B6B37CE1416F2BCDE67A1A439`, status PASS, zero findings, exact allowed nondecision CopyTime at source line 678
- V10 to V11 diff proof SHA256: `0B95D49C9D2234ED790E6E09F8AF800C809B499B5366CB451CDD26EDC7732F34`
- Journal-budget addendum SHA256: `C0AD425D1F368A41FE740E3EC22D1CF823F088005848BF14789C6EFFDD3AEF21`
- Tester no-spam projection SHA256: `DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B`, 871,692 bytes
- Agent no-spam projection SHA256: `2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF`, 858,852 bytes
- Compact-telemetry contract test SHA256: `C6CB1D4CE000DF09B8478E1A64FA30542E5D38E5AF84C834A6834FD2EE5A4CB0`
- AlphaFactory SHA256 with bounded-cap support: `55B3B0641BD843B1B1D9620086180CDBC180E9FA2865B08090ED89DF92043571`
- Research-cost manifest SHA256: `7167F5066D90B9CA7BA935F5B5BDC87E243F348E21958ABE283599E20C552676`

HYP023 reached MT5 but failed the frozen engineering journal gate before formal DQ typing, costs or unified validation. No HYP023 PF, PnL, expectancy, validation or market-edge result informs this revision.

## Exactly authorized revision

V11 must be byte-equivalent to V10 after only:

1. identity/version/magic changes to HYP024/V11/5604124; and
2. deletion of the nondecision per-volume `STBS_MARGIN_STRESS_UNSAFE` print after the margin `safe` result is already computed.

No signal, indicator, timeframe, ATR, price geometry, candidate loop, margin calculation, selected volume, entry, SL, TP, holding, exit, risk lock, commission reserve, cost source, filter, threshold or acceptance change is authorized.

The harness must also carry an explicit `max_journal_delta_bytes=4194304` through the task packet, contract receipt, normalized Alpha manifest, DQ gate and HYP024 runner. Omission defaults to one MiB for unrelated lanes. HYP024 requires exactly four MiB. Truncation remains an unconditional engineering failure.

Measured informing replay after only the exact spam deletion is two files and 1,730,544 raw UTF-16LE bytes (871,692 + 858,852), with one identical terminal summary per source. One MiB is provably insufficient; four MiB provides 2.42x headroom. Raising the cap without removing spam would exceed 17 MiB and remains forbidden.

## Frozen MT5 contract

- Symbol/chart: native `XAUUSD`, EA attached to `M15`
- Supertrend decision source: completed native H1 bars, exact frozen Supertrend 10 x 3 recursive mapping inherited from HYP003/HYP012 parity
- Execution ATR: completed native M15 ATR14 at the exact decision time
- Tester preload: `2005.01.01` through `2023.01.01`, Model0, ExecutionMode0, FixedDelay0
- Economic scoring window: inclusive dates `2018.01.02` through `2022.12.30`; pre-2018 bars advance state only and must never trade or score
- Deposit/currency/leverage/spread: 100000 USD, 1:100, current spread semantic with Spread CLI omitted
- Telemetry: `trade-only`, lifecycle-v3, `InpAuditOnly=false`, `InpEnableTelemetry=true`
- Exact overrides: `InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-024;InpMagic=5604124;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V11_COMPACT_MARGIN_TELEMETRY`
- Timeout: 900 seconds
- One-shot IDs: `STBS024-PACKET-BUILD-001`, then `STBS024-MODEL0-TRAIN-001`
- Same-ID retry: false

The exact `HYP-STBS-XAUUSD-M15-024_POST_PACKET_REVIEW.md` path must exist as the frozen `RESERVED_NOT_AUTHORITY` placeholder before packet sealing. The builder rehashes the placeholder and unchanged Git path set immediately before the COMPLETE terminal. After that terminal, only bytes at the same path may be replaced. The final control has exactly five ordered lines: schema `stbs024_post_packet_review.v1`, HYP024 ID, exact packet SHA, exact packet-terminal SHA, and exact verdict `PASS_SCREENED_AUTHORITY`. Any extra, duplicate, contradictory, FAIL, PENDING or negated verdict fails. The screened row binds its final SHA, and the runner may hash/read it only after the durable Model0 launch claim. The placeholder is never approval evidence.

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

Any failure above terminalizes HYP024 with no economic verdict. Existing report values must not be used to tune a successor.

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
