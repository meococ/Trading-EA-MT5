# HYP-MULTI-TSMOM-D1-003 — source/account gate failure

Status: `KILL_EXACT_NINE_ASSET_CELL_SOURCE_CADENCE_FAIL_NO_ECONOMIC_VERDICT`

Run: `02. AlphaFactory/runs/EA_MultiAssetTSMOMD1V3/20260812_052638`

V3 removed the V2 execution churn completely:

- `partial_close=0`, `partial_open=0`, `partial_unwinds=0`;
- `order_send_rejects=0`, `close_rejects=0`, `market_closed_rejects=0`;
- `orders_without_common_readiness=0`, `basket_recomputations=0`.

The exact nine-asset design nevertheless fails before economics for two
independent reasons.

## Source/cadence failure

The run observed 127 Monday snapshots before account termination, but only 105
atomic baskets (`atomic_ratio=0.82677165`). The 22 failures are consecutive from
2018-01-08 through 2018-06-04: at least one member of the fixed universe never
formed a simultaneous <=60-second quote with an open MT5 session during those
Mondays. Relaxing quote freshness or trimming the universe after seeing this is
forbidden.

Local FivePercent `.tkc` inventory confirms that full 2018 real-tick coverage is
not available for the frozen universe. EURUSD, GBPUSD, and USDJPY have files
from 2016; AUDUSD, USDCAD, USDCHF, and BTCUSD begin in 2023, NZDUSD in 2025, and
XAUUSD in 2026. Older D1 histories exist, but they do not prove real tick-level
common execution for the nine-symbol 2018 cell.

## Account stop-out boundary

The journal binds the FivePercent tester account to money-mode thresholds:

`MTS_ACCOUNT_MARGIN mode=1 call=92000.00000000 stopout=90000.00000000 leverage=100`

With the frozen USD 100,000 deposit, the terminal forcibly stopped the test at
balance USD 89,998.83 on 2020-06-15. Consequently, the run covered only 127 of
208 expected Mondays and cannot supply a 2018-2021 economic verdict. Headline
PF 0.6936584299, 945 trades, and net -USD 10,001.17 are forbidden as strategy
evidence.

Changing deposit can avoid the fixed-money account floor, but it cannot repair
the independent 2018 all-nine source failure. This exact hypothesis is killed
at the lawful source frontier. A new hypothesis must use a source-complete
first cell or acquire new point-in-time data under separate Owner authority.
