VERDICT: PASS

Neutral adversarial re-review of T-PAPRO-ZONE-1 (2026-09-20) after the first review of
this file returned FAIL. All three previous hard failures are fixed and independently
re-verified; checks A-E pass. Only cosmetic residuals remain (last section). Summary of
the three fixed findings:

1. **Prefix-test non-vacuity — FIXED.** `tests/test_prefix_invariance.py` now picks query
   bars dynamically where the live book is non-empty (`_pick_query_bars`, :27-35),
   asserts `live_full` non-empty, and compares `live_dicts(t)` (17-key full causal state)
   and `zones_at(t)` between the full and truncated runs (`_assert_prefix_equal`, :38-52).
   On both fixtures every chosen bar has 2-25 live zones and both books are equal. A leaky
   `FractalZones` subclass reading `ctx.a(min(t+5, n-1))` is caught by the test's own
   prefix comparison (`AssertionError ('fractal_h1', 2000)`) and by the corruption probe
   (first diff `clean=(2, 1.128576, 1.129054)` vs `corrupt=(2, 1.159181, 1.159659)`);
   the clean generator passes the same probe. The old `[] == []` failure is gone.
2. **SHORTLIST numbers — FIXED.** `fractal_h1` 674/50k and `ref_levels` 1284/50k are the
   headline numbers; 6111 and 11402 are now labelled "over the full 2016-2021 DESIGN
   slice" (re-measured: 6111 and 11402 on n=445,858). `profile_va` now reads "six of the
   eight windows show 0 armed zones (only windows 3 and 4 arm 1 and 2)". Every section-2
   "Measured" number and every section-3 data cell matches my rerun (only run-second cells
   differ, wall-clock noise on a shared machine).
3. **Arming rule — FIXED.** `common.arm_zones` skips `v.broken_idx is not None`
   (common.py:641-642); the new `test_armed_excludes_broken` (:91-99) covers it. Measured:
   zero broken zones in any armed set over the test fixture and over a 62-bar scan
   (line1_cluster excluded 107 broken live zones, fractal_h1 48). SHORTLIST section 1 now
   matches the code.

Commands were run from `<repo>\03. EA Developer\PA_Pro` (or the
`struct/zones` directory for pytest), one process at a time, BelowNormal,
`OMP_NUM_THREADS=4`. No file other than this review was written; no git, no MT5.

---

## Check A — full suite: PASS

**Method.** Exact command in `<repo>\03. EA Developer\PA_Pro\struct\zones`:

```
(Get-Process -Id $PID).PriorityClass='BelowNormal'; $env:OMP_NUM_THREADS=4; python -m pytest tests -q
```

**Evidence (verbatim):**

```
..................................................                       [100%]
50 passed in 22.95s
```

Collection (verbatim last line and the new ids):

```
50 tests collected in 0.13s
...
tests/test_prefix_invariance.py::test_armed_excludes_broken[line1_cluster]
...
tests/test_prefix_invariance.py::test_armed_excludes_broken[ref_levels]
```

The previous review recorded `44 passed in 18.39s`; the count grew by exactly 6 = the six
parametrized cases of `test_armed_excludes_broken`, which is present in the collection.
`SHORTLIST.md:25` ("50 tests pass") now matches the suite.

**PASS.** (No counterexample.)

---

## Check B — prefix-test non-vacuity: PASS (previous FAIL fixed)

**Method.** Heredoc replicating the test's `_pick_query_bars` on the exact two fixtures of
`test_prefix_invariance.py` (`synthetic_bars(n=2200, seed=11)`, `t_trunc=2000`;
`load_ctx(max_bars=6000)`, `t_trunc=4500`), then running the test's own
`_assert_prefix_equal`-equivalent comparison (full ctx vs `slice_bars(bars, t_trunc+1)`),
plus a leaky subclass of `FractalZones` overriding `_on_bar` to read
`ctx.a(min(t+5, n-1))` and shift all live bands by `A5 - A0`.

**Evidence — chosen bars and live-book sizes (verbatim):**

