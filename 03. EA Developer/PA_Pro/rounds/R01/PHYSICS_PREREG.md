# R01 PHYSICS_PREREG — zone-generator level-physics bake-off (FROZEN)

Round: R01 · Program: PA-PRO · Authority: `PA_PRO_CHARTER.md` §4 +
`docs/CHARTER_ADDENDUM_1.md` + `docs/CHARTER_ADDENDUM_2.md` + Lead ruling R01-C1
(`rounds/R01/00_LEAD_RULINGS_READ_FIRST.md`) + `research/zones/SHORTLIST.md` §4.
This file is frozen: the SHA256 is recorded in `rounds/R01/FREEZE.json` together
with the harness/generator code hashes and the EVENT/CONTROL table hashes, all
written **before any outcome column exists anywhere on disk**. After the freeze
this file may not be edited; a new version means a new trial.

**NO OUTCOMES HAVE BEEN COMPUTED FOR THIS DOCUMENT.**

---

## 0. DEVIATIONS AND DECISIONS (pre-declared, with the measurement that forced each)

1. **Charter §4 control rule replaced by Addendum 2** (Lead ruling R01-C1; SHA
   `DCB85C81E4D1755D7FA2DD8EF5FD934E4F2B65C62556308AA6BE4F5B964088CE`). Forcing
   measurement (outcome-blind, EURUSD 48 days, line1_cluster): the charter-literal
   "no real zone or reference level within 2 widths" exclusion leaves 2.6% of the
   candidate price space eligible, 85% of real events have essentially zero
   eligible space, realized K = 0.08 controls/event (20 controls for 264 events).
   The replacement is the geometry-matched arbitrary band with no structure
   exclusion except the triggering zone Z itself (A1).
2. **Primary population = ARMED zones** (Lead ruling §1 + SHORTLIST §4). "All
   intact live zones" was the draft's primary; it is retained as a pre-declared
   sensitivity view, **not run this round** (declared: the armed tables are the
   primary object of the families that will consume the winner).
3. **Harness arming parity.** The harness reproduces `gen.views_at(t, arm=True)`
   exactly; parity is certified in `rounds/R01/PARITY.md` (EURUSD 200 bars x 6
   generators, 100 bars x 3 symbols for line1_cluster, **0 mismatches**). The
   pass-state vs replay-state divergence found during parity work (the ZONE-1
   `state_at` replay starts at `born_idx`, the pass at `created_idx`) is resolved
   by replaying each zone once with the generator's own `_step_zone`; no ZONE-1
   file was edited.
4. **Sensitivity views NOT RUN this round** (declared, no selection freedom):
   all-intact-live population, zone width 0.20 vs 0.25 x ATR(H1) for the
   baseline, barriers with A(t) frozen at the anchor, block bootstrap by
   symbol-week, per-scale/per-kind strata (the old perception-spec zone types are
   retired with the old perception spec).
5. **Power floors are the SHORTLIST §4 floors** (>= 1,000 pooled core resolved
   events per generator; >= 60 pooled top-tercile resolved break events for the
   continuation endpoint, else `UNDERPOWERED`), per Lead ruling §4/§6. The
   original ruling-5 request to derive floors from measured counts is satisfied
   by the outcome-blind counts recorded in `FREEZE.json` (all six generators were
   measured; five clear 1,000 comfortably, `profile_va` is expected to be
   UNDERPOWERED).
6. **Costs** AUDUSD/USDCAD/NZDUSD remain 1.4-pip `proxy` and are used only in the
   DESIGN-side viability arithmetic (charter §3); they must be measured before
   any CONFIRM unseal. D1 completeness `min_src=1424` accepted (server 00:00-00:15
   is a data gap); D1 is not used in this run.
7. **Ledger** T000001 (family `X`, smoke) stays per append-only policy and counts
   in the DSR trial number. R01 adds exactly **6 ledger trials** (one per
   generator, `family="PHYSICS"`, `split="DESIGN"`); the 12 hypotheses (6 x 2
   endpoints) are fields of those trials, not extra trials.
