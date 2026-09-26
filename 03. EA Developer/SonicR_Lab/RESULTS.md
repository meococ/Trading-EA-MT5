# RESULTS - SONIC-LAB Round 2 (technical, English)

Round completed 2026-09-23. PREREG frozen 16:06Z sha256=94214bbfa768665e7741d2f79dd2e6ba54ddad3eee848ed1ae9a080df473abb1 — unchanged since logging (verify: `python -c "import hashlib;print(hashlib.sha256(open('PREREG.md','rb').read()).hexdigest())"`). 17 configs <= 22; no config added after freeze.

## 1. Parity (D-prerequisite)

See PARITY_J.md. Verdict: PARTIAL PASS.
- Interpretation A (W2 telemetry): N=1441 PF=0.912 | B (W2 gate): N=364 PF=0.863 vs reference N=307 PF=0.94.
- Economics reproduce within tolerance both ways; N residual +35% (B) attributed to broker-feed difference + deleted run artifacts. B is the probable as-run object (the packet's '~' fidelity mark on W2 supports a live gate).

## 2. Census (C2, outcome-blind, DESIGN)

| group | EURUSD sig/wk | XAUUSD sig/wk |
|-------|---------------|----------------|
| F0_J  | 2.02 | 1.96 |
| +W2whq / +W2swing | 0.40 / 0.30 | 0.66 / 0.18 |
| +W3 | 0.86 | 0.90 |
| +W4a / +W4b | 0.05 / 0.00 | 0.05 / 0.00 |
| +R1b | 2.00 | 1.93 |
| +R2a / +R2b | 1.53 / 0.64 | 1.57 / 0.29 |
| +PV | 0.04 | 0.04 |
| F1_FULL(_RE) | 0.00 | 0.00 |
| F2_NH a/b | 7.20 / 6.65 | 7.92 / 7.37 |
| F3_LUCY a/b | 20.25 / 15.13 | 20.96 / 16.48 |
| F4_BAI14 | 17.20 | 17.69 |

Sparse flags (<0.5/wk): W2whq/W2swing (EUR, XAU b), W4a/W4b, PV, FULL.
Kept in the table per protocol.

## 3. DESIGN results (D1) - headline PF x1 / x1.5 / x2

| cfg | EUR n | PF1 | PF15 | PF2 | expR | XAU n | PF1 | PF15 | PF2 |
|-----|------|-----|------|-----|------|-------|-----|------|-----|
| F0_J | 598 | 0.90 | 0.87 | 0.85 | -0.041 | 647 | 0.79 | 0.70 | 0.62 |
| F1_W2whq | 132 | 0.92 | 0.89 | - | -0.042 | 221 | 0.88 | 0.79 | 0.71 |
| F1_W2swing | 99 | 1.08 | 1.05 | - | +0.003 | 64 | 0.57 | 0.51 | 0.45 |
| F1_W3 | 270 | 1.06 | 1.03 | - | -0.017 | 309 | 0.70 | 0.62 | 0.55 |
| F1_W4a | 18 | 1.20 | 1.17 | - | +0.134 | 22 | 1.49 | 1.29 | 1.11 |
| F1_R1b | 596 | 0.94 | 0.91 | - | -0.030 | 631 | 0.87 | 0.78 | 0.69 |
| F1_R2a | 442 | 0.95 | 0.93 | - | -0.019 | 485 | 0.95 | 0.89 | 0.83 |
| F1_R2b | 199 | 0.79 | 0.77 | - | -0.114 | 102 | 0.71 | 0.61 | 0.52 |
| F1_PV | 13 | 0.97 | 0.94 | - | -0.186 | 17 | 0.61 | 0.54 | 0.48 |
| F2_NH_a | 1862 | 1.07 | 1.03 | 1.00 | +0.052 | 2214 | 0.81 | 0.73 | 0.66 |
| F2_NH_b | 1298 | **1.147** | **1.123** | **1.10** | +0.004 | 1448 | **1.053** | **0.988** | **0.928** |
| F3_LUCY_a | 4209 | 0.86 | 0.79 | 0.73 | -0.101 | 4902 | 0.64 | 0.49 | 0.38 |
| F3_LUCY_b | 2761 | 0.75 | 0.70 | 0.66 | -0.235 | 3394 | 0.60 | 0.51 | 0.43 |
| F4_BAI14 | 2895 | 0.97 | 0.93 | 0.90 | -0.042 | 3122 | 0.82 | 0.73 | 0.65 |

(F1_W4b, F1_FULL, F1_FULL_RE: zero signals both symbols.)

## 4. Negative controls (D2) - percentile of real PF vs 100 random-entry seeds

| cfg | EUR pct | flip | +20b | XAU pct | flip | +20b |
|-----|---------|------|------|---------|------|------|
| F0_J | 62 | 0.91 | 0.81 | 67 | 0.58 | 0.65 |
| F1_W2whq | 59 | **1.18** | 0.47 | 76 | 0.50 | 0.63 |
| F1_W2swing | 86 | 0.41 | 0.75 | 14 | 0.47 | 1.02 |
| F1_W3 | 93 | 0.77 | 1.04 | 26 | 0.61 | 0.60 |
| F1_W4a | 71 | 1.82 | 1.79 | 90 | 2.56 | 0.65 |
| F1_R1b | 79 | 0.96 | 0.82 | 86 | 0.64 | 0.65 |
| F1_R2a | 56 | 1.24 | 0.73 | 76 | 0.73 | 0.89 |
| F1_R2b | 28 | 1.00 | 1.15 | 48 | 0.76 | 0.46 |
| F1_PV | 55 | 0.90 | 0.33 | 32 | 0.44 | 1.98 |
| F2_NH_a | 93 | 0.92 | 0.82 | 26 | 0.74 | 0.70 |
| F2_NH_b | **100** | 1.02 | 0.89 | **96** | 0.78 | 0.88 |
| F3_LUCY_a | 98 | 0.86 | 0.76 | 100 | 0.63 | 0.54 |
| F3_LUCY_b | 2 | 0.85 | 0.76 | 5 | 0.76 | 0.57 |
| F4_BAI14 | 89 | 0.95 | 0.72 | 77 | 0.78 | 0.69 |

Read: F2_NH_b is the only config beating the 95th percentile on BOTH
symbols (100 / 96). F3_LUCY_a's high percentiles with PF<1 mean random
entries lose even faster - no edge. F1_W2whq EURUSD direction-flip
PF=1.18: fading WHQ-gated breakouts is a NEW hypothesis, not a Sonic
variant - noted only.

## 5. Multiple testing (D3)

- 34 config-runs. Max-PF null bootstrap (2,000 draws over per-config
  nulls): p50 = 1.716, p95 = 4.088, max = 8.12.
- Read: across 34 trials the BEST random PF is typically ~1.7. Any
  single config PF in the 1.2-1.5 zone (e.g. F1_W4a 1.49) is inside the
  luck envelope - only the control-percentile and cross-symbol
  consistency carry evidentiary weight. F2_NH_b's 100/96 percentile pair
  is the only result that does.
- Deflated Sharpe (r_x1, sqrt(N) scaling): F2_NH_b EUR +0.13, XAU +1.9;
  all F1/F3/F4 negative or <0.3.

## 6. Ladder anatomy (D4) - delta vs F0_J on EURUSD

| element | dPF | dExpR | dCad (sig/wk) |
|---------|------|--------|----------------|
| W2whq | +0.02 | -0.001 | -1.62 |
| W2swing | **+0.18** | +0.043 | -1.72 |
| W3 | **+0.16** | +0.024 | -1.16 |
| W4a | +0.30 | +0.175 | -1.97 (dead) |
| W4b | n/a | n/a | dead |
| R1b | +0.04 | +0.011 | -0.02 |
| R2a | +0.05 | +0.022 | -0.49 |
| R2b | -0.11 | -0.073 | -1.38 |
| PV | +0.07 | -0.145 | -1.98 (dead) |

Answer to "which missing element moves the needle": the S/R-origin
gate (W2, swing-zone flavor) and the leg-1-through-Dragon requirement
(W3) each add ~+0.15-0.18 PF on EURUSD and point the same way - the
missing Classic elements do carry real information. W4 (angle) is the
strongest single gate (+0.30) but kills cadence to ~2 signals/year, so
it cannot be evaluated. XAUUSD: every element delta is negative vs EUR -
the Classic economics do not transfer to gold.

## 7. Selection (D5) - OUTCOME: none advance

| candidate | gate failed |
|-----------|-------------|
| EURUSD F2_NH_b | PF1 1.147 < 1.20; pos-years 6/11 < 60% |
| XAUUSD F2_NH_b | PF1 1.053 < 1.20; pos-years 6/11 < 60% |
| all others | PF1 < 1.20 or cadence < 1/wk or pct < 95 |

runs/selection.json = empty, frozen 2026-09-23T18:2xZ. VALIDATION was
NOT run - there is nothing to read once. HOLDOUT untouched throughout.

## 8. Portfolio view (D6)

Only F2_NH_b survives controls. Combined cadence EUR+XAU = 2.48 + 2.77
= 5.25 trades/wk (below GOAL band 10-40/wk/symbol but consistent with
Sonic doctrine ~5/wk). Daily-P/L correlation EUR vs XAU F2_NH_b:
+0.31 (light co-movement; computed on DESIGN exits).

## 9. MC drawdown (prereg budget DD P95 <= 30R)

| config | P50 | P95 |
|--------|-----|-----|
| F2_NH_b EUR | 170R | 196R |
| F2_NH_b XAU | 51R | 79R |

Even the best family fails the DD budget on bootstrap reorderings -
the trade sequence is "many small losses punctuated by rare big wins",
which is exactly what a median-r_x1 of -1.02R with mean +0.004R says.

## 10. Verdict per family (honest)

- **F0_J / F1 ladder (Classic)**: the mechanical core is ~breakeven
  (EUR 0.90, XAU 0.79) - reproduces the 16/08 finding. The missing
  elements (W2 swing-zone, W3 thru-Dragon) add real PF (+0.15-0.18 each
  on EUR) but from a base too low to reach 1.20; they do not combine
  into the FULL composite without the cadence-killing gates. Classic
  wave is not viable as traded in this spec.
- **F2 Nhat Hoai**: the ONLY family with signal evidence (pct 100/96,
  flip loses on XAU). PF 1.15 EUR / 1.05 XAU, ~2.5 trades/wk. Real but
  sub-gate: economics leak at the exit (see anatomy).
- **F3 Lucy / F4 Bai14**: dead on costs (PF 0.60-0.97); kill in this
  spec.
- Scout remains undefined - excluded per brief.

## 11. MFE/MAE anatomy (why F2_NH_b is positive but fails)

EURUSD F2_NH_b (n=1298): median r_x1 = -1.02R, mean +0.004R.
- Winners (37%): median MFE +2.28R.
- Losers: median MFE +0.61R - the typical losing trade ran +0.6R
  favorable before dying back to -1R: the premise moves price, the exit
  donates it.
- Exits: SL 752, Friday-flat 289, TP 257. 22% of trades end on the
  weekend flatten, not on the plan.
- Clean-only (no suspect bar) PF = 1.155 vs all-trade 1.147 - suspect
  bars do not drive the result.

This is a textbook management leak, not a dead premise.

## 12. E5 - recommended next approaches (no abandonment)

1. **Exit redesign on F2_NH_b (cheapest, highest-value)**: the signal
   has real directional info and losers run +0.6R first. Test, in a NEW
   prereg: (a) break-even move at +0.5R + fixed TP 1.5-2R; (b) TP 1.5R
   fixed instead of zone; (c) time-stop after 8 M15 bars if MFE < 0.5R.
   Each is one parameter line on the same signal stream.
2. **Minimal J composite**: J + W2swing + W3 only (skip W4/PV - they
   kill cadence). Each element alone adds +0.15-0.18; if they stack the
   composite approaches 1.2-1.4. One config, one run.
3. **F2_NH_b + H1-context filter**: XAU PF 1.05 with pct=96 - the
   mechanism works on gold but the 5.5p/trade cost plane eats it. An
   H1 trend-agreement gate (reuse Lucy's H1 trend block) should raise
   per-trade expectancy by cutting counter-trend pullbacks.
4. Noted anomaly (new hypothesis, NOT Sonic): EURUSD WHQ-gated Classic
   trigger inverted PF=1.18 - a fade-the-WHQ-breakout family worth one
   cheap probe.

## 13. Errata / honesty notes

- PREREG §5 wrote the J stop as "leg-0 extreme" (correct per source
  code; the packet's loose 'leg-1' wording resolved by inspection).
- Parity N not reproduced (documented gap - feed + deleted artifacts).
- F1_W4a PF 1.20-1.49 sits INSIDE the max-PF null envelope (p50=1.72);
  with n=18-22 it is un-evaluable, not a hidden winner.
- 2020 partial year counted as a year in pos_years (6/11) - the full-year
  count is 6/10 = 60%, which would pass that gate; PF gate fails anyway.
- Suspect-bar share is material (30-38% of trades) on the pre-2010 hcc
  extension for parity; DESIGN sims on lab cache run ~12-18% suspect
  exits (flagged, clean-PF within 0.01 of headline).

## 14. Errata E0 - sl_big_swing wrong-side stop (post-review fix, 18:4xZ)

The neutral reviewer found `sl_big_swing` could return a swing extreme
on the WRONG side of the pending entry (long trade, SL above entry ->
risk ~0 -> one trade booked -154R; 11 invalid trades across the trade
files). Fixes applied:
- `sl_big_swing` now returns the most recent CONFIRMED swing extreme
  strictly beyond the pending price on the stop side (long: below,
  short: above); None otherwise (randomized unit test, 200 trials).
- sim.py admission guard kept as a second line (rejects wrong-side or
  dust stops; count in df.attrs["rejected"], later superseded by E2).

Before/after on EURUSD F2_NH_b (the config that absorbed the -154R):
- as-registered (bug): n=1298, exp_r=+0.004R, maxDD=173.7R, PF1=1.147
- fixed (guard + source fix): n=1291, exp_r=+0.132R, maxDD=47.8R,
  PF1=1.148 - the phantom tail is gone; the family verdict stands.

The Lead's E1-E3 errata (19:02Z) and addendum A1 (19:17Z) build on this
fixed harness - see RESULTS_v2.md for the corrected-harness numbers;
this file stays the round-2 as-registered record.
