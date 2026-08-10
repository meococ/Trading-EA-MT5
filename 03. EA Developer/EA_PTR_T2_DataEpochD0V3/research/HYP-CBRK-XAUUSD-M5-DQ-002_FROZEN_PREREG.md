# HYP-CBRK-XAUUSD-M5-DQ-002 — frozen exact-window zero-trade DQ

Frozen before the sole AlphaFactory data-acquisition run. This child may inspect native MT5 data quality only and cannot execute the strategy or evaluate outcomes.

- Parent: `HYP-CBRK-XAUUSD-M5-002`.
- EA/source: `EA_PTR_T2_DataEpochD0V3` / `03. EA Developer/EA_PTR_T2_DataEpochD0V3/EA_PTR_T2_DataEpochD0V3.mq5`.
- Source SHA256: `07EF04835CC7624FC8632A0B6E1958A754A93205FB679751B4748D45E6EA4B29`.
- EA contract SHA256: `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`.
- Symbol/timeframe/window: `XAUUSD / M5 / 2018.01.02–2022.12.30`.
- Model/execution/delay/spread: `0 / 0 / 0 ms / current`.
- Deposit/leverage: `100000 USD / 1:100`.
- Telemetry: `none / off`.
- Expected report population: exactly `351303` bars. Any other count fails; no boundary convention or post-run reinterpretation is allowed.
- History Quality: strictly greater than `97%`.
- Exact tester bounds, synchronized series, exact first-epoch CopyTime proof, nontruncated journal and current broker/server/account/data fingerprints are mandatory.
- Orders, strategy deals, trades, returns, PF, performance analysis and economics must all remain zero/absent.

Exact overrides:

```text
InpCollectionOnly=true;InpEpochManifestSha256=AEBB0EC6AEBEBE5D0ECA81FC42CB1765CF67835BA1FC134D12827E7B87C3A43E;InpExpectedTimeframe=5;InpGenerationId=T2;InpHypothesisId=HYP-CBRK-XAUUSD-M5-DQ-002
```

Exactly one registry-authorized `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE` run through the existing `research_loop_engine.ps1` is permitted. The standard research lock, task packet, execution receipt, transition log and run-local manifest are the evidence surface; no HYP-specific wrapper is allowed. Same-ID retry, strategy execution, costs, validation, holdout, optimization, paper, live and promotion are forbidden.