8. **EMA25** is allowed as a logged feature and as the PAF-10 anchor (bank note),
   not used in this run.

---

## 1. Question, estimand, falsifier

**Estimand (Lead ruling R01-C1 §2, quoted verbatim):**

> D = P(bounce | fresh approach to an ARMED zone of generator g) − P(bounce |
> fresh approach to a geometry-matched arbitrary band). D is the incremental
> value of using this generator's zones instead of an arbitrary level with the
> same geometry.

- Question (charter §4): does the market respect a generator's zones more than
  geometry-matched arbitrary bands?
- Falsifier: if no generator shows a top-tercile D with 95% CI lower bound > 0
  and D >= +5.0pp after multiplicity correction, LINES MATTER is not supported
  and level-based families are deprioritized (charter §4). Language is exactly:
  a FAIL means *no measurable edge over arbitrary levels of the same geometry*,
  it does NOT mean levels do not exist.
- The run is DESIGN-only and is not an economic evaluation: no fills, no PnL, no
  costs are applied to the proportions (costs enter only the viability
  arithmetic, §8).

## 2. Data, splits, symbols, clock

| item | definition | source |
|---|---|---|
| split | DESIGN 2016-01-01 .. 2021-12-31 only; the loader refuses anything else without an `UNSEAL/` token | charter §3 |
| bars | M5 = complete 5x M1 buckets; `suspect` M1 dropped | `lib/pa_data.py` |
| symbols (gated) | EURUSD, GBPUSD, USDJPY, AUDUSD | charter §3 |
| clock | server UTC+2/+3 through `lib/pa_clock.py` | frozen |
| ATR | Wilder ATR14 on complete H1 buckets; `A(t)` = newest H1 bucket CLOSED at or before the close of M5 bar t | `struct/zones/common.py` |
| warm-up | 30 calendar days before 2016-01-01 for indicators only; warm-up bars can never produce events | charter §3 |
| window semantics | event/outcome windows are bar-index windows over existing bars, gaps skipped | declared |

## 3. Event — FRESH approach to an existing zone (exact)

Zone population: the **ARMED** set at bar t, exactly as the generator computes it
(`views_at(t, arm=True)`: live, not currently broken, center within
`arm_near_atr` = 2.0 x A(t) of the close, dedupe by center within 0.25 x A,
strongest first, cap `arm_max` = 6). Parity with the generator's own arming is
certified in `PARITY.md`.

Let `band_j = [lo_j, hi_j]` be the zone's causal band at bar j. Event at bar t
on zone Z iff **all** hold:

1. **Entry**: `h_t >= lo_t` and `l_t <= hi_t` (bar range intersects the band).
2. **Freshness**: scanning `j = t-1 .. max(0, t-24)`: no bar's range intersects
   its band at j, AND at least one j in that window has close distance
   `max(lo_j - c_j, c_j - hi_j) >= 1.0 x A(t)`.
3. **First entry of the episode**: the bar `t-1` does not intersect its band
   (equivalent to the freshness scan by construction).
4. **Approach side**: `s = -1` iff `c_{t-1} <= lo_t`; `s = +1` iff
   `c_{t-1} >= hi_t`; any other case is rejected and counted.
5. **Usability**: `created_idx <= t - 24`, `t <= end_idx`, state intact
   (`broken is None` at t), strength score available, `A(t)` valid, bar t not
   warm-up.
6. **Dedup**: one event per (zone, episode) by construction; a re-entry without
   an intervening `>= 1.0 x A(t)` away bar cannot fire. Same-zone events within
   48 bars are counted as `overlap` and kept (reported, not filtered).

## 4. Outcome over <= 48 M5 bars (exact)

- Window `j = t+1 .. t+48`; events without all 48 bars are dropped at
  resolution (counted).
