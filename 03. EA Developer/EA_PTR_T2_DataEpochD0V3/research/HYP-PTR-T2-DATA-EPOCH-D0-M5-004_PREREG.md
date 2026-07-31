# HYP-PTR-T2-DATA-EPOCH-D0-M5-004 Preregistration

## Identity and fresh mechanism

- Hypothesis ID: `HYP-PTR-T2-DATA-EPOCH-D0-M5-004`
- EA name: `EA_PTR_T2_DataEpochD0V3`
- Parent: `CAMPAIGN-PTR-E01/T2 data epoch`
- Mechanism: all-available MT5 **real-tick** data acquisition using tester `Model=4` (`Every tick based on real ticks`), not HYP003 generated-tick `Model=0`
- Authority: `DATA_ACQUISITION_ONLY_NO_PERFORMANCE`
- Predecessor closeout: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/HYP-PTR-T2-DATA-EPOCH-D0-M5-003_DATA_QUALITY_CLOSEOUT.json`
- Predecessor closeout SHA256: `A986A5E6E7F6223CC1B2DFFE22B1F7EFF2BD91ABB4D2167E691D0B16B0E18FE6`
- This is a fresh data-generation/fidelity contract opened before any HYP004 run. It does not change a trading rule, inspect PnL, or rescue HYP003 in place.

## Frozen data contract

- Server: `FivePercentOnline-Real`
- Mandatory symbols, exact order, no skip: `XAUUSD`, `BTCUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`, `NZDUSD`
- Timeframe: `M5`
- Tester model: integer `4`
- Requested From sentinel: `1970.01.01`
- Requested To: `2026.07.30`
- Availability cutoff UTC: `2026-07-30T23:59:59Z`
- History Quality: strict `>97.0`
- Epoch contract: `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH_V2.json`
- Epoch contract SHA256: `88F6281385DED567E05B23BB6347F2A91B768C8B5653DAC394751D06003901C8`
- Evidence ledger: `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EVIDENCE_V2.jsonl`

## Source and capability binding

- Canonical source: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/EA_PTR_T2_DataEpochD0V3.mq5`
- Source SHA256: `EB9273BC7F1E0A5C7DB420916EC43CA3EE2A9BAE932D9C2101E4B85058FED70F`
- EA contract: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/ALPHAFACTORY_EA_CONTRACT.json`
- EA contract SHA256: `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`
- Telemetry profile/tier: `none` / `off`
- Run role: `control`
- Required sidecars: `[]`
- Collection only: `InpCollectionOnly=true`

## Fatal gates per symbol

Each symbol requires one independently selected PASS row. Missing or partial evidence is invalid, not a market failure.

1. Task packet, execution receipt, source, prereg, epoch contract, cost manifest and all declared hashes must match before MT5.
2. Packet, receipt, config snapshot and run manifest must all bind integer `model=4`; any other model is fatal.
3. The tester journal must explicitly identify real-tick execution with a case-insensitive `real ticks` marker. Absence of that readback is fatal even if the packet says Model 4.
4. MT5 report History Quality must be strictly greater than `97.0` and must equal the manifest data-quality gate.
5. Journal history synchronization must end at `2026.07.30`. The requested `1970.01.01` sentinel means MT5 is asked for all history available under this real-tick mode; a broker-limited start is accepted only when the run-local journal and series proof agree and no terminal-cache truncation is detected.
6. `DATA_EPOCH_D0_SERIES_PROOF` must be unique and valid: synchronized M5, positive first epochs, `CopyTime` count/result `1`, error `0`, and `copytime_from_epoch == copytime_first_epoch == m5_first_epoch`.
7. Exactly zero trades; zero-trade collection summary only. Any deal/order/position activity, PnL field authority, performance sidecar, or economic metric is fatal.
8. Receipt/manifest must bind the current broker, server, account, symbol geometry and data fingerprints. Identity discovery runs may only rebind a future packet; they cannot be selected evidence.
9. Aggregate readiness requires `9/9` selected PASS rows. No symbol substitution and no partial promotion.

## Sequential stop rule and fallback

- Run the exact nine-symbol HYP004 epoch serially under the AlphaFactory global lock.
- If any symbol cannot satisfy real-tick readback or `History Quality >97`, park HYP004 with the exact symbol/data failure radius; do not call no-edge.
- Only after that terminal closeout may a fresh ID preregister the original fixed economic window `2018.01.01..2026.07.30`. The date rule must be frozen before those runs and cannot depend on PnL.
- If the fixed 2018 real-tick epoch still cannot produce 9/9 valid symbols, a broker/data-source change is an Owner scope decision.

## Explicit non-authority

This prereg authorizes no trading, PF, WR, expectancy, optimization, validation, holdout, promotion, paper trading or live trading. It only tests whether the mandatory MT5 data epoch is fit for later research.
