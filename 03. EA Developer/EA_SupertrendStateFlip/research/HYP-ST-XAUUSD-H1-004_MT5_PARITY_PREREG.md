# HYP-ST-XAUUSD-H1-004 — Frozen AlphaFactory MT5 full-bar parity audit

Status: `FROZEN_PRE_COMPILE_PRE_MT5_ENGINEERING_ONLY`  
Parent: `HYP-ST-XAUUSD-H1-003` (`PARK_CORRECTNESS_PASS_HANDOFF_TO_FRESH_MT5_PARITY_CHILD_NO_ECONOMICS`)  
Candidate EA: `EA_SupertrendStateFlip`

## Objective and boundary

Prove that one direct MQL5 Supertrend 10/3 state-machine build reproduces the sealed HYP003 source oracle on every comparable closed H1 bar when scheduled by MT5 Strategy Tester. This hypothesis is correctness-only. It authorizes no order, deal, outcome price, return, cost, PnL, PF, drawdown, optimization, validation, holdout, paper or live claim.

HYP004 is a declared engineering revision of the HYP003 MQL source. The only new behavior is the read-only `DATA_EPOCH_D0_SERIES_PROOF` required by AlphaFactory's zero-trade Model-4 collection lane. It does not feed, filter, reset or otherwise change the H1 Supertrend calculation, event state, parity CSV or expected counts. HYP003's original source/EX5/log remain immutable under `ST003-COMPILE-001`.

## Frozen parents and implementation

- HYP003 terminal registry row raw SHA-256: `040144A5DBE29F905A28E2DC99B7B26B1B332D175DD8B46BA91203125BD209D5`.
- HYP003 oracle attempt start/oracle/report/receipt/terminal SHA-256: `54ED6C2FF92C9B98C7AF447F2C44672723193E9182B59DEC3BC8A26FB2F4A01E` / `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096` / `53D23C61A6CC2005B0587834A500F47860EF2104912BD7D61FDA05C52242CFC9` / `56DC6CBD39721002F892AE9981A47FF397455F57B744277C2C9A3F13EF0C621B` / `7CCB8FE8C33F3369522C93E78B6B12CBAD79FEB408B399827041E6F2EF650396`.
- HYP003 immutable compile source/EX5/log/receipt/terminal SHA-256: `C4C2A0A700434A2C104551D9AD33ECB8893ACB887E25C6E2E045F4A94638A32E` / `F446A86B86294B8E244173F545E989C664C4BCEB5F79885247B7D0EF8593A06A` / `F640411BAD680146289741EF839FFDBFAF8E68383ACEA519BA8A7EBC8C81837E` / `5537AD04B6945027B7552791ADBF3F3B133D6CAE6AFF582C870FC3E4DB2638C9` / `AC0639C649A878CAB29F2B3BB16C18153A02CBFEDE938B3E1FDA4438B0E7F564`.
- HYP004 MQL source: `03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5`, SHA-256 `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`.
- One-shot static compile runner: `run_st004_static_compile.py`, SHA-256 `7274527DEF9A1F082558959FEEF2BC6B5DDB06B182340EA0FDF8C815CE84152F`.
- Claim-before-MT5 launcher: `run_st004_mt5_parity.py`, SHA-256 `0B3DDBF7E03C2CF5B76CF6290620E9CFA0963564F8429EE2C7527A7E918D0090`.
- Comparator: `compare_st003_mql5_parity.py`, SHA-256 `1D1D52C739B563981B252A7E659D9251BC4A90036BA7B4F290FD29AB73FA9772`.
- Post-run collector: `collect_st004_mt5_artifacts.py`, SHA-256 `C84724BA660AA17836FC5267BD3BE531516E7C21BD6A05ADE1D52BE780534B8F`.
- HYP003 parity tests: `tests/test_st003_mql5_parity.py`, SHA-256 `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`.
- HYP004 harness tests: `tests/test_st004_mt5_artifacts.py`, SHA-256 `AB4C0BF0464C704AFB91F0EEEC5D42C1CCDF13BA5DA7C774097F37D964B2C606`.
- AlphaFactory runner / report parser / non-repaint auditor SHA-256: `758D0185A862E023309F7D1A9DFF5970072D71F310975AFCE526CD6E5965F93F` / `A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B` / `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`.
- Zero-trade cost boundary manifest: `HYP004_COLLECTION_ONLY_COST_SOURCE_MANIFEST.json`, SHA-256 `96240602E57C4196E558798633CA1A91A4CEFA735024615754EA065B38C4390F`.

The direct formula, initial `DOWN` state, TR/SMA10/Wilder-RMA operation order, strict band comparisons, upper-first coincident-band identity, flat-bar acceptance, no rounding and chronological gap handling remain exactly those frozen in HYP003. The audit identity and CSV schema remain HYP003 because HYP004 tests that implementation against the HYP003 oracle.

