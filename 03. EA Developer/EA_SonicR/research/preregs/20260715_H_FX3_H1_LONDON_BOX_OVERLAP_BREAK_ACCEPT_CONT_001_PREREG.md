# Prereg — HYP-FX3-H1-LONDON-BOX-OVERLAP-BREAK-ACCEPT-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_london_box_overlap_break_accept`
- Lane: `hard_pivot_w8_entrystate_20260715`
- Thesis / post-friction $/trade → cadence:
  Overlap-only accept filters false London box breaks that die under +$12
  (raises post-friction expectancy); London+overlap clocks keep cadence.
- Box: London UTC[7,12) HL.
- Accept: overlap UTC[12,16) first close beyond box.
- Box size ∈[0.4,2.5]*ATR; RR=2.0; hold≤12.
- Hard ≠ ORB/IB densify; ≠ W7 handoff nest densify; ≠ Asia-sweep; ≠ FVG.
- Model 0: only PROBE_SURVIVOR.
