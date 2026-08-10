# HYP-STBS-XAUUSD-M15-012 — pre-run contract failure

## Verdict

`PARK_PRE_RUN_CONTRACT_RECEIPT_AND_COST_WINDOW_UNFROZEN_NO_MT5_NO_ECONOMICS`

HYP012 did not reach compile, MetaTrader 5, source data, orders, deals, returns, PF, or any other economic output. The direct AlphaFactory invocation stopped before execution with:

`ContractReceipt is required for backtest evidence.`

The failed command was a preflight mistake, not a consumed MT5 experiment. No AlphaFactory run directory or HYP012 attempt evidence root was created.

## Exact blockers

1. The screened registry row authorized a Model-0 TRAIN falsification but did not bind a task packet or AlphaFactory contract receipt. The row also set `packet_build_authorized=false`, so a receipt could not legally be minted under the same hypothesis after the failure.
2. The seven-field generic registry acceptance contract does not fully encode the preregistered minimum trade count, direction balance, yearly concentration, positive expectancy, or no-negative-year gates. Those exact gates need a report-bound supplemental contract.
3. The frozen tester preload is `2005.01.01–2023.01.01`, while verified research cost coverage is `2018.01.02–2022.12.30`. The current integrated research loop incorrectly requires those windows to be identical. Relabeling the historical cost evidence as covering 2005–2023 would be false.
4. A deterministic report-bound cost artifact must state how the tester result and external spread, commission, and latency proxy are combined so that spread or commission is not silently double-counted.

## Failure radius

This parks only the HYP012 pre-run authorization package. It says nothing about the EA's market edge, PF, expectancy, or cost robustness. HYP011 engineering parity remains valid. A fresh child may reuse the byte-identical EA after freezing an integrated task packet, receipt, supplemental gates, and distinct preload/economic windows.