```
=== synthetic n=2200 seed=11 t_trunc=2000 ===
line1_cluster  qbars=[1950, 1975, 2000]  live=[6, 6, 6]  armed=[0, 0, 0] live>0=True eq_live=True eq_zones=True OK
fractal_h1     qbars=[1950, 1975, 2000]  live=[2, 2, 2]  armed=[0, 0, 0] live>0=True eq_live=True eq_zones=True OK
kde_swing      qbars=[1950, 1975, 2000]  live=[8, 8, 8]  armed=[0, 0, 0] live>0=True eq_live=True eq_zones=True OK
profile_va     qbars=[1950, 1975, 2000]  live=[4, 4, 4]  armed=[0, 0, 0] live>0=True eq_live=True eq_zones=True OK
sd_base        qbars=[1950, 1975, 2000]  live=[3, 3, 3]  armed=[0, 0, 0] live>0=True eq_live=True eq_zones=True OK
ref_levels     qbars=[1950, 1975, 2000]  live=[7, 7, 7]  armed=[0, 0, 0] live>0=True eq_live=True eq_zones=True OK
one dict key count=17 keys=['age', 'born_idx', 'broken_idx', 'fresh', 'hi', 'kind', 'last_touch', 'lo', 'meta', 'n_respected', 'parts', 'quality', 'role_flip', 'scale', 'strength', 'touches', 'zid']
=== real EURUSD max_bars=6000 t_trunc=4500 ===
line1_cluster  qbars=[4450, 4475, 4500]  live=[24, 25, 24] armed=[6, 5, 6] live>0=True eq_live=True eq_zones=True OK
fractal_h1     qbars=[4450, 4475, 4500]  live=[13, 12, 13] armed=[2, 1, 4] live>0=True eq_live=True eq_zones=True OK
kde_swing      qbars=[4450, 4475, 4500]  live=[15, 15, 16] armed=[3, 4, 6] live>0=True eq_live=True eq_zones=True OK
profile_va     qbars=[4450, 4475, 4500]  live=[3, 3, 3]  armed=[2, 1, 0] live>0=True eq_live=True eq_zones=True OK
sd_base        qbars=[4450, 4475, 4500]  live=[2, 2, 2]  armed=[1, 1, 1] live>0=True eq_live=True eq_zones=True OK
ref_levels     qbars=[4450, 4475, 4500]  live=[8, 8, 8]  armed=[1, 1, 2] live>0=True eq_live=True eq_zones=True OK
one dict key count=17 keys=['age', 'born_idx', 'broken_idx', 'fresh', 'hi', 'kind', 'last_touch', 'lo', 'meta', 'n_respected', 'parts', 'quality', 'role_flip', 'scale', 'strength', 'touches', 'zid']
```

Every comparison is between non-empty books of real state dicts (17 keys, including
`broken_idx`, `role_flip`, `quality`, `parts`), and the truncated run equals the full run
on both `live_dicts` and `zones_at` for all 12 generator x fixture combinations.

**Evidence — leak detection (verbatim):**

```
t=1999 full a(2004)=0.003980976 | cut a(2000)=0.004016980
t=2000 full a(2005)=0.003980976 | cut a(2000)=0.004016980
LEAK CAUGHT (prefix comparison): ('fractal_h1', 2000)
leaky mutant: live_clean=3 live_corrupt=3 CAUGHT=True
  first diff: clean=(2, 1.128576, 1.129054) corrupt=(2, 1.159181, 1.159659)
negative control (clean FractalZones): live_clean=2 live_corrupt=2 CAUGHT=False
```

The corruption probe corrupts all bars after t and all H1 buckets whose close is later
than the M5 close at t (indices `>= hcut`). An earlier probe attempt that started at
`hcut+1` left the one future-relevant H1 bucket intact and was correctly NOT caught,
which confirms the probe detects the read of exactly that bucket. The clean generator
passes the identical probe, so the catch is attributable to the leak.

**Residual (cosmetic, not a FAIL):** on the synthetic fixture the ARMED sets at the
chosen bars are still empty for all six generators (`armed=[0,0,0]`), so the `zones_at`
equality line there is still `[] == []`; the non-vacuity now rests on `live_dicts`
(6/2/8/4/3/7 zones). On real data all six armed sets are non-empty.

**PASS.**

---

## Check C — arming fix: PASS (previous FAIL fixed)

