# HYP-STBS-XAUUSD-M15-020 Model-0 baseline preregistration

Status: frozen before task-packet build, MT5 execution, report/lifecycle read or performance analysis.

## Thesis and lineage

HYP020 is a fresh economic child of terminal HYP019. It corrects only the research-cost provenance schema that the HYP019 dry-run rejected before any attempt claim or MT5 access. V7 is a mechanical identity revision of the reviewed V6 implementation: only version/name, hypothesis/variant and magic change; all signal, ATR, geometry, FSM, sizing, account-safe margin, restart and lifecycle logic remain unchanged. Its identity is HYP020, magic `5604120` and variant `STBS_H1_FLIP_M15_BURST_TRADE_V7_ACCOUNT_SAFE`.

Parent HYP019 terminal raw-row SHA256 is `F5A1072893D887E0E8A6EDF3538DC85F4D8B37222CF27A5A4DBDEDADF7C0FBC1`. Same-ID HYP019 retry is forbidden. HYP020 is not an engineering-only hypothesis: it authorizes preparation for one untuned economic baseline after engineering gates pass.

Frozen implementation evidence: source `B49D1CA7868B723C10B12A23D2C07CA1DF5F2A0BB86B0860C05FD34CE0F03750`; EX5 `E8FDDC9B96FD796C014C7CE482E7BADAA2D5EAB65BB328CE68FA34C6D7E6301C`; compile log `E225C1BEDF0D7DEFB9E7D31751B83183BE1858A431BAF2DCCC3E072C9E6E83B3` with 0 errors and 0 warnings; EA contract `891E6636F45B263F6163F5E703C9E87B912846B114CE25D5E45517871FD28057`; non-repaint manifest `B7E577EA409D59D7F544D3F074186745EF30D23D0A074249302196C01AA391CC`; non-repaint audit `F9FBE6B857B3FDEEFB4BA894B4B5F89E53EE5C527BE71D36CD21B620EE3B318A`; V6/V7 diff proof `35DF6A7C0781CA4A68C9DF09D014CF7A43AA4FA39F9B5A5D5D6C32C71E298714`; focused test `3CE80E99EAF30FF84B95496291665317BCBB0A6BD62CD9D623F3FDD693C4138C` with 5 passing tests; corrected cost manifest `14BA26C7C7140EEEFBD6046DB9C22F6DBB9181922233DC7AADADD379AF29A2C0`.

## Frozen execution

- Outer and inner hypothesis: `HYP-STBS-XAUUSD-M15-020`.
- EA/package: `EA_SupertrendBurstScalperTradeV7`.
- Symbol/chart: XAUUSD M15; closed-bar signals only.
- Tester preload: 2005.01.01 through 2023.01.01; Supertrend state advances over the full preload.
- Economic scoring: inclusive 2018.01.02 through 2022.12.30 only; no trade outside this window is admissible.
- Model 0, ExecutionMode 0, FixedDelay 0, nonvisual, timeout 900 seconds.
- Deposit 100000 USD, leverage 1:100, semantic spread `current`; omit the AlphaFactory CLI `-Spread` argument.
- Telemetry: `trade-only`, lifecycle-v3.
- Exactly one attempt: `STBS020-MODEL0-TRAIN-001`; no retry.
- Exact overrides: `InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-020;InpMagic=5604120;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V7_ACCOUNT_SAFE`.

## Engineering-first acceptance

Before PF or returns are accepted: exactly one new run; run-local source/EX5/config/compile identity; 0 errors and 0 warnings; HQ greater than 97; exact B326 data and 100k account fingerprints; unique RunMeta with HYP020 identity, audit false and runtime_failed false; lifecycle row count exact; every owned report deal and position reconciled including partial fills, fees, commission and swap; exactly one final close for every opened position; zero orphan/pending exposure, stop-out or emergency exit; and zero trades outside the scoring window. Any failure terminalizes HYP020 without an economic verdict.

## Frozen economic falsification gates

- Research-proxy costs use the exact corrected HYP020 manifest; no numerical cost assumption changed from HYP019.
- Completed trades at least 500.
- Cadence 2 to 5 completed trades per inclusive calendar week.
- LONG and SHORT each at least 30% of trades; no calendar year above 30% of trades.
- Mean x1 net R strictly positive and every calendar year 2018-2022 positive at x1.
- PF after x1 costs strictly greater than 1.30; x1.5 PF at least 1.25; x2 PF at least 1.00.
- Maximum drawdown at most 8%.

This single baseline is not optimization. Optimization, WFA, OOS, holdout, Monte Carlo, paper, live, promotion and market-edge claims remain forbidden. The research proxy can falsify the baseline but cannot promote it.
