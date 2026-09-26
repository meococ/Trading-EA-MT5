# PREREG_V5 — ROUND 2E: MULTI-TIMEFRAME TREND AGREEMENT AS AN ENTRY
FILTER FOR F2_NH_b

Frozen 2026-09-23 (before the first file that contains P/L split by
S_T). Verbatim-frozen; amendments go in new sections, never edits.
Walls unchanged: no MQL5/MT5/alpha.ps1/git write; heavy runs only via
heavy_run.py --lane sonic-lab, never parallel; read-only outside
SonicR_Lab; HOLDOUT of every symbol sealed; VALIDATION read at most
once and only if the confirm stage passes (logged unlock). Round 2D
outputs are final and not edited.

## Question

Do NH_b trades with more higher-timeframe trend agreement earn more, on
symbols the rule was not designed on, and does the filtered system
clear the gate on unread data?

## Split (identical to round 2D)

Snippet (rerun and verified):

    D basket: ['AUDUSD', 'USDCHF', 'GBPJPY', 'USDJPY', 'GBPUSD']
    C: ['NZDUSD', 'USDCAD', 'EURJPY', 'AUDJPY', 'EURGBP']
    D total = ['AUDUSD', 'USDCHF', 'GBPJPY', 'USDJPY', 'GBPUSD',
               'EURUSD', 'XAUUSD']

DESIGN set D (7): AUDUSD, USDCHF, GBPJPY, USDJPY, GBPUSD, EURUSD,
XAUUSD. CONFIRM set C (5): NZDUSD, USDCAD, EURJPY, AUDJPY, EURGBP.

## Honest limits (all written before any S_T P/L)

- D and C share the same time window, and correlated symbols sit on
  both sides of the split, so only VALIDATION tests time.
- The Lead has seen X0 per-symbol results on C (2C, PREREG_V4).
- D has been used in rounds 2C and 2D.
- Trend-context rules were already tested in earlier rounds on
  EURUSD/XAUUSD in other families, with results (PREREG.md /
  RESULTS*.md):
    * F3_LUCY_a/b: H1 trend gate (last CLOSED H1: close vs H1 EMA89 and
      H1 dragon mid) -> M5 rejection touch. DESIGN PF 0.86/0.75 EUR,
      0.64/0.60 XAU - dead on costs (RESULTS.md, RESULTS_v2.md).
    * F4_BAI14: EMA34-band bounce with EMA200/610 context, TP 2R -
      PF ~0.97 EUR, ~0.65-0.98 XAU; dead on costs.
    * F1_W3/W4a/W4b: leg-1 through Dragon / Dragon angle >= 0.05/0.10
      ATR - F1_W3 EUR PF_R 1.08-1.19 but failed the dual-harness
      selection; angle variants did not replicate.
    * F0_J and F2_NH_b themselves carry no trend-direction gate; the
      confluence score S of round 2/2B (PVA/W4/PV stack) showed a weak
      EUR/XAU dose-response that did NOT replicate on the 2C basket
      (Stouffer p 0.26/0.44).

## Score (frozen definition)

sig_ctm is the OPEN time of the M15 signal bar t (closes at
sig_ctm + 900). A higher-timeframe bar is usable only if
open + step <= sig_ctm + 900. All HTF bars are built from ALL M1 bars
in server time via src.data.resample - the same routine the M15 signal
context uses; EMAs use indicators.ema (MT5-style SMA seed, causal).
One label set shared by H0 and H1.

    A1 TREND89 (M15 bar t): long: EMA34(close)[t] > EMA89(close)[t];
       short: EMA34 < EMA89.
    A2 H1DRAGON (last usable H1 bar): long: close > H1 EMA34(High);
       short: close < H1 EMA34(Low).
    A3 H4TREND (last usable H4 bar j): long: H4 EMA89(close)[j] >
       H4 EMA89(close)[j-6]; short: lower.
    S_T = A1 + A2 + A3 in {0,1,2,3}.

Warm-up: a trade whose score needs an EMA with fewer than 3 x period
bars of history on its timeframe (H4 EMA89: 267 H4 bars; H1 EMA34: 102
H1 bars; M15 EMA89: 267 M15 bars) gets S_T = NA. NA trades are dropped
from the base; the SAME base (X0-HOLD trades with a defined score) is
used for every statistic, including X0's own numbers.

Trading rule (fixed): keep a trade iff S_T >= c, with c chosen on D by
the cutoff rule below from {2, 3} only.

