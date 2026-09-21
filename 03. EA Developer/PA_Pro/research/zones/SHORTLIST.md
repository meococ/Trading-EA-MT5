# SHORTLIST — zone generators for the R01 preregistered physics bake-off (T-PAPRO-ZONE-1)

Status: **frozen candidate list + frozen defaults** for the zone-generator bake-off of
`docs/CHARTER_ADDENDUM_1.md` item 4. Every number in this file is pre-declared NOW, before any
outcome exists. This task computed **no outcomes** (no bounce/break rates, no returns, no win
rates, no fills) and read no bar after a decision bar for any statistic or picture. The physics
run itself is R01 (charter §4, `rounds/R01/PHYSICS_PREREG_DRAFT.md`) and is the only place where
reaction proportions may be measured.

Authority chain: Owner request 2026-09-20 19:18 → `docs/CHARTER_ADDENDUM_1.md` → `PA_PRO_CHARTER.md`
§4 → this file → `struct/zones/` code. The survey behind the candidate choices is
`research/zones/INDICATOR_SURVEY.md` (39 generator candidates) + `_legacy_kills.md`.

Candidate list (6), in registry order (`struct/zones/registry.py`):

| # | name | module / class | family | scale | source family in the survey |
|---|---|---|---|---|---|
| 1 | `line1_cluster` | `line1_cluster_zones.py` / `Line1ClusterZones` | **BASELINE**: LINE-1 M5 lag-3 swing clusters converted to zones | micro | existing LINE-1 seed (`EA_VolmanPA/research/lines/vpa_lines.py`) |
| 2 | `fractal_h1` | `fractal_zones.py` / `FractalZones` | H1 pivot S/R zones (pivot-cluster family) | meso | MT4 "Smart S/R Zones", TV #2.3/#2.5, "ATR-ranked" family |
| 3 | `kde_swing` | `kde_swing_zones.py` / `KdeSwingZones` | kernel-density of swing prices (adaptive width) | micro/meso | `scipy.gaussian_kde` / `sklearn.KernelDensity` methods |
| 4 | `profile_va` | `profile_zones.py` / `ProfileZones` | time-at-price value area (POC/VA70) | macro | `marketprofile` / TV Volume Profile / MT5 Volume Profile Levels |
| 5 | `sd_base` | `sd_base_zones.py` / `SdBaseZones` | supply/demand base + impulse | micro | ExMachina S&D, Miron SupplyDemandZones, TV #2.8 |
| 6 | `ref_levels` | `ref_zones.py` / `RefZones` | non-swing references (PDH/PDL/PDC, Asia, week, round 00/50) | meso/macro | PERCEPTION_SPEC O3-O6; round numbers (Osler 2000/2003) |

All six were implemented, unit-tested and prefix-invariance-tested; 50 tests pass
(`struct/zones/tests/`, see `EVIDENCE` in the report). All six ran on DESIGN EURUSD M5 and are
rendered on the same 8 seed-frozen windows (`research/zones/WINDOWS.json`, seed 20260920) as
shaded bands in `research/zones/snapshots/<generator>/` with `snapshots/INDEX.csv`.

---

## 1. Common contract (frozen; implemented in `struct/zones/common.py`)

**Interface.** `Gen(ctx).run()` then `zones_at(t) -> list of {lo, hi, kind, strength, born_idx,
touches, fresh}` (plus diagnostics: `zid, scale, n_respected, broken_idx, role_flip, age,
last_touch, quality, parts`). `views_at(t)` returns the same objects; `counts_at(t)` returns
(live, armed).

**Causality (binding).**
- Every object at bar `t` uses bars `<= t` only. Pivots are confirmed late with an explicit lag:
  M5 lag-3 swings at `j+3`; H1 lag-2 fractals at the close of H1 bucket `j+2` (mapped to the
  first M5 bar whose close reaches it); ATR14(H1) is the newest H1 bucket CLOSED at or before the
  decision bar (the bucket containing `t` is never used).
