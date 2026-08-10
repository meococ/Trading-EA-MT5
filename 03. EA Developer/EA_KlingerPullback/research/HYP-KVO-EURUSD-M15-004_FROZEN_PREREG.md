# HYP-KVO-EURUSD-M15-004 — Frozen untuned economic baseline

## Thesis and engineering-only revision

The market thesis and every strategy parameter remain exactly HYP-KVO-EURUSD-M15-003: Klinger 34/55/13 pullback re-entry with EMA100 trend on EURUSD M15, three-bar swing plus 0.15 ATR stop, 1.50R target, 16-bar exit, one accepted trade/day and 0.25% equity risk.

HYP003 completed MT5 but was inadmissible before economics. Exact `OrderSend=false`, `TRADE_RETCODE_MARKET_CLOSED`, order/deal 0 was classified fatal, and 9,524 routine signal rows caused the two-file journal delta to truncate at 1 MiB. PF and PnL were not opened.

HYP004 changes only engineering evidence behavior:

- Exact `MARKET_CLOSED` with result order/deal both zero may be a definitive no-fill even if `OrderSend=false`; it is nonfatal only after successful zero owned-position/order reconciliation.
- Every other transport failure, retcode, result ticket or uncertain/nonzero inventory remains fatal.
- Routine signal, accepted-entry, OrderCheck rejection and definitive-no-fill prints are removed. INIT, D0, preload, fatal, close failure and terminal summary evidence remain.
- The next receipt binds `max_journal_delta_bytes=33554432`. HYP003 proves the frozen source has 9,524 raw signals over the full TRAIN path, but its fatal flag prevented later broker attempts, so its 118,200-byte compact projection is diagnostic only. The conservative bound instead allows one native reject record for every raw signal plus seven additional native records for every possible accepted-entry/exit lifecycle on each of 2,919 calendar days, across both tester sources. At 260 UTF-16 bytes per native record plus 1 MiB fixed overhead, this is 16,626,216 bytes; the frozen 32 MiB limit supplies 2.018 times headroom. Exact arithmetic and supporting log hashes are frozen in `HYP-KVO-EURUSD-M15-004_JOURNAL_BUDGET_PROOF.json`. Truncation remains fatal. This changes evidence collection only.

No outcome, PF or trade subset informed any market rule.

## Frozen identity/data

- Hypothesis `HYP-KVO-EURUSD-M15-004`; package `EA_KlingerPullback`
- Variant `KVO34_55_13_EMA100_PULLBACK_REENTRY_COMPACT`; magic `5604004`
- EURUSD M15; TRAIN `[2010-01-04, 2018-01-01)`; Model 0; execution/fixed delay 0
- Validation 2018–2022 and holdout 2023–2025 remain sealed
- One attempt only; no optimization

## Frozen signal/execution

- Klinger VF/CM flat-safe recursion, EMA34/55, signal EMA13, EMA100 trend and full completed-history preload are unchanged.
- LONG/SHORT arm/cross/equality/reset rules are unchanged.
- Exact next native M15 open only; gaps consume events.
- FOK market order; one owned position; no pending orders or pyramiding.
- Risk, SL, TP, time exit, Friday/weekend/design flatten, daily lock and peak-DD lock are unchanged.
- No trailing, breakeven, partial exit or post-result exit modification.
- No session, direction, volatility, spread, news or performance-derived filter.

## Acceptance

Engineering first: compile 0/0, NR PASS, complete nontruncated journal, D0 proof, HQ `>97%`, `runtime_failed=false`, report/summary reconciliation and no orphan inventory.

Then TRAIN requires PF `>1.30` after report costs, positive expectancy/net, cadence `2–5` closed positions/week, each direction at least 30%, no year above 30%, equity DD `<=8%`. A material miss kills the mechanism; no rescue tuning. Only a pass may open full cost coverage/stress and validation.

## Frozen implementation evidence

- MQL5 source SHA256 `D106560C5960AE90E8AA83767C14065B51BDDF09D55DAF34DE0DCA67399249C2`
- compiled EX5 SHA256 `996877B0BAEA3DD9FDFC98D70778390467E2ED7115425B42838DEB5609E8882B`
- compile log SHA256 `A28CD635962E9BABCDE4E2E1B3B73DD15EE7033375AA0EE81E5D4788CD75E10A` with `0 errors, 0 warnings`
- EA contract SHA256 `609CCAC7632F74E47B15D5D5262592B7DBF45F8314DE39135E4121AE0984A95C`
- source-to-spec SHA256 `CA6D120CA18F439154ECAD36673A14419BD92C8D0F7AC19BE55B2294E8DBD6FC`
- non-repaint manifest SHA256 `9667661930C7D84D375B6DF9920A9053131840FD805E4130AD26CD68E6DD544F`
- non-repaint audit SHA256 `83C8E789AA223D49FE66C6205C87590A2ED7627B2C7FB5987DCCD864F9F58A4D`, verdict `PASS`
- source-contract test SHA256 `14562AA0B54E8587297F4F703D01B63D29B984A1BE8CE7D24D670EA79EFE90C2`; focused result `14 passed`
- journal-budget proof SHA256 `C9144F5C20ADA902D44A1315EE7CC318BF9AEE2E8E75ED36393C362371B2488E`
- AlphaFactory source SHA256 `B5AFD1B4478532A284B4B2C53B2AB7E200FC3C2D0D1A7D27EB9D4BE41DA8E226`
