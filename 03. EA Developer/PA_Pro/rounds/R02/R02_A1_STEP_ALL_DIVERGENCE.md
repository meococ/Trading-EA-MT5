# R02-A1 — `_step_all` vs exact replay: event-set divergence audit

**Status:** complete (outcome-blind). **Scope:** DESIGN split only, all 4
symbols x all 6 generators. **Date:** 2026-09-21. **Author:** independent
auditor (no R02 authorship).

No outcome field, ledger metric, or outcome-side code was read or executed
anywhere in this audit (`resolve_arrivals`, `arrival_outcome.*`,
`phys_resolve.bounce_cond`, `phys_resolve.cont_cond`, `r02_outcomes/`,
`reexec_r02/out*` — none touched).

---

## 1. What R02's event construction actually is

Chain per (symbol, generator), from `arrival_freeze2.build_symbol`
(`research/arrival/arrival_freeze2.py:96-169`):

1. `ctx = load_ctx(symbol)` — M5 bars, DESIGN window 2016-01-01 → 2022-01-01
   with ≤30 d warmup (`lib/pa_sealed.py:46`, `WARMUP_MAX_DAYS`).
2. `src = GenSource(g, registry.get(g), ctx).run()` —
   `research/physics/phys_source.py:130-133`. Two stages:
   - `gen.run()` → `_on_bar(t)` + `_step_all(t)` per bar
     (`struct/zones/common.py:617-624`, `_step_all` at `:398-442`);
   - `build_timelines()` (`phys_source.py:104-128`) replays `_step_zone`
     from `born_idx` to the *pass-set* `end_idx` per zone and records the
     replayed state changes into `_tl`. **So the states R02 reads are
     already full replays** — the `_step_all` approximation can only leak
     through (a) the zone universe (`_live` membership, `end_idx`
     truncation at pass-observed breaks, `common.py:493-495`) and (b)
     pass-side effects that alter the universe itself (generators reading
     `_live`/`end_idx` inside `_on_bar`).
3. `u_atr = armed_width_atr(src, step=288)` (`arrival_common.py:101`) —
   median armed-zone width in ATR units, sampled every 288 bars.
4. `_grids_events` (`arrival_freeze2.py:85-93`): per server-day segment
   (`day_segments`, `arrival_common.py:89`), `build_day_grid` at the
   day-open bar (`arrival_common.py:114`), then `arrival_events`
   (`arrival_common.py:132`).
   - **Arrival** (D2, `arrival_common.py:21-28`): bar `t` range intersects
     band `G`; no intersection in `[t-24, t-1]`; ≥1 close in that window
     ≥ `1.0 * A(t)` away; side from `c[t-1]`; valid ATR; non-warmup.
     Lookback may cross the day boundary. Band width `w_p = u_atr * 0.75 *
     A(day-open)` (`W_SCALE=0.75`, `arrival_freeze2.py:42`).
   - **Dedup:** none needed — the 24-bar no-intersection rule makes
     arrivals on one band self-separated; distinct bands can co-fire.
5. `tag_arms(ev, src, margins=(0.5,), bars)` (`arrival_common.py:232-312`):
   at `tp = t-1`, TREATED iff an **armed** zone overlaps `G`
   (`armed_views_cached`, `phys_source.py:244-252`); CONTROL iff **no live
   zone** within `0.5 * w_p` (`active_at_fast`, `phys_source.py:211-219`);
   else EXCLUDED. Treated events get `zone_zid` = argmax `(S, -zid)`
   overlapping armed zone (`:277`), `zone_S` (`:276`), `cover` (`:279`),
   `zone_fresh` (`:282-286`).
6. `attach_touches` (`arrival_contrast.py:293-313`): `zone_touches`,
   `zone_since_touch = min(tp - last_touch, 1440)` from
   `state_at(z, tp)` of the argmax zone.
7. **E3 arms** (`arrival_freeze2.py:147-169` + `arrival_contrast.py:267-290`):
   tercile bounds `(q33, q67)` of `zone_since_touch` pooled over treated
   events; `recent = zst <= q33`, `stale = zst >= q67`, else mid.

## 2. The two semantics compared

- **P (as built):** `GenSource(...).run()` verbatim — the `_step_all`
  pass (steps only near-band / pending / warm zones) plus
  `build_timelines` replay. This is exactly what R02 froze.
