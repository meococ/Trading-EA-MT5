# STUDY_PLAN — DR-MARKET pre-registration

Lane: `research/market/` (DR-MARKET mandate, Lead 2026-09-21 08:16Z).
Written and hashed into the ledger (`kind=market_study_prereg`) **before any
forward-looking statistic is computed.** Any deviation lands in
`DEVIATIONS.md`.

Scope: DESIGN 2016-01-01 → 2021-12-31 only; core symbols EURUSD, GBPUSD,
USDJPY, AUDUSD; M5 bars resampled from the sealed `pa_data` M1 cache;
outcomes resolved on the M1 path. No fills, no PnL, no setups.

---

## 0. Primitives (all causal)

- **ABR** at bar t = mean(high−low) of the 50 closed M5 bars *before* t
  (`abr[t]`, NaN until then). All ABR-unit quantities use `abr[t]` of the
  event bar.
- **tol** at bar t = max(1.0 pip, 0.25·abr[t]) — spec v1 edge tolerance.
- **CET minute** = server minute − 60 (mod 1440). Server = UTC+2/+3 EU DST,
  proven in `CLOCK_AUDIT_DESIGN.md` (M0).
- **Server day** = t // 86400 on bar-open server epoch. Week = Mon-start
  server days (feed: Mon 00:16 → Fri ~23:59 server, daily gap 00:00–00:15).
- **Year** = `pa_clock.server_year` of the bar close.
- **DC pivot** (directional change): state machine on M5 bars; a pivot is
  *confirmed* at the first bar whose price retraced θ from the running
  extreme. Pivot price = the extreme; `t_confirm` = confirmation bar.
  Two pre-declared scales: **θ₁ = 1.0·abr[t]** (micro) and
  **θ₂ = 2.5·abr[t]** (meso).
- **Warm-up** bars (before 2016-01-01) never produce events.

## 1. Level sets (M3)

All levels are zones [p−tol, p+tol]. A touch event on level L at bar t:

- bar t's range intersects the zone;
- no bar in [t−24, t) intersected the zone (FRESH=24);
- some close in [t−24, t) was ≥ 1.0·abr[t] from the zone (AWAY=1.0);
- `side` = −1 if c[t−1] ≤ zlo (approach from below → resistance),
  +1 if c[t−1] ≥ zhi (support);
- abr[t] finite, bar t not warm-up.

Sets:

| id | construction | active |
|---|---|---|
| S1 | θ₁ swing pivots | from confirm bar, max 1440 bars |
| S2 | θ₂ swing pivots | same |
| PDH/PDL | prev server-day high/low | whole server day |
| ASIA | Asia high/low 00:00–08:00 CET | 09:00 srv → day end |
| RND | 00/50 grid (50-pip spacing, offset 0) | levels within ±3.5·abr of day open, per day |
| P-RND20 | same grid, offset +20 pips (endings 20/70) | same |
| P-RND10 | offset +10 pips (endings 10/60) | same |
| P-RAND | 24 uniform prices/day within ±3.5·abr of day open (seeded per symbol-day) | per day |

P-RAND is the universal placebo for S1/S2/PDH/ASIA; RND is additionally
contrasted with P-RND20 (primary) and P-RND10 (sensitivity).

## 2. Outcomes on the M1 path (horizon H = 48 M5 bars unless stated)

For a touch event with side −1 (level above): near edge = zlo, far = zhi.

- **BOUNCE**: M1 low ≤ zlo − x·abr before M1 high ≥ zhi + x·abr.
- **BREAK**: the high barrier first. **NONE**: neither within H.
- x ∈ {1, 2}. Primary contrast: `P_rev = BOUNCE / N` (all events);
  secondary: `BOUNCE/(BOUNCE+BREAK)` among resolved.
- **Overshoot** = max penetration beyond the far edge over [t, resolve]
  (price units → reported in pips and abr). Also overshoot at fixed small
  windows (3 bars) for the T/F poke calibration.
- **bars_to** resolution in M5 bars.
- For side +1, mirrored.

## 3. Placebo matching and contrast