**Method.** Code read of `common.arm_zones`; heredoc on the exact test fixture
(`load_ctx(max_bars=8000)`, bars 4000/5500/7999) comparing `views_at(t, arm=False)` vs
`views_at(t, arm=True)` for all six generators, plus a 62-bar scan for `line1_cluster`
and `fractal_h1`; read of the new test.

**Code (common.py:639-642, verbatim):**

```python
    out = []
    for v in views:
        if v.broken_idx is not None:
            continue
```

**Test (tests/test_prefix_invariance.py:91-99, verbatim):**

```python
@pytest.mark.parametrize("name", registry.names())
def test_armed_excludes_broken(name):
    ctx = load_ctx(max_bars=8000)
    g = _gen(name, ctx).run()
    for t in (4000, 5500, 7999):
        armed_ids = {z.zid for z in g.views_at(t, arm=True)}
        for v in g.views_at(t, arm=False):
            if v.broken_idx is not None:
                assert v.zid not in armed_ids, (name, t, v.zid)
```

**Evidence — exact test fixture (verbatim):**

```
line1_cluster  t=4000  live=19  armed=6  broken_live=0  broken_armed=0 excluded=0
line1_cluster  t=5500  live=22  armed=5  broken_live=3  broken_armed=0 excluded=3
line1_cluster  t=7999  live=18  armed=5  broken_live=1  broken_armed=0 excluded=1
fractal_h1     t=4000  live=10  armed=2  broken_live=0  broken_armed=0 excluded=0
fractal_h1     t=5500  live=14  armed=1  broken_live=2  broken_armed=0 excluded=2
fractal_h1     t=7999  live=14  armed=4  broken_live=0  broken_armed=0 excluded=0
kde_swing      t=4000  live=13  armed=4  broken_live=0  broken_armed=0 excluded=0
kde_swing      t=5500  live=16  armed=3  broken_live=1  broken_armed=0 excluded=1
kde_swing      t=7999  live=10  armed=3  broken_live=0  broken_armed=0 excluded=0
profile_va     t=4000  live=4   armed=1  broken_live=0  broken_armed=0 excluded=0
profile_va     t=5500  live=4   armed=0  broken_live=0  broken_armed=0 excluded=0
profile_va     t=7999  live=5   armed=1  broken_live=0  broken_armed=0 excluded=0
sd_base        t=4000  live=1   armed=0  broken_live=0  broken_armed=0 excluded=0
sd_base        t=5500  live=3   armed=1  broken_live=0  broken_armed=0 excluded=0
sd_base        t=7999  live=1   armed=0  broken_live=0  broken_armed=0 excluded=0
ref_levels     t=4000  live=8   armed=3  broken_live=0  broken_armed=0 excluded=0
ref_levels     t=5500  live=8   armed=2  broken_live=2  broken_armed=0 excluded=2
ref_levels     t=7999  live=8   armed=3  broken_live=1  broken_armed=0 excluded=1
```

**Evidence — 62-bar scan (verbatim):**

```
line1_cluster  sampled bars=62 armed_total=312 broken_in_armed=0 broken_excluded=107
fractal_h1     sampled bars=62 armed_total=159 broken_in_armed=0 broken_excluded=48
```

No armed view anywhere has `broken_idx is not None`, and the exclusion is non-vacuous
(line1_cluster 3+1 broken at two of the three test bars, fractal_h1 2, ref_levels 2+1,
kde_swing 1; across the scan 107 and 48). **PASS.**

---

## Check D — SHORTLIST number honesty: PASS

**Method.** Fresh `python struct/zones/diagnostics.py --max-bars 50000` from
`03. EA Developer/PA_Pro`; full-series run through `load_ctx("EURUSD")` (n=445,858) for
the two previously false counts; `snapshots/INDEX.csv` recomputed with python `csv`;
verbatim cell-by-cell comparison against `SHORTLIST.md` sections 2 and 3; independent
spot-check of three INDEX rows against a live run on the full series.

**Section 3 table vs fresh diagnostics (verbatim):**

