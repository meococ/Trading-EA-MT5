# QFSI Reprice Prep Coordinator — 2026-07-14

Status: **`BLOCKED_NEEDS_OWNER_REAL_LOGIN`**  
Process: GPT waived · nested `cursor-grok-4.5-high-fast` · no-Git · no densify Model 0  
GOAL claim: **false** · confirmed claim: **false**

## Verdict

Live read-only probe still sees **`MetaQuotes-Demo`**, not `FivePercentOnline-Real`.  
No-live QFSI capture was **not** started (Demo would contaminate the Real lane).  
MaxKZ2 reprice packet is **frozen and ready** for the moment Owner logs Real.

## Probe / inventory (this turn)

| Artifact | Result | SHA256 |
|---|---|---|
| Probe V3 | `BROKER_SERVER_MISMATCH` · observed `MetaQuotes-Demo` | `4B3EC9B5B501D21965D95843C8B2B386E176FD27544E1CD68E70648826F27308` |
| Inventory V2 | `STOP_DATA_FRONTIER` · 0 eligible bundles | `B970FCA51C34C13E86D5EB4BBAC68C153BAEB6D926EFF8DA480907CD5CC4ED08` |
| `common.ini` | Login `108623344` · Server `MetaQuotes-Demo` | terminal `D0E8209F77C8CF37AD8BF550E51FF075` |
| Safety | `orders_sent=0` · `trade_allowed=false` · read-only | — |

Demo quote samples exist (EURUSD/GBPUSD/XAUUSD/USDJPY) but are **`UNPROVEN_HISTORY_SAMPLE`** and **non-evidence** for QFSI.

## Survivor reprice lock

- ID: `HYP-SB-MAXKZ2-DENSITY-002`
- Baseline run: `20260714_192304` — PF **1.33** / **546** trades / **~2.09**/wk / net **+$8123** / DD **~0.85%**
- Cost: `UNVERIFIED_TESTER_DEFAULT` only — research-bar hit, **not GOAL**
- Checklist: `preflight/20260714_MAXKZ2_QFSI_REPRICE_CHECKLIST.md`
- Receipt: `preflight/20260714_QFSI_REPRICE_PREP_RECEIPT.json`

## Owner steps (exact)

1. MT5 → **Login to Trade Account** → server **`FivePercentOnline-Real`** (exact).
2. Ensure Market Watch: unsuffixed **EURUSD, GBPUSD, XAUUSD, USDJPY**.
3. No live orders required for capture.
4. Tell agent — agent re-runs:

```powershell
python "02. AlphaFactory/tools/execution_data_foundation.py" probe-mt5 `
  --expected-server "FivePercentOnline-Real" `
  --symbols EURUSD GBPUSD XAUUSD USDJPY `
  --sample-hours 1 `
  --out "03. EA Developer/EA_SonicR/research/preflight/v4_data/mt5_probe_real.json"
```

5. Only if `server_match=true` / `TARGET_SERVER_READONLY_PROBE_COMPLETE`: start **explicit** no-live QFSI capture (quotes + heartbeat; commission/slippage from legitimate fills only — never manufacture trades).
6. When hash-bound bundle validates: reprice MaxKZ2 under verified cost using frozen checklist (same overrides; new `run_id`). Then optional A1 `20260714_002505`.

## Agent next (when unblocked)

| Status target | Condition |
|---|---|
| `QFSI_CAPTURE_RUNNING` | Real login confirmed + capture explicitly started |
| `REPRICE_READY_WAITING_REAL` | Real probe OK but capture not yet complete / not enough sample |
| Reprice Model 0 | Eligible Real cost bundle bound — **no strategy redesign** |

## Hard stops (reconfirmed)

- No densify Model 0 · no day/hour mining from rebuild readouts  
- Do not mix Demo into Real QFSI bundles  
- Missing cost ≠ 0 · no GOAL/confirmed claim from this prep

## Paths

- Receipt: `preflight/20260714_QFSI_REPRICE_PREP_RECEIPT.json`
- Checklist: `preflight/20260714_MAXKZ2_QFSI_REPRICE_CHECKLIST.md`
- Probe: `preflight/v4_data/20260714_MT5_READONLY_PROBE_V3.json`
- Inventory: `preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V2.json`
- Contract: `04. Project Control/ai/data_contracts/20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md`
- Prior blocker: `readouts/20260714_PATH_A_REAL_QFSI_LOGIN_BLOCKER.md`
