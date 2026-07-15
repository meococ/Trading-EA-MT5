# Prereg — HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_asia_sweep_mid_reclaim`
- Lane: `hard_pivot_w5_entrystate_20260715`
- Thesis / thick∩cadence breaker: Asia HL is a **daily clocked
  location** (cadence floor across FX3) — NOT an open FVG window.
  Mid-reclaim after sweep is the accept filter for edge under +$12.
- Asia box UTC[0,7); ≥4 bars.
- Signal UTC[7,14): wick sweeps Asia extreme
  by ≥0.05*ATR; close reclaim beyond Asia mid; body≥0.2*ATR.
- Entry next open; SL beyond sweep+0.1*ATR; RR=2.0; hold≤12.
- Max 1/day/symbol. Universe a priori: EURUSD+GBPUSD+USDJPY.
- Hard ≠ W1–W4 densify; ≠ Spark Asian M15 breakout densify;
  ≠ ORB/IB densify; ≠ FVG densify; ≠ equal-HL densify.
- Model 0: only PROBE_SURVIVOR.
