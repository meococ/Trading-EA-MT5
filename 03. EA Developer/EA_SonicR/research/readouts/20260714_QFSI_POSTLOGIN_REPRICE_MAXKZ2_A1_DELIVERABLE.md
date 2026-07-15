# Deliverable — Post-login QFSI / MaxKZ2+A1 cost reprice

Created: 2026-07-14T15:05:50.436919Z
Owner signal: `đã login`
Primary verdict: **`CAPTURE_INCOMPLETE`**
Partial diagnostic: `PARTIAL_DIAGNOSTIC_MAXKZ2_FAIL`
GOAL / confirmed claims: **false**
Validate-full recommended: **false**

## Account probe

| Field | Value |
|---|---|
| Expected | `FivePercentOnline-Real` |
| Observed | `FivePercentOnline-Real` |
| Match | true |
| Probe | `TARGET_SERVER_READONLY_PROBE_COMPLETE` |
| Probe SHA256 | `F84627EF86A2D7ED2C79164A8F16A7240DDFD6F588C004258E657C2A20B259F4` |
| Trade allowed | False |
| Orders / positions | 0 / 0 |
| MetaQuotes-Demo | **rejected** (fail-closed path unused) |

## Capture / inventory status

| Gate | Have | Need |
|---|---|---|
| Eligible hash-bound bundles | 0 | >=1 |
| Inventory QFSI | `STOP_DATA_FRONTIER` | not STOP |
| USDJPY commission lifecycles | 0 | 30 |
| EURUSD commission lifecycles | 2 | 30 |
| Slippage fills / symbol | 0 | 100 |
| Quote elapsed days | <1 day across captures 001-004_EXTENSION | 90 |

Active passive capture: `20260714_QFSI_REAL_004_EXTENSION` (quotes accumulating; commission/slippage still empty for USDJPY).

## Partial Real cost model (diagnostic only)

| Component | Value |
|---|---|
| Symbol | USDJPY |
| Lot P50 | 0.5 |
| Spread USD/lot P50 | 0.617589 |
| Spread USD/lot P90 | 1.235178 |
| Commission clue | $4.00/lot RT (EURUSD N=2, transferred) |
| Slippage | MISSING ≠ 0 |
| Base RT $/trade P50 | **$2.3088** |
| Base RT $/trade P90 | **$2.6176** |

Caveat: additive haircut on tester-current reports may double-count spread already in PnL → conservative.

## Metrics (Real P50 haircut)

| Book | Run | Trades | /wk | Base PF | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---|---|---|---|---|---|---|
| MAXKZ2 | `20260714_192304` | 546 | 2.09 | 1.333761 | **1.275** | **1.246** | **1.218** | FAIL |
| A1 | `20260714_002505` | 520 | 1.99 | 1.344267 | **1.284** | **1.255** | **1.227** | FAIL |
| RR2 | `20260714_194221` | 524 | 2.01 | 1.378321 | **1.323** | **1.297** | **1.271** | PASS |

Campaign survivor MaxKZ2 remains **HIT_RESEARCH_BAR** under tester `current` only; under this partial Real model it does **not** clear GOAL cost-stress (x1 PF must >1.30). A1 weekend-flat reference included same pass. RR2 remains the stronger partial-Real friction sleeve but is **not confirmed**.

## Artifacts

- Receipt: `d:/Trading EA MT5/03. EA Developer/EA_SonicR/research/preflight/20260714_QFSI_POSTLOGIN_REPRICE_MAXKZ2_A1_RECEIPT.json`
- Inventory V5: `d:/Trading EA MT5/03. EA Developer/EA_SonicR/research/preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V5.json` SHA `FC064ED7DB3CFC2F6E3FD5F5AB76A1042C12DD5FBE5271E07B5782F9B1721210`
- Deal import: `d:/Trading EA MT5/02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_DEAL_HISTORY_IMPORT_POSTLOGIN/import_manifest.json`
- Probe V5: `d:/Trading EA MT5/03. EA Developer/EA_SonicR/research/preflight/v4_data/20260714_MT5_READONLY_PROBE_V5_POSTLOGIN.json`

## Next Owner actions

1. Keep Real logged in; continue quote capture overnight.
2. Export Account History (All History) with Commission → `owner_deal_export_drop` until USDJPY/EURUSD commission ≥30 each.
3. Provide side-referenced slippage fills (≥100/symbol) — cannot invent from quotes.
4. Do **not** run validate-full / claim confirmed until inventory eligible ≥1.
