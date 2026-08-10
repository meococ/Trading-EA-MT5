# HYP-CBRK-XAUUSD-M5-DQ-001 — Frozen zero-trade native MT5 data preflight

Frozen before the sole data-acquisition run. This object exists only to determine whether the exact future `HYP-CBRK-XAUUSD-M5-001` Model-0 baseline window is fully available and to mint the comparable MT5 data fingerprint before any strategy outcome.

- Parent economic hypothesis: `HYP-CBRK-XAUUSD-M5-001`.
- EA: `EA_PTR_T2_DataEpochD0V3`, no-trade collection probe.
- Source path: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/EA_PTR_T2_DataEpochD0V3.mq5`.
- Source SHA256: `07EF04835CC7624FC8632A0B6E1958A754A93205FB679751B4748D45E6EA4B29`.
- EA contract SHA256: `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`.
- Symbol/timeframe: `XAUUSD / M5`.
- Requested fixed window: `2018.01.02` through `2022.12.30`.
- Model: `0`, execution mode `0`, delay `0`, spread `current`.
- Deposit/leverage: `100000 USD / 1:100`.
- Telemetry profile/tier: `none / off`.
- Exact overrides: `InpCollectionOnly=true;InpEpochManifestSha256=AEBB0EC6AEBEBE5D0ECA81FC42CB1765CF67835BA1FC134D12827E7B87C3A43E;InpExpectedTimeframe=5;InpGenerationId=T2;InpHypothesisId=HYP-CBRK-XAUUSD-M5-DQ-001`.

Acceptance is data-only:

1. Strategy Tester History Quality strictly greater than `97%`.
2. Tester journal bounds exactly cover the requested window without truncation.
3. Coverage class is `fixed_window`, symbol `XAUUSD`, period `M5`, model `0`.
4. Series proof is synchronized, CopyTime from the first available M5 epoch returns exactly one bar with zero last error, and first epochs reconcile.
5. Report bar population must equal the frozen native source count for the same inclusive dates, subject only to a documented tester boundary convention. The intended exact reference is the FivePercent native M5 source SHA `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`; any incomparable or materially incomplete population fails closed.
6. Zero orders, zero strategy deals, zero trades, zero returns, zero PF, zero performance analysis, and no economic claim.

The sole allowed action is one AlphaFactory `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE` control run. Same-ID retry, source/parameter change, Model-4 substitution, strategy execution, validation, holdout, optimization, paper, live, and promotion are forbidden.
