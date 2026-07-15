# Deliverable — Owner MT5 auth + QFSI continuation

Created: 2026-07-14T16:25:00Z
Owner auth (VI): freely open/close/restart MT5 unless another backtest is live; login confirmed.
Primary arc: `BLOCKED_OTHER_PROGRESS` → (slot free) → `REAL_VERIFIED__CAPTURE_005_RUNNING`
Full QFSI / confirmed reprice: still **`CAPTURE_INCOMPLETE`** / **`STOP_DATA_FRONTIER`**
MT5 restarted this session: **false**
Live orders: **0**

## Timeline

1. **Pre-restart gate:** live AlphaFactory backtest detected —
   `HYP-SB-MAXKZ2-RR2-FRICTION-001` challenger (`alpha.ps1` PID 12640,
   `terminal64` 48032, `metatester64` 42164, run `20260714_231750`, lock held).
   Hard exception applied → **MT5 not killed/restarted**.
2. **After challenger report landed + lock cleared:** readonly probe V7
   observed `FivePercentOnline-Real` login **26451822**, match=true,
   orders/positions 0, connected=true.
3. **Capture:** launched `20260714_QFSI_REAL_005_POSTAUTH` PID **35892**
   (duration 3600s, poll 2000ms, read-only). Quotes/heartbeats accumulating.

## Account

| Field | Value |
|---|---|
| Expected | `FivePercentOnline-Real` |
| Observed | `FivePercentOnline-Real` |
| Login | 26451822 |
| Probe | `TARGET_SERVER_READONLY_PROBE_COMPLETE` |
| Probe path | `preflight/v4_data/20260714_MT5_READONLY_PROBE_V7_OWNER_AUTH_QFSI.json` |
| Probe SHA256 | `BEEC29088654E4CDD67A837013C5929D5B5475DBC351F433070461A259F794CE` |

## Gaps (unchanged blockers)

| Gate | Have | Need |
|---|---|---|
| Eligible hash-bound bundles | 0 | ≥1 |
| Inventory QFSI | `STOP_DATA_FRONTIER` | not STOP |
| USDJPY commission lifecycles | 0 | ≥30 |
| EURUSD commission lifecycles | 2 | ≥30 |
| Slippage fills / symbol | 0 | ≥100 (MISSING ≠ 0) |
| Quote elapsed days | ≪90 | ≥90 |
| owner_deal_export_drop new files | 0 | Account History export |

Inventory V7 SHA256: `59A7407B23D4EC6963BD24C253B37E2483A75541154F931D4B89FF89F42F8058`

## Reprice

**Not upgraded.** No new commission/slippage evidence vs prior partial Real P50 ~$2.31 / aggregated ~$2.62.
MaxKZ2 `20260714_192304` prior FAIL under partial Real cost stands. Do **not** densify. Not confirmed / not GOAL.

## Artifacts

- Blocker receipt (decision-time): `preflight/20260714_QFSI_OWNER_AUTH_BLOCKED_OTHER_PROGRESS_RECEIPT.json` SHA `D1D1A4B21BFD979203824C5110AFF88B648431F2D65ED8E2B03C5766535BBBC5`
- Post-auth inventory snapshot: `preflight/20260714_QFSI_POSTAUTH_CAPTURE_INVENTORY.json`
- Inventory V7: `preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V7.json`
- Live capture: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_QFSI_REAL_005_POSTAUTH/`
- Stop file: `…/STOP_QFSI_CAPTURE.flag` (absent while running)

## Next Owner action

1. Leave Real logged in; let capture `005_POSTAUTH` finish (~1h) or keep extending overnight.
2. Drop Account History (All History, with Commission) into `owner_deal_export_drop` until USDJPY/EURUSD commission ≥30 each.
3. Side-referenced slippage fills still required for full QFSI — cannot invent from quotes.
4. Do not claim confirmed / validate-full until inventory eligible ≥1.
