# Offline — CHF-risk + AUD-com3 + ADR greenfield (Round 7)

Receipt `CBDD990E84153D85A7A38242F6CA1D8A9B55C6BAF98DA23EA7DBB1486410F397`
Generated `2026-07-15T05:45:40.798551Z`
Cost a priori +$12; gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.
CHF beta freeze: α=-4.83048e-06 β=-0.77113 n=12421 R²=0.497748 driver=FX_RISK_BASKET_mean(EU,GU,-UJ).
QFSI parallel: 007 accumulate hb=9480 quotes=6586 deadline=2026-07-15T07:39:26.186865Z; cost freeze still GAP; login not headline.

## HYP-USDCHF-H1-FXRISK-BASKET-RESID-FADE-001
- **KILLED_AT_OFFLINE_PROBE** (pf_fail, cadence_fail, stress_fail)
- N=239 PF=1.0052 tpw=0.9167 x1.5=0.952
- detail={"by_reason": {"sl": 158, "tp": 79, "time": 2}, "by_sym": {"USDCHF": 239}, "funnel": {"n_bars": 31094, "n_signal": 239, "n_trades": 239, "n_skip_hour": 29798, "n_skip_open": 0}, "beta_fit": {"alpha": -4.830480472174185e-06, "beta": -0.771130332377738, "n_fit": 12421, "r2": 0.497748, "window": "2019-01-01..2020-12-31", "driver": "FX_RISK_BASKET_mean(EU,GU,-UJ)"}, "resid_finite": 31155}

## HYP-AUD-COM3-H1-BASKET-RESID-MR-001
- **KILLED_AT_OFFLINE_PROBE** (pf_fail, cadence_fail, stress_fail)
- N=107 PF=1.052 tpw=0.4104 x1.5=0.9895
- detail={"by_reason": {"time": 3, "tp": 43, "sl": 61}, "by_sym": {"AUDUSD": 107}, "funnel": {"n_bars": 31105, "n_signal": 107, "n_trades": 107, "n_skip_hour": 29807, "n_skip_open": 7}, "spread_finite": 31153}

## HYP-FX3-H1-ADR-EXHAUST-FADE-001
- **KILLED_AT_OFFLINE_PROBE** (pf_fail, cadence_fail, stress_fail)
- N=85 PF=0.771 tpw=0.326 x1.5=0.7209
- detail={"by_reason": {"sl": 51, "tp": 22, "time": 12}, "by_sym": {"USDJPY": 73, "EURUSD": 11, "GBPUSD": 1}, "funnel": {"n_bars": 31159, "n_eligible": 104, "n_signal": 85, "n_trades": 85, "n_skip_open": 0, "n_skip_day": 0}}
