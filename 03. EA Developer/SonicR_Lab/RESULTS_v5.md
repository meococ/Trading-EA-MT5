# RESULTS v5 — ROUND 2E: MTF Trend Agreement as Entry Filter for F2_NH_b

Round 2E, Lead brief 23/09 22:15Z. One hypothesis: trades with more
higher-timeframe trend agreement earn more (dose-response on
S_T = A1+A2+A3 in {0..3}). Entry selection only; everything else frozen
from X0-HOLD (2C/2D). Same D/C split as 2D. PREREG_V5 sha256
`430ac821bef5d0b5442c2188750906a0d4ee1df588a809b5dc0100c5c6df0bdb`,
frozen 2026-09-23T21:56:50Z, before the first S_T-split P/L file.

## The score (as frozen)

- A1 TREND89 (M15): EMA34c[t] vs EMA89c[t] agrees with direction.
- A2 H1DRAGON (last usable H1 bar, open+3600 <= sig close):
  close vs H1 EMA34(High)/(Low).
- A3 H4TREND (last usable H4 bar j): EMA89c[j] vs EMA89c[j-6].
- Keep iff S_T >= c, c in {2,3} chosen on D by the frozen cutoff rule.
- Warm-up NA if <3x period history on the needed timeframe; NA dropped;
  every statistic uses the same defined-score base.
- Alignment verified causally: a HTF bar counts only when
  open + step <= sig_ctm + 900.

## Tests (all pass before any P/L)

- T1 no look-ahead: mutating every M1 bar after sig_ctm+900 leaves the
  score unchanged; checked at start/middle/end of H1 and H4 bars and at
  Monday open, on synthetic data AND real EURUSD M1. tests/test_trend.py
  4/4.
- Sunday-stub check: real EURUSD has two 1-minute Sunday bars
  (2019-12-01 18:01:36, 2022-06-05 00:59:44) with bogus prices; both are
  suspect-flagged and never selected as usable HTF bars by any trade
  (asserted). Synthetic series contain no Sunday/Saturday bars.
- T2 fixed list: X0-HOLD files from 2D (D) and 2C (C) only; join on
  (sym, sig_ctm, dir); 0 unmatched across all 12 symbols.
- T3 outcome-blind label sanity: S_T distribution ~30/22/26/20 %
  (0/1/2/3), stable by direction and year; NA ~1.6%.

## Design run (D only, DESIGN window, fixed list, cost x1)

Base: H1 n=8301 trades (143 NA dropped), H0 n=9127 (153 NA).

### S_T bucket table, pooled D

| S_T | n | mean R H0 | PF_R H0 | n | mean R H1 | PF_R H1 | PF_R15 H1 |
|----:|----:|------:|------:|----:|------:|------:|------:|
| 0 | 3003 | +0.022 | 1.032 | 2849 | +0.050 | 1.075 | 1.033 |
| 1 | 2050 | +0.080 | 1.121 | 1825 | +0.066 | 1.101 | 1.055 |
| 2 | 2325 | +0.054 | 1.082 | 2079 | +0.083 | 1.128 | 1.081 |
| 3 | 1749 | +0.020 | 1.031 | 1548 | +0.004 | 1.006 | 0.957 |

Non-monotone: the fullest agreement bucket (S_T=3) is the worst on H1.
Spearman rho: H0 +0.027 (p=0.009, n-size significance only),
H1 +0.006 (p=0.60).

### Slope b (OLS of R on S_T, symbol fixed effects)

| harness | b | 95% LB (one-sided) | 90% CI | p_1s |
|---|---:|---:|---:|---:|
| H0 | +0.0017 | -0.028 | [-0.028, +0.029] | 0.47 |
| H1 | -0.0068 | -0.039 | [-0.039, +0.023] | 0.64 |

### Cutoff rule -> c = 2

c=3 fails the rule on both legs: cadence H1 = 0.42 < 0.5 and kept PF_R
(c3) = 1.031 H0 / 1.006 H1 < (c2) 1.060 H0 / 1.077 H1. So c = 2.

### Kept (S_T>=2) vs removed, pooled D

| harness | n_k | PF_R x1 kept | PF_R x1.5 kept | PF pips kept | E[R] kept | PF_R rem | sep | sep LB95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H0 | 4074 | 1.060 | 1.013 | 1.020 | +0.039 | 1.067 | -0.006 | -0.068 |
| H1 | 3627 | 1.077 | 1.028 | 1.109 | +0.049 | 1.085 | -0.007 | -0.076 |

Cadence H1 = 0.99 trades/week/symbol. Positive years (kept): 55% H0 /
64% H1. Kept PF_R with swap assumption: 1.043 H0 / 1.058 H1 (vs 1.060 /
1.077 without). X0 on the same base: 1.064 H0 / 1.082 H1.