```
symbol=EURUSD bars=50000 queries=[8333, 18749, 29166, 39582, 49999]
line1_cluster      0.7s created=  1845 live=[25, 20, 18, 12, 20] armed=[6, 4, 6, 6, 6] width_atr_med=0.50
fractal_h1         0.2s created=   674 live=[15, 21, 14, 10, 15] armed=[3, 1, 4, 1, 3] width_atr_med=0.32
kde_swing          1.8s created=   570 live=[9, 7, 9, 13, 15] armed=[3, 0, 3, 5, 2] width_atr_med=0.60
profile_va         0.6s created=   177 live=[4, 4, 3, 6, 8] armed=[1, 0, 1, 0, 0] width_atr_med=0.54
sd_base            0.4s created=   304 live=[5, 3, 5, 7, 4] armed=[1, 0, 1, 3, 0] width_atr_med=0.32
ref_levels         0.4s created=  1284 live=[7, 9, 9, 8, 9] armed=[2, 1, 4, 4, 3] width_atr_med=0.27
```

Cell comparison against SHORTLIST.md:264-269 — all created/live/armed/width cells match
exactly; the only differing cells are run-seconds: kde_swing 1.2 vs my 1.8, ref_levels
0.3 vs my 0.4. Those are wall-clock quantities on a shared machine, not data claims.

**Section 2 "Measured" lines — all verified:**

- 2.1 (:131-132) "1845 zones created, live 12-25, armed 4-6; on the 8 windows armed avg
  5.38, max 6" — created 1845, live 12-25 over the 5 sampled bars, armed 4-6, INDEX avg
  5.3750, max 6. Match.
- 2.2 (:155-157) "674 zones created / 50k bars (6111 over the full 2016-2021 DESIGN
  slice), armed avg 2.50 on the 8 windows, max 4" — diagnostics 674; full series
  `full-slice fractal_h1 zones created = 6111` (n=445858); INDEX avg 2.5000 max 4. Match;
  the old false "6111 / 50k" wording is gone.
- 2.3 (:186) "570 zones created / 50k bars, armed avg 2.50 on the 8 windows, max 5" —
  diagnostics 570; INDEX avg 2.5000 max 5. Match.
- 2.4 (:204-209) "armed 3 zones total (avg 0.38, max 2) and six of the eight windows show
  0 armed zones (only windows 3 and 4 arm 1 and 2)" — INDEX `[0,0,0,1,2,0,0,0]`: total 3,
  avg 0.3750, max 2, six zeros, windows 3 and 4. Match; the old "two windows" claim is
  gone.
- 2.5 (:232-233) "304 zones created / 50k bars, armed avg 1.00 on the 8 windows, max 3" —
  diagnostics 304; INDEX avg 1.0000 max 3. Match.
- 2.6 (:252-254) "1284 zones created / 50k bars (11402 over the full 2016-2021 DESIGN
  slice), armed avg 3.00 on the 8 windows (max 4), the highest non-baseline armed count" —
  diagnostics 1284; full series `full-slice ref_levels zones created = 11402`; INDEX avg
  3.0000 max 4; non-baseline averages ref 3.00 > fractal 2.50 = kde 2.50 > sd 1.00 >
  profile 0.375. Match; the old false "11402 / 50k" wording is gone.

**Section 3 window-average prose (:271-274) vs INDEX (verbatim):**

```
fractal_h1     n=8 armed=[2, 2, 3, 2, 4, 3, 1, 3] avg=2.5000 max=4 zeros=0
kde_swing      n=8 armed=[3, 1, 4, 3, 2, 1, 1, 5] avg=2.5000 max=5 zeros=0
line1_cluster  n=8 armed=[6, 6, 6, 4, 5, 5, 6, 5] avg=5.3750 max=6 zeros=0
profile_va     n=8 armed=[0, 0, 0, 1, 2, 0, 0, 0] avg=0.3750 max=2 zeros=6
ref_levels     n=8 armed=[2, 3, 4, 3, 4, 3, 2, 3] avg=3.0000 max=4 zeros=0
sd_base        n=8 armed=[0, 1, 1, 3, 1, 0, 0, 2] avg=1.0000 max=3 zeros=3
```

All six averages/maxes match :272-273 (5.38/6, 3.00/4, 2.50/4, 2.50/5, 1.00/3, 0.38/2).

**Independent spot-check of INDEX rows against the live full series (verbatim):**