- Zone geometry and generator quality have step histories (`geom_hist`, `qual_hist`), so a query
  at a past bar cannot see a later widening/update.
- Queries replay the same state machine the pass used and are side-effect free
  (`common.ZoneGen.state_at`); prefix invariance is tested for every generator on synthetic and
  real data (`tests/test_prefix_invariance.py`).
- **LINE-1 note (binding).** The LINE-1 engine's `_htf_align` scoring is known to use future
  swings (being fixed in the LINE-1 session, per the Lead's resume message). NO candidate here
  uses LINE-1 scoring, `_htf_align`, or the LINE-1 armed-line set. The baseline reuses ONLY the
  `_confirm_swings` rule (`vpa_lines.py:436-450`), and its parity with that rule is asserted in
  `tests/test_line1_parity.py`.

**Width rule (addendum 1 item 1).** Zone bands are always `[lo, hi]` with width in
`[0.20, 0.60] x ATR14(H1)` measured at band creation. Generators that absorb new members cap the
merged band at 0.6 x A. A band created under a larger A can be wider than 0.6 x A(t) later; that
is an honest consequence of ATR scaling and is reported in `snapshots/INDEX.csv`
(`width_atr_med`), not hidden.

**State machine (same for all candidates).**
- TOUCH: bar range intersects `[lo, hi]`; episodes >= 2 bars apart. A wick through the band that
  closes back inside is a touch, not a break.
- RESPECTED: a touch followed within 48 bars by a close `>= 1.0 x ATR14(H1)` away from the near
  edge on the approach side and no break first.
- BREAK: a close through the zone to the FAR side of its role by `> 0.10 x ATR14(H1)` (ceiling
  breaks up, floor breaks down; no role before the first touch, so no break). A close back on the
  approach side is a test, never a break.
- RECLAIM (BREAK_FAIL): close back inside within 96 bars → intact again, pre-break role.
- FLIP_CONFIRMED: reclaim window lapses with price still beyond → role flips (T_role = 1).
- FRESH: intact and no touch in the last 24 bars.
- RETIRE: generator `max_age_bars`, or `break + 192` bars.

**Strength v0 (pre-declared weights, sum 1.00).**

```
S = 0.30*T_touch + 0.20*T_resp + 0.15*T_rec + 0.10*T_age
  + 0.10*T_scale + 0.05*T_role + 0.05*T_ref + 0.05*T_qual
T_touch = min(1, touches/4)          T_resp = min(1, n_respected/3)
T_rec   = exp(-(t-last_touch)/288)   T_age  = min(1, age_bars/288)
T_scale = 0.4 micro | 0.7 meso | 1.0 macro
T_role  = 1 iff FLIP_CONFIRMED       T_ref  = min(1, (n_ref + n_round)/2)  (refs.py)
T_qual  = min(1, quality / QUAL_REF)  -- generator-specific, table below
T_vol   = 0 for every candidate (the PA-PRO loader has no tick volume; uniform term)
```

Three terms are deliberately outside this v0: `T_conf`-style reference confluence is carried by
`T_ref` instead of the PERCEPTION_SPEC split, and `T_vol` is a declared zero for all candidates
(a uniform term cannot affect within-generator ranking). The weights are frozen for the physics
run; any calibration afterwards is a new ledger trial (charter :121-122).

**Arming rule (addendum 1 item 3).** Armed at `t`: live and `broken_idx is None` (a
currently-broken zone stays in the live book for diagnostics but is never armed; a role-flipped
zone is intact in its new role and can arm — the prereg's broken-then-reclaimed table is
secondary), center within `2.0 x ATR14(H1)` of the close; a weaker candidate whose center is
within `0.25 x ATR14(H1)` of an already-armed stronger zone is dropped; at most `6` armed,
strongest first. The bake-off's event population is the ARMED set (charter §4 + addendum item 3);
the full live book is reported for diagnostics. Enforced in `common.arm_zones` and tested by
`test_armed_excludes_broken`.

**Declared generator quality terms.**

| generator | quality input | QUAL_REF | saturates at |
|---|---|---|---|
| `line1_cluster` | cluster member count (M5 swings) | 2.0 | 2 members |
| `fractal_h1` | cluster member count (H1 pivots) | 2.0 | 2 members |
| `kde_swing` | peak density / (peak + median peak of the refresh) | 1.0 | q≈1 |
| `profile_va` | POC bin weight / mean VA bin weight | 3.0 | 3x mean |
| `sd_base` | impulse displacement / ATR14(H1) | 2.0 | 2.0 x A |
| `ref_levels` | 1.0 (references declared inherently strong; uniform) | 1.0 | always 1 |

---

## 2. Per-generator spec (defaults frozen)

### 2.1 `line1_cluster` — BASELINE (LINE-1 swing clusters → zones)

**Algorithm.** Consume confirmed +-3-bar M5 swings (LINE-1 `_confirm_swings` rule). A new swing
is absorbed into the nearest live `swing` zone whose band at the confirm bar is within
`link_atr x A` of the price and whose merged band stays `<= 0.6 x A`; otherwise it seeds a zone
`[price - w/2, price + w/2]`. Highs and lows cluster together (role reversal is one zone). Age is
dated from the swing bar, availability from its confirm bar (LINE-1 `_seed_levels` convention).

| parameter | value | parameter | value |
|---|---|---|---|
| `pivot_lag` | 3 | `width_atr` | 0.25 |
| `scan_bars` | 240 | `max_width_atr` | 0.60 |
| `link_atr` | 0.25 | `max_age_bars` | 2880 (10 days) |

**Merge rule.** single-link within 0.25 x A, cap 0.6 x A. **Freshness/retirement.** common rules,
`max_age` 10 days. **Scale.** micro (T_scale = 0.4). **Measured** (50k EURUSD M5 bars):
1845 zones created, live 12-25, armed 4-6; on the 8 windows armed avg 5.38, max 6.

**Why it could beat / must be beaten.** It is the incumbent object: LINE-1's swings were audited
to coincide with the frozen DR3 micro-barriers (LINE_AUDIT). Converting them to ATR zones with a
0.25 x A link is the minimal delta that satisfies the Owner's "areas, not lines" direction. The
bake-off asks whether any other structural family beats this baseline; it also gives the baseline
its first honest reaction measurement (DR3/ECON-1 measured PnL, not zone physics).

### 2.2 `fractal_h1` — H1 pivot S/R zones (meso)

**Algorithm.** Confirmed +-2-bar H1 fractals, mapped to M5 confirm bars. Past-leg prominence
filter: a high qualifies when `price - min(H1 low over [j-12, j]) >= 0.40 x A` at the confirm
bar (and symmetric for lows), i.e. only structure a pro would call a swing. Qualified pivots are
absorbed into the nearest live `swing_h1` zone within `link_atr x A` while the merged band stays
`<= 0.6 x A`, else seed `[price - 0.30 x A/2, price + 0.30 x A/2]`.

| parameter | value | parameter | value |
|---|---|---|---|
| `pivot_k` (H1) | 2 | `width_atr` | 0.30 |
| `prom_lookback` (H1 bars) | 12 | `link_atr` | 0.30 |
| `prom_atr` | 0.40 | `max_width_atr` | 0.60 |
| `scan_bars` (M5 stale guard) | 480 | `max_age_bars` | 5760 (20 days) |

**Merge rule.** single-link 0.30 x A, cap 0.60 x A. **Scale.** meso (0.7). **Measured:**
674 zones created / 50k bars (6111 over the full 2016-2021 DESIGN slice), armed avg 2.50 on the
8 windows, max 4.

**Why it could beat the baseline.** The baseline's M5 lag-3 pivots are micro structure (a swing
that stands out over 15 minutes). A pro's chart is H1-scale structure with a prominence filter;
this candidate spends its zone budget on fewer, larger swings and older zones (20 days), which
should raise the respected-test rate if zone physics is scale-dependent.

