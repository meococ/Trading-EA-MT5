# Readout — HYP-SB-MAXKZ2-EURUSD-TRANSFER-001

Date: 2026-07-14  
Run: `20260714_194007`  
EA: `EA_SilverBullet`  
Verdict: **`KILLED_AT_MODEL_0`** (transfer fail)

## Metrics (tester `current`)

| Metric | Value |
|---|---|
| Symbol | EURUSD M15 |
| Overrides | MaxKZ2 verbatim (`InpMaxTradesPerKZ=2` + weekend flat) |
| Trades | 576 |
| PF | **0.99** |
| Net | −$186 |
| Max DD | ~1.80% |
| tpw elapsed | **~2.21**/wk |

Cadence inside band; PF kill. USDJPY MaxKZ2 geometry does **not** transfer to EURUSD
(parallel to SparkGBP non-transfer).

## Do not

Retune KZ/hours/days from EURUSD losers; densify USDJPY MaxKZ2 as rescue of this kill.

## Cost

`UNVERIFIED_TESTER_DEFAULT`. Not confirmed.
