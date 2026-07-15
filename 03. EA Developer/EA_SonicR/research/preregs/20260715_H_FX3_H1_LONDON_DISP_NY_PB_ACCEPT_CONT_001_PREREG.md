# Prereg — HYP-FX3-H1-LONDON-DISP-NY-PB-ACCEPT-CONT-001

- State: `preregistered` (frozen pre-offline)
- Feature family: `fx_h1_london_disp_ny_pb_accept`
- Lane: `hard_pivot_w7_entrystate_20260715`
- Thesis / post-friction $/trade → cadence:
  Nested London→NY handoff raises confirmation rarity (edge thickness
  after +$12) vs single-session accepts; session clocks keep cadence
  without FVG densify.
- Arm UTC[7,12): displace body≥0.85*ATR
  ratio≥0.55 closing beyond Asia[0,7) extreme.
- NY UTC[12,17): stage1 PB-touch (no accept);
  stage2 accept beyond zone (≤8 bars) → next open CONT.
- RR=2.0; hold≤12. Max 1/day/symbol.
- Hard ≠ W6 same-session nested densify; ≠ W5 Asia-sweep mid-reclaim;
  ≠ NY-open-impulse densify; ≠ leadlag peer; ≠ FVG densify.
- Model 0: only PROBE_SURVIVOR.
