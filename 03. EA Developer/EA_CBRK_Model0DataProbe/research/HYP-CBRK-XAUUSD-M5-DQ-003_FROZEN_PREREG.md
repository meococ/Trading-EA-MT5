# HYP-CBRK-XAUUSD-M5-DQ-003 - frozen exact-window zero-trade Model-0 DQ

Frozen before compile and before the sole AlphaFactory data-acquisition run. This child exists only because terminal DQ002 bound a Model-4 epoch manifest to a Model-0 authority. It may inspect native MT5 data quality only and cannot execute the CBRK strategy or evaluate outcomes.

- Parent strategy: `HYP-CBRK-XAUUSD-M5-002`.
- Failed engineering predecessor: `HYP-CBRK-XAUUSD-M5-DQ-002`.
- EA/source: `EA_CBRK_Model0DataProbe` / `03. EA Developer/EA_CBRK_Model0DataProbe/EA_CBRK_Model0DataProbe.mq5`.
- Source SHA256: `C6D1102894AB94A18DF6B9A04C523652A26D8211A9972A9517918CD209C1D25D`.
- EA contract SHA256: `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`.
- Scoped epoch manifest: `03. EA Developer/EA_CBRK_Model0DataProbe/research/CBRK_DQ003_MODEL0_EPOCH.json`.
- Scoped epoch manifest SHA256: `ACF4E34FC3885EA00CD776DF73B54EB676952E0F39955CD346591F61B43440F5`.
- Symbol/timeframe/window: `XAUUSD / M5 / 2018.01.02-2022.12.30`.
- Model/execution/delay/spread: `0 / 0 / 0 ms / current`.
- Deposit/leverage: `100000 USD / 1:100`.
- Telemetry: `none / off`.
- Expected report population: exactly `351303` bars. Any other count fails; no boundary reinterpretation is allowed.
- History Quality: strictly greater than `97%`.
- Exact tester bounds, synchronized series, exact first-epoch CopyTime proof, nontruncated journal and frozen broker/server/account/data fingerprints are mandatory.
- Orders, strategy deals, trades, returns, PF, performance analysis and economics must all remain zero/absent.

The source delta from the reviewed V3 probe is limited to package/header identity, generation identity `CBRK-DQ003`, and the Model-0 epoch-manifest SHA at the input default and fail-closed Configure comparison. The probe still has no OrderSend, no trade lifecycle and no telemetry sidecar.

Exact overrides:

```text
InpCollectionOnly=true;InpEpochManifestSha256=ACF4E34FC3885EA00CD776DF73B54EB676952E0F39955CD346591F61B43440F5;InpExpectedTimeframe=5;InpGenerationId=CBRK-DQ003;InpHypothesisId=HYP-CBRK-XAUUSD-M5-DQ-003
```

Exactly one registry-authorized `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE` run through the existing `research_loop_engine.ps1` is permitted. The standard research lock, task packet, execution receipt, transition log and run-local manifest are the evidence surface; no HYP-specific wrapper is allowed. Same-ID retry, strategy execution, costs, validation, holdout, optimization, paper, live and promotion are forbidden.
