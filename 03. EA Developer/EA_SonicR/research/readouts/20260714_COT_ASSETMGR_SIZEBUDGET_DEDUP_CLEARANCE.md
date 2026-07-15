# De-dup Clearance — HYP-RR2-CFTC-JPY-ASSETMGR-SIZEBUDGET-001

## Against
- Killed z-gate: `HYP-RR2-CFTC-JPY-LEVMONEY-ZGATE-001` (skip-gate on |z| lev-money)
- Killed lev-money size: `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001` (size on |net_lev_money|)

## Why not a clone
| Axis | LevMoney size (killed) | AssetMgr size (this) |
|---|---|---|
| Trader category | Leveraged Money | Asset Manager / Institutional |
| Panel field | net_lev_money | net_asset_mgr |
| Score | |net_lev| percentile | |net_am| percentile |
| Semantics | SIZE BUDGET | SIZE BUDGET (same family, different exogenous category — learning object) |

Cleared: different CFTC category; same size-budget mechanism by design to test category transfer after lev-money stress fail.