## Authorized phase sequence

1. After independent static review and an initial registry probe, run exactly one AlphaFactory static compile for the HYP004 source. Immediately archive source/EX5/log with a truthful one-shot receipt and terminal; require 0 errors and 0 warnings.
2. Build the exact control task packet/execution receipt and run the collection-aware non-repaint audit. The sole permitted `CopyTime` is the exact non-decision first-date proof under `DATA_ACQUISITION_ONLY_NO_PERFORMANCE` authority.
3. After independent review of the compiled archive, receipt, non-repaint audit and run harness, append the second and final pre-run `state=probe` authority row binding their exact hashes.
4. Confirm the frozen `FILE_COMMON` target does not exist. Do not delete, truncate or overwrite it.
5. `ST004-MT5-001` must write an exclusive/fsynced attempt marker before invoking AlphaFactory. Execute exactly one AlphaFactory Model-4 audit, then exactly one `ST004-ARTIFACT-COLLECT-001`, then exactly one `ST004-COMPARATOR-001`. Each stage has an independent limit of one and an unconsumed metric; any failed/crashed stage is consumed with no same-ID retry.

No source Parquet may be reopened by HYP004. The comparator uses only the sealed HYP003 oracle and MT5 artifacts.

## Exact AlphaFactory invocation contract

- EA / symbol / timeframe: `EA_SupertrendStateFlip` / `XAUUSD` / `H1`.
- Window: `2018.01.01` through `2023.01.01`.
- Model / execution / fixed delay: `4 / 0 / 0`.
- Role / telemetry profile / tier: `control / none / off`.
- Deposit / leverage / spread: `10000 / 100 / current`.
- Timeout: `1800` seconds.
- Required sidecars and indicator dependencies: empty.
- Overrides, byte-for-byte: `InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpEnableTelemetry=false;InpParityFileName=ST003_MQL5_PARITY_001.csv`.
- Receipt authority: `DATA_ACQUISITION_ONLY_NO_PERFORMANCE` with fixed-window `History Quality >97`, exact journal bounds and M5/M1 first-date series proof. This witness establishes terminal data provenance only; it is not an economic or formula input.
- Frozen common filename: `ST003_MQL5_PARITY_001.csv`.

Model 4 is only a completed-H1 scheduling mechanism. The EA contains no trade API and `OnTester()` remains a constant zero.

## Evidence sealing

AlphaFactory must bind the exact source snapshot, run EX5 snapshot, staged tester EX5, config, report, zero-trade summary, data-quality gate and run-local `logs/tester_journal_delta.log`. Immediately after the run, `ST004-ARTIFACT-COLLECT-001` must:

- verify the exact run manifest/invocation, reviewed EX5 hash, zero-trade report context and data-quality journal binding;
- accept only the newly created exact `FILE_COMMON` CSV and exactly one contemporaneous tester journal containing one clean frozen summary and no `ST003_FATAL`;
- verify 29,460 rows, 690 raw, 683 executable, seven gaps, 339 LONG and 344 SHORT;
- seal CSV, tester journal and the contemporaneous 0-error/0-warning compile log into the canonical run directory without overwrite;
- bind the run EX5 snapshot and source-to-copy hashes in an exclusive receipt/terminal.

`ST004-COMPARATOR-001` then consumes only those canonical run-local artifacts and the sealed HYP003 oracle. It must use an exclusive attempt marker, deterministic replay and receipt/terminal hash chain.

## Pass gates

All gates are conjunctive:

1. Reviewed static compile and the automatic run compile both prove 0 errors / 0 warnings, and the reviewed, snapshotted and executed EX5 hashes are identical.
2. Collection-aware non-repaint audit passes with no finding; no order/deal API exists.
3. Exact AlphaFactory manifest, receipt, Model-4 window, overrides, data-quality contract and canonical run-local provenance pass.
4. Tester report has exactly zero deals and journal has exactly one clean `ST003_SUMMARY` in the sealed selected tester log, no `ST003_FATAL`.
5. Oracle/MQL schemas and identities are exact; 29,460 unique increasing source epochs match with no missing/extra row.
6. Integer/state/event/direction fields match exactly on every row.
7. ATR10/final-upper/final-lower/Supertrend absolute error is `<= max(1e-10, 1e-12*abs(expected))` on every row.
8. Counts match 690 raw / 683 executable / seven gaps / 339 LONG / 344 SHORT.
9. Comparator replay is byte-identical; receipts/terminals bind every input/output; zero orders/trades/outcome/economic counters.

Any failure is an exact HYP004 engineering/parity failure and requires a fresh revision. A full pass yields only `ENGINEERING_VALID_DIRECT_MQL5_MT5_PARITY_PASS`; it authorizes a separately preregistered economic child, not economics itself.
