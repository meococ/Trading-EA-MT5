# LEAD NOTE 4 - PREREG v2 amendment for ROUND 2B, frozen BEFORE any per-element P/L (Lead, 23/09 17:40Z)

DO NOT apply anything in this note to round 2. Finish round 2 exactly as PREREG.md says (sparse configs stay
in the table, flagged). This note is the frozen spec for round 2B, which runs in this same session right
after round 2 (RESULTS.md written). The Lead froze it at 17:40Z, while the census was still running and before
any DESIGN P/L existed for any config other than F0_J (whose aggregate PF the Lead saw in PARITY_J). Record
that fact and this file's sha256 in PREREG_V2.md.

## Why (census, EURUSD DESIGN, 523 weeks, outcome-blind)
F0_J 1055 signals (2.0/wk). W2whq 209, W2swing 156, W3 448, W4a 28, W4b 0, PV 23, FULL 0, FULL_RE 0.
The "add the 5 missing elements" question - the Owner's chosen direction - is unanswerable as registered:
- W4 is mis-specified, not rare by chance. The EMA34 moves ~0.057 x (close - EMA) per bar, so a 5-bar slope
  >= 0.05 ATR/bar needs the close ~0.9 ATR above the Dragon for 5 bars in a row. A Classic trigger is the
  bar that re-crosses the Dragon after a pullback, so the gate contradicts the setup it filters.
- PV stacks two sparse conditions (swing-cluster zones, themselves ~15% of F0, plus slope agreement).
- AND-ing five gates on a 2/week base cannot keep >= 1 trade/week/symbol.

## Round 2B configs (8 new; the trial count for deflated Sharpe becomes 25)
Base = F0_J signal generator (same wave, trigger, entry, session, costs, sim). All inputs are bars <= t.
1. F1_W4c: Dragon pointing the trade way over the wave: dir * (mid[t] - mid[t-20]) > 0.
2. F1_W4d: dir * angle20[t] >= Q, angle20 = (mid[t]-mid[t-20]) / (20*ATR14[t]); Q = median of dir*angle20
   over F0_J DESIGN signals of the same symbol, computed in the 2B census, written into PREREG_V2.md with the
   hash BEFORE any 2B P/L.
3. F1_PV2a: volume at the turn - any bar in [leg2-1, leg2+1] has PVA class rising or climax (TAH thresholds,
   already code-verified). leg2 must be a swing confirmed at or before t.
4. F1_PV2b: breakout with volume - trigger bar t has PVA class rising or climax.
5-8. F5 confluence score S = W2any + W3 + W4c + PV2a (0..4), W2any = WHQ zone OR swing zone at the leg-0
   origin price. Exits = R1b (big-swing SL) + R2a (TP at historic S/R), as in F1_FULL.
   F5_S2 (S >= 2), F5_S3 (S >= 3), F5_S2_EXT and F5_S3_EXT (same, session = london_ext).

## Essence test, pre-registered (the main 2B answer)
On F0_J DESIGN trades (J exits, both symbols, all signals, no gates), compute S per trade. Report expectancy R,
PF x1 and PF x1.5 per S bucket (merge upward any bucket with < 30 trades), with 1000-sample bootstrap 90% CIs.
Test: one-sided Spearman between S and trade R, p < 0.05, per symbol and pooled. Same split for each single
element (with vs without). This is REPORTED as evidence on whether confluence adds edge; configs are still
SELECTED only by the PREREG selection rule.

## Protocol
- 2B census first (counts only, plus Q for W4d); freeze PREREG_V2.md with sha256; then DESIGN P/L; controls
  (random-entry with 100 seeds, direction flip, +20-bar shift) for any config that clears the selection rule.
- VALIDATION: read once, only for 2B configs that pass the selection rule (at most 3). Round-2 configs are not
  re-read. HOLDOUT stays sealed.
- Selection rule, costs, windows, heavy_run lock and walls: unchanged.
- Known semantics to document in LEAD_HANDOFF (not a bug, but the MQL5 port must copy it): in the round-2 PV
  label, `zones_at(j)` for a look-back bar j < t returns zones built from swings confirmed up to t (causal for
  the decision at t, but not "zones as known at j").
- Deliverables: RESULTS.md section "Round 2B", BAO_CAO_LAB.md updated (Vietnamese), LEAD_HANDOFF.md updated,
  REVIEW.md: the neutral reviewer re-checks the 2B census, PREREG_V2 hash timing vs first 2B P/L file, and the
  W4d Q computation.
