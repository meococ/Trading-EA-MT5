# Path A — Real QFSI Login Blocker — 2026-07-14

Status: `BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN`  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`

## What was checked

| Check | Result |
|---|---|
| Active MT5 `common.ini` Login | `108623344` |
| Active MT5 `common.ini` Server | `MetaQuotes-Demo` |
| `FivePercentOnline-Real` string in Terminal config / `accounts.dat` | **Absent** |
| Prior probe `preflight/v4_data/20260713_MT5_READONLY_PROBE_V2.json` | `observed_server=MetaQuotes-Demo`; `server_match=false`; verdict `BROKER_SERVER_MISMATCH` |

## Implication

- Demo / Strategy Tester `current` may continue as **research-proxy** screens.
- Agents **cannot** invent Real credentials or claim broker-verified cost.
- SB+Spark offline compose (`PROBE_NEAR_GOAL_CADENCE_AND_PF_BUT_COST_UNCONFIRMED`)
  remains **not confirmed** until Real QFSI bundles exist.

## Owner-physical unblock

1. Login MT5 to `FivePercentOnline-Real` (no live orders required).
2. Authorize read-only QFSI capture for EURUSD / GBPUSD / XAUUSD / USDJPY as
   contracted.
3. Reprice parked SB A1 (`20260714_002505`) first, then Spark, under verified cost.
