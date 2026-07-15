# Broker Cost Provenance Audit

Date: 2026-07-11

Verdict: `COST_PROVENANCE_FAIL / OUTCOME_PROBE_BLOCKED`

This was a read-only audit of the currently connected FivePercentOnline MT5
environment. No tester, order, position, history export, or account mutation
was performed. Raw account identifiers, tickets, and trade rows are not stored
in this artifact.

## Environment

- Python: `C:\Program Files\Python312\python.exe`
- MetaTrader5 package: `5.0.5509`
- terminal build: `5961`
- server: `FivePercentOnline-Real`
- symbols: unsuffixed `EURUSD`, `GBPUSD`, `USDJPY`
- execution mode: Market Execution for all three symbols

## Historical M15 Spread Coverage

Rates were queried in UTC monthly chunks. Every month in train
`2021-2023` and holdout `2024-2025` returned M15 bars. Because a real floating
spread cannot be zero for most of the history, `spread == 0` is treated as
missing rather than free execution. Quantiles below are conditional on
`spread > 0` and are in pips.

| Symbol | Window | M15 bars | Non-zero spread | Coverage | P50 | P90 | P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 2021-2023 | 74,722 | 24,593 | 32.913% | 0.10 | 0.70 | 1.40 | 2.70 |
| EURUSD | 2024-2025 | 49,880 | 1,967 | 3.943% | 1.10 | 2.90 | 4.10 | 12.736 |
| GBPUSD | 2021-2023 | 74,712 | 33,585 | 44.953% | 0.10 | 1.10 | 1.90 | 5.00 |
| GBPUSD | 2024-2025 | 49,881 | 2,104 | 4.218% | 3.80 | 7.20 | 10.085 | 24.70 |
| USDJPY | 2021-2023 | 74,722 | 22,863 | 30.597% | 0.10 | 0.90 | 1.70 | 3.30 |
| USDJPY | 2024-2025 | 49,889 | 2,313 | 4.636% | 2.70 | 6.20 | 7.00 | 10.30 |

These conditional quantiles are not an unconditional broker spread model,
especially in 2024-2025 where coverage is about `4%`. They cannot be used as a
cost override or imputed into the missing bars.

MetaQuotes documents that `copy_rates_range` exposes the bar `spread` field,
uses UTC time, and depends on history available in the terminal:

- [MQL5 Python copy_rates_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)

## Commission Evidence

The full available account history contained only 11 deals and 10 orders.
Commission was grouped by fully closed position lifecycle, requiring matched
entry/exit volume and excluding incomplete or reverse lifecycles.

| Symbol | Trade fills | Closed lifecycles | Non-zero commission samples | Finding |
|---|---:|---:|---:|---|
| EURUSD | 4 | 2 | 2 | Both indicate `USD 4.00` per round-turn lot, but `N=2` is not calibration evidence. |
| GBPUSD | 0 | 0 | 0 | No evidence. |
| USDJPY | 0 | 0 | 0 | No evidence. |

The two EURUSD lifecycles are also concentrated in two days in July 2026.
They are a preliminary clue, not a verified commission model. The preregistered
cost gate requires at least 30 independent, fully closed same-symbol
lifecycles before using history-derived commission.

## Slippage Evidence

Orders and deals were grouped by order ticket and checked for full-volume fill.
The intended side-specific adverse-slippage calculation is:

```text
buy adverse points  = max((fill_vwap - independent_pre_fill_ask) / point, 0)
sell adverse points = max((independent_pre_fill_bid - fill_vwap) / point, 0)
```

EURUSD had four matched market/stop order lifecycles, but none had a defensible
independent pre-fill reference:

- two client Market Execution orders recorded `ORDER_PRICE_OPEN = 0`;
- two stop-loss orders had order price equal to fill VWAP within `0.05` point
  and only `N=2`, so independence cannot be established.

GBPUSD and USDJPY had no target-symbol orders or deals. Usable independent
reference samples are therefore `0` for all symbols, and no P90 adverse
slippage estimate exists.

This is expected under Market Execution: the order price field may be absent
for a market request, while deal price is the execution result.

- [MQL5 order properties](https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties)
- [MQL5 trade request](https://www.mql5.com/en/docs/constants/structures/mqltraderequest)
- [MQL5 deal properties](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties)

## Exact Blockers

- `EURUSD`: missing spread coverage, only two commission samples, zero usable
  slippage-reference samples.
- `GBPUSD`: missing spread coverage and zero commission/slippage samples.
- `USDJPY`: missing spread coverage and zero commission/slippage samples.

Zero/missing fields must never be interpreted as zero cost.

## Reopen Gate

Do not manufacture trades to fill the sample. Reopen cost calibration only
after legitimate activity or a broker-provided source supplies:

- complete historical bid/ask quote ticks for every eligible signal and outcome
  path; bar-level spread alone cannot prove ask high/low barrier touches;
- at least 30 fully closed same-symbol commission lifecycles, or an explicit
  hash-pinned broker/account/symbol commission contract, with per-trade
  contemporaneous quote-to-account conversion (required for USDJPY on a USD
  account; a current tick-value snapshot is invalid);
- at least 100 proactive fills per symbol, including at least 30 buys and 30
  sells, with independently logged pre-send ask for buys and bid for sells.

Until then, no offline outcome probe, EA source patch, compile, MT5 backtest, or
promotion claim is authorized for
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`.