### 2.3 `kde_swing` — kernel-density swing zones

**Algorithm.** Sample confirmed M5 lag-3 and H1 lag-2 pivots from the last `window_bars` = 1440
bars, weighted by past-leg prominence clipped to `[0.2, 1.5] x A`. Every `refresh_bars` = 24
bars, build a 160-point price grid and a Gaussian kernel density `h = 0.20 x A`; peaks (local
maxima >= `0.50 x max`) become zones whose half-maximum support is clipped/widened to
`[0.20, 0.60] x A` around the peak; peaks link to an existing live zone within `0.25 x A` (band
replaced, quality refreshed). `T_qual` = peak height normalized by the refresh's own peak median;
scale is meso when the H1 weight share in the half-max region >= 0.5.

| parameter | value | parameter | value |
|---|---|---|---|
| `refresh_bars` | 24 | `bandwidth_atr` | 0.20 |
| `window_bars` | 1440 | `peak_frac` | 0.50 |
| `grid_n` | 160 | `link_atr` | 0.25 |
| `w_clip` | [0.20, 1.50] | `min/max_width_atr` | 0.20 / 0.60 |
| `max_age_bars` | 2880 | | |

**Why it could beat the baseline.** Width becomes data-driven (half-max support) instead of a
fixed 0.25 x A, and zone strength is a density height rather than a raw touch count. If the
market's memory sits in swing *clusters* rather than at a single level, KDE zones should place
their edges where the crowd actually transacts and score better in the top strength tercile.
**Measured:** 570 zones created / 50k bars, armed avg 2.50 on the 8 windows, max 5.

