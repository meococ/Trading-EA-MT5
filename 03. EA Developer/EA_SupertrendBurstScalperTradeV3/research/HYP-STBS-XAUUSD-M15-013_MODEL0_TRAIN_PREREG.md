# HYP-STBS-XAUUSD-M15-013 — one untuned Model-0 economic baseline

Status: `FROZEN_PRE_OUTCOME`

## Thesis and exact revision boundary

The market thesis is unchanged: a completed native H1 Supertrend-10x3 state flip may retain enough next-open continuation to support a short M15 burst trade. Entry is only at the exact next native M15 open. The prior completed M15 ATR14 supplies a 1.00 ATR protective stop; target is 1.50R; requested-price equity risk is 0.25%; maximum hold is eight completed M15 bars. The strategy holds at most one owned position, never pyramids, never trails or moves to breakeven, blocks Friday entries after 18:00 UTC, and flattens by 20:00 UTC/weekend.

HYP013 is a fresh child of terminal pre-run HYP012. HYP012 opened no compile, MT5, report, outcome or economics, so no outcome informed this revision. HYP013 changes only outer/inner identity, magic and lifecycle-v3 evidence emission needed by the canonical verified-cost builder. Every common V2/V3 trade function is byte-equivalent under the frozen source test; trading signals, execution FSM, risk, stop, target, holding period, sessions and indicator parameters are unchanged.

- EA: `EA_SupertrendBurstScalperTradeV3`.
- Source SHA256: `8E1DEA824FC0BC1699FC618AC71F2C8D7848556215699FFF432DA1BF9EEFF3B0`.
- Direct parent HYP012 terminal raw-row SHA256: `AC4881E72A875E914580F3C5CEE9269273DF031F681609B605B183608BE6F1FF`.
- Engineering parity ancestor HYP011 terminal raw-row SHA256: `8E69D8AAD2021E12475E8879AA4E0914299FC77F0D1CDE806FB1ECDDAD138232`.
- Frozen V2 source ancestor SHA256: `D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB`.
- Exact effective overrides: `InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-013;InpMagic=5604113;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_FSM_V3_TELEMETRY`.
- No optimization, parameter search, session/direction selection, post-read filter or same-ID retry is permitted.

## Engineering evidence frozen before outcomes

- MetaEditor compile: `0 errors, 0 warnings`; EX5 SHA256 `8330D957AC11B04A0E3EA46482C67E97253C945BAEAA60AC9DE720C5372BDBA7`; compile-log SHA256 `DBB242DB21626640C72FC6A14982F39B450EDA6CEDE2AEE2D11A40947A431CD4`.
- EA capability contract SHA256: `891E6636F45B263F6163F5E703C9E87B912846B114CE25D5E45517871FD28057`; telemetry profile is `lifecycle-v3` and tier must be `trade-only`.
- Static non-repaint manifest SHA256 `BB4D50443DF5E823CB67DE2DD5E010D6B687BE2D447D25C89C203705377DF553`; audit SHA256 `69D1DE724BE08DD2BD776543AD9D0368DBEA788577884E1B26BFA83E2B56B86C`, status PASS, zero findings. The canonical loop must rerun this audit against the run snapshot and execution receipt.
- Source/telemetry contract test SHA256 `6839FAEB9179D676C955F741D12CAF57E0C26F6AE7B9024DA845921C230200B3`.
- AlphaFactory plus focused suite: 266 AlphaFactory tests and 14 HYP013/cost-window/RunMeta mutation tests passed before any outcome read.

## Sole baseline execution contract

- Broker/server/account: frozen Five Percent fingerprints in the task packet and cost manifest.
- Symbol/chart: `XAUUSD`, native M15.
- Tester preload window: `2005.01.01` through `2023.01.01`; Model 0, execution mode 0, fixed delay 0, current tester spread, USD 10,000, leverage 1:100, control role, nonvisual, timeout 900 seconds.
- Economic/cost scoring window: inclusive `2018.01.02` through `2022.12.30`. Full prehistory may advance the recursive H1 state, but every report trade deal, position entry and exit must remain inside this scoring window. Any preload/post-window trade makes the baseline invalid rather than being deleted.
- One Model-0 economic attempt only. A timeout, missing report, missing lifecycle row, report/lifecycle mismatch or invalid data fingerprint is an engineering failure and reveals no economic verdict.

The canonical toolchain is frozen to:

- `02. AlphaFactory/alpha.ps1` SHA256 `68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8`;
- research loop SHA256 `2E89E9C654B301C7BDB22AF344BA7BEFD4C8B7459AE7BE6EFF9A36118E7D61DE`;
- verified-cost builder SHA256 `617AF7E526E7D30DBB7C6BBEF7B6DB3740552ABA31BFBFB0F6C42A4C1F8BB3AD`;
- unified validator SHA256 `E9C26801D020298AE6BADD1737ECE5B77778EA34951B99EB3A0B81F47D5E9DE2`;
- non-repaint auditor SHA256 `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`.

## Frozen cost evidence and evidentiary ceiling

The exact HYP013 cost-source manifest SHA256 is `77A7D738AD945AB869CC1682110FF64C1DC3D8827039F68F937392A793C7CAF8`. It binds complete historical XAUUSD M1 bid/ask coverage for the economic window, maximum tester-observed commission of USD 4.40 per lot round turn, and direction-aware 1,000 ms adverse executable-quote proxy p90 of 80 XAU pips round turn. The builder must join every MT5 report deal to lifecycle-v3 telemetry, reconcile completed positions and reprice each position in initial-risk R. It also requires exactly one manifest-bound RunMeta with the frozen HYP013/variant/magic, `audit_only=false`, `promotion_eligible=false`, `diagnostic.runtime_failed=false`, and `diagnostic.lifecycle_rows` exactly equal to the lifecycle CSV data-row count; this semantic result is included in the canonical cost rebuild.

This evidence is explicitly `RESEARCH_PROXY`: commission is tester evidence and slippage is a quote proxy, not an observed fill. It can economically falsify HYP013 but cannot make it promotion-ready, paper-ready or live-ready, even if every baseline gate passes.

## Exact baseline acceptance gates

The separate baseline verdict uses only the following predeclared gates:

- at least 500 completed positions;
- 2.0–5.0 completed positions per elapsed economic-window calendar week, using `completed_positions / (((economic_to - economic_from).days + 1) / 7)` because both boundary dates are inclusive;
- BUY and SELL each at least 30% of positions;
- no exit calendar year above 30% of positions;
- every calendar year 2018–2022 has at least one exit and strictly positive x1 net R;
- strictly positive mean x1 net R;
- x1 cost-adjusted PF strictly greater than 1.30;
- x1.5 cost-stress PF at least 1.25;
- x2 cost-stress PF at least 1.00;
- maximum equity drawdown at most 8%.

The wider unified-validation verdict may remain REVIEW because optimization-aware WFA, variant robustness, holdout and promotion-grade execution costs are intentionally absent. `baseline_falsification_verdict` is therefore the only authority for deciding this one TRAIN object: PASS may open a fresh, separately preregistered robustness/OOS lane; FAIL parks only HYP013 and forces a materially new strategy mechanism after independent review; BLOCKED triggers a fresh engineering revision without interpreting PF or expectancy. No result-mined rescue is allowed.