```
line1_cluster  bar=44161 counts_at=(18,6) width_med=0.576 | INDEX says (18,6) w=0.576
fractal_h1     bar=44161 counts_at=(15,2) width_med=0.349 | INDEX says (15,2) w=0.349
profile_va     bar=423050 counts_at=(9,0) width_med=nan | INDEX says (9,0) w=nan
```

The regenerated INDEX (mtime 21:41:21) is consistent with the fixed arming rule.

**PASS** (the two timing cells are cosmetic, not a data mismatch).

---

## Check E — regression pass of previously passing checks: PASS

**E1. Corruption probe, all six generators, two bars.** Same method as the first review
(`load_ctx(max_bars=4000)`, t=2999 and 3599; all bars after t replaced by `x*1.07 + 0.05`,
all H1 buckets with close later than the M5 close at t shifted the same way; fresh run;
compare armed `zones_at(t)` and `live_dicts(t)`).

```
line1_cluster  t=2999 zones=6 corrupted_zones=6 CAUGHT_zones=True live=22 corrupted_live=22 CAUGHT_live=True
fractal_h1     t=2999 zones=4 corrupted_zones=4 CAUGHT_zones=True live=9 corrupted_live=9 CAUGHT_live=True
kde_swing      t=2999 zones=4 corrupted_zones=4 CAUGHT_zones=True live=15 corrupted_live=15 CAUGHT_live=True
profile_va     t=2999 zones=2 corrupted_zones=2 CAUGHT_zones=True live=8 corrupted_live=8 CAUGHT_live=True
sd_base        t=2999 zones=0 corrupted_zones=0 CAUGHT_zones=True live=1 corrupted_live=1 CAUGHT_live=True
ref_levels     t=2999 zones=3 corrupted_zones=3 CAUGHT_zones=True live=8 corrupted_live=8 CAUGHT_live=True
t=2999 ALL IDENTICAL zones=True live_dicts=True
line1_cluster  t=3599 zones=6 corrupted_zones=6 CAUGHT_zones=True live=13 corrupted_live=13 CAUGHT_live=True
fractal_h1     t=3599 zones=4 corrupted_zones=4 CAUGHT_zones=True live=8 corrupted_live=8 CAUGHT_live=True
kde_swing      t=3599 zones=3 corrupted_zones=3 CAUGHT_zones=True live=15 corrupted_live=15 CAUGHT_live=True
profile_va     t=3599 zones=0 corrupted_zones=0 CAUGHT_zones=True live=4 corrupted_live=4 CAUGHT_live=True
sd_base        t=3599 zones=2 corrupted_zones=2 CAUGHT_zones=True live=2 corrupted_live=2 CAUGHT_live=True
ref_levels     t=3599 zones=2 corrupted_zones=2 CAUGHT_zones=True live=8 corrupted_live=8 CAUGHT_live=True
t=3599 ALL IDENTICAL zones=True live_dicts=True
```

All 12 comparisons (armed set and full live book) are unchanged when every bar after t is
replaced; the live book carries the check where the armed set is empty (`sd_base` t=2999).
`sd_base` armed at t=2999 is now 0 (was 1 before the arming fix) — an expected consequence
of the fix, and its live book (1 zone) is still compared.

**E2. No-outcome grep.** Pattern
`pnl|profit|win_rate|bounce|forward|shift\(|\[t \+|t\+1|t\+48`, case-insensitive, over
`struct/zones/` and `research/zones/` (excluding this review file). Per-file hit counts
(verbatim from `rg -c`):

```
struct/zones: common.py 3, refs.py 1, runner.py 1, profile_zones.py 1, ref_zones.py 1,
              sd_base_zones.py 1, tests/test_prefix_invariance.py 1
research/zones: INDICATOR_SURVEY.md 30, _legacy_kills.md 39, SHORTLIST.md 7,
              _survey_python_academic.md 25, _survey_tv.md 2, _survey_mt45.md 1
```

Classification: every hit is prose or a docstring. In `struct/zones/` all nine are
"no outcomes / no PnL / no forward bars" declarations (`common.py:8,13,339`, `refs.py:12`,
`runner.py:15`, `profile_zones.py:34`, `ref_zones.py:42`, `sd_base_zones.py:6`) plus the
`test_prefix_invariance.py:8` docstring "bars[:T+1]". In `research/zones/` they are the
explicit no-outcome statements (`SHORTLIST.md:5,329,339`; `INDICATOR_SURVEY.md:3,11,723`),
academic findings quoted as literature (Osler, Park & Irwin, Lo et al.), and legacy PnL
metrics quoted from `_legacy_kills.md` as citations. No computation of any outcome.