### E1-E5 (frozen design rule)

| gate | requirement | observed | verdict |
|---|---|---|---|
| E1 | b>0 both, LB95>0 on H1 | H1 b=-0.007, LB95=-0.039 | FAIL |
| E2 | b>0 long, short, every LOYO fold (H1) | long b=-0.024; short +0.003; 9/11 LOYO folds < 0 | FAIL |
| E3 | kept PF_R x1 >= 1.15 both; x1.5 >= 1.05 H1 | 1.060 / 1.077 / x1.5=1.028 | FAIL |
| E4 | null pct >= 95 H1 | 43.4 | FAIL |
| E5 | cadence >= 0.5/wk/sym H1 | 0.99 | PASS |

Per-symbol kept-vs-removed PF_R on H1: better on 3 of 7 symbols
(GBPJPY, USDCHF, XAUUSD), worse on 4.

### Components alone (H1, reporting only)

| comp | n_kept | PF_R kept | PF_R rem | mean R kept | mean R rem |
|---|---:|---:|---:|---:|---:|
| A1 M15 trend | 3618 | 1.088 | 1.077 | +0.056 | +0.051 |
| A2 H1 dragon | 4001 | 1.048 | 1.112 | +0.031 | +0.073 |
| A3 H4 trend | 3008 | 1.081 | 1.082 | +0.051 | +0.055 |

A1 alone is the only component with the right sign, and it is worth
~+0.006 mean R — far below what a 1.15 gate needs. A2 (H1 dragon
agreement) actually goes the wrong way.

### Free running (reporting only)

Filtered order stream (S_T>=2), X0 exits: pooled per-symbol PF_R H1
median ~1.16, range 0.99-1.24; H0 median ~1.07. (Free-running looks
better than fixed-list because the one-position rule drops trades, but
it is secondary by prereg.)

## Decision: STOP after the design stage

E1-E4 all fail; no candidate may advance. Per the frozen rule: C stays
unread for every score level, VALIDATION stays unread, HOLDOUT sealed,
nothing relaxed.

## Power note (computed at decision time; moot since C never runs)

Half of D's b is ~-0.003. With bootstrap sd ~0.019, P(K1 lb95>0) ~ 3%,
joint P(K1-K4) < 1% even if C were run.

## Honest reading

1. The Sonic R doctrine "trade the M15 Dragon only with the larger
   trend" does NOT help NH_b entries. Agreement is not even monotone —
   S_T=3 is the worst bucket on H1.
2. Why it may be so: NH_b already enters at a Dragon break after a
   pullback; when the trend already agrees on three timeframes the move
   is mature (entry late / mean-reversion point), and full HTF
   alignment correlates with exhaustion, not continuation. The counter
   (S_T=0, trend disagreement) earns +0.05R on H1 — NH_b is quietly a
   counter-trend-flavoured breakout.
3. The thin F2_NH_b edge is broad (9/10 symbols PF_R>1 in 2C) but not
   directional-context-dependent in this form.

## Next approaches for the Lead (2-3, with reasons)

1. **Pullback-quality filter instead of trend filter** — score the
   pullback leg itself (depth in ATR, number of M15 bars below the
   Dragon, whether the leg made a fresh swing low). Why it could work:
   the round-1 anatomy showed leg shape carries signal; unlike trend
   agreement, pullback quality is a pre-entry, actionable, and
   mechanically definable variable with no hindsight.
2. **Measure real rollover cost in round 3, then revisit the exit** —
   the only place 2D found anything (daily flat) was killed by
   fabricated bars; on real spread/swap numbers a narrower variant
   (skip only the roll window) may survive where the full daily flat
   died.
3. **Volatility-regime gate** — enter only when M15 ATR or realized
   compression is in a defined band; NH_b's edge may be concentrated in
   post-compression expansions. Pre-entry variable, no look-ahead, and
   orthogonal to both trend and pullback shape.

## Repro

- `src/trend.py` — score engine (causal, vectorized).
- `tests/test_trend.py` — T1 (look-ahead incl. Monday open, mid-bar),
  Sunday-stub, join; 4/4 pass.
- `runs/score_2e.py` — label run (all 12 syms, labels only).
- `runs/design_2e.py` — D statistics, cutoff, E1-E5, null, bootstrap.
- `out/scores_2e_<sym>.csv` — per-trade labels (no P/L).
- `out/design_2e_summary.csv`, `design_2e_persym*.csv`,
  `design_2e_free.csv`, `base_2d*.csv`.
- `LAB_LOG.md` — timestamps, freeze hash, decision.