- Barrier `m = 1.0 x A(t)` (frozen at the event bar).
- **BOUNCE**: first bar whose range touches `e_near - m` (`s=-1`) /
  `e_near + m` (`s=+1`), where `e_near = lo_t` (`s=-1`) / `hi_t` (`s=+1`).
- **BREAK**: first bar whose **close** is `>= e_far + m` (`s=-1`) /
  `<= e_far - m` (`s=+1`), `e_far` = the other edge.
- **Resolution (adverse-first)**: scan bars in order; if the same bar shows both
  the bounce touch and the break close, **BREAK wins**; otherwise the earlier bar
  wins. **NONE**: neither by t+48.
- Proportions are conditional on resolution: `P(BOUNCE|resolved) =
  n_bounce / (n_bounce + n_break)`; raw shares with NONE in the denominator are
  reported side by side.
- **M1 path note**: M5 bars are complete 5xM1 buckets, so a bar's own high/low
  are the exact M1-path extremes; the "first touch on the M1 path" rule therefore
  reduces to `l_j <= level <= h_j` and within-bar ordering is settled by the
  adverse-first rule above.
- **BREAK continuation analogue**: for BREAK events, `b_b` = break bar, `c_b` its
  close, `side_b = -s`; window `b_b+1 .. b_b+48`: **CONT** = first touch of
  `c_b + side_b * m`; **RETURN** = first touch of the zone midpoint `z_mid`;
  same bar shows both → RETURN wins; resolved = CONT or RETURN; proportion
  `P(CONT|resolved)`.
- For control (arbitrary) bands the identical rules apply with `m = 1.0 x
  A(t_k)` and the band's own midpoint.

## 5. Controls — CHARTER ADDENDUM 2 (binding; replaces the draft §5)

> Per real event, K = 5 matched arbitrary bands: same anchor bar t, same side,
> same width w, near edge at least 1.0 x ATR14(H1)(t) from c_{t-1}, centre drawn
> Uniform over the eligible same-side part of the 5-day range R5, the fake event
> being the first fresh approach under the identical event rules, up to 20
> redraws, per-event seeded RNG. The ONLY placement exclusion is that the fake
> band may not overlap the triggering zone Z itself. No other zone and no
> reference level is excluded.

Implementation details (declared): `R5 = [min(l), max(h)]` over bars
`[t-1440, t-1]`; the eligible same-side interval is
`[max(R5_lo, c_{t-1} + A + w/2), R5_hi]` for `s=-1` and
`[R5_lo, min(R5_hi, c_{t-1} - A - w/2)]` for `s=+1` (negated intervals rejected
as empty slots); per-event RNG `np.random.default_rng([20260920, symbol_ordinal,
t])`; the fake event search is the same scanner over `[t, t+1440]` with the same
side, freshness and away-bar rules; a first approach on the wrong side counts as
a failed draw; fewer than 5 realized controls is logged. Contamination (fake
bands coinciding with real structure) biases D toward zero, never away from it;
it is measured and reported, never corrected.

## 6. Strata and descriptive views

Primary strata (reported per generator): **strength tercile** (per-generator
q33/q67 computed on the POOLED CORE armed event table before any outcome join
and recorded in `FREEZE.json`) x **symbol** x **year** (2016-2021, server year).
Session (Asia 00:00-05:00 / London 05:00-11:00 / NY 11:30-17:30 UTC / off) is
descriptive only. The draft's zone-type stratum is retired with the old
perception spec; generator identity replaces it.

Mandatory descriptive views (Addendum 2 item 4; reported, never gates, never
tie-breaks):

- (i) **contamination rate** per generator: share of realized control events
  whose band overlaps >= 1 ARMED zone of the same generator at the control's own
  event bar `t_k`; plus the share whose band contains >= 1 reference level.
- (ii) **coverage** per generator: median share of the +-2 x ATR14(H1) window
  around the close covered by that generator's armed bands, sampled every 48th
  non-warm-up bar of DESIGN.