- **E (exact):** the same generator class driven by a pass that steps
  **every live zone on every bar** — the loop `_step_all` approximates.
  New zones get `z.st` backfilled over `[born_idx, created)` under
  `_replaying` (state only), so `z.st` ≡ the `views_at` replay state at
  every bar; break-observed `end_idx` truncation fires at the true replay
  bar; the retire heap / `_live` / `_reindex` machinery is kept identical.
  This is the `sf_ctx.run_pass` shadow-state convention
  (`families/sf_ctx.py`), generalised to a dense step set.

Both sides then run the identical frozen pipeline above. The P side
reproduces `FREEZE_v3` exactly on all 24 cells (`u_atr`, `n_events`,
`n_treated`, e3 bounds and arm sizes — `freeze_ok=True` everywhere),
which pins the re-implementation to the frozen artifact.

**Grid normalisation (method note).** `arrival_events` depends only on the
price grid, not on zones — so once `u_atr` is fixed, the event *set* is
zone-universe-independent by construction. `u_atr` itself differs slightly
between semantics (armed-zone width median). Results are therefore reported
in two layers: **own-grid** (each side's own `u_atr` — the literal "R02 vs
exact" comparison) and **same-grid** (E pipeline re-run on P's `u_atr` —
isolates the pure semantics effect on arms/state).

**zcache reuse — rejected.** `rounds/SF01/zcache/<SYM>_line1_cluster.npz`
(built by `sf_ctx.build_arrays`, DESIGN M5) stores per bar only the
`SLOTS=10` nearest/strongest zone records (`sf_ctx.py:67,288-299`), while
`zcnt` reaches 28 — the full live set is not recoverable, so
`active_at_fast`/`live_gap` (control arming) cannot be rebuilt from it.
Only `line1_cluster` and `sd_base` caches exist anyway. The replay was
therefore computed directly. (Used for nothing except this inspection.)

**Matching key:** `(bar_idx, glo, ghi)` rounded to 1e-10 — a band instance
on a bar. Under same-grid this matches 1:1 (verified: 0 unmatched both
directions, all 4 symbols). Under own-grid a same-bar fuzzy match
(`|Δglo|,|Δghi| ≤ 0.5·w_p`) is reported separately. Zone identity for
universe/argmax comparisons uses the birth key `(born_idx, created_idx,
lo0, hi0)`, not `zid` (zids renumber after any universe divergence).

## 3. line1_cluster — headline table (same-grid layer)

All events exist under both semantics on the fixed grid; what changes is
their arm tags and zone attributes.

| symbol | n_events | arm flips | % | both-treated | E3 flips¹ | % of both-T | E3-label changes² | % of events |
|---|---|---|---|---|---|---|---|---|
| AUDUSD | 26 267 | 575 | 2.19 | 17 723 | 421 | 2.38 | 890 | 3.39 |
| EURUSD | 24 474 | 533 | 2.18 | 15 704 | 308 | 1.96 | 719 | 2.94 |
| GBPUSD | 24 525 | 531 | 2.17 | 15 454 | 339 | 2.19 | 764 | 3.11 |
| USDJPY | 25 561 | 560 | 2.19 | 17 038 | 335 | 1.97 | 801 | 3.13 |

¹ `zone_since_touch` tercile-class change among events treated under both
semantics (P's bounds applied to both sides; own-bounds counts are
identical — bounds come out equal, e.g. EURUSD `[1.0, 55.0]` both sides).
² events whose E3 membership/label differs = arm flips involving T
(event leaves/enters the treated pool) + class flips among both-treated.

Arm-flip direction detail (same-grid), e.g. AUDUSD: T→X 162, X→T 151,
T→C 70, C→T 86, C→X 61, X→C 45 — roughly symmetric in/out flows.

### Attribute diffs among both-treated events

| symbol | diff argmax zone³ | zone_S | zone_since_touch | zone_touches | zone_fresh |
|---|---|---|---|---|---|
| AUDUSD | 1 077 (6.1%) | 1 124 (6.3%) | 745 (4.2%) | 1 159 (6.5%) | 259 (1.5%) |
| EURUSD | 876 (5.6%) | 901 (5.7%) | 603 (3.8%) | 965 (6.1%) | 206 (1.3%) |
| GBPUSD | 896 (5.8%) | 912 (5.9%) | 608 (3.9%) | 979 (6.3%) | 232 (1.5%) |
| USDJPY | 870 (5.1%) | 903 (5.3%) | 588 (3.5%) | 958 (5.6%) | 225 (1.3%) |

