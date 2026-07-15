# Prereg — HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_breaker_retest_accept`
- Lane: `hard_pivot_w2_entrystate_20260715`
- Symbol/TF: FX3 / H1
- Thesis: thick $/trade from delayed acceptance at BOS-bar body
  (breaker location) after closed structure break — joint cadence
  target via FX3 H1 swing BOS frequency, not FVG rarity / auction spam.
- Signal: confirmed swing pivot L=3; closed BOS beyond pivot
  with body≥0.25*ATR; arm breaker = BOS-bar body;
  **no entry on arm bar**.
- Trigger: later closed H1 (≤8) wicks into body + closes
  back outside in BOS direction; enter next H1 open.
- SL beyond opposite body ±0.15 ATR; RR=2.0; hold≤12;
  session UTC[7,17); max 1/day/symbol.
- Gates: N≥80; tpw∈[2,5]; PF≥1.30; PF@$12≥1.30; x1.5≥1.25.
- Hard ≠ auction-persist-k densify; ≠ FVG-retest-k densify;
  ≠ H1-BOS-M15-PB densify; ≠ fractal5-break densify; ≠ H1-OB-mitigation-k;
  ≠ R10–R31 / exit / MaxKZ / ETH VR / ORB/IB.
- Model 0: only PROBE_SURVIVOR.