- (iii) **S-CLEAN**: D recomputed on clean controls only (no armed-zone overlap
  at `t_k`, no reference level inside the band); events with zero clean controls
  dropped; `N_kept` reported. **S-NEAR**: D restricted to controls with
  `t_k - t <= 288` bars.

Declared interpretation (Addendum 2 item 5): a sparser generator is attenuated
less by contamination than a denser one; selectivity is part of what the
bake-off measures and is not corrected for — coverage is reported so the reader
can see it.

## 7. Statistics, gate, multiplicity, winner rule

Notation: for real event e, `B_e = 1[BOUNCE]`, `R_e = 1[resolved]`; `B_{e,k}` for
its controls. Paired difference `d_e = B_e/R_e - mean_k(B_{e,k}/R_{e,k})`;
pairs with unresolved real events or zero resolved controls are dropped and
counted. `D` = mean(d_e).

- CIs: Wilson 95% per single proportion.
- Primary test: **paired cluster bootstrap** (B = 10,000, seed 20260920),
  resampling real events with replacement, each carrying its own control set;
  percentile 2.5%/97.5% CI; one-sided bootstrap p = `(1 + #{D_b <= 0}) / (B+1)`;
  exact sign test reported as secondary.
- **Gate "LINES MATTER"** (charter §4; per SHORTLIST §4): `D_top >= +5.0pp`, CI
  lower bound > 0, monotone `D_bot <= D_mid <= D_top` (point estimates),
  `D_top > 0` in >= 3/4 core symbols and >= 4/6 DESIGN years; the same
  thresholds for the continuation analogue.
- **Multiplicity**: 6 generators x 2 endpoints = 12 hypotheses; BH-FDR at
  `q <= 0.10` across all 12 (bootstrap p-values); a generator's endpoint is a
  pass only with BH `q <= 0.10` AND the gate thresholds above.
- **Power floors** (SHORTLIST §4): pooled core resolved events >= 1,000 per
  generator, else `UNDERPOWERED` (not a loss); continuation endpoint requires
  >= 60 pooled top-tercile resolved break events, else `UNDERPOWERED`.
- **Winner rule** (SHORTLIST §4, quoted): rank eligible candidates by `D_top`
  (primary endpoint); the ranked leader must beat the BASELINE `line1_cluster`
  by at least +2.0pp absolute in `D_top`, otherwise the baseline is declared
  champion; if no candidate passes the charter thresholds the bake-off is a FAIL
  (LINES MATTER not supported); exact ties (overlapping 95% CIs of the winner
  margin) prefer the baseline, then fewer parameters, then fewer armed zones per
  bar; the winner is the object family for the next round, losers close with
  their measured numbers.
- **Viability arithmetic** (charter §4): `required bias = c_rt / (2m) + 2.00pp`
  per symbol, reported next to the measured top-tercile D.

## 8. Ledger and run plan

- One ledger trial per generator (`family="PHYSICS"`, `round="R01"`,
  `split="DESIGN"`, `symbols` core, `tf="M5"`, `n` = resolved events,
  `spec_sha256` = this file, `params` = generator + control design + freeze
  hash, `key_metrics` = D/CI/p/BH/sensitivities). 6 trials total.
- `FREEZE.json` is written BEFORE outcomes and carries: this file's SHA, the
  Addendum-2 SHA, sorted `struct/zones/*.py`, sorted `research/physics/*.py`
  (less `tests/`), sorted `lib/*.py` hashes, every EVENTS/CONTROLS table hash,
  per-generator q33/q67, coverage, extraction counters, seed, split, symbol
  list, and data-file stamps.
- Outcome resolution, statistics and the results tables run via
  `lib/pa_slots.py` (max 2 of our python processes, 4 threads, BelowNormal).
- No commits, no pushes, no worktrees; writes only under `PA_Pro/`.

## 9. What this prereg deliberately does not do

No fills, no PnL, no costs applied, no ML, no weight calibration, no parameter
search, no post-hoc strata, no reading of any split other than DESIGN, and no
outcome column exists at freeze time.