³ genuinely different physical zone selected as argmax (birth-key match);
the raw `zone_zid` field differs on ~98% of both-treated events but that
mostly reflects zid renumbering after universe divergence, so it is not
reported as a semantic difference.

### Own-grid layer (literal event-set question)

| symbol | u_atr P→E | Δ% | n_ev P→E | exact-key matches | same-bar fuzzy matches |
|---|---|---|---|---|---|
| AUDUSD | 0.50963→0.50947 | −0.03 | 26 267→26 266 | 0 | 26 191 (99.7%) |
| EURUSD | 0.50870→0.50855 | −0.03 | 24 474→24 488 | 0 | 24 432 (99.8%) |
| GBPUSD | 0.50890→0.50751 | −0.28 | 24 525→24 587 | 0 | 24 063 (98.1%) |
| USDJPY | 0.50963→0.50822 | −0.28 | 25 561→25 633 | 0 | 25 032 (97.9%) |

The grid shift is small but moves every band edge, so literal `(bar,band)`
keys never collide; ~98–99.8% of P events have a same-bar counterpart
under exact semantics (the rest are bands that moved >0.5·w_p or
appeared/disappeared at grid edges). Event *count* changes ≤ +0.6%.

### Universe divergence (mechanism)

| symbol | zones P→E | only-P / only-E⁴ | shared w/ end changed | earlier in E | later in E |
|---|---|---|---|---|---|
| AUDUSD | 15 862→15 892 | 605 / 635 | 1 548 (10.1%) | 1 071 | 477 |
| EURUSD | 16 650→16 687 | 519 / 556 | 1 846 (11.4%) | 1 283 | 563 |
| GBPUSD | 16 692→16 720 | 538 / 566 | 1 856 (11.5%) | 1 306 | 550 |
| USDJPY | 16 210→16 240 | 505 / 535 | 1 682 (10.7%) | 1 198 | 484 |

⁴ zones whose birth key exists under only one semantics — `_on_bar`
consults `_live` (e.g. `line1_cluster` pivot-merge, `sd_base` center-block),
so retirement differences cascade into creation.

Counter evidence (AUDUSD; other symbols identical pattern):
`zone_flip` 934 → 4 025 (**the pass observes only ~23% of flips**),
`zone_reclaim` 36 534 → 38 239 (+4.7%, the missed-late-reclaim channel),
`zone_break` 42 262 → 42 671 (+1.0%, missed gap-bar breaks → zombies live
longer: `zone_touch` 447 704 → 445 728, i.e. zombie zones keep accruing
touches under the pass). `end_idx` moves **earlier** under exact ~2.3x
more often than later — the dominant mechanism is exactly the predicted
one: `_step_all` misses breaks/reclaims on bars that never come near the
band, so zones survive longer and with staler state than `views_at` would
give.

Secondary check: live-overlap (E2-style "any live zone overlaps band")
flips on P events: 361/343/347/340 per symbol (~1.4%).

## 4. Other five generators (same-grid layer)

| gen | symbol | n_ev P→E | arm flips (%) | E3 flips | end_idx changed |
|---|---|---|---|---|---|
| fractal_h1 | AUDUSD | 40 538→40 550 | 129 (0.32) | 21 | 414 |
| | EURUSD | 36 597→36 612 | 134 (0.37) | 20 | 505 |
| | GBPUSD | 36 662→36 662 | 142 (0.39) | 21 | 462 |
| | USDJPY | 38 917→38 932 | 185 (0.48) | 23 | 499 |
| sd_base | AUDUSD | 41 132→41 202 | 248 (0.60) | 5 | 325 |
| | EURUSD | 36 171→36 171 | 220 (0.61) | 11 | 311 |
| | GBPUSD | 36 823→36 847 | 247 (0.67) | 5 | 409 |
| | USDJPY | 41 021→41 035 | 251 (0.61) | 7 | 376 |
| kde_swing | all 4 | 20 853–22 402 | 0–4 (≤0.02) | 0–4 | 8–17 |
| profile_va | all 4 | 19 293–22 250 | 4–16 (≤0.08) | 0–2 | 1–9 |
| ref_levels | all 4 | 47 555–52 803 | 0–1 (≤0.00) | 0–1 | 0 |

