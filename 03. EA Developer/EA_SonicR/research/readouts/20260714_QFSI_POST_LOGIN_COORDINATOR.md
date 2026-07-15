# QFSI Post-Login Coordinator — 2026-07-14

Status: **`REAL_CONFIRMED_CAPTURE_RUNNING`**  
Process: GPT waived · nested `cursor-grok-4.5-high-fast` · no-Git · no densify  
GOAL claim: **false** · confirmed claim: **false**

## Verdict

Owner Real login confirmed. Read-only probe V4 sees exact server
`FivePercentOnline-Real` (`TARGET_SERVER_READONLY_PROBE_COMPLETE`).  
No-live QFSI capture has been **explicitly started**.  
MaxKZ2 verified-cost reprice is **not** complete — sample gates still fail-closed.

## Probe

| Field | Value |
|---|---|
| Artifact | `preflight/v4_data/20260714_MT5_READONLY_PROBE_V4.json` |
| SHA256 | `7C38E9DC2166FBAF269ABFB3E34AF30032EE04A3FC0A7CEF7BD1F3FCF3CDF6A3` |
| Expected | `FivePercentOnline-Real` |
| Observed | `FivePercentOnline-Real` |
| `server_match` | **true** |
| Trade allowed | false |
| Orders / positions | 0 / 0 |
| Symbols present | EURUSD, GBPUSD, XAUUSD, USDJPY |

Prior blocker `BLOCKED_NEEDS_OWNER_REAL_LOGIN` / Demo V3 mismatch is **cleared**.

## Capture started

| Item | Detail |
|---|---|
| Tool | `02. AlphaFactory/tools/execution_data_qfsi_nolive_capture.py` |
| Seed ID | `20260714_QFSI_REAL_001` |
| Seed end status | `CAPTURE_WINDOW_COMPLETE_PARTIAL` |
| Manifest SHA256 | `BCE364CB5016359D8401B6F23118209AB24E780D1105FC40E8C99FA4FD7F19AD` |
| Hash inventory | `preflight/v4_data/20260714_QFSI_REAL_001_HASH_MANIFEST.json` |
| Heartbeats / quotes (seed) | 116 / 116 |
| Commission lifecycles | EURUSD **2**; GBPUSD/XAUUSD/USDJPY **0** |
| Slippage fills | **0** (not invented) |
| Continuation | `20260714_QFSI_REAL_003_CONTINUATION` (~30 min, stop via `STOP_QFSI_CAPTURE.flag`) |

Inventory V3: `STOP_DATA_FRONTIER` · eligible bundles **0**  
(`preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V3.json`).

## MaxKZ2 reprice path

Survivor lock unchanged: `HYP-SB-MAXKZ2-DENSITY-002` / baseline `20260714_192304`.

| Step | Result |
|---|---|
| Real probe | PASS |
| Capture start | PASS (partial seed + continuation) |
| Verified cost artifact | **FAIL** — gates unmet |
| Stress / readout under verified cost | **NOT RUN** (fail-closed) |

Blockers: quote elapsed ≪90d · commission ≪30/symbol (USDJPY=0) · slippage missing · no eligible QFSI bundle.

## Next

1. Keep Real login connected; let continuation capture accumulate heartbeats/quotes.
2. Stop explicitly with `STOP_QFSI_CAPTURE.flag` when Owner wants pause.
3. Reprice MaxKZ2 only after hash-bound bundle validates eligible (or Owner supplies equivalent broker execution report with independent pre-send refs).
4. Do **not** densify / day-hour mine / claim GOAL from this login event alone.

## Paths

- Receipt: `preflight/20260714_QFSI_POST_LOGIN_RECEIPT.json`
- Checklist: `preflight/20260714_MAXKZ2_QFSI_REPRICE_CHECKLIST.md`
- Probe V4 / Inventory V3 under `preflight/v4_data/`
- Evidence: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/`
