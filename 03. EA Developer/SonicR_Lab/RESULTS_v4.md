# RESULTS_v4 — ROUND 2D: EXIT MANAGEMENT FOR F2_NH_b

Verdict: **NO candidate eligible on DESIGN -> round stopped after the
design stage.** CONFIRM set C was never opened for any variant, no
VALIDATION read, HOLDOUT sealed. No threshold relaxed.

Protocol artefacts: PREREG_V4.md sha256
`1421a4f0ef39bac7ffe9e7e0de36f64a2a0d21426756defe427f1e779068d300`
frozen 2026-09-23T21:26:03Z, before the first exit-variant P/L file
(first `out/trades_2d_*` written 21:27:41Z by the design run).
Files: `out/design_2d_summary{,_e1}.csv`, `out/design_2d_pess{,_e1}.csv`,
`out/design_2d_slices{,_e1}.csv`, `out/trades_2d_<sym>_<cfg>{,_e1}.csv`
(D symbols only).

## 1. Split (Lead-fixed, verified before any variant P/L)

    D: AUDUSD, USDCHF, GBPJPY, USDJPY, GBPUSD + EURUSD, XAUUSD (7)
    C: NZDUSD, USDCAD, EURJPY, AUDJPY, EURGBP (5)

Honest limit (pre-registered): C shares the same time window and the
Lead had already seen X0's per-symbol results on C from 2C; C would
test the exit effect (paired dR), not the entry edge. The level test
was reserved for VALIDATION. No C-symbol exit-variant file exists.

## 2. Mandatory tests T1-T5 — all PASS (before the freeze)

    T1 regression: X0 through the new exit layer reproduces the 2C
      trade files row for row (exit_ctm, exit px, reason, r_x1/x15/x2
      to 1e-9), 12 symbols x H0/H1 x {fixed list, free running}
      = 24/24 cells, zero fails. runs/verify_2d.py.
    T2 synthetic paths: +1R then back to entry -> "be" ~0R; SL and
      trigger in one M1 bar -> "sl" at -1R; X2 formula (one bar
      reaching both +1R and TP: leg A at +1R, leg B at TP); E1b on leg
      A; short mirrors; pessimistic same-bar -> BE on the trigger bar.
      tests/test_exits.py.
    T3 dragon look-ahead: post-exit M1 edits + RECOMPUTED M15/EMA34 ->
      exit unchanged; altering the triggering M15 bar's close moves the
      decision; H1 skips an M15 check when its last M1 is suspect.
    T4 X0 random-entry null through the new code = 2C null path
      (GBPUSD seed 0): identical trades/R.
    T5 X0-DF free-running reproduces pf_r_x1_flat2350 on AUDUSD +
      EURUSD, H0 and H1, to 1e-9.
    Plus: no X0 fill in [23:50, roll window end) on any D symbol ->
      DF never changes an entry. Handcheck 16/16 fresh-path replays on
      both harnesses (be / leg-A partial / dragon / flat / sl),
      runs/handcheck_2d.py (independent verifier, not src.exits).

## 3. Design table — pooled D (fixed list, n = 9280 H0 / 8444 H1)

PF_R x1 (H0 / H1), mean paired dR vs X0-HOLD (90% CI week-bootstrap,
2000, seed 20260924):

| cfg      | PF_R x1 H0 | PF_R x1 H1 | PF_R x1.5 H1 | dR H0 [CI]       | dR H1 [CI]       | pess dR H1* |
|----------|-----------:|-----------:|-------------:|-----------------:|-----------------:|------------:|
| X0-HOLD  |     1.0697 |     1.0856 |       1.0398 |     0 (ref)      |     0 (ref)      |       -     |
| X0-DF    |     1.2045 |     1.0934 |       1.0239 | +0.040 [+.015,+.065] | -0.016 [-.042,+.009] |  -0.029 |
| X1-HOLD  |     0.9263 |     1.0796 |       1.0171 | -0.085 [-.103,-.066] | -0.018 [-.037,-.000] |  -0.034 |
| X1-DF    |     1.1946 |     1.0678 |       0.9911 | +0.026 [-.000,+.053] | -0.030 [-.057,-.004] |  -0.043 |
| X2-HOLD  |     0.9316 |     1.0506 |       0.9891 | -0.080 [-.101,-.060] | -0.032 [-.053,-.011] |  -0.040 |
| X2-DF    |     1.1270 |     1.0377 |       0.9620 | +0.001 [-.027,+.028] | -0.041 [-.069,-.014] |  -0.048 |
| X3-HOLD  |     0.8673 |     1.0592 |       0.9976 | -0.115 [-.137,-.093] | -0.028 [-.052,-.005] |  -0.043 |
| X3-DF    |     1.1958 |     1.0667 |       0.9901 | +0.027 [-.000,+.053] | -0.031 [-.058,-.004] |  -0.043 |
| X4-HOLD  |     0.6797 |     1.0984 |       1.0353 | -0.232 [-.350,-.156] | -0.009 [-.036,+.017] |  -0.025 |
| X4-DF    |     1.0717 |     1.0960 |       1.0180 | -0.016 [-.134,+.063] | -0.020 [-.050,+.010] |  -0.031 |

*mean of per-symbol pessimistic-same-bar dR (H1); the guard needs
 pooled pessimistic dR > 0 - every candidate fails it already per-symbol.