`kde_swing`, `profile_va`, `ref_levels` are effectively immune (their
`_on_bar` barely consults `_live` and their zones retire on simple rules);
`fractal_h1` and `sd_base` show a milder version of the same mechanism.

## 5. Sampled mismatch reasons (line1_cluster)

One-line diagnoses for the first mismatches (EURUSD / AUDUSD cells):

1. bar 5931 EURUSD T→X — argmax zone retired 544 bars earlier under exact
   (missed break → zombie under pass).
2. bar 5937 EURUSD E3 stale→recent — same zone retired 2 071 bars earlier.
3. bar 6786 EURUSD E3 stale→recent — different physical argmax zone.
4. bar 7220 EURUSD C→T — armed set differs at same live universe
   (arming window content changed).
5. bar 8216 EURUSD E3 recent→stale — argmax retired 788 bars earlier.
6. bar 5843 AUDUSD X→T — zone still live under pass; exact retired it
   (zombie armed the band).
7. bar 9692 AUDUSD T→X — argmax retired 1 253 bars earlier under exact.
8. bar 10552 AUDUSD T→C — argmax retired 400 bars earlier; live-gap
   boundary also moved.
9. bar 11488 AUDUSD T→X — argmax retired 975 bars earlier.
10. bar 6032 EURUSD C→X — live-gap boundary crossed (a ±1-zone difference
    near `margin·w_p`).

Recurring pattern: the exact side retires zones earlier (missed breaks
under pass), sees more reclaims and ~4–5x more flips, and the different
live set occasionally changes which armed zone overlaps the band.

## 6. Plain statement for the claim unit (E3 / line1_cluster)

Holding the event grid fixed, **the `_step_all` approximation does not add
or remove a single event** (arrival eligibility is zone-independent); it
changes the grid itself only through `u_atr` drifting ≤0.28% relative
(≥97.9% of events keep a same-bar counterpart). What it does change:
**~2.2% of events flip arm** (Treated/Control/Excluded) and **~2.0–2.4%
of both-treated events flip E3 recent/stale class**; counting membership
changes in/out of treated, **~2.9–3.4% of all events carry a different E3
label** under exact replay. Among treated events, ~5–6% select a
genuinely different argmax zone and ~4–7% see a changed zone-state field
(`zone_S`, `zone_touches`, `zone_since_touch`, `zone_fresh`).

So: "the approximation changes ~0% of events on a fixed grid (the grid
itself shifts ≤0.3%, perturbing ≤2% of event bands beyond half-width) and
~2.2% of arm assignments / ~2–3.4% of E3 recent-stale labels." Whether
that biases R02's E3 contrast is an outcome question and is deliberately
not addressed here.

## 7. Reproduction

Script: `research/arrival/_scratch/r02_a1/audit_step_all.py`
(`run_exact` = dense-step pass; `run_pipeline` = verbatim freeze2 chain;
`compare` = 3-run diff). Per-cell JSONs in `_scratch/r02_a1/cells/*.json`;
physical-zone addendum `cells/<SYM>_line1_cluster_phys.json`. Run: one
`pa_slot`, BelowNormal, ~20 min wall clock for all 24 cells.

## 8. Open

- `zone_since_touch` uses `state_at` on the argmax zone — where the argmax
  zone differs physically (~5–6% of treated), the E3 flip may reflect a
  *different zone's* history rather than a state error per se; the table
  reports the net effect either way, which is what R02 consumed.
- zcache files were inspected but not reused (truncated to 10 of ≤28 live
  zones per bar); the audit's E pass is a fresh dense-step replay. It was
  sanity-checked: `armed_views_cached` ≡ `gen.views_at` on 400 random bars
  per cell, 0 diffs, on the P source.
- The `run_exact` code was hardened after the run to mirror `_step_all`'s
  invalid-ATR early-return literally; ATR is invalid only on bars 0–166
  (before any zone exists), so the reported numbers are unaffected.
- No statement about outcome sensitivity of the E3 estimate is made or
  implied; that requires the sealed outcome lane.