## Statistics (fixed list, cost x1 unless stated)

    Slope b = OLS coefficient of trade R on S_T with symbol fixed
    effects, pooled over the stage's symbols.
    Also reported: mean R, PF_R x1/x1.5 and n per S_T bucket (merge a
    bucket with < 30 trades upward), Spearman.
    Bootstrap: resample calendar 4-week blocks JOINTLY for all symbols
    and all trades (the same blocks for every subset), 2000 resamples,
    seed 20260924; CIs and one-sided p from it.
    Kept set K = trades with S_T >= c; removed Rm = the rest;
    sep = mean R(K) - mean R(Rm).
    Null for K (regime-preserving): for each draw, one shift k (whole
    weeks, uniform in [8, W-8], W = number of calendar weeks in the
    stage's window, same k for all symbols) moves every symbol's
    per-M15-bar trend state series circularly in time; recompute each
    trade's A1-A3 from the shifted states and its own direction, apply
    the same c; pooled PF_R of the kept set; 1000 draws, seed
    20260924; pct = share of null values strictly below the real kept
    PF_R.
    Cadence = kept trades / W / number of symbols (W as above).
    Swap (reporting only, never used to select; Lead assumption, round
    3 measures): each rollover crossed costs 0.3 pip on FX (0.003 on
    JPY pairs), $0.30 on XAUUSD, triple on the Wednesday roll; show
    PF_R x1 with and without.

## CUTOFF RULE (on D, before the eligibility check)

c = 3 if its kept cadence on D (H1) >= 0.5 trade/week/symbol and its
kept pooled PF_R x1 >= the c = 2 kept PF_R on both H0 and H1;
otherwise c = 2.

## DESIGN-STAGE RULE (on D pooled, 7 symbols; all must hold)

    E1 dose-response: b > 0 on H0 and H1, with the one-sided 95% lower
       bound > 0 on H1.
    E2 not a direction or a year: on H1, b > 0 within long trades and
       within short trades, and b > 0 in every leave-one-calendar-year-
       out fold.
    E3 level: kept pooled PF_R x1 >= 1.15 on H0 and H1; kept pooled
       PF_R x1.5 >= 1.05 on H1.
    E4 regime-preserving null pct >= 95 on H1.
    E5 cadence of the kept set >= 0.5 trade/week/symbol on H1 (a
       12-symbol account then gets ~6/week, above the doctrine cap of
       5).
    Fail -> the round stops after the design stage; C stays unread; no
    threshold, component or c is changed.

## POWER NOTE (after the design decision, before touching C; logged; it
changes nothing)

By resampling D, the probability that K1-K4 all pass if C's true b and
sep are half of D's.

## CONFIRM-STAGE RULE (on C, fixed list, DESIGN window, the c chosen on
D)

    K1 b: one-sided 95% lower bound > 0 on H1, and b > 0 on H0.
    K2 kept PF_R > removed PF_R on >= 4 of the 5 C symbols (H1).
    K3 lift, relative to what the Lead already saw on C: kept pooled
       PF_R x1 - X0 pooled PF_R x1 (same base) >= +0.04 on H0 and on
       H1; kept pooled PF_R x1.5 >= 1.00 on H1.
    K4 regime-preserving null pct >= 95 on H1.
    All four pass -> step 5. Any fail -> stop, report.

## VALIDATION RULE (read ONCE, only if confirm passed; all 12 symbols;
decided on the FIXED LIST = X0-HOLD rerun on the VALIDATION window with
the same code, then the filter applied; free running is reporting
only):

    kept pooled PF_R x1 >= 1.10 and expectancy > 0 on H0 AND H1; kept
    pooled PF_R x1.5 >= 1.00 on H1; kept PF_R > 1.00 on >= 7 of 12
    symbols (H1); b > 0 on H1.

## Multiple testing note

One hypothesis (b) with one 2-way cutoff choice on D; one on C; one on
VALIDATION.

## Mandatory tests status (all PASS before this freeze)

    T1 no look-ahead: tests/test_trend.py - score invariant to edits of
      every M1 bar after sig_ctm + 900 (M15/H1/H4 + EMAs rebuilt), at
      M15 bars at the start/middle/end of an H1 bar and of an H4 bar,
      and at the Monday open; synthetic + real EURUSD. Sunday-stub unit
      test: synthetic has none; real EURUSD has exactly 2 single-M1
      Sunday bars, both suspect-flagged, never selected as a usable
      HTF bar by any scored trade (asserted).
    T2 fixed list: X0-HOLD trade files (2D for D, 2C for C) are the
      only inputs; join on (sym, sig_ctm, dir) - zero unmatched rows
      asserted per symbol per harness in runs/score_2e.py.
    T3 label sanity: S_T distributions per symbol / direction / year in
      out/score_dist_2e.csv (labels only, no P/L).
