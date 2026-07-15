# Prereg — HYP-FX3-H1-ATR-EXPANSION-PDMID-ACCEPT-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_atr_expansion_pdmid_accept`
- Lane: `hard_pivot_w7_entrystate_20260715`
- Thesis / post-friction $/trade → cadence:
  PD-mid accept is cadence-capable; ATR>median expansion filter
  removes chop mid-crosses that die under +$12, raising WR and
  post-friction expectancy into the GOAL band — WITHOUT densifying FVG.
- Signal UTC[7,17): close accept beyond prior-day mid
  with body≥0.2*ATR AND ATR[j] > median(ATR[48]).
- Entry next open; SL beyond signal extreme/mid+0.12*ATR; RR=2.0; hold≤12.
- Max 1/day/symbol. Universe a priori: EURUSD+GBPUSD+USDJPY.
- Hard ≠ W1–W6 densify; ≠ London excess wick; ≠ FVG; ≠ auction-persist;
  ≠ prior-day-open break densify; ≠ H4-balance densify.
- Model 0: only PROBE_SURVIVOR.
