# EA_OnlineRidge_EUR_H1_V12ML

Active `HYP-ORLS-EURUSD-H1-001`: pure-MQL5 causal online recursive least squares on six EURUSD H1 raw microstructure/path features. Each prediction uses only completed bars, every training label matures exactly four contiguous H1 opens later, and all standardization is past-only.

The initial authorized stage is DESIGN `[2018-01-01, 2022-01-01)`. Validation 2022-2023 and holdout 2024-current remain unopened until the preceding gates pass.

The first run `20260812_031618` is engineering-invalid before economics because the ATR24 buffer was one element short. It is preserved as `INVALID_RUNTIME_ARRAY_BOUND_NO_ECONOMIC_READOUT`; the exact runtime-only repair continues under `EA_OnlineRidge_EUR_H1_V12MLR1` / `HYP-ORLS-EURUSD-H1-002`.