A code-only search for future indexing (`\[t *\+ *[0-9]|\[j *\+ *[0-9]|shift\(` over
`struct/zones/*.py`) found no `shift(` and no `[t + k]`/`[j + k]` indexing; the only hits
are `common.py:148,150` (`h[j + 1:j + k + 1]` inside `confirmed_pivots`, whose consumers
gate on `confirm_idx = j + k <= t`) and the matching assertion at `tests/test_common.py:141`
— the same accepted causal-precompute pattern as the first review.

**E3. INDEX.csv / PNGs.**

```
INDEX.csv data rows = 48
missing PNG files = []
PNG count = 48
max armed across rows = 6 (line1_cluster)
```

All 48 rows are 6 generators x 8 windows, every `file` path resolves.

**E4. WINDOWS.json mtime.**

```
WINDOWS.json mtime = 2026-09-20 21:19:26.352279
first PNG mtime    = 2026-09-20 21:40:45.454369
WINDOWS.json earlier than first PNG = True
```

(The 48 PNGs were re-rendered ~21:40 after the arming fix; `INDEX.csv` 21:41:21,
`SHORTLIST.md` 21:41:58. The window record predates the first render, as claimed.)

**E5. INDICATOR_SURVEY.md.**

```
candidate headings: 1.1-1.15 (15) + 2.1-2.15 (15) + 3.1-3.9 (9) + 4.1-4.10 (10) = 49
## 5. What the legacy repo already killed in this space (line 695)
### Zone physics is a different question (line 720)
```

49 candidate blocks, requirement >= 12 met; the legacy-kills section exists with the
no-outcomes disclaimer. Unchanged from the first review.

**PASS.**

---

## Claims I could not verify

- The survey's external facts (licences, URLs, `[fetched]` markers, quoted licence
  headers) were not re-fetched; only its structure and candidate counts were checked.
- I did not vision-review the 48 PNG files this round (existence, path resolution, row
  counts and INDEX-vs-live-series consistency were checked instead).
- R01 has not been run, so I cannot verify that the pre-declared broken-then-reclaimed
  secondary table will actually be produced there.
- No git was used (per task rules), so the change history/diff of the fix was not
  inspected; only the current file contents and their behavior were verified.
- The provenance `_survey_*.md` numbers were not re-derived from upstream sources.

## Residual cosmetic issues (none is a check failure)

1. Two run-second cells in SHORTLIST section 3 differ from a fresh rerun (kde_swing 1.2
   vs 1.8, ref_levels 0.3 vs 0.4); wall-clock noise, all data cells match.
2. On the synthetic prefix fixture the armed sets at the chosen bars are empty for all
   six generators, so the `zones_at` equality assertion remains `[] == []` there; the
   non-vacuity comes from `live_dicts` (which the test asserts non-empty and compares).
3. `test_armed_excludes_broken` does not assert that broken zones exist at its three
   bars; it is vacuous for `profile_va` and `sd_base` there (the other four generators
   exercise it). A positive control would make the test self-documenting.
4. The first review's non-future Defect 1 is unchanged: `state_at` replays from
   `born_idx` while the pass starts `_step_zone` at `created_idx` (common.py:433 vs
   :538), so for born<created zones the replayed `touches`/`fresh` are not literally
   "the state the pass built" (all bars <= t; no leak). Out of scope of the three FAIL
   findings, but still worth a future cleanup.
5. `meta["n_members"]` in line1_cluster/fractal zones is now static 1 (the member count
   lives in `quality`, causally); harmless, since `zone_dict` does not expose `meta`.
6. Section 2.1's "live 12-25" is derived from the same 5 sampled bars as section 3, not a
   full-run range; minor ambiguity inherited from the first version.

---

*(Reviewer note: this file overwrote the previous FAIL version of the same review; the
evidence above is from the re-review run on 2026-09-20. No repo file other than this one
was modified.)*