Strata per symbol: `side × dow × utc 4h-bucket × abr tercile × approach_atr
decile` (deciles/terciles computed on pooled real+placebo events of that
symbol). Contrast **D = mean_real − mean_plac**, pooled across strata with
Hajek weights ∝ #real in stratum (min cell 5 each side). CIs: day-block
bootstrap, n_boot = 2000, resampling server days jointly over both arms.
Two-sided bootstrap p: `2·min(P(D≤0), P(D>0))` from the bootstrap
distribution (min resolution 1/(B+1)).

## 4. Question families and BH-FDR structure (q = 0.10 within each family)

- **F-R (reaction, 20 tests):** D[P_rev] vs placebo for
  {S1, S2, PDH/PDL, ASIA, RND} × {x=1,2} pooled over core symbols; plus
  RND vs P-RND20 and RND vs P-RND10 at x∈{1,2} (4 tests). Family size 24.
- **F-O (overshoot, descriptive):** quantiles (50/75/90) of overshoot per
  set — no contrast, no FDR; used to set zone-width/poke parameters.
- **F-A (age decay):** D[P_rev] of S1+S2 pooled by age bin
  {[0,3h),[3,8h),[8,24h),[24,72h),[72h,120h]} (5 tests); half-life fit
  reported descriptively.
- **F-T (touch count):** P_rev by touch_no {1,2,3+} and D vs placebo per
  bin (6 tests over the pooled level sets S1,S2,PDH,ASIA).
- **F-B (break→retest, role reversal):** among BREAK (x=1) events:
  P(retest of the zone within 12 and 48 bars); among retests,
  P(rebound ≥1·abr in break direction before re-crossing the zone by
  1·abr) vs placebo breaks (4 tests).
- **F-C (cascades, Osler 2005):** first cross of a round price (close
  ≥ tol beyond it; that grid price untouched in the prior 288 M5 bars);
  outcome = signed move in cross direction over H ∈ {3, 12} bars from the
  cross-bar close. Contrast RND vs P-RND20 and vs P-RAND (4 tests).
- **F-X (boxes/breakouts, §5)** and **F-L (lines, §6)**, **F-M
  (momentum/EMA, §7)** as declared below.

## 5. M4 — boxes and breakouts

**Causal box detector (declared).** At bar t look back W = 30 bars:
`hh = max h`, `ll = min l` over the window. Candidate is confirmed at t iff

- height hh−ll ∈ [1.5, 6.0]·abr[t];
- top touches `#{i: h_i ≥ hh − tol_i}` ≥ 2 and bottom touches
  `#{i: l_i ≤ ll + tol_i}` ≥ 2 in the window;
- touch types interleave: the first and last edge-touch in the window are
  on opposite edges;
- span between first and last edge touch ≥ 9 bars.

The box [ll, hh] freezes at the confirm bar `t_b`; it dies at the first
close ≥ tol beyond an edge (**BOX_BREAK** event) or 100 bars after birth.
At most one break event per box per direction.

**Metrics**

- Height (pips, abr) and duration (bars) distributions per session
  (descriptive; sessions: Asia 00–08, EU 08–14:30, US 14:30–18:00,
  off 18–24 CET).
- **Follow-through** after BOX_BREAK at horizon H ∈ {6,12,24,48}:
  P(move ≥ y·abr beyond the edge in break direction before ≥ y·abr back
  through it), y = 1; also median max-favourable excursion (MFE) in abr.
  Split by **buildup**: ≥ 3 bars immediately before the break bar each with
  range ≤ 0.8·abr and (up break) non-decreasing lows and each high within
  1·abr of the edge — (a) buildup vs (b) none.
- **False breaks**: bars trading beyond the edge and closing back inside,
  by poke depth δ ∈ (0,1], (1,2], (2,3], (3,5] pips; outcome = P(reach the
  opposite edge within 24 bars).
- **Placebo**: per-day random prices (the P-RAND pool) that were touched
  ≥ 2 times within tol in the trailing 30 bars → "fake edge"; break =
  first close ≥ tol beyond it. Same follow-through metrics. Matched on the
  same strata (side→direction, dow, hour-bucket, abr tercile, height
  tercile where applicable).
