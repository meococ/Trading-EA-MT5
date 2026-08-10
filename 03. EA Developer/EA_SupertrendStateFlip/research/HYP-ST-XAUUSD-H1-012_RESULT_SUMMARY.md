# HYP-ST-XAUUSD-H1-012 — comparator result

Status: `PARK_ENGINEERING_VALID_DIRECT_MQL5_MT5_PARITY_PASS_NO_ECONOMICS`

The sole authorized comparator attempt `ST012-COMPARATOR-001` completed and
proved exact bar-by-bar parity between the frozen source oracle and the direct
MQL5 implementation.

## Reconciled result

- Oracle rows: `29,460`.
- MQL5 rows: `29,460`.
- Exact indicator/event/time mismatches: `0`.
- Maximum absolute errors for ATR10, final upper band, final lower band and
  Supertrend: `0.0`.
- Raw flips: `690`; executable flips: `683`; exact-next gap rejects: `7`.
- Executable directions: `339 LONG`, `344 SHORT`.
- Orders, trades, PnL, returns and economic trials: `0`.

The result is strictly an engineering-correctness result. It does not test
entry/exit geometry, costs, profit factor, expectancy or market edge. The
same ID may not be rerun or promoted to economics.

## Immutable evidence

- `attempt_started.json`: `BE3A64AD8F60BB0517B05FF346219E415DD71320A2A858672DBA10136CFC54F3`
- `st003_full_bar_parity_report.json`: `5B031C2BF528718DF4B54DADCB2F937E85EA703F8FC25225D792E1224D9FCD04`
- `st009_full_bar_parity_receipt.json`: `6ED0DDA55598CAAC14D08C328DDB90E16480D64084DB28B8CA968B415D326919`
- `attempt_terminal.json`: `02572F12BB50BC4A3E56C7BF2D17F2449E7A0A20DBD62C32A4571B8F214FCD6B`

