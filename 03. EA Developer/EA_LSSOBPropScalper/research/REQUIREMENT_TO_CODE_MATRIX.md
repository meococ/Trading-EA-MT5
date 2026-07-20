# Requirement-to-Code Matrix - HYP-LSS-OB-REPL-EURUSD-M15-001

This matrix is frozen with the no-outcome probe plan. `planned_exact` means the
probe must implement the row exactly before its artifact can be interpreted.

| Requirement | Frozen quantitative rule | Probe state | Planned surface |
|---|---|---|---|
| EURUSD M15 decisions | UTC M1 resampled to closed M15; decision at close | `planned_exact` | `resample_ohlc`, `run_detector` |
| H1 BOS bias | Strength-2 confirmed pivots; latest closed-bar break direction | `planned_exact` | `context_frame` |
| H4 premium/discount | Latest confirmed pivot range brackets price; midpoint 50% | `planned_exact` | `context_frame` |
| Sessions | M15 opens 07:00-10:00 or 13:00-16:00 UTC | `planned_exact` | `session_id` |
| Liquidity sweep | Latest confirmed same-side M15 pivot in preceding 20 bars; wick through and close inside | `planned_exact` | `detect_sweep` |
| Displacement | Within 3 bars; directional body >=1.8 x `atr_mt5(14)` | `planned_exact` | `advance_setup` |
| Strict FVG | Bull `low[i] > high[i-2]`; bear inverse | `planned_exact` | `strict_fvg` |
| Order block | Last opposite candle since sweep; body overlaps FVG | `planned_exact` | `find_order_block` |
| Freshness/invalidation | Intermediate adverse-wick close invalid; later close past sweep invalid | `planned_exact` | `advance_setup` |
| Control | Decision-ready at displacement close with common gates | `planned_exact` | `control_event` |
| Challenger retest | First overlap touch within 12 bars and same killzone | `planned_exact` | `advance_setup` |
| Confirmation | Engulfing or body/range >=0.60 with close in directional outer 25% | `planned_exact` | `is_confirmation` |
| ADX | Closed M15 `adx_mt5(14) >25.0` | `planned_exact` | `common_gates` |
| News | Bound EUR/USD source-C calendar; inclusive +/-30 minutes | `planned_exact` | `NewsGuard` |
| Stop geometry | Farther of sweep/OB adverse wick +1.5 pip; first quote distance 8-12 pip | `planned_exact` | `decision_geometry` |
| Single active setup | Ignore new sweeps until ready/expiry/invalidation | `planned_exact` | `SetupState` |
| No outcome | No forward result, fill, PnL, stop/target result, MFE/MAE or 2023+ bars | `planned_exact` | schema validator/tests |
| Cadence | Inclusive elapsed calendar weeks; pooled and split counts | `planned_exact` | `density_summary` |
| Identity | Report/data/news/prereg hashes and deterministic event IDs | `planned_exact` | artifact metadata |

No `.mq5`, Model 0, cost economics, WFA, Monte Carlo or FTMO pass simulation is
authorized by this matrix. Those surfaces exist only after `DENSITY_FEASIBLE_ONLY`.