- **F-X tests:** D[follow-through] real vs placebo (y=1, H=24); buildup (a)
  vs (b) difference; false-break P(opposite edge) vs placebo pokes (levels
  P-RAND touched ≥2×). Family size 6.

## 6. M5 — trend lines

- Line = through two consecutive confirmed θ₂ pivots of the same kind,
  drawn at the second pivot's confirmation bar; extended forward until a
  close ≥ tol beyond it or 288 bars.
- **Third-touch event** on a line: first bar whose wick comes within tol of
  the line value at that bar, no line-touch in the prior 24 bars, and a
  close ≥ 1·abr from the line in that window (same freshness machinery).
- **Placebo lines**: for each real line, 2 placebos sharing the anchor
  times and slope (same length), price-shifted by ±δ·abr[t2], δ ~ U{1.5,4}
  seeded per line. Same touch machinery; matched on strata + slope class.
- **Outcomes**: BOUNCE/BREAK/NONE identical to §2 with zlo/zhi =
  line_val(t) ± tol at the touch bar (fixed barriers, M1 path, H=48).
- **Slope rule**: slope class = sign of (p2−p1)/(t2−t1) normalised by abr:
  flat if |s| < 0.02·abr/bar. For LINE_BREAK events (first close ≥ tol
  through an active line), measure P(continuation ≥1·abr before reversal
  ≥1·abr within 24 bars) by slope class × break direction.
- **F-L tests:** D[P_rev] 3rd-touch real vs placebo lines (2 tests: x=1,2);
  slope-class effect on post-break continuation: rising-vs-(flat|falling)
  difference for up-breaks and down-breaks (2 tests). Family size 4.

## 7. M6 — momentum, pullbacks, EMA

- M5 log returns `r_t = log(c_t/c_{t−1})`. Autocorrelation at lags 1–12 and
  variance ratio VR(k) = Var(Σ_k r)/(k·Var r), k ∈ {2,4,8,12,24,48}, per
  session (CET). Day-block bootstrap CIs.
- **Pullback depth**: within θ₂ directional-change trends, depth =
  retrace amplitude / prior leg amplitude; distribution per session
  (descriptive).
- **EMA test**: pullback-end pivots = confirmed θ₁ pivots counter to the
  current θ₂ DC direction. At the pivot extreme bar, distance
  |pivot_price − EMA_L|/abr for L ∈ {15,20,25,35,50}. Test: P(pivot within
  x·abr of EMA25) − P(within x·abr of EMA20) and − EMA50, x ∈ {0.5,1.0}
  (4 tests); also mean rank of |distance| across L (descriptive).
- **F-M tests:** autocorr lag-1..3 per session pooled sign test (descriptive
  primary; 4 formal tests: lag1 by session), VR(12) vs 1 per session
  (4 tests), EMA contrasts (4 tests). Family size 12.

## 8. Statistics and reporting

- Day-block bootstrap (n_boot=2000, seed 20260921) for every CI; the block
  is the server day. Where a pooled stat uses only real events (no
  placebo), the same resampling applies.
- BH-FDR q = 0.10 inside each F-family as listed. An effect is a **stable
  effect** iff it also has the same sign in ≥ 4/6 DESIGN years and ≥ 3/4
  core symbols (per-year/per-symbol D computed with the same strata).
- Effect sizes reported in pips **and** ABR units; per-symbol and per-year
  tables accompany every pooled number.
- Multiple-testing note: descriptive-only outputs (distributions, quantiles)
  are labelled and carry no p-values.

## 9. Causality and integrity

- Every object at bar t uses only bars ≤ t: pivots at their *confirmation*
  bar (not the extreme bar); PDH/ASIA only from completed windows; line
  anchors at confirmation; the box detector reads a trailing window.
- Levels and boxes are frozen once born; pokes never move edges.
- The M1 resolver only reads bars inside the forward window and returns
  first-hit results — no fill semantics, no costs.
- Each result family is appended to the ledger (`kind=market_study`) with
  `spec_sha256` = SHA256 of this file's text and `data_sha256` = SHA256 of
  the per-symbol event tables it consumed.
- Code: `research/market/mk_*.py` only; `lib/` untouched; ≤ 2 `pa_slots`.
