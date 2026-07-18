# READOUT — HYP-KALSHI-MACRO-PRINT-H1-XAU-001

**Terminal verdict:** `KILL_AT_OFFLINE_PROBE`  
**Package:** `EA_KalshiMacroPrint` (research only; **no `.mq5` authority**)  
**Evidence tick:** `.context/cron_20260718_0211/`  
**Run:** `20260718_200326_KALSHI_MACRO_ECON`

## Claim tested

Real-money Kalshi Economics event-claim probability flow (count-weighted YES price delta × frozen XAU polarity), thinned max-1-per-UTC-weekday, closed-bar join to XAUUSD H1 next open, SL 1.5×ATR14 / TP 2R / timestop 12 / refractory 12, cost UNVERIFIED_PROXY 82 XAU points RT, vs matched same-schedule H1 momentum control.

## Result (no rescue)

| Item | Train | Validation |
|---|---:|---:|
| N | 616 | 259 |
| Trades/elapsed week | 4.850 | 4.954 |
| PF gross | 0.941 | 0.947 |
| PF x1 | 0.744 | 0.796 |
| PF x1.5 | 0.664 | 0.731 |
| PF x2 | 0.594 | 0.673 |
| Exp x1 (R) | -0.170 | -0.134 |
| Max DD% x1 | 42.56 | 19.21 |
| Control PF x1 | 0.819 | 0.898 |

- Positive years @x1: **0/4**
- Bootstrap P95 DD x1: **64.74%**
- Gates: **4/14**; failed: g2_source_cadence_2_5, g5_gross_pf, g6_pf_x1, g7_pf_x15, g8_pf_x2, g9_exp_x1, g10_dd, g11_years, g12_control_margin, g14_bootstrap_dd

## Failure packet

- Object: regulated prediction-market macro probability print flow on XAUUSD H1
- Failure mode: **no edge after cost; worse than momentum control; catastrophic DD**
- Not a source/PIT failure: World=0, holdout=0, paired schedule OK, N and executed cadence adequate
- Forbidden rescues: sign flip, densify venue, hour/year veto, threshold sweep, EURUSD switch under same ID

## Authority

- `source_build_authorized=false`
- `model0_authorized=false`
- `promotion_eligible=false`
- GOAL remains UNMET
