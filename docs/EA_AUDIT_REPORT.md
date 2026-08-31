# EA Audit Report
Status: authoritative | Last updated: 2026-04-10

## EA_ITSM — E8 MC Gate

**VERDICT: PASS — deployable on E8 Markets (USDJPY+)**

| Metric | Value | Gate |
|--------|-------|------|
| Full-period PF (374t, USDJPY) | 1.525 | ✅ ≥1.20 |
| E8 recent PF (18t, USDJPY+) | 1.682 | ✅ confirms edge |
| MC P95 DD at 0.5% risk | **4.93%** | ✅ <8% E8 cap |
| P(breach 8% DD / 1yr) | **0.19%** | ✅ negligible |
| WFA | 5/5 | ✅ |
| Robustness | 7/7 | ✅ |
| CI 95% lower | 1.208 | ✅ >1.0 |
| All 8 validation gates | PASS | ✅ |

**Recommended E8 sizing: 0.65–0.75% risk/trade** (P95 DD 6.4–7.4%, CAGR ~6–7%/yr).
Do not exceed 0.75% — P95 DD crosses 8% cap at 1.0% risk.

Full MC analysis: `docs/archive/auto/EA_AUDIT_MC_ITSM_20260410.md`

## EA_Cobra — E8 Status

**VERDICT: PASS — confirmed E8 deployable on XAUUSD+**
Recent E8 standalone (10t, 2025.11–2026.03): PF 1.499, DD 0.27%.
Validated config: `InpKzNycStart=16;InpKzNycEnd=17;InpRiskPct=0.10;InpSkipThu=1`

## Comparative (E8 dual deployment)

| | ITSM (USDJPY+) | Cobra (XAUUSD+) |
|--|---------------|-----------------|
| Recent E8 PF | **1.682** | 1.499 |
| Trades/yr | **~47** | ~29 |
| MC P95 DD | 4.93% | ~0.8%* |
| Correlation | -0.01 to -0.03 (natural hedge) ||

*Cobra MC from news-filter run; lower DD because lower risk% preset.

Dual deployment viable. Combined correlation near zero — portfolio benefit is real.
