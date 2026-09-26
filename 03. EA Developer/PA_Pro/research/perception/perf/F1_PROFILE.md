# F1 — throughput collapse profile + proposed patch (R47 §47.4.3 / R48 §48.5)

Scope: profile-only, outcome-blind.  DESIGN EURUSD M5 2019-01+ via
`scale/design_loader.py`, one `pa_slots` slot, BelowNormal.
Raw logs: `_log_f1.txt` (unpatched 55d), `_f1_profile_perf.py` output
(patched 25d).  Patch candidate: `_scratch/perf/` (engine.py, swings.py).

## Measured collapse (unpatched STABLE 9acaa206)

| day | bars/s | book.seq | objects tot/del | births |
|-----|--------|----------|-----------------|--------|
|   0 |    991 |       90 |    36 /  29     |    17  |
|   5 |     92 |      526 |   115 / 108     |    85  |
|  25 |     54 |     2472 |   412 / 407     |   346  |
|  50 |     12 |     4791 |   763 / 758     |   675  |
|  54 |     32 |     5096 |   815 / 808     |   724  |

(Rows: ~92 swings/day appended forever; ~14 objects/day retire but stay
in `objects`; `_births` ledger never trims.  Bounded: ACTIVE 5–8,
salience pool 15–27, grave maps ~50.)

cProfile day 5 → day 50 (275-bar day): calls 9.0M → 66.2M,
wall 3.1s → 23.6s.  Top fns day 50: `book.alive` 15.3s cum /
2645 calls, `floor_min` 12.5M calls, `_floors` 15.2M calls,
`engine._abr` 15.2M calls — every floor check walks all of `seq` and
re-derives `ABR(t_conf)` per pivot.  Same signature as SCALE's
6484-bar run (FINDINGS F1).

## Why each structure grows

- `book.seq`: append-only saddle evidence — `alive()`, `structural()`,
  `recent()`, `superseded()` all re-scan it per call; `alive` alone is
  called ~2645×/day (salience scoring, lines eval, box windows).
- `engine.objects`: append-only — dead objects are never unlinked;
  `active()` scans all 815 to return ~7.
- `_births`: append-only rate ledger — scans stay ~724×few per round;
  not hot, left alone.

## Patch (`_scratch/perf/`, proposed — NOT landed; §48.5 identity gate)

No lookback shortened.  Pure indexing/caching:

1. **`swings._floors` memoized on the Pivot.** `floor_min(p)` /
   `floor_struct(p)` depend only on `p.t_conf` (frozen at confirm) and
   the fixed pmin/pstruct multiples — a pure function of the pivot.
   Cached as `p._fl` on first use → `engine._abr` calls collapse from
   15.2M to ~#pivots.
2. **`book._alive` maintained incrementally in `add()`.**  alive-ness
   is fixed at birth (`prom_birth` and floor are both frozen), so the
   survivor list is append-only.  `alive()` returns the book's own
   list (read-only contract — verified: every caller iterates or
   comprehends, none mutates).
3. **`structural()` cached per book generation.**  `_gen` bumps on
   `add()` and on real prom deepens in `update_running()` only;
   ~10 structural() calls/bar collapse to ≤1 recompute.
4. **`recent()` / `superseded()` bisect.**  `seq` and `_alive` are
   t_conf-monotonic (pivots emit in confirm order) → prefix windows
   via `bisect` instead of full scans.
5. **`engine._act` registry.**  `Obj.state` becomes a property whose
   setter adds/removes `o` in `eng._act` (dict keyed by objects-index);
   `active()` = sorted keys → exact objects-order preserved (revivals
   land at original index — tie-break order unchanged).  `__setstate__`
   bridges legacy pickles (`state` → `_state`).

Untouched: `_prominence` backward scan (bounded by dominator),
`_births` (small), `cand_log` (opt-in), all scoring logic.

## Measured result (patched, same 2019-01+ DESIGN run, `_log_f1_perf55.txt`)

| day | bars/s unpatched | bars/s patched | speedup |
|-----|------------------|----------------|---------|
|   0 |    991 |  1167 |  1.2× |
|   5 |     92 |   743 |  8.1× |
|  24 |     58 |   191 |  3.3× |
|  50 |     12 |   118 |  9.8× |
|  54 |     32 |   104 |  3.3× |

Structure counts are IDENTICAL run-to-run (seq 5096, objects 815,
births 724 at day 54) — the patch changes cost, not content.

Same-day cProfile (day-21 segment): 981k calls / 0.282s →
95k calls / 0.058s (~10× fewer calls, ~5× wall).  Residual slope is
the genuine per-candidate swing scans in salience/lines
(`_lab_line_score`, `score`, `_eval`) — next lever if needed:
dir/t_ext-indexed alive views; not required for this pass.

## Identity evidence so far

- `tests/` on patched modules: same 7 named failures, rest green
  (test_swings + test_cet fully green).
- `cache.canonical()` (objects+cand_log+bars) vs `9acaa206` pickles:
  **1728/1728 byte-identical** — all 576 `m1_v1` tau windows plus the
  1152 `c1r_p_cong_k3`/`c1r_p_cong_n8` variant runs (param-overridden
  patched engines reproduce those too), 0 diff, 0 err.
- 20-day continuous DESIGN run: engine output **byte-identical** to
  unpatched (`_canon_20d.pkl`), 345 vs 143 bars/s (2.4×).
- Pickle round-trip of a patched engine: canonical-identical; `_act`
  registry restores; `__setstate__` reads legacy `state` pickles.

## Identity plan for landing (next round, §48.5)

1. ~~TUNE 1728/1728~~ — done: 1728/1728 byte-identical (all tau
   windows, all three cached param variants).
2. ~~Byte-identical 20-day DESIGN run~~ — done (above).
3. ~~55-day speed run~~ — done: day-50 118 vs 12 bars/s (~10×).
4. ~~Unmodified suite on patched defaults~~ — done: **65/72, the same
   seven named failures**, zero new (PYTHONPATH=_scratch/perf pytest).