### 2.4 `profile_va` — time-at-price value area

**Algorithm.** At each server-day rollover, build a time-at-price histogram over the trailing
1440 M5 bars on a `0.10 x A` price grid (each bar spreads its range uniformly across the bins it
covers). POC = heaviest bin; the value area grows from the POC by repeatedly adding the larger
neighbour until `70%` of window weight is included. One `profile_poc` zone per day: band
`[VAL, VAH]` re-centred on the POC when clipped/widened to `[0.20, 0.60] x A`. `T_qual` = POC bin
weight / mean VA bin weight (saturates at 3x).

| parameter | value | parameter | value |
|---|---|---|---|
| `window_bars` | 1440 (5 days) | `va_frac` | 0.70 |
| `bin_atr` | 0.10 | `min/max_width_atr` | 0.20 / 0.60 |
| `max_bins` | 800 | `max_age_bars` | 2880 |

**Why it could beat the baseline.** This is a completely different information source (where time
was spent, not where swings stopped) and the survey flagged it as orthogonal to all pivot
families. **Measured caveat (pre-declared expectation):** day-anchored POC zones drift away from
price on trends; on the 8 windows this generator armed 3 zones total (avg 0.38, max 2) and **six
of the eight windows show 0 armed zones** (only windows 3 and 4 arm 1 and 2). It is expected to
be the event-poorest candidate and may be marked UNDERPOWERED by the power floor rather than lose
on the point estimate.

### 2.5 `sd_base` — supply/demand base + impulse zones

**Algorithm.** At each bar, scan base lengths `nb` 1..3 and impulse lengths `k` 1..6: the base
`[t-k-nb+1 .. t-k]` must be tight (`max(h) - min(l) <= 0.35 x A`); a demand structure exists when
`c[t] - max(h[base]) >= 1.2 x A` (supply symmetric). Emit one zone per bar for the largest
displacement; band = base range padded by `0.05 x A`, widened/clipped to `[0.20, 0.60] x A`;
dedupe by same-kind live-zone center within `0.25 x A` and by used base bar +-1. `T_qual` =
displacement / A (saturates at 2.0 x A).

| parameter | value | parameter | value |
|---|---|---|---|
| `base_max_bars` | 3 | `imp_min_atr` | 1.2 |
| `imp_max_bars` | 6 | `pad_atr` | 0.05 |
| `base_range_atr` | 0.35 | `dedupe_atr` | 0.25 |
| `min/max_width_atr` | 0.20 / 0.60 | `max_age_bars` | 1440 (5 days) |

