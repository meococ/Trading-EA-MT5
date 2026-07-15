# Prereg — HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_leadlag_peer_accept`
- Lane: `hard_pivot_w5_entrystate_20260715`
- Thesis / thick∩cadence breaker: **a priori multi-symbol peer book**.
  Lead impulse = rare thick timing; lag delayed accept = quality.
  Cadence expands across frozen peers — MUST NOT be “open FVG
  window because cadence failed”.
- Universe freeze (a priori): EURUSD, GBPUSD, USDJPY.
- Frozen edges: EURUSD↔GBPUSD same-side; EURUSD/GBPUSD→USDJPY opposite.
- Lead: body≥0.5*ATR close beyond prior 12-bar extreme.
- Lag arm: lag close still inside its 12-bar range at lead time.
- Trigger: lag accept close beyond LOOK extreme within ≤5 bars.
- Session UTC[7,17); SL=1.25 ATR; RR=2.0; hold≤12.
- Hard ≠ W1–W4 densify; ≠ R12 relstr densify; ≠ R20/R21 lead densify;
  ≠ FVG densify; ≠ oneslot densify.
- Model 0: only PROBE_SURVIVOR.
