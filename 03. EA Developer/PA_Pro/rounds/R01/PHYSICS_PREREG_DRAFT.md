# R01 PHYSICS_PREREG — "do LINES MATTER?" — **DRAFT** (not frozen; frozen at R01 start)

Task: `PA_PRO_CHARTER.md` §4 ("Level physics — the first market question"), lines 103-124. This file is a
**draft of the preregistration**, written in R00 before any perception code exists. It gets frozen at the
start of R01 (SHA recorded together with the perception code SHA and the event table, **before any outcome
is computed**). Until frozen it may be edited; after the freeze it may not (a new version = a new trial).

**NO OUTCOMES HAVE BEEN COMPUTED FOR THIS DOCUMENT.** Every number below is either a published
measurement (ATR tables, costs) or arithmetic on those published measurements, as labelled. Cost
provenance: charter §3 :96-98, `docs/COSTS.md:21-29` (sub-agent B's table, landed during this draft and
identical to the charter fallback), `lib/pa_costs.py:40-57`. AUDUSD/USDCAD/NZDUSD remain `proxy` 1.4 per
charter :97-98 and `COSTS.md:26-29` (§6 of that file documents the failed cost-evidence search).

Object definitions used here are in `struct/PERCEPTION_SPEC.md` (zones O2/O3/O4/O5/O6, events E1/E3, lags
§4, strength v0 §5). That spec is the L1 contract this experiment consumes.

---

## 1. Question, falsifier, decision rule

- Question (charter :104-105): does the market respect our zones more than matched fake zones? Osler-style test.
- Falsifier: if real zones are no more respected than matched fake zones, then level-based families are
  deprioritized and the loop continues with the other families (charter :123-124). A FAIL is a clean,
  publishable answer, not a retreat.
- The physics run is **DESIGN-only** and is **not** an economic evaluation: no fills, no PnL, no costs are
  applied to the proportions (cost enters only in §8 arithmetic). It still uses the referee discipline for
  timing/tie rules so that later setups inherit the same semantics.

## 2. Data, splits, symbols, clock

| item | definition | source |
|---|---|---|
| split | DESIGN 2016-01-01 .. 2021-12-31 only. No VAL/OOS/HOLDOUT read; the loader refuses outside DESIGN without an `UNSEAL/` token | charter :84-94 |
| bars | M5 = complete 5x M1 buckets; `suspect` M1 bars dropped; only complete M5 bars | charter :80-81; method `DATA_INVENTORY.md:41-53`, `vpa_data.py:33-53` |
| M1 path | for tie resolution only (§4), from the same cache, same suspect filter | charter :71-72 |
| clock | server UTC+2/+3 via `lib/pa_clock.py` (frozen `eu_server_offset_hours` semantics, mod-1440 wrap) | charter :82-83; `pa_clock.py:11-24`, `vpa_random_baseline.py:60-70`, `vpa_data.py:55-61` |
| H1 context | complete server-hour buckets from M1, Wilder ATR14 | `DATA_INVENTORY.md:45-53` |
| symbols (core, gated) | EURUSD, GBPUSD, USDJPY, AUDUSD | charter :95 |
| symbols (extended, reported only) | USDCAD, USDCHF, NZDUSD | charter :95 |
| warm-up | max 30 calendar days before 2016-01-01 for indicator bootstrap only; never produces events | charter :93-94 |

Event/outcome windows are bar-index windows (existing M5 bars, gaps skipped), never calendar spans.
Weekend/holiday gaps therefore shorten nothing: "previous 24 bars" means the previous 24 existing M5 bars
(`ASSUMPTION:` declared here in advance).

## 3. Event — FRESH approach to an existing zone Z (exact)

**Zones tested** (PERCEPTION_SPEC §2, all causal):
`swing` (O2 multi-swing cluster), `pdh_pdl` (O3 PDH/PDL/PDC), `session` (O4 Asia high/low),
`week` (O5), `round` (O6 00/50 grid). Band `[z_lo, z_hi]`, width `w = 0.25 x ATR14(H1)(a)` where `a` is
the confirm bar of the zone's last anchor (charter "width ~0.2-0.25 x ATR14(H1)" :55-56; v0 picks 0.25 and
freezes it).
Primary population: **intact** zones only (`broken_idx is None` at `t`). Broken-then-reclaimed (role-flip)
zones are a pre-declared **secondary table only**, never part of the gate.
Zone usable at `t` requires `created_idx <= t - 24` (an "existing" zone, not one born on the event bar)
and `t <= end_idx` (the object is still alive in the L1, not expired).

