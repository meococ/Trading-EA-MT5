# PREREG_V6 — ROUND 2F: London morning vs afternoon for F2_NH_b

Frozen with sha256 BEFORE the first file with AM/PM-split P/L for a C
symbol and before any VALIDATION access.

## Question

Do NH_b trades signalled in the London morning earn more than those
signalled in the afternoon, on symbols the observation was not made on
and on unread years, and does a morning-only NH_b clear the gate?

## Discovery (seen on D before the test; NOT evidence)

Recomputed on D with the corrected DST mapping (T3):
  H1: AM n=5535 PF_R 1.150 | PM n=2913 PF_R 0.965
  H0: AM n=6323 PF_R 1.138 | PM n=2961 PF_R 0.930
  AM>PM in 9/11 DESIGN years (H1), 10/11 (H0); 6/7 (H1) and 7/7 (H0)
  D symbols. Boundary not tuned: london_ext(07-16) minus
  ny_overlap(12-16); the gap holds for any split 09:00-15:00.
Features the Lead examined on D before choosing this one: fill weekday,
account-cap subsets, hold time, MFE/MAE of losers and winners,
exit-reason mix, risk size quintile, TP distance quintile, fill hour,
direction, year, signal-to-fill wait, cost-per-R quartile, the 2E trend
score. Only the AM/PM split is tested; the others are not.

## Label

AM iff London hour of the M15 signal bar open (sig_ctm) in [7,12);
PM iff [12,16); else OUT (excluded from every statistic incl. base;
none exist after the DST fix). Year = London calendar year of the
signal bar. Holding is unchanged (SL/TP/Friday flatten). Entry, SL,
TP, exits (X0-HOLD), costs, E1/E1b/E2/E3, H0/H1 unchanged.

## Split (rerun of `random.Random(20260924)`, pasted output)

    D = ['AUDUSD','USDCHF','GBPJPY','USDJPY','GBPUSD','EURUSD','XAUUSD']
    C = ['NZDUSD','USDCAD','EURJPY','AUDJPY','EURGBP']

Honest limits: C shares the window and currency drivers with D (a
time-of-day effect is partly market-wide); the Lead has seen X0
per-symbol results on C; D was used in rounds 2C-2E; only VALIDATION
tests time.

## Statistics (cost x1 unless stated)

- sep = mean R(AM) - mean R(PM).
- Bootstrap: calendar 4-week blocks resampled JOINTLY for all symbols
  and all trades (same block draw for every subset), 2000 resamples,
  seed 20260924; one-sided p and 95% lower bound from it.
- Primary harness H1 (suspect roll bars voided); H0 must agree in sign.
- Two modes: FIXED LIST (X0-HOLD trades from the _dstfix files, AM
  kept) and FREE-RUNNING AM-ONLY (generator never places PM orders).
- Reported only (no gates): sep ex-Friday and Friday-only; AM vs PM
  gross (before costs); swap column (0.3 pip/roll FX, 0.003 JPY,
  $0.30 XAUUSD, triple on the Wednesday roll; a position crosses a roll
  when open at the symbol's roll-window start).

## CONFIRM-STAGE RULE (C, 5 symbols, DESIGN window, fixed list)

- K1 sep: one-sided 95% lower bound > 0 on H1, and sep > 0 on H0.
- K2 AM PF_R > PM PF_R on >= 4 of the 5 C symbols (H1).
- K3 on H1: sep > 0 within longs and within shorts, and AM PF_R > PM
  PF_R in >= 6 of the 10 full DESIGN years (2010-2019).
All three pass -> step 5. Any fail -> stop, report; VALIDATION unread.

## VALIDATION RULE (read ONCE, only if confirm passed; all 12 symbols)

- V1 AM pooled PF_R x1 >= 1.10 and expectancy > 0 on H0 AND H1, and AM
  pooled PF_R x1.5 >= 1.00 on H1 — required in BOTH modes (fixed list
  and free-running AM-only).
- V2 AM PF_R > 1.00 on >= 7 of 12 symbols (H1, fixed list).
- V3 sep > 0 on H1 with one-sided 95% LB > 0 (fixed list).
VALIDATION bounds = PREREG.md registered (DESIGN_END .. VALIDATION_END);
positions still open at the window end are closed at the last
VALIDATION bar's close and counted; no HOLDOUT bar is read. Indicators
warm up on DESIGN prices; signals only inside the window.

## Power (computed on D before touching C; logged; changes nothing)

Joint probability that K1-K3 pass, and that V1-V3 pass, if the true
effect equals D's, and if it is half of D's, by joint 4-week-block
resampling of D. Approximations used: the C stage is modelled by the
joint D resample (K2 threshold scaled to >=5 of 7 D symbols; V2 to
>=5 of 7); "half of D's" shifts AM trades down and PM trades up by
sep_D/4 each so the resampled sep halves exactly. These are power
estimates, not gates.

## Multiple testing note

One hypothesis (the AM/PM split), chosen on D after the features listed
above; tested once on C and once on VALIDATION. H1 primary; H0 sign
agreement required.
