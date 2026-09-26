# PARITY_J - object J known-answer test

Reference run: 20260816_205426, EURUSD M15 London, N=307, PF=0.94 on
~2000-01-03..2026-08-14 (documented assumption; run artifacts deleted).

This harness: F0_J on J-PARITY window 2000-01-03..2023-05-17 (ends at the
HOLDOUT seal - holdout never loaded even for the control).

## Result

Interpretation A - F0_J as coded (W2 telemetry, no gate):
- fills N = 1441   (window-scaled expectation ~269; tolerance
  |N-N_exp| <= 20% -> FAIL)
- PF after cost x1 = 0.912   (tolerance |PF-0.94| <= 0.15 ->
  PASS)
- signals placed = 2503; fill rate = 57.6%

Interpretation B - same config slot, W2 WHQ-proximity gate ON:
- fills N = 364   -> FAIL on N
- PF after cost x1 = 0.863 -> PASS on PF
- signals placed = 580

- exits A: {'sl': 672, 'tp': 665, 'flat': 103, 'sl_same': 1}
- suspect fills A = 0,
  suspect exits A = 401
- runtime 336s

## Interpretation notes

- J config implements the 16/08 spec as coded: S/R proximity telemetry
  (no gate - sr.blocked never gates in the EA source), trend side +
  dragon slope + wave + leg-3 close beyond band + bullish/bearish candle,
  pending at signal extreme +/-3 pips, ttl 4 bars, SL leg-0 extreme
  -/+0.1*ATR14 cap 120 pips, TP first WHQ half-step >=15 pips else 1.5R,
  London 08-16, weekly cap 5.

## Gap analysis and verdict

Economics PASS in both interpretations (PF 0.912 / 0.863 vs 0.94,
tolerance 0.15). N FAIL in both, with B (W2 gate ON) far closer
(364 vs ~270, +35%) than A (1441, +435%). Additional window probe on B
(same trades file): restricting to 2010+ gives N=163, PF=0.947; to 2015+
N=76, PF=0.864 - no window variant lands inside the +-20% band, so the
residual N gap is structural, not a window mis-guess.

Most likely causes, in order:
1. Feed difference: the 16/08 run's broker feed (research-plane pull)
   vs this lab-cache MQ-Demo feed -> different tick -> different
   fractal/wave enumeration. A few percent of swing/bar differences
   compound across 23 years into the +-35% residual.
2. Spec drift in the surviving source: SNR_Signal.mqh was repurposed
   after 16/08 (the file now hosts an XAU H1 object); the packet's own
   fidelity matrix marks W2 '~' - consistent with the gate existing at
   run time and being weakened/removed later. Interpretation B is the
   closer structural match and the probable as-run object.
3. Second-order spec details with no surviving evidence (exact w in the
   W2 band, max_pullback_age, weekly-cap counting convention).

Verdict: PARTIAL PASS - economics reproduce the 16/08 run within
tolerance; the exact N=307 is not reproducible because the run artifacts
are deleted and the surviving source no longer encodes the run-time
gate. The ladder proceeds on the preregistered table: F0_J = the
code-faithful permissive base (interpretation A), and F1_W2whq
(interpretation B) measures the W2 gate itself - which is exactly the
ladder's purpose. All configs share one engine, so relative deltas are
unbiased by the residual N gap. Recorded as a documented gap per the
prereg protocol, not silently patched by tuning to 307.

## Amended criterion (LEAD_NOTE_2, 23/09 16:20Z)

The Lead established that the run window is UNRECOVERABLE (no registry
row, runs.db pruned, no log entry) and that ~116 sig/yr makes a 26-year
N=307 implausible - the run was probably a short window, possibly inside
the sealed holdout. PREREG section 6's N-band is therefore unjudgable;
the parity criterion is amended to:

- (a) PF of F0_J on the J-parity window within 0.94 +/- 0.15:
  **PASS** (0.912).
- (b) trades/year + which window lengths would give N=307 at this
  density: F0_J produced 1441 fills over ~23.4 y = 61.6 fills/yr; at
  this density N=307 corresponds to a ~5.0-year window. Under
  interpretation B: 364/23.4 = 15.6/yr -> ~19.7 years.
- (c) spot-check 10 F0_J trades by hand against bars: **DONE**
  (`runs/handcheck.py`, fresh code path, 10/10 exact match on
  fill price, exit price, exit time and reason - see REVIEW.md).

Git revision used for the as-coded spec: NOT recoverable - the J source
was inspected in the CURRENT working tree (`SNR_ClassicWave.mqh`,
`SNR_Signal.mqh`, EA wiring) which still contains the J parser verbatim
(file untouched since 16/08 per file content, but the run rev itself is
not recorded anywhere). The run's tester model/cost settings are also
NOT recorded - cost tolerance is covered by the +-0.15 PF band.
Interpretation B was run because PREREG section 6 itself prescribed the
w2-gate probe when N overshoots - it is labeled inference, and LEAD_NOTE_2
item 1 (do not chase N) is respected: the conclusion keeps A as F0_J.


## Hand-check on BOTH harnesses (A1 step-1a, runs/handcheck.py)

Same 15 signals (10 F0_J + 5 F2_NH_b) replayed by the independent path on
H0 (suspect bars tradable) and H1 (skip_suspect + gap rules), compared to
the two CSV sets:

| harness | F0_J checked | mismatches | F2_NH_b checked | mismatches |
|---------|--------------|------------|------------------|------------|
| H0 | 10 | 0 | 5 | 0 |
| H1 | 10 | 0 | 5 | 0 |

30/30 pass. On H1 the replayed exits differ from H0 exactly where suspect
bars were skipped (later exit bar / gap-at-clean-open fill) and match the
_e1 CSVs field-for-field: pending_px, entry, exit_px, r_x1, exit_reason.