**Why it could beat the baseline.** The base is where a professional says "this is where the
seller/buyer was"; the object is anchored to a specific price *event* (impulse) rather than a
pivot extremum, and its band comes from the base's own range. If zone physics is about order
placement and absorption, base zones should be more respected than swing clusters. (Legacy S/D
*strategies* were killed as trade chains; the zone physics of the base object itself was never
measured — see `_legacy_kills.md` §12.) **Measured:** 304 zones created / 50k bars, armed avg
1.00 on the 8 windows, max 3.

### 2.6 `ref_levels` — day/session/week references + round numbers

**Algorithm.** Publish 0.25 x A bands at the bar each level becomes knowable: PDH/PDL/PDC at the
server-day rollover, Asia high/low at the first bar after the UTC 00:00-05:00 window, previous
week high/low at the Monday rollover, and the nearest 00/50 grid prices above/below the rollover
close. Each slot keeps only its newest zone (explicit retirement); same-kind coincidences within
0.25 x A are deduped and carried over. `T_qual = 1.0` for all references (declared).

| parameter | value |
|---|---|
| `width_atr` | 0.25 |
| `dedupe_atr` | 0.25 |
| `max_age_bars` | 2880 (backstop; rollover retire is primary) |

**Why it could beat the baseline.** These are the levels a discretionary trader actually marks
before the session; the survey's Osler strand is specifically about round numbers and stops.
`ref_levels` is the non-swing control arm: if physics passes for references but not for swing
clusters, the whole cluster family is the wrong object. **Measured:** 1284 zones created / 50k
bars (11402 over the full 2016-2021 DESIGN slice), armed avg 3.00 on the 8 windows (max 4), the
highest non-baseline armed count.

---

## 3. Measured diagnostics (no outcomes; DESIGN EURUSD M5, 50,000 bars + the 8 windows)

`python struct/zones/diagnostics.py --max-bars 50000` (2026-09-20):

| generator | run s | zones created | live (5 sampled bars) | armed (5 sampled bars) | width/A median |
|---|---|---|---|---|---|
| `line1_cluster` | 0.7 | 1845 | 25,20,18,12,20 | 6,4,6,6,6 | 0.50 |
| `fractal_h1` | 0.2 | 674 | 15,21,14,10,15 | 3,1,4,1,3 | 0.32 |
| `kde_swing` | 1.2 | 570 | 9,7,9,13,15 | 3,0,3,5,2 | 0.60 |
| `profile_va` | 0.6 | 177 | 4,4,3,6,8 | 1,0,1,0,0 | 0.54 |
| `sd_base` | 0.4 | 304 | 5,3,5,7,4 | 1,0,1,3,0 | 0.32 |
| `ref_levels` | 0.3 | 1284 | 7,9,9,8,9 | 2,1,4,4,3 | 0.27 |

Armed counts on the 8 frozen windows (`snapshots/INDEX.csv`, after the arming fix that excludes
currently-broken zones): `line1_cluster` avg 5.38 (max 6), `ref_levels` 3.00 (max 4), `fractal_h1`
2.50 (max 4), `kde_swing` 2.50 (max 5), `sd_base` 1.00 (max 3), `profile_va` 0.38 (max 2). Every
generator respects the chart-hygiene cap of 6 armed zones.

Snapshots: 48 PNGs, `research/zones/snapshots/<generator>/win_<i>_<UTC>.png`, same 8 windows for
every generator, bands shaded, opacity = 0.10 + 0.55 x strength, current close marked, no bar
after the decision bar drawn; metrics in `snapshots/INDEX.csv`; window seed record
`research/zones/WINDOWS.json` (seed 20260920, written before the first render).

---

## 4. Bake-off decision rule (pre-declared, with multiplicity correction)