Expectancy (r_x1 mean), pip PF and per-symbol tables:
`out/design_2d_summary{,_e1}.csv`. Exit-reason mixes (H1 pooled, each
mix also carries 1 sl_same row): X0-HOLD sl 4927 / flat 1975 / tp 1541;
X0-DF flat 5298 / sl 2457 / tp 688; X1-HOLD sl 3551 / be 2237 /
flat 1425 / tp 1230; X2 identical reason mix to X1 (legs merged into
one row); X3-HOLD sl 3551 / dragon 1958 / be 992 / flat 981 / tp 961;
X4-HOLD sl 3552 / dragon 2674 / flat 1118 / be 1100 (no tp).
Free-running PF_R per
symbol in the same file (`pf_r_x1_free`): X0-DF free takes ~40% more
fills (shorter holds free the book) at lower PF.

## 4. Design rule applied -> why each candidate failed

Eligibility needed ALL of: pooled PF_R x1 >= 1.10 on H0 AND H1;
PF_R x1.5 >= 1.00 on H1; mean dR > 0 on H0 AND H1; pessimistic dR > 0
on H1.

- **X0-DF**: best PF (1.20 H0) but H1 PF 1.0934 < 1.10 and mean dR
  -0.016 on H1. It "saves" ~50% of X0 SL-losers by flattening before
  SL, but cuts ~46-55% of TP winners; R gained 2944R vs R lost 3081R
  (H1). On H0 the balance flips positive because flat also avoids the
  fabricated rollover bars - i.e. most of the H0 improvement is a
  data-artifact effect, not real exit alpha.
- **X1-HOLD** (BE at +1R): saves ~25-28% of SL losers but cuts ~20% of
  TP winners; H0 -0.085R (suspect bars create fake +1R triggers -> BE
  exits at fabricated reversals), H1 -0.018R. Fails dR on both.
- **X2-HOLD** (partials): same BE mechanics plus leg A caps half the
  position at +1R -> ~100% of TP winners are cut to smaller profit.
  H0 -0.080, H1 -0.032. Fails.
- **X3-HOLD** (dragon): exits 1958 trades on closed-M15 crosses; cuts
  ~27-38% of TP winners and beats X1 nowhere. H0 -0.115, H1 -0.028.
- **X4-HOLD** (run, no TP): worst on H0 (-0.232R, PF 0.68) - removing
  TP while BE+dragon cap the upside destroys the >24h winners that
  carry the edge. H1 PF 1.098 is cosmetic; mean dR -0.009, fails.
- **DF variants**: uniformly better than HOLD twins on H0, uniformly
  worse on H1 -> the daily-flat "improvement" is concentrated in the
  suspect rollover window. As an exit rule on clean data it does not
  survive pairing.
- **Pessimistic column**: negative for every candidate on H1
  (-0.025..-0.048); even under the friendlier same-bar ordering no
  candidate could pass.

## 5. Where the edge actually lives (reporting only, pooled D)

Mean r_x1 by hours held, X0-HOLD (H0): <4h -0.54R (n=2246),
4-12h -0.06R (3564), 12-24h -0.33R (1222), **>24h +1.00R (2248)**.
By fill weekday: Mon -0.06, Tue +0.09, Wed +0.03, Thu +0.05,
**Fri +0.19**. The profitable mass sits in LONG holds and Friday
fills - the daily flat amputates exactly the >24h bucket (residual
>24h n=111 under DF, mean +0.43). This explains mechanically why DF
fails on H1 even though it looked good in 2C's secondary column.
Slices file: `out/design_2d_slices{,_e1}.csv`.

## 6. What was NOT done (per frozen rule)

C set unread for every candidate (verified: no `trades_2d_*` file for
NZDUSD/USDCAD/EURJPY/AUDJPY/EURGBP exists). K1-K4 not run. VALIDATION
never unlocked; HOLDOUT sealed (loader guard test stands from 2C).
No parameter changed anywhere; entries/SL/TP/session/costs/E1-E3
untouched (T1 regression proves byte-level exit equivalence for X0).

## 7. Honest reading + next approaches

The F2_NH_b exit is not improvable by protection-at-+1R mechanics:
~28% of SL losers did touch +1R first (Lead's diagnostic was right),
but the same +1R zone is where TP winners transit, so protecting it
costs more than it saves - on BOTH harnesses. And the "overnight
holding is a cost" hypothesis is wrong on clean data: the >24h bucket
is the ONLY profitable holding-time bucket on H0; daily flat's
apparent gain was fabricated-rollover avoidance, which H1 already
removes properly.

Technically justified next steps (would need a new prereg):

1. **Measure real rollover cost before more exit work** (round-3
   data): the only place exit management showed any gain is exactly
   the roll window, and it is unmeasurable with current data. A
   spread/swap model may justify a *targeted* roll-avoidance exit
   (close only trades that would be held through the window AND are
   near BE), rather than a blanket 23:50 flat.
2. **Asymmetric time-stop**: <4h holds average -0.54R (the losing
   bucket), >24h holds carry the edge. A rule that exits only stale
   losers (still < 0 after N hours) while leaving TP in place attacks
   the losing tail without touching winners - mechanically opposite
   to what failed here.
3. **Higher-protection trigger**: +1R is inside the TP transit zone;
   a BE move only after +1.5R/+2R, or an ATR-trailing stop, protects
   deeper-profit trades without cutting median winners. Must be
   preregistered; not testable under this round's walls.
