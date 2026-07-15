# Offline — Cross-asset / RV greenfield (Round 6)

Receipt `028B2721F6709E3AB519C454A7D498FEEAB5752578813A0C8DCD98488A22EC80`
Generated `2026-07-15T05:40:20.462734Z`
Cost a priori +$12; gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.
Beta freeze: α=-1.39201e-05 β=0.013481 n=3193 R²=0.003364 driver=NAS100.

## HYP-EUR-TRIAD-H1-PARITY-RESID-MR-001
- **KILLED_AT_OFFLINE_PROBE** (stress_fail)
- N=1107 PF=1.3288 tpw=4.246 x1.5=1.245
- detail={"by_reason": {"tp": 442, "sl": 525, "time": 140}, "by_sym": {"EURGBP": 1107}, "funnel": {"n_bars": 31112, "n_signal": 1107, "n_trades": 1107, "n_skip_open": 13211, "n_skip_day": 11098}, "resid_finite": 31158, "z_finite": 31111}

## HYP-USDJPY-H1-NAS100-BETA-RESID-FADE-001
- **KILLED_AT_OFFLINE_PROBE** (pf_fail, cadence_fail, stress_fail)
- N=316 PF=0.7857 tpw=1.2121 x1.5=0.7412
- detail={"by_reason": {"sl": 218, "tp": 81, "time": 16, "eod": 1}, "by_sym": {"USDJPY": 316}, "funnel": {"n_bars": 31093, "n_signal": 316, "n_trades": 316, "n_skip_hour": 29798, "n_skip_open": 0}, "beta_fit": {"alpha": -1.3920148351424978e-05, "beta": 0.013481028259046872, "n_fit": 3193, "r2": 0.003364, "window": "2019-01-01..2020-12-31", "driver": "NAS100"}, "resid_finite": 28178}

## HYP-XAU-XAG-H1-RATIO-ZMR-001
- **KILLED_AT_OFFLINE_PROBE** (pf_fail, cadence_fail, stress_fail)
- N=127 PF=0.9868 tpw=0.4871 x1.5=0.5556
- detail={"by_reason": {"sl": 78, "tp": 48, "time": 1}, "by_sym": {"XAGUSD": 127}, "funnel": {"n_bars": 29508, "n_signal": 127, "n_trades": 127, "n_skip_hour": 28220, "n_skip_open": 4}, "spread_finite": 29552}
