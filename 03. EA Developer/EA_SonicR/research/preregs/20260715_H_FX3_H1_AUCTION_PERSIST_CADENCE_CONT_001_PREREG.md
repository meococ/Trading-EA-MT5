# Prereg — HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_auction_persist_cadence`
- Lane: `hard_pivot_entrystate_rebuild_20260715`
- Symbol/TF: FX3 / H1
- Thesis: thick $/trade from acceptance at distribution extremes +
  range expansion; cadence engineered a priori for book sleeve
  (VR *lesson*, NOT ETH VR densify).
- Signal (closed-bar): ≥3 of last 4 closes in outer quartile of
  prior 48 closes (same side) AND range > median(prior
  12 ranges); session UTC hour ∈[7,17).
- Entry: next H1 open. SL/RR/hold frozen:
  SL=1.5 ATR, RR=2.0, hold≤10, max 1/day/symbol.
- Gates: N≥80; tpw∈[2,5]; PF≥1.30; PF@$12≥1.30; x1.5≥1.25.
- Banned: ETH VR-k densify; AC/HA/ER/ROC rename; exit/MaxKZ densify;
  R10–R31 densify; ORB/IB.
- Model 0: only PROBE_SURVIVOR.
