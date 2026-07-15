# Prereg — HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001

- State: `preregistered` (frozen pre-offline)
- Parent shelf: `HYP-SB-MAXKZ2-RR2-FRICTION-001` / run `194548`
- Feature family: `sb_disp_body_mitigation_accept`
- Lane: `hard_pivot_w2_entrystate_20260715`
- Symbol/TF: USDJPY / M15
- Thesis: keep FVG near-miss *lesson* (accept-delay thick $/trade)
  but change **location class** to displacement BODY (not FVG gap)
  to raise cadence without densifying killed FVG-retest object.
- Arm: SB disp gates (body≥0.4*H1ATR, ratio≥0.7)
  in KZ; zone = [min(o,c), max(o,c)] of disp bar; no arm-bar fill.
- Trigger: later closed M15 (≤8) wick-into-body + close
  accept outside in disp direction; enter next M15 open.
- SL beyond opposite body ±0.2 ATR; RR=2.0; MaxKZ=2;
  KZ LDN(11, 12)/NY(16, 18); no HTF in probe.
- Challenger gates: joint + PF@$12 > control 1.120 + x1.5 > 1.013.
- Hard ≠ FVG-retest-k densify; ≠ bodyATR impulse-gate densify;
  ≠ H1-OB-mitigation-k densify; ≠ MaxKZ/exit densify.
- Model 0: only PROBE_SURVIVOR.