**Runs.** In R01, each of the 6 candidates is frozen at the defaults of this file and run through
the SAME preregistered physics test (`rounds/R01/PHYSICS_PREREG_DRAFT.md` §3-§7: fresh approach
to an armed zone, BOUNCE / BREAK / NONE over <= 48 M5 bars with symmetric `m = 1.0 x ATR14(H1)`
barriers, K = 5 matched fake zones per event, seed 20260920, DESIGN only, core symbols,
M5 with H1 context). Every candidate run is ONE ledger trial (`family="zone_physics"`,
`spec_sha256` = the frozen candidate spec). No fills, no PnL, no costs enter this run.

**Endpoints.** Primary: `D_top` = pooled top-tercile `P(BOUNCE|resolved)` minus the matched-fake
control, on the ARMED zone population. Secondary: the break-continuation analogue
`D_cont_top` (charter §4). Both are reported per symbol, per year, per strength tercile.

**Eligibility (pre-declared power floors).**
1. Pooled core resolved real events >= 1,000, else the candidate is `UNDERPOWERED` (not a loss).
2. For the continuation endpoint only: >= 60 pooled top-tercile resolved break events, else
   `UNDERPOWERED` for that endpoint.

**Multiplicity.** 6 candidates x 2 endpoints = 12 hypotheses. The p-value per candidate is the
one-sided paired-cluster-bootstrap tail of `D <= 0` (B = 10,000, same construction as the
prereg). BH-FDR at `q <= 0.10` is applied across all 12; a candidate's endpoint is a "pass" only
with BH q <= 0.10 AND the charter threshold (`D >= +5.0pp`, bootstrap 95% CI lower bound > 0,
monotone `D_bot <= D_mid <= D_top`, `D_top > 0` in >= 3/4 core symbols and >= 4/6 DESIGN years).
The program-level trial count for later Deflated-Sharpe accounting includes these 12 trials.

**Winner rule (pre-declared).**
1. Rank eligible candidates by `D_top` (primary endpoint).
2. The ranked leader must beat the BASELINE (`line1_cluster`) by at least `+2.0pp` absolute in
   `D_top`; otherwise the baseline is declared the champion (the incumbent keeps its place unless
   a challenger is materially better — the pre-declared materiality margin).
3. If no candidate passes the charter thresholds, the bake-off is a FAIL: LINES MATTER is not
   supported and level-based families are deprioritized (charter :123-124). The baseline is not
   promoted by default.
4. Exact ties (within the bootstrap noise, i.e. overlapping 95% CIs of the winner margin):
   prefer the baseline, then the generator with fewer parameters, then the one with fewer armed
   zones per bar (chart hygiene). This tie-break order is fixed now.
5. The winner is the object family for the next round; losing candidates are closed with their
   measured numbers, and any parameter change to a loser is a NEW candidate/spec in a new round
   (never a post-hoc rescue, `do_not_repeat_failures.md:3-8`).

**Pre-declared sensitivity views (reported, never used to select):** width 0.20 vs 0.25 x A for
the baseline; barriers with `A(t)` frozen at the anchor; block bootstrap by symbol-week; the
secondary continuation endpoint; per-scale and per-kind strata. These are unchanged from
`PHYSICS_PREREG_DRAFT.md` §7 and add no new selection freedom.

**What is explicitly NOT in the bake-off decision:** any outcome on this task's data, any
bounce/break count, any return/PnL, any per-generator parameter search, any winner chosen by
looking at the snapshots (the snapshots are a perceptual hygiene check only), and any reuse of a
killed legacy strategy (round-number fade, PDH/PDL sweep fade, VWAP/volume-clock fade, OB/SMC/FVG
chains, DR3 micro-line breaks, fractal-sweep trades — `_legacy_kills.md`).

---

## 5. No-outcomes statement (task T-PAPRO-ZONE-1)

This task produced zone OBJECTS and their pictures only. It computed no outcome of any kind:
no bounce/break rates, no returns, no win rates, no fills, no PnL, no forward-looking statistic,
and no bar after a decision bar was drawn or used in any measurement. Every generator, test and
snapshot here is causal (bars <= decision bar) and prefix-invariance-tested. The preregistered
physics bake-off that decides the winner is R01 and has not been run.