Let `A(t) = ATR14(H1)` at the last H1 bucket closed at or before the close of bar `t`;
`d(b, Z) = max(z_lo - c_b, 0, c_b - z_hi)` (0 inside the band).

Event at bar `t` on zone `Z` iff **all** hold:

1. **Entry**: `h_t >= z_lo` and `l_t <= z_hi` (bar range intersects the band).
2. **Freshness**: scanning `j = t-1, t-2, ...` down to `max(0, t-24)` over the existing M5 bars:
   - if a bar `j` has range ∩ Z -> **no event** (the episode started earlier; `t` is not its first entry),
   - else if `d(j, Z) >= 1.0 * A(t)` -> event accepted with `b0 = j` (stop the scan),
   - else continue; if the scan exhausts 24 bars with no away bar -> no event.
3. **Approach side**: `s = -1` (from below) iff `c_{t-1} <= z_lo`; `s = +1` (from above) iff
   `c_{t-1} >= z_hi`. Any other case (impossible with rule 1's scan, kept as a guard) -> reject + counter.
4. `A(t)` is valid (>= 14 completed H1 buckets since warm-up start).

Derived geometry for the outcome: near edge `e_near = z_lo` if `s=-1` else `z_hi`; far edge `e_far` = the
other edge; `z_mid = (z_lo+z_hi)/2`.

**De-duplication**: one event per (zone, approach episode) by construction (rule 2). Two events on the same
zone cannot be closer than 25 bars (the scan window), and a re-entry without an intervening `>= 1.0 x A(t)`
away bar does not fire. One bar may legitimately carry events on different zones — separate rows keyed by
`(symbol, bar_idx, zone_id, side)`. Consecutive same-zone events inside the outcome window are allowed by
the description above but are **not** removed: they are an event-table property to be reported (overlap
counter) and handled in §7's bootstrap, not by a post-hoc filter.

## 4. Outcome over <= 48 M5 bars (exact)

- Window: bars `j = t+1 .. t+48` (the event bar `t` itself is excluded — the entry is knowable only at its
  close; this kills the within-bar look-ahead debate for both real and fake events).
- Barrier: `m = 1.0 * A(t)` (frozen at the event bar). Bars must exist through `t+48` (else the event is
  dropped at extraction; no outcome imputation).
- **BOUNCE**: first touch of `b_lvl = e_near - m` (`s=-1`) / `e_near + m` (`s=+1`) on the M1 path.
- **BREAK**: first M5 bar whose **close** is `>= e_far + m` (`s=-1`) / `<= e_far - m` (`s=+1`).
- **Resolution rule (adverse-first, referee-consistent)**: scan M5 bars in order, each bar's M1 path in
  order. If the same M5 bar contains both the BOUNCE touch and the BREAK close, **BREAK wins** (break is
  the adverse outcome for the zone-respect hypothesis; the referee uses SL-first on ambiguity, charter
  :71-72, `ECON1_RESULTS.md:92`). If BOUNCE and BREAK occur in different bars, the earlier bar wins.
- **NONE**: neither by the end of `t+48`. Primary proportions are **conditional on resolution**:
  `P(BOUNCE|resolved) = n_bounce / (n_bounce + n_break)`; the raw shares (with NONE in the denominator) are
  also reported for real and control side by side, because a differing NONE rate is itself a finding.

**BREAK_CLOSE continuation analogue**: for every event whose outcome is BREAK, let `b_b` be the break-close
bar, `c_b` its close, and `side = -s` the direction of the break (`s=-1` = approach from below = upward
break = `side=+1`; `s=+1` = downward break = `side=-1`). New window `j = b_b+1 .. b_b+48`:
- **continuation**: first touch of `c_cont = c_b + side * m` on the M1 path;
- **return**: first touch of `z_mid` on the M1 path;
- same M1 bar -> `return` wins (adverse-first for continuation); resolved = continuation or return;
  `P(cont|resolved) = cont / (cont + ret)`; windows must fit inside DESIGN.
For fake zones the same rule with `z_mid` replaced by the fake band midpoint.

## 5. Controls — K=5 fake zones per real event

Charter text (:111-113): "per real event, K=5 fake zones at the same time, same side, same distance from
price, same width, placed at prices with no real zone or reference level within 2 widths (sampled from the
recent 5-day range). Same approach and outcome definitions."

**DECISION (v0 reading of the charter, flagged for Lead confirmation at freeze).** A horizontal level "at
the same distance from the current price on the same side" is the *same price* (prices are one-dimensional),
so "same time + same side + same distance + different eligible price" cannot all hold literally. v0 reads
the list as a **matched-design spec**, matched on:
- **same time**: fake zones are drawn at the anchor bar `t` (same market state); the fake *event* is the
  first fresh approach to the fake zone within `ctrl_search = 1440` bars (5 days) after `t`; the
  `t_k - t` distribution is a reported diagnostic. Literal same-bar entry is impossible for a different
  price, so epoch matching is the operational form.
- **same side**: `s` matched; the fake band lies entirely on the same side of `c_{t-1}` as `Z`.
- **same distance from price**: operationalized as the identical approach-distance rule (§3.2) plus the
  placement constraint that at the anchor the fake near edge is `>= 1.0 x A(t)` away from `c_{t-1}` — the
  same minimum distance the freshness rule uses. (This is the only reading that is simultaneously exact,
  testable and not degenerate.)
- **same width**: `w` copied from the real zone (price units).
- **no real object within 2 widths**: at both `t` (creation) and `t_k` (event), the fake band must be at
  band-to-band distance `> 2*w` from every live or broken L1 zone of any type and from every reference
  level (PDH/PDL/PDC/Asia/week/round), and `> 2*w` from `Z` itself.
- **sampled from the recent 5-day range**: candidate center prices `P ~ Uniform(R5 on the allowed side)`,
  `R5 = [min(l), max(h)]` over bars `t-1440 .. t-1`, excluding `|P - c_{t-1}| < 1.0 x A(t)`.

**Sampler**: per slot, up to 20 redraws; a draw is accepted when a fake event `t_k` in `[t, t+1440]`
satisfies §3 fully (same side, same rules) and both eligibility checks pass. If 20 redraws fail, the slot
is left empty, `n_ctrl < 5` is logged, and the event keeps its realized `K_e` (all statistics use the
realized `K_e`; the realized mean `K` is reported). Candidate `t_k` search uses the identical scanner as §3
(same code path, asserted by a test).

**Seed policy**: global program seed `20260920` (same as LINE-1 / ECON1,
`lines1_common.py:33`, `COST_FEASIBILITY.md:126`). Per-event RNG:
`np.random.default_rng([seed, symbol_ordinal, t])` — order-independent, reproducible, one control set per
real event. No re-seeding after the freeze; the control table is frozen with the event table (SHA in
`FREEZE.json`).

**Outcome at fake events**: identical definitions (§4) with `m_k = 1.0 * A(t_k)`, `w_k = w`, same side.
Barrier ATR is the fake event's own ATR (the literal §4 rule); the paired real-vs-control geometry is `m`
in each event's own volatility units. Pre-declared sensitivity view (b): all barriers (real and fake)
computed with `A(t)` frozen at the anchor `t`, while the fake event still fires at its own `t_k`.

## 6. Strata (all reported for real and control side by side)

| stratum | definition |
|---|---|
| strength tercile | strength v0 (PERCEPTION_SPEC §5) at the event bar; boundaries `q33/q67` computed on the pooled core event table **before** any outcome join, recorded in `FREEZE.json` |
| zone type | `swing` / `pdh_pdl` / `session` / `week` / `round` |
| scale | `micro` / `meso` / `macro` (strongest anchor scale of the zone) |
| symbol | core (gated) / extended (reported only) |
| year | server year of the event bar (DESIGN years 2016-2021 = 6) |
| session | Asia 00:00-05:00 UTC / London 05:00-11:00 / NY 11:30-17:30 / off — UTC windows from `vpa_random_baseline.py:50-53`, assigned by the event bar close's `utc_min` |

## 7. Statistics and gates

Notation: for real event `e` in a cell, `B_e = 1[BOUNCE]`, `R_e = 1[resolved]`; for its controls
`B_{e,k}`. Paired difference of the cell:
`D = mean_e [ (B_e / R_e) - (1/K_e) * sum_k (B_{e,k} / R_{e,k}) ]` (undefined pairs dropped and counted;
`resolved`-conditioned, §4).

- **CIs**: Wilson 95% CI per single proportion (per symbol/tercile cells).
- **Difference CI / primary test**: **paired cluster bootstrap** — resample the real events of the cell
  with replacement (B = 10,000, seed `20260920`), carrying each event's own control set; recompute `D`;
  report the percentile 2.5%/97.5% CI. Gate requires `D >= +5.0pp` **and** CI lower bound > 0.
- **Exact secondary test**: sign test — among events with `d_e != 0`, two-sided exact binomial on
  `#{d_e>0}` under p=0.5, reported with its p-value (scipy `binomtest`; if scipy is unavailable, the exact
  test is implemented by the closed-form binomial sum — no approximation).
- **Pooled vs per-symbol**: the gate statistic is pooled over core symbols (all core events in one pool);
  per-symbol `D` is reported, as are per-year `D`.

**Gate "LINES MATTER"** (charter :116-118, exact thresholds):
1. Top-tercile pooled `D_top >= +5.0pp` with bootstrap 95% CI lower bound `> 0`;
2. monotone across terciles: `D_bot <= D_mid <= D_top` (point estimates, no tolerance — literal reading);
3. same sign: `D_top > 0` in `>= 3/4` core symbols and in `>= 4/6` DESIGN years.

**Break-continuation analogue** (charter :118, same thresholds): replace BOUNCE with
`P(continuation|resolved)` over BREAK events (real) vs fake-zone break events (control); same pooled
`>= +5pp`, CI lower bound `> 0`, same monotonicity, same `3/4` and `4/6` rules. **Power floor
(pre-declared):** if the pooled top-tercile cell has fewer than 60 resolved break events, the analogue is
reported as `UNDERPOWERED` and does not gate this round.

Multiplicity: this prereg declares exactly 2 physical gate families (respect / continuation). The BH-FDR
rule (charter :159) governs round screens, not this preregistered physics question; each family must hold
its own thresholds independently. No other cell of this experiment may be quoted as a gate.

**Pre-declared sensitivity views** (reported inside the same trial, not gates): (a) symmetric-barrier
definition (BOUNCE also requires a close `m` away); (b) all barriers computed with `A(t)` frozen at the
anchor `t` (real and fake); (c) zone width 0.20 vs 0.25 x ATR14(H1); (d) block bootstrap by symbol-week.
All are fixed now, before any outcome.

## 8. Viability arithmetic per symbol (arithmetic only, no measurement)

With symmetric barriers `m` and round-turn cost `c_rt`, a fade/break edge fired at the zone nets
`2*p*m - c_rt` per event if it is right with probability `0.5 + p` (gross win `+m`, gross loss `-m`, one
cost per round trip). Break-even directional bias:

```
p_req = c_rt / (2m)     (charter :119-120)
p_viable = p_req + margin,   margin = +2.00pp (pre-declared)
```

**Margin justification (pre-declared, not calibrated):** (i) NONE/censored events are not free in live
management — the exit happens somewhere between the barriers, so a point estimate at break-even is not
enough; (ii) at the expected sample sizes a 95% CI half-width is a few pp, so the point estimate must clear
break-even by a buffer for evidence to exist; (iii) the +2.0pp is a fixed round number chosen before any
outcome, not tuned. `ASSUMPTION:` the fill/exit mechanics of a real setup (spread at fill, slippage beyond
`c_rt`) are treated as inside the margin, not separately modelled here.

`m = 1.0 x median ATR14(H1)` per symbol. Primary column from `DATA_INVENTORY.md:27-35` (overall
2010-2026 median, the file's downstream reference). Sensitivity column = median of the six yearly
medians 2016-2021 from the same file's per-year tables (pure arithmetic; rows cited below).
`c_rt` from charter :96-98 / `COSTS.md:21-29` / `pa_costs.py:40-57`; `proxy` = 1.4 fallback, not a
measurement.

Pre-declared context from the same cost table (not part of the table above): the 10x c_rt geometry guard
equals `1.02 / 1.07` x the median ATR14(H1) for AUDUSD / NZDUSD (`COSTS.md:87,90`), i.e. for those two a
`m = 1.0 x ATR14(H1)` barrier is the *smallest* geometry that could ever satisfy the guard at x1 — their
gate read must be interpreted with that in mind.

| Symbol | c_rt (pips) | source | m overall (pips) | p_req (pp) | **p_viable (+2pp)** | m DESIGN-sens (pips) | p_viable sens (pp) | ATR rows (DATA_INVENTORY.md) |
|---|---|---|---|---|---|---|---|---|
| EURUSD (core) | 1.0 | measured, `COST_FEASIBILITY.md:75` | 15.40 | 3.25 | **5.25** | 14.53 | 5.44 | overall :29; yearly :116-121 |
| GBPUSD (core) | 1.1 | measured, `COST_FEASIBILITY.md:76` | 19.40 | 2.84 | **4.84** | 18.715 | 4.94 | overall :30; yearly :174-179 |
| USDJPY (core) | 1.4 | measured, `COST_FEASIBILITY.md:77` | 15.81 | 4.43 | **6.43** | 12.20 | 7.74 | overall :31; yearly :232-237 |
| AUDUSD (core) | 1.4 | `proxy`, charter :97-98 | 13.72 | 5.10 | **7.10** | 11.955 | 7.86 | overall :32; yearly :290-295 |
| USDCAD (ext) | 1.4 | `proxy`, charter :97-98 | 15.25 | 4.59 | **6.59** | 16.115 | 6.34 | overall :33; yearly :348-353 |
| USDCHF (ext) | 1.1 | measured, `COST_FEASIBILITY.md:78` | 12.80 | 4.30 | **6.30** | 11.405 | 6.82 | overall :34; yearly :406-411 |
| NZDUSD (ext) | 1.4 | `proxy`, charter :97-98 | 13.13 | 5.33 | **7.33** | 12.135 | 7.77 | overall :35; yearly :464-469 |

Reading rule (pre-declared): after the physics run, the measured top-tercile bias is compared with
`p_viable` per symbol; a symbol whose measured bias is below `p_viable` cannot carry a level family at
`m = 1 x ATR14(H1)` without either a smaller `c_rt`, a larger barrier geometry or a bigger measured bias.
This is arithmetic, no outcomes were measured to write it.

Fallback if an ATR number is missing (did not happen; kept for the block): use the ATR14 M5 table
`COST_FEASIBILITY.md:28-37` scaled by `sqrt(12)` and mark the cell `ASSUMPTION:`. All 7 symbols are present
in `DATA_INVENTORY.md`, so no cell uses this path.

## 9. Run plan for R01

**Build order (code):**
1. `lib/pa_data.py` — M5+M1+tick-volume loader on `lib/pa_clock.py`, DESIGN guard, suspect drop. Caller: all runs.
2. `struct/line_engine.py` — verbatim copy of LINE-1 `vpa_lines.py` + `tests/test_line_engine.py`
   (prefix invariance). Provenance SHA in `docs/PROVENANCE.md`.
3. `struct/swings.py`, `zones.py`, `refs.py`, `patterns.py`, `buildup.py`, `trend.py`, `context.py`,
   `events.py`, `pa_struct.py` per `struct/PERCEPTION_SPEC.md` §2-§4, with
   `tests/test_struct_causal.py` (prefix invariance + no-future-access for every module).
4. `rounds/R01/phys_extract.py` — build the zone table, the fresh-approach event table, and the K=5
   control sets using the frozen seed. **Writes no outcome columns.** Outputs `EVENTS.csv`, `CONTROLS.csv`.
5. **FREEZE** (single script step, recorded before outcomes): `rounds/R01/FREEZE.json` =
   `{prereg_sha256, struct_code_sha256, lib_code_sha256, events_sha256, controls_sha256, seed=20260920,
   q33, q67, n_events_real, n_controls_realized, n_events_dropped_window, gate_table}`. The prereg SHA is
   this file promoted to frozen status; the code SHA covers sorted `struct/*.py` then sorted `lib/*.py`
   (same hash method as `pa_ledger.code_sha256:228-239`, applied to both directories).
6. `rounds/R01/phys_resolve.py` — join outcomes (M5 closes + M1 path), build `PHYSICS_RESULTS.md`
   (all §6 strata, §7 statistics, §8 comparison). Run via `lib/pa_slots.py` (max 2 our processes,
   OMP/MKL/OPENBLAS=4, BelowNormal) — mandatory, charter :214-215.
7. `rounds/R01/ROUND_REPORT.md` (charter :220-222) + report to the Lead. No commit, no push.

**Ledger discipline:** R01 consumes **1 trial** (`trial_id` auto from `lib/pa_ledger.py:140-167`,
`family="level_physics"`, `spec_sha256` = frozen prereg, `split="DESIGN"`, symbols core). The per-symbol,
per-year, per-tercile tables and the four pre-declared sensitivity views are fields of that one trial's
`key_metrics`, not extra trials. Any later weight calibration (charter :121-122) is a **new** trial.
A FAIL gate is logged with the same discipline and closes the question per charter :123-124.

**Power floor (pre-declared before extraction):** if pooled core real events < 1,000, the round reports the
gate as `UNDERPOWERED` and does not declare LINES MATTER either way; the extraction counters (events
extracted, dropped for window/eligibility reasons, controls realized) are reported in full.

**What this draft deliberately does not do:** no perception code, no events, no proportions, no fills, no
economic evaluation, no worktree, no commit.
